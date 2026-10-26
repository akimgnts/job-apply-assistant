/* Browser session login: the password is sent only over HTTPS and never stored. */
(function () {
  document.addEventListener('submit', async function (event) {
    const form = event.target;
    if (!form || form.id !== 'access-form') return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const data = new FormData(form);
    const password = String(data.get('password') || data.get('token') || '').trim();
    const submit = form.querySelector('[type="submit"]');
    if (submit) submit.disabled = true;
    try {
      const response = await fetch('/auth/login', {
        method: 'POST', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password})
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || 'Connexion refusée.');
      }
      window.sessionStorage.removeItem('jobapply-token');
      window.location.reload();
    } catch (error) {
      const message = form.querySelector('.form-error');
      if (message) message.textContent = error.message;
      else window.alert(error.message);
      if (submit) submit.disabled = false;
    }
  }, true);
})();
