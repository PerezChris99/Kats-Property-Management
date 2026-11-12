// Authenticated synthetic staging load test. Never aim at production.
//
// KATS_LOAD_TEST_APPROVED=yes
// KATS_STAGING_BASE_URL=https://staging.example.com
// KATS_STAGING_COOKIE="access_token_cookie=..."
// KATS_STAGING_ROLE=TENANT or OWNER
// k6 run ops/load-workspace.js
//
// Cookie must belong to an isolated test account, never a real tenant.
// Script uses read-only endpoints; no payments or account changes.
import http from 'k6/http';
import { check, sleep } from 'k6';

const base = (__ENV.KATS_STAGING_BASE_URL || '').replace(/\/+$/, '');
const cookie = __ENV.KATS_STAGING_COOKIE || '';
const role = __ENV.KATS_STAGING_ROLE || 'TENANT';
if (__ENV.KATS_LOAD_TEST_APPROVED !== 'yes'
  || !/^https:\/\/[a-z0-9.-]*?(staging|test)[a-z0-9.-]*(?::\d+)?$/i.test(base)
  || !/^access_token_cookie=[A-Za-z0-9_.=-]+(?:;[ ]*[a-z_]+=[A-Za-z0-9_.=-]+)*$/.test(cookie)
  || !['OWNER','TENANT'].includes(role)) {
  throw new Error('Use approved HTTPS staging, isolated test cookies and an explicit test role.');
}

export const options = {
  scenarios: { authorizedRead: {
    executor: 'ramping-vus', startVUs: 0,
    stages: [
      { duration: '30s', target: 5 },
      { duration: '60s', target: 15 },
      { duration: '60s', target: 25 },
      { duration: '30s', target: 0 }
    ],
    gracefulRampDown: '10s'
  }},
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500', 'p(99)<1200'],
    checks: ['rate>0.99']
  },
  userAgent: 'KATS-authorized-staging-workspace/1.0'
};

export default function () {
  const headers = {Cookie: cookie, Accept:'application/json'};
  const requestOptions = {headers, timeout:'8s', responseType:'none', redirects:0};
  const urls = role === 'OWNER'
    ? ['/api/v1/dashboard','/api/v1/properties?page=1&page_size=25',
       '/api/v1/invoices?page=1&page_size=25',
       '/api/v1/operations/maintenance-aging']
    : ['/api/v1/tenant/dashboard','/api/v1/tenant/lease',
       '/api/v1/invoices?page=1&page_size=25',
       '/api/v1/maintenance?page=1&page_size=25'];

  const selected = urls[Math.floor(Math.random()*urls.length)];
  const response = http.get(base+selected,requestOptions);
  check(response, { 'authorized read succeeded': r => r.status===200 });
  sleep(1);
}
