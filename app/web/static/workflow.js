'use strict';

Object.assign(labels, {
  applied: 'Candidaté',
  received: 'Réception confirmée',
  replied: 'Réponse reçue',
  interview: 'Entretien',
  rejected: 'Refus'
});

const workflowStatusOrder = ['saved','analyzed','generated','applied','received','replied','interview','rejected','archived'];
const workflowStatusLabels = workflowStatusOrder.reduce((acc, key) => ({...acc, [key]: labels[key] || key}), {});
const todayISO = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
const wfApi = async (path, options = {}) => api(path, options);
const wfPost = (path, payload = {}) => wfApi(path, {method: 'POST', body: JSON.stringify(payload)});

function installDailyNav() {
  if ($('[data-nav="daily"]')) return;
  nav.splice(1, 0, ['daily', 'clock', 'Offres du jour']);
  const link = document.createElement('a');
  link.href = '#daily';
  link.dataset.nav = 'daily';
  link.className = 'nav-link';
  link.innerHTML = `${icon('clock')}<span>Offres du jour</span>`;
  $('[data-nav="offers"]')?.before(link);
}

function actionLabel(row) {
  if (row.follow_up_due) return 'Relance';
  if (row.status === 'generated') return 'Envoyer';
  if (row.status === 'applied' || row.status === 'received') return 'Attendre';
  if (row.status === 'replied') return 'Lire';
  if (row.status === 'interview') return 'Préparer';
  return 'Préparer';
}

async function dailyPage() {
  const dateValue = state.dailyDate || todayISO();
  const payload = await wfApi(`/business-france/daily?${new URLSearchParams({date: dateValue, verify_external: 'true'})}`);
  const offers = payload.offers || [];
  const rows = offers.map(offer => {
    const contact = offer.contact?.email || offer.contact?.name || 'Contact direct non confirmé';
    const availability = offer.external_availability?.official?.length
      ? 'Site entreprise'
      : offer.external_availability?.job_boards?.length
        ? 'Autre job board'
        : offer.external_availability?.status === 'checked'
          ? 'Business France seulement'
          : 'À vérifier';
    return `<tr>
      <td><div class="table-job">${logo(offer.company)}<button data-action="daily-offer" data-date="${esc(dateValue)}" data-id="${offer.id}"><strong>${esc(offer.title)}</strong><small>${esc(offer.company)} · ${esc([offer.city, offer.country].filter(Boolean).join(', '))}</small></button></div></td>
      <td><span class="badge ${offer.priority === 'top' ? 'generated' : 'saved'}">${esc(offer.priority || 'standard')}</span></td>
      <td class="hide-mobile"><strong>${offer.match_score ?? '—'}</strong><span class="muted"> /100</span></td>
      <td class="hide-mobile">${esc(contact)}</td>
      <td class="hide-mobile">${esc(availability)}</td>
      <td><button class="icon-button" data-action="daily-import" data-date="${esc(dateValue)}" data-id="${offer.id}" aria-label="Créer le dossier">${icon('briefcase')}</button></td>
    </tr>`;
  }).join('');
  return heading('OFFRES DU JOUR', 'Business France, prêt à traiter', 'Les offres du jour sont classées pour décider vite : top, contact, lien source et disponibilité hors Business France.',
    `<input id="daily-date" type="date" value="${esc(dateValue)}" aria-label="Date des offres"><button class="btn" data-action="daily-refresh">${icon('refresh')}Actualiser</button>`) +
    (payload.warning ? `<div class="archive-notice">${icon('info')}${esc(payload.warning)}</div>` : '') +
    `<section class="metrics">
      <div class="metric"><div class="metric-top"><span>Offres trouvées</span>${icon('radar')}</div><div class="metric-number">${number(payload.total || offers.length)}</div><div class="metric-caption">Business France · ${esc(payload.date)}</div></div>
      <div class="metric"><div class="metric-top"><span>Top à traiter</span>${icon('spark')}</div><div class="metric-number">${number(offers.filter(o => o.priority === 'top').length)}</div><div class="metric-caption">Score indicatif profil/marché</div></div>
      <div class="metric"><div class="metric-top"><span>Contacts directs</span>${icon('mail')}</div><div class="metric-number">${number(offers.filter(o => o.contact?.email).length)}</div><div class="metric-caption">Source conservée dans le dossier</div></div>
      <div class="metric"><div class="metric-top"><span>Vérification externe</span>${icon('external')}</div><div class="metric-number">${payload.verified_external ? 'Oui' : 'Non'}</div><div class="metric-caption">${payload.cached ? 'Cache local' : 'Scan demandé'}</div></div>
    </section>
    <section class="panel">
      <div class="toolbar">${searchInput('Filtrer les offres du jour…')}<span class="muted">${number(offers.length)} offres exploitables</span></div>
      ${offers.length ? `<div class="table-wrap"><table><thead><tr><th>Offre</th><th>Priorité</th><th class="hide-mobile">Match</th><th class="hide-mobile">Contact</th><th class="hide-mobile">Autre source</th><th>Dossier</th></tr></thead><tbody>${rows}</tbody></table></div>` : empty('radar', 'Aucune offre trouvée pour cette date', 'Essaie une autre date ou vérifie la clé Business France dans les réglages.')}
    </section>`;
}

async function workflowApplicationsPage() {
  if (state.applicationView === 'tracking') return trackingPage();
  const data = await wfApi('/workflow/applications');
  const rows = (data.items || []).filter(row => {
    const haystack = `${row.company || ''} ${row.job_title || ''} ${row.status || ''}`.toLowerCase();
    return !state.q || haystack.includes(state.q.toLowerCase());
  });
  const metrics = [
    ['briefcase', 'Dossiers', rows.length, 'Candidatures visibles'],
    ['file', 'Documents prêts', rows.filter(r => r.documents?.length >= 3).length, 'CV, lettre, mail'],
    ['mail', 'Emails liés', rows.reduce((sum, r) => sum + (r.email_count || 0), 0), 'Gmail / réception'],
    ['clock', 'Relances', rows.filter(r => r.follow_up_due).length, 'À traiter maintenant']
  ];
  return heading('PIPELINE CANDIDATURE', 'À traiter, candidaté, relancé', 'Une vue courte pour agir vite : préparer le dossier, marquer candidaté, relier les mails et passer à la suite.',
    btn('Nouvelle candidature', 'create')) + applicationTabs() +
    `<section class="metrics">${metrics.map(([i,l,n,c]) => `<div class="metric"><div class="metric-top"><span>${l}</span>${icon(i)}</div><div class="metric-number">${number(n)}</div><div class="metric-caption">${c}</div></div>`).join('')}</section>
    <section class="gmail-connection"><span class="connection-mark">${icon('mail')}</span><div><strong>${data.gmail?.mailbox || 'Gmail lecture seule'}</strong><p>${data.gmail?.configured ? `Dernière synchro : ${date(data.gmail.last_sync)}` : 'Non configuré. Les dossiers restent utilisables sans Gmail.'}</p></div><button class="btn btn-small" data-action="workflow-sync">${icon('refresh')}Sync</button></section>
    <section class="panel">
      <div class="toolbar">${searchInput('Rechercher une candidature…')}<span class="muted">${number(rows.length)} dossiers</span></div>
      ${rows.length ? `<div class="table-wrap"><table><thead><tr><th>Dossier</th><th>Statut</th><th class="hide-mobile">Action</th><th class="hide-mobile">Documents</th><th class="hide-mobile">Emails</th><th></th></tr></thead><tbody>${rows.map(row => `<tr>
        <td><div class="table-job">${logo(row.company)}<button data-action="workflow-app" data-id="${row.id}"><strong>${esc(row.job_title || 'Offre')}</strong><small>${esc(row.company || 'Entreprise')} · ${row.match_score === null ? 'score à analyser' : `${row.match_score}/10`}</small></button></div></td>
        <td>${badge(row.status)}</td>
        <td class="hide-mobile"><span class="badge ${row.follow_up_due ? 'saved' : 'generated'}">${esc(actionLabel(row))}</span></td>
        <td class="hide-mobile">${number(row.documents?.length || 0)}/3</td>
        <td class="hide-mobile">${number(row.email_count || 0)}</td>
        <td><button class="icon-button" data-action="workflow-app" data-id="${row.id}" aria-label="Ouvrir">${icon('arrow')}</button></td>
      </tr>`).join('')}</tbody></table></div>` : empty('briefcase', 'Aucun dossier à traiter', 'Enregistre une offre du jour ou colle une annonce pour lancer le pipeline.', `<a class="btn btn-primary" href="#daily">${icon('clock')}Voir les offres du jour</a>`)}
    </section>`;
}

async function workflowAppDrawer(id) {
  const version = openDrawer();
  try {
    const row = await wfApi(`/workflow/applications/${id}`);
    if (version !== drawerVersion) return;
    $('#drawer').dataset.kind = 'workflow-app';
    $('#drawer').dataset.id = id;
    const statusOptions = workflowStatusOrder.map(status => `<option value="${status}" ${row.status === status ? 'selected' : ''}>${esc(workflowStatusLabels[status])}</option>`).join('');
    $('#drawer').innerHTML = drawerTop('DOSSIER · WORKFLOW') + `<div class="drawer-title">${logo(row.company)}<div><h2>${esc(row.job_title || 'Candidature')}</h2><p>${esc(row.company || 'Entreprise à préciser')}</p></div></div>
      <div class="flex-between">${badge(row.status)}<select id="workflow-status" data-id="${row.id}" aria-label="Statut">${statusOptions}</select></div>
      <div class="score-box"><span class="score-number">${row.match_score ?? '—'}<span style="font-size:14px">/10</span></span><div><h3>${esc(row.next_action || 'Action suivante')}</h3><p>${row.follow_up_due ? 'Relance à traiter.' : 'Le pipeline reste synchronisé avec vos documents et vos emails liés.'}</p></div></div>
      <div class="drawer-actions">
        ${btn('Préparer / compléter', 'workflow-prepare', 'btn-primary', 'spark', `data-id="${row.id}"`)}
        ${row.status !== 'applied' ? btn('Marquer candidaté', 'workflow-status-action', 'btn', 'check', `data-id="${row.id}" data-status="applied"`) : ''}
        ${row.source_url ? `<a class="btn" href="${esc(safeURL(row.source_url))}" target="_blank" rel="noopener noreferrer">Offre source ${icon('external')}</a>` : ''}
      </div>
      <section class="drawer-section"><h3>Documents</h3>${row.documents?.length ? row.documents.map(doc => `<div class="setting-row"><button class="text-link" data-action="document" data-id="${doc.id}">${icon(doc.type === 'mail' ? 'mail' : 'file')}${esc(docLabels[doc.type] || doc.type)}</button><button class="icon-button" data-action="download" data-id="${doc.id}">${icon('download')}</button></div>`).join('') : '<p>Aucun document prêt. Lance “Préparer / compléter”.</p>'}</section>
      <section class="drawer-section"><h3>Emails liés</h3>${row.emails?.length ? row.emails.map(email => `<button class="offer-row" data-action="workflow-email" data-id="${email.id}"><span class="email-symbol">${icon('mail')}</span><div class="offer-main"><h3>${esc(email.subject || 'Sans objet')}</h3><div class="offer-meta">${esc(email.sender_email || '')} · ${esc(email.classification || 'à vérifier')}</div></div>${icon('chevron')}</button>`).join('') : '<p>Aucun email lié. Utilise la synchronisation Gmail puis rattache les messages entrants.</p>'}</section>
      <section class="drawer-section"><h3>Contacts</h3>${row.contacts?.length ? row.contacts.map(c => `<div class="setting-row"><div><strong>${esc(c.name)}</strong><small>${esc(c.role || '')}</small>${c.email ? `<small>${esc(c.email)}</small>` : ''}</div>${c.linkedin ? `<a class="text-link" href="${esc(safeURL(c.linkedin))}" target="_blank">LinkedIn ${icon('external')}</a>` : ''}</div>`).join('') : '<p>Aucun contact fiable enregistré pour cette entreprise.</p>'}</section>
      <details class="drawer-section"><summary>Texte de l’offre</summary><div class="offer-description mt">${esc(row.raw_offer || '')}</div></details>`;
  } catch (error) {
    if (version === drawerVersion) $('#drawer').innerHTML = drawerTop('DOSSIER') + empty('info', 'Dossier indisponible', esc(error.message));
  }
}

async function dailyOfferDrawer(dateValue, offerId) {
  const version = openDrawer();
  try {
    const payload = await wfApi(`/business-france/daily?${new URLSearchParams({date: dateValue, verify_external: 'true'})}`);
    const offer = (payload.offers || []).find(row => String(row.id) === String(offerId));
    if (!offer) throw new Error('Offre introuvable pour cette date.');
    if (version !== drawerVersion) return;
    const ext = offer.external_availability || {};
    $('#drawer').innerHTML = drawerTop('OFFRE DU JOUR') + `<div class="drawer-title">${logo(offer.company)}<div><h2>${esc(offer.title)}</h2><p>${esc(offer.company)} · ${esc([offer.city, offer.country].filter(Boolean).join(', '))}</p></div></div>
      <div class="detail-grid"><div><small>MATCH</small><strong>${offer.match_score ?? '—'} /100</strong></div><div><small>PRIORITÉ</small><strong>${esc(offer.priority || 'standard')}</strong></div><div><small>CONTACT</small><strong>${esc(offer.contact?.email || offer.contact?.name || 'Non confirmé')}</strong></div><div><small>AUTRE SOURCE</small><strong>${esc(ext.status || 'À vérifier')}</strong></div></div>
      <div class="drawer-actions">${btn('Créer le dossier', 'daily-import', 'btn-primary', 'briefcase', `data-date="${esc(dateValue)}" data-id="${offer.id}"`)}<a class="btn" href="${esc(safeURL(offer.business_france_url))}" target="_blank" rel="noopener noreferrer">Business France ${icon('external')}</a></div>
      <section class="drawer-section"><h3>Pourquoi ça matche</h3>${(offer.match_reasons || []).length ? `<ul>${offer.match_reasons.map(reason => `<li>${esc(reason)}</li>`).join('')}</ul>` : '<p>Score indicatif calculé depuis les mots-clés de l’offre.</p>'}</section>
      <section class="drawer-section"><h3>Disponibilité hors Business France</h3>${[...(ext.official || []), ...(ext.job_boards || []), ...(ext.candidates || [])].length ? [...(ext.official || []), ...(ext.job_boards || []), ...(ext.candidates || [])].map(link => `<div class="setting-row"><strong>${esc(link.label || 'Lien candidat')}</strong><a class="text-link" href="${esc(safeURL(link.url))}" target="_blank">Ouvrir ${icon('external')}</a></div>`).join('') : '<p>Aucun autre lien vérifié automatiquement pour le moment.</p>'}</section>
      <section class="drawer-section"><h3>Description</h3><div class="offer-description">${esc([offer.description, offer.profile].filter(Boolean).join('\n\n'))}</div></section>`;
  } catch (error) {
    if (version === drawerVersion) $('#drawer').innerHTML = drawerTop('OFFRE') + empty('info', 'Offre indisponible', esc(error.message));
  }
}

async function assistantAction(action) {
  const result = await wfPost('/assistant/action', action);
  if (result.navigate?.type === 'open') {
    if (result.navigate.resource === 'applications') await workflowAppDrawer(result.navigate.id);
    else if (result.navigate.resource === 'offers') await detail('offer', result.navigate.id);
    else if (result.navigate.resource === 'companies') await detail('company', result.navigate.id);
    else toast(result.message || 'Élément trouvé.');
  } else {
    toast(result.message || 'Action effectuée.');
    if (result.application) await workflowAppDrawer(result.application.id);
    await render({preserveFocus: true});
  }
}

function installAssistant() {
  if ($('#assistant-float')) return;
  document.body.insertAdjacentHTML('beforeend', `<section id="assistant-float" class="assistant-float collapsed" aria-label="Assistant JobApply">
    <button class="assistant-bubble" data-assistant="toggle" aria-label="Ouvrir l’assistant">${icon('spark')}</button>
    <div class="assistant-panel" role="dialog" aria-label="Assistant JobApply">
      <div class="assistant-head"><strong>Assistant JobApply</strong><button class="icon-button" data-assistant="toggle" aria-label="Fermer">${icon('close')}</button></div>
      <div class="assistant-log" id="assistant-log"><p>Pose une question sur tes offres, contacts, dossiers, emails ou documents. Les actions sensibles passent par un bouton.</p></div>
      <form id="assistant-form"><input id="assistant-input" autocomplete="off" placeholder="Ex. qu’est-ce que je dois traiter maintenant ?"><button class="btn btn-primary" type="submit">${icon('arrow')}</button></form>
    </div>
  </section>`);
}

function addAssistantMessage(role, html) {
  const log = $('#assistant-log');
  const node = document.createElement('div');
  node.className = `assistant-message ${role}`;
  node.innerHTML = html;
  log.append(node);
  log.scrollTop = log.scrollHeight;
}

installDailyNav();
pages.daily = dailyPage;
pages.applications = workflowApplicationsPage;
installAssistant();
navigate();

document.addEventListener('click', async event => {
  const actionEl = event.target.closest('[data-action]');
  if (actionEl && !actionEl.disabled) {
    try {
      switch (actionEl.dataset.action) {
        case 'daily-refresh':
          state.dailyDate = $('#daily-date')?.value || todayISO();
          await render({preserveFocus: true});
          return;
        case 'daily-offer':
          await dailyOfferDrawer(actionEl.dataset.date, actionEl.dataset.id);
          return;
        case 'daily-import': {
          actionEl.disabled = true;
          const app = await wfPost('/preparation/daily', {date: actionEl.dataset.date, offer_id: Number(actionEl.dataset.id)});
          toast('Dossier créé depuis l’offre du jour.');
          await workflowAppDrawer(app.id);
          await render({preserveFocus: true});
          return;
        }
        case 'workflow-app':
          await workflowAppDrawer(actionEl.dataset.id);
          return;
        case 'workflow-prepare': {
          actionEl.disabled = true;
          const result = await wfPost(`/preparation/applications/${actionEl.dataset.id}`);
          toast(result.missing?.length ? 'Dossier partiel. Les pièces manquantes restent visibles.' : 'Dossier prêt.');
          await workflowAppDrawer(result.application.id);
          await render({preserveFocus: true});
          return;
        }
        case 'workflow-status-action': {
          actionEl.disabled = true;
          const app = await wfPost(`/workflow/applications/${actionEl.dataset.id}/status`, {status: actionEl.dataset.status});
          toast('Statut mis à jour.');
          await workflowAppDrawer(app.id);
          await render({preserveFocus: true});
          return;
        }
        case 'workflow-sync':
          actionEl.disabled = true;
          await wfPost('/workflow/gmail/sync');
          toast('Synchronisation Gmail terminée ou statut mis à jour.');
          await render({preserveFocus: true});
          return;
      }
    } catch (error) {
      actionEl.disabled = false;
      toast(error.message, true);
    }
  }

  const assistantEl = event.target.closest('[data-assistant]');
  if (assistantEl?.dataset.assistant === 'toggle') {
    $('#assistant-float').classList.toggle('collapsed');
    if (!$('#assistant-float').classList.contains('collapsed')) $('#assistant-input')?.focus();
  }

  const assistantActionEl = event.target.closest('[data-assistant-action]');
  if (assistantActionEl) {
    try {
      await assistantAction(JSON.parse(assistantActionEl.dataset.assistantAction));
    } catch (error) {
      toast(error.message, true);
    }
  }
});

document.addEventListener('change', async event => {
  if (event.target.id === 'daily-date') {
    state.dailyDate = event.target.value;
    await render({preserveFocus: true});
  }
  if (event.target.id === 'workflow-status') {
    event.target.disabled = true;
    try {
      const app = await wfPost(`/workflow/applications/${event.target.dataset.id}/status`, {status: event.target.value});
      toast('Statut mis à jour.');
      await workflowAppDrawer(app.id);
      await render({preserveFocus: true});
    } catch (error) {
      toast(error.message, true);
      event.target.disabled = false;
    }
  }
});

document.addEventListener('submit', async event => {
  if (event.target.id !== 'assistant-form') return;
  event.preventDefault();
  const input = $('#assistant-input');
  const message = input.value.trim();
  if (!message) return;
  input.value = '';
  addAssistantMessage('user', esc(message));
  addAssistantMessage('assistant loading', '<span class="spinner"></span>');
  try {
    const response = await wfPost('/assistant/message', {message, history: []});
    $('.assistant-message.loading')?.remove();
    const actions = (response.actions || []).map(action => `<button class="btn btn-small" data-assistant-action='${esc(JSON.stringify(action))}'>${esc(action.label || action.type)}</button>`).join('');
    const sources = (response.sources || []).slice(0, 5).map(source => `<span class="tag">${esc(source.label)}</span>`).join('');
    addAssistantMessage('assistant', `<p>${esc(response.reply).replace(/\n/g, '<br>')}</p>${sources ? `<div class="tags">${sources}</div>` : ''}${actions ? `<div class="assistant-actions">${actions}</div>` : ''}`);
  } catch (error) {
    $('.assistant-message.loading')?.remove();
    addAssistantMessage('assistant', `<p>${esc(error.message)}</p>`);
  }
});
