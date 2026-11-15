/* Runs only after the user invokes the extension on the target tab. No network. */
(() => {
  if (globalThis.jobApplyForm) return;
  const entries = new Map();
  let counter = 0;
  const visible = el => !el.disabled && !el.readOnly && el.getClientRects().length > 0 && !el.closest('[hidden],[aria-hidden="true"]');
  const label = el => ([...(el.labels || [])].map(x => x.innerText).join(' ') || el.getAttribute('aria-label') || document.getElementById(el.getAttribute('aria-labelledby'))?.innerText || el.placeholder || el.name || '').trim().slice(0, 500);
  function scan() {
    entries.clear();
    const fields = [];
    for (const el of document.querySelectorAll('input,textarea,select,[role="combobox"]')) {
      if (!visible(el) || ['hidden','submit','button','reset','image'].includes(el.type)) continue;
      const detected = el.tagName === 'TEXTAREA' ? 'textarea' : el.tagName === 'SELECT' ? 'select' : el.getAttribute('role') === 'combobox' ? 'custom' : el.type || 'text';
      const type = ['text','email','tel','url','number','date','textarea','select','file','checkbox','radio','password','hidden','custom'].includes(detected) ? detected : 'custom';
      const id = `field-${++counter}`;
      const field = {id, label:label(el), name:(el.name || '').slice(0,200), type, autocomplete:(el.autocomplete || '').slice(0,100), required:el.required || el.getAttribute('aria-required') === 'true', filled:type === 'file' ? Boolean(el.files?.length) : ['checkbox','radio'].includes(type) ? el.checked : Boolean(el.value), options:el.tagName === 'SELECT' ? [...el.options].map(o=>o.text.slice(0,300)).slice(0,100) : []};
      entries.set(id, {el, label:field.label});
      fields.push(field);
      if (fields.length === 80) break;
    }
    const article = document.querySelector('main,[role="main"],article') || document.body;
    return {url:location.href, title:document.title, text:(article.innerText || '').slice(0,22000), fields, embeddedForms:document.querySelectorAll('iframe').length};
  }
  function apply(url, answers, attachment) {
    if (location.href !== url) throw new Error('La page a changé. Relisez le nouveau formulaire.');
    const applied=[], skipped=[];
    for (const answer of answers) {
      const entry = entries.get(answer.id);
      if (!entry || !visible(entry.el) || entry.label !== label(entry.el)) {skipped.push(answer.id);continue;}
      const el=entry.el;
      if (el.value || ['checkbox','radio','password','hidden','file','submit'].includes(el.type) || el.getAttribute('role') === 'combobox') {skipped.push(answer.id);continue;}
      if (el.tagName === 'SELECT') {
        const option=[...el.options].find(o=>o.value===answer.value || o.text===answer.value);
        if (!option) {skipped.push(answer.id);continue;}
        el.value=option.value;
      } else {
        const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;
        Object.getOwnPropertyDescriptor(proto,'value').set.call(el,String(answer.value));
      }
      el.dispatchEvent(new Event('input',{bubbles:true}));
      el.dispatchEvent(new Event('change',{bubbles:true}));
      applied.push(answer.id);
    }
    if (attachment) {
      const entry=entries.get(attachment.fieldId);
      if (!entry || entry.el.type!=='file' || entry.el.files.length || !visible(entry.el)) throw new Error('Champ de pièce jointe indisponible ou déjà renseigné.');
      const bytes=Uint8Array.from(atob(attachment.base64), c=>c.charCodeAt(0));
      const file=new File([bytes],attachment.filename,{type:attachment.mime});
      const max=15*1024*1024;
      if (file.size>max) throw new Error('Document trop volumineux.');
      const transfer=new DataTransfer();transfer.items.add(file);entry.el.files=transfer.files;
      entry.el.dispatchEvent(new Event('change',{bubbles:true}));
      applied.push(attachment.fieldId);
    }
    // No clicks, navigation, submit(), requestSubmit(), or event on submit buttons.
    return {applied,skipped};
  }
  globalThis.jobApplyForm={scan,apply};
})();
