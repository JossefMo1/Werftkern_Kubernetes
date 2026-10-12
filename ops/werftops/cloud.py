"""Hetzner VM provisioning with durable intent and ambiguous-create recovery.

No provider calls run during import or planning. The live CLI never accepts an
arbitrary API URL, redirects, embedded tokens, free-form cloud-init, or deletes.
"""
from __future__ import annotations
import http.client, ipaddress, json, pathlib, time, urllib.error, urllib.parse, urllib.request
from .common import Blocked, canonical, fingerprint, lock, name, private_read, read_json, write_json

class Ambiguous(Blocked): pass
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl): return None

class Hetzner:
    def __init__(self, token_file):
        token=private_read(token_file,4096).decode().strip()
        if len(token)<32 or any(c.isspace() for c in token): raise Blocked("CLOUD_TOKEN_INVALID")
        self.token=token
        self.opener=urllib.request.build_opener(NoRedirect())
    @property
    def credential_fingerprint(self):
        return __import__('hashlib').sha256(b'werftkern:hetzner-cloud:v1:'+self.token.encode()).hexdigest()
    def call(self, method, path, payload=None):
        if not path.startswith("/") or ".." in path or "\n" in path: raise Blocked("API_PATH_INVALID")
        request=urllib.request.Request("https://api.hetzner.cloud/v1"+path,
            data=canonical(payload) if payload is not None else None,
            headers={"Authorization":"Bearer "+self.token,"Content-Type":"application/json","User-Agent":"werftkern/0.2.0"},method=method)
        try:
            with self.opener.open(request,timeout=30) as resp:
                raw=resp.read(4*1024*1024+1)
                if len(raw)>4*1024*1024: raise Blocked("PROVIDER_RESPONSE_TOO_LARGE")
                result=json.loads(raw)
                if not isinstance(result,dict): raise Ambiguous("PROVIDER_RESPONSE_INVALID")
                # An absent/malformed inventory is not proof that a paid resource
                # does not exist. Validate before callers consider a create.
                resource=urllib.parse.urlsplit(path).path
                if method=='GET' and resource in ('/servers','/server_types'):
                    items=result.get(resource[1:])
                    if not isinstance(items,list) or any(not isinstance(item,dict) for item in items):
                        raise Ambiguous("PROVIDER_RESPONSE_INVALID")
                return result
        except urllib.error.HTTPError as e:
            # Do not repeat mutations automatically, even after 429 or 5xx.
            raise Ambiguous("PROVIDER_HTTP_"+str(e.code)) from None
        except (OSError, ValueError, http.client.HTTPException):
            raise Ambiguous("PROVIDER_RESPONSE_UNKNOWN") from None

def validate(plan):
    required={"format","name","location","networkId","firewallId","sshKeyId","servers"}
    if set(plan)!=required or plan.get("format")!="werftkern-hetzner/v1": raise Blocked("CLOUD_PLAN_SCHEMA_INVALID")
    name(plan["name"]);name(plan["location"])
    if any(type(plan[k]) is not int or plan[k]<1 for k in ("networkId","firewallId","sshKeyId")): raise Blocked("EXISTING_NETWORK_FIREWALL_AND_SSH_KEY_REQUIRED")
    servers=plan["servers"]
    if not 1<=len(servers)<=20: raise Blocked("SERVER_COUNT_LIMIT")
    seen=set()
    for s in servers:
        if set(s)!={"name","serverType","imageId"} or type(s["imageId"]) is not int or s["imageId"]<1: raise Blocked("PIN_NUMERIC_IMAGE_ID_AND_SERVER_TYPE")
        name(s["name"]);name(s["serverType"])
        if s["name"] in seen: raise Blocked("SERVER_NAME_DUPLICATE")
        seen.add(s["name"])
    return fingerprint(plan)

def expected_labels(plan, digest):
    return {"werftkern-cluster":plan["name"],"werftkern-plan":digest[:32]}

def check_server(server, spec, plan, digest):
    if server.get("name")!=spec["name"] or server.get("labels",{})!=expected_labels(plan,digest): raise Blocked("SERVER_OWNERSHIP_CONFLICT")
    if server.get("server_type",{}).get("name")!=spec["serverType"] or server.get("image",{}).get("id")!=spec["imageId"] or server.get("datacenter",{}).get("location",{}).get("name")!=plan["location"]:
        raise Blocked("SERVER_CONFIGURATION_CONFLICT")
    addresses=[n.get("ip") for n in server.get("private_net",[]) if n.get("network")==plan["networkId"]]
    if len(addresses)!=1 or not ipaddress.ip_address(addresses[0]).is_private: raise Blocked("SERVER_PRIVATE_NETWORK_NOT_READY")
    return addresses[0]

def apply(plan, journal_path, confirm, accept_costs, api):
    digest=validate(plan)
    if confirm!=digest or not accept_costs: raise Blocked("PLAN_HASH_AND_COST_ACCEPTANCE_REQUIRED")
    with lock(str(journal_path)+".lock"):
        p=pathlib.Path(journal_path)
        state=read_json(p,private=True) if p.exists() else {"format":"werftkern-cloud-journal/v1","plan":digest,"servers":{}}
        if state.get("plan")!=digest: raise Blocked("CLOUD_JOURNAL_PLAN_CONFLICT")
        # Validation reads BEFORE any paid action.
        net=api.call("GET",f"/networks/{plan['networkId']}").get("network",{})
        if not net.get("subnets"): raise Blocked("CLOUD_NETWORK_HAS_NO_SUBNET")
        api.call("GET",f"/firewalls/{plan['firewallId']}");api.call("GET",f"/ssh_keys/{plan['sshKeyId']}")
        for spec in plan["servers"]:
            entry=state["servers"].get(spec["name"])
            matches=api.call("GET","/servers?"+urllib.parse.urlencode({"name":spec["name"],"per_page":50})).get("servers",[])
            if len(matches)>1: raise Blocked("SERVER_NAME_AMBIGUOUS")
            if matches:
                server=matches[0]
                if entry is None: raise Blocked("PREEXISTING_SERVER_NOT_CREATED_BY_THIS_JOURNAL")
                if entry.get("id") and entry["id"]!=server.get("id"):raise Blocked("SERVER_ID_CHANGED")
            else:
                if entry is not None:
                    # POST may have succeeded but not appeared in a later list yet.
                    # NEVER create again just because the read returned empty.
                    raise Ambiguous("CREATE_INTENT_EXISTS_WAIT_OR_REVIEW_PROVIDER_NO_BLIND_RETRY")
                state["servers"][spec["name"]]={"stage":"create-intent"}
                write_json(p,state)
                payload={"name":spec["name"],"server_type":spec["serverType"],"image":spec["imageId"],"location":plan["location"],"networks":[plan["networkId"]],"firewalls":[{"firewall":plan["firewallId"]}],"ssh_keys":[plan["sshKeyId"]],"labels":expected_labels(plan,digest),"public_net":{"enable_ipv4":True,"enable_ipv6":False},"start_after_create":True}
                try: result=api.call("POST","/servers",payload)
                except Exception:
                    state["servers"][spec["name"]]["stage"]="create-ambiguous";write_json(p,state);raise
                server=result.get("server",{})
                if type(server.get("id")) is not int:raise Ambiguous("CREATE_RESPONSE_ID_MISSING")
                state["servers"][spec["name"]]={"stage":"created-pending","id":server["id"]}
                write_json(p,state)
                # Actions are asynchronous. Read verified state rather than assuming create means ready.
                server=api.call("GET",f"/servers/{server['id']}").get("server",{})
            ip=check_server(server,spec,plan,digest)
            if server.get("status")!="running": raise Blocked("SERVER_NOT_RUNNING_REAPPLY_TO_OBSERVE")
            state["servers"][spec["name"]]={"id":server["id"],"stage":"provisioned-not-runtime-qualified","privateAddress":ip}
            write_json(p,state)
        return state
