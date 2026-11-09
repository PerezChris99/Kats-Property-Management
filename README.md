# Kats Property Management

Single-business, mobile-first Ugandan property-management system. UGX is stored in integer amounts.

**Status: Development only. NOT ready for production financial transactions or EFRIS.** This repository was empty before initialization on November 9, 2026.

## Architecture
- Backend: Flask, PostgreSQL 16, SQLAlchemy 2, Flask-Migrate, Argon2id password hashing, JWT HTTP-only cookies.
- Frontend: React + TypeScript + Vite, mobile-first interface and PWA offline fallback.
- Services: Redis and Celery workers; Nginx frontend; local Docker Compose.
- Deployment target: HostWares VPS. External MTN, Airtel and EFRIS integrations are not yet connected.

## Local run
1. Install Docker and Compose. Copy `.env.example` to `.env`. Replace example passwords and secrets with independent long random values.
2. Run `docker compose up --build -d`.
3. Run `docker compose exec api flask --app wsgi db upgrade`.
4. Create the first owner securely using `docker compose exec api flask --app wsgi create-user --role OWNER` (interactive).
5. Visit http://localhost:5173, then sign in. API health: http://localhost:8000/healthz.

## Native development
Python 3.12+, Node 22+, PostgreSQL and Redis. From backend: install requirements in a virtualenv, set DATABASE_URL, migrate, run `flask --app wsgi run --port 8000`. From frontend: `npm install && npm run dev`.

## Security boundaries
Access and refresh JWTs are stored in HttpOnly cookies with CSRF verification on authenticated mutations. Owner/staff operations require backend role checks. Cash and bank entries remain pending until reviewed by another authorized staff member; the invoice ledger is updated only on approval. This is a baseline workflow, not a substitute for operational verification.

Production requires HTTPS, object-level access tests, database backups and restore exercises, rate-limit testing, signed provider callbacks, approved EFRIS access, monitoring, migration validation, UAT and owner signoff. The current Docker Compose binds HTTP ports to localhost; it is for development, not an internet-exposed deployment.

## Git flow
Use `perez` for development; review and merge verified code via PR into `main`. The very first seed commit was the only direct commit on `main`, required because the repo started with no branches. No release tag until production acceptance.

See [Architecture](docs/ARCHITECTURE.md) and [Delivery status](docs/DELIVERY_STATUS.md).
