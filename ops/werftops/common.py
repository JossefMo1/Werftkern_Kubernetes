"""Small fail-closed building blocks. Host paths are trusted administrator inputs."""
from __future__ import annotations
import contextlib, fcntl, hashlib, json, os, pathlib, re, signal, stat, subprocess, tempfile, threading, time

class Blocked(RuntimeError):
    pass

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()

def fingerprint(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def digest_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def private_read(path, limit=4*1024*1024):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_mode & 0o077 or s.st_uid != os.geteuid() or s.st_size > limit:
            raise Blocked("PRIVATE_OWNED_REGULAR_FILE_REQUIRED")
        raw = f.read(limit+1)
        if len(raw) > limit:
            raise Blocked("FILE_TOO_LARGE")
        return raw

def bounded_read(path, limit=4*1024*1024):
    """Read a non-private regular file without an unbounded allocation.

    Public JSON inputs may intentionally use normal file permissions (and may
    be symlinks), so this does not apply the ownership/mode checks from
    ``private_read``.  The descriptor is opened before checking its metadata,
    which keeps the size decision tied to the bytes that are actually read.
    """
    if type(limit) is not int or limit < 1:
        raise Blocked("FILE_READ_LIMIT_INVALID")
    fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as f:
        s = os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_size > limit:
            raise Blocked("FILE_TOO_LARGE")
        raw = f.read(limit + 1)
        if len(raw) > limit:
            raise Blocked("FILE_TOO_LARGE")
        return raw

def read_json(path, private=False):
    raw = private_read(path) if private else bounded_read(path)
    return parse_json(raw)

def parse_json(raw, limit=4*1024*1024):
    """Parse JSON while rejecting ambiguous object keys and non-finite numbers.

    ``ValueError`` remains the signal for malformed JSON so callers can map an
    invalid remote response to their existing fail-closed error.  Security
    relevant ambiguities are raised as ``Blocked`` and must not be retried.
    """
    if not isinstance(raw, (bytes, bytearray, str)):
        raise ValueError("JSON_INPUT_INVALID")
    if len(raw) > limit:
        raise Blocked("JSON_TOO_LARGE")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise Blocked("DUPLICATE_JSON_KEY")
            result[key] = value
        return result
    def invalid_constant(_): raise Blocked("NON_FINITE_JSON_NUMBER")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)

def write_json(path, value, exclusive=False):
    atomic(path, canonical(value)+b"\n", exclusive=exclusive)

def atomic(path, raw, mode=0o600, exclusive=False):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if p.is_symlink():
        raise Blocked("REFUSING_SYMLINK")
    fd, name = tempfile.mkstemp(prefix=".stage-", dir=p.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            os.fchmod(f.fileno(), mode)
            f.write(raw); f.flush(); os.fsync(f.fileno())
        if exclusive:
            os.link(name, p)  # atomic no-replace
            os.unlink(name)
        else:
            os.replace(name, p)
        d = os.open(p.parent, os.O_DIRECTORY)
        try: os.fsync(d)
        finally: os.close(d)
    finally:
        if os.path.exists(name): os.unlink(name)

@contextlib.contextmanager
def lock(path):
    p = pathlib.Path(path); p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(p, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid != os.geteuid() or st.st_mode & 0o077:
            raise Blocked("UNSAFE_LOCK_FILE")
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise Blocked("ANOTHER_OPERATION_IS_RUNNING") from None
        yield
    finally: os.close(fd)

def run(argv, *, data=None, timeout=120, env=None, stdout=None, cwd=None, max_output=16*1024*1024):
    """Run one owned process with bounded captured output and stable errors.

    Never run shell=True; raw command output may contain secrets, so hide errors.
    Reader threads continuously drain both pipes, preventing a child that emits
    concurrently on stdout and stderr from deadlocking while output is bounded.
    """
    if type(max_output) is not int or max_output < 1:
        raise Blocked("COMMAND_OUTPUT_LIMIT_INVALID")
    capture_stdout = stdout is None
    stdout_chunks = []
    stderr_chunks = []
    overflow = threading.Event()
    readers = []

    def drain(stream, chunks):
        total = 0
        try:
            while True:
                chunk = stream.read(65536)
                if not chunk:
                    return
                if total <= max_output:
                    remaining = max_output + 1 - total
                    chunks.append(chunk[:remaining])
                total += len(chunk)
                if total > max_output:
                    overflow.set()
        finally:
            stream.close()

    def stop_owned(child):
        try: os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            child.wait()

    try:
        child = subprocess.Popen(argv, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                 stdout=stdout if stdout is not None else subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 env=env, cwd=cwd, start_new_session=True)
    except OSError:
        raise Blocked("COMMAND_UNAVAILABLE:"+pathlib.Path(argv[0]).name) from None

    if capture_stdout:
        readers.append(threading.Thread(target=drain, args=(child.stdout, stdout_chunks), daemon=True))
    readers.append(threading.Thread(target=drain, args=(child.stderr, stderr_chunks), daemon=True))
    for reader in readers: reader.start()

    def feed_stdin():
        try:
            child.stdin.write(data)
            child.stdin.close()
        except (BrokenPipeError, OSError):
            try: child.stdin.close()
            except OSError: pass

    feeder = None
    if data is not None:
        feeder = threading.Thread(target=feed_stdin, daemon=True)
        feeder.start()

    try:
        deadline = time.monotonic() + timeout
        while child.poll() is None:
            if overflow.is_set():
                stop_owned(child)
                raise Blocked("COMMAND_OUTPUT_TOO_LARGE")
            if time.monotonic() >= deadline:
                stop_owned(child)
                raise Blocked("COMMAND_TIMEOUT:"+pathlib.Path(argv[0]).name)
            time.sleep(0.01)
    except Blocked:
        if child.poll() is None: stop_owned(child)
        for reader in readers: reader.join(timeout=5)
        if feeder is not None: feeder.join(timeout=5)
        raise
    except BaseException:
        if child.poll() is None: stop_owned(child)
        for reader in readers: reader.join(timeout=5)
        if feeder is not None: feeder.join(timeout=5)
        raise

    for reader in readers: reader.join(timeout=5)
    if feeder is not None: feeder.join(timeout=5)
    if overflow.is_set():
        raise Blocked("COMMAND_OUTPUT_TOO_LARGE")
    if child.returncode:
        raise Blocked("COMMAND_FAILED:"+pathlib.Path(argv[0]).name)
    return b"".join(stdout_chunks) if capture_stdout else b""

def host_preflight():
    if os.geteuid() != 0:
        raise Blocked("ROOT_REQUIRED")
    values = dict(line.split("=",1) for line in pathlib.Path("/etc/os-release").read_text().splitlines() if "=" in line)
    if values.get("ID", "").strip('"') != "ubuntu" or values.get("VERSION_ID", "").strip('"') != "24.04" or not pathlib.Path("/run/systemd/system").exists():
        raise Blocked("DEDICATED_UBUNTU_24_04_SYSTEMD_HOST_REQUIRED")

def name(value):
    if not isinstance(value,str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", value):
        raise Blocked("INVALID_NAME")
    return value

def sha(value):
    if not isinstance(value,str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise Blocked("INVALID_SHA256")
    return value
