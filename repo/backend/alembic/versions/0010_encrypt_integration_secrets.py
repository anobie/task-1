"""encrypt integration secrets

Revision ID: 0010_encrypt_integration_secrets
Revises: 0009_scope_grants
Create Date: 2026-04-02 18:40:00
"""

from base64 import urlsafe_b64encode
import hashlib
import os

import sqlalchemy as sa
from alembic import op
from cryptography.fernet import Fernet

revision = "0010_encrypt_integration_secrets"
down_revision = "0009_scope_grants"
branch_labels = None
depends_on = None


def _fernet_from_material(key_material: str) -> Fernet:
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    return Fernet(urlsafe_b64encode(digest))


def upgrade() -> None:
    op.add_column("integration_clients", sa.Column("secret_ciphertext", sa.Text(), nullable=True))

    bind = op.get_bind()
    key_material = os.getenv("INTEGRATION_SECRET_ENC_KEY") or os.getenv("SECRET_KEY")
    if not key_material:
        raise RuntimeError("INTEGRATION_SECRET_ENC_KEY or SECRET_KEY must be set for migration.")
    fernet = _fernet_from_material(key_material)

    rows = bind.execute(sa.text("SELECT id, secret_key FROM integration_clients")).fetchall()
    for row in rows:
        secret_key = row[1]
        ciphertext = fernet.encrypt(secret_key.encode("utf-8")).decode("utf-8")
        bind.execute(
            sa.text("UPDATE integration_clients SET secret_ciphertext = :ciphertext, secret_key = NULL WHERE id = :id"),
            {"ciphertext": ciphertext, "id": row[0]},
        )

    op.alter_column("integration_clients", "secret_ciphertext", nullable=False)
    op.alter_column("integration_clients", "secret_key", existing_type=sa.String(length=128), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    key_material = os.getenv("INTEGRATION_SECRET_ENC_KEY") or os.getenv("SECRET_KEY")
    if not key_material:
        raise RuntimeError("INTEGRATION_SECRET_ENC_KEY or SECRET_KEY must be set for migration.")
    fernet = _fernet_from_material(key_material)

    rows = bind.execute(sa.text("SELECT id, secret_ciphertext FROM integration_clients")).fetchall()
    for row in rows:
        ciphertext = row[1]
        secret_key = fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        bind.execute(
            sa.text("UPDATE integration_clients SET secret_key = :secret_key WHERE id = :id"),
            {"secret_key": secret_key, "id": row[0]},
        )

    op.alter_column("integration_clients", "secret_key", existing_type=sa.String(length=128), nullable=False)
    op.drop_column("integration_clients", "secret_ciphertext")
