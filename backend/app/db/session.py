"""
Configuração de sessão do banco de dados
Gerencia conexões e sessões SQLAlchemy
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Cria engine do SQLAlchemy
# Para SQLite, check_same_thread=False é necessário
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG  # Log SQL queries em modo debug
)

# Factory de sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency para obter sessão do banco de dados
    Usado em endpoints FastAPI via Depends()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

