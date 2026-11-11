"""One-time synthetic Neon database seeding. Never runs on app boot or deploy.

Run only after fully migrating the isolated katsproperty Neon PostgreSQL
database with the migration role, under explicitly opted-in staging settings.
The strong synthetic password is supplied from a secret manager (not Git).
"""
from seed_demo_preview import seed

if __name__ == "__main__":
    seed(public_demo=True)
