// KATS staging-only read-path performance baseline.
//
// Usage:
//   KATS_LOAD_TEST_APPROVED=yes BASE_URL=https://your-staging-domain k6 run ops/load-test.js
//
// This script intentionally performs read-only public requests. It does NOT
// benchmark logged-in tenant flows or real-money services. Do not target
// production, third-party gateways, or unknown public infrastructure.
import http from 'k6/http';
import { check, sleep } from 'k6';

if (__ENV.KATS_LOAD_TEST_APPROVED !== 'yes' || !__ENV.BASE_URL) {
  throw new Error('Require explicit KATS_LOAD_TEST_APPROVED=yes and BASE_URL for authorized staging.');
}
const base = __ENV.BASE_URL.replace(/\/+$/, '');
if (!/^https:\/\/[a-z0-9.-]+(?::\d+)?$/i.test(base)) {
  throw new Error('Use a staging HTTPS hostname. No credentials or URL paths allowed.');
}

export const options = {
  scenarios: {
    publicReadRamp: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '60s', target: 25 },
        { duration: '60s', target: 50 },
        { duration: '30s', target: 0 }
      ],
      gracefulRampDown: '10s'
    }
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<500', 'p(99)<1200'],
    checks: ['rate>0.99']
  },
  userAgent: 'KATS-authorized-staging-load-check/1.0'
};

export default function () {
  const options = { timeout: '8s', tags: { surface: 'public' } };
  const health = http.get(base + '/healthz', options);
  check(health, { 'health status 200': r => r.status === 200 });
  const landing = http.get(base + '/api/v1/public/landing-content', options);
  check(landing, {
    'public landing status 200': r => r.status === 200,
    'JSON served': r => String(r.headers['Content-Type'] || '').includes('application/json')
  });
  sleep(1);
}
