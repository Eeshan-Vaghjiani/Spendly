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
      addEventListener(){}, focus(){}, scrollIntoView(){},
    });
    return elements.get(id);
  };
  const context = vm.createContext({
    document:{getElementById:element, querySelector:()=>({content:'synthetic-csrf'})},
    fetch:path=>new Promise((resolve,reject)=>pending.push({path,resolve,reject})),
    Intl, URLSearchParams, setTimeout, location:{assign(){}},
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

test('an empty history explains the observation boundary and disables paging',async()=>{
  const h=harness();h.select('legacy');const request=h.run('loadSignIns()');
  h.pending[0].resolve({ok:true,status:200,json:async()=>({data:{items:[],page:1,pages:0,total:0}})});
  await request;
  assert.match(h.element('signins-list').innerHTML,/Older history is unavailable/);
  assert.equal(h.element('signins-prev').disabled,true);
  assert.equal(h.element('signins-next').disabled,true);
});
