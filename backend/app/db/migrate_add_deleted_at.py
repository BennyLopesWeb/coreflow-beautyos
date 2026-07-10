"""
Script de migração para adicionar coluna deleted_at
Adiciona a coluna deleted_at em todas as tabelas que precisam de soft delete
"""
import sqlite3
from pathlib import Path
from app.core.config import settings

def migrate_add_deleted_at():
    """
    Adiciona coluna deleted_at nas tabelas que precisam de soft delete
    """
    # Obtém o caminho do banco de dados
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    
    if not Path(db_path).exists():
        print(f"❌ Banco de dados não encontrado: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Lista de tabelas que precisam de deleted_at
        tables = [
            "clientes",
            "trancas", 
            "agendamentos",
            "fila",
            "financeiro",
            "users"
        ]
        
        for table in tables:
            # Verifica se a tabela existe
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                print(f"⚠️  Tabela '{table}' não existe, pulando...")
                continue
            
            # Verifica se a coluna já existe
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [col[1] for col in cursor.fetchall()]
            
            if "deleted_at" not in columns:
                print(f"➕ Adicionando coluna 'deleted_at' na tabela '{table}'...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at DATETIME")
                print(f"✅ Coluna 'deleted_at' adicionada na tabela '{table}'")
            else:
                print(f"ℹ️  Coluna 'deleted_at' já existe na tabela '{table}'")
        
        conn.commit()
        print("\n✅ Migração concluída com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro na migração: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_add_deleted_at()

