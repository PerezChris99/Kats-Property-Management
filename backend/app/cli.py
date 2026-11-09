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
