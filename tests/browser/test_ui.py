#!/usr/bin/env python3
"""Real Chromium DOM tests with an IN-MEMORY fetch fixture, NOT a live cluster.
No browser network requests or server are used. Requires playwright and Chromium.
"""
import json, pathlib, re
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[2]
assets=ROOT/'internal/dashboard/assets';out=ROOT/'evidence';out.mkdir(exist_ok=True)
fixture=r'''
window.fixtureRequests=[];
window.fixtureState={name:'UI-Testcluster — synthetische Daten',nodes:{aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa:{id:'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',name:'worker-1',address:'10.10.0.11',healthy:true,lastSeen:new Date().toISOString(),cpuMilli:1750,memoryMiB:3584,drain:false,revoked:false}},workloads:{},allocations:{},events:[]};
// about:blank has no secure-origin randomUUID. This fixture only supplies test IDs;
// the shipped application uses the browser's native cryptographic implementation.
let fixtureSeq=0;if(!crypto.randomUUID)Object.defineProperty(crypto,'randomUUID',{value:()=>`00000000-0000-4000-8000-${String(++fixtureSeq).padStart(12,'0')}`});
window.fetch=async(path,options={})=>{
 const data=options.body?JSON.parse(options.body):null;
 if(path==='/session')return new Response(JSON.stringify({token:'browser-test-token'}),{status:data.code==='ui-test-code'?200:403});
 if(path==='/api/state')return new Response(JSON.stringify(window.fixtureState),{status:200});
 window.fixtureRequests.push({path,payload:data,hasIdempotencyKey:!!options.headers['Idempotency-Key']});
 if(path==='/api/workloads')window.fixtureState.workloads[data.name]={uid:'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',name:data.name,generation:1,spec:data.spec,phase:'pending',history:[],deleting:false};
 return new Response(JSON.stringify({accepted:true}),{status:202});
};
'''
checks=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 html=(assets/'index.html').read_text();html=re.sub(r'<link[^>]*>', '', html);html=re.sub(r'<script[^>]*>.*?</script>', '',html)
 page.set_content(html);page.add_style_tag(content=(assets/'style.css').read_text());page.add_script_tag(content=fixture);page.add_script_tag(content=(assets/'app.js').read_text())
 assert page.locator('#login').is_visible();assert not page.locator('#workspace').is_visible();checks.append('login-required-screen')
 page.fill('#login-code','wrong');page.click('#login-form button');page.wait_for_selector('#login-error:not([hidden])');checks.append('invalid-login-feedback')
 page.fill('#login-code','ui-test-code');page.click('#login-form button');page.wait_for_selector('#workspace:not([hidden])')
 page.wait_for_function("document.querySelector('#metric-nodes').textContent==='1 / 1'");checks.append('node-state-rendered')
 assert page.locator('#empty-apps').is_visible();checks.append('empty-state')
 page.click('#show-create');page.fill('[name=name]','shop');page.fill('[name=image]','sha256:'+'c'*64);page.click('#create-form button[type=submit]')
 page.wait_for_function("document.querySelector('#workload-rows').textContent.includes('shop')");checks.append('workload-form-post-and-render')
 request=page.evaluate('window.fixtureRequests.at(-1)');assert request['hasIdempotencyKey'] and request['payload']['expectedGeneration']==0;checks.append('version-and-idempotency-fields')
 assert page.get_by_role('button',name='Rollback',exact=True).is_disabled();checks.append('rollback-disabled-without-history')
 page.evaluate("window.fixtureState.workloads.shop.spec.secrets=[{name:'db',version:2}];window.fixtureState.workloads.shop.spec.command=['/app'];window.fixtureState.workloads.shop.spec.node='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa';window.fixtureState.workloads.shop.spec.replacementPolicy='duplicate-safe';window.fixtureState.workloads.shop.generation=3")
 page.click('#refresh');page.wait_for_function("document.querySelector('#workload-rows').textContent.includes('db@2')")
 page.click('#show-create');page.fill('[name=name]','shop');page.click('#create-form button[type=submit]')
 page.wait_for_function("window.fixtureRequests.filter(r=>r.path==='/api/workloads').length===2")
 edited=page.evaluate('window.fixtureRequests.at(-1).payload')
 assert edited['expectedGeneration']==3 and edited['spec']['secrets']==[{'name':'db','version':2}] and edited['spec']['command']==['/app'] and edited['spec']['node']=='a'*32 and edited['spec']['replacementPolicy']=='duplicate-safe'
 checks.append('editing-preserves-hidden-security-and-placement-fields')
 page.on('dialog', lambda d:d.accept())
 page.get_by_role('button',name='Pausieren',exact=True).click();page.wait_for_function("window.fixtureRequests.at(-1).path.endsWith('/pause')")
 checks.append('pause-uses-typed-mutation-route')
 page.screenshot(path=str(out/'dashboard-desktop-fixture.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'dashboard-mobile-fixture.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth');checks.append('mobile-no-horizontal-page-overflow')
 assert not errors;checks.append('no-javascript-runtime-errors')
 browser.close()
(out/'browser-test.json').write_text(json.dumps({'status':'passed','checks':checks,'mode':'real Chromium, in-memory DOM and fetch fixture, no browser network','api':'synthetic UI-test data, not a live cluster','browserTransportQualification':'not tested here; local HTTP navigation blocked by environment policy','screenshotsContain':'synthetic UI-test data'},indent=2)+'\n')
print(json.dumps({'status':'passed','checks':len(checks)}))
