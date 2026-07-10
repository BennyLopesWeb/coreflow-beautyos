#!/usr/bin/env python3
"""
Script para criar ou atualizar usuário de teste no banco de dados.

Uso:
    python scripts/seed_user.py
    python scripts/seed_user.py --email benny@email.com --nome Benny --password 123456
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash


def seed_user(
    email: str,
    nome: str,
    password: str,
    telefone: str | None = None,
    is_superuser: bool = False,
) -> User:
    """
    Cria ou atualiza um usuário profissional no banco.

    Args:
        email: E-mail do usuário (único).
        nome: Nome completo.
        password: Senha em texto plano (será hasheada).
        telefone: Telefone opcional.
        is_superuser: Se True, concede acesso administrativo.

    Returns:
        Instância User persistida no banco.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        hashed_password = get_password_hash(password)

        if user:
            user.nome = nome
            user.hashed_password = hashed_password
            user.telefone = telefone
            user.ativo = True
            user.is_superuser = is_superuser
            user.deleted_at = None
            action = "atualizado"
        else:
            user = User(
                email=email.lower(),
                nome=nome,
                hashed_password=hashed_password,
                telefone=telefone,
                ativo=True,
                is_superuser=is_superuser,
            )
            db.add(user)
            action = "criado"

        db.commit()
        db.refresh(user)
        print(f"Usuário {action}: id={user.id} email={user.email} nome={user.nome}")
        return user
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed de usuário TrançaPro")
    parser.add_argument("--email", default="benny@email.com")
    parser.add_argument("--nome", default="Benny")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--telefone", default=None)
    parser.add_argument("--admin", action="store_true", help="Concede acesso administrativo")
    args = parser.parse_args()

    seed_user(args.email, args.nome, args.password, args.telefone, is_superuser=args.admin)
