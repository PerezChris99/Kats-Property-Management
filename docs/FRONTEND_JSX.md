# React frontend — JavaScript / JSX only

**Kats Properties · Proprietary software. All rights reserved.**

The frontend uses JavaScript (.js) and React JSX (.jsx). It no longer requires
TypeScript, TSX, a TS compiler, tsconfig, or any TypeScript-specific build step.

## Structure

| File | Responsibility |
| --- | --- |
| src/main.jsx | React initialization, router and PWA registration |
| src/App.jsx | Public/authenticated routes, resource pages and dashboard |
| src/WorkspaceNavigation.jsx | Accessible navigation, mobile drawer and search |
| src/Modules.jsx | Finance, documents, maintenance and administration |
| src/AccountScreens.jsx | Login recovery, invitations, permission management |
| src/ProrationPage.jsx, AnnualTrendsPage.jsx, PortfolioEditPage.jsx and ExpenseApprovalsPage.jsx | Lazy-loaded feature views |
| src/lib/api.js | Same-origin requests, CSRF, session refresh, request deadlines and GET coalescing |
| src/styles.css | Responsive interface and reduced-motion styling |
| vite.config.js | JSX and Vite development/production configuration |
| tests/api.test.mjs | JavaScript API behavior and security regression tests |
| eslint.config.js | JavaScript correctness and React Hooks rules |

## Developer workflow

~~~bash
cd frontend
npm ci
npm run dev
npm run lint
npm test
npm run build
~~~

The production build includes a JSX-only source gate, strict ESLint, API
unit tests and Vite's optimized bundle. CI and the Docker production image
run from the committed package-lock.json using npm ci.

## Code conventions

- React components belong in .jsx files. Framework-independent utilities
  belong in .js files. Use ES modules and JSX, never TSX or TypeScript.
- Browser validation improves usability; the backend must validate every
  incoming value again. Role and object access is always server-enforced.
- React escapes normal text. Never render user-provided HTML with innerHTML or
  dangerouslySetInnerHTML. Preserve CSP and do not put secrets in browser code.
- Use the authenticated API helper for same-origin CSRF, no-store, secure
  session refresh and deliberate transport error handling.
- Preserve lazy feature loading, accessible labels, clear loading and error
  states, keyboard focus behavior and reduced-motion preferences.
- Write regression tests for changed payments, permissions, authentication,
  forms and other sensitive journeys. Verify behavior on actual devices.

Plain JSX provides the same React capabilities and runtime performance.
JavaScript does not provide TypeScript's compile-time type checking; maintain
quality through ESLint, runtime guards, focused tests, code review, and real
staging acceptance. A successful build is not proof that every workflow works.
