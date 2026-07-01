import psycopg2
from psycopg2.extensions import register_adapter, AsIs
import numpy as np

register_adapter(np.int64, AsIs)
register_adapter(np.int32, AsIs)
register_adapter(np.int16, AsIs)
register_adapter(np.int8, AsIs)
register_adapter(np.float64, AsIs)
register_adapter(np.float32, AsIs)
register_adapter(np.bool_, AsIs)
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



import urllib.parse


COLUNAS_MAP = {
    'id': 'ID',
    'municipio': 'Municipio',
    'municipio_id': 'Municipio_ID',
    'estado': 'Estado',
    'bairro': 'Bairro',
    'upm': 'UPM',
    'descricao': 'Descricao',
    'nome': 'Nome',
    'urllogin': 'UrlLogin',
    'urlconsulta': 'UrlConsulta',
    'urlpdf': 'UrlPdf',
    'login': 'Login',
    'senha': 'Senha',
    'duplaautenticacao': 'DuplaAutenticacao',
    'tipo': 'Tipo',
    'status': 'Status',
    'tempo_expiracao_horas': 'Tempo_Expiracao_Horas',
    'layout_id': 'Layout_ID',
    'nome_layout': 'Nome_Layout',
    'nome_grupo': 'Nome_Grupo',
    'ordem': 'Ordem',
    'ordem_excel': 'Ordem_Excel',
    'tem_itens': 'Tem_Itens',
    'grupo_id': 'Grupo_ID',
    'nome_item_excel': 'Nome_Item_Excel',
    'palavra_busca': 'Palavra_Busca',
    'exportar_excel': 'Exportar_Excel',
    'bairro_id': 'Bairro_ID',
    'upm_id': 'UPM_ID',
    'nome_alternativo': 'Nome_Alternativo',
    'servico_id': 'Servico_ID',
    'session_data': 'Session_Data',
    'data_login': 'Data_Login',
    'bairro_oficial': 'Bairro_Oficial',
    'bairroid': 'BairroID',
    'vinculoid': 'VinculoID',
    'tipo_local': 'Tipo_Local',
    'descricao_ia': 'Descricao_IA',
    'instrucao': 'Instrucao',
    'exibir_no_menu': 'Exibir_No_Menu',
    'id_municipio_srop': 'id_municipio_srop'
}

def ajustar_colunas(df):
    if not df.empty:
        df.rename(columns=COLUNAS_MAP, inplace=True)
    return df

db_pass = urllib.parse.quote_plus(os.getenv('DB_PASSWORD', ''))
CONN_STR = f"postgresql+psycopg2://{os.getenv('DB_USER')}:{db_pass}@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"

engine = create_engine(CONN_STR)

def obter_conexao():
    return engine.raw_connection()



import streamlit as st



@st.cache_resource

def inicializar_banco():

    """Cria as tabelas estruturadas com restrições NOT NULL se o banco for novo"""

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # Tabela de Municípios

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS municipios (
        ID SERIAL PRIMARY KEY,
        Municipio TEXT NOT NULL,
        Estado TEXT NOT NULL,
        id_municipio_srop VARCHAR(50) DEFAULT NULL
    )
    """)
    cursor.execute("ALTER TABLE municipios ADD COLUMN IF NOT EXISTS id_municipio_srop VARCHAR(50) DEFAULT NULL;")

    

    # Tabela de Bairros

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS bairros (

        ID SERIAL PRIMARY KEY,

        Bairro TEXT NOT NULL,

        Municipio_ID INTEGER NOT NULL,

        CONSTRAINT fk_bairros_municipio
            FOREIGN KEY (Municipio_ID) REFERENCES municipios(ID)
            ON UPDATE CASCADE ON DELETE RESTRICT

    )

    """)

    

    # Tabela de UPMs

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS upms (

        ID SERIAL PRIMARY KEY,

        UPM TEXT NOT NULL,

        Descricao TEXT NOT NULL DEFAULT '',

        Municipio_ID INTEGER,

        CONSTRAINT fk_upms_municipio
            FOREIGN KEY (Municipio_ID) REFERENCES municipios(ID)
            ON UPDATE CASCADE ON DELETE SET NULL

    )

    """)



    # Tabela de vínculo entre UPMs e Bairros

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS upm_bairros (

        ID SERIAL PRIMARY KEY,

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

        ID SERIAL PRIMARY KEY,

        Bairro_ID INTEGER NOT NULL,

        Nome_Alternativo TEXT NOT NULL,

        UNIQUE(Bairro_ID, Nome_Alternativo),

        FOREIGN KEY(Bairro_ID) REFERENCES bairros(ID) ON DELETE CASCADE

    )

    """)



    # Tabela de Serviços

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS servicos (

        ID SERIAL PRIMARY KEY,

        Nome TEXT NOT NULL,

        UrlLogin TEXT NOT NULL,

        UrlConsulta TEXT NOT NULL,

        UrlPdf TEXT NOT NULL,

        Login TEXT NOT NULL,

        Senha TEXT NOT NULL,

        DuplaAutenticacao TEXT NOT NULL DEFAULT 'Não',

        Tipo TEXT NOT NULL DEFAULT 'SROP',

        Status TEXT NOT NULL DEFAULT 'Ativo',

        Tempo_Expiracao_Horas INTEGER NOT NULL DEFAULT 4,
        Exibir_No_Menu TEXT NOT NULL DEFAULT 'Sim'

    )

    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS servicos_sessoes (
        ID SERIAL PRIMARY KEY,
        Servico_ID INTEGER NOT NULL,
        Session_Data TEXT NOT NULL,
        Data_Login TEXT NOT NULL,
        Status TEXT NOT NULL DEFAULT 'Ativa',
        FOREIGN KEY(Servico_ID) REFERENCES servicos(ID)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS layouts (
        ID SERIAL PRIMARY KEY,
        Nome_Layout TEXT NOT NULL UNIQUE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS layout_grupos (
        ID SERIAL PRIMARY KEY,
        Layout_ID INTEGER NOT NULL,
        Nome_Grupo TEXT NOT NULL,
        Ordem INTEGER NOT NULL,
        Ordem_Excel INTEGER NOT NULL DEFAULT 1,
        Tem_Itens INTEGER NOT NULL DEFAULT 1,
        Exportar_Excel INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(Layout_ID) REFERENCES layouts(ID) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS layout_itens (
        ID SERIAL PRIMARY KEY,
        Grupo_ID INTEGER NOT NULL,
        Nome_Item_Excel TEXT NOT NULL,
        Palavra_Busca TEXT NOT NULL,
        Ordem INTEGER NOT NULL,
        Ordem_Excel INTEGER NOT NULL DEFAULT 1,
        Exportar_Excel INTEGER NOT NULL DEFAULT 1,
        FOREIGN KEY(Grupo_ID) REFERENCES layout_grupos(ID) ON DELETE CASCADE
    )
    """)

    # Tabela de Tipos de Local (Classificação IA)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipos_local (
        ID SERIAL PRIMARY KEY,
        Tipo_Local TEXT NOT NULL UNIQUE,
        Descricao_IA TEXT NOT NULL,
        Status TEXT NOT NULL DEFAULT 'Ativo'
    )
    """)

    # Tabela de Prompts (Classificação IA)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS prompts_ia (
        ID SERIAL PRIMARY KEY,
        Nome TEXT NOT NULL,
        Tipo TEXT NOT NULL,
        Instrucao TEXT NOT NULL,
        Status TEXT NOT NULL DEFAULT 'Ativo'
    )
    """)

    # -----------------------------------------------------------------------
    # Migração automática: adiciona Municipio_ID em bairros (banco existente)
    # -----------------------------------------------------------------------
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='bairros'")
    colunas_bai = [row[0].lower() for row in cursor.fetchall()]

    if "municipio_id" not in colunas_bai:
        # Adiciona a coluna FK (nullable temporariamente)
        cursor.execute("ALTER TABLE bairros ADD COLUMN IF NOT EXISTS Municipio_ID INTEGER")
        # Popula com base no nome do município
        cursor.execute("""
            UPDATE bairros b
            SET Municipio_ID = m.ID
            FROM municipios m
            WHERE LOWER(TRIM(b.Municipio)) = LOWER(TRIM(m.Municipio))
            AND b.Municipio_ID IS NULL
        """)
        # Torna NOT NULL somente se todos foram preenchidos
        cursor.execute("SELECT COUNT(*) FROM bairros WHERE Municipio_ID IS NULL")
        orfaos_bai = cursor.fetchone()[0]
        if orfaos_bai == 0:
            cursor.execute("ALTER TABLE bairros ALTER COLUMN Municipio_ID SET NOT NULL")
            # Adiciona FK se não existir
            cursor.execute("""
                DO $$ BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conname = 'fk_bairros_municipio' AND conrelid = 'bairros'::regclass
                    ) THEN
                        ALTER TABLE bairros
                            ADD CONSTRAINT fk_bairros_municipio
                            FOREIGN KEY (Municipio_ID) REFERENCES municipios(ID)
                            ON UPDATE CASCADE ON DELETE RESTRICT;
                    END IF;
                END $$;
            """)

    # Garante a remoção da coluna antiga de texto "Municipio" caso a migração já tenha sido concluída
    if "municipio_id" in colunas_bai and "municipio" in colunas_bai:
        cursor.execute("ALTER TABLE bairros DROP COLUMN IF EXISTS Municipio")

    # -----------------------------------------------------------------------
    # Migração automática: adiciona Municipio_ID em upms (banco existente)
    # -----------------------------------------------------------------------
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='upms'")
    colunas_upm = [row[0].lower() for row in cursor.fetchall()]

    if "municipio_id" not in colunas_upm:
        cursor.execute("ALTER TABLE upms ADD COLUMN IF NOT EXISTS Municipio_ID INTEGER")
        # Popula com base no nome do município (se coluna Municipio ainda existir)
        if "municipio" in colunas_upm:
            cursor.execute("""
                UPDATE upms u
                SET Municipio_ID = m.ID
                FROM municipios m
                WHERE LOWER(TRIM(u.Municipio)) = LOWER(TRIM(m.Municipio))
                AND u.Municipio_ID IS NULL
            """)
        # Adiciona FK se não existir
        cursor.execute("""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_upms_municipio' AND conrelid = 'upms'::regclass
                ) THEN
                    ALTER TABLE upms
                        ADD CONSTRAINT fk_upms_municipio
                        FOREIGN KEY (Municipio_ID) REFERENCES municipios(ID)
                        ON UPDATE CASCADE ON DELETE SET NULL;
                END IF;
            END $$;
        """)

    # Garante a remoção das colunas antigas de texto de upms caso a migração já tenha sido concluída
    if "municipio_id" in colunas_upm:
        for col_antiga in ['municipio', 'bairro', 'estado']:
            if col_antiga in colunas_upm:
                cursor.execute(f"ALTER TABLE upms DROP COLUMN IF EXISTS {col_antiga}")

    # -----------------------------------------------------------------------
    # Garante coluna Descricao na tabela de UPMs (banco existente)
    # -----------------------------------------------------------------------
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='upms'")
    colunas_upm = [row[0].lower() for row in cursor.fetchall()]

    if "descricao" not in colunas_upm:

        cursor.execute("ALTER TABLE upms ADD COLUMN Descricao TEXT NOT NULL DEFAULT ''")



    # Garanta as colunas novas na tabela de serviços para bancos já existentes

    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='servicos'")

    colunas_ser = [row[0] for row in cursor.fetchall()]

    if "duplaautenticacao" not in [c.lower() for c in colunas_ser]:

        cursor.execute("ALTER TABLE servicos ADD COLUMN DuplaAutenticacao TEXT NOT NULL DEFAULT 'Não'")

    col_ser_lower = [c.lower() for c in colunas_ser]

    if "tipo" not in col_ser_lower:
        cursor.execute("ALTER TABLE servicos ADD COLUMN Tipo TEXT NOT NULL DEFAULT 'SROP'")

    if "status" not in col_ser_lower:
        cursor.execute("ALTER TABLE servicos ADD COLUMN Status TEXT NOT NULL DEFAULT 'Ativo'")

    if "tempo_expiracao_horas" not in col_ser_lower:
        cursor.execute("ALTER TABLE servicos ADD COLUMN Tempo_Expiracao_Horas INTEGER NOT NULL DEFAULT 4")

    if "layout_id" not in col_ser_lower:
        cursor.execute("ALTER TABLE servicos ADD COLUMN Layout_ID INTEGER")

    # Garanta a coluna Ordem_Excel na tabela de layout_grupos
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='layout_grupos'")
    colunas_grp = [row[0].lower() for row in cursor.fetchall()]
    if "ordem_excel" not in colunas_grp:
        cursor.execute("ALTER TABLE layout_grupos ADD COLUMN Ordem_Excel INTEGER NOT NULL DEFAULT 1")
        # Copia o valor de Ordem para Ordem_Excel inicialmente
        cursor.execute("UPDATE layout_grupos SET Ordem_Excel = Ordem")

    # Garanta a coluna Ordem_Excel na tabela de layout_itens
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='layout_itens'")
    colunas_itn = [row[0].lower() for row in cursor.fetchall()]
    if "ordem_excel" not in colunas_itn:
        cursor.execute("ALTER TABLE layout_itens ADD COLUMN Ordem_Excel INTEGER NOT NULL DEFAULT 1")
        # Copia o valor de Ordem para Ordem_Excel inicialmente
        cursor.execute("UPDATE layout_itens SET Ordem_Excel = Ordem")

    

    # Migra dados antigos de UPMs para a tabela de vínculos (muitos-para-muitos)

    cursor.execute("SELECT COUNT(*) FROM upm_bairros")

    if cursor.fetchone()[0] == 0:

        cursor.execute("""

        INSERT INTO upm_bairros (UPM_ID, Bairro_ID)
        SELECT u.ID, b.ID

        FROM upms u

        JOIN bairros b ON LOWER(u.Bairro) = LOWER(b.Bairro) AND LOWER(u.Municipio) = LOWER(b.Municipio)
        ON CONFLICT (UPM_ID, Bairro_ID) DO NOTHING

        """)

    

    # Garante os metadados padrão para TODOS os layouts cadastrados (permite renomeação e ocultação)
    cursor.execute("SELECT ID, Nome_Layout FROM layouts")
    layouts_lista = cursor.fetchall()
    for l_id, l_nome in layouts_lista:
        # Busca ou cria o grupo 'METADADOS DO BO' para este layout (Ordem 0 para aparecer no topo)
        cursor.execute("SELECT ID FROM layout_grupos WHERE Layout_ID = %s AND Nome_Grupo = 'METADADOS DO BO'", (l_id,))
        grupo_meta = cursor.fetchone()
        if not grupo_meta:
            cursor.execute("INSERT INTO layout_grupos (Layout_ID, Nome_Grupo, Ordem, Tem_Itens, Exportar_Excel) VALUES (%s, 'METADADOS DO BO', 0, 1, 1) RETURNING ID", (l_id,))
            g_id = cursor.fetchone()[0]
        else:
            g_id = grupo_meta[0]
            
        # Cadastra os itens especiais de metadados padrão se não existirem
        metadados_defaults = [
            ("ARQUIVO", "*ARQUIVO*", 1, 1),
            ("BO_NUMERO", "*BO_NUMERO*", 2, 2),
            ("DATA_DO_REGISTRO", "*DATA_DO_REGISTRO*", 3, 3),
            ("HORA_DO_REGISTRO", "*HORA_DO_REGISTRO*", 4, 4)
        ]
        for nome_col, keyword, ordem, ordem_excel in metadados_defaults:
            cursor.execute("SELECT 1 FROM layout_itens WHERE Grupo_ID = %s AND Palavra_Busca = %s", (g_id, keyword))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO layout_itens (Grupo_ID, Nome_Item_Excel, Palavra_Busca, Ordem, Ordem_Excel, Exportar_Excel) VALUES (%s, %s, %s, %s, %s, 1)", (g_id, nome_col, keyword, ordem, ordem_excel))
                
    conn.commit()

    conn.close()



def listar_dados(tabela: str) -> pd.DataFrame:

    """Busca qualquer tabela do banco e retorna como um DataFrame do Pandas"""

    try:

        return ajustar_colunas(pd.read_sql(f"SELECT * FROM {tabela}", engine))

    except Exception:

        return pd.DataFrame()



def salvar_registro(tabela: str, dados_dict: dict) -> bool:

    """Insere um novo registro apenas se não for duplicado no banco"""

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    dados_salvar = dados_dict.copy()

    

    if tabela == "municipios":

        municipio = dados_salvar["Municipio"].strip()

        cursor.execute("SELECT 1 FROM municipios WHERE LOWER(Municipio) = LOWER(%s)", (municipio,))

        if cursor.fetchone():

            conn.close()

            return False 

            

    elif tabela == "bairros":

        bairro = dados_salvar["Bairro"].strip()

        municipio_id = dados_salvar.get("Municipio_ID")

        cursor.execute("SELECT 1 FROM bairros WHERE LOWER(Bairro) = LOWER(%s) AND Municipio_ID = %s", (bairro, municipio_id))

        if cursor.fetchone():

            conn.close()

            return False



    elif tabela == "upms":

        upm = dados_salvar["UPM"].strip()

        cursor.execute("SELECT 1 FROM upms WHERE LOWER(UPM) = LOWER(%s)", (upm,))

        if cursor.fetchone():

            conn.close()

            return False

            

    elif tabela == "servicos":

        nome = dados_salvar["Nome"].strip()

        cursor.execute("SELECT 1 FROM servicos WHERE LOWER(Nome) = LOWER(%s)", (nome,))

        if cursor.fetchone():

            conn.close()

            return False

        # Criptografa a senha antes de gravar no banco de dados

        if "Senha" in dados_salvar:

            dados_salvar["Senha"] = criptografar_senha(dados_salvar["Senha"])

            

    conn.close()

    

    df = pd.DataFrame([dados_salvar])

    # IMPORTANTE: Força as colunas para minúsculo para evitar erro de Case Sensitivity no PostgreSQL (UndefinedColumn)
    df.columns = df.columns.str.lower()
    
    df.to_sql(tabela, engine, if_exists='append', index=False)

    return True



def listar_bairros_com_municipio() -> pd.DataFrame:

    """Retorna todos os bairros com JOIN na tabela de municípios (nome e estado)"""

    query = """

    SELECT

        b.ID,

        b.Bairro,

        b.Municipio_ID,

        m.Municipio,

        m.Estado

    FROM bairros b

    JOIN municipios m ON b.Municipio_ID = m.ID

    ORDER BY m.Municipio, b.Bairro

    """

    try:

        return ajustar_colunas(pd.read_sql(query, engine))

    except Exception:

        return pd.DataFrame()



def listar_bairros_vinculados(upm_id: int) -> pd.DataFrame:

    query = """

    SELECT

        ub.ID AS VinculoID,

        b.ID AS BairroID,

        b.Bairro,

        b.Municipio_ID,

        m.Municipio,

        m.Estado

    FROM upm_bairros ub

    JOIN bairros b ON ub.Bairro_ID = b.ID

    JOIN municipios m ON b.Municipio_ID = m.ID

    WHERE ub.UPM_ID = %s

    ORDER BY m.Municipio, b.Bairro

    """

    return ajustar_colunas(pd.read_sql(query, engine, params=(upm_id,)))



def atualizar_vinculo_bairros(upm_id: int, bairro_ids: list) -> bool:

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    cursor.execute("DELETE FROM upm_bairros WHERE UPM_ID = %s", (upm_id,))

    for bairro_id in bairro_ids:

        cursor.execute(

            "INSERT INTO upm_bairros (UPM_ID, Bairro_ID) VALUES (%s, %s) ON CONFLICT (UPM_ID, Bairro_ID) DO NOTHING",

            (upm_id, bairro_id),

        )

    conn.commit()

    conn.close()

    return True





def obter_mapeamento_upms() -> dict:

    """Retorna um dicionário mapeando (bairro_normalizado, municipio_normalizado) -> nome_da_upm"""

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    query = """

    SELECT b.Bairro, m.Municipio, u.UPM

    FROM upms u

    JOIN upm_bairros ub ON u.ID = ub.UPM_ID

    JOIN bairros b ON ub.Bairro_ID = b.ID

    JOIN municipios m ON b.Municipio_ID = m.ID

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

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    cursor.execute("SELECT Municipio FROM municipios")

    rows = cursor.fetchall()

    conn.close()

    return {normalizar_texto(row[0]): row[0] for row in rows}





def obter_mapeamento_nomes_bairros() -> dict:

    """Retorna um dicionário mapeando (bairro_normalizado, municipio_normalizado) -> Bairro_Oficial_Do_Banco"""

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.Bairro, m.Municipio
        FROM bairros b
        JOIN municipios m ON b.Municipio_ID = m.ID
    """)

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

        conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

        df = ajustar_colunas(pd.read_sql("SELECT * FROM bairros_alternativos WHERE Bairro_ID = %s ORDER BY Nome_Alternativo", conn, params=(bairro_id,)))

        conn.close()

        return df

    except Exception:

        return pd.DataFrame()



def salvar_nome_alternativo(bairro_id: int, nome_alternativo: str) -> bool:

    """Insere um novo nome alternativo para o bairro se não for duplicado"""

    nome_alternativo = nome_alternativo.strip()

    if not nome_alternativo:

        return False

        

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    
    

    # Verifica se já existe para este bairro (case insensitive)

    cursor.execute(

        "SELECT 1 FROM bairros_alternativos WHERE Bairro_ID = %s AND LOWER(Nome_Alternativo) = LOWER(%s)",

        (bairro_id, nome_alternativo)

    )

    if cursor.fetchone():

        conn.close()

        return False

        

    cursor.execute(

        "INSERT INTO bairros_alternativos (Bairro_ID, Nome_Alternativo) VALUES (%s, %s)",

        (bairro_id, nome_alternativo)

    )

    conn.commit()

    conn.close()

    return True



def excluir_nome_alternativo(id_alternativo: int):

    """Exclui um nome alternativo do banco"""

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    
    cursor.execute("DELETE FROM bairros_alternativos WHERE ID = %s", (id_alternativo,))

    conn.commit()

    conn.close()



def obter_mapeamento_alternativo_bairros() -> dict:

    """Retorna um dicionário mapeando (bairro_alternativo_normalizado, municipio_normalizado) -> Bairro_Nome_Oficial"""

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    query = """

    SELECT ba.Nome_Alternativo, b.Bairro, m.Municipio

    FROM bairros_alternativos ba

    JOIN bairros b ON ba.Bairro_ID = b.ID

    JOIN municipios m ON b.Municipio_ID = m.ID

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

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    
    if tabela == "bairros":
        cursor.execute("DELETE FROM upm_bairros WHERE Bairro_ID = %s", (id_registro,))
        cursor.execute("DELETE FROM bairros_alternativos WHERE Bairro_ID = %s", (id_registro,))
    elif tabela == "upms":
        cursor.execute("DELETE FROM upm_bairros WHERE UPM_ID = %s", (id_registro,))

    cursor.execute(f"DELETE FROM {tabela} WHERE ID = %s", (id_registro,))

    conn.commit()

    conn.close()





def limpar_banco_dados():

    """Exclui todos os registros de todas as tabelas e reinicia os IDs autoincrementais"""

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

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

        

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # 1. Carrega municípios existentes em memória para comparação rápida

    cursor.execute("SELECT Municipio, Estado FROM municipios")

    existentes = {(str(row[0]).strip().upper(), str(row[1]).strip().upper()) for row in cursor.fetchall()}

    

    # 2. Processa as linhas

    for _, row in df.iterrows():
        municipio = row.get("Municipio")
        estado = row.get("Estado", "MT")
        
        # Suporta o nome amigável do Excel ou a coluna técnica
        id_srop = row.get("Código ID Município SROP")
        if pd.isna(id_srop):
            id_srop = row.get("Codigo ID Municipio SROP")
        if pd.isna(id_srop):
            id_srop = row.get("id_municipio_srop")
        if pd.isna(id_srop):
            id_srop = row.get("idmunicipiosrop")
            
        id_srop_clean = str(id_srop).strip().split('.')[0] if not pd.isna(id_srop) and str(id_srop).strip() else None

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
            if id_srop_clean:
                try:
                    cursor.execute("UPDATE municipios SET id_municipio_srop = %s WHERE LOWER(Municipio) = LOWER(%s) AND LOWER(Estado) = LOWER(%s)", (id_srop_clean, mun_clean, est_clean))
                    pulados += 1
                except Exception:
                    erros += 1
            else:
                pulados += 1
        else:
            try:
                cursor.execute(
                    "INSERT INTO municipios (Municipio, Estado, id_municipio_srop) VALUES (%s, %s, %s)",
                    (mun_clean, est_clean, id_srop_clean)
                )
                existentes.add(key)
                inseridos += 1
            except Exception:
                erros += 1

                

    conn.commit()

    conn.close()

    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}





def importar_bairros_lote(df: pd.DataFrame) -> dict:

    """Importa bairros a partir de um DataFrame, normalizando nomes e evitando duplicatas.
    Resolve o Municipio_ID pelo nome do município antes de inserir."""

    inseridos = 0

    pulados = 0

    erros = 0

    

    if df.empty:

        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}

        

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # 1. Carrega municípios em memória: nome_normalizado -> ID

    cursor.execute("SELECT ID, Municipio FROM municipios")

    municipios_map = {normalizar_texto(row[1]): row[0] for row in cursor.fetchall()}

    

    # 2. Carrega bairros existentes de forma normalizada (Bairro, Municipio_ID)

    cursor.execute("SELECT b.Bairro, b.Municipio_ID FROM bairros b")

    existentes = {(normalizar_texto(row[0]), row[1]) for row in cursor.fetchall()}

    

    # 3. Processa as linhas

    for _, row in df.iterrows():

        bairro = row.get("Bairro")

        municipio = row.get("Municipio")

        

        if pd.isna(bairro) or not str(bairro).strip() or pd.isna(municipio) or not str(municipio).strip():

            erros += 1

            continue

            

        # Padronização e normalização

        bai_clean = str(bairro).strip().upper()

        mun_clean = padronizar_municipio(municipio)

        mun_norm = normalizar_texto(mun_clean)

        

        # Resolve o ID do município

        municipio_id = municipios_map.get(mun_norm)

        if not municipio_id:

            erros += 1

            continue

        

        key_norm = (normalizar_texto(bai_clean), municipio_id)

        if key_norm in existentes:

            pulados += 1

        else:

            try:

                cursor.execute(

                    "INSERT INTO bairros (Bairro, Municipio_ID) VALUES (%s, %s)",

                    (bai_clean, municipio_id)

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

        

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # 1. Mapeamento de Bairros Oficiais em memória (Bairro, Municipio) -> ID

    cursor.execute("""
        SELECT b.ID, b.Bairro, m.Municipio
        FROM bairros b
        JOIN municipios m ON b.Municipio_ID = m.ID
    """)

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

                    "INSERT INTO bairros_alternativos (Bairro_ID, Nome_Alternativo) VALUES (%s, %s)",

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

    """Importa UPMs e atualiza a tabela de relacionamentos (upm_bairros).
    Resolve Municipio_ID pelo nome do município. Não armazena Bairro/Municipio/Estado como texto."""

    inseridos = 0

    pulados = 0

    erros = 0

    

    if df.empty:

        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}

        

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # 1. Carrega UPMs existentes em memória UPM -> ID

    cursor.execute("SELECT ID, UPM FROM upms")

    upms_map = {str(row[1]).strip().upper(): row[0] for row in cursor.fetchall()}

    

    # 2. Carrega Bairros existentes em memória (Bairro, Municipio_ID) -> ID

    cursor.execute("SELECT b.ID, b.Bairro, m.Municipio FROM bairros b JOIN municipios m ON b.Municipio_ID = m.ID")

    bairros_map = {(str(row[1]).strip().upper(), str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}

    

    # 3. Relacionamentos UPM_Bairro existentes em memória

    cursor.execute("SELECT UPM_ID, Bairro_ID FROM upm_bairros")

    rel_existentes = {(row[0], row[1]) for row in cursor.fetchall()}

    

    for _, row in df.iterrows():

        upm = row.get("UPM")

        descricao = row.get("Descricao", "")

        bairro = row.get("Bairro")

        municipio = row.get("Municipio")

        

        if pd.isna(upm) or not str(upm).strip() or pd.isna(bairro) or pd.isna(municipio):

            erros += 1

            continue

            

        upm_clean = str(upm).strip().upper()

        desc_clean = str(descricao).strip() if not pd.isna(descricao) else ""

        bai_clean = str(bairro).strip().upper()

        mun_clean = padronizar_municipio(municipio)

        

        # Insere ou busca ID da UPM (apenas UPM e Descricao — sem texto de município)

        upm_id = upms_map.get(upm_clean)

        if not upm_id:

            try:

                cursor.execute(

                    "INSERT INTO upms (UPM, Descricao) VALUES (%s, %s) RETURNING ID",

                    (upm_clean, desc_clean)

                )

                upm_id = cursor.fetchone()[0]

                upms_map[upm_clean] = upm_id

                inseridos += 1

            except Exception:

                erros += 1

                continue

        else:

            pulados += 1

            

        # Vínculo com o bairro via upm_bairros

        key_bairro = (bai_clean, mun_clean.upper())

        bairro_id = bairros_map.get(key_bairro)

        

        if bairro_id and upm_id:

            rel_key = (upm_id, bairro_id)

            if rel_key not in rel_existentes:

                try:

                    cursor.execute(

                        "INSERT INTO upm_bairros (UPM_ID, Bairro_ID) VALUES (%s, %s) ON CONFLICT (UPM_ID, Bairro_ID) DO NOTHING",

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

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # 1. Busca contagem de bairros por município via JOIN

    query_contagem = """

    SELECT m.Municipio, COUNT(*), MAX(b.Bairro)

    FROM bairros b

    JOIN municipios m ON b.Municipio_ID = m.ID

    GROUP BY m.ID, m.Municipio

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

        JOIN municipios m ON b.Municipio_ID = m.ID

        WHERE LOWER(b.Bairro) = 'todos' AND LOWER(m.Municipio) = LOWER(%s)

        """

        cursor.execute(query_upm, (mun,))

        row = cursor.fetchone()

        if row:

            mapa_mun_todos[normalizar_texto(mun)] = row[0]

            

    conn.close()

    return mapa_mun_todos





def importar_nomes_alternativos_lote(df: pd.DataFrame) -> dict:

    """Importa nomes alternativos vinculando ao ID correto do Bairro Oficial"""

    inseridos = 0

    pulados = 0

    erros = 0

    

    if df.empty:

        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}

        

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # 1. Mapeamento de Bairros Oficiais em memória (Bairro, Municipio) -> ID

    cursor.execute("""
        SELECT b.ID, b.Bairro, m.Municipio
        FROM bairros b
        JOIN municipios m ON b.Municipio_ID = m.ID
    """)

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

                    "INSERT INTO bairros_alternativos (Bairro_ID, Nome_Alternativo) VALUES (%s, %s)",

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

    """Importa UPMs e atualiza a tabela de relacionamentos (upm_bairros).
    Resolve Municipio_ID pelo nome do município. Não armazena Bairro/Municipio/Estado como texto."""

    inseridos = 0

    pulados = 0

    erros = 0

    

    if df.empty:

        return {"inseridos": inseridos, "pulados": pulados, "erros": erros}

        

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # 1. Carrega UPMs existentes em memória UPM -> ID

    cursor.execute("SELECT ID, UPM FROM upms")

    upms_map = {str(row[1]).strip().upper(): row[0] for row in cursor.fetchall()}

    

    # 2. Carrega Bairros existentes em memória (Bairro, Municipio) -> ID via JOIN

    cursor.execute("SELECT b.ID, b.Bairro, m.Municipio FROM bairros b JOIN municipios m ON b.Municipio_ID = m.ID")

    bairros_map = {(str(row[1]).strip().upper(), str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}

    

    # 3. Relacionamentos UPM_Bairro existentes em memória

    cursor.execute("SELECT UPM_ID, Bairro_ID FROM upm_bairros")

    rel_existentes = {(row[0], row[1]) for row in cursor.fetchall()}

    

    for _, row in df.iterrows():

        upm = row.get("UPM")

        descricao = row.get("Descricao", "")

        bairro = row.get("Bairro")

        municipio = row.get("Municipio")

        

        if pd.isna(upm) or not str(upm).strip() or pd.isna(bairro) or pd.isna(municipio):

            erros += 1

            continue

            

        upm_clean = str(upm).strip().upper()

        desc_clean = str(descricao).strip() if not pd.isna(descricao) else ""

        bai_clean = str(bairro).strip().upper()

        mun_clean = padronizar_municipio(municipio)

        

        # Insere ou busca ID da UPM (apenas UPM e Descricao — sem texto de município)

        upm_id = upms_map.get(upm_clean)

        if not upm_id:

            try:

                cursor.execute(

                    "INSERT INTO upms (UPM, Descricao) VALUES (%s, %s) RETURNING ID",

                    (upm_clean, desc_clean)

                )

                upm_id = cursor.fetchone()[0]

                upms_map[upm_clean] = upm_id

                inseridos += 1

            except Exception:

                erros += 1

                continue

        else:

            pulados += 1

            

        # Vínculo com o bairro via upm_bairros

        key_bairro = (bai_clean, mun_clean.upper())

        bairro_id = bairros_map.get(key_bairro)

        

        if bairro_id and upm_id:

            rel_key = (upm_id, bairro_id)

            if rel_key not in rel_existentes:

                try:

                    cursor.execute(

                        "INSERT INTO upm_bairros (UPM_ID, Bairro_ID) VALUES (%s, %s) ON CONFLICT (UPM_ID, Bairro_ID) DO NOTHING",

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

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # 1. Busca contagem de bairros por município via JOIN

    query_contagem = """

    SELECT m.Municipio, COUNT(*), MAX(b.Bairro)

    FROM bairros b

    JOIN municipios m ON b.Municipio_ID = m.ID

    GROUP BY m.ID, m.Municipio

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

        JOIN municipios m ON b.Municipio_ID = m.ID

        WHERE LOWER(b.Bairro) = 'todos' AND LOWER(m.Municipio) = LOWER(%s)

        """

        cursor.execute(query_upm, (mun,))

        row = cursor.fetchone()

        if row:

            mapa_mun_todos[normalizar_texto(mun)] = row[0]

            

    conn.close()

    return mapa_mun_todos



def importar_servicos_lote(df) -> dict:
    """Importa serviços mantendo a criptografia e atualizando registros existentes pelo Nome"""
    inseridos = pulados = erros = 0
    if df.empty: return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
    import psycopg2, pandas as pd
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT ID, Nome, Senha FROM servicos")
    existentes = {str(row[1]).strip().upper(): (row[0], row[2]) for row in cursor.fetchall()}
    for _, row in df.iterrows():
        nome = row.get("Nome")
        if pd.isna(nome):
            erros += 1; continue
        nome_clean = str(nome).strip()
        nome_upper = nome_clean.upper()
        url_login = str(row.get("UrlLogin", "")).strip() if not pd.isna(row.get("UrlLogin")) else ""
        url_consulta = str(row.get("UrlConsulta", "")).strip() if not pd.isna(row.get("UrlConsulta")) else ""
        url_pdf = str(row.get("UrlPdf", "")).strip() if not pd.isna(row.get("UrlPdf")) else ""
        login = str(row.get("Login", "")).strip() if not pd.isna(row.get("Login")) else ""
        senha = str(row.get("Senha", "")).strip() if not pd.isna(row.get("Senha")) else ""
        dupla = str(row.get("DuplaAutenticacao", "Não")).strip() if not pd.isna(row.get("DuplaAutenticacao")) else "Não"
        tipo = str(row.get("Tipo", "SROP")).strip() if not pd.isna(row.get("Tipo")) else "SROP"
        status = str(row.get("Status", "Ativo")).strip() if not pd.isna(row.get("Status")) else "Ativo"
        exibir_menu = str(row.get("Exibir_No_Menu", "Sim")).strip() if not pd.isna(row.get("Exibir_No_Menu")) else "Sim"
        senha_final = senha
        if senha:
            teste_desc = descriptografar_senha(senha)
            if teste_desc == "Erro ao descriptografar":
                senha_final = criptografar_senha(senha)
        if nome_upper in existentes:
            id_existente, _ = existentes[nome_upper]
            try:
                cursor.execute("UPDATE servicos SET UrlLogin=%s, UrlConsulta=%s, UrlPdf=%s, Login=%s, Senha=%s, DuplaAutenticacao=%s, Tipo=%s, Status=%s, Exibir_No_Menu=%s WHERE ID=%s",
                    (url_login, url_consulta, url_pdf, login, senha_final, dupla, tipo, status, exibir_menu, id_existente))
                pulados += 1
            except: erros += 1
        else:
            try:
                cursor.execute("INSERT INTO servicos (Nome, UrlLogin, UrlConsulta, UrlPdf, Login, Senha, DuplaAutenticacao, Tipo, Status, Exibir_No_Menu) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (nome_clean, url_login, url_consulta, url_pdf, login, senha_final, dupla, tipo, status, exibir_menu))
                inseridos += 1
            except: erros += 1
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}

def importar_layouts_lote(df) -> dict:
    inseridos = pulados = erros = 0
    if df.empty: return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
    import psycopg2, pandas as pd
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT ID, Nome_Layout FROM layouts")
    existentes = {str(row[1]).strip().upper(): row[0] for row in cursor.fetchall()}
    for _, row in df.iterrows():
        nome = str(row.get("Nome_Layout", "")).strip()
        if not nome or pd.isna(row.get("Nome_Layout")):
            erros += 1; continue
        nome_upper = nome.upper()
        if nome_upper in existentes:
            pulados += 1
        else:
            try:
                cursor.execute("INSERT INTO layouts (Nome_Layout) VALUES (%s)", (nome,))
                inseridos += 1
                existentes[nome_upper] = cursor.lastrowid
            except: erros += 1
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}

def importar_grupos_lote(df) -> dict:
    inseridos = pulados = erros = 0
    if df.empty: return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
    import psycopg2, pandas as pd
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT ID, Nome_Layout FROM layouts")
    layouts_map = {str(row[1]).strip().upper(): row[0] for row in cursor.fetchall()}
    cursor.execute("SELECT ID, Layout_ID, Nome_Grupo FROM layout_grupos")
    existentes = {(row[1], str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}
    for _, row in df.iterrows():
        if pd.isna(row.get("Nome_Layout")) or pd.isna(row.get("Nome_Grupo")):
            erros += 1; continue
        nome_layout = str(row.get("Nome_Layout", "")).strip().upper()
        nome_grupo = str(row.get("Nome_Grupo", "")).strip().upper()
        ordem = int(row.get("Ordem", 1)) if not pd.isna(row.get("Ordem")) else 1
        ordem_excel = int(row.get("Ordem_Excel", ordem)) if not pd.isna(row.get("Ordem_Excel")) else ordem
        tem_itens = int(row.get("Tem_Itens", 1)) if not pd.isna(row.get("Tem_Itens")) else 1
        exportar = int(row.get("Exportar_Excel", 1)) if not pd.isna(row.get("Exportar_Excel")) else 1
        layout_id = layouts_map.get(nome_layout)
        if not layout_id:
            erros += 1; continue
        key = (layout_id, nome_grupo)
        if key in existentes:
            try:
                cursor.execute("UPDATE layout_grupos SET Ordem=%s, Ordem_Excel=%s, Tem_Itens=%s, Exportar_Excel=%s WHERE ID=%s", (ordem, ordem_excel, tem_itens, exportar, existentes[key]))
                pulados += 1
            except: erros += 1
        else:
            try:
                cursor.execute("INSERT INTO layout_grupos (Layout_ID, Nome_Grupo, Ordem, Ordem_Excel, Tem_Itens, Exportar_Excel) VALUES (%s, %s, %s, %s, %s, %s)", (layout_id, nome_grupo, ordem, ordem_excel, tem_itens, exportar))
                inseridos += 1
                existentes[key] = cursor.lastrowid
            except: erros += 1
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}

def importar_itens_lote(df) -> dict:
    inseridos = pulados = erros = 0
    if df.empty: return {"inseridos": inseridos, "pulados": pulados, "erros": erros}
    import psycopg2, pandas as pd
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT ID, Nome_Layout FROM layouts")
    layouts_map = {str(row[1]).strip().upper(): row[0] for row in cursor.fetchall()}
    cursor.execute("SELECT ID, Layout_ID, Nome_Grupo FROM layout_grupos")
    grupos_map = {(row[1], str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}
    cursor.execute("SELECT ID, Grupo_ID, Nome_Item_Excel FROM layout_itens")
    existentes = {(row[1], str(row[2]).strip().upper()): row[0] for row in cursor.fetchall()}
    for _, row in df.iterrows():
        if pd.isna(row.get("Nome_Layout")) or pd.isna(row.get("Nome_Grupo")) or pd.isna(row.get("Nome_Item_Excel")) or pd.isna(row.get("Palavra_Busca")):
            erros += 1; continue
        nome_layout = str(row.get("Nome_Layout", "")).strip().upper()
        nome_grupo = str(row.get("Nome_Grupo", "")).strip().upper()
        nome_item = str(row.get("Nome_Item_Excel", "")).strip().upper()
        palavra = str(row.get("Palavra_Busca", "")).strip()
        ordem = int(row.get("Ordem", 1)) if not pd.isna(row.get("Ordem")) else 1
        ordem_excel = int(row.get("Ordem_Excel", ordem)) if not pd.isna(row.get("Ordem_Excel")) else ordem
        exportar = int(row.get("Exportar_Excel", 1)) if not pd.isna(row.get("Exportar_Excel")) else 1
        layout_id = layouts_map.get(nome_layout)
        if not layout_id:
            erros += 1; continue
        grupo_id = grupos_map.get((layout_id, nome_grupo))
        if not grupo_id:
            erros += 1; continue
        key = (grupo_id, nome_item)
        if key in existentes:
            try:
                cursor.execute("UPDATE layout_itens SET Palavra_Busca=%s, Ordem=%s, Ordem_Excel=%s, Exportar_Excel=%s WHERE ID=%s", (palavra, ordem, ordem_excel, exportar, existentes[key]))
                pulados += 1
            except: erros += 1
        else:
            try:
                cursor.execute("INSERT INTO layout_itens (Grupo_ID, Nome_Item_Excel, Palavra_Busca, Ordem, Ordem_Excel, Exportar_Excel) VALUES (%s, %s, %s, %s, %s, %s)", (grupo_id, nome_item, palavra, ordem, ordem_excel, exportar))
                inseridos += 1
                existentes[key] = cursor.lastrowid
            except: erros += 1
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "pulados": pulados, "erros": erros}

def listar_dados(tabela):


    df = ajustar_colunas(pd.read_sql(f"SELECT * FROM {tabela}", engine))

    return df



# =====================================================================

# Gerenciamento de Sessão Persistente (SROP)

# =====================================================================



def salvar_sessao(servico_id: int, session_data: dict) -> None:

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    # Data no formato Local/Sistema

    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    data_str = json.dumps(session_data)

    # Criptografa os dados antes de inserir no banco

    data_cripto = criptografar_senha(data_str)

    

    # Encerra qualquer sessão ativa anterior do mesmo serviço

    cursor.execute("UPDATE servicos_sessoes SET Status = 'Substituída' WHERE Servico_ID = %s AND Status = 'Ativa'", (servico_id,))

    

    # Insere sempre uma nova linha como 'Ativa'

    cursor.execute("INSERT INTO servicos_sessoes (Servico_ID, Session_Data, Data_Login, Status) VALUES (%s, %s, %s, 'Ativa')", (servico_id, data_cripto, agora))

    conn.commit()

    conn.close()



def obter_sessao_ativa(servico_id: int) -> dict:

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    

    # Busca o tempo limite configurado

    cursor.execute("SELECT Tempo_Expiracao_Horas FROM servicos WHERE ID = %s", (servico_id,))

    row_ser = cursor.fetchone()

    tempo_horas = int(row_ser[0]) if row_ser else 4

    

    cursor.execute("SELECT ID, Session_Data, Data_Login FROM servicos_sessoes WHERE Servico_ID = %s AND Status = 'Ativa' ORDER BY ID DESC LIMIT 1", (servico_id,))

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

            conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

            cursor = conn.cursor()
            cursor.execute("UPDATE servicos_sessoes SET Status = %s WHERE ID = %s", (f'Expirada ({tempo_horas}h)', sessao_db_id))

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

        conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

        cursor = conn.cursor()
        cursor.execute("UPDATE servicos_sessoes SET Status = 'Erro Parse' WHERE ID = %s", (sessao_db_id,))

        conn.commit()

        conn.close()

        return None



def limpar_sessao(servico_id: int) -> None:

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    cursor.execute("UPDATE servicos_sessoes SET Status = 'Encerrada' WHERE Servico_ID = %s AND Status = 'Ativa'", (servico_id,))

    conn.commit()

    conn.close()



def excluir_historico_sessao(sessao_id: int) -> None:

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    cursor.execute("DELETE FROM servicos_sessoes WHERE ID = %s", (sessao_id,))

    conn.commit()

    conn.close()



def limpar_historico_inativo() -> None:

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    cursor.execute("DELETE FROM servicos_sessoes WHERE Status != 'Ativa'")

    conn.commit()

    conn.close()



def atualizar_status_sessao(sessao_id: int, status: str) -> None:

    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))

    cursor = conn.cursor()

    cursor.execute("UPDATE servicos_sessoes SET Status = %s WHERE ID = %s", (status, sessao_id))

    conn.commit()

    conn.close()

# ==========================================
# CRUD DE LAYOUTS DINMICOS (OCR)
# ==========================================

def listar_layouts() -> pd.DataFrame:
    try:
        return ajustar_colunas(pd.read_sql("SELECT * FROM layouts ORDER BY Nome_Layout", engine))
    except:
        return pd.DataFrame()

def salvar_layout(nome: str) -> bool:
    nome = nome.strip()
    if not nome: return False
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM layouts WHERE LOWER(Nome_Layout) = LOWER(%s)", (nome,))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("INSERT INTO layouts (Nome_Layout) VALUES (%s)", (nome,))
    conn.commit()
    conn.close()
    return True

def atualizar_nome_layout(layout_id: int, novo_nome: str) -> bool:
    novo_nome = novo_nome.strip()
    if not novo_nome: return False
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM layouts WHERE LOWER(Nome_Layout) = LOWER(%s) AND ID != %s", (novo_nome, layout_id))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("UPDATE layouts SET Nome_Layout = %s WHERE ID = %s", (novo_nome, layout_id))
    conn.commit()
    conn.close()
    return True

def excluir_layout(layout_id: int) -> bool:
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM servicos WHERE Layout_ID = %s", (layout_id,))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("DELETE FROM layouts WHERE ID = %s", (layout_id,))
    conn.commit()
    conn.close()
    return True

def clonar_layout(layout_id: int, novo_nome: str) -> bool:
    novo_nome = novo_nome.strip()
    if not novo_nome:
        return False
    
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    
    try:
        # 1. Verifica se já existe um layout com o novo nome
        cursor.execute("SELECT 1 FROM layouts WHERE LOWER(Nome_Layout) = LOWER(%s)", (novo_nome,))
        if cursor.fetchone():
            conn.close()
            return False
        
        # 2. Cria o novo layout
        cursor.execute("INSERT INTO layouts (Nome_Layout) VALUES (%s) RETURNING ID", (novo_nome,))
        novo_layout_id = cursor.fetchone()[0]
        
        # 3. Busca os grupos do layout original
        cursor.execute("""
            SELECT ID, Nome_Grupo, Ordem, Ordem_Excel, Tem_Itens, Exportar_Excel 
            FROM layout_grupos 
            WHERE Layout_ID = %s
        """, (layout_id,))
        grupos_origem = cursor.fetchall()
        
        for g_id, g_nome, g_ordem, g_ordem_excel, g_tem_itens, g_exportar in grupos_origem:
            # 4. Insere o grupo no novo layout
            cursor.execute("""
                INSERT INTO layout_grupos (Layout_ID, Nome_Grupo, Ordem, Ordem_Excel, Tem_Itens, Exportar_Excel) 
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING ID
            """, (novo_layout_id, g_nome, g_ordem, g_ordem_excel, g_tem_itens, g_exportar))
            novo_grupo_id = cursor.fetchone()[0]
            
            # 5. Busca os itens desse grupo original
            cursor.execute("""
                SELECT Nome_Item_Excel, Palavra_Busca, Ordem, Ordem_Excel, Exportar_Excel 
                FROM layout_itens 
                WHERE Grupo_ID = %s
            """, (g_id,))
            itens_origem = cursor.fetchall()
            
            for i_nome, i_palavra, i_ordem, i_ordem_excel, i_exportar in itens_origem:
                # 6. Insere o item associado ao novo grupo
                cursor.execute("""
                    INSERT INTO layout_itens (Grupo_ID, Nome_Item_Excel, Palavra_Busca, Ordem, Ordem_Excel, Exportar_Excel) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (novo_grupo_id, i_nome, i_palavra, i_ordem, i_ordem_excel, i_exportar))
                
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.rollback()
        conn.close()
        return False

def listar_grupos(layout_id: int) -> pd.DataFrame:
    try:
        return ajustar_colunas(pd.read_sql("SELECT * FROM layout_grupos WHERE Layout_ID = %s ORDER BY Ordem", engine, params=(layout_id,)))
    except:
        return pd.DataFrame()

def salvar_grupo(layout_id: int, nome: str, ordem: int, tem_itens: int, exportar_excel: int = 1, ordem_excel: int = None) -> bool:
    if ordem_excel is None:
        ordem_excel = ordem
    nome = nome.strip().upper()
    if not nome: return False
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM layout_grupos WHERE Layout_ID = %s AND Nome_Grupo = %s", (layout_id, nome))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("INSERT INTO layout_grupos (Layout_ID, Nome_Grupo, Ordem, Ordem_Excel, Tem_Itens, Exportar_Excel) VALUES (%s, %s, %s, %s, %s, %s)", 
                   (layout_id, nome, ordem, ordem_excel, tem_itens, exportar_excel))
    conn.commit()
    conn.close()
    return True

def atualizar_grupo(grupo_id: int, layout_id: int, nome: str, ordem: int, tem_itens: int, exportar_excel: int = 1, ordem_excel: int = None) -> bool:
    if ordem_excel is None:
        ordem_excel = ordem
    nome = nome.strip().upper()
    if not nome: return False
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM layout_grupos WHERE Layout_ID = %s AND Nome_Grupo = %s AND ID != %s", (layout_id, nome, grupo_id))
    if cursor.fetchone():
        conn.close()
        return False
    cursor.execute("UPDATE layout_grupos SET Nome_Grupo = %s, Ordem = %s, Ordem_Excel = %s, Tem_Itens = %s, Exportar_Excel = %s WHERE ID = %s", 
                   (nome, ordem, ordem_excel, tem_itens, exportar_excel, grupo_id))
    conn.commit()
    conn.close()
    return True

def excluir_grupo(grupo_id: int) -> bool:
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM layout_grupos WHERE ID = %s", (grupo_id,))
    conn.commit()
    conn.close()
    return True

def resetar_ordenacao_grupo(grupo_id: int) -> bool:
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    try:
        cursor = conn.cursor()
        # Reseta os itens do grupo para Ordem = 1 e Ordem_Excel = 1
        cursor.execute("UPDATE layout_itens SET Ordem = 1, Ordem_Excel = 1 WHERE Grupo_ID = %s", (grupo_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erro ao resetar ordenacao do grupo: {e}")
        return False
    finally:
        conn.close()

def listar_itens(grupo_id: int) -> pd.DataFrame:
    try:
        return ajustar_colunas(pd.read_sql("SELECT * FROM layout_itens WHERE Grupo_ID = %s ORDER BY Ordem", engine, params=(grupo_id,)))
    except:
        return pd.DataFrame()

def validar_nome_coluna_layout(layout_id: int, nome_coluna: str) -> bool:
    nome_coluna = nome_coluna.strip().upper()
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    query = """
    SELECT 1 
    FROM layout_itens li
    JOIN layout_grupos lg ON li.Grupo_ID = lg.ID
    WHERE lg.Layout_ID = %s AND UPPER(li.Nome_Item_Excel) = %s
    """
    cursor.execute(query, (layout_id, nome_coluna))
    existe = cursor.fetchone() is not None
    conn.close()
    return not existe

def salvar_item(layout_id: int, grupo_id: int, nome_item_excel: str, palavra_busca: str, ordem: int, exportar_excel: int = 1, ordem_excel: int = None) -> bool:
    if ordem_excel is None:
        ordem_excel = ordem
    nome_item_excel = nome_item_excel.strip().upper()
    palavra_busca = palavra_busca.strip()
    if not nome_item_excel or not palavra_busca: return False
    
    if not validar_nome_coluna_layout(layout_id, nome_item_excel):
        return False
        
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("INSERT INTO layout_itens (Grupo_ID, Nome_Item_Excel, Palavra_Busca, Ordem, Ordem_Excel, Exportar_Excel) VALUES (%s, %s, %s, %s, %s, %s)", 
                   (grupo_id, nome_item_excel, palavra_busca, ordem, ordem_excel, exportar_excel))
    conn.commit()
    conn.close()
    return True

def atualizar_exportacao_item(item_id: int, exportar_excel: int) -> bool:
    try:
        import psycopg2
        conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
        cursor = conn.cursor()
        cursor.execute("UPDATE layout_itens SET Exportar_Excel = %s WHERE ID = %s", (exportar_excel, item_id))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def atualizar_item(item_id: int, layout_id: int, nome_item_excel: str, palavra_busca: str, ordem: int, exportar_excel: int = 1, ordem_excel: int = None) -> bool:
    if ordem_excel is None:
        ordem_excel = ordem
    nome_item_excel = nome_item_excel.strip().upper()
    palavra_busca = palavra_busca.strip()
    if not nome_item_excel or not palavra_busca: return False
    
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute('''
        SELECT COUNT(1) FROM layout_itens i
        JOIN layout_grupos g ON i.Grupo_ID = g.ID
        WHERE g.Layout_ID = %s AND i.Nome_Item_Excel = %s AND i.ID != %s
    ''', (layout_id, nome_item_excel, item_id))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False
        
    cursor.execute("UPDATE layout_itens SET Nome_Item_Excel = %s, Palavra_Busca = %s, Ordem = %s, Ordem_Excel = %s, Exportar_Excel = %s WHERE ID = %s", 
                   (nome_item_excel, palavra_busca, ordem, ordem_excel, exportar_excel, item_id))
    conn.commit()
    conn.close()
    return True

def excluir_item(item_id: int) -> bool:
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    cursor.execute("DELETE FROM layout_itens WHERE ID = %s", (item_id,))
    conn.commit()
    conn.close()
    return True

# ==========================================
# Funções CRUD: Tipos de Local (IA)
# ==========================================

def listar_tipos_local() -> pd.DataFrame:
    try:
        return ajustar_colunas(pd.read_sql("SELECT * FROM tipos_local ORDER BY Tipo_Local", engine))
    except:
        return pd.DataFrame()

def listar_tipos_local_ativos() -> pd.DataFrame:
    try:
        return ajustar_colunas(pd.read_sql("SELECT * FROM tipos_local WHERE Status = 'Ativo' ORDER BY Tipo_Local", engine))
    except:
        return pd.DataFrame()

def salvar_tipo_local(tipo_local: str, descricao_ia: str, status: str = 'Ativo') -> bool:
    tipo_local = tipo_local.strip().upper()
    if not tipo_local or not descricao_ia: return False
    
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM tipos_local WHERE Tipo_Local = %s", (tipo_local,))
    if cursor.fetchone():
        conn.close()
        return False
        
    cursor.execute("INSERT INTO tipos_local (Tipo_Local, Descricao_IA, Status) VALUES (%s, %s, %s)", 
                   (tipo_local, descricao_ia, status))
    conn.commit()
    conn.close()
    return True

def atualizar_tipo_local(tipo_id: int, tipo_local: str, descricao_ia: str, status: str) -> bool:
    tipo_local = tipo_local.strip().upper()
    if not tipo_local or not descricao_ia: return False
    
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM tipos_local WHERE Tipo_Local = %s AND ID != %s", (tipo_local, tipo_id))
    if cursor.fetchone():
        conn.close()
        return False
        
    cursor.execute("UPDATE tipos_local SET Tipo_Local = %s, Descricao_IA = %s, Status = %s WHERE ID = %s", 
                   (tipo_local, descricao_ia, status, tipo_id))
    conn.commit()
    conn.close()
    return True

def excluir_tipo_local(tipo_id: int) -> bool:
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tipos_local WHERE ID = %s", (tipo_id,))
    conn.commit()
    conn.close()
    return True

def obter_set_tipos_local() -> set:
    """Retorna um set com os nomes (em maiúsculo) de todos os tipos locais ativos para validação rápida"""
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute("SELECT Tipo_Local FROM tipos_local WHERE Status = 'Ativo'")
    resultados = cursor.fetchall()
    conn.close()
    return {row[0].strip().upper() for row in resultados}

# ==========================================
# Funções CRUD: Prompts IA
# ==========================================

def listar_prompts() -> pd.DataFrame:
    try:
        return ajustar_colunas(pd.read_sql("SELECT * FROM prompts_ia ORDER BY Tipo", engine))
    except:
        return pd.DataFrame()

def salvar_prompt(nome: str, tipo: str, instrucao: str, status: str = 'Ativo') -> bool:
    nome = nome.strip()
    tipo = tipo.strip()
    if not nome or not tipo or not instrucao: return False
    
    conn = obter_conexao()
    cursor = conn.cursor()
    
    # Se o novo for ativo, desativa os outros do mesmo Tipo
    if status == 'Ativo':
        cursor.execute("UPDATE prompts_ia SET Status = 'Inativo' WHERE Tipo = %s", (tipo,))
        
    cursor.execute("INSERT INTO prompts_ia (Nome, Tipo, Instrucao, Status) VALUES (%s, %s, %s, %s)", 
                   (nome, tipo, instrucao, status))
    conn.commit()
    conn.close()
    return True

def atualizar_prompt(prompt_id: int, nome: str, tipo: str, instrucao: str, status: str) -> bool:
    nome = nome.strip()
    tipo = tipo.strip()
    if not nome or not tipo or not instrucao: return False
    
    conn = obter_conexao()
    cursor = conn.cursor()
    
    # Se mudar para ativo, desativa os outros do mesmo Tipo
    if status == 'Ativo':
        cursor.execute("UPDATE prompts_ia SET Status = 'Inativo' WHERE Tipo = %s AND ID != %s", (tipo, prompt_id))
        
    cursor.execute("UPDATE prompts_ia SET Nome = %s, Tipo = %s, Instrucao = %s, Status = %s WHERE ID = %s", 
                   (nome, tipo, instrucao, status, prompt_id))
    conn.commit()
    conn.close()
    return True

def excluir_prompt(prompt_id: int) -> bool:
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM prompts_ia WHERE ID = %s", (prompt_id,))
    conn.commit()
    conn.close()
    return True

def obter_prompt_ativo(tipo: str) -> str:
    """Retorna a instrução do prompt ativo para o dado Tipo"""
    conn = obter_conexao()
    cursor = conn.cursor()
    cursor.execute("SELECT Instrucao FROM prompts_ia WHERE Tipo = %s AND Status = 'Ativo' LIMIT 1", (tipo,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

# ==========================================
# Funções de Importação em Lote (Excel)
# ==========================================

def importar_tipos_local_lote(df: pd.DataFrame) -> dict:
    conn = obter_conexao()
    cursor = conn.cursor()
    inseridos = 0
    atualizados = 0
    erros = 0
    
    for _, row in df.iterrows():
        try:
            tipo = str(row.get("Tipo_Local", "")).strip().upper()
            descricao = str(row.get("Descricao_IA", "")).strip()
            status = str(row.get("Status", "Ativo")).strip()
            
            if not tipo or not descricao:
                erros += 1
                continue
                
            cursor.execute("SELECT ID FROM tipos_local WHERE Tipo_Local = %s", (tipo,))
            existe = cursor.fetchone()
            
            if existe:
                cursor.execute("UPDATE tipos_local SET Descricao_IA = %s, Status = %s WHERE ID = %s", 
                               (descricao, status, existe[0]))
                atualizados += 1
            else:
                cursor.execute("INSERT INTO tipos_local (Tipo_Local, Descricao_IA, Status) VALUES (%s, %s, %s)", 
                               (tipo, descricao, status))
                inseridos += 1
        except:
            erros += 1
            
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "atualizados": atualizados, "erros": erros}

def importar_prompts_ia_lote(df: pd.DataFrame) -> dict:
    conn = obter_conexao()
    cursor = conn.cursor()
    inseridos = 0
    atualizados = 0
    erros = 0
    
    for _, row in df.iterrows():
        try:
            nome = str(row.get("Nome", "")).strip()
            tipo = str(row.get("Tipo", "")).strip()
            instrucao = str(row.get("Instrucao", "")).strip()
            status = str(row.get("Status", "Ativo")).strip()
            
            if not nome or not tipo or not instrucao:
                erros += 1
                continue
                
            cursor.execute("SELECT ID FROM prompts_ia WHERE Nome = %s AND Tipo = %s", (nome, tipo))
            existe = cursor.fetchone()
            
            if status == 'Ativo':
                cursor.execute("UPDATE prompts_ia SET Status = 'Inativo' WHERE Tipo = %s", (tipo,))
            
            if existe:
                cursor.execute("UPDATE prompts_ia SET Instrucao = %s, Status = %s WHERE ID = %s", 
                               (instrucao, status, existe[0]))
                atualizados += 1
            else:
                cursor.execute("INSERT INTO prompts_ia (Nome, Tipo, Instrucao, Status) VALUES (%s, %s, %s, %s)", 
                               (nome, tipo, instrucao, status))
                inseridos += 1
        except:
            erros += 1
            
    conn.commit()
    conn.close()
    return {"inseridos": inseridos, "atualizados": atualizados, "erros": erros}

def sincronizar_sequencias() -> None:
    """Sincroniza as sequências do PostgreSQL com os IDs máximos das tabelas."""
    conn = psycopg2.connect(host=os.getenv('DB_HOST'), port=os.getenv('DB_PORT'), dbname=os.getenv('DB_NAME'), user=os.getenv('DB_USER'), password=os.getenv('DB_PASSWORD'))
    cursor = conn.cursor()
    tables = [
        'municipios', 'bairros', 'upms', 'servicos', 'servicos_sessoes', 
        'layouts', 'layout_grupos', 'layout_itens', 'bairros_alternativos', 
        'upm_bairros', 'tipos_local', 'prompts_ia'
    ]
    for t in tables:
        try:
            seq_name = f"{t}_id_seq"
            cursor.execute(f"SELECT setval('{seq_name}', COALESCE((SELECT MAX(id) FROM {t}), 0) + 1, false);")
        except:
            conn.rollback()
    conn.commit()
    conn.close()

def listar_grupos_excel(layout_id: int) -> pd.DataFrame:
    """Busca grupos de um layout ordenados pela Ordem_Excel (ordem de colunas)."""
    try:
        return ajustar_colunas(pd.read_sql("SELECT * FROM layout_grupos WHERE Layout_ID = %s ORDER BY Ordem_Excel", engine, params=(layout_id,)))
    except:
        return pd.DataFrame()

def listar_itens_excel(grupo_id: int) -> pd.DataFrame:
    """Busca itens de um grupo ordenados pela Ordem_Excel (ordem de colunas)."""
    try:
        return ajustar_colunas(pd.read_sql("SELECT * FROM layout_itens WHERE Grupo_ID = %s ORDER BY Ordem_Excel", engine, params=(grupo_id,)))
    except:
        return pd.DataFrame()
