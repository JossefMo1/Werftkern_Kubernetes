#!/usr/bin/env python3
"""Create a deterministic Docker-load archive, without requiring a Docker daemon.
The same content-addressed local image is loaded on every node by the agent.
"""
from __future__ import annotations
import hashlib, io, json, pathlib, subprocess, tarfile
ROOT = pathlib.Path(__file__).resolve().parent.parent
out = ROOT / 'build'; out.mkdir(exist_ok=True)
raw = (out / 'demo-server').read_bytes()
def tar_bytes(files: dict[str, tuple[bytes,int]]) -> bytes:
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode='w',format=tarfile.USTAR_FORMAT) as tar:
        for name,(data,mode) in sorted(files.items()):
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=mode;info.mtime=0;info.uid=0;info.gid=0;tar.addfile(info,io.BytesIO(data))
    return stream.getvalue()
layer=tar_bytes({'server':(raw,0o555),'licenses/GO-LICENSE':((ROOT/'third_party/go.LICENSE').read_bytes(),0o444)})
config={'architecture':'amd64','os':'linux','created':'2026-09-24T00:00:00Z','config':{'User':'65532:65532','Entrypoint':['/server'],'ExposedPorts':{'8080/tcp':{}}},'rootfs':{'type':'layers','diff_ids':['sha256:'+hashlib.sha256(layer).hexdigest()]},'history':[{'created':'2026-09-24T00:00:00Z','created_by':'Werftkern demo image builder'}]}
config_bytes=json.dumps(config,sort_keys=True,separators=(',',':')).encode();digest=hashlib.sha256(config_bytes).hexdigest()
manifest=[{'Config':digest+'.json','RepoTags':['werftkern-demo:0.2.0-dev.3'],'Layers':['layer.tar']}]
archive=tar_bytes({digest+'.json':(config_bytes,0o644),'manifest.json':(json.dumps(manifest,separators=(',',':')).encode(),0o644),'layer.tar':(layer,0o644)})
(out/'demo-image.tar').write_bytes(archive)
metadata={'image':'sha256:'+digest,'archiveSha256':hashlib.sha256(archive).hexdigest(),'compiler':subprocess.check_output(['go','version'],text=True).strip()}
(out/'demo.json').write_text(json.dumps(metadata,indent=2)+'\n')
example={'apiVersion':'werftkern/v1alpha1','name':'demo','expectedGeneration':0,'spec':{'image':metadata['image'],'replicas':2,'cpuMilli':100,'memoryMiB':32,'port':8080,'readinessPath':'/healthz'}}
(out/'demo.workload.json').write_text(json.dumps(example,indent=2)+'\n')
print(metadata['image'])
