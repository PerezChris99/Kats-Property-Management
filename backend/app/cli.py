import click
from argon2 import PasswordHasher
from flask.cli import with_appcontext
from .extensions import db
from .models import User

def register_commands(app):
    @app.cli.command("create-user")
    @click.option("--email", prompt=True)
    @click.option("--name", prompt=True)
    @click.option("--role", type=click.Choice(["OWNER", "MANAGER", "ACCOUNTANT", "CARETAKER", "TENANT", "SUPER_ADMIN"]), default="OWNER")
    @click.password_option()
    @with_appcontext
    def create_user(email, name, role, password):
        """Bootstrap an account using the server console. No public elevation."""
        email = email.strip().lower()
        if len(password) < 12:
            raise click.ClickException("Password must have 12 or more characters")
        if db.session.query(User.id).filter_by(email=email).first():
            raise click.ClickException("Account already exists")
        user = User(email=email, full_name=name.strip(), role=role, password_hash=PasswordHasher().hash(password))
        db.session.add(user)
        db.session.commit()
        click.echo("Created user " + user.id)


    @app.cli.command("seed-permissions")
    @with_appcontext
    def seed_permissions():
        """Bootstrap conservative backend route grants.

        Existing grants are NOT overwritten: use only for new installations or
        newly-added route defaults. Run this after every migration/deployment.
        """
        from .models import Role, Permission, RolePermission
        from flask import current_app
        role_names=("OWNER","MANAGER","ACCOUNTANT","CARETAKER","TENANT","SUPER_ADMIN")
        for name in role_names:
            if db.session.get(Role,name) is None:
                db.session.add(Role(name=name,description="Kats "+name.replace("_"," ").title()))
        db.session.flush()
        count=0
        for endpoint,view in current_app.view_functions.items():
            assigned=getattr(view,"__allowed_roles__",None)
            if assigned is None:
                continue
            name="route:"+endpoint
            if db.session.get(Permission,name) is None:
                db.session.add(Permission(name=name,description="Route "+endpoint))
                db.session.flush()
                for role in assigned:
                    db.session.add(RolePermission(role_name=role,permission_name=name))
                count+=1
        db.session.commit()
        click.echo(f"Seeded {count} new route permission(s); existing grants preserved.")


    @app.cli.command("security-preflight")
    @with_appcontext
    def security_preflight():
        """Fail production readiness when DB role/RLS/config are unsafe.

        Run using the ACTUAL production application DB credentials after
        migrations and before enabling traffic; never run this as DBA.
        """
        import os
        from sqlalchemy import text
        from .config import validate_production_config
        if os.getenv("APP_ENV") != "production":
            raise click.ClickException("Set APP_ENV=production for a real production preflight")
        try:
            validate_production_config()
        except RuntimeError as error:
            raise click.ClickException(str(error)) from None
        role=db.session.execute(text("""
          SELECT rolname,rolsuper,rolbypassrls,rolcreaterole,rolcreatedb
          FROM pg_roles WHERE rolname=current_user
        """)).one()
        if any((role.rolsuper,role.rolbypassrls,role.rolcreaterole,role.rolcreatedb)):
            raise click.ClickException(
                "Application PostgreSQL user has elevated database privileges; "
                "use a dedicated non-superuser, non-BYPASSRLS runtime account"
            )
        security=db.session.execute(text("""
          SELECT relrowsecurity,relforcerowsecurity
          FROM pg_class WHERE oid = 'documents'::regclass
        """)).one()
        if not all(security):
            raise click.ClickException("Private-document RLS is not enabled and forced")
        policy=db.session.execute(text("""
          SELECT count(*) FROM pg_policies
          WHERE schemaname=current_schema() AND tablename='documents'
            AND policyname='kats_document_scope'
        """)).scalar()
        if not policy:
            raise click.ClickException("Private-document RLS policy is missing")
        scoped_tables=("tenants","leases","invoices","payments",
                       "maintenance_requests","notifications")
        for table in scoped_tables:
            state=db.session.execute(text("""
              SELECT cls.relrowsecurity, cls.relforcerowsecurity,
                     EXISTS (SELECT 1 FROM pg_policies p
                             WHERE p.schemaname=current_schema()
                               AND p.tablename=cls.relname
                               AND p.policyname='kats_runtime_scope')
              FROM pg_class cls
              WHERE cls.oid = to_regclass(:table)
            """),{"table":table}).first()
            if not state or not all(state):
                raise click.ClickException("Core tenant/finance FORCE RLS missing for " + table)
        expected=int(os.getenv("DB_POOL_SIZE","5"))+int(os.getenv("DB_MAX_OVERFLOW","2"))
        click.echo("PASS: restricted application DB role, document/tenant/finance "
                   "FORCE RLS policies, Redis and production configuration checks.")
        click.echo(f"WARNING: pool allowance is {expected} connections per web worker "
                   "plus Celery, exports and administration; benchmark your database "
                   "connection budget and review remaining API-only tables.")
        click.echo("NEXT: validate public TLS edge, providers, backups, "
                   "S3 antivirus, penetration tests and staging load benchmarks.")
