'use strict';
(() => {
  let token = '', state = null, busy = false, connected = false, connectionError = false;
  const $ = id => document.getElementById(id);
  const text = (tag, value, cls) => { const e = document.createElement(tag); e.textContent = value; if (cls) e.className = cls; return e; };
  const error = message => { $('error').textContent = message; $('error').hidden = false; };
  async function api(path, body) {
    const headers = {Authorization: `Bearer ${token}`};
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; headers['Idempotency-Key'] = crypto.randomUUID().replaceAll('-', ''); }
    const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit'});
    if (!response.ok) { const raw = await response.text(); let message = raw; try { message = JSON.parse(raw).code || raw; } catch {} throw new Error(message); }
    return response.json();
  }
  function healthy(n) { return !!n && !n.revoked && n.healthy && Date.now() - Date.parse(n.lastSeen) < 30000; }
  async function refresh() {
    if (!token || busy) return;
    try { state = await api('/api/state'); render(); connected = true; $('create-form').querySelector('button[type=submit]').disabled = false; $('connection').textContent = 'Verbunden · Live-Zustand'; if (connectionError) { $('error').hidden = true; connectionError = false; } $('show-create').disabled = false; }
    catch (e) { connected = false; connectionError = true; $('create-form').querySelector('button[type=submit]').disabled = true; $('connection').textContent = 'Verbindung unterbrochen'; $('show-create').disabled = true; document.querySelectorAll('.actions button,.node button').forEach(b => b.disabled = true); error(`Status konnte nicht aktualisiert werden. Angezeigte Daten können veraltet sein. ${e.message}`); }
  }
  function render() {
    const nodes = Object.values(state.nodes), apps = Object.values(state.workloads).sort((a,b)=>a.name.localeCompare(b.name)), allocations = Object.values(state.allocations);
    $('cluster-name').textContent = state.name;
    $('metric-nodes').textContent = `${nodes.filter(healthy).length} / ${nodes.length}`;
    $('metric-apps').textContent = apps.length;
    $('metric-ready').textContent = allocations.filter(a => a.desired === 'run' && a.phase === 'ready' && healthy(state.nodes[a.nodeId])).length;
    $('metric-memory').textContent = `${allocations.filter(a=>a.phase!=='stopped').reduce((sum,a)=>sum+a.spec.memoryMiB,0)} MiB`;
    $('empty-apps').hidden = apps.length !== 0;
    $('workload-rows').replaceChildren();
    apps.forEach(w => {
      const row = document.createElement('tr'), name = document.createElement('td'), status = document.createElement('td'), actions = document.createElement('td');
      name.append(text('strong',w.name),text('small',w.spec.image));
      if ((w.spec.secrets||[]).length) name.append(text('small',`Secrets: ${w.spec.secrets.map(s=>`${s.name}@${s.version}`).join(', ')}`));
      const badge = text('span',w.phase,'status'); if (['ready','blocked','degraded','updating','pending'].includes(w.phase)) badge.classList.add(w.phase); status.append(badge);
      if(w.reason) status.append(text('small',w.reason));
      const ready = allocations.filter(a=>a.workloadUid===w.uid && a.desired==='run' && a.phase==='ready' && healthy(state.nodes[a.nodeId])).length;
      actions.className='actions';
      for (const [label, action] of [[w.paused?'Fortsetzen':'Pausieren',w.paused?'resume':'pause'],['Rollback','rollback'],['Löschen','delete']]) {
        const b=text('button',label,'secondary'); b.disabled=w.deleting||(action==='rollback'&&!(w.history||[]).length);
        b.addEventListener('click',async()=>{if(!confirm(`${label}: ${w.name}?`))return;busy=true;b.disabled=true;try{await api(`/api/workloads/${w.name}/${action}`,{expectedGeneration:w.generation});}catch(e){error(e.message)}finally{busy=false;await refresh()}});actions.append(b);
      }
      row.append(name,status,text('td',`${ready} / ${w.spec.replicas}`),text('td',`r${w.generation}`),actions);$('workload-rows').append(row);
    });
    $('node-grid').replaceChildren();
    nodes.sort((a,b)=>a.name.localeCompare(b.name)).forEach(n=>{
      const card=text('article','','node'), badge=text('span',n.revoked?'Gesperrt':n.drain?'Drain':healthy(n)?'Bereit':'Unbekannt',`status ${healthy(n)?'ready':'blocked'}`);
      card.append(text('h3',n.name),badge,text('p',`${n.address} · ${n.cpuMilli} mCPU · ${n.memoryMiB} MiB planbare Kapazität`),text('code',n.id));
      const b=text('button',n.drain?'Drain aufheben':'Sicher drainen','secondary');b.addEventListener('click',async()=>{if(!confirm(`Node ${n.name}: ${n.drain?'Drain aufheben':'Drain starten'}?`))return;try{await api(`/api/nodes/${n.id}`,{drain:!n.drain});await refresh()}catch(e){error(e.message)}});card.append(text('p','Kapazität abzüglich Hostreserve.'),b);$('node-grid').append(card);
    });
    $('events').replaceChildren();(state.events||[]).slice(-12).reverse().forEach(e=>{const r=text('div','','event');r.append(text('time',new Date(e.at).toLocaleString('de-DE')),text('span',e.action),text('code',e.target));$('events').append(r)});
    $('updated').textContent=`Aktualisiert: ${new Date().toLocaleTimeString('de-DE')}`;
  }
  $('login-form').addEventListener('submit',async e=>{e.preventDefault();try{const r=await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:$('login-code').value}),credentials:'omit',cache:'no-store'});if(!r.ok)throw new Error('Anmeldecode ungültig oder zu viele Versuche.');token=(await r.json()).token;$('login-code').value='';$('login').hidden=true;$('login-error').hidden=true;$('workspace').hidden=false;$('refresh').disabled=false;await refresh()}catch(e){$('login-error').textContent=e.message;$('login-error').hidden=false}});
  $('refresh').addEventListener('click',refresh);
  $('show-create').addEventListener('click',()=>{$('create-panel').hidden=false;$('create-panel').scrollIntoView({behavior:'smooth',block:'start'})});
  $('close-create').addEventListener('click',()=>{$('create-panel').hidden=true});
  $('create-form').addEventListener('submit',async e=>{e.preventDefault();if(!state || !connected)return;const data=new FormData(e.target);const name=String(data.get('name'));const existing=state.workloads[name];const req={apiVersion:'werftkern/v1alpha1',name,expectedGeneration:existing?existing.generation:0,spec:{...(existing?.spec||{}),image:String(data.get('image')),replicas:Number(data.get('replicas')),cpuMilli:Number(data.get('cpuMilli')),memoryMiB:Number(data.get('memoryMiB')),port:Number(data.get('port')),readinessPath:String(data.get('readinessPath'))}};
    busy=true;const button=e.target.querySelector('button[type=submit]');button.disabled=true;try{await api('/api/workloads',req);$('create-panel').hidden=true}catch(e){error(e.message)}finally{busy=false;button.disabled=false;await refresh()}});
  setInterval(refresh,3000);
})();
