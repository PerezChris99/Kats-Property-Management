import test from 'node:test'
import assert from 'node:assert/strict'
import {api} from '../src/lib/api.js'

function setup(fetcher, cookie = 'csrf_access_token=csrf-a; csrf_refresh_token=csrf-r') {
  const events = []
  globalThis.document = {cookie}
  globalThis.fetch = fetcher
  globalThis.window = {dispatchEvent(event) { events.push(event.type) }}
  return events
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status, headers: {'content-type': 'application/json'}
  })
}

test('expired access cookie refreshes once, retries GET, and does not cache resolved user data', async () => {
  const calls = []
  setup(async (url, options) => {
    calls.push({url, options})
    if (url === '/api/v1/auth/refresh') return json({ok: true})
    if (calls.length === 1) return json({error:{message:'Expired'}}, 401)
    return json({items: [1]})
  })
  assert.deepEqual(await api('properties'), {items:[1]})
  assert.equal(calls.length, 3)
  assert.equal(calls[1].url, '/api/v1/auth/refresh')
  assert.equal(calls[1].options.method, 'POST')
  assert.equal(calls[1].options.headers['X-CSRF-TOKEN'], 'csrf-r')
  assert.equal(calls[1].options.credentials, 'same-origin')
  assert.equal(calls[1].options.cache, 'no-store')
  await api('properties')
  assert.equal(calls.length, 4, 'A second read must refetch private data')
})

test('invalid refresh token surfaces a session-expired event and never loops', async () => {
  let calls = 0
  const events = setup(async () => {
    calls += 1
    return json({error:{message:'Sign in again'}}, 401)
  }, 'csrf_access_token=csrf-a')
  await assert.rejects(api('dashboard'), /Sign in again/)
  assert.equal(calls, 1, 'No refresh request when cookie is absent')
  assert.deepEqual(events, ['kats:session-expired'])
})

test('aborted navigation requests remain cancellations, not network errors', async () => {
  setup(async (_url, options) => {throw options.signal.reason})
  const controller = new AbortController()
  controller.abort()
  await assert.rejects(api('properties', {signal: controller.signal}),
    error => error instanceof DOMException && error.name === 'AbortError')
})

test('timeout and other network failures remain user-readable without leaking internals', async () => {
  setup(async () => { throw new DOMException('sensitive path', 'TimeoutError') })
  await assert.rejects(api('properties'), /Request timed out/)
  setup(async () => { throw new Error('SQL password:secret') })
  await assert.rejects(api('properties'), /Unable to connect/)
})

test('GETs with distinct request headers are not incorrectly coalesced', async () => {
  let calls = 0
  setup(async () => { calls++; return json({count:calls}) })
  const [a, b] = await Promise.all([
    api('properties', {headers: {'X-Use':'one'}}),
    api('properties', {headers: {'X-Use':'two'}}),
  ])
  assert.deepEqual([a.count, b.count], [1,2])
  assert.equal(calls, 2)
})

test('huge untrusted server errors are replaced with bounded generic messages', async () => {
  setup(async () => json({error:{message:'x'.repeat(301)}}, 500))
  await assert.rejects(api('properties'), /Request failed \(500\)/)
})
