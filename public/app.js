'use strict';
const $ = id => document.getElementById(id);
const money = value => new Intl.NumberFormat('en-IN', {style:'currency',currency:'INR',maximumFractionDigits:0}).format(value);
const esc = value => String(value ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const human = value => String(value || 'Unknown').toLowerCase().replaceAll('_',' ').replace(/^./, c => c.toUpperCase());
const labels = {B0:'No intervention',B1:'Ungated retry','B1.5':'Reason-aware retry',RZP:'Fixed card reference','B2.25':'Timing only','B2.5':'Timing + attempts','B2.75':'Timing + attempts + consent',B2:'Full guardrails',B3:'Guardrails + interpreter'};
const outcomes = ['Recovered','Human review','Stopped','Awaiting outcome'];
const tones = ['recovered','review','stopped','awaiting'];
let evidence, batch, scenario, selectedScenario = 'recover', activeStatus = 'all', page = 0, currentReceipt, apiAvailable = false;
let toastTimer;
function toast(message) { $('toast').textContent = message; $('toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('toast').classList.remove('visible'), 5000); }
function status(row) {
  if (row.provider_timed_out || ['abstain','escalate'].includes(row.decision) || row.final_action === 'escalate_to_human') return 'Human review';
  if (row.provider_postcondition_state === 'RECOVERED') return 'Recovered';
  return row.provider_call_made ? 'Awaiting outcome' : 'Stopped';
}
function badge(value) { const tone = value === 'Recovered' ? 'good' : value === 'Human review' ? 'warn' : value === 'Awaiting outcome' ? 'blue' : ''; return '<span class="badge '+tone+'">'+esc(value)+'</span>'; }
function download(value, filename) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+'\n'], {type:'application/json'}));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function navigate(name) {
  if (!['recovery','lab','policies','proof'].includes(name)) name = 'recovery';
  document.querySelectorAll('.page').forEach(el => el.hidden = el.id !== 'page-'+name);
  document.querySelectorAll('[data-page]').forEach(el => {el.classList.toggle('active',el.dataset.page === name); el.setAttribute('aria-current', el.dataset.page === name ? 'page' : 'false');});
  $('page-name').textContent = {recovery:'Recovery overview',lab:'Failure lab',policies:'Policy comparison',proof:'Razorpay proof'}[name];
  history.replaceState(null,'','#'+name); window.scrollTo({top:0,behavior:'instant'});
}
document.querySelectorAll('[data-page]').forEach(button => button.addEventListener('click',() => navigate(button.dataset.page)));
document.querySelectorAll('[data-go]').forEach(button => button.addEventListener('click',() => navigate(button.dataset.go)));
window.addEventListener('hashchange',() => navigate(location.hash.slice(1)));
async function request(path, data) {
  const response = await fetch('./api/demo/'+path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data || {}), signal:AbortSignal.timeout(30000)});
  if (!response.ok) throw new Error('Engine returned HTTP '+response.status);
  return response.json();
}
function renderBatch() {
  const summary = batch.summaries.find(row => row.arm === 'B3');
  const counts = Object.fromEntries(outcomes.map(s => [s,batch.receipts.filter(row => status(row) === s).length]));
  const stoppedCalls = batch.receipts.filter(row => !row.provider_call_made).reduce((n,row) => n+row.provider_call_count,0);
  const cards = [
    ['Simulated recovery',money(summary.recovered_inr),counts.Recovered+' payments recovered','↗'],
    ['Value protected by denial',money(summary.protected_value_by_denial_inr),'Synthetic prohibited value not sent','◇'],
    ['Human review',String(counts['Human review']),'Uncertainty escalated with evidence','↳'],
    ['Calls on stopped cases',String(stoppedCalls),summary.provider_calls+' total simulated provider calls','✓']
  ];
  $('stats').innerHTML = cards.map((c,i) => '<div class="stat '+(i===0?'first':'')+'"><div class="stat-label">'+c[0]+'<span class="stat-icon">'+c[3]+'</span></div><div class="stat-value">'+esc(c[1])+'</div><div class="stat-detail">'+esc(c[2])+'</div></div>').join('');
  $('distribution').innerHTML = outcomes.map((s,i) => '<span class="'+tones[i]+'" style="width:'+counts[s]/batch.n*100+'%" title="'+esc(s)+': '+counts[s]+'"></span>').join('');
  $('distribution').setAttribute('aria-label',outcomes.map(s => s+': '+counts[s]).join(', '));
  $('outcome-list').innerHTML = outcomes.map((s,i) => '<div class="outcome-row"><span><i class="dot '+tones[i]+'"></i>'+s+'</span><b>'+counts[s]+'</b></div>').join('');
  $('batch-source').textContent = 'Seed '+batch.seed+' · '+batch.regime+' · ledger '+batch.ledger_sha256.slice(0,12)+'…';
  const m = evidence.manifest;
  $('evaluation-size').textContent = (m.seeds.length*m.regimes.length*m.n_per_seed*m.arms.length).toLocaleString()+' policy decisions · '+m.seeds.length+' seeds';
  renderQueue();
}
function renderQueue() {
  const query = $('case-search').value.trim().toLowerCase();
  const rows = batch.receipts.filter(row => (activeStatus === 'all' || status(row) === activeStatus) && (row.case_id+' '+human(row.diagnosed_reason)+' '+row.reason_codes.join(' ')).toLowerCase().includes(query));
  const limit=8, pages=Math.max(1,Math.ceil(rows.length/limit)); page=Math.min(page,pages-1);
  $('queue-count').textContent = rows.length;
  $('queue-body').innerHTML = rows.slice(page*limit,(page+1)*limit).map(row => {
    const caseNo = Number(row.case_id.split('_').pop())+1;
    return '<tr><td class="case-id">MG-'+String(caseNo).padStart(4,'0')+'<small>Scheduled AutoPay</small></td><td>'+esc(human(row.diagnosed_reason))+'</td><td>'+money(row.amount_inr)+'</td><td>'+badge(status(row))+'</td><td class="calls">'+row.provider_call_count+'</td><td><button class="text-button inspect" data-case="'+esc(row.case_id)+'">View receipt ↗</button></td></tr>';
  }).join('') || '<tr><td colspan="6" class="empty">No cases match this filter. Try another status or search.</td></tr>';
  $('page-info').textContent = rows.length ? 'Showing '+(page*limit+1)+'–'+Math.min((page+1)*limit,rows.length)+' of '+rows.length+' cases' : '0 matching cases';
  $('prev').disabled = page===0; $('next').disabled = page>=pages-1;
  document.querySelectorAll('.inspect').forEach(button => button.addEventListener('click',() => openReceipt(batch.receipts.find(row => row.case_id===button.dataset.case))));
}
document.querySelectorAll('[data-status]').forEach(button => button.addEventListener('click',() => {
  activeStatus=button.dataset.status; page=0; document.querySelectorAll('[data-status]').forEach(b => {b.classList.toggle('active', b===button);b.setAttribute('aria-pressed',String(b===button));}); renderQueue();
}));
$('case-search').addEventListener('input',() => {page=0;renderQueue();});
$('prev').addEventListener('click',() => {page--;renderQueue();});
$('next').addEventListener('click',() => {page++;renderQueue();});
$('run-batch').addEventListener('click',async () => {
  const button=$('run-batch');button.disabled=true;button.textContent=apiAvailable?'Running the Python engine…':'Loading exported engine run…';
  try {
    batch=apiAvailable ? await request('batch') : structuredClone(evidence.batch);
    page=0;renderBatch();toast(apiAvailable?'Batch executed: 100 cases, 9 policies, one frozen ledger.':'Exported engine run replayed. Static hosting does not execute Python.');
  } catch (error) {toast(error.message+'. Previous results remain visible.');}
  finally {button.disabled=false;button.textContent=apiAvailable?'▶ Run recovery batch':'↻ Replay recovery batch';}
});
$('export-batch').addEventListener('click',() => download(batch,'mandateguard-batch-evidence.json'));
function openReceipt(row) {
  currentReceipt=row; $('receipt-title').textContent='MG-'+String(Number(row.case_id.split('_').pop())+1).padStart(4,'0');
  const facts=[['Outcome',status(row)],['Recovered (simulated)',money(row.recovered_inr)],['Provider calls',row.provider_call_count],['Mandate state',row.mandate_state],['Interpretation',human(row.diagnosed_reason)],['Confidence',Math.round(row.confidence*100)+'%'],['Provider postcondition',row.provider_postcondition_state || 'No provider action'],['Legitimate recovery forgone',money(row.legitimate_recovery_forgone_inr)]];
  $('receipt-content').innerHTML='<div class="receipt-facts">'+facts.map(([k,v])=>'<div><small>'+esc(k)+'</small><strong>'+esc(v)+'</strong></div>').join('')+'</div><div class="trace">'+row.audit_events.map(event=>'<div class="trace-item"><span>'+event.sequence+'</span><div><strong>'+esc(human(event.event_type))+'</strong><p>'+esc(event.reason_codes.join(' · '))+'</p><p>Provider call: '+event.provider_call_made+'</p></div></div>').join('')+'</div><details><summary>Raw receipt, idempotency key and audit hashes</summary><pre>'+esc(JSON.stringify(row,null,2))+'</pre></details>';
  $('verify-result').textContent='';$('receipt-dialog').showModal();
}
$('close-dialog').addEventListener('click',()=>$('receipt-dialog').close());
$('receipt-dialog').addEventListener('click',event=>{if(event.target===$('receipt-dialog')){const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();}});
$('export-receipt').addEventListener('click',()=>download(currentReceipt,'mandateguard-receipt.json'));
// AuditChain uses Python's sorted JSON with its default separators and ASCII escaping.
function pythonJson(value) {
  if (value===null || typeof value !=='object') return JSON.stringify(value).replace(/[\u007f-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
  if (Array.isArray(value)) return '['+value.map(pythonJson).join(', ')+']';
  return '{'+Object.keys(value).sort().map(k=>pythonJson(k)+': '+pythonJson(value[k])).join(', ')+'}';
}
async function digest(text) {return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,'0')).join('');}
async function verifyChain(events) {
  if (!events.length) return false;
  let previous='GENESIS';
  for (const event of events) {
    const {event_hash,...body}=event;
    if (body.previous_hash!==previous || await digest(pythonJson(body))!==event_hash) return false;
    previous=event_hash;
  }
  return true;
}
$('verify-receipt').addEventListener('click',async()=>{
  try {
    const valid=await verifyChain(currentReceipt.audit_events);
    const tampered=structuredClone(currentReceipt.audit_events);tampered[0].decision='tampered';
    const detects=!(await verifyChain(tampered));
    $('verify-result').textContent=valid&&detects?'Verified in this browser: every hash matches; editing a decision breaks the chain.':'Verification failed: this receipt must not be trusted.';
  } catch { $('verify-result').textContent='Browser cryptography unavailable. Use HTTPS or localhost, or verify with the Python demo.'; }
});
function renderScenarios() {
  $('scenario-list').innerHTML=['recover','revoked','optout','notice','ambiguous','forged','timeout'].map(key=>{const value=evidence.scenarios[key];return '<button class="scenario '+(key===selectedScenario?'active':'')+'" data-scenario="'+key+'" aria-pressed="'+(key===selectedScenario)+'">'+esc(value.title)+'<small>'+esc(value.description)+'</small></button>';}).join('');
  document.querySelectorAll('[data-scenario]').forEach(button=>button.addEventListener('click',()=>{selectedScenario=button.dataset.scenario;scenario=evidence.scenarios[selectedScenario];renderScenarios();renderScenario(false);}));
}
function renderScenario(live) {
  const row=scenario.receipt;
  $('scenario-title').textContent=scenario.title;$('scenario-description').textContent=scenario.description;
  $('scenario-mode').textContent=live?'JUST EXECUTED · LOCAL PYTHON ENGINE':'EXPORTED PYTHON ENGINE RESULT';
  const steps=[['Authenticate',scenario.ingress.accepted?'HMAC verified over the signed fixture bytes.':scenario.ingress.reason_code],
    ['Interpret',row?human(row.diagnosed_reason)+(row.interpreter_consulted?' · deterministic bounded interpreter':' · deterministic reason mapping'):'Not reached'],
    ['Authorize',row?row.reason_codes.map(human).join(' · '):'Not reached'],
    ['Provider outcome',row?.provider_postcondition_state || 'No provider action'],
    ['Evidence',row?(row.audit_verified?'Audit chain verified by Python':'Audit verification failed'):'Rejected body hash: '+scenario.ingress.body_sha256]];
  $('scenario-result').innerHTML='<div class="verdict"><div><small>FINAL OUTCOME</small><strong>'+esc(scenario.status)+'</strong>'+(row?'<small>'+money(row.recovered_inr)+' recovered · simulated</small>':'')+'</div><div><strong class="call-number">'+scenario.provider_call_count+'</strong><small>provider calls</small></div></div><div class="trace">'+steps.map(([name,text],i)=>'<div class="trace-item"><span>'+String(i+1).padStart(2,'0')+'</span><div><strong>'+name+'</strong><p>'+esc(text)+'</p></div></div>').join('')+'</div>'+(scenario.scenario==='timeout'?'<div class="notice">One call was attempted. Its outcome is unknown. This is human review, not a claim that no payment happened.</div>':'');
  $('run-scenario').textContent=apiAvailable?'Run scenario ↗':'Replay engine evidence ↗';
}
$('run-scenario').addEventListener('click',async()=>{
  const button=$('run-scenario');button.disabled=true;
  try {scenario=apiAvailable?await request('scenario',{scenario:selectedScenario}):evidence.scenarios[selectedScenario];renderScenario(apiAvailable);toast(apiAvailable?'Scenario executed by Python.':'Showing exported Python evidence; no new execution on static hosting.');}
  catch(error){toast(error.message+'. Previous evidence retained.');}finally{button.disabled=false;}
});
$('export-scenario').addEventListener('click',()=>download(scenario,'mandateguard-'+selectedScenario+'.json'));
function renderPolicies() {
  const regime=$('regime').value;
  const rows=evidence.manifest.arms.map(arm=>evidence.aggregate.find(row=>row.arm===arm&&row.regime===regime));
  const max=Math.max(...rows.flatMap(row=>[row.incremental_recovered_inr.mean,row.realized_harm_inr.mean]),1);
  $('policy-bars').innerHTML=rows.map(row=>'<div class="bar-row"><div class="bar-label"><b>'+esc(row.arm)+'</b><small>'+esc(labels[row.arm])+'</small></div><div class="bar-pair"><span style="background:var(--teal);width:'+row.incremental_recovered_inr.mean/max*100+'%"></span><span style="background:var(--red);width:'+row.realized_harm_inr.mean/max*100+'%"></span></div><div class="bar-value"><span>'+money(row.incremental_recovered_inr.mean)+'</span><span>'+money(row.realized_harm_inr.mean)+'</span></div></div>').join('');
  $('policy-table').innerHTML=rows.map(row=>'<tr><td><b>'+esc(row.arm)+'</b></td>'+['incremental_recovered_inr','legitimate_recovery_forgone_inr','realized_harm_inr'].map(key=>'<td>'+money(row[key].mean)+'</td>').join('')+'<td>'+row.violations.mean.toFixed(1)+'</td></tr>').join('');
  const model=$('price-model').value, curve=evidence.sensitivity.per_regime[regime][model];
  $('price-curve').innerHTML='<div class="price-grid">'+curve.map(point=>'<div class="price-point '+(['B2','B3'].includes(point.recommended_arm)?'guarded':'')+'"><small>'+(model==='harm_multiplier_curve'?point.harm_multiplier+'× harm':money(point.violation_cost_inr)+'/breach')+'</small><b>'+point.recommended_arm+'</b><span>'+money(point.net_value_by_arm_inr[point.recommended_arm])+' net</span></div>').join('')+'</div>';
}
$('regime').addEventListener('change',renderPolicies);$('price-model').addEventListener('change',renderPolicies);
function renderProof() {
  const p=evidence.provider_proofs, proof=p.artifacts.recovery_proof.proof, blocked=p.artifacts.safe_block_zero_write, verified=p.summary.recovery_verified;
  $('proof-cards').innerHTML='<article class="card"><p class="eyebrow">01 · CAPTURED RECOVERY</p><span class="badge '+(verified?'good':'bad')+'">'+(verified?'Saved proof hash verified':'Proof verification failed')+'</span><div class="proof-amount">'+money(proof.amount_minor/100)+'</div><h2>Captured in Razorpay Test Mode</h2><p>Independent payment verification is bound to the original recovery case and Payment Link action.</p><small class="muted">'+esc(proof.payment_id)+'</small></article><article class="card"><p class="eyebrow">02 · ALREADY PAID</p><span class="badge '+(p.summary.already_paid_zero_write_verified?'good':'bad')+'">'+(p.summary.already_paid_zero_write_verified?'Captured zero-write evidence':'Evidence incomplete')+'</span><div class="proof-amount">'+blocked.payment_links_before+' → '+blocked.payment_links_after+'</div><h2>No new fallback link</h2><p>The saved run found an already-paid order and stopped before creating another collection object.</p><small class="muted">'+esc(blocked.order_id)+'</small></article>';
  $('proof-json').textContent=JSON.stringify(p.artifacts,null,2);
  $('model-evidence').textContent=JSON.stringify(evidence.real_interpreter_evidence,null,2);
}
$('export-proof').addEventListener('click',()=>download(evidence.provider_proofs,'mandateguard-captured-testmode-proof.json'));
async function init() {
  for(const button of document.querySelectorAll('main button'))button.disabled=true;
  try {
    const response=await fetch('./evidence.json');if(!response.ok)throw new Error('Evidence file could not be loaded.');
    evidence=await response.json();batch=evidence.batch;scenario=evidence.scenarios.recover;
    try {const health=await fetch('./api/health',{signal:AbortSignal.timeout(2500)});apiAvailable=health.ok&&(await health.json()).mode==='local_simulator';}catch{apiAvailable=false;}
    $('mode').textContent=apiAvailable?'Python engine connected':'Recorded engine evidence';
    $('run-batch').textContent=apiAvailable?'▶ Run recovery batch':'↻ Replay recovery batch';
    for(const button of document.querySelectorAll('main button'))button.disabled=false;
    renderBatch();renderScenarios();renderScenario(false);renderPolicies();renderProof();navigate(location.hash.slice(1));
  } catch(error) {
    $('load-error').hidden=false;$('load-error').textContent=error.message+' Serve this folder over HTTP, or run python scripts/build_showcase.py to regenerate the evidence.';
    $('mode').textContent='Evidence unavailable';
  }
}
init();
