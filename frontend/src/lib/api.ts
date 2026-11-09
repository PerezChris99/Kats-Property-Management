function cookie(name:string) {
  return document.cookie.split('; ').find(c=>c.startsWith(name+'='))?.split('=').slice(1).join('=')||''
}
export function csrfToken() {return cookie('csrf_access_token')}
let refreshing:Promise<boolean>|null = null
async function refreshAccess() {
  if(!refreshing) {
    refreshing = (async()=>{
      const token = cookie('csrf_refresh_token')
      if(!token)return false
      try {
        const response = await fetch('/api/v1/auth/refresh',{
          method:'POST',credentials:'same-origin',cache:'no-store',
          headers:{'X-CSRF-TOKEN':token}
        })
        return response.ok
      } catch{return false}
    })().finally(()=>{refreshing=null})
  }
  return refreshing
}
export async function api(path: string, opts: RequestInit = {}) {
  const perform=()=>{
    const headers = new Headers(opts.headers)
    if (opts.body) headers.set('Content-Type', 'application/json')
    if (opts.method && opts.method !== 'GET') headers.set('X-CSRF-TOKEN', csrfToken())
    return fetch('/api/v1/' + path, {...opts, headers, credentials:'same-origin', cache:'no-store'})
  }
  let response=await perform()
  if(response.status===401 && !['auth/login','auth/refresh'].includes(path)) {
    if(await refreshAccess()) response=await perform()
    else window.dispatchEvent(new Event('kats:session-expired'))
  }
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.error?.message || 'Request failed (' + response.status + ')')
  return payload
}
