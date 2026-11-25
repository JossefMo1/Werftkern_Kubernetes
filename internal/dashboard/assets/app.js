'use strict';
(() => {
  let token = '', state = null, busy = false, connected = false, connectionError = false;
  const $ = id => document.getElementById(id);
  const announce = message => {
    const node = $('operation-status');
    if (!node) return;
    node.textContent = '';
    if (message) window.setTimeout(() => { node.textContent = message; }, 0);
  };
  const scrollBehavior = () => window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
  const text = (tag, value, cls) => { const e = document.createElement(tag); e.textContent = value; if (cls) e.className = cls; return e; };
  const errorText = Object.freeze({
    STATE_UNAVAILABLE: 'Der Zustandsdienst ist nicht erreichbar. Prüfe den lokalen Controllerdienst und die etcd-Verbindung.',
    CONTROL_PLANE_UNREACHABLE: 'Der Controller ist nicht erreichbar. Prüfe den lokalen Dienst und die etcd-Verbindung.',
    LOGIN_REQUIRED: 'Die Dashboard-Anmeldung ist abgelaufen. Lade die Seite neu und melde dich erneut an.',
    ADMIN_IDENTITY_REQUIRED: 'Der Controller hat die Admin-Anmeldung abgelehnt. Starte eine neue Dashboard-Sitzung.',
    VERSION_CONFLICT: 'Der Zustand hat sich geändert. Aktualisiere die Ansicht und wiederhole die Aktion.',
    IDEMPOTENCY_CONFLICT: 'Die Anfrage-ID wurde bereits mit anderen Daten verwendet. Prüfe den Vorgang, statt ihn zu wiederholen.',
    NOT_FOUND: 'Das angeforderte Objekt existiert nicht mehr. Aktualisiere die Ansicht.',
    ACTION_INVALID: 'Die angeforderte Aktion ist für dieses Objekt nicht zulässig.',
    MAINTENANCE_BLOCKS_NEW_MUTATIONS: 'Der Controller führt gerade Wartung aus. Wiederhole die Änderung nach Abschluss.',
    NODE_NOT_AUTHORIZED: 'Der Node ist nicht mehr autorisiert. Prüfe Zertifikat und Node-Status.',
    JSON_REQUIRED: 'Die Anfrage war kein gültiges JSON.',
    INVALID_OR_OVERSIZED_JSON: 'Die Anfrage ist ungültig oder zu groß.'
  });
  const describeError = code => {
    const normalized = String(code || 'UNKNOWN_ERROR').trim().slice(0, 80);
    return (errorText[normalized] || 'Der Controller hat die Aktion abgelehnt.') + ` (Fehlercode: ${normalized})`;
  };
  const error = (message, code) => {
    const node = $('error'), normalized = String(code || 'UNKNOWN_ERROR').trim().slice(0, 80);
    node.dataset.errorCode = normalized;
    node.textContent = message;
    node.hidden = false;
  };
  const clearError = () => {
    const node = $('error');
    node.hidden = true;
    delete node.dataset.errorCode;
  };
  async function api(path, body) {
    const headers = {Authorization: `Bearer ${token}`};
    if (body !== undefined) { headers['Content-Type'] = 'application/json'; headers['Idempotency-Key'] = crypto.randomUUID().replaceAll('-', ''); }
    const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store', credentials: 'omit'});
    if (!response.ok) {
      const raw = await response.text();
      let code = `HTTP_${response.status}`;
      try {
        const problem = JSON.parse(raw);
        if (problem && typeof problem.code === 'string' && problem.code.trim()) code = problem.code;
        else if (problem && typeof problem.title === 'string' && problem.title.trim()) code = problem.title;
      } catch {}
      throw new Error(code.trim().slice(0, 80));
    }
    return response.json();
  }
  function healthy(n) { const age = n ? Date.now() - Date.parse(n.lastSeen) : Infinity; return !!n && !n.revoked && n.healthy && Number.isFinite(age) && age >= -5000 && age < 30000; }
  async function refresh() {
    if (!token || busy) return;
    const wasConnected = connected;
    $('workspace').setAttribute('aria-busy', 'true');
    try {
      state = await api('/api/state'); render(); connected = true; $('create-form').querySelector('button[type=submit]').disabled = false; $('connection').textContent = 'Verbunden · Live-Zustand'; if (connectionError) { clearError(); connectionError = false; } $('show-create').disabled = false;
      if (!wasConnected) announce('Dashboard verbunden. Der aktuelle Zustand ist geladen.');
    } catch (e) {
      connected = false; connectionError = true; $('create-form').querySelector('button[type=submit]').disabled = true; $('connection').textContent = 'Verbindung unterbrochen'; $('show-create').disabled = true; document.querySelectorAll('.actions button,.node button').forEach(b => b.disabled = true); error(`Status konnte nicht aktualisiert werden. Angezeigte Daten können veraltet sein. ${describeError(e.message)}`, e.message);
      if (wasConnected) announce('Verbindung zum Controller unterbrochen.');
    } finally { $('workspace').setAttribute('aria-busy', 'false'); }
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
        const b=text('button',label,'secondary'); b.disabled=w.deleting||(action==='rollback'&&!(w.history||[]).length); b.setAttribute('aria-label', `${label} ${w.name}`);
        b.addEventListener('click',async()=>{if(!confirm(`${label}: ${w.name}?`))return;busy=true;b.disabled=true;b.setAttribute('aria-busy','true');announce(`${label} für ${w.name} wird ausgeführt.`);try{await api(`/api/workloads/${w.name}/${action}`,{expectedGeneration:w.generation});announce(`${label} für ${w.name} wurde angenommen.`);}catch(e){error(describeError(e.message),e.message)}finally{busy=false;await refresh()}});actions.append(b);
      }
      row.append(name,status,text('td',`${ready} / ${w.spec.replicas}`),text('td',`r${w.generation}`),actions);$('workload-rows').append(row);
    });
    $('node-grid').replaceChildren();
    nodes.sort((a,b)=>a.name.localeCompare(b.name)).forEach(n=>{
      const card=text('article','','node'), badge=text('span',n.revoked?'Gesperrt':n.drain?'Drain':healthy(n)?'Bereit':'Unbekannt',`status ${healthy(n)?'ready':'blocked'}`);
      card.append(text('h3',n.name),badge,text('p',`${n.address} · ${n.cpuMilli} mCPU · ${n.memoryMiB} MiB planbare Kapazität`),text('code',n.id));
      const b=text('button',n.drain?'Drain aufheben':'Sicher drainen','secondary');b.setAttribute('aria-label', `${n.drain?'Drain aufheben':'Sicher drainen'} ${n.name}`);b.addEventListener('click',async()=>{if(!confirm(`Node ${n.name}: ${n.drain?'Drain aufheben':'Drain starten'}?`))return;try{await api(`/api/nodes/${n.id}`,{drain:!n.drain});clearError();announce(`Node ${n.name} wird aktualisiert.`);await refresh()}catch(e){error(describeError(e.message),e.message)}});card.append(text('p','Kapazität abzüglich Hostreserve.'),b);$('node-grid').append(card);
    });
    $('events').replaceChildren();(state.events||[]).slice(-12).reverse().forEach(e=>{const r=text('div','','event');r.append(text('time',new Date(e.at).toLocaleString('de-DE')),text('span',e.action),text('code',e.target));$('events').append(r)});
    $('updated').textContent=`Aktualisiert: ${new Date().toLocaleTimeString('de-DE')}`;
  }
  $('login-form').addEventListener('submit',async e=>{e.preventDefault();try{const r=await fetch('/session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:$('login-code').value}),credentials:'omit',cache:'no-store'});if(!r.ok)throw new Error('Anmeldecode ungültig oder zu viele Versuche.');token=(await r.json()).token;$('login-code').value='';$('login').hidden=true;$('login-error').hidden=true;$('workspace').hidden=false;$('refresh').disabled=false;await refresh()}catch(e){$('login-error').textContent=e.message;$('login-error').hidden=false}});
  $('refresh').addEventListener('click',refresh);
  $('show-create').addEventListener('click',()=>{$('create-panel').hidden=false;$('create-panel').scrollIntoView({behavior:scrollBehavior(),block:'start'});$('create-form').querySelector('input').focus();announce('Formular zum Ausrollen einer Anwendung geöffnet.')});
  $('close-create').addEventListener('click',()=>{$('create-panel').hidden=true;$('show-create').focus();announce('Formular geschlossen.')});
  $('create-form').addEventListener('submit',async e=>{e.preventDefault();if(!state || !connected)return;const data=new FormData(e.target);const name=String(data.get('name'));const existing=state.workloads[name];const req={apiVersion:'werftkern/v1alpha1',name,expectedGeneration:existing?existing.generation:0,spec:{...(existing?.spec||{}),image:String(data.get('image')),replicas:Number(data.get('replicas')),cpuMilli:Number(data.get('cpuMilli')),memoryMiB:Number(data.get('memoryMiB')),port:Number(data.get('port')),readinessPath:String(data.get('readinessPath'))}};
    busy=true;const button=e.target.querySelector('button[type=submit]');button.disabled=true;announce(`Anwendung ${name} wird ausgerollt.`);try{await api('/api/workloads',req);clearError();$('create-panel').hidden=true;$('show-create').focus();announce(`Anwendung ${name} wurde zur Bereitstellung eingereicht.`)}catch(e){error(describeError(e.message),e.message);announce(`Ausrollen von ${name} fehlgeschlagen.`)}finally{busy=false;button.disabled=false;await refresh()}});
  setInterval(refresh,3000);
})();
