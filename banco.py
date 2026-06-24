import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import unicodedata

def corrigir_mojibake(texto):
    if not texto:
        return ""
    texto_str = str(texto)
    try:
        return texto_str.encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        try:
            return texto_str.encode('cp1252').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            return texto_str

def normalizar_texto(texto):
    texto_corrigido = corrigir_mojibake(texto)
    nfkd = unicodedata.normalize('NFKD', texto_corrigido)
    return "".join([char for char in nfkd if not unicodedata.combining(char)]).lower().strip()

def padronizar_municipio(municipio_bruto):
    if not municipio_bruto:
        return ""
    
    # 1. Corrige mojibake se houver
    m_limpo = corrigir_mojibake(municipio_bruto)
    
    # 2. Faz TRIM e UPPER
    m_upper = str(m_limpo).strip().upper()
    
    # Normalização sem acentos para a comparação de regras
    nfkd = unicodedata.normalize('NFKD', m_upper)
    m_sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    
    # 3. Regras específicas de padronização
    if m_sem_acento in ["VARZEA GRANDE", "VG", "V GRANDE", "VARZEA G", "VGRANDE", "VARZEA GRAN"]:
        return "VÁRZEA GRANDE"
        
    if m_sem_acento in ["POCONE"]:
        return "POCONÉ"
        
    if m_sem_acento in ["SENHORA DO LIVRAMENTO", "N SENHORA DO LIVRAMENTO", "NOSSA SENHORA LIVRAMENTO", "NOSSA SENHORA"]:
        return "NOSSA SENHORA DO LIVRAMENTO"
        
    if m_sem_acento in ["ROSARIO OESTE", "R. OESTE", "ROSARIO"]:
        return "ROSÁRIO OESTE"
        
    return m_upper

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

    # Tabela de nomes alternativos de bairros (equivalências)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bairros_alternativos (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Bairro_ID INTEGER NOT NULL,
        Nome_Alternativo TEXT NOT NULL,
        UNIQUE(Bairro_ID, Nome_Alternativo),
        FOREIGN KEY(Bairro_ID) REFERENCES bairros(ID) ON DELETE CASCADE
    )
    """)

    # Se o banco já existir, garanta a coluna Descricao na tabela de UPMs
    cursor.execute("PRAGMA table_info(upms)")
    colunas_upm = [row[1] for row in cursor.fetchall()]
    if "Descricao" not in colunas_upm:
        cursor.execute("ALTER TABLE upms ADD COLUMN Descricao TEXT NOT NULL DEFAULT ''")
    
    # Migra dados antigos de UPMs para a tabela de vínculos (muitos-para-muitos)
    cursor.execute("SELECT COUNT(*) FROM upm_bairros")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT OR IGNORE INTO upm_bairros (UPM_ID, Bairro_ID)
        SELECT u.ID, b.ID
        FROM upms u
        JOIN bairros b ON LOWER(u.Bairro) = LOWER(b.Bairro) AND LOWER(u.Municipio) = LOWER(b.Municipio)
        """)
    
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


def obter_mapeamento_upms() -> dict:
    """Retorna um dicionário mapeando (bairro_normalizado, municipio_normalizado) -> nome_da_upm"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = """
    SELECT b.Bairro, b.Municipio, u.UPM
    FROM upms u
    JOIN upm_bairros ub ON u.ID = ub.UPM_ID
    JOIN bairros b ON ub.Bairro_ID = b.ID
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    mapeamento = {}
    for bairro, municipio, upm in rows:
        b_norm = normalizar_texto(bairro)
        m_norm = normalizar_texto(municipio)
        mapeamento[(b_norm, m_norm)] = upm
    return mapeamento


def obter_mapeamento_nomes_municipios() -> dict:
    """Retorna um dicionário mapeando municipio_normalizado -> Nome_Oficial_Do_Banco"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT Municipio FROM municipios")
    rows = cursor.fetchall()
    conn.close()
    return {normalizar_texto(row[0]): row[0] for row in rows}


def obter_mapeamento_nomes_bairros() -> dict:
    """Retorna um dicionário mapeando (bairro_normalizado, municipio_normalizado) -> Bairro_Oficial_Do_Banco"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT Bairro, Municipio FROM bairros")
    rows = cursor.fetchall()
    conn.close()
    
    mapeamento = {}
    for bairro, municipio in rows:
        b_norm = normalizar_texto(bairro)
        m_norm = normalizar_texto(municipio)
        mapeamento[(b_norm, m_norm)] = bairro
    return mapeamento



def listar_nomes_alternativos(bairro_id: int) -> pd.DataFrame:
    """Retorna os nomes alternativos para um determinado bairro"""
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql("SELECT * FROM bairros_alternativos WHERE Bairro_ID = ? ORDER BY Nome_Alternativo", conn, params=(bairro_id,))
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

def salvar_nome_alternativo(bairro_id: int, nome_alternativo: str) -> bool:
    """Insere um novo nome alternativo para o bairro se não for duplicado"""
    nome_alternativo = nome_alternativo.strip()
    if not nome_alternativo:
        return False
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Verifica se já existe para este bairro (case insensitive)
    cursor.execute(
        "SELECT 1 FROM bairros_alternativos WHERE Bairro_ID = ? AND LOWER(Nome_Alternativo) = LOWER(?)",
        (bairro_id, nome_alternativo)
    )
    if cursor.fetchone():
        conn.close()
        return False
        
    cursor.execute(
        "INSERT INTO bairros_alternativos (Bairro_ID, Nome_Alternativo) VALUES (?, ?)",
        (bairro_id, nome_alternativo)
    )
    conn.commit()
    conn.close()
    return True

def excluir_nome_alternativo(id_alternativo: int):
    """Exclui um nome alternativo do banco"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM bairros_alternativos WHERE ID = ?", (id_alternativo,))
    conn.commit()
    conn.close()

def obter_mapeamento_alternativo_bairros() -> dict:
    """Retorna um dicionário mapeando (bairro_alternativo_normalizado, municipio_normalizado) -> Bairro_Nome_Oficial"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    query = """
    SELECT ba.Nome_Alternativo, b.Bairro, b.Municipio
    FROM bairros_alternativos ba
    JOIN bairros b ON ba.Bairro_ID = b.ID
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    
    mapeamento = {}
    for nome_alternativo, bairro_oficial, municipio in rows:
        alt_norm = normalizar_texto(nome_alternativo)
        mun_norm = normalizar_texto(municipio)
        mapeamento[(alt_norm, mun_norm)] = bairro_oficial
    return mapeamento


def excluir_registro(tabela: str, id_registro: int):
    """Exclui uma linha de qualquer tabela do banco com base no ID"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute(f"DELETE FROM {tabela} WHERE ID = ?", (id_registro,))
    conn.commit()
    conn.close()
