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
