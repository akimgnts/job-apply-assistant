const $=id=>document.getElementById(id);
let target, snapshot, plan, applications=[];
const status=message=>{$('status').textContent=message;};
const origin=()=>$('server').value;

// Requests execute inside the authenticated Job Apply tab. No password/token
// is stored in the extension or exposed to a job board.
async function api(path, method='GET', body=null, binary=false) {
  if (!/^\/api\/(workflow\/applications(?:\/\d+)?|applications(?:\/\d+)?|preparation\/applications\/\d+|extension\/plan|documents\/\d+\/pdf)$/.test(path)) throw new Error('Action non autorisée.');
  const tabs=await chrome.tabs.query({url:origin()+'/*'});
  const tab=tabs[0];
  if (!tab) {await chrome.tabs.create({url:origin()});throw new Error('Connectez-vous à Job Apply dans l’onglet ouvert, puis revenez au formulaire et reconnectez l’espace.');}
  const [response]=await chrome.scripting.executeScript({target:{tabId:tab.id},func:async (path,method,body,binary)=>{
    try {
      const r=await fetch(path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
      if(!r.ok) return {error:r.status===401?'Connectez-vous à votre espace Job Apply.':`Action impossible (${r.status}). Ouvrez le dossier dans Job Apply pour vérifier son état.`};
      if(!binary)return {data:await r.json()};
      const buffer=await r.arrayBuffer();
      if(buffer.byteLength>15*1024*1024)return {error:'Document trop volumineux.'};
      const bytes=new Uint8Array(buffer);let encoded='';for(let i=0;i<bytes.length;i+=8192)encoded+=String.fromCharCode(...bytes.subarray(i,i+8192));
      return {data:{base64:btoa(encoded),mime:'application/pdf'}};
    }catch{return {error:'Connexion à Job Apply indisponible.'};}
  },args:[path,method,body,binary]});
  if(response.result.error)throw new Error(response.result.error);
  return response.result.data;
}
function option(value,text){const o=document.createElement('option');o.value=value;o.textContent=text;return o;}
async function loadApplications(selected) {
  applications=(await api('/workflow/applications')).items;
  $('application').replaceChildren(option('','Choisir un dossier'),...applications.map(a=>option(a.id,`${a.company||'Entreprise à préciser'} · ${a.job_title||'Poste à préciser'}`)));
  if(selected)$('application').value=selected;
  updateDocuments();
}
function updateDocuments(){
  plan=null;$('answers').replaceChildren();$('fill').disabled=true;
  const app=applications.find(a=>String(a.id)===$('application').value);
  $('document').replaceChildren(...(app?.documents||[]).filter(d=>d.type!=='mail').map(d=>option(d.id,d.type==='cv'?'CV · dernière version':'Lettre · dernière version')));
  $('attach').disabled=!app?.documents.length || !snapshot?.fields.some(f=>f.type==='file');
}
async function targetTab(){
  const saved=await chrome.storage.session.get('targetTab');
  target=saved.targetTab;
  if(!target)throw new Error('Cliquez sur l’icône de l’extension depuis le formulaire voulu.');
  const tab=await chrome.tabs.get(target);
  if(!/^https?:/.test(tab.url||'') || new URL(tab.url).origin===origin())throw new Error('Ouvrez l’offre ou le formulaire du recruteur, puis cliquez sur l’extension.');
  return target;
}
async function verifyTarget(){
  const saved=await chrome.storage.session.get('targetTab');
  if(saved.targetTab!==target)throw new Error('Vous avez changé de formulaire. Relisez-le avant de remplir.');
}
async function readForm(){
  const tabId=await targetTab();
  await chrome.scripting.executeScript({target:{tabId},files:['form.js']});
  const [read]=await chrome.scripting.executeScript({target:{tabId},func:()=>globalThis.jobApplyForm.scan()});
  snapshot=read.result;
  $('title').value=snapshot.title.slice(0,255);
  $('upload-field').replaceChildren(...snapshot.fields.filter(f=>f.type==='file').map(f=>option(f.id,f.label||'Pièce jointe')));
  return snapshot;
}
async function guarded(button,action){button.disabled=true;try{await action();}catch(e){status(e.message);}finally{button.disabled=false;}}
$('connect').onclick=e=>guarded(e.target,async()=>{await loadApplications();status('Espace connecté. Choisissez votre dossier.');});
$('application').onchange=updateDocuments;
$('server').onchange=()=>{applications=[];snapshot=null;plan=null;updateDocuments();};
$('prepare').onclick=e=>guarded(e.target,async()=>{
  const id=$('application').value;if(!id)throw new Error('Choisissez un dossier.');
  status('Analyse et préparation en cours… Gardez ce panneau ouvert.');
  const result=await api(`/preparation/applications/${id}`,'POST');
  await loadApplications(id);status(result.missing.length?'Certaines pièces restent à préparer dans Job Apply.':'CV, lettre et email disponibles. Relisez-les dans Job Apply.');
});
$('import').onclick=e=>guarded(e.target,async()=>{
  const company=$('company').value.trim(),title=$('title').value.trim();
  if(!company||!title)throw new Error('Renseignez l’entreprise et le poste avant l’import.');
  const read=await readForm();
  const existing=applications.find(a=>a.source_url===read.url);
  if(existing){$('application').value=existing.id;updateDocuments();status('Cette offre est déjà dans votre pipeline.');return;}
  const row=await api('/applications','POST',{company,job_title:title,source_url:read.url,raw_offer:read.text});
  await loadApplications(row.id);status('Offre ajoutée au pipeline. Préparez les pièces du dossier.');
});
$('scan').onclick=e=>guarded(e.target,async()=>{
  const id=$('application').value;if(!id)throw new Error('Choisissez le dossier correspondant à cette offre.');
  plan=null;$('fill').disabled=true;
  const read=await readForm();
  status('Lecture du formulaire et recherche des preuves du profil…');
  plan=await api('/extension/plan','POST',{application_id:Number(id),fields:read.fields});
  $('answers').replaceChildren();
  for(const answer of plan.answers){
    const field=read.fields.find(f=>f.id===answer.id),wrap=document.createElement('label');wrap.textContent=field.label||field.name;
    const input=document.createElement(field.type==='textarea'?'textarea':'input');input.value=answer.value;input.dataset.field=answer.id;
    const proof=document.createElement('small');proof.textContent=answer.evidence;
    wrap.append(input,proof);$('answers').append(wrap);
  }
  for(const pending of plan.pending){const p=document.createElement('p');p.className='pending';p.textContent=`${read.fields.find(f=>f.id===pending.id)?.label||'Champ'} : ${pending.reason}`;$('answers').append(p);}
  $('fill').disabled=!plan.answers.length;
  $('attach').disabled=!$('document').value || !read.fields.some(f=>f.type==='file');
  status(`${plan.answers.length} proposition(s) à relire. ${plan.pending.length} champ(s) conservés ou à compléter.${read.embeddedForms?' Des formulaires intégrés peuvent nécessiter une saisie manuelle.':''}`);
});
$('fill').onclick=e=>guarded(e.target,async()=>{
  if(!plan||!snapshot)throw new Error('Relisez d’abord le formulaire.');
  await verifyTarget();
  const answers=[...$('answers').querySelectorAll('[data-field]')].map(el=>({id:el.dataset.field,value:el.value}));
  const [r]=await chrome.scripting.executeScript({target:{tabId:target},func:(url,answers)=>globalThis.jobApplyForm.apply(url,answers),args:[snapshot.url,answers]});
  status(`${r.result.applied.length} champ(s) remplis ; ${r.result.skipped.length} ignorés car modifiés ou déjà renseignés. Vérifiez le formulaire avant de poursuivre.`);
});
$('attach').onclick=e=>guarded(e.target,async()=>{
  if(!snapshot||!$('upload-field').value||!$('document').value)throw new Error('Relisez le formulaire et choisissez le document ainsi que son champ.');
  await verifyTarget();
  const documentId=$('document').value;
  const file=await api(`/documents/${documentId}/pdf`,'GET',null,true);
  const app=applications.find(a=>String(a.id)===$('application').value);
  const doc=app?.documents.find(d=>String(d.id)===documentId);
  if(!doc)throw new Error('Document étranger au dossier sélectionné.');
  const filename=`${doc.type}_${app.id}.pdf`;
  await chrome.scripting.executeScript({target:{tabId:target},func:(url,file)=>globalThis.jobApplyForm.apply(url,[],file),args:[snapshot.url,{...file,filename,fieldId:$('upload-field').value}]});
  status('PDF joint. Vérifiez le fichier affiché sur le formulaire du recruteur.');
});
