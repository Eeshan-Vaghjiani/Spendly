'use strict';
const $ = id => document.getElementById(id);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cash = v => new Intl.NumberFormat('en-KE',{style:'currency',currency:'KES',maximumFractionDigits:2}).format(v);
const date = v => new Date(v).toLocaleString('en-KE');
const csrf = document.querySelector('meta[name="csrf-token"]').content;
let selected = null, recordRows = [], system = null, pendingAction = null;
const pages = {users:1, records:1, audit:1};
let usersRequest = 0, detailRequest = 0, recordsRequest = 0, auditRequest = 0;

function notice(message, error=false){$('notice').textContent=message;$('notice').className=error?'error':'';$('notice').hidden=false;}
async function api(path, method='GET', body, download=false){
  const response = await fetch('/api/v1/admin'+path,{method,cache:'no-store',credentials:'same-origin',headers:{Accept:'application/json','Content-Type':'application/json','X-CSRF-Token':csrf},body:body?JSON.stringify(body):undefined});
  if(response.status===401){location.assign('/admin/login');throw new Error('Your administrator session expired.');}
  if(!response.ok){const data=await response.json();throw new Error(data.error?.message||`Request failed (${response.status}).`);}
  return download?response.blob():(await response.json()).data;
}
function pageControls(kind,data){
  pages[kind]=data.page;$(kind+'-prev').disabled=data.page<=1;$(kind+'-next').disabled=data.page>=data.pages;
  $(kind+'-page').textContent=`Page ${data.page} of ${Math.max(1,data.pages)} · ${data.total} records`;
}
async function loadUsers(){
  const serial=++usersRequest;
  const query=new URLSearchParams({q:$('search').value,status:$('account-status').value,page:pages.users});
  const data=await api('/users?'+query);if(serial!==usersRequest)return;
  $('user-list').innerHTML=data.items.length?data.items.map(u=>`<tr><td><strong>${esc(u.display_name)}</strong><br><small>@${esc(u.username)}</small></td><td>${esc(u.email)}</td><td>${esc(u.login_provider)}</td><td><span class="pill ${u.is_active?'':'off'}">${u.is_active?'Active':'Disabled'}</span></td><td><button data-open="${esc(u.id)}" class="secondary">Manage</button></td></tr>`).join(''):'<tr><td colspan="5" class="empty">No accounts match your search.</td></tr>';
  pageControls('users',data);
}
async function openUser(id,focus=true){
  const serial=++detailRequest;++recordsRequest;selected=null;recordRows=[];$('detail').hidden=true;
  const data=await api('/users/'+encodeURIComponent(id));if(serial!==detailRequest)return;
  selected=data.user;$('detail').hidden=false;$('detail-title').textContent=selected.display_name;
  $('detail-subtitle').textContent=`@${selected.username} · ${selected.email} · ${selected.is_active?'Active':'Disabled'} · Training consent: ${selected.model_training_opt_in?'opted in':'not opted in'}`;
  $('detail-summary').innerHTML=[['Transactions',data.counts.transactions],['Budgets',data.counts.budgets],['Income entered',cash(data.income)],['Expenses entered',cash(data.expense)]].map(([k,v])=>`<div>${esc(k)}<strong>${esc(v)}</strong></div>`).join('');
  $('account-actions').innerHTML=`<button data-account="profile" class="secondary">Edit profile</button><button data-account="status" class="${selected.is_active?'danger':'secondary'}">${selected.is_active?'Disable account':'Enable account'}</button><button data-account="revoke" class="secondary">Revoke sessions</button><button data-account="export" class="secondary">Export account data</button><button data-account="delete" class="danger" ${selected.is_active?'disabled title="Disable the account first"':''}>Delete account</button>`;
  pages.records=1;await loadRecords();if(focus){$('detail-title').focus();$('detail').scrollIntoView({block:'start'});}
}
async function loadRecords(){
  if(!selected)return;
  const serial=++recordsRequest,kind=$('record-kind').value;
  $('add-record').hidden=!['transactions','budgets'].includes(kind);
  $('record-list').innerHTML='<tr><td colspan="4">Loading records…</td></tr>';
  const data=await api(`/users/${selected.id}/records/${kind}?page=${pages.records}`);if(serial!==recordsRequest)return;
  recordRows=data.items;
  $('record-head').innerHTML='<tr><th>Record</th><th>Details</th><th>Value / status</th><th>Actions</th></tr>';
  $('record-list').innerHTML=data.items.length?data.items.map(row=>{
    let title,detail,value;
    if(kind==='transactions'){title=date(row.transaction_timestamp);detail=`${row.category} · ${row.merchant||'No merchant'}${row.is_recurring?' · Recurring':''}`;value=`${row.transaction_type} · ${cash(row.amount)}`;}
    else if(kind==='budgets'){title=row.category;detail=`${row.period_start} – ${row.period_end}`;value=cash(row.amount);}
    else if(kind==='forecasts'){title=`${row.period_start} – ${row.period_end}`;detail=`Experimental · ${row.model_version}`;value=cash(row.predicted_spending);}
    else if(kind==='alerts'){title=date(row.created_at);detail=row.explanation;value=`Score ${Number(row.anomaly_score).toFixed(3)} · ${row.model_version}`;}
    else{title=row.title;detail=row.message;value=row.severity;}
    const actions=['transactions','budgets'].includes(kind)?`<button data-edit="${esc(row.id)}" class="secondary">Edit</button><button data-delete="${esc(row.id)}" class="danger">Delete</button>`:'Read only';
    return `<tr><td><strong>${esc(title)}</strong><br><small>${esc(row.id)}</small></td><td>${esc(detail)}</td><td>${esc(value)}</td><td>${actions}</td></tr>`;
  }).join(''):'<tr><td colspan="4" class="empty">No records in this category.</td></tr>';
  pageControls('records',data);
}
async function loadSettings(){
  system=await api('/settings');$('analysis-status').textContent=system.analysis_enabled?'Enabled · new insights can be generated':'Paused · no new analysis requests';
  $('toggle-analysis').disabled=false;$('toggle-analysis').textContent=system.analysis_enabled?'Pause new insights':'Resume new insights';
  $('runtime-status').textContent=`${system.model_runtime} · ${system.models_loaded?'Artifacts loaded':'Models unavailable'} · ${Object.entries(system.model_info).map(([k,v])=>`${k}: ${v.version}`).join(' / ')}`;
}
async function loadAudit(){
  const serial=++auditRequest;const data=await api('/audit?page='+pages.audit);if(serial!==auditRequest)return;
  $('audit-list').innerHTML=data.items.length?data.items.map(row=>`<tr><td>${esc(date(row.created_at))}<br><small>${esc(row.actor)}</small></td><td>${esc(row.action)}</td><td>${esc(row.target_type)}<br><small>${esc(row.target_id)}</small></td><td>${esc(row.reason)}<br><small>${esc(JSON.stringify(row.details))}</small></td></tr>`).join(''):'<tr><td colspan="4" class="empty">No activity yet.</td></tr>';
  pageControls('audit',data);
}
function field(name,label,value='',type='text',options){
  return {name,label,value,type,options};
}
function showAction(title,description,fields,run){
  pendingAction=run;$('action-form').reset();$('action-error').hidden=true;$('action-title').textContent=title;$('action-description').textContent=description;
  $('action-fields').innerHTML=fields.map(f=>`<label>${esc(f.label)}${f.options?`<select name="${esc(f.name)}">${f.options.map(v=>`<option value="${esc(v)}" ${String(f.value)===v?'selected':''}>${esc(v)}</option>`).join('')}</select>`:`<input required name="${esc(f.name)}" type="${esc(f.type)}" value="${esc(f.value)}" ${f.type==='number'?'min="0.01" max="999999999999.99" step="0.01"':''}>`}</label>`).join('');
  $('action-dialog').showModal();
}
function accountAction(action){
  if(!selected)return;const u={...selected},base='/users/'+u.id;
  const done=async(body,path=base,method='PATCH',extra={})=>{await api(path,method,{...body,...extra});await openUser(u.id,false);await loadUsers();};
  if(action==='profile')showAction('Edit account profile',`Editing @${u.username}. Email, Google identity and consent cannot be changed.`,[field('display_name','Display name',u.display_name),field('username','Username',u.username)],b=>done(b));
  if(action==='status')showAction(u.is_active?'Disable account':'Enable account',u.is_active?'This blocks sign-in and revokes existing access tokens immediately.':'This restores sign-in; previously revoked tokens remain invalid.',[],b=>done(b,base,'PATCH',{is_active:!u.is_active}));
  if(action==='revoke')showAction('Revoke all sessions',`@${u.username} must sign in again on all devices.`,[],b=>done(b,base+'/revoke-sessions','POST'));
  if(action==='delete')showAction('Permanently delete account',`This removes @${u.username} and all their financial records and stored insights. No app undo is available. Audit entries remain. Type the exact username.`,[field('confirm_username','Confirm username')],async b=>{await api(base,'DELETE',b);selected=null;++detailRequest;++recordsRequest;$('detail').hidden=true;await loadUsers();});
  if(action==='export')showAction('Export private account data','The download contains personal financial records. Store it securely and delete it when no longer needed. Credentials are excluded.',[],async b=>{const blob=await api(base+'/export','POST',b,true);const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`spendly-user-${u.id}.json`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
}
function recordAction(id,remove=false){
  if(!selected)return;const userId=selected.id,kind=$('record-kind').value,row=recordRows.find(r=>r.id===id);
  if(!['transactions','budgets'].includes(kind))return;
  const base=`/users/${userId}/records/${kind}`;
  if(remove){showAction('Permanently delete record',`No undo. Historical insights are not recomputed. Type this record ID: ${id}`,[field('confirm_id','Confirm record ID')],async b=>{await api(base+'/'+id,'DELETE',b);await openUser(userId,false);});return;}
  let fields;
  if(kind==='transactions')fields=[field('transaction_timestamp','Timestamp (UTC, ISO 8601)',row?.transaction_timestamp||new Date().toISOString()),field('amount','Amount (KES)',row?.amount||'','number'),field('category','Category',row?.category||''),field('transaction_type','Type',row?.transaction_type||'expense','text',['expense','income']),field('merchant','Merchant (use a dash if none)',row?.merchant||'-'),field('is_recurring','Recurring',String(row?.is_recurring||false),'text',['false','true'])];
  else fields=[field('period_start','Start date',row?.period_start||'','date'),field('period_end','End date',row?.period_end||'','date'),field('category','Category',row?.category||''),field('amount','Amount (KES)',row?.amount||'','number')];
  showAction(`${row?'Correct':'Add'} ${kind==='transactions'?'transaction':'budget'}`,'This changes the user’s financial records. Existing analyses remain historical snapshots; the user should generate a new analysis.',fields,async b=>{const {reason,admin_password,...record}=b;record.amount=Number(record.amount);if(kind==='transactions'){record.is_recurring=record.is_recurring==='true';if(record.merchant==='-')record.merchant=null;}await api(base+(row?'/'+row.id:''),row?'PUT':'POST',{reason,admin_password,record});await openUser(userId,false);});
}
function safe(fn){return(...args)=>{try{return Promise.resolve(fn(...args)).catch(e=>notice(e.message,true));}catch(e){notice(e.message,true);}};}
$('search-form').addEventListener('submit',safe(e=>{e.preventDefault();pages.users=1;return loadUsers();}));
$('user-list').addEventListener('click',safe(e=>{const b=e.target.closest('[data-open]');if(b)return openUser(b.dataset.open);}));
$('close-detail').onclick=()=>{selected=null;++detailRequest;++recordsRequest;$('detail').hidden=true;};
$('record-kind').onchange=safe(()=>{pages.records=1;return loadRecords();});
$('account-actions').onclick=e=>{const b=e.target.closest('[data-account]');if(b)accountAction(b.dataset.account);};
$('add-record').onclick=()=>recordAction();
$('record-list').onclick=e=>{const b=e.target.closest('[data-edit],[data-delete]');if(b)recordAction(b.dataset.edit||b.dataset.delete,Boolean(b.dataset.delete));};
for(const [kind,loader] of Object.entries({users:loadUsers,records:loadRecords,audit:loadAudit})){
  $(kind+'-prev').onclick=safe(()=>{pages[kind]=Math.max(1,pages[kind]-1);return loader();});
  $(kind+'-next').onclick=safe(()=>{pages[kind]++;return loader();});
}
$('refresh-audit').onclick=safe(loadAudit);
$('toggle-analysis').onclick=()=>{const enabled=!system.analysis_enabled;showAction(enabled?'Resume new insights':'Pause new insights','This affects all users. Financial record entry and stored results stay available. No model artifact or threshold is changed.',[],async b=>{await api('/settings','PUT',{...b,analysis_enabled:enabled});await loadSettings();});};
$('action-cancel').onclick=()=>{$('action-dialog').close();};
$('action-dialog').addEventListener('close',()=>{$('action-form').reset();pendingAction=null;});
$('action-dialog').addEventListener('cancel',e=>{if($('action-submit').disabled)e.preventDefault();});
$('action-form').addEventListener('submit',async e=>{
  e.preventDefault();if(!pendingAction||$('action-submit').disabled)return;
  const body=Object.fromEntries(new FormData(e.target));$('action-submit').disabled=true;$('action-cancel').disabled=true;$('action-error').hidden=true;
  try{await pendingAction(body);$('action-dialog').close();notice('Action completed. The audit trail has been updated.');await loadAudit();}
  catch(error){$('action-error').textContent=error.message;$('action-error').hidden=false;}
  finally{$('action-submit').disabled=false;$('action-cancel').disabled=false;e.target.elements.admin_password.value='';}
});
Promise.allSettled([loadUsers(),loadSettings(),loadAudit()]).then(results=>results.forEach(r=>{if(r.status==='rejected')notice(r.reason.message,true);}));
