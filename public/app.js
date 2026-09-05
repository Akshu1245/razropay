'use strict';
const $ = id => document.getElementById(id);
const money = value => new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(Number(value||0));
const esc = value => String(value ?? '—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const human = value => String(value || 'Unknown').toLowerCase().replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
const clone = value => typeof structuredClone === 'function' ? structuredClone(value) : JSON.parse(JSON.stringify(value));
const labels = {
  B0:'No intervention', B1:'Ungated retry', 'B1.5':'Reason-aware retry', RZP:'Fixed card-schedule reference',
  'B2.25':'Timing frontier', 'B2.5':'Timing + attempts frontier', 'B2.75':'Timing + attempts + consent frontier',
  B2:'Full deterministic guardrails', B3:'Same guardrails + bounded interpreter'
};
const outcomes=['Recovered','Stopped','Human review','Awaiting outcome'];
const exemplarKeys=['recover','revoked','timeout'];
const boundaryKeys=['optout','notice','ambiguous','forged'];
let evidence,batch,currentReceipt,apiAvailable=false,activeStatus='all',page=0,selectedBoundary='ambiguous',boundaryScenario;
let scenarios={};
const liveScenarios=new Set();
let toastTimer;

function toast(message){
  $('toast').textContent=message;
  $('toast').classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),4500);
}
function setRunState(kind,title,message){
  const box=$('run-state');
  box.className='run-state '+kind;
  box.innerHTML='<span class="run-state-dot"></span><strong>'+esc(title)+'</strong><span>'+esc(message)+'</span>';
}
function status(row){
  if(!row) return 'Unknown';
  if(row.provider_timed_out || ['abstain','escalate'].includes(row.decision) || row.final_action==='escalate_to_human') return 'Human review';
  if(row.provider_postcondition_state==='RECOVERED') return 'Recovered';
  return row.provider_call_made ? 'Awaiting outcome' : 'Stopped';
}
function badge(value){
  const tone=value==='Recovered'?'good':value==='Human review'?'warn':value==='Awaiting outcome'?'blue':value==='Rejected at ingress'?'bad':'';
  return '<span class="badge '+tone+'">'+esc(value)+'</span>';
}
function download(value,filename){
  const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'],{type:'application/json'}));
  const link=document.createElement('a');
  link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function request(path,data){
  const response=await fetch('./api/demo/'+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data||{}),signal:AbortSignal.timeout(30000)});
  if(!response.ok) throw new Error('Engine returned HTTP '+response.status);
  return response.json();
}

function renderBatch(){
  if(!batch) return;
  const summary=batch.summaries.find(row=>row.arm==='B3');
  const counts=Object.fromEntries(outcomes.map(name=>[name,batch.receipts.filter(row=>status(row)===name).length]));
  const cards=[
    ['Simulated revenue recovered',money(summary.recovered_inr),summary.provider_calls+' provider calls in the guarded workflow',true],
    ['Payments recovered',String(counts.Recovered),counts.Recovered+' of '+batch.n+' cases reached a recovered postcondition',false],
    ['Cases stopped',String(counts.Stopped),'No provider action on these stopped cases',false],
    ['Cases requiring review',String(counts['Human review']),'Uncertainty is held before another automated action',false],
    ['Awaiting outcome',String(counts['Awaiting outcome']),'Provider called; recovery is not yet confirmed',false],
    ['Recoverable value forgone',money(summary.legitimate_recovery_forgone_inr),'Synthetic latent recovery blocked by controls',false]
  ];
  $('stats').innerHTML=cards.map(card=>'<div class="stat-card '+(card[3]?'primary':'')+'"><div class="stat-label">'+esc(card[0])+'</div><div class="stat-value">'+esc(card[1])+'</div><div class="stat-detail">'+esc(card[2])+'</div></div>').join('');
  $('batch-source').textContent='Recorded provenance · seed '+batch.seed+' · '+batch.regime+' · ledger '+batch.ledger_sha256.slice(0,14)+'…';
  const m=evidence.manifest;
  $('evaluation-size').textContent=(m.seeds.length*m.regimes.length*m.n_per_seed*m.arms.length).toLocaleString()+' policy decisions · '+m.seeds.length+' seeds · '+m.arms.length+' arms';
  renderQueue();
}

function caseCopy(key,scenario){
  const row=scenario?.receipt;
  if(key==='recover') return {
    kicker:'A · Eligible failure', title:'Retry is permitted',
    why:'The failure is recoverable and the configured authority checks allow the bounded action.',
    action:scenario?.status || 'Recovered', tone:'recovered'
  };
  if(key==='revoked') return {
    kicker:'B · Revoked mandate', title:'Stop before the provider',
    why:'The failure itself looks retryable, but the mandate state is revoked. That control ends authority to execute.',
    action:scenario?.status || 'Stopped', tone:'stopped'
  };
  return {
    kicker:'C · Unknown timeout', title:'Ask a human before another action',
    why:'A provider call happened, but its postcondition is unknown. The workflow does not guess that it failed or retry blindly.',
    action:scenario?.status || 'Human review', tone:'review'
  };
}
function caseTimeline(key,scenario){
  const row=scenario?.receipt;
  if(!row) return [];
  const reason=human(row.diagnosed_reason);
  const checks=key==='revoked'?'Mandate state: '+human(row.mandate_state):row.reason_codes.map(human).slice(0,3).join(' · ') || 'Configured controls evaluated';
  const action=key==='recover'?(row.provider_call_made?'Provider action permitted':'No provider action'):
    key==='revoked'?'Denied before provider':row.provider_call_made?'Provider call attempted':'No provider action';
  const outcome=key==='timeout'?'Postcondition unknown → human review':row.provider_postcondition_state?human(row.provider_postcondition_state):status(row);
  return [
    ['Failure','Scheduled UPI AutoPay debit failure received'],
    ['Diagnosis',reason],
    ['Control checks',checks],
    ['Action',action],
    ['Outcome',outcome]
  ];
}
function renderCase(key,live=false){
  const scenario=scenarios[key];
  const host=$('case-'+key);
  if(!scenario || !host) return;
  const row=scenario.receipt;
  const copy=caseCopy(key,scenario);
  const calls=scenario.provider_call_count ?? row?.provider_call_count ?? 0;
  host.dataset.tone=copy.tone;
  const timeline=caseTimeline(key,scenario);
  host.innerHTML='<div class="case-kicker"><strong>'+esc(copy.kicker)+'</strong>'+badge(scenario.status)+'</div>'+
    '<h3>'+esc(copy.title)+'</h3><p class="case-description">'+esc(scenario.description)+'</p>'+
    '<div class="case-verdict"><div><small>ACTUAL ENGINE OUTCOME</small><strong>'+esc(copy.action)+'</strong></div><div class="call-count"><small>PROVIDER CALLS</small><strong>'+esc(calls)+'</strong></div></div>'+
    '<p class="decision-why">'+esc(copy.why)+'</p>'+
    '<ol class="timeline">'+timeline.map((step,i)=>'<li><span>'+String(i+1).padStart(2,'0')+'</span><div><b>'+esc(step[0])+'</b><small>'+esc(step[1])+'</small></div></li>').join('')+'</ol>'+
    '<div class="case-actions">'+(row?'<button class="button secondary compact" data-receipt-key="'+esc(key)+'">View decision receipt</button>':'')+
    '<span class="badge '+(row?.audit_verified?'good':'')+'">'+(row?.audit_verified?'Audit chain verified by Python':key==='timeout'?'Unknown outcome held':'Evidence available')+'</span></div>'+
    '<p class="muted">'+(live?'Just executed by the local Python engine.':'Recorded engine evidence. Static hosting does not execute Python.')+'</p>';
}
function renderCases(live=false){exemplarKeys.forEach(key=>renderCase(key,live));}

function renderBoundaryList(){
  $('boundary-list').innerHTML=boundaryKeys.map(key=>{
    const item=evidence.scenarios[key];
    return '<button class="boundary-button '+(selectedBoundary===key?'active':'')+'" data-boundary="'+key+'" aria-pressed="'+(selectedBoundary===key)+'"><strong>'+esc(item.title)+'</strong><small>'+esc(item.description)+'</small></button>';
  }).join('');
  document.querySelectorAll('[data-boundary]').forEach(button=>button.addEventListener('click',()=>{
    selectedBoundary=button.dataset.boundary;
    boundaryScenario=scenarios[selectedBoundary] || evidence.scenarios[selectedBoundary];
    renderBoundaryList();renderBoundary();
  }));
}
function renderBoundary(live=liveScenarios.has(selectedBoundary)){
  const scenario=boundaryScenario || evidence.scenarios[selectedBoundary];
  if(!scenario) return;
  const row=scenario.receipt;
  $('boundary-mode').textContent=live?'JUST EXECUTED · LOCAL PYTHON ENGINE':'RECORDED ENGINE EVIDENCE';
  $('boundary-title').textContent=scenario.title;
  $('boundary-description').textContent=scenario.description;
  const steps=[
    ['Authenticate',scenario.ingress.accepted?'HMAC verified over the signed fixture bytes.':human(scenario.ingress.reason_code)],
    ['Interpret',row?human(row.diagnosed_reason)+(row.interpreter_consulted?' · bounded interpreter consulted':' · deterministic reason mapping'):'Not reached'],
    ['Control checks',row?(row.reason_codes.map(human).join(' · ')||'Configured controls evaluated'):'Not reached'],
    ['Provider outcome',row?.provider_postcondition_state || 'No provider action'],
    ['Evidence',row?(row.audit_verified?'Audit chain verified by Python':'Audit verification failed'):'Rejected body hash: '+scenario.ingress.body_sha256]
  ];
  $('boundary-output').innerHTML='<div class="boundary-verdict"><div><small>FINAL OUTCOME</small><strong>'+esc(scenario.status)+'</strong></div><div><small>PROVIDER CALLS</small><strong class="provider-number">'+esc(scenario.provider_call_count)+'</strong></div></div>'+
    '<div class="trace">'+steps.map((step,i)=>'<div class="trace-item"><span>'+String(i+1).padStart(2,'0')+'</span><div><strong>'+esc(step[0])+'</strong><p>'+esc(step[1])+'</p></div></div>').join('')+'</div>'+
    (selectedBoundary==='ambiguous'?'<div class="notice">Low-confidence interpretation abstains before the provider. AI proposes an interpretation; deterministic controls keep execution authority.</div>':'');
  $('run-boundary').textContent=apiAvailable?'Run boundary check':'Replay recorded boundary check';
}

function renderQueue(){
  if(!batch) return;
  const query=$('case-search').value.trim().toLowerCase();
  const rows=batch.receipts.filter(row=>(activeStatus==='all'||status(row)===activeStatus) && (row.case_id+' '+human(row.diagnosed_reason)+' '+row.reason_codes.join(' ')).toLowerCase().includes(query));
  const limit=8,pages=Math.max(1,Math.ceil(rows.length/limit));page=Math.min(page,pages-1);
  $('queue-body').innerHTML=rows.slice(page*limit,(page+1)*limit).map(row=>{
    const numeric=Number(row.case_id.split('_').pop());
    const label=Number.isFinite(numeric)?'MG-'+String(numeric+1).padStart(4,'0'):esc(row.case_id);
    return '<tr><td class="case-id">'+label+'<small>Scheduled UPI AutoPay</small></td><td>'+esc(human(row.diagnosed_reason))+'</td><td>'+money(row.amount_inr)+'</td><td>'+badge(status(row))+'</td><td class="calls">'+row.provider_call_count+'</td><td><button class="text-button inspect" data-case="'+esc(row.case_id)+'">View receipt</button></td></tr>';
  }).join('') || '<tr><td colspan="6" class="empty">No cases match this filter.</td></tr>';
  $('page-info').textContent=rows.length?'Showing '+(page*limit+1)+'–'+Math.min((page+1)*limit,rows.length)+' of '+rows.length:'0 matching cases';
  $('prev').disabled=page===0;$('next').disabled=page>=pages-1;
  document.querySelectorAll('.inspect').forEach(button=>button.addEventListener('click',()=>openReceipt(batch.receipts.find(row=>row.case_id===button.dataset.case))));
}

document.querySelectorAll('[data-status]').forEach(button=>button.addEventListener('click',()=>{
  activeStatus=button.dataset.status;page=0;
  document.querySelectorAll('[data-status]').forEach(item=>{item.classList.toggle('active',item===button);item.setAttribute('aria-pressed',String(item===button));});
  renderQueue();
}));
$('case-search').addEventListener('input',()=>{page=0;renderQueue();});
$('prev').addEventListener('click',()=>{page=Math.max(0,page-1);renderQueue();});
$('next').addEventListener('click',()=>{page++;renderQueue();});

function receiptName(row,fallback){
  if(fallback) return fallback;
  const numeric=Number(String(row.case_id||'').split('_').pop());
  return Number.isFinite(numeric)?'MG-'+String(numeric+1).padStart(4,'0'):String(row.case_id||'Decision receipt');
}
function openReceipt(row,fallback){
  if(!row){toast('This case has no downstream receipt because it was rejected before diagnosis.');return;}
  currentReceipt=row;
  $('receipt-title').textContent=receiptName(row,fallback);
  const facts=[
    ['Outcome',status(row)],['Recovered · simulated',money(row.recovered_inr)],['Provider calls',row.provider_call_count],['Mandate state',human(row.mandate_state)],
    ['Diagnosis',human(row.diagnosed_reason)],['Interpretation score · not measured accuracy',Math.round(Number(row.confidence||0)*100)+'%'],['Postcondition',row.provider_postcondition_state?human(row.provider_postcondition_state):'No provider action'],['Recoverable value forgone',money(row.legitimate_recovery_forgone_inr)]
  ];
  $('receipt-content').innerHTML='<div class="receipt-facts">'+facts.map(f=>'<div><small>'+esc(f[0])+'</small><strong>'+esc(f[1])+'</strong></div>').join('')+'</div>'+
    '<h3>Audit timeline</h3><div class="trace">'+row.audit_events.map(event=>'<div class="trace-item"><span>'+event.sequence+'</span><div><strong>'+esc(human(event.event_type))+'</strong><p>'+esc(event.reason_codes.join(' · '))+'</p><p>Provider call: '+esc(event.provider_call_made)+'</p></div></div>').join('')+'</div>'+
    '<details><summary>Technical receipt: idempotency key, call identifiers and hashes</summary><pre>'+esc(JSON.stringify(row,null,2))+'</pre></details>';
  $('verify-result').textContent='';
  $('receipt-dialog').showModal();
}
document.addEventListener('click',event=>{
  const button=event.target.closest('[data-receipt-key]');
  if(!button) return;
  const key=button.dataset.receiptKey;
  openReceipt(scenarios[key]?.receipt,scenarios[key]?.title || 'Decision receipt');
});
$('close-dialog').addEventListener('click',()=>$('receipt-dialog').close());
$('receipt-dialog').addEventListener('click',event=>{
  if(event.target!==$('receipt-dialog')) return;
  const r=event.target.getBoundingClientRect();
  if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom) event.target.close();
});
$('export-receipt').addEventListener('click',()=>currentReceipt&&download(currentReceipt,'mandateguard-decision-receipt.json'));

function pythonJson(value){
  if(value===null||typeof value!=='object') return JSON.stringify(value).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
  if(Array.isArray(value)) return '['+value.map(pythonJson).join(', ')+']';
  return '{'+Object.keys(value).sort().map(k=>pythonJson(k)+': '+pythonJson(value[k])).join(', ')+'}';
}
async function digest(text){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('');}
async function verifyChain(events){
  if(!events?.length) return false;
  let previous='GENESIS';
  for(const event of events){
    const {event_hash,...body}=event;
    if(body.previous_hash!==previous || await digest(pythonJson(body))!==event_hash) return false;
    previous=event_hash;
  }
  return true;
}
$('verify-receipt').addEventListener('click',async()=>{
  if(!currentReceipt) return;
  try{
    const valid=await verifyChain(currentReceipt.audit_events);
    const tampered=clone(currentReceipt.audit_events);tampered[0].decision='tampered';
    const tamperDetected=!(await verifyChain(tampered));
    $('verify-result').textContent=valid&&tamperDetected?'Verified in this browser: the shipped hashes match, and editing the first decision breaks the chain. This is tamper-evident, not immutable storage.':'Verification failed. Do not trust this receipt.';
  }catch{
    $('verify-result').textContent='Browser cryptography is unavailable. Use HTTPS or localhost, or verify with the Python tooling.';
  }
});

function renderProof(){
  const p=evidence.provider_proofs,proof=p.artifacts.recovery_proof.proof,blocked=p.artifacts.safe_block_zero_write;
  const verified=p.summary.recovery_verified,zero=p.summary.already_paid_zero_write_verified;
  $('proof-cards').innerHTML='<div class="proof-mini">'+badge(verified?'Verified saved proof':'Proof verification failed')+'<div class="amount">'+money(proof.amount_minor/100)+'</div><h3>Captured payment</h3><p>Independent Test Mode capture verification bound to the fallback case.</p></div>'+
    '<div class="proof-mini">'+badge(zero?'Zero-write verified':'Evidence incomplete')+'<div class="amount">'+blocked.payment_links_before+' → '+blocked.payment_links_after+'</div><h3>Already paid</h3><p>No new fallback collection object was created.</p></div>';
  $('proof-json').textContent=JSON.stringify(p.artifacts,null,2);
  $('model-evidence').textContent=JSON.stringify(evidence.real_interpreter_evidence,null,2);
  $('interpreter-comparison').innerHTML=evidence.manifest.regimes.map(regime=>{
    const b2=evidence.aggregate.find(row=>row.regime===regime&&row.arm==='B2');
    const b3=evidence.aggregate.find(row=>row.regime===regime&&row.arm==='B3');
    const delta=b3.incremental_recovered_inr.mean-b2.incremental_recovered_inr.mean;
    return '<tr><th scope="row">'+esc(human(regime.replace(/^R\d+_/,'')))+'</th><td>'+money(b2.incremental_recovered_inr.mean)+'</td><td>'+money(b3.incremental_recovered_inr.mean)+'</td><td>'+(delta>0?'+':'')+money(delta)+'</td><td>'+money(b2.realized_harm_inr.mean)+' / '+money(b3.realized_harm_inr.mean)+'</td></tr>';
  }).join('');
}
$('export-proof').addEventListener('click',()=>download(evidence.provider_proofs,'mandateguard-captured-razorpay-testmode-evidence.json'));

function renderPolicies(){
  const regime=$('regime').value;
  const rows=evidence.manifest.arms.map(arm=>evidence.aggregate.find(row=>row.arm===arm&&row.regime===regime)).filter(Boolean);
  const max=Math.max(...rows.flatMap(row=>[row.incremental_recovered_inr.mean,row.realized_harm_inr.mean]),1);
  $('policy-bars').innerHTML=rows.map(row=>'<div class="bar-row"><div class="bar-label"><b>'+esc(row.arm)+'</b><small>'+esc(labels[row.arm])+'</small></div><div class="bar-pair"><span style="background:var(--teal);width:'+Math.max(.4,row.incremental_recovered_inr.mean/max*100)+'%"></span><span style="background:var(--red);width:'+Math.max(.4,row.realized_harm_inr.mean/max*100)+'%"></span></div><div class="bar-value"><span>'+money(row.incremental_recovered_inr.mean)+'</span><span>'+money(row.realized_harm_inr.mean)+'</span></div></div>').join('');
  $('policy-table').innerHTML=rows.map(row=>'<tr><td><b>'+esc(row.arm)+'</b></td><td>'+esc(labels[row.arm])+'</td><td>'+money(row.incremental_recovered_inr.mean)+'</td><td>'+money(row.legitimate_recovery_forgone_inr.mean)+'</td><td>'+money(row.realized_harm_inr.mean)+'</td><td>'+row.violations.mean.toFixed(1)+'</td></tr>').join('');
  const model=$('price-model').value;
  const curve=evidence.sensitivity.per_regime[regime][model];
  $('price-curve').innerHTML='<div class="price-grid">'+curve.map(point=>'<div class="price-point '+(['B2','B3'].includes(point.recommended_arm)?'guarded':'')+'"><small>'+(model==='harm_multiplier_curve'?point.harm_multiplier+'× harm':money(point.violation_cost_inr)+' / breach')+'</small><b>'+esc(point.recommended_arm)+'</b><span>'+money(point.net_value_by_arm_inr[point.recommended_arm])+' net</span></div>').join('')+'</div>';
}
$('regime').addEventListener('change',renderPolicies);
$('price-model').addEventListener('change',renderPolicies);

async function runDemonstration(){
  const button=$('run-demo');
  button.disabled=true;
  setRunState('loading','Running recovery demonstration…',apiAvailable?'Executing the Python engine for the batch and three decisive cases.':'Static hosting will replay the exported engine evidence; no fake live execution is shown.');
  try{
    if(apiAvailable){
      const [newBatch,recover,revoked,timeout]=await Promise.all([
        request('batch'),request('scenario',{scenario:'recover'}),request('scenario',{scenario:'revoked'}),request('scenario',{scenario:'timeout'})
      ]);
      batch=newBatch;scenarios.recover=recover;scenarios.revoked=revoked;scenarios.timeout=timeout;
    }else{
      batch=clone(evidence.batch);
      exemplarKeys.forEach(key=>{scenarios[key]=clone(evidence.scenarios[key]);});
    }
    page=0;renderBatch();renderCases(apiAvailable);
    setRunState('success',apiAvailable?'Demonstration executed.':'Recorded evidence replayed.',apiAvailable?'The displayed batch and three case outcomes came from the local Python engine.':'Static hosting does not execute Python; every displayed result is labeled recorded engine evidence.');
    toast(apiAvailable?'Recovery demonstration executed by Python.':'Recorded engine evidence replayed; no live execution was claimed.');
    document.querySelector('#cases').scrollIntoView({behavior:'smooth',block:'start'});
  }catch(error){
    setRunState('error','Demonstration could not be refreshed.',error.message+' Previous verified evidence remains visible.');
    toast(error.message+'. Previous evidence remains visible.');
  }finally{button.disabled=false;button.textContent=apiAvailable?'Run recovery demonstration':'Replay recovery demonstration';}
}
$('run-demo').addEventListener('click',runDemonstration);
$('export-batch').addEventListener('click',()=>batch&&download(batch,'mandateguard-batch-evidence.json'));
$('run-boundary').addEventListener('click',async()=>{
  const button=$('run-boundary');button.disabled=true;
  const key=selectedBoundary;
  try{
    const result=apiAvailable?await request('scenario',{scenario:key}):clone(evidence.scenarios[key]);
    scenarios[key]=result;
    if(apiAvailable) liveScenarios.add(key);
    if(selectedBoundary===key){boundaryScenario=result;renderBoundary();}
    toast(apiAvailable?'Boundary check executed by Python.':'Recorded boundary evidence replayed.');
  }catch(error){toast(error.message+'. Previous boundary evidence remains visible.');}
  finally{button.disabled=false;button.textContent=apiAvailable?'Run boundary check':'Replay recorded boundary check';}
});
$('export-boundary').addEventListener('click',()=>boundaryScenario&&download(boundaryScenario,'mandateguard-'+selectedBoundary+'-evidence.json'));

async function init(){
  document.querySelectorAll('main button').forEach(button=>button.disabled=true);
  try{
    const response=await fetch('./evidence.json');
    if(!response.ok) throw new Error('Evidence file could not be loaded.');
    evidence=await response.json();batch=evidence.batch;
    Object.keys(evidence.scenarios).forEach(key=>{scenarios[key]=evidence.scenarios[key];});
    boundaryScenario=scenarios[selectedBoundary];
    try{
      const health=await fetch('./api/health',{signal:AbortSignal.timeout(2500)});
      apiAvailable=health.ok && (await health.json()).mode==='local_simulator';
    }catch{apiAvailable=false;}
    $('mode').textContent=apiAvailable?'Python engine connected':'Recorded engine evidence';
    $('run-demo').textContent=apiAvailable?'Run recovery demonstration':'Replay recovery demonstration';
    document.querySelectorAll('main button').forEach(button=>button.disabled=false);
    renderBatch();renderCases(false);renderBoundaryList();renderBoundary(false);renderPolicies();renderProof();
    setRunState('success',apiAvailable?'Python engine connected.':'Recorded evidence loaded.',apiAvailable?'Use the primary action to execute the batch and three decisive cases through the shared engine.':'This static view replays exported engine results and does not pretend to execute Python.');
  }catch(error){
    $('load-error').hidden=false;
    $('load-error').textContent=error.message+' Serve this folder over HTTP or regenerate public/evidence.json with scripts/build_showcase.py.';
    $('mode').textContent='Evidence unavailable';
    setRunState('error','Evidence unavailable.',error.message);
  }
}
init();
