import { useRouteError, Link } from 'react-router-dom';

/* React Router's data-router errorElement is a genuine render/route error
 * boundary. The UI is a functional component; no class component required.
 * Child render errors, failed dynamic imports and route errors surface here.
 */
export function RouteFailure() {
  const error = useRouteError();
  const failedChunk = String(error?.message || '').toLowerCase().includes('import');
  return <main className="kats-fatal-page" role="alert">
    <section className="kats-fatal-inner">
      <span className="eyebrow">WORKSPACE RECOVERY</span>
      <h1>We couldn’t open this page.</h1>
      <p>{failedChunk ?
        'The application was updated while this page was open. Refresh to load the latest files.' :
        'An unexpected page error occurred. Your existing records have not been changed by this screen.'}</p>
      <div className="kats-error-actions">
        <button type="button" className="button" onClick={()=>window.location.reload()}>Reload page</button>
        <Link to="/dashboard" className="outline-button">Back to dashboard</Link>
        <Link to="/login" className="outline-button">Sign in</Link>
      </div>
    </section>
  </main>;
}
export function NotFoundPage() {
  return <main className="kats-fatal-page" role="status">
    <section className="kats-fatal-inner">
      <span className="eyebrow">PAGE NOT FOUND · 404</span>
      <h1>This page doesn’t exist.</h1>
      <p>Use the dashboard or homepage to navigate to an available section.</p>
      <div className="kats-error-actions">
        <Link className="button" to="/dashboard">Workspace</Link>
        <Link className="outline-button" to="/">Homepage</Link>
      </div>
    </section>
  </main>;
}
