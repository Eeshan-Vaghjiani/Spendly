// Run with: node --test backend/tests/admin_sign_in_ui.test.cjs
// Delayed-response regressions for the real admin script; no browser/network I/O.
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {readFileSync} = require('node:fs');
const {join} = require('node:path');
const vm = require('node:vm');

function harness() {
  const elements = new Map(), pending = [];
  const element = id => {
    if (!elements.has(id)) elements.set(id, {
      innerHTML:'', textContent:'', disabled:false, hidden:false, value:'',
      listeners:{},
      addEventListener(name,listener){this.listeners[name]=listener;},
      reset(){}, showModal(){this.closed=false;},
      close(){this.closed=true;this.listeners.close?.();},
      focus(){}, scrollIntoView(){},
    });
    return elements.get(id);
  };
  const context = vm.createContext({
    document:{getElementById:element, querySelector:()=>({content:'synthetic-csrf'})},
    fetch:path=>new Promise((resolve,reject)=>pending.push({path,resolve,reject})),
    Intl, URLSearchParams, setTimeout, location:{assign(){}},
    FormData:class { constructor(form){return Object.entries(form.syntheticBody);} },
  });
  let source = readFileSync(join(__dirname,'../app/static/admin/manage.js'),'utf8');
  source = source.replace(/^Promise\.allSettled\(\[loadUsers\(\),loadSettings\(\),loadAudit\(\)\]\).*$/m,'');
  vm.runInContext(source,context);
  const run = code => vm.runInContext(code,context);
  const select = id => run(`selected={id:${JSON.stringify(id)}}; ++signinsRequest;`);
  const resolve = (request,provider='password') => request.resolve({
    ok:true,status:200,json:async()=>({data:{page:1,per_page:20,total:1,pages:1,
      items:[{created_at:'2026-10-20T12:00:00Z',provider,event:'sign_in'}]}}),
  });
  return {elements,element,pending,run,select,resolve};
}

test('a delayed previous-account response cannot overwrite the current account',async()=>{
  const h=harness(); h.select('first');const first=h.run('loadSignIns()');
  h.select('second');const second=h.run('loadSignIns()');
  h.resolve(h.pending[1],'google');await second;
  const expected=h.element('signins-list').innerHTML;
  assert.match(expected,/Google/);
  h.resolve(h.pending[0],'password');await first;
  assert.equal(h.element('signins-list').innerHTML,expected);
});

test('a stale failure cannot replace the newer account history or disable refresh',async()=>{
  const h=harness();h.select('first');const first=h.run('loadSignIns()');
  h.select('second');const second=h.run('loadSignIns()');h.resolve(h.pending[1],'google');await second;
  const expected=h.element('signins-list').innerHTML;
  h.pending[0].reject(new Error('previous request offline'));await first;
  assert.equal(h.element('signins-list').innerHTML,expected);
  assert.equal(h.element('refresh-signins').disabled,false);
});

test('current failure clears previous rows and allows explicit retry',async()=>{
  const h=harness();h.select('current');h.element('signins-list').innerHTML='previous history';
  const request=h.run('loadSignIns()');
  assert.doesNotMatch(h.element('signins-list').innerHTML,/previous history/);
  h.pending[0].reject(new Error('offline'));
  await assert.rejects(request,/offline/);
  assert.match(h.element('signins-list').innerHTML,/Unable to load sign-ins/);
  assert.equal(h.element('refresh-signins').disabled,false);
  assert.equal(h.element('signins-prev').disabled,true);
  assert.equal(h.element('signins-next').disabled,true);
  const retry=h.run('loadSignIns()');h.resolve(h.pending[1]);await retry;
  assert.match(h.element('signins-list').innerHTML,/Password/);
});

test('closing an account invalidates its pending history response',async()=>{
  const h=harness();h.select('first');const request=h.run('loadSignIns()');
  h.element('close-detail').onclick();
  assert.equal(h.element('detail').hidden,true);
  assert.equal(h.element('signins-list').textContent,'');
  h.resolve(h.pending[0]);await request;
  assert.doesNotMatch(h.element('signins-list').innerHTML,/Password/);
});

test('closing an account returns keyboard focus to its connected Manage button',()=>{
  const h=harness();
  h.run('let focused=false;accountOpener={isConnected:true,focus(){focused=true}}');
  h.element('close-detail').onclick();
  assert.equal(h.run('focused'),true);
  assert.equal(h.run('accountOpener'),null);
});

test('closing after a list refresh returns focus to Search when the old button is detached',()=>{
  const h=harness();let searchFocused=false;
  h.element('search').focus=()=>{searchFocused=true;};
  h.run('accountOpener={isConnected:false,focus(){throw new Error("Detached button")}}');
  h.element('close-detail').onclick();
  assert.equal(searchFocused,true);
  assert.equal(h.run('accountOpener'),null);
});

test('an empty history explains the observation boundary and disables paging',async()=>{
  const h=harness();h.select('legacy');const request=h.run('loadSignIns()');
  h.pending[0].resolve({ok:true,status:200,json:async()=>({data:{items:[],page:1,pages:0,total:0}})});
  await request;
  assert.match(h.element('signins-list').innerHTML,/Older history is unavailable/);
  assert.equal(h.element('signins-prev').disabled,true);
  assert.equal(h.element('signins-next').disabled,true);
});

test('records failure clears actions and paging, then retry recovers',async()=>{
  const h=harness();h.select('current');h.element('record-kind').value='transactions';
  h.element('records-next').disabled=false;
  h.run("recordRows=[{id:'old-row'}]");
  const request=h.run('loadRecords()');
  const whileLoading={next:h.element('records-next').disabled,add:h.element('add-record').disabled,rows:h.run('recordRows.length')};
  h.pending[0].reject(new Error('offline'));await assert.rejects(request,/offline/);
  assert.deepEqual(whileLoading,{next:true,add:true,rows:0});
  assert.match(h.element('record-list').innerHTML,/Unable to load records/);
  assert.equal(h.element('records-next').disabled,true);
  assert.equal(h.element('add-record').disabled,true);
  assert.equal(h.element('refresh-records').disabled,false);
  const retry=h.run('loadRecords()');
  h.pending[1].resolve({ok:true,status:200,json:async()=>({data:{items:[],page:1,pages:0,total:0}})});
  await retry;
  assert.match(h.element('record-list').innerHTML,/No records/);
  assert.equal(h.element('add-record').disabled,false);
});

test('a stale records failure cannot replace a newer category or its controls',async()=>{
  const h=harness();h.select('current');h.element('record-kind').value='transactions';
  const first=h.run('loadRecords()');h.element('record-kind').value='budgets';const second=h.run('loadRecords()');
  h.pending[1].resolve({ok:true,status:200,json:async()=>({data:{items:[],page:1,pages:0,total:0}})});
  await second;
  const expected=h.element('record-list').innerHTML;
  h.pending[0].reject(new Error('old offline request'));
  await first;
  assert.equal(h.element('record-list').innerHTML,expected);
  assert.equal(h.element('add-record').disabled,false);
  assert.equal(h.element('refresh-records').disabled,false);
});

for(const kind of ['users','audit']){
  test(`${kind} failure clears stale rows and page controls`,async()=>{
    const h=harness();h.element(`${kind==='users'?'user':'audit'}-list`).innerHTML='previous private rows';
    h.element(`${kind}-next`).disabled=false;
    const request=h.run(kind==='users'?'loadUsers()':'loadAudit()');
    const loadingDisabled=h.element(`${kind}-next`).disabled;
    h.pending[0].reject(new Error('offline'));await assert.rejects(request,/offline/);
    assert.equal(loadingDisabled,true);
    assert.doesNotMatch(h.element(`${kind==='users'?'user':'audit'}-list`).innerHTML,/previous private rows/);
    assert.match(h.element(`${kind==='users'?'user':'audit'}-list`).innerHTML,/Unable to load/);
    assert.equal(h.element(`${kind}-next`).disabled,true);
  });
}

test('a saved action stays completed when its subsequent view refresh fails',async()=>{
  const h=harness(),form=h.element('action-form');
  form.syntheticBody={reason:'Synthetic test only',admin_password:'test-only-password'};
  form.elements={admin_password:{value:'test-only-password'}};
  h.run("let savedWrites=0;pendingAction=async()=>{savedWrites++;return async()=>{throw new Error('refresh unavailable')}}");
  const submit=form.listeners.submit({preventDefault(){},target:form});
  await new Promise(setImmediate);
  for(const request of h.pending)request.resolve({ok:true,status:200,json:async()=>({data:{items:[],page:1,pages:0,total:0}})});
  await submit;
  assert.equal(h.run('savedWrites'),1);
  assert.equal(h.element('action-dialog').closed,true);
  assert.equal(h.element('action-error').hidden,true);
  assert.match(h.element('notice').textContent,/saved.*refresh/i);
  assert.equal(form.elements.admin_password.value,'');
});

test('record creation completes the write before starting any view refresh',async()=>{
  const h=harness();h.select('synthetic-user');h.element('record-kind').value='budgets';
  h.run('recordAction()');
  const write=h.run("pendingAction({amount:'125.50',category:'total',period_start:'2026-10-19',period_end:'2026-10-25',reason:'Synthetic correction',admin_password:'test-only-password'})");
  assert.equal(h.pending.length,1);
  assert.match(h.pending[0].path,/records\/budgets$/);
  h.pending[0].resolve({ok:true,status:201,json:async()=>({data:{id:'new-budget'}})});
  const refresh=await write;
  assert.equal(typeof refresh,'function');
  assert.equal(h.pending.length,1);
});

test('a rejected action stays open for correction and clears its password',async()=>{
  const h=harness(),form=h.element('action-form');
  form.syntheticBody={reason:'Synthetic test only',admin_password:'test-only-password'};
  form.elements={admin_password:{value:'test-only-password'}};
  h.run("showAction('Synthetic action','Testing',[],async()=>{throw new Error('Confirmation rejected')})");
  await form.listeners.submit({preventDefault(){},target:form});
  assert.equal(h.element('action-dialog').closed,false);
  assert.equal(h.element('action-error').hidden,false);
  assert.match(h.element('action-error').textContent,/Confirmation rejected/);
  assert.equal(form.elements.admin_password.value,'');
  assert.equal(h.element('action-submit').disabled,false);
});
