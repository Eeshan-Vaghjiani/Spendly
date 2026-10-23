// Real dashboard script with synthetic responses; no network or personal data.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {readFileSync}=require('node:fs');
const {join}=require('node:path');
const vm=require('node:vm');

function harness(){
  const elements=new Map(),listeners={},pending=[];
  const ctx=new Proxy({}, {get:(target,key)=>key==='scale'||key==='clearRect'||key==='beginPath'||key==='moveTo'||key==='lineTo'||key==='stroke'||key==='bezierCurveTo'||key==='arc'||key==='fill'||key==='fillText'?()=>{}:target[key],set:(target,key,value)=>(target[key]=value,true)});
  const element=id=>{
    if(!elements.has(id))elements.set(id,{innerHTML:'',textContent:'',disabled:false,style:{},clientWidth:240,
      setAttribute(){},removeAttribute(){},addEventListener:(name,fn)=>{listeners[id+name]=fn;},getContext:()=>ctx});
    return elements.get(id);
  };
  const context=vm.createContext({document:{getElementById:element},window:{devicePixelRatio:1,addEventListener:(name,fn)=>{listeners[name]=fn;},location:{assign(){}}},Intl,Number,Array,Object,Math,Date,Set,
    fetch:()=>new Promise(resolve=>pending.push(resolve)),setTimeout:fn=>{fn();return 1;},clearTimeout(){}});
  const html=readFileSync(join(__dirname,'../app/templates/admin/dashboard.html'),'utf8');
  const source=html.match(/<script>([\s\S]*?)<\/script>/)[1];
  vm.runInContext(source,context);
  return {element,listeners,pending,run:code=>vm.runInContext(code,context)};
}

test('daily activity has direct counts, escapes dates and retains zeros',()=>{
  const h=harness();
  const html=h.run(`activityRows({days:[{date:'<unsafe>',sign_ins:0,new_users:0},{date:'2026-10-20',sign_ins:4,new_users:2}]})`);
  assert.match(html,/&lt;unsafe&gt;/);assert.match(html,/<strong>0<\/strong>/);assert.match(html,/width:100%/);
  assert.match(h.run('activityRows(null)'),/unavailable/);
});

test('unmatched evaluation cannot produce metric bars or guessed scores',()=>{
  const h=harness();
  const html=h.run(`modelCards({forecasting:{version:'v1',evaluation:{status:'mismatch',cohorts:[{label:'unsafe',metrics:{F1:1}}]}}})`);
  assert.match(html,/unavailable for this serving artifact/);assert.doesNotMatch(html,/evaluation-track/);assert.doesNotMatch(html,/100\.00%/);
});

test('matched cohort bars keep labels, limitations and exact values',()=>{
  const h=harness();
  const html=h.run(`modelCards({anomaly:{version:'v1',evaluation:{status:'artifact_matched',cohorts:[{label:'Synthetic test',limitation:'Not real-user accuracy',metrics:{precision:.625,recall:.75,F1:.68},source:{url:'https://example.invalid/evidence',sha256:'fixture'}}]}}})`);
  assert.match(html,/Synthetic test/);assert.match(html,/Not real-user accuracy/);assert.match(html,/62\.50%/);assert.match(html,/width:62\.5%/);assert.match(html,/Evidence source/);
});

test('dashboard keeps extra metrics and resize redraws without a new API request',async()=>{
  const h=harness();
  const metrics={users:48,signed_in_users_7d:15,signed_in_users_30d:20,google_users:8,engaged_users:12,new_users_30d:4,transactions:420,income:48000,expense:32000,net_savings:16000,budgeted:40000,analysis_runs:96,forecasts:8,predicted_spending:12000,unusual_alerts:2};
  h.pending[0]({ok:true,status:200,json:async()=>({data:{metrics,generated_at:'2026-10-20T10:00:00Z',release:{api_release:'test'},cashflow:[{label:'Oct',income:48000,expense:32000}],model_info:{},recent_forecasts:[],recent_unusual_alerts:[],recent_users:[],account_activity:{days:[]}}})});
  await new Promise(setImmediate);
  const top=h.element('metrics').innerHTML,extra=h.element('extra-metrics').innerHTML;
  assert.equal((top.match(/<article/g)||[]).length,4);assert.match(top,/Analysis runs/);assert.doesNotMatch(top,/Google accounts/);assert.match(extra,/Google accounts/);assert.match(extra,/Predicted spending/);
  h.listeners.resize();assert.equal(h.pending.length,1);assert.equal(h.element('refresh').disabled,false);
});
