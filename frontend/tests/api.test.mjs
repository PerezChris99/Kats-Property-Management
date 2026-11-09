import test from 'node:test'
import assert from 'node:assert/strict'
import {api, csrfToken} from '../src/lib/api.js'

function setup(fetcher, cookie = 'csrf_access_token=unit-test-csrf') {
  globalThis.document = {cookie}
  globalThis.fetch = fetcher
  globalThis.window = {dispatchEvent() {}}
}

test('API rejects remote, rooted and traversal paths before any network call', async () => {
  let calls = 0
  setup(async () => {calls++; return new Response('{}', {status:200})})
  for (const path of ['https://attacker.example', '//attacker.example', '../secret', 'a/../secret', '', '/api/v1/users']) {
    await assert.rejects(api(path), /Invalid API path/)
  }
  assert.equal(calls, 0)
})

test('authenticated mutations use same-origin no-store and CSRF', async () => {
  const calls = []
  setup(async (url, options) => {
    calls.push({url, options})
    return new Response(JSON.stringify({ok:true}), {status:200, headers:{'content-type':'application/json'}})
  })
  const result = await api('properties', {method:'POST', body:JSON.stringify({name:'Kats'})})
  assert.deepEqual(result, {ok:true})
  assert.equal(calls.length, 1)
  assert.equal(calls[0].url, '/api/v1/properties')
  assert.equal(calls[0].options.method, 'POST')
  assert.equal(calls[0].options.credentials, 'same-origin')
  assert.equal(calls[0].options.cache, 'no-store')
  assert.equal(calls[0].options.headers.get('X-CSRF-TOKEN'), csrfToken())
  assert.equal(calls[0].options.headers.get('Content-Type'), 'application/json')
})

test('concurrent identical GETs share one pending request but never store completed data', async () => {
  let calls = 0
  setup(async () => {
    calls++
    await new Promise(resolve => setTimeout(resolve, 15))
    return new Response(JSON.stringify({count:calls}), {status:200, headers:{'content-type':'application/json'}})
  })
  const [a, b] = await Promise.all([api('dashboard'),api('dashboard')])
  assert.deepEqual(a, {count:1})
  assert.deepEqual(b, {count:1})
  assert.equal(calls,1)
  await api('dashboard')
  assert.equal(calls,2)
})

test('429 and server error handling do not leak internal transport state', async () => {
  setup(async () => new Response('{}', {status:429,headers:{'content-type':'application/json'}}))
  await assert.rejects(api('dashboard'), /Too many requests/)
  setup(async () => new Response(JSON.stringify({error:{message:'Access denied'}}), {status:403,headers:{'content-type':'application/json'}}))
  await assert.rejects(api('dashboard'), /Access denied/)
})
