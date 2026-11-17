// Served from the public static-only service-worker cache. This script never
// accesses session, tenant or financial data; the app re-authenticates online.
(function () {
  function reconnect() {
    if (navigator.onLine) window.location.replace('/');
  }
  window.addEventListener('online', reconnect);
  document.getElementById('retry-online')?.addEventListener('click', reconnect);
})();
