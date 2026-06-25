import sqlite3
import pandas as pd
from sqlalchemy import create_engine
import unicodedata
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

# Configuração da chave de criptografia Fernet
SECRET_KEY_PATH = ".env"
_key = os.getenv("CRYPTO_KEY")

if not _key:
    _key_bytes = Fernet.generate_key()
    _key = _key_bytes.decode('utf-8')
    if not os.path.exists(SECRET_KEY_PATH):
        with open(SECRET_KEY_PATH, "w", encoding="utf-8") as f:
            f.write(f"CRYPTO_KEY={_key}\n")
    else:
        with open(SECRET_KEY_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
        replaced = False
        for idx, line in enumerate(lines):
            if line.startswith("CRYPTO_KEY="):
                lines[idx] = f"CRYPTO_KEY={_key}\n"
                replaced = True
                break
        if not replaced:
            lines.append(f"CRYPTO_KEY={_key}\n")
        with open(SECRET_KEY_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
    load_dotenv()

cipher = Fernet(_key.encode('utf-8'))

def criptografar_senha(senha: str) -> str:
    if not senha:
        return ""
    return cipher.encrypt(senha.encode('utf-8')).decode('utf-8')

def descriptografar_senha(senha_cripto: str) -> str:
    if not senha_cripto:
        return ""
    try:
        return cipher.decrypt(senha_cripto.encode('utf-8')).decode('utf-8')
    except Exception:
        return "Erro ao descriptografar"

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

    # Tabela de Serviços
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Nome TEXT NOT NULL,
        UrlLogin TEXT NOT NULL,
        UrlConsulta TEXT NOT NULL,
        UrlPdf TEXT NOT NULL,
        Login TEXT NOT NULL,
        Senha TEXT NOT NULL,
        DuplaAutenticacao TEXT NOT NULL DEFAULT 'Não',
        Tipo TEXT NOT NULL DEFAULT 'SROP',
        Status TEXT NOT NULL DEFAULT 'Ativo',
        Tempo_Expiracao_Horas INTEGER NOT NULL DEFAULT 4
    )
    """)
    
    # Se o banco já existir, garanta a coluna Descricao na tabela de UPMs
    cursor.execute("PRAGMA table_info(upms)")
    colunas_upm = [row[1] for row in cursor.fetchall()]
    if "Descricao" not in colunas_upm:
        cursor.execute("ALTER TABLE upms ADD COLUMN Descricao TEXT NOT NULL DEFAULT ''")

    # Garanta as colunas novas na tabela de serviços para bancos já existentes
    cursor.execute("PRAGMA table_info(servicos)")
    colunas_ser = [row[1] for row in cursor.fetchall()]
    if "DuplaAutenticacao" not in colunas_ser:
        cursor.execute("ALTER TABLE servicos ADD COLUMN DuplaAutenticacao TEXT NOT NULL DEFAULT 'Não'")
    if "Tipo" not in colunas_ser:
        cursor.execute("ALTER TABLE servicos ADD COLUMN Tipo TEXT NOT NULL DEFAULT 'SROP'")
    if "Status" not in colunas_ser:
        cursor.execute("ALTER TABLE servicos ADD COLUMN Status TEXT NOT NULL DEFAULT 'Ativo'")
    if "Tempo_Expiracao_Horas" not in colunas_ser:
        cursor.execute("ALTER TABLE servicos ADD COLUMN Tempo_Expiracao_Horas INTEGER NOT NULL DEFAULT 4")
    
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
    dados_salvar = dados_dict.copy()
    
    if tabela == "municipios":
        municipio = dados_salvar["Municipio"].strip()
        cursor.execute("SELECT 1 FROM municipios WHERE LOWER(Municipio) = LOWER(?)", (municipio,))
        if cursor.fetchone():
            conn.close()
            return False 
            
    elif tabela == "bairros":
        bairro = dados_salvar["Bairro"].strip()
        municipio = dados_salvar["Municipio"]
        cursor.execute("SELECT 1 FROM bairros WHERE LOWER(Bairro) = LOWER(?) AND Municipio = ?", (bairro, municipio))
        if cursor.fetchone():
            conn.close()
            return False

    elif tabela == "upms":
        upm = dados_salvar["UPM"].strip()
        cursor.execute("SELECT 1 FROM upms WHERE LOWER(UPM) = LOWER(?)", (upm,))
        if cursor.fetchone():
            conn.close()
            return False
            
    elif tabela == "servicos":
        nome = dados_salvar["Nome"].strip()
        cursor.execute("SELECT 1 FROM servicos WHERE LOWER(Nome) = LOWER(?)", (nome,))
        if cursor.fetchone():
            conn.close()
            return False
        # Criptografa a senha antes de gravar no banco de dados
        if "Senha" in dados_salvar:
            dados_salvar["Senha"] = criptografar_senha(dados_salvar["Senha"])
            
    conn.close()
    
    df = pd.DataFrame([dados_salvar])
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


def limpar_banco_dados():
    """Exclui todos os registros de todas as tabelas e reinicia os IDs autoincrementais"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = OFF")
    cursor.execute("DELETE FROM bairros_alternativos")
    cursor.execute("DELETE FROM upm_bairros")
    cursor.execute("DELETE FROM upms")
    cursor.execute("DELETE FROM bairros")
    cursor.execute("DELETE FROM municipios")
    conn.commit()
    
    # Executa VACUUM fora de transação ativa definindo isolation_level como None
    conn.isolation_level = None
    cursor.execute("VACUUM")
    conn.close()


def importar_municipios_lote(df: pd.DataFrame) -> dict:
    """Importa municípios a partir de um DataFrame, evitando duplicatas"""
    inseridos = 0
    pulados = 0
    erros = 0
    
    if df.empty:
        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Carrega municípios existentes em memória para comparação rápida
    cursor.execute("SELECT Municipio, Estado FROM municipios")
    existentes = {(str(row[0]).strip().upper(), str(row[1]).strip().upper()) for row in cursor.fetchall()}
    
    # 2. Processa as linhas
    for _, row in df.iterrows():
        municipio = row.get("Municipio")
        estado = row.get("Estado", "MT")
        
        if pd.isna(municipio) or not str(municipio).strip():
            erros += 1
            continue
            
        mun_clean = padronizar_municipio(municipio)
        est_clean = str(estado).strip().upper()
        
        # Garante que UF tem 2 letras
        if len(est_clean) > 2 and " - " in est_clean:
            est_clean = est_clean.split(" - ")[0].strip()
            
        key = (mun_clean.upper(), est_clean)
        if key in existentes:
            pulados += 1
        else:
            try:
                cursor.execute(
                    "INSERT INTO municipios (Municipio, Estado) VALUES (?, ?)",
                    (mun_clean, est_clean)
                )
                existentes.add(key)
                inseridos += 1
            except Exception:
                erros += 1
                
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}


def importar_bairros_lote(df: pd.DataFrame) -> dict:
    """Importa bairros a partir de um DataFrame, normalizando nomes e evitando duplicatas"""
    inseridos = 0
    pulados = 0
    erros = 0
    
    if df.empty:
        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Carrega bairros existentes de forma normalizada (sem acentos e em minúsculas)
    cursor.execute("SELECT Bairro, Municipio FROM bairros")
    existentes = {(normalizar_texto(row[0]), normalizar_texto(row[1])) for row in cursor.fetchall()}
    
    # 2. Processa as linhas
    for _, row in df.iterrows():
        bairro = row.get("Bairro")
        municipio = row.get("Municipio")
        
        if pd.isna(bairro) or not str(bairro).strip() or pd.isna(municipio) or not str(municipio).strip():
            erros += 1
            continue
            
        # Padronização e normalização
        bai_clean = str(bairro).strip().upper()
        mun_clean = padronizar_municipio(municipio)
        
        key_norm = (normalizar_texto(bai_clean), normalizar_texto(mun_clean))
        if key_norm in existentes:
            pulados += 1
        else:
            try:
                cursor.execute(
                    "INSERT INTO bairros (Bairro, Municipio) VALUES (?, ?)",
                    (bai_clean, mun_clean)
                )
                existentes.add(key_norm)
                inseridos += 1
            except Exception:
                erros += 1
                
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}


def importar_nomes_alternativos_lote(df: pd.DataFrame) -> dict:
    """Importa nomes alternativos vinculando ao ID correto do Bairro Oficial"""
    inseridos = 0
    pulados = 0
    erros = 0
    
    if df.empty:
        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Mapeamento de Bairros Oficiais em memória (Bairro, Municipio) -> ID
    cursor.execute("SELECT ID, Bairro, Municipio FROM bairros")
    bairros_map = {(str(row[1]).strip().upper(), str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}
    
    # 2. Nomes alternativos existentes em memória (Bairro_ID, Nome_Alternativo)
    cursor.execute("SELECT Bairro_ID, Nome_Alternativo FROM bairros_alternativos")
    existentes = {(row[0], str(row[1]).strip().upper()) for row in cursor.fetchall()}
    
    # 3. Processa
    for _, row in df.iterrows():
        bairro_oficial = row.get("Bairro_Oficial")
        municipio = row.get("Municipio")
        nome_alt = row.get("Nome_Alternativo")
        
        if pd.isna(bairro_oficial) or pd.isna(municipio) or pd.isna(nome_alt):
            erros += 1
            continue
            
        bai_oficial_clean = str(bairro_oficial).strip().upper()
        mun_clean = padronizar_municipio(municipio)
        nome_alt_clean = str(nome_alt).strip().upper()
        
        key_bairro = (bai_oficial_clean, mun_clean.upper())
        bairro_id = bairros_map.get(key_bairro)
        
        if not bairro_id:
            # Bairro oficial não encontrado
            erros += 1
            continue
            
        key_alt = (bairro_id, nome_alt_clean)
        if key_alt in existentes:
            pulados += 1
        else:
            try:
                cursor.execute(
                    "INSERT INTO bairros_alternativos (Bairro_ID, Nome_Alternativo) VALUES (?, ?)",
                    (bairro_id, nome_alt_clean)
                )
                existentes.add(key_alt)
                inseridos += 1
            except Exception:
                erros += 1
                
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}


def importar_upms_lote(df: pd.DataFrame) -> dict:
    """Importa UPMs, seus bairros originais e atualiza a tabela de relacionamentos (upm_bairros)"""
    inseridos = 0
    pulados = 0
    erros = 0
    
    if df.empty:
        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Carrega UPMs existentes em memória UPM -> ID
    cursor.execute("SELECT ID, UPM FROM upms")
    upms_map = {str(row[1]).strip().upper(): row[0] for row in cursor.fetchall()}
    
    # 2. Carrega Bairros existentes em memória (Bairro, Municipio) -> ID
    cursor.execute("SELECT ID, Bairro, Municipio FROM bairros")
    bairros_map = {(str(row[1]).strip().upper(), str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}
    
    # 3. Relacionamentos UPM_Bairro existentes em memória
    cursor.execute("SELECT UPM_ID, Bairro_ID FROM upm_bairros")
    rel_existentes = {(row[0], row[1]) for row in cursor.fetchall()}
    
    for _, row in df.iterrows():
        upm = row.get("UPM")
        descricao = row.get("Descricao", "")
        bairro = row.get("Bairro")
        municipio = row.get("Municipio")
        estado = row.get("Estado", "MT")
        
        if pd.isna(upm) or not str(upm).strip() or pd.isna(bairro) or pd.isna(municipio):
            erros += 1
            continue
            
        upm_clean = str(upm).strip().upper()
        desc_clean = str(descricao).strip() if not pd.isna(descricao) else ""
        bai_clean = str(bairro).strip().upper()
        mun_clean = padronizar_municipio(municipio)
        est_clean = str(estado).strip().upper()
        if len(est_clean) > 2 and " - " in est_clean:
            est_clean = est_clean.split(" - ")[0].strip()
            
        # Insere ou busca ID da UPM
        upm_id = upms_map.get(upm_clean)
        if not upm_id:
            try:
                cursor.execute(
                    "INSERT INTO upms (UPM, Descricao, Bairro, Municipio, Estado) VALUES (?, ?, ?, ?, ?)",
                    (upm_clean, desc_clean, bai_clean, mun_clean, est_clean)
                )
                upm_id = cursor.lastrowid
                upms_map[upm_clean] = upm_id
                inseridos += 1
            except Exception:
                erros += 1
                continue
        else:
            pulados += 1
            
        # Vínculo com o bairro
        key_bairro = (bai_clean, mun_clean.upper())
        bairro_id = bairros_map.get(key_bairro)
        
        if bairro_id and upm_id:
            rel_key = (upm_id, bairro_id)
            if rel_key not in rel_existentes:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO upm_bairros (UPM_ID, Bairro_ID) VALUES (?, ?)",
                        (upm_id, bairro_id)
                    )
                    rel_existentes.add(rel_key)
                except Exception:
                    pass
                    
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}


def obter_municipios_com_bairro_todos_unico() -> dict:
    """
    Retorna um dicionário mapeando municipio_normalizado -> UPM correspondente,
    para os municípios que possuem apenas UM bairro cadastrado, e esse bairro é 'TODOS'.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Busca contagem de bairros por município
    query_contagem = """
    SELECT Municipio, COUNT(*), MAX(Bairro)
    FROM bairros
    GROUP BY Municipio
    """
    cursor.execute(query_contagem)
    municipios_elegiveis = []
    for municipio, qtd_bairros, nome_bairro in cursor.fetchall():
        if qtd_bairros == 1 and normalizar_texto(nome_bairro) == "todos":
            municipios_elegiveis.append(municipio)
            
    # 2. Mapeia a UPM de cada município elegível
    mapa_mun_todos = {}
    for mun in municipios_elegiveis:
        query_upm = """
        SELECT u.UPM
        FROM upms u
        JOIN upm_bairros ub ON u.ID = ub.UPM_ID
        JOIN bairros b ON ub.Bairro_ID = b.ID
        WHERE LOWER(b.Bairro) = 'todos' AND LOWER(b.Municipio) = LOWER(?)
        """
        cursor.execute(query_upm, (mun,))
        row = cursor.fetchone()
        if row:
            mapa_mun_todos[normalizar_texto(mun)] = row[0]
        key_norm = (normalizar_texto(bai_clean), normalizar_texto(mun_clean))
        if key_norm in existentes:
            pulados += 1
        else:
            try:
                cursor.execute(
                    "INSERT INTO bairros (Bairro, Municipio) VALUES (?, ?)",
                    (bai_clean, mun_clean)
                )
                existentes.add(key_norm)
                inseridos += 1
            except Exception:
                erros += 1
                
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}


def importar_nomes_alternativos_lote(df: pd.DataFrame) -> dict:
    """Importa nomes alternativos vinculando ao ID correto do Bairro Oficial"""
    inseridos = 0
    pulados = 0
    erros = 0
    
    if df.empty:
        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Mapeamento de Bairros Oficiais em memória (Bairro, Municipio) -> ID
    cursor.execute("SELECT ID, Bairro, Municipio FROM bairros")
    bairros_map = {(str(row[1]).strip().upper(), str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}
    
    # 2. Nomes alternativos existentes em memória (Bairro_ID, Nome_Alternativo)
    cursor.execute("SELECT Bairro_ID, Nome_Alternativo FROM bairros_alternativos")
    existentes = {(row[0], str(row[1]).strip().upper()) for row in cursor.fetchall()}
    
    # 3. Processa
    for _, row in df.iterrows():
        bairro_oficial = row.get("Bairro_Oficial")
        municipio = row.get("Municipio")
        nome_alt = row.get("Nome_Alternativo")
        
        if pd.isna(bairro_oficial) or pd.isna(municipio) or pd.isna(nome_alt):
            erros += 1
            continue
            
        bai_oficial_clean = str(bairro_oficial).strip().upper()
        mun_clean = padronizar_municipio(municipio)
        nome_alt_clean = str(nome_alt).strip().upper()
        
        key_bairro = (bai_oficial_clean, mun_clean.upper())
        bairro_id = bairros_map.get(key_bairro)
        
        if not bairro_id:
            # Bairro oficial não encontrado
            erros += 1
            continue
            
        key_alt = (bairro_id, nome_alt_clean)
        if key_alt in existentes:
            pulados += 1
        else:
            try:
                cursor.execute(
                    "INSERT INTO bairros_alternativos (Bairro_ID, Nome_Alternativo) VALUES (?, ?)",
                    (bairro_id, nome_alt_clean)
                )
                existentes.add(key_alt)
                inseridos += 1
            except Exception:
                erros += 1
                
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}


def importar_upms_lote(df: pd.DataFrame) -> dict:
    """Importa UPMs, seus bairros originais e atualiza a tabela de relacionamentos (upm_bairros)"""
    inseridos = 0
    pulados = 0
    erros = 0
    
    if df.empty:
        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Carrega UPMs existentes em memória UPM -> ID
    cursor.execute("SELECT ID, UPM FROM upms")
    upms_map = {str(row[1]).strip().upper(): row[0] for row in cursor.fetchall()}
    
    # 2. Carrega Bairros existentes em memória (Bairro, Municipio) -> ID
    cursor.execute("SELECT ID, Bairro, Municipio FROM bairros")
    bairros_map = {(str(row[1]).strip().upper(), str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}
    
    # 3. Relacionamentos UPM_Bairro existentes em memória
    cursor.execute("SELECT UPM_ID, Bairro_ID FROM upm_bairros")
    rel_existentes = {(row[0], row[1]) for row in cursor.fetchall()}
    
    for _, row in df.iterrows():
        upm = row.get("UPM")
        descricao = row.get("Descricao", "")
        bairro = row.get("Bairro")
        municipio = row.get("Municipio")
        estado = row.get("Estado", "MT")
        
        if pd.isna(upm) or not str(upm).strip() or pd.isna(bairro) or pd.isna(municipio):
            erros += 1
            continue
            
        upm_clean = str(upm).strip().upper()
        desc_clean = str(descricao).strip() if not pd.isna(descricao) else ""
        bai_clean = str(bairro).strip().upper()
        mun_clean = padronizar_municipio(municipio)
        est_clean = str(estado).strip().upper()
        if len(est_clean) > 2 and " - " in est_clean:
            est_clean = est_clean.split(" - ")[0].strip()
            
        # Insere ou busca ID da UPM
        upm_id = upms_map.get(upm_clean)
        if not upm_id:
            try:
                cursor.execute(
                    "INSERT INTO upms (UPM, Descricao, Bairro, Municipio, Estado) VALUES (?, ?, ?, ?, ?)",
                    (upm_clean, desc_clean, bai_clean, mun_clean, est_clean)
                )
                upm_id = cursor.lastrowid
                upms_map[upm_clean] = upm_id
                inseridos += 1
            except Exception:
                erros += 1
                continue
        else:
            pulados += 1
            
        # Vínculo com o bairro
        key_bairro = (bai_clean, mun_clean.upper())
        bairro_id = bairros_map.get(key_bairro)
        
        if bairro_id and upm_id:
            rel_key = (upm_id, bairro_id)
            if rel_key not in rel_existentes:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO upm_bairros (UPM_ID, Bairro_ID) VALUES (?, ?)",
                        (upm_id, bairro_id)
                    )
                    rel_existentes.add(rel_key)
                except Exception:
                    pass
                    
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}


def obter_municipios_com_bairro_todos_unico() -> dict:
    """
    Retorna um dicionário mapeando municipio_normalizado -> UPM correspondente,
    para os municípios que possuem apenas UM bairro cadastrado, e esse bairro é 'TODOS'.
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # 1. Busca contagem de bairros por município
    query_contagem = """
    SELECT Municipio, COUNT(*), MAX(Bairro)
    FROM bairros
    GROUP BY Municipio
    """
    cursor.execute(query_contagem)
    municipios_elegiveis = []
    for municipio, qtd_bairros, nome_bairro in cursor.fetchall():
        if qtd_bairros == 1 and normalizar_texto(nome_bairro) == "todos":
            municipios_elegiveis.append(municipio)
            
    # 2. Mapeia a UPM de cada município elegível
    mapa_mun_todos = {}
    for mun in municipios_elegiveis:
        query_upm = """
        SELECT u.UPM
        FROM upms u
        JOIN upm_bairros ub ON u.ID = ub.UPM_ID
        JOIN bairros b ON ub.Bairro_ID = b.ID
        WHERE LOWER(b.Bairro) = 'todos' AND LOWER(b.Municipio) = LOWER(?)
        """
        cursor.execute(query_upm, (mun,))
        row = cursor.fetchone()
        if row:
            mapa_mun_todos[normalizar_texto(mun)] = row[0]
            
    conn.close()
    return mapa_mun_todos

def listar_dados(tabela):
    df = pd.read_sql(f"SELECT * FROM {tabela}", engine)
    return df

# =====================================================================
# Gerenciamento de Sessão Persistente (SROP)
# =====================================================================

def salvar_sessao(servico_id: int, session_data: dict) -> None:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Data no formato Local/Sistema
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data_str = json.dumps(session_data)
    # Criptografa os dados antes de inserir no banco
    data_cripto = criptografar_senha(data_str)
    
    # Encerra qualquer sessão ativa anterior do mesmo serviço
    cursor.execute("UPDATE servicos_sessoes SET Status = 'Substituída' WHERE Servico_ID = ? AND Status = 'Ativa'", (servico_id,))
    
    # Insere sempre uma nova linha como 'Ativa'
    cursor.execute("INSERT INTO servicos_sessoes (Servico_ID, Session_Data, Data_Login, Status) VALUES (?, ?, ?, 'Ativa')", (servico_id, data_cripto, agora))
    conn.commit()
    conn.close()

def obter_sessao_ativa(servico_id: int) -> dict:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Busca o tempo limite configurado
    cursor.execute("SELECT Tempo_Expiracao_Horas FROM servicos WHERE ID = ?", (servico_id,))
    row_ser = cursor.fetchone()
    tempo_horas = int(row_ser[0]) if row_ser else 4
    
    cursor.execute("SELECT ID, Session_Data, Data_Login FROM servicos_sessoes WHERE Servico_ID = ? AND Status = 'Ativa' ORDER BY ID DESC LIMIT 1", (servico_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
        
    sessao_db_id, session_data_cripto, data_login_str = row
    
    # Descriptografa os dados
    session_data_str = descriptografar_senha(session_data_cripto)
    if session_data_str == "Erro ao descriptografar":
        # Fallback de segurança caso a sessão já estivesse gravada em texto puro antes da atualização
        session_data_str = session_data_cripto
    
    # Valida regra de expiração configurada
    try:
        data_login = datetime.strptime(data_login_str, '%Y-%m-%d %H:%M:%S')
        limite = data_login + timedelta(hours=tempo_horas)
        if datetime.now() > limite:
            # Sessão expirada
            conn = sqlite3.connect(DB_FILE)
            conn.execute("UPDATE servicos_sessoes SET Status = ? WHERE ID = ?", (f'Expirada ({tempo_horas}h)', sessao_db_id))
            conn.commit()
            conn.close()
            return None
            
        # Adiciona a data de login no dicionário de retorno para a interface exibir
        sessao_obj = json.loads(session_data_str)
        return {
            "cookies": sessao_obj,
            "data_login": data_login
        }
    except Exception:
        # Em caso de erro de parse, encerra por segurança
        conn = sqlite3.connect(DB_FILE)
        conn.execute("UPDATE servicos_sessoes SET Status = 'Erro Parse' WHERE ID = ?", (sessao_db_id,))
        conn.commit()
        conn.close()
        return None

def limpar_sessao(servico_id: int) -> None:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE servicos_sessoes SET Status = 'Encerrada' WHERE Servico_ID = ? AND Status = 'Ativa'", (servico_id,))
    conn.commit()
    conn.close()

def excluir_historico_sessao(sessao_id: int) -> None:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM servicos_sessoes WHERE ID = ?", (sessao_id,))
    conn.commit()
    conn.close()

def limpar_historico_inativo() -> None:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM servicos_sessoes WHERE Status != 'Ativa'")
    conn.commit()
    conn.close()

def atualizar_status_sessao(sessao_id: int, status: str) -> None:
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE servicos_sessoes SET Status = ? WHERE ID = ?", (status, sessao_id))
    conn.commit()
    conn.close()
