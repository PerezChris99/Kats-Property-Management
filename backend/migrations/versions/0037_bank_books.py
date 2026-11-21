"""Separate bank ledgers while retaining historical postings in BANK."""
import sqlalchemy as sa
from alembic import op

revision = "0037_bank_books"
down_revision = "0036_postgres_rate_limits"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("bank_statements") as batch:
        batch.add_column(sa.Column("book_code", sa.String(40), nullable=False, server_default="BANK"))
        batch.create_foreign_key("fk_bank_statement_book", "gl_accounts", ["book_code"], ["code"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION kats_guard_book_code() RETURNS trigger AS $$
          BEGIN RAISE EXCEPTION 'Statement ledger identity is immutable'; END;
          $$ LANGUAGE plpgsql""")
        op.execute("""CREATE TRIGGER kats_statement_book_guard BEFORE UPDATE OF book_code
            ON bank_statements FOR EACH ROW WHEN (OLD.book_code IS DISTINCT FROM NEW.book_code)
            EXECUTE FUNCTION kats_guard_book_code()""")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM bank_statements WHERE book_code <> 'BANK'")).scalar():
        raise RuntimeError("Restore a verified backup to roll back after posting additional bank accounts")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TRIGGER kats_statement_book_guard ON bank_statements")
        op.execute("DROP FUNCTION kats_guard_book_code()")
    with op.batch_alter_table("bank_statements") as batch:
        batch.drop_constraint("fk_bank_statement_book", type_="foreignkey")
        batch.drop_column("book_code")
