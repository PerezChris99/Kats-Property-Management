// The offline response is served at the requested URL. Reload it so normal
// authentication and deep-link routing run again when connectivity returns.
(function () {
  function reconnect() {
    if (window.location.pathname === '/offline.html') window.location.replace('/dashboard');
    else window.location.reload();
  }
  window.addEventListener('online', reconnect);
  document.getElementById('retry-online')?.addEventListener('click', reconnect);
})();
