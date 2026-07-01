import os
import time
import logging
import re
import banco as db
from dotenv import load_dotenv

# Configuração de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def anonimizar_texto(texto: str) -> str:
    """
    Substitui padrões de dados sensíveis por TAGS.
    """
    if not texto:
        return ""
        
    texto_anonimo = str(texto)
    
    # 1. CPFs (ex: 123.456.789-00 ou 12345678900)
    texto_anonimo = re.sub(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', '[CPF]', texto_anonimo)
    texto_anonimo = re.sub(r'\b\d{11}\b', '[CPF]', texto_anonimo)
    
    # 2. RGs (ex: 12.345.678-9, 12.345.678-X)
    texto_anonimo = re.sub(r'\b\d{1,2}\.\d{3}\.\d{3}-[0-9X|x]\b', '[RG]', texto_anonimo)
    
    # 3. Telefones (corrige falha de word boundary antes de parêntese)
    texto_anonimo = re.sub(r'(?:\(?\d{2}\)?\s?)?\d{4,5}-\d{4}', '[TELEFONE]', texto_anonimo)
    
    # 3.5 Emails
    texto_anonimo = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL]', texto_anonimo)
    
    # 4. Placas de Veículos (Mercosul e Antiga)
    texto_anonimo = re.sub(r'\b[A-Za-z]{3}-?\d[A-Za-z0-9]\d{2}\b', '[PLACA]', texto_anonimo)
    
    # 5. Cartões de Crédito (aproximado)
    texto_anonimo = re.sub(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b', '[CARTAO]', texto_anonimo)
    
    return texto_anonimo

try:
    from google import genai
    from google.genai import errors
    GENAI_DISPONIVEL = True
except ImportError:
    GENAI_DISPONIVEL = False
    logger.warning("google-genai não está instalado. Classificação IA não funcionará.")

# Configura o Vertex AI
load_dotenv(override=True)
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "").strip()
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1").strip()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

# Variável global em cache
_gemini_client = None

def get_gemini_client():
    global _gemini_client
    if _gemini_client:
        return _gemini_client
        
    if not GENAI_DISPONIVEL or not GCP_PROJECT_ID:
        return None
        
    try:
        import json
        from google.oauth2 import service_account
        
        # Busca a credencial no banco (serviço ativo do tipo Gemini)
        df_servicos = db.listar_dados("servicos")
        if not df_servicos.empty:
            servico_gemini = df_servicos[(df_servicos["Tipo"] == "Gemini") & (df_servicos["Status"] == "Ativo")]
            if not servico_gemini.empty:
                json_credenciais_cripto = servico_gemini.iloc[0]["Senha"]
                json_str = db.descriptografar_senha(json_credenciais_cripto)
                cred_info = json.loads(json_str)
                # O Google Vertex AI requer escopo explícito quando criamos credenciais na mão a partir de um JSON
                credentials = service_account.Credentials.from_service_account_info(
                    cred_info, 
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
                
                _gemini_client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION, credentials=credentials)
                logger.info("Credenciais do Gemini carregadas do Banco de Dados com sucesso.")
                return _gemini_client
    except Exception as e:
        logger.error(f"Erro ao carregar credenciais do Gemini do banco: {e}")
        
    # Fallback para as credenciais padrão do ambiente caso falhe ou não encontre no banco
    try:
        logger.warning("Usando Application Default Credentials para o Gemini.")
        _gemini_client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
        return _gemini_client
    except Exception as e:
        logger.error(f"Erro ao inicializar Vertex AI padrão: {e}")
        return None


def obter_categorias_formatadas(tipo: str) -> tuple[str, dict]:
    """
    Retorna uma string formatada com as categorias e descrições para injetar no prompt,
    e um dicionário com os nomes limpos (sem acentos) mapeados para a string original do banco.
    """
    categorias_str = ""
    categorias_validas = {}
    
    if tipo == "Tipo Local":
        df_tipos = db.listar_tipos_local_ativos()
        if not df_tipos.empty:
            linhas_prompt = []
            for _, row in df_tipos.iterrows():
                nome_original = str(row['Tipo_Local']).strip().upper()
                nome_limpo = db.normalizar_texto(nome_original).upper()
                desc = str(row['Descricao_IA']).strip()
                linhas_prompt.append(f"- {nome_limpo}: {desc}")
                categorias_validas[nome_limpo] = nome_original
            
            categorias_str = "\n".join(linhas_prompt)
            
    # Futuro: adicionar elif tipo == "Gravidade", etc...
    
    return categorias_str, categorias_validas

def classificar_com_retry(prompt: str, max_retries: int = 3, log_callback=None) -> str:
    """Envia o prompt para a API do Gemini com lógica de retry em caso de Rate Limit (429)"""
    client = get_gemini_client()
    
    if not client:
        return "ERRO_CONFIG: Cliente Google GenAI não inicializado. Verifique as credenciais."
        
    for tentativa in range(max_retries):
        try:
            # Em chamadas de classificação simples sem temperatura alta, reduzimos um pouco a temperatura 
            # para respostas mais consistentes
            # Envia a requisição usando o novo SDK client.models.generate_content
            response = client.models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.1
                )
            )
            # Retorna apenas o texto limpo, trata se for None
            if not response.text:
                return "NI"
            return response.text.strip().upper()
            
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Quota" in err_str or "ResourceExhausted" in err_str:
                espera = 15 * (2 ** tentativa) # 15s, 30s, 60s
                msg = f"⏳ Limite atingido. Pausando por {espera} segundos para evitar bloqueio..."
                logger.warning(msg)
                if log_callback:
                    log_callback(msg)
                time.sleep(espera)
            else:
                logger.error(f"Erro na API do Gemini: {err_str}")
                return f"ERRO_API: {err_str}"
                
    return "ERRO_RATE_LIMIT"

def classificar(tipo: str, texto: str, log_callback=None) -> str:
    """
    Função principal que o app vai chamar.
    tipo: ex "Tipo Local"
    texto: A Narrativa do BO
    """
    if not GENAI_DISPONIVEL or not GCP_PROJECT_ID:
        return "SEM_CHAVE_API"
        
    if not texto or str(texto).strip() == "" or str(texto).lower() == "nan":
        return "NI"
        
    # 1. Busca o prompt configurado no banco
    prompt_template = db.obter_prompt_ativo(tipo)
    if not prompt_template:
        return "SEM_PROMPT"
        
    # 2. Busca as categorias ativas no banco para este Tipo
    categorias_str, categorias_validas = obter_categorias_formatadas(tipo)
    if not categorias_str:
        return "SEM_CATEGORIAS"
        
    # 3. Anonimiza o texto (filtro de privacidade) e substitui os marcadores do prompt
    texto_seguro = anonimizar_texto(str(texto))
    prompt_final = prompt_template.replace("{CATEGORIAS}", categorias_str)
    prompt_final = prompt_final.replace("{TEXTO}", texto_seguro)
    
    # 3.5 Remove qualquer caractere corrompido do prompt inteiro para evitar que a IA tente copiá-los
    prompt_final = db.normalizar_texto(prompt_final)
    
    resposta_ia = classificar_com_retry(prompt_final, log_callback=log_callback)
    
    if resposta_ia.startswith("ERRO_"):
        return resposta_ia
        
    # Limpa a resposta (tira aspas, espaços)
    resposta_limpa = resposta_ia.replace('"', '').replace("'", "").strip()
    resposta_limpa_norm = db.normalizar_texto(resposta_limpa).upper()
    
    # 5. Valida se a resposta está dentro das permitidas mapeadas
    if resposta_limpa_norm in categorias_validas:
        return categorias_validas[resposta_limpa_norm]
        
    import difflib
    # Tenta aproximação em caso de pequenos erros
    matches = difflib.get_close_matches(resposta_limpa_norm, list(categorias_validas.keys()), n=1, cutoff=0.7)
    if matches:
        return categorias_validas[matches[0]]
        
    # Se a IA respondeu NI ou algo não reconhecido
    if resposta_limpa == "NI":
        return "NI"
        
    return "NI" # Fallback conservador se a IA inventar palavras
