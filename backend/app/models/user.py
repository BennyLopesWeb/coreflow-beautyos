"""
Model User
Representa o profissional (usuário do sistema)
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    """
    Model de User (Profissional)
    Armazena informações do profissional que usa o sistema
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    nome = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    telefone = Column(String, nullable=True)
    ativo = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # Soft delete
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    memberships = relationship("UserCompany", back_populates="user")

