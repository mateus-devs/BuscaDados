import os
import psycopg2
import time
from playwright.sync_api import sync_playwright

def verificar_erro_portal(page) -> str:
    """
    Verifica se há alguma mensagem de erro visível na página do Keycloak ou portal e retorna o texto.
    """
    seletores = [
        "#input-error",
        ".alert-error",
        ".kc-feedback-text",
        ".alert-danger",
        ".alert",
        ".error-message"
    ]
    for sel in seletores:
        try:
            el = page.locator(sel)
            if el.count() > 0 and el.first.is_visible():
                txt = el.first.inner_text().strip()
                if txt:
                    return txt
        except Exception:
            pass
    return ""

def aguardar_resultado_login(page, dupla_autenticacao: bool, timeout_ms: int = 15000) -> str:
    """
    Aguarda após o envio das credenciais.
    Retorna:
    - 'otp' se a tela de MFA (Dupla Autenticação) apareceu.
    - 'sucesso' se o login foi concluído e redirecionado (URL mudou).
    - 'erro: <mensagem>' se um erro de login foi detectado.
    - 'timeout' se esgotar o tempo.
    """
    start_time = time.time()
    while (time.time() - start_time) * 1000 < timeout_ms:
        # 1. Verifica se há erro na tela
        erro = verificar_erro_portal(page)
        if erro:
            return f"erro: {erro}"
            
        # 2. Verifica se o campo OTP apareceu
        try:
            otp_field = page.locator("#otp")
            if otp_field.count() > 0 and otp_field.first.is_visible():
                return "otp"
        except Exception:
            pass
        
        # 3. Verifica se fomos redirecionados para fora do Keycloak (sucesso)
        if "protocol/openid-connect" not in page.url and "/auth/" not in page.url:
            return "sucesso"
            
        time.sleep(0.2)
        
    return "timeout"

def realizar_login_srop(
    url_login: str,
    usuario: str,
    senha: str,
    codigo_mfa: str,
    dupla_autenticacao: bool,
    status_callback=None
) -> dict:
    """
    Executa o login via navegador Playwright e captura o estado da sessão (cookies).
    """
    if status_callback:
        status_callback("Iniciando navegador automatizado...")
        
    session_state = None
    
    with sync_playwright() as p:
        # Iniciamos o navegador no modo invisível (headless) conforme solicitado pelo usuário
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        # Variável para armazenar o token Bearer capturado do tráfego do SPA
        captured_token = {"value": None}
        
        def handle_request(request):
            if "/srop-api/" in request.url:
                auth_header = request.headers.get("authorization")
                if auth_header and "bearer" in auth_header.lower():
                    captured_token["value"] = auth_header

        page.on("request", handle_request)
        
        # 1. Acesso à tela de login
        if status_callback:
            status_callback("Acessando a tela de login...")
        try:
            page.goto(url_login, timeout=45000)
        except Exception as e:
            browser.close()
            raise Exception(f"Erro ao acessar a página de login: {str(e)}. Verifique a conexão ou a URL cadastrada.")
            
        # 2. Preenchimento de Usuário e Senha
        try:
            page.wait_for_selector("#username", timeout=15000)
            page.fill("#username", usuario)
            page.wait_for_selector("#password", timeout=15000)
            page.fill("#password", senha)
        except Exception as e:
            browser.close()
            raise Exception("Não foi possível localizar os campos de Usuário e Senha na tela de login. Verifique se os seletores HTML foram alterados pelo portal.")
            
        if status_callback:
            status_callback("Enviando credenciais de acesso...")
            
        try:
            page.click("#kc-login")
        except Exception as e:
            browser.close()
            raise Exception(f"Erro ao clicar no botão de login: {str(e)}")
            
        # 3. Tratamento de Dupla Autenticação (MFA)
        if status_callback:
            status_callback("Validando credenciais...")
            
        resultado = aguardar_resultado_login(page, dupla_autenticacao)
        
        if resultado.startswith("erro:"):
            erro_msg = resultado.split("erro:", 1)[1].strip()
            browser.close()
            raise Exception(f"Erro no Login: {erro_msg}")
        elif resultado == "timeout":
            browser.close()
            raise Exception("Tempo esgotado ao aguardar validação das credenciais pelo portal.")
        elif resultado == "otp":
            if not dupla_autenticacao:
                browser.close()
                raise Exception("O portal solicitou Dupla Autenticação (MFA), mas esta opção está desativada nas configurações do serviço.")
            
            try:
                if status_callback:
                    status_callback("Preenchendo código de Dupla Autenticação (MFA)...")
                page.fill("#otp", codigo_mfa)
                
                # Clica no botão Entrar da tela de OTP
                page.click("#kc-login")
                
                # Aguarda redirecionamento ou erro do MFA
                start_time = time.time()
                mfa_sucesso = False
                while (time.time() - start_time) < 15:
                    erro_mfa = verificar_erro_portal(page)
                    if erro_mfa:
                        browser.close()
                        raise Exception(f"Erro na Autenticação (MFA): {erro_mfa}")
                    
                    if "protocol/openid-connect" not in page.url and "/auth/" not in page.url:
                        mfa_sucesso = True
                        break
                    time.sleep(0.2)
                    
                if not mfa_sucesso:
                    browser.close()
                    raise Exception("Erro ao validar Dupla Autenticação (MFA): Tempo esgotado para login.")
            except Exception as e:
                browser.close()
                if "Erro na Autenticação" in str(e):
                    raise e
                raise Exception(f"Erro ao preencher ou submeter o código MFA: {str(e)}")
        elif resultado == "sucesso":
            # Já logou e redirecionou sem precisar de MFA
            pass
                
        # 4. Verificação de login e carregamento do portal
        try:
            # Tenta aguardar a rede ociosa para carregamento do frontend SROP
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
            
        if status_callback:
            status_callback("Registrando sessão segura no portal...")
            
        # Pausa obrigatória para garantir que o Javascript do portal SROP grave
        # todos os cookies de sessão corretamente antes de fecharmos o navegador.
        time.sleep(4)
            
        # Captura os cookies e armazenamento local do contexto de sessão
        if status_callback:
            status_callback("Salvando credenciais da sessão...")
        session_state = context.storage_state()
        
        # Injeta o token interceptado diretamente no estado da sessão para ser usado na consulta
        if captured_token["value"]:
            session_state["srop_bearer_token"] = captured_token["value"]
            
        # DEBUG: Salvar o estado da sessão em um arquivo para análise de tokens/cookies
        try:
            import json
            import os
            debug_path = os.path.join(os.path.dirname(__file__), "scratch", "debug_session.json")
            os.makedirs(os.path.dirname(debug_path), exist_ok=True)
            with open(debug_path, "w", encoding="utf-8") as f:
                json.dump(session_state, f, indent=2)
        except Exception:
            pass
        
        # Fecha navegador de forma limpa
        browser.close()
        
    return session_state

def consultar_e_baixar_srop(
    session_state: dict,
    url_consulta: str,
    url_pdf_template: str,
    data_inicial: str,
    data_final: str,
    temp_dir: str,
    status_callback=None,
    id_municipio: str = None,
    size: int = None,
    numero_boletim: str = None,
    data_ini_fato: str = None,
    data_fim_fato: str = None
) -> list[str]:
    """
    Executa a consulta e download dos PDFs em segundo plano utilizando os cookies da sessão persistida.
    Detecta automaticamente se a sessão expirou.
    """
    if status_callback:
        status_callback("Iniciando consulta em segundo plano...")
        
    pdf_paths = []
    
    with sync_playwright() as p:
        # Iniciamos o navegador no modo invisível (headless) utilizando os cookies salvos
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session_state)
        
        # Formatação da URL de Consulta e requisição
        url_consulta_formatada = url_consulta.replace("{DataInicialRegistro}", data_inicial).replace("{DataFinalRegistro}", data_final)
        
        if id_municipio is not None:
            url_consulta_formatada = url_consulta_formatada.replace("{idMunicipio}", str(id_municipio))
        if size is not None:
            url_consulta_formatada = url_consulta_formatada.replace("{size}", str(size))
            
        # Condicional para número do boletim
        if numero_boletim:
            url_consulta_formatada = url_consulta_formatada.replace("{numeroBoletimOcorrencia}", str(numero_boletim))
        else:
            url_consulta_formatada = url_consulta_formatada.replace("&numeroBoletimOcorrencia={numeroBoletimOcorrencia}", "")
            url_consulta_formatada = url_consulta_formatada.replace("?numeroBoletimOcorrencia={numeroBoletimOcorrencia}", "?")
            url_consulta_formatada = url_consulta_formatada.replace("numeroBoletimOcorrencia={numeroBoletimOcorrencia}", "")
            
        # Condicional para data inicial do fato
        if data_ini_fato:
            url_consulta_formatada = url_consulta_formatada.replace("{DataInicialFato}", str(data_ini_fato))
        else:
            url_consulta_formatada = url_consulta_formatada.replace("&DataInicialFato={DataInicialFato}", "")
            url_consulta_formatada = url_consulta_formatada.replace("?DataInicialFato={DataInicialFato}", "?")
            url_consulta_formatada = url_consulta_formatada.replace("DataInicialFato={DataInicialFato}", "")
            
        # Condicional para data final do fato
        if data_fim_fato:
            url_consulta_formatada = url_consulta_formatada.replace("{DataFinalFato}", str(data_fim_fato))
        else:
            url_consulta_formatada = url_consulta_formatada.replace("&DataFinalFato={DataFinalFato}", "")
            url_consulta_formatada = url_consulta_formatada.replace("?DataFinalFato={DataFinalFato}", "?")
            url_consulta_formatada = url_consulta_formatada.replace("DataFinalFato={DataFinalFato}", "")
            
        # Limpa possíveis restos de formatação na URL
        url_consulta_formatada = url_consulta_formatada.replace("?&", "?")
        url_consulta_formatada = url_consulta_formatada.rstrip("&").rstrip("?")
        
        # Exibe a URL gerada no console de comando e no status do Streamlit
        print(f"\n[LOG SROP] URL de Consulta Montada: {url_consulta_formatada}\n")
        if status_callback:
            status_callback(f"URL de Consulta: {url_consulta_formatada}")
            status_callback("Verificando sessão e consultando Boletins de Ocorrência...")
            
        # Prepara os headers com o token Bearer caso tenha sido capturado
        headers = {}
        if "srop_bearer_token" in session_state:
            headers["Authorization"] = session_state["srop_bearer_token"]
            
        # Faz a chamada da API utilizando a sessão de cookies compartilhada e o token Bearer
        try:
            response = context.request.get(url_consulta_formatada, headers=headers)
            
            # Detecta se a sessão expirou (HTTP 401/403 ou se retornou HTML de login do Keycloak)
            if response.status in [401, 403]:
                raise Exception("Sessão expirada")
                
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                raise Exception("Sessão expirada")
                
            json_data = response.json()
        except Exception as e:
            browser.close()
            if "Sessão expirada" in str(e):
                raise Exception("Sessão expirada. Por favor, realize o login novamente.")
            raise Exception(f"Erro ao obter dados de consulta: {str(e)}. Verifique se a URL de consulta é válida.")
            
        # Extração dos números de BOs
        content = json_data.get("content", [])
        if not content:
            browser.close()
            if status_callback:
                status_callback("Nenhum registro encontrado no período selecionado.")
            return []
            
        bo_numeros = []
        for item in content:
            numero = item.get("numeroBoletimOcorrencia")
            if numero:
                bo_numeros.append(str(numero).strip())
                
        # Garante lista única mantendo a ordem original da consulta
        bo_numeros = list(dict.fromkeys(bo_numeros))
        total_bo = len(bo_numeros)
        
        if status_callback:
            status_callback(f"Encontrado(s) {total_bo} boletim(s) de ocorrência. Iniciando downloads...")
            
        # Cria a pasta temporária de downloads se não existir
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download de cada PDF
        for idx, numero in enumerate(bo_numeros):
            pdf_url = url_pdf_template.replace("{numero}", numero)
            if status_callback:
                status_callback(f"Baixando PDF {idx+1}/{total_bo} (BO: {numero})...")
                
            try:
                pdf_response = context.request.get(pdf_url, headers=headers)
                if pdf_response.status == 200:
                    dest_path = os.path.join(temp_dir, f"{numero.replace('.', '_')}.pdf")
                    with open(dest_path, "wb") as f:
                        f.write(pdf_response.body())
                    pdf_paths.append(dest_path)
                else:
                    if status_callback:
                        status_callback(f"⚠️ Alerta: Falha ao baixar PDF do BO {numero} (HTTP {pdf_response.status})")
            except Exception as e:
                if status_callback:
                    status_callback(f"⚠️ Alerta: Erro ao baixar PDF do BO {numero}: {str(e)}")
                    
        # Fechar navegador
        browser.close()
        
    return pdf_paths

def encerrar_sessao_srop(session_state: dict, url_login: str) -> None:
    """Abre o navegador invisível, entra com a sessão ativa e tenta clicar em Realizar Logoff para encerrar a sessão na SESP."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session_state)
        page = context.new_page()
        
        try:
            page.goto(url_login, timeout=30000)
            page.wait_for_load_state('networkidle', timeout=15000)
            
            # Tenta encontrar e clicar no botão de logoff
            logoff_btn = page.locator("text=Realizar Logoff")
            if logoff_btn.count() > 0:
                logoff_btn.first.click(timeout=5000)
                # Aguarda para garantir que o request de logout foi finalizado no servidor
                page.wait_for_timeout(2000)
            else:
                # Fallback, tenta outras strings comuns caso o nome exato falhe por capitalização
                for fallback_text in ["LOGOFF", "Sair", "Desconectar"]:
                    fallback_btn = page.locator(f"text={fallback_text}")
                    if fallback_btn.count() > 0:
                        fallback_btn.first.click(timeout=5000)
                        page.wait_for_timeout(2000)
                        break
        except Exception as e:
            pass # Ignora erros de timeout, pois a limpeza local do banco é garantida
        finally:
            browser.close()

def testar_conexao_srop(session_state: dict, url_consulta: str) -> bool:
    """Testa se a sessão do SROP está viva fazendo uma requisição mínima."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session_state)
        
        headers = {}
        if "srop_bearer_token" in session_state:
            headers["Authorization"] = session_state["srop_bearer_token"]
            
        try:
            from datetime import datetime
            hoje = datetime.now().strftime("%Y-%m-%d")
            url_consulta_formatada = url_consulta.replace("{DataInicialRegistro}", hoje).replace("{DataFinalRegistro}", hoje)
            
            response = context.request.get(url_consulta_formatada, headers=headers)
            
            if response.status in [401, 403]:
                return False
                
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type:
                return False
                
            return True
        except Exception:
            return False
        finally:
            browser.close()
