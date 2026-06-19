import sqlite3
import pandas as pd
from sqlalchemy import create_engine

DB_FILE = "buscadados.db"
CONN_STR = f"sqlite:///{DB_FILE}"
engine = create_engine(CONN_STR)

def inicializar_banco():
    """Cria as tabelas estruturadas com restrições NOT NULL se o banco for novo"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Tabela de Municípios
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS municipios (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Municipio TEXT NOT NULL,
        Estado TEXT NOT NULL
    )
    """)
    
    # Tabela de Bairros
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bairros (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Bairro TEXT NOT NULL,
        Municipio TEXT NOT NULL
    )
    """)
    
    # Tabela de UPMs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS upms (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        UPM TEXT NOT NULL,
        Descricao TEXT NOT NULL DEFAULT '',
        Bairro TEXT NOT NULL,
        Municipio TEXT NOT NULL,
        Estado TEXT NOT NULL
    )
    """)

    # Tabela de vínculo entre UPMs e Bairros
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS upm_bairros (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        UPM_ID INTEGER NOT NULL,
        Bairro_ID INTEGER NOT NULL,
        UNIQUE(UPM_ID, Bairro_ID),
        FOREIGN KEY(UPM_ID) REFERENCES upms(ID),
        FOREIGN KEY(Bairro_ID) REFERENCES bairros(ID)
    )
    """)

    # Se o banco já existir, garanta a coluna Descricao na tabela de UPMs
    cursor.execute("PRAGMA table_info(upms)")
    colunas_upm = [row[1] for row in cursor.fetchall()]
    if "Descricao" not in colunas_upm:
        cursor.execute("ALTER TABLE upms ADD COLUMN Descricao TEXT NOT NULL DEFAULT ''")
    
    conn.commit()
    conn.close()

def listar_dados(tabela: str) -> pd.DataFrame:
    """Busca qualquer tabela do banco e retorna como um DataFrame do Pandas"""
    try:
        return pd.read_sql(f"SELECT * FROM {tabela}", engine)
    except Exception:
        return pd.DataFrame()

def salvar_registro(tabela: str, dados_dict: dict) -> bool:
    """Insere um novo registro apenas se não for duplicado no banco"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if tabela == "municipios":
        municipio = dados_dict["Municipio"].strip()
        cursor.execute("SELECT 1 FROM municipios WHERE LOWER(Municipio) = LOWER(?)", (municipio,))
        if cursor.fetchone():
            conn.close()
            return False 
            
    elif tabela == "bairros":
        bairro = dados_dict["Bairro"].strip()
        municipio = dados_dict["Municipio"]
        cursor.execute("SELECT 1 FROM bairros WHERE LOWER(Bairro) = LOWER(?) AND Municipio = ?", (bairro, municipio))
        if cursor.fetchone():
            conn.close()
            return False

    elif tabela == "upms":
        upm = dados_dict["UPM"].strip()
        cursor.execute("SELECT 1 FROM upms WHERE LOWER(UPM) = LOWER(?)", (upm,))
        if cursor.fetchone():
            conn.close()
            return False
            
    conn.close()
    
    df = pd.DataFrame([dados_dict])
    df.to_sql(tabela, engine, if_exists='append', index=False)
    return True

def listar_bairros_vinculados(upm_id: int) -> pd.DataFrame:
    query = """
    SELECT
        ub.ID AS VinculoID,
        b.ID AS BairroID,
        b.Bairro,
        b.Municipio
    FROM upm_bairros ub
    JOIN bairros b ON ub.Bairro_ID = b.ID
    WHERE ub.UPM_ID = ?
    ORDER BY b.Municipio, b.Bairro
    """
    return pd.read_sql(query, engine, params=(upm_id,))

def atualizar_vinculo_bairros(upm_id: int, bairro_ids: list) -> bool:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM upm_bairros WHERE UPM_ID = ?", (upm_id,))
    for bairro_id in bairro_ids:
        cursor.execute(
            "INSERT OR IGNORE INTO upm_bairros (UPM_ID, Bairro_ID) VALUES (?, ?)",
            (upm_id, bairro_id),
        )
    conn.commit()
    conn.close()
    return True


def excluir_registro(tabela: str, id_registro: int):
    """Exclui uma linha de qualquer tabela do banco com base no ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(f"DELETE FROM {tabela} WHERE ID = ?", (id_registro,))
    conn.commit()
    conn.close()
