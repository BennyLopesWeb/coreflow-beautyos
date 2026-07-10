"""
Service de Cliente
Lógica de negócio para gerenciamento de clientes
"""
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate, ClienteUpdate
from app.core.exceptions import NotFoundError, ConflictError


class ClienteService:
    """
    Service para gerenciamento de clientes
    Centraliza regras de negócio relacionadas a clientes
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def listar_clientes(self) -> List[Cliente]:
        """Lista todos os clientes (não deletados)"""
        return self.db.query(Cliente).filter(Cliente.deleted_at.is_(None)).all()
    
    def buscar_por_id(self, cliente_id: int) -> Optional[Cliente]:
        """Busca cliente por ID (não deletado)"""
        return self.db.query(Cliente).filter(
            Cliente.id == cliente_id,
            Cliente.deleted_at.is_(None)
        ).first()
    
    def buscar_por_telefone(self, telefone: str) -> Optional[Cliente]:
        """Busca cliente por telefone (não deletado)"""
        return self.db.query(Cliente).filter(
            Cliente.telefone == telefone,
            Cliente.deleted_at.is_(None)
        ).first()
    
    def obter_cliente(self, cliente_id: int) -> Cliente:
        """
        Obtém cliente por ID
        Lança exceção se não encontrado
        """
        cliente = self.buscar_por_id(cliente_id)
        if not cliente:
            raise NotFoundError("Cliente", str(cliente_id))
        return cliente
    
    def criar_cliente(self, cliente_data: ClienteCreate) -> Cliente:
        """
        Cria novo cliente
        Valida telefone único
        """
        # Validação: telefone deve ser único
        cliente_existente = self.buscar_por_telefone(cliente_data.telefone)
        if cliente_existente:
            raise ConflictError(f"Cliente com telefone {cliente_data.telefone} já existe")
        
        cliente = Cliente(**cliente_data.model_dump())
        self.db.add(cliente)
        self.db.commit()
        self.db.refresh(cliente)
        return cliente
    
    def atualizar_cliente(self, cliente_id: int, cliente_data: ClienteUpdate) -> Cliente:
        """
        Atualiza cliente existente
        Valida telefone único se estiver atualizando
        """
        cliente = self.obter_cliente(cliente_id)
        
        update_data = cliente_data.model_dump(exclude_unset=True)
        
        # Validação: se está atualizando telefone, verifica unicidade
        if "telefone" in update_data and update_data["telefone"] != cliente.telefone:
            cliente_existente = self.buscar_por_telefone(update_data["telefone"])
            if cliente_existente:
                raise ConflictError(f"Cliente com telefone {update_data['telefone']} já existe")
        
        # Atualiza campos
        for key, value in update_data.items():
            setattr(cliente, key, value)
        
        self.db.commit()
        self.db.refresh(cliente)
        return cliente

