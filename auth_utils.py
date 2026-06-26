import requests
import jwt
import urllib.parse
import streamlit as st

# =====================================================================
# CONFIGURAÇÕES DO KEYCLOAK (Provedor de Identidade - SSO)
# =====================================================================
# Endereço onde o servidor Keycloak está rodando. Em produção (VPS), 
# isso seria o IP ou domínio real (ex: https://auth.buscadados.com)
KEYCLOAK_URL = "http://localhost:8080"

# O 'Realm' é o "ambiente" ou "banco de dados" isolado dentro do Keycloak.
# Nós criamos o 'buscadados' para não misturar com os usuários Master do sistema.
REALM = "buscadados"

# O 'Client ID' é como o seu aplicativo Python se identifica para o Keycloak.
# O Keycloak só aceita logins que venham de aplicativos conhecidos (cadastrados nele).
CLIENT_ID = "buscadados-app"

# A URL exata para onde o Keycloak deve devolver o usuário depois que ele
# digitar a senha corretamente. O Keycloak bloqueia qualquer devolução 
# para sites desconhecidos por segurança (para evitar roubo de token).
REDIRECT_URI = "http://localhost:8501/"


def get_login_url():
    """
    PASSO 1 DO LOGIN: Gera a URL que vai abrir a tela de usuário e senha.
    Essa URL aponta diretamente para o Keycloak.
    """
    auth_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/auth"
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code", # Pede para o Keycloak devolver um 'código de autorização' provisório
        "scope": "openid profile email roles" # O que queremos saber do usuário (nome, email, cargo)
    }
    # Monta a URL completa com os parâmetros (ex: http://localhost:8080/.../auth?client_id=...)
    return f"{auth_url}?{urllib.parse.urlencode(params)}"

def get_logout_url(id_token):
    """
    ENCERRAMENTO DE SESSÃO: Gera a URL para avisar o Keycloak que o usuário 
    clicou em 'Sair' e que ele deve invalidar a sessão atual.
    """
    logout_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/logout"
    params = {
        "id_token_hint": id_token, # Manda a identidade atual para o Keycloak saber quem está saindo
        "post_logout_redirect_uri": REDIRECT_URI # Devolve para a tela inicial do Streamlit após sair
    }
    return f"{logout_url}?{urllib.parse.urlencode(params)}"

def exchange_code_for_token(code):
    """
    PASSO 2 DO LOGIN: Quando o usuário acerta a senha no Keycloak, o Keycloak 
    redireciona de volta para o Streamlit colocando um '?code=123xyz' na URL.
    
    Por segurança, esse 'código' dura apenas segundos. O Streamlit (aqui nos bastidores)
    pega esse código e bate na porta do Keycloak para trocá-lo pelo 'Crachá Oficial' 
    do usuário (chamado de Access Token / JWT).
    """
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    payload = {
        "grant_type": "authorization_code", # Estamos trocando um código de autorização
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "code": code # O código temporário capturado da URL
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # Faz uma requisição 'invisível' (API) para o Keycloak
    response = requests.post(token_url, data=payload, headers=headers)
    if response.status_code == 200:
        return response.json() # Devolve os Tokens (Access Token e ID Token)
    else:
        st.error(f"Erro ao obter token: {response.text}")
        return None

def decode_token(access_token):
    """
    PASSO 3 DO LOGIN: O Token de Acesso (JWT) recebido é um texto longo cheio de letras
    aleatórias. Ele é um JSON criptografado. Esta função decodifica o texto para 
    podermos ler o que tem dentro (Nome, E-mail, Cargos).
    """
    try:
        # options={"verify_signature": False} é usado aqui porque a comunicação de rede é local.
        # NUNCA use 'False' em produção externa! Lá, o código deve buscar a "Chave Pública" 
        # oficial do Keycloak para validar que o token não foi falsificado por um hacker.
        decoded = jwt.decode(access_token, options={"verify_signature": False})
        return decoded
    except Exception as e:
        st.error(f"Erro ao decodificar token: {e}")
        return None

def get_user_info(decoded_token):
    """
    PASSO 4 DO LOGIN: Extrai as informações úteis de dentro do crachá (Token decodificado)
    para o nosso aplicativo usar mais facilmente (ex: para saber se a pessoa é Admin).
    """
    if not decoded_token:
        return None
        
    roles = []
    # No padrão do Keycloak, os cargos (roles) ficam escondidos dentro da gaveta 'realm_access'
    realm_access = decoded_token.get("realm_access", {})
    if isinstance(realm_access, dict):
        roles = realm_access.get("roles", [])
        
    return {
        "name": decoded_token.get("name", "Usuário"),
        "email": decoded_token.get("email", ""),
        "preferred_username": decoded_token.get("preferred_username", ""),
        "roles": roles, # Uma lista com todos os cargos (ex: ['Admin', 'Operador'])
        
        # Cria atalhos booleanos (Verdadeiro ou Falso) para facilitar a vida no app.py
        "is_admin": "Admin" in roles,
        "is_operador": "Operador" in roles
    }
