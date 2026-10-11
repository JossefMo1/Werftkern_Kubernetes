"""Small fail-closed building blocks. Host paths are trusted administrator inputs."""
from __future__ import annotations
import contextlib, fcntl, hashlib, json, os, pathlib, re, stat, subprocess, tempfile, signal

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

def read_json(path, private=False):
    raw = private_read(path) if private else pathlib.Path(path).read_bytes()
    if len(raw) > 4*1024*1024:
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

def run(argv, *, data=None, timeout=120, env=None, stdout=None, cwd=None):
    """Never run shell=True; raw command output may contain secrets, so hide errors."""
    try:
        child = subprocess.Popen(argv, stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                 stdout=stdout or subprocess.PIPE, stderr=subprocess.PIPE,
                                 env=env, cwd=cwd, start_new_session=True)
    except OSError:
        raise Blocked("COMMAND_UNAVAILABLE:"+pathlib.Path(argv[0]).name) from None
    try:
        output, _ = child.communicate(input=data, timeout=timeout)
    except subprocess.TimeoutExpired:
        # The process group is created for this invocation, never an operator PID.
        # Do not leave pgBackRest helpers writing after a timed-out invocation.
        try: os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: child.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try: os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            child.communicate()
        raise Blocked("COMMAND_TIMEOUT:"+pathlib.Path(argv[0]).name) from None
    except BaseException:
        try: os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        child.communicate()
        raise
    if child.returncode:
        raise Blocked("COMMAND_FAILED:"+pathlib.Path(argv[0]).name)
    return output or b""

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
