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

def classificar_com_retry(prompt: str, max_retries: int = 5, log_callback=None) -> str:
    """Envia o prompt para a API do Gemini com lógica de retry, tratando Timeout, 429, 500 e 503."""
    import random
    client = get_gemini_client()
    
    if not client:
        return "ERRO_CONFIG: Cliente Google GenAI não inicializado. Verifique as credenciais."
        
    for tentativa in range(max_retries):
        try:
            # Em chamadas de classificação simples sem temperatura alta, reduzimos um pouco a temperatura 
            # para respostas mais consistentes
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
            err_str = str(e).lower()
            # Captura os erros especificados pelo usuário: 429, 500, 503, timeout
            termos_instabilidade = ["429", "500", "503", "quota", "resourceexhausted", "timeout", "deadline"]
            if any(term in err_str for term in termos_instabilidade):
                # Exponential backoff base 2 iniciando em 2s (2, 4, 8, 16, 32...)
                espera = 2 ** (tentativa + 1)
                msg = f"⏳ Falha de conexão ou Rate Limit (Erro). Pausando por {espera}s (Tentativa {tentativa+1}/{max_retries})..."
                logger.warning(msg)
                if log_callback:
                    log_callback(msg)
                time.sleep(espera)
            else:
                logger.error(f"Erro desconhecido na API do Gemini: {err_str}")
                return f"ERRO_API: {str(e)}"
                
    msg_falha_final = f"ERRO_TENTATIVAS_ESGOTADAS: O lote falhou seguidamente após {max_retries} tentativas."
    logger.error(msg_falha_final)
    if log_callback:
        log_callback(f"❌ {msg_falha_final}")
    return "ERRO_MAX_RETRIES"

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

def classificar_em_lote(tipo: str, itens: list[tuple[int, str]], log_callback=None) -> dict[int, str]:
    """
    Classifica um array de ocorrências em uma única requisição.
    itens: Lista de tuplas (num_tarefa, texto_da_narrativa)
    Retorna: Dicionário onde a chave é num_tarefa e o valor é a Classificação (novo_tipo)
    """
    import pandas as pd
    
    if not GENAI_DISPONIVEL or not GCP_PROJECT_ID:
        return {id_: "SEM_CHAVE_API" for id_, _ in itens}
        
    if not itens:
        return {}
        
    prompt_template = db.obter_prompt_ativo(tipo)
    if not prompt_template:
        return {id_: "SEM_PROMPT" for id_, _ in itens}
        
    categorias_str, categorias_validas = obter_categorias_formatadas(tipo)
    if not categorias_str:
        return {id_: "SEM_CATEGORIAS" for id_, _ in itens}
        
    bloco_textos = ""
    for id_, texto in itens:
        texto_seg = anonimizar_texto(str(texto)) if pd.notna(texto) else ""
        if not texto_seg.strip():
            texto_seg = "VAZIO"
        bloco_textos += f"[ID_LOTE: {id_}]\nTEXTO: {texto_seg}\n\n"
        
    prompt_final = prompt_template.replace("{CATEGORIAS}", categorias_str)
    prompt_final = prompt_final.replace("{TEXTO}", bloco_textos)
    prompt_final = db.normalizar_texto(prompt_final)
    
    instrucao_lote = """
ATENÇÃO MÁXIMA AO "id": Você está recebendo ocorrências identificadas por [ID_LOTE: X].
O valor da chave "id" no seu JSON DEVE SER EXATAMENTE O NÚMERO X QUE VEIO NO TEXTO. 
NUNCA reinicie a contagem para 1. Se você recebeu [ID_LOTE: 36], você deve devolver "id": 36.

Você DEVE retornar a sua resposta EXCLUSIVAMENTE em formato JSON (um Array de Objetos) com as chaves:
- "id": O número exato do ID_LOTE avaliado.
- "classificacao": O nome exato da categoria escolhida (ou "NI" se não classificar).

NÃO RETORNE MAIS NADA ALÉM DO JSON. NÃO PONHA EXPLICAÇÕES EM TEXTO.
Exemplo de formato (SE VOCÊ RECEBEU OS IDs 36 e 37):
[
  {"id": 36, "classificacao": "VIA PÚBLICA"},
  {"id": 37, "classificacao": "À COMÉRCIO"}
]
"""
    prompt_final += "\n" + instrucao_lote
    
    resposta_ia = classificar_com_retry(prompt_final, log_callback=log_callback)
    
    if resposta_ia.startswith("ERRO_"):
        return {id_: resposta_ia for id_, _ in itens}
        
    import json
    import difflib
    
    # Extração super-robusta garantindo que pegamos o array JSON ignorando "conversa" da IA
    start_idx = resposta_ia.find('[')
    end_idx = resposta_ia.rfind(']')
    
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        resposta_json_limpa = resposta_ia[start_idx:end_idx+1]
    else:
        # Tenta achar um objeto puro caso ele não tenha gerado lista
        start_obj = resposta_ia.find('{')
        end_obj = resposta_ia.rfind('}')
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            resposta_json_limpa = resposta_ia[start_obj:end_obj+1]
        else:
            resposta_json_limpa = resposta_ia
            
    retorno = {}
    try:
        resultados = json.loads(resposta_json_limpa)
        if not isinstance(resultados, list):
            resultados = [resultados] # Fallback se retornou um único objeto
            
        for item in resultados:
            # Pega chaves ignorando se vieram maiúsculas, minúsculas ou com acento
            chave_id = next((k for k in item.keys() if str(k).lower().strip() == "id"), None)
            chave_class = next((k for k in item.keys() if str(k).lower().strip() in ["classificacao", "classificação"]), None)
            
            val_id = item.get(chave_id, -1) if chave_id else -1
            id_ = int(val_id)
            
            val_class = item.get(chave_class, "NI") if chave_class else "NI"
            classificacao = str(val_class).replace('"', '').replace("'", "").strip()
            
            resposta_limpa_norm = db.normalizar_texto(classificacao).upper()
            if resposta_limpa_norm in categorias_validas:
                retorno[id_] = categorias_validas[resposta_limpa_norm]
            else:
                matches = difflib.get_close_matches(resposta_limpa_norm, list(categorias_validas.keys()), n=1, cutoff=0.7)
                if matches:
                    retorno[id_] = categorias_validas[matches[0]]
                else:
                    retorno[id_] = "NI"
                    
    except Exception as e:
        logger.error(f"Erro no parse do JSON do lote: {e}. Resposta: {resposta_ia}")
        resposta_encurtada = resposta_ia.replace('\n', ' ')
        return {id_: f"ERRO_JSON_MALFORMADO | RAW: {resposta_encurtada}" for id_, _ in itens}
        
    # Proteção Cega Avançada: Se a IA "viciou" e reiniciou a contagem para 1,2,3... mas entregou todos os itens perfeitamente:
    if len(retorno) > 0 and len(retorno) == len(itens):
        ids_originais = [i[0] for i in itens]
        ids_retornados = sorted(list(retorno.keys()))
        # Se ela reiniciou a contagem em vez de usar os originais (e nós não estamos no Lote 1)
        if ids_retornados == list(range(1, len(itens) + 1)) and ids_originais[0] != 1:
            # Remapeia pareando em ordem sequencial
            novo_retorno = {}
            for original_id, fake_id in zip(ids_originais, ids_retornados):
                novo_retorno[original_id] = retorno[fake_id]
            retorno = novo_retorno

    # Garantir que todos os IDs enviados tenham uma resposta final
    for id_, _ in itens:
        if id_ not in retorno:
            resposta_encurtada = resposta_ia.replace('\n', ' ')
            retorno[id_] = f"ERRO_IA_OMITIU_ITEM | RAW: {resposta_encurtada}"
            
    return retorno
