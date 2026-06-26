import streamlit as st
import pandas as pd
import banco as db
import sqlite3
from datetime import datetime

# Configuração global da página do Streamlit
st.set_page_config(page_title="BuscaDados", layout="wide", initial_sidebar_state="expanded")

# Inicializa o arquivo de banco de dados SQLite e cria as tabelas se não existirem
db.inicializar_banco()

# --- ESTILIZAÇÃO CUSTOMIZADA DO MENU LATERAL (CSS INJECT) ---
st.markdown("""
    <style>
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label {
            background-color: rgba(248, 249, 250, 0.9) !important;
            padding: 12px 18px !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
            border: 1px solid rgba(233, 236, 239, 0.8) !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02) !important;
            transition: all 0.15s ease-out !important;
            cursor: pointer !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label:hover {
            background-color: rgba(255, 255, 255, 1) !important;
            border-color: rgba(255, 75, 75, 0.3) !important;
            transform: translateX(5px) translateY(-1px) !important;
            box-shadow: 4px 4px 10px rgba(255, 75, 75, 0.1) !important;
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label[data-checked="true"] {
            background: linear-gradient(135deg, #ff4b4b 0%, #e82c2c 100%) !important;
            border-color: #ff4b4b !important;
            color: white !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 15px rgba(255, 75, 75, 0.4) !important;
            transform: scale(1.02) !important;
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label[data-checked="true"]:hover {
            transform: scale(1.03) translateX(3px) !important;
            box-shadow: 0 6px 20px rgba(255, 75, 75, 0.6) !important;
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label span[data-testid="stRadioButtonChoiceIndicator"] {
            display: none !important;
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label div[data-testid="stWidgetMarkdownInsideRadio"] {
            padding-left: 0px !important;
            margin-left: 0px !important;
            font-size: 1.05rem !important;
            letter-spacing: 0.3px !important;
        }
        
        /* --- CORREÇÕES VISUAIS DA GRADE (GRID) E PAGINAÇÃO --- */
        /* Alinha botões e textos da grade centralizados verticalmente */
        div[data-testid="stHorizontalBlock"] {
            align-items: center !important;
        }
        /* Deixa os botões da tabela mais achatados para diminuir a altura inútil da linha */
        div[data-testid="stHorizontalBlock"] button {
            min-height: 36px !important;
            padding-top: 0px !important;
            padding-bottom: 0px !important;
        }
        /* Estiliza o dropdown de paginação para combinar com os botões brancos */
        div[data-testid="stSelectbox"] > div[data-baseweb="select"] > div {
            min-height: 36px !important;
            border-radius: 8px !important;
            border: 1px solid rgba(49, 51, 63, 0.2) !important;
        }
    </style>
""", unsafe_allow_html=True)

import auth_utils

# --- CONTROLE DE MENSAGENS E ESTADOS ---
if "mensagem_sucesso" not in st.session_state: st.session_state.mensagem_sucesso = None
if "menu_override" not in st.session_state: st.session_state.menu_override = None
if "radio_selecionado" not in st.session_state: st.session_state.radio_selecionado = "🗺️ Manutenção de Municípios"

if "sub_tela_mun" not in st.session_state: st.session_state.sub_tela_mun = "listar"
if "sub_tela_bai" not in st.session_state: st.session_state.sub_tela_bai = "listar"
if "sub_tela_upm" not in st.session_state: st.session_state.sub_tela_upm = "listar"
if "sub_tela_ser" not in st.session_state: st.session_state.sub_tela_ser = "listar"

if "modo_form_mun" not in st.session_state: st.session_state.modo_form_mun = "cadastro"
if "modo_form_bai" not in st.session_state: st.session_state.modo_form_bai = "cadastro"
if "modo_form_upm" not in st.session_state: st.session_state.modo_form_upm = "cadastro"
if "modo_form_ser" not in st.session_state: st.session_state.modo_form_ser = "cadastro"

if "dados_sel_mun" not in st.session_state: st.session_state.dados_sel_mun = {"ID": None, "Municipio": "", "Estado": "MT - Mato Grosso"}
if "dados_sel_bai" not in st.session_state: st.session_state.dados_sel_bai = {"ID": None, "Bairro": "", "Municipio": ""}
if "dados_sel_upm" not in st.session_state: st.session_state.dados_sel_upm = {"ID": None, "UPM": "", "Descricao": "", "Bairro": "", "Municipio": "", "Estado": ""}
if "dados_sel_ser" not in st.session_state: st.session_state.dados_sel_ser = {"ID": None, "Nome": "", "UrlLogin": "", "UrlConsulta": "", "UrlPdf": "", "Login": "", "Senha": "", "DuplaAutenticacao": "Não", "Tipo": "SROP", "Status": "Ativo", "Tempo_Expiracao_Horas": 4}

# --- AUTENTICAÇÃO KEYCLOAK (O "PORTEIRO" DO SISTEMA) ---
# Aqui começa a barreira de segurança. Tudo abaixo daqui só roda se a pessoa for autorizada.

# 1. Cria o espaço na memória (sessão) para guardar o "Crachá" do usuário
if "user_info" not in st.session_state:
    st.session_state.user_info = None

# 2. Quando o usuário volta do Keycloak (após digitar a senha), o Keycloak coloca um 'code' na barra de endereços
query_params = st.query_params
if "code" in query_params and not st.session_state.user_info:
    code = query_params["code"]
    
    # 3. Manda esse código secreto de volta pro Keycloak (nos bastidores) em troca do Token de Acesso (Crachá)
    token_response = auth_utils.exchange_code_for_token(code)
    
    if token_response and "access_token" in token_response:
        access_token = token_response["access_token"]
        id_token = token_response.get("id_token")
        
        # 4. Decodifica (abre) o crachá para ver quem é a pessoa e os cargos dela
        decoded = auth_utils.decode_token(access_token)
        user_info = auth_utils.get_user_info(decoded)
        
        if user_info:
            user_info["id_token"] = id_token # Guarda para podermos fazer o Logout depois
            st.session_state.user_info = user_info # Salva o usuário na memória!
            
            # 5. Limpa a barra de endereços (tira o ?code=...) e recarrega a página com o usuário logado
            st.query_params.clear()
            st.rerun()

# 6. Se, depois de tudo, o usuário AINDA NÃO ESTIVER LOGADO (ou seja, acabou de entrar no site)
if not st.session_state.user_info:
    # --- DESIGN PREMIUM DA TELA DE LOGIN (STREAMLIT) ---
    st.markdown("""
        <style>
            /* Esconde a barra lateral, menu superior e rodapé na tela de login para focar 100% no cartão */
            [data-testid="collapsedControl"] { display: none; }
            [data-testid="stHeader"] { display: none; }
            footer { display: none; }
            
            /* Centralização e background */
            .main {
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            }
            
            /* Estilo do Cartão Neumórfico (Efeito de relevo/vidro) */
            .login-card {
                background: rgba(255, 255, 255, 0.9);
                backdrop-filter: blur(10px);
                padding: 50px 40px;
                border-radius: 24px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1), 0 1px 3px rgba(0,0,0,0.05);
                text-align: center;
                border: 1px solid rgba(255, 255, 255, 0.5);
                margin-top: 5vh;
            }
            
            .login-icon {
                font-size: 60px;
                margin-bottom: -15px;
                animation: float 3s ease-in-out infinite;
            }
            
            .login-title {
                font-size: 38px;
                font-weight: 900;
                color: #1E293B;
                letter-spacing: -1px;
                margin-bottom: 5px;
            }
            
            .login-subtitle {
                color: #64748B;
                font-size: 16px;
                font-weight: 500;
                margin-bottom: 35px;
            }
            
            .login-divider {
                height: 1px;
                background: linear-gradient(90deg, transparent, rgba(255, 75, 75, 0.3), transparent);
                margin: 25px 0;
            }
            
            @keyframes float {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-10px); }
                100% { transform: translateY(0px); }
            }
        </style>
    """, unsafe_allow_html=True)

    # Layout de 3 colunas para forçar o cartão a ficar centralizado
    _, col_center, _ = st.columns([1, 1.5, 1])
    
    with col_center:
        st.markdown("""
            <div class="login-card">
                <div class="login-icon">
                    <svg xmlns="http://www.w3.org/2000/svg" width="68" height="68" viewBox="0 0 24 24" fill="none" stroke="url(#grad1)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <defs>
                            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" style="stop-color:#2563EB;stop-opacity:1" />
                                <stop offset="100%" style="stop-color:#6366F1;stop-opacity:1" />
                            </linearGradient>
                        </defs>
                        <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                        <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                        <circle cx="12" cy="16" r="1" fill="#2563EB"></circle>
                    </svg>
                </div>
                <div class="login-title">BuscaDados</div>
                <div class="login-subtitle">Plataforma Segura de Extração de Dados</div>
                <div class="login-divider"></div>
                <p style="color: #94A3B8; font-size: 14px; margin-bottom: 25px;">
                    Ambiente restrito. O acesso é monitorado e requer autenticação via SSO (Single Sign-On).
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # O botão fica fora do markdown para manter a interatividade do Python/Streamlit
        login_url = auth_utils.get_login_url()
        st.link_button("🔐 ACESSAR SISTEMA", login_url, type="primary", use_container_width=True)
        
        st.markdown("<br><p style='text-align: center; color: #94A3B8; font-size: 12px;'>© 2024 BuscaDados. Todos os direitos reservados.</p>", unsafe_allow_html=True)

    # MATA A EXECUÇÃO AQUI! O código do Streamlit para nesta linha.
    st.stop() 

# 7. Se o código chegou até aqui, é porque a pessoa ESTÁ LOGADA!
user = st.session_state.user_info
is_admin = user.get("is_admin", False)

# --- MENU LATERAL ESQUERDO ---
st.sidebar.title("🤖 BuscaDados")
st.sidebar.subheader("Menu Principal")

opcoes_menu = ["🗺️ Manutenção de Municípios", "🏘️ Manutenção de Bairros", "🏢 Manutenção de UPMs", "🔌 Manutenção de Serviços", "📥 Importar Dados Base", "🤖 Robô de Extração (BO)", "⚙️ Configurações"]

# --- CONTROLE DE ACESSO BASEADO EM PAPEL (RBAC) ---
# Se o usuário NÃO for Administrador (ou seja, é um Operador), ele sofre uma restrição.
if not is_admin:
    # Sobrescrevemos a lista de menus para ter APENAS a extração. Todo o resto some!
    opcoes_menu = ["🤖 Robô de Extração (BO)"]
    if st.session_state.radio_selecionado not in opcoes_menu:
        st.session_state.radio_selecionado = "🤖 Robô de Extração (BO)"

# O index do radio deve ser baseado no que está em st.session_state.radio_selecionado, 
# MAS se estivermos numa tela de serviço (override), o menu principal deve ficar "desmarcado"
if st.session_state.menu_override:
    idx_radio_atual = None
else:
    idx_radio_atual = opcoes_menu.index(st.session_state.radio_selecionado) if st.session_state.radio_selecionado in opcoes_menu else 0

radio_val = st.sidebar.radio(
    "Selecione uma opção:",
    opcoes_menu,
    index=idx_radio_atual,
    label_visibility="collapsed"
)

# Se o usuário clicou ativamente no radio (radio_val != None) e o valor for diferente do guardado,
# OU se ele clicou no menu principal para sair de uma tela de serviço (override ativo)
if radio_val is not None:
    if radio_val != st.session_state.radio_selecionado or st.session_state.menu_override is not None:
        st.session_state.radio_selecionado = radio_val
        st.session_state.menu_override = None
        st.rerun()

# Definimos a variável final 'menu' a ser usada nas telas
menu = st.session_state.menu_override if st.session_state.menu_override else radio_val

# --- EXIBIÇÃO DE SERVIÇOS CADASTRADOS NO SIDEBAR ---
st.sidebar.markdown("<hr style='margin: 15px 0px 15px 0px;'>", unsafe_allow_html=True)
st.sidebar.subheader("🔌 Serviços Ativos")
df_servicos_sidebar = db.listar_dados("servicos")
if not df_servicos_sidebar.empty:
    # Filtra apenas os serviços ativos para exibição no menu lateral
    df_servicos_sidebar = df_servicos_sidebar[df_servicos_sidebar.get("Status", "Ativo") == "Ativo"]
    if not df_servicos_sidebar.empty:
        for idx, row in df_servicos_sidebar.iterrows():
            id_servico = row["ID"]
            nome_servico = row["Nome"]
            is_ativo = (st.session_state.menu_override == f"servico_{id_servico}")
            
            btn_label = f"🎯 {nome_servico} (Ativo)" if is_ativo else f"🔹 {nome_servico}"
            
            if st.sidebar.button(btn_label, key=f"btn_sid_{id_servico}", width="stretch"):
                st.session_state.menu_override = f"servico_{id_servico}"
                st.rerun()
    else:
        st.sidebar.info("Nenhum serviço ativo cadastrado.")
else:
    st.sidebar.info("Nenhum serviço cadastrado.")

st.sidebar.markdown("<hr style='margin: 15px 0px 15px 0px;'>", unsafe_allow_html=True)
st.sidebar.write(f"👤 Logado como: **{user['name']}**")
logout_url = auth_utils.get_logout_url(user.get("id_token", ""))
st.sidebar.link_button("Sair do Sistema (Logout)", logout_url, use_container_width=True)

# Se um serviço estiver ativo via override, vamos injetar CSS para desmarcar visualmente o radio button
if st.session_state.menu_override:
    st.markdown("""
        <style>
            div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label[data-checked="true"] {
                background-color: #f8f9fa !important;
                border-color: #e9ecef !important;
                color: inherit !important;
                font-weight: normal !important;
            }
        </style>
    """, unsafe_allow_html=True)

# =====================================================================
# 1. TELA: MANUTENÇÃO DE MUNICÍPIO (COMPLETA)
# =====================================================================
if menu == "🗺️ Manutenção de Municípios":
    st.title("📍 Manutenção de Município")
    
    if st.session_state.mensagem_sucesso:
        st.success(st.session_state.mensagem_sucesso)
        st.session_state.mensagem_sucesso = None
        
    if st.session_state.sub_tela_mun == "listar":
        if st.button("➕ Cadastrar Novo Município", width="stretch"):
            st.session_state.sub_tela_mun = "formulario"
            st.session_state.modo_form_mun = "cadastro"
            st.session_state.dados_sel_mun = {"ID": None, "Municipio": "", "Estado": "MT - Mato Grosso"}
            st.rerun()
            
        st.write("")
        df_mun = db.listar_dados("municipios")
        
        texto_busca_mun = st.text_input("🔍 Buscar Município por Nome:", key="busca_mun_lista")
        if texto_busca_mun:
            import unicodedata
            def remover_acento_mun(t):
                if not t: return ""
                return "".join(c for c in unicodedata.normalize('NFKD', str(t)) if not unicodedata.combining(c)).lower()
            
            busca_norm = remover_acento_mun(texto_busca_mun)
            mun_norm = df_mun["Municipio"].apply(remover_acento_mun)
            df_mun = df_mun[mun_norm.str.contains(busca_norm, na=False)]
            
        if "pagina_mun" not in st.session_state: st.session_state.pagina_mun = 1
        
        itens_por_pagina = 10
        total_paginas_mun = max(1, (len(df_mun) - 1) // itens_por_pagina + 1)
        if st.session_state.pagina_mun > total_paginas_mun: st.session_state.pagina_mun = total_paginas_mun
        
        start_idx = (st.session_state.pagina_mun - 1) * itens_por_pagina
        end_idx = start_idx + itens_por_pagina
        df_mun_exibicao = df_mun.iloc[start_idx:end_idx]
        
        if df_mun.empty:
            st.info("Nenhum município cadastrado no banco de dados ainda.")
        else:
            st.subheader(f"Municípios Cadastrados (Página {st.session_state.pagina_mun} de {total_paginas_mun})")
            col_id, col_nome, col_est, col_acoes = st.columns([0.8, 3, 3, 3.2])
            with col_id: st.write("**ID**")
            with col_nome: st.write("**Município**")
            with col_est: st.write("**Estado**")
            with col_acoes: st.write("**Ações Disponíveis**")
            st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            for idx, row in df_mun_exibicao.iterrows():
                id_atual = row["ID"]
                mun_atual = row["Municipio"]
                est_atual = row["Estado"]
                
                c_id, c_nome, c_est, c_vis, c_edt, c_exc = st.columns([0.8, 3, 3, 1, 1, 1.2])
                c_id.write(f"`{id_atual}`")
                c_nome.write(mun_atual)
                c_est.write(est_atual)
                
                if c_vis.button("👁️ Ver", key=f"vis_mun_{id_atual}", width="stretch"):
                    st.session_state.sub_tela_mun = "formulario"; st.session_state.modo_form_mun = "visualizar"
                    st.session_state.dados_sel_mun = {"ID": id_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()
                    
                if c_edt.button("✏️ Editar", key=f"edt_mun_{id_atual}", width="stretch"):
                    st.session_state.sub_tela_mun = "formulario"; st.session_state.modo_form_mun = "editar"
                    st.session_state.dados_sel_mun = {"ID": id_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()
                    
                if c_exc.button("🗑️ Excluir", key=f"exc_mun_{id_atual}", width="stretch", type="primary"):
                    st.session_state.sub_tela_mun = "formulario"; st.session_state.modo_form_mun = "excluir"
                    st.session_state.dados_sel_mun = {"ID": id_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()
            
            st.write("")
            col_ant, col_e1, col_pag, col_e2, col_prox = st.columns([1, 1, 0.8, 1, 1])
            if col_ant.button("⬅️ Página Anterior", disabled=(st.session_state.pagina_mun <= 1), use_container_width=True, key="btn_ant_mun"):
                st.session_state.pagina_mun -= 1; st.rerun()
                
            def set_page_mun():
                st.session_state.pagina_mun = st.session_state.combo_pag_mun
                
            with col_pag:
                st.selectbox(
                    "Pular para a página", 
                    options=range(1, total_paginas_mun + 1), 
                    index=st.session_state.pagina_mun - 1,
                    key="combo_pag_mun",
                    on_change=set_page_mun,
                    label_visibility="collapsed"
                )
                
            if col_prox.button("Próxima Página ➡️", disabled=(st.session_state.pagina_mun >= total_paginas_mun), use_container_width=True, key="btn_prox_mun"):
                st.session_state.pagina_mun += 1; st.rerun()

    elif st.session_state.sub_tela_mun == "formulario":
        modo = st.session_state.modo_form_mun; dados = st.session_state.dados_sel_mun
        campos_bloqueados = True if modo in ["visualizar", "excluir"] else False
        
        if modo == "cadastro": st.subheader("➕ Cadastrar Novo Município")
        elif modo == "visualizar": st.subheader(f"👁️ Visualizando Registro ID: {dados['ID']}")
        elif modo == "editar": st.subheader(f"✏️ Editando Registro ID: {dados['ID']}")
        elif modo == "excluir":
            st.subheader(f"⚠️ Confirmar Exclusão do Registro ID: {dados['ID']}")
            st.error(f"Atenção: Você está prestes a deletar o município '{dados['Municipio']}'. Esta ação não pode ser desfeita.")

        novo_mun = st.text_input("Nome do Município", value=dados["Municipio"], disabled=campos_bloqueados, key="input_mun_dinamico").strip()
        estado_mun = st.selectbox("Estado", ["MT - Mato Grosso"], index=0, disabled=campos_bloqueados, key="select_est_dinamico")
        
        st.write("")
        if modo == "cadastro":
            c_salvar, c_cancelar = st.columns(2)
            if c_salvar.button("💾 Salvar no Banco", key="btn_salvar_mun", width="stretch"):
                if novo_mun:
                    if db.salvar_registro("municipios", {"Municipio": novo_mun, "Estado": estado_mun}):
                        st.session_state.sub_tela_mun = "listar"; st.session_state.mensagem_sucesso = f"🎉 Município '{novo_mun}' cadastrado com sucesso!"; st.rerun()
                    else: st.error(f"⚠️ Erro: O município '{novo_mun}' já existe!")
                else: st.error("Por favor, digite o nome do município.")
            if c_cancelar.button("❌ Cancelar e Voltar", key="btn_cancelar_cad_mun", width="stretch"):
                st.session_state.sub_tela_mun = "listar"; st.rerun()
                    
        elif modo == "visualizar":
            if st.button("⬅️ Voltar para a Consulta", key="btn_voltar_vis_mun", width="stretch"):
                st.session_state.sub_tela_mun = "listar"; st.rerun()
                
        elif modo == "editar":
            c_atualizar, c_cancelar = st.columns(2)
            if c_atualizar.button("💾 Salvar Alterações", key="btn_update_mun", width="stretch"):
                if novo_mun:
                    conn = sqlite3.connect("buscadados.db"); cursor = conn.cursor()
                    cursor.execute("UPDATE municipios SET Municipio = ?, Estado = ? WHERE ID = ?", (novo_mun, estado_mun, dados["ID"]))
                    conn.commit(); conn.close()
                    st.session_state.sub_tela_mun = "listar"; st.session_state.mensagem_sucesso = "✏️ Município alterado com sucesso!"; st.rerun()
                else: st.error("O nome do município não pode ficar em branco.")
            if c_cancelar.button("❌ Cancelar", key="btn_cancelar_edit_mun", width="stretch"):
                st.session_state.sub_tela_mun = "listar"; st.rerun()
                
        elif modo == "excluir":
            c_deletar, c_voltar = st.columns(2)
            if c_deletar.button("🗑️ Sim, Excluir Registro", key="btn_delete_confirm_mun", width="stretch"):
                db.excluir_registro("municipios", dados["ID"])
                st.session_state.sub_tela_mun = "listar"; st.session_state.mensagem_sucesso = f"🗑️ Município '{dados['Municipio']}' removido!"; st.rerun()
            if c_voltar.button("❌ Cancelar e Manter", key="btn_voltar_del_mun", width="stretch"):
                st.session_state.sub_tela_mun = "listar"; st.rerun()

# =====================================================================
# 2. TELA: MANUTENÇÃO DE BAIRRO (COM FILTROS AVANÇADOS)
# =====================================================================
elif menu == "🏘️ Manutenção de Bairros":
    st.title("🏡 Manutenção de Bairro")
    
    if st.session_state.mensagem_sucesso:
        st.success(st.session_state.mensagem_sucesso)
        st.session_state.mensagem_sucesso = None
        
    if st.session_state.sub_tela_bai == "listar":
        if st.button("➕ Cadastrar Novo Bairro", width="stretch"):
            st.session_state.sub_tela_bai = "formulario"
            st.session_state.modo_form_bai = "cadastro"
            st.session_state.dados_sel_bai = {"ID": None, "Bairro": "", "Municipio": ""}
            st.rerun()
            
        st.write("")
        df_bai = db.listar_dados("bairros")
        df_mun_existentes = db.listar_dados("municipios")
        
        if df_bai.empty:
            st.info("Nenhum bairro cadastrado no banco de dados ainda.")
        else:
            # --- SEÇÃO DE FILTROS COM LAYOUT APRIMORADO ---
            with st.container():
                # Proporções otimizadas para os filtros ficarem alinhados lado a lado
                col_filtro_mun, col_filtro_txt = st.columns([2, 3])
                
                with col_filtro_mun:
                    lista_mun_filtro = ["Todos os Municípios"]
                    if not df_mun_existentes.empty:
                        lista_mun_filtro.extend(df_mun_existentes["Municipio"].unique().tolist())
                    # Reduzimos o rótulo incluindo um emoji para um visual mais limpo
                    municipio_filtrado = st.selectbox("🏙️ Filtrar por Município", lista_mun_filtro, key="filtro_mun_bai")
                    
                with col_filtro_txt:
                    texto_filtrado = st.text_input("🔍 Digite o nome do Bairro para pesquisar...", key="filtro_txt_bai").strip()
            
            st.markdown("<hr style='margin: 10px 0px 20px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            # --- APLICAÇÃO DOS FILTROS NO DATAFRAME ---
            # 1. Filtro por Município (Selectbox)
            if municipio_filtrado != "Todos os Municípios":
                df_bai = df_bai[df_bai["Municipio"] == municipio_filtrado]
                
            # 2. Filtro por Texto (Ignorando Case e Acentuação)
            if texto_filtrado:
                import unicodedata
                
                def remover_acentos_e_case(texto):
                    if not texto:
                        return ""
                    # Remove acentuações e transforma em minúsculo
                    nfkd_form = unicodedata.normalize('NFKD', str(texto))
                    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()
                
                # Cria uma busca temporária normalizada no Pandas
                bairros_normalizados = df_bai["Bairro"].apply(remover_acentos_e_case)
                termo_busca_normalizado = remover_acentos_e_case(texto_filtrado)
                
                # Filtra as linhas que contêm o termo pesquisado
                df_bai = df_bai[bairros_normalizados.str.contains(termo_busca_normalizado, na=False)]
            
            if "pagina_bai" not in st.session_state: st.session_state.pagina_bai = 1
            
            itens_por_pagina_bai = 10
            total_paginas_bai = max(1, (len(df_bai) - 1) // itens_por_pagina_bai + 1)
            if st.session_state.pagina_bai > total_paginas_bai: st.session_state.pagina_bai = total_paginas_bai
            
            start_idx_bai = (st.session_state.pagina_bai - 1) * itens_por_pagina_bai
            end_idx_bai = start_idx_bai + itens_por_pagina_bai
            df_bai_exibicao = df_bai.iloc[start_idx_bai:end_idx_bai]
            
            st.write("")
            
            if df_bai.empty:
                st.warning("Nenhum bairro encontrado para os filtros selecionados.")
            else:
                st.subheader(f"Bairros Cadastrados (Página {st.session_state.pagina_bai} de {total_paginas_bai})")
                col_id, col_nome, col_mun, col_acoes = st.columns([0.8, 2.5, 2.5, 4.2])
                with col_id: st.write("**ID**")
                with col_nome: st.write("**Bairro**")
                with col_mun: st.write("**Município Vinculado**")
                with col_acoes: st.write("**Ações Disponíveis**")
                st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
                
                for idx, row in df_bai_exibicao.iterrows():
                    id_atual = row["ID"]
                    bai_atual = row["Bairro"]
                    mun_atual = row["Municipio"]
                    
                    c_id, c_nome, c_mun, c_vis, c_edt, c_alt, c_exc = st.columns([0.8, 2.5, 2.5, 0.8, 1.0, 1.4, 1.0])
                    c_id.write(f"`{id_atual}`")
                    c_nome.write(bai_atual)
                    c_mun.text(mun_atual)
                    
                    if c_vis.button("👁️ Ver", key=f"vis_bai_{id_atual}", width="stretch"):
                        st.session_state.sub_tela_bai = "formulario"; st.session_state.modo_form_bai = "visualizar"
                        st.session_state.dados_sel_bai = {"ID": id_atual, "Bairro": bai_atual, "Municipio": mun_atual}; st.rerun()
                    if c_edt.button("✏️ Editar", key=f"edt_bai_{id_atual}", width="stretch"):
                        st.session_state.sub_tela_bai = "formulario"; st.session_state.modo_form_bai = "editar"
                        st.session_state.dados_sel_bai = {"ID": id_atual, "Bairro": bai_atual, "Municipio": mun_atual}; st.rerun()
                    if c_alt.button("🏷️ Nomes", key=f"alt_bai_{id_atual}", width="stretch"):
                        st.session_state.sub_tela_bai = "alternativos"
                        st.session_state.dados_sel_bai = {"ID": id_atual, "Bairro": bai_atual, "Municipio": mun_atual}; st.rerun()
                    if c_exc.button("🗑️ Excluir", key=f"exc_bai_{id_atual}", width="stretch", type="primary"):
                        st.session_state.sub_tela_bai = "formulario"; st.session_state.modo_form_bai = "excluir"
                        st.session_state.dados_sel_bai = {"ID": id_atual, "Bairro": bai_atual, "Municipio": mun_atual}; st.rerun()
                
                st.write("")
                col_ant, col_e1, col_pag, col_e2, col_prox = st.columns([1, 1, 0.8, 1, 1])
                if col_ant.button("⬅️ Página Anterior", disabled=(st.session_state.pagina_bai <= 1), use_container_width=True, key="btn_ant_bai"):
                    st.session_state.pagina_bai -= 1; st.rerun()
                    
                def set_page_bai():
                    st.session_state.pagina_bai = st.session_state.combo_pag_bai
                    
                with col_pag:
                    st.selectbox(
                        "Pular para a página", 
                        options=range(1, total_paginas_bai + 1), 
                        index=st.session_state.pagina_bai - 1,
                        key="combo_pag_bai",
                        on_change=set_page_bai,
                        label_visibility="collapsed"
                    )
                    
                if col_prox.button("Próxima Página ➡️", disabled=(st.session_state.pagina_bai >= total_paginas_bai), use_container_width=True, key="btn_prox_bai"):
                    st.session_state.pagina_bai += 1; st.rerun()

    elif st.session_state.sub_tela_bai == "formulario":
        modo = st.session_state.modo_form_bai; dados = st.session_state.dados_sel_bai
        campos_bloqueados = True if modo in ["visualizar", "excluir"] else False
        
        if modo == "cadastro": st.subheader("➕ Cadastrar Novo Bairro")
        elif modo == "visualizar": st.subheader(f"👁️ Visualizando Bairro ID: {dados['ID']}")
        elif modo == "editar": st.subheader(f"✏️ Editando Bairro ID: {dados['ID']}")
        elif modo == "excluir":
            st.subheader(f"⚠️ Confirmar Exclusão do Bairro ID: {dados['ID']}")
            st.error(f"Atenção: Você está prestes a remover o bairro '{dados['Bairro']}' de '{dados['Municipio']}'. Esta ação não pode ser desfeita.")

        novo_bairro = st.text_input("Nome do Bairro", value=dados["Bairro"], disabled=campos_bloqueados, key="input_bai_dinamico").strip()
        
        df_mun_existentes = db.listar_dados("municipios")
        lista_formatada = []
        
        if not df_mun_existentes.empty:
            df_mun_existentes["UF"] = df_mun_existentes["Estado"].str[:2]
            df_mun_existentes["Exibicao"] = df_mun_existentes["Municipio"] + " / " + df_mun_existentes["UF"]
            lista_formatada = df_mun_existentes["Exibicao"].tolist()
        
        idx_padrao = 0
        if dados["Municipio"] and not df_mun_existentes.empty:
            filtro = df_mun_existentes[df_mun_existentes["Municipio"] == dados["Municipio"]]
            if not filtro.empty:
                str_exibicao_salva = filtro.iloc[0]["Exibicao"]
                if str_exibicao_salva in lista_formatada:
                    idx_padrao = lista_formatada.index(str_exibicao_salva)

        municipio_selecionado_combo = st.selectbox(
            "Vincular ao Município", 
            lista_formatada if lista_formatada else ["Cadastre um município primeiro antes de continuar"], 
            index=idx_padrao, 
            disabled=campos_bloqueados, 
            key="sel_mun_bai_form"
        )
        
        st.write("")
        if modo == "cadastro":
            c_s, c_c = st.columns(2)
            if c_s.button("💾 Salvar Bairro", key="btn_salvar_bairro_db", width="stretch"):
                if novo_bairro and lista_formatada:
                    municipio_puro = municipio_selecionado_combo.split(" / ")[0].strip()
                    
                    if db.salvar_registro("bairros", {"Bairro": novo_bairro, "Municipio": municipio_puro}):
                        st.session_state.sub_tela_bai = "listar"
                        st.session_state.mensagem_sucesso = f"🎉 Bairro '{novo_bairro}' cadastrado com sucesso!"
                        st.rerun()
                    else: 
                        st.error("⚠️ Erro: Este bairro já está cadastrado para o município selecionado!")
                else: 
                    st.error("Por favor, preencha o nome do bairro.")
            if c_c.button("❌ Cancelar e Voltar", key="btn_cancelar_cad_bai", width="stretch"): 
                st.session_state.sub_tela_bai = "listar"; st.rerun()
                
        elif modo == "visualizar":
            if st.button("⬅️ Voltar para a Consulta", key="btn_voltar_vis_bai", width="stretch"): 
                st.session_state.sub_tela_bai = "listar"; st.rerun()
                
        elif modo == "editar":
            c_up, c_cc = st.columns(2)
            if c_up.button("💾 Salvar Alterações", key="btn_update_bairro_db", width="stretch"):
                if novo_bairro:
                    municipio_puro = municipio_selecionado_combo.split(" / ")[0].strip()
                    
                    conn = sqlite3.connect("buscadados.db"); cursor = conn.cursor()
                    cursor.execute("UPDATE bairros SET Bairro = ?, Municipio = ? WHERE ID = ?", (novo_bairro, municipio_puro, dados["ID"]))
                    conn.commit(); conn.close()
                    st.session_state.sub_tela_bai = "listar"
                    st.session_state.mensagem_sucesso = "✏️ Bairro atualizado com sucesso!"
                    st.rerun()
                else:
                    st.error("O nome do bairro não pode ficar em branco.")
            if c_cc.button("❌ Cancelar", key="btn_cancelar_edit_bai", width="stretch"): 
                st.session_state.sub_tela_bai = "listar"; st.rerun()
                
        elif modo == "excluir":
            c_del, c_v = st.columns(2)
            if c_del.button("🗑️ Sim, Excluir Registro", key="btn_delete_confirm_bai", width="stretch"):
                db.excluir_registro("bairros", dados["ID"])
                st.session_state.sub_tela_bai = "listar"
                st.session_state.mensagem_sucesso = f"🗑️ Bairro '{dados['Bairro']}' removido com sucesso!"
                st.rerun()
            if c_v.button("❌ Cancelar e Manter", key="btn_voltar_del_bai", width="stretch"):
                st.session_state.sub_tela_bai = "listar"
                st.rerun()

    elif st.session_state.sub_tela_bai == "alternativos":
        dados = st.session_state.dados_sel_bai
        st.subheader(f"🏷️ Nomes Alternativos para Bairro: {dados['Bairro']}")
        
        st.write("#### Bairro Selecionado")
        col_b_nome, col_b_mun = st.columns(2)
        col_b_nome.text_input("Bairro", value=dados["Bairro"], disabled=True, key="bai_alt_view_nome")
        col_b_mun.text_input("Município", value=dados["Municipio"], disabled=True, key="bai_alt_view_mun")
        
        st.markdown("<hr style='margin: 10px 0px 20px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
        
        # Formulário para cadastrar nova equivalência
        st.write("#### ➕ Cadastrar Novo Nome Alternativo / Equivalente")
        col_input_alt, col_btn_add = st.columns([3, 1])
        
        with col_input_alt:
            novo_alt = st.text_input("Ex: JD SAO SIMAU, SAO SIMAO, S SIMAO", key="input_novo_alt_bairro", label_visibility="collapsed").strip()
            
        with col_btn_add:
            if st.button("➕ Adicionar", key="btn_add_alt_bairro", width="stretch"):
                if novo_alt:
                    # Tenta salvar no banco
                    if db.salvar_nome_alternativo(dados["ID"], novo_alt):
                        st.success(f"🎉 Nome alternativo '{novo_alt}' cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error(f"⚠️ Erro: O nome alternativo '{novo_alt}' já está cadastrado para este bairro.")
                else:
                    st.error("Por favor, digite um nome alternativo.")
                    
        st.write("")
        st.write("#### 📋 Nomes Alternativos Cadastrados")
        
        df_alt = db.listar_nomes_alternativos(dados["ID"])
        
        if df_alt.empty:
            st.info("Nenhum nome alternativo cadastrado para este bairro ainda.")
        else:
            col_h_nome, col_h_acao = st.columns([3, 1])
            with col_h_nome: st.write("**Nome Alternativo / Equivalência**")
            with col_h_acao: st.write("**Ação**")
            st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            for idx, row in df_alt.iterrows():
                alt_id = row["ID"]
                alt_nome = row["Nome_Alternativo"]
                
                c_nome, c_acao = st.columns([3, 1])
                c_nome.write(alt_nome)
                if c_acao.button("🗑️ Excluir", key=f"btn_del_alt_{alt_id}", width="stretch", type="primary"):
                    db.excluir_nome_alternativo(alt_id)
                    st.rerun()
                    
        st.markdown("<hr style='margin: 20px 0px 20px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
        
        if st.button("⬅️ Voltar para a Consulta de Bairros", key="btn_voltar_alt_bai_list", width="stretch"):
            st.session_state.sub_tela_bai = "listar"
            st.rerun()

# =====================================================================
# 3. TELA: MANUTENÇÃO DE UPMS (COMPLETA)
# =====================================================================
elif menu == "🏢 Manutenção de UPMs":
    st.title("🏢 Manutenção de UPMs")
    
    if st.session_state.mensagem_sucesso:
        st.success(st.session_state.mensagem_sucesso)
        st.session_state.mensagem_sucesso = None
        
    if st.session_state.sub_tela_upm == "listar":
        if st.button("➕ Cadastrar Nova UPM", width="stretch"):
            st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "cadastro"
            st.session_state.dados_sel_upm = {"ID": None, "UPM": "", "Descricao": "", "Bairro": "", "Municipio": "", "Estado": ""}; st.rerun()
            
        st.write("")
        df_upm = db.listar_dados("upms")
        
        if "pagina_upm" not in st.session_state: st.session_state.pagina_upm = 1
        
        itens_por_pagina_upm = 10
        total_paginas_upm = max(1, (len(df_upm) - 1) // itens_por_pagina_upm + 1)
        if st.session_state.pagina_upm > total_paginas_upm: st.session_state.pagina_upm = total_paginas_upm
        
        start_idx_upm = (st.session_state.pagina_upm - 1) * itens_por_pagina_upm
        end_idx_upm = start_idx_upm + itens_por_pagina_upm
        df_upm_exibicao = df_upm.iloc[start_idx_upm:end_idx_upm]
        
        if df_upm.empty:
            st.info("Nenhuma UPM cadastrada no banco de dados ainda.")
        else:
            st.subheader(f"UPMs Cadastradas (Página {st.session_state.pagina_upm} de {total_paginas_upm})")
            col_id, col_upm, col_desc, col_vis, col_edt, col_vinc, col_exc = st.columns([0.8, 2.2, 3.4, 1.1, 1.1, 1.3, 1.1])
            with col_id: st.write("**ID**")
            with col_upm: st.write("**UPM**")
            with col_desc: st.write("**Descrição**")
            with col_vis: st.write("**Ver**")
            with col_edt: st.write("**Editar**")
            with col_vinc: st.write("**Vincular**")
            with col_exc: st.write("**Excluir**")
            st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            for idx, row in df_upm_exibicao.iterrows():
                id_atual = row["ID"]
                upm_atual = row["UPM"]
                desc_atual = row.get("Descricao", "")
                
                c_id, c_upm, c_desc, c_vis, c_edt, c_vinc, c_exc = st.columns([0.8, 2.2, 3.4, 1.1, 1.1, 1.3, 1.1])
                c_id.write(f"`{id_atual}`")
                c_upm.write(upm_atual)
                c_desc.write(desc_atual)
                
                if c_vis.button("👁️ Ver", key=f"vis_upm_{id_atual}", width="stretch"):
                    st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "visualizar"
                    st.session_state.dados_sel_upm = {"ID": id_atual, "UPM": upm_atual, "Descricao": desc_atual}; st.rerun()
                if c_edt.button("✏️ Editar", key=f"edt_upm_{id_atual}", width="stretch"):
                    st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "editar"
                    st.session_state.dados_sel_upm = {"ID": id_atual, "UPM": upm_atual, "Descricao": desc_atual}; st.rerun()
                if c_vinc.button("🔗 Vincular", key=f"vinc_upm_{id_atual}", width="stretch"):
                    st.session_state.sub_tela_upm = "vincular"
                    st.session_state.dados_sel_upm = {"ID": id_atual, "UPM": upm_atual, "Descricao": desc_atual}; st.rerun()
                if c_exc.button("🗑️ Excluir", key=f"exc_upm_{id_atual}", width="stretch", type="primary"):
                    st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "excluir"
                    st.session_state.dados_sel_upm = {"ID": id_atual, "UPM": upm_atual, "Descricao": desc_atual}; st.rerun()
            
            st.write("")
            col_ant, col_e1, col_pag, col_e2, col_prox = st.columns([1, 1, 0.8, 1, 1])
            if col_ant.button("⬅️ Página Anterior", disabled=(st.session_state.pagina_upm <= 1), use_container_width=True, key="btn_ant_upm"):
                st.session_state.pagina_upm -= 1; st.rerun()
                
            def set_page_upm():
                st.session_state.pagina_upm = st.session_state.combo_pag_upm
                
            with col_pag:
                st.selectbox(
                    "Pular para a página", 
                    options=range(1, total_paginas_upm + 1), 
                    index=st.session_state.pagina_upm - 1,
                    key="combo_pag_upm",
                    on_change=set_page_upm,
                    label_visibility="collapsed"
                )
                
            if col_prox.button("Próxima Página ➡️", disabled=(st.session_state.pagina_upm >= total_paginas_upm), use_container_width=True, key="btn_prox_upm"):
                st.session_state.pagina_upm += 1; st.rerun()

    elif st.session_state.sub_tela_upm == "formulario":
        modo = st.session_state.modo_form_upm; dados = st.session_state.dados_sel_upm
        campos_bloqueados = True if modo in ["visualizar", "excluir"] else False
        
        if modo == "cadastro": st.subheader("➕ Cadastrar Nova UPM")
        elif modo == "visualizar": st.subheader(f"👁️ Visualizando UPM ID: {dados['ID']}")
        elif modo == "editar": st.subheader(f"✏️ Editando UPM ID: {dados['ID']}")
        elif modo == "excluir":
            st.subheader(f"⚠️ Confirmar Exclusão da UPM ID: {dados['ID']}")
            st.error(f"Atenção: Você está prestes a deletar a UPM '{dados['UPM']}'. Esta ação não pode ser desfeita.")

        nome_upm = st.text_input("Nome/Identificador da UPM", value=dados["UPM"], disabled=campos_bloqueados, key="upm_nome_in").strip()
        descricao_upm = st.text_area("Descrição da UPM", value=dados.get("Descricao", ""), disabled=campos_bloqueados, key="upm_desc_in", height=120).strip()
        
        st.write("")
        if modo == "cadastro":
            c_s, c_c = st.columns(2)
            if c_s.button("💾 Salvar no Banco", key="btn_salvar_upm", width="stretch"):
                if nome_upm:
                    if db.salvar_registro("upms", {"UPM": nome_upm, "Descricao": descricao_upm, "Bairro": "", "Municipio": "", "Estado": ""}):
                        st.session_state.sub_tela_upm = "listar"; st.session_state.mensagem_sucesso = f"🎉 UPM '{nome_upm}' cadastrada com sucesso!"; st.rerun()
                    else: st.error(f"⚠️ Erro: A UPM '{nome_upm}' já existe!")
                else: st.error("Por favor, preencha o nome/identificador da UPM.")
            if c_c.button("❌ Cancelar e Voltar", key="btn_cancelar_cad_upm", width="stretch"):
                st.session_state.sub_tela_upm = "listar"; st.rerun()
                
        elif modo == "visualizar":
            if st.button("⬅️ Voltar para a Consulta", key="btn_voltar_vis_upm", width="stretch"):
                st.session_state.sub_tela_upm = "listar"; st.rerun()
                
        elif modo == "editar":
            c_s, c_c = st.columns(2)
            if c_s.button("💾 Salvar Alterações", key="btn_update_upm", width="stretch"):
                if nome_upm:
                    conn = sqlite3.connect("buscadados.db"); cursor = conn.cursor()
                    cursor.execute("UPDATE upms SET UPM = ?, Descricao = ? WHERE ID = ?", (nome_upm, descricao_upm, dados["ID"]))
                    conn.commit(); conn.close()
                    st.session_state.sub_tela_upm = "listar"; st.session_state.mensagem_sucesso = "✏️ UPM alterada com sucesso!"; st.rerun()
                else: st.error("O nome da UPM não pode ficar em branco.")
            if c_c.button("❌ Cancelar", key="btn_cancelar_edit_upm", width="stretch"):
                st.session_state.sub_tela_upm = "listar"; st.rerun()
                
        elif modo == "excluir":
            c_s, c_c = st.columns(2)
            if c_s.button("🗑️ Sim, Excluir Registro", key="btn_delete_confirm_upm", width="stretch"):
                # Limpa vínculos em upm_bairros primeiro
                conn = sqlite3.connect("buscadados.db"); cursor = conn.cursor()
                cursor.execute("DELETE FROM upm_bairros WHERE UPM_ID = ?", (dados["ID"],))
                conn.commit(); conn.close()
                # Exclui a UPM
                db.excluir_registro("upms", dados["ID"])
                st.session_state.sub_tela_upm = "listar"; st.session_state.mensagem_sucesso = f"🗑️ UPM '{dados['UPM']}' removida!"; st.rerun()
            if c_c.button("❌ Cancelar e Manter", key="btn_voltar_del_upm", width="stretch"):
                st.session_state.sub_tela_upm = "listar"; st.rerun()

    elif st.session_state.sub_tela_upm == "vincular":
        dados = st.session_state.dados_sel_upm
        st.subheader(f"🔗 Vincular Bairros à UPM: {dados['UPM']}")
        
        # Exibe os detalhes da UPM selecionada como somente leitura
        st.write("#### UPM Selecionada")
        col_upm_v, col_desc_v = st.columns([1, 2])
        col_upm_v.text_input("UPM", value=dados["UPM"], disabled=True, key="upm_vinc_view_nome")
        col_desc_v.text_area("Descrição", value=dados.get("Descricao", ""), disabled=True, key="upm_vinc_view_desc", height=68)
        
        df_b = db.listar_dados("bairros"); df_m = db.listar_dados("municipios")
        
        if df_b.empty:
            st.warning("Cadastre bairros antes de criar vínculos.")
            if st.button("⬅️ Voltar", width="stretch", key="upm_vinc_back_empty"):
                st.session_state.sub_tela_upm = "listar"; st.rerun()
        else:
            # Junta bairros com municípios para exibição completa
            df_bairros_completo = df_b.merge(df_m, on="Municipio", how="left", suffixes=("_bairro", "_municipio"))
            df_bairros_completo["Exibicao"] = df_bairros_completo["Bairro"] + " (" + df_bairros_completo["Municipio"] + ")"
            
            # Inicializa a lista de selecionados no session_state para persistência
            if "selected_bairro_ids" not in st.session_state:
                bairros_vinculados = db.listar_bairros_vinculados(dados["ID"])
                st.session_state.selected_bairro_ids = set(bairros_vinculados["BairroID"].tolist())
                if not bairros_vinculados.empty:
                    st.session_state.vinc_default_mun = bairros_vinculados.iloc[0]["Municipio"]
                else:
                    st.session_state.vinc_default_mun = "Todos os Municípios"
                
            st.markdown("<hr style='margin: 10px 0px 20px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            # Estrutura de colunas para layout profissional de Filtros e Resumo
            col_filtros, col_resumo = st.columns([3, 1])
            
            with col_filtros:
                st.write("#### 🔍 Filtros de Busca")
                col_filtro_mun, col_filtro_txt = st.columns([1, 1])
                
                with col_filtro_mun:
                    lista_municipios = ["Todos os Municípios"]
                    if not df_m.empty:
                        lista_municipios.extend(df_m["Municipio"].unique().tolist())
                    
                    idx_padrao_mun = 0
                    if "vinc_default_mun" in st.session_state and st.session_state.vinc_default_mun in lista_municipios:
                        idx_padrao_mun = lista_municipios.index(st.session_state.vinc_default_mun)
                        
                    mun_selecionado = st.selectbox(
                        "🏙️ Filtrar por Município", 
                        lista_municipios, 
                        index=idx_padrao_mun, 
                        key="vinc_mun_filtro"
                    )
                    
                with col_filtro_txt:
                    busca_txt = st.text_input("🔍 Buscar por nome do Bairro", key="vinc_busca_txt").strip()
            
            with col_resumo:
                st.write("#### 📍 Resumo")
                st.info(f"Selecionados: **{len(st.session_state.selected_bairro_ids)}** bairros")
                if st.button("🗑️ Limpar Seleções", width="stretch", key="clear_all_vinc"):
                    st.session_state.selected_bairro_ids.clear()
                    st.rerun()

            # Reseta a paginação se os filtros mudarem
            if "ultimo_mun_filtro" not in st.session_state:
                st.session_state.ultimo_mun_filtro = mun_selecionado
            if "ultima_busca_txt" not in st.session_state:
                st.session_state.ultima_busca_txt = busca_txt
                
            if st.session_state.ultimo_mun_filtro != mun_selecionado or st.session_state.ultima_busca_txt != busca_txt:
                st.session_state.pagina_vinc = 1
                st.session_state.ultimo_mun_filtro = mun_selecionado
                st.session_state.ultima_busca_txt = busca_txt

            # Ordena bairros colocando os atualmente selecionados no topo em tempo real
            df_bairros_completo["Vinculado"] = df_bairros_completo["ID_bairro"].apply(
                lambda x: x in st.session_state.selected_bairro_ids
            )
            df_ordenado = df_bairros_completo.sort_values(
                by=["Vinculado", "Municipio", "Bairro"],
                ascending=[False, True, True]
            )

            # Aplica os filtros ao DataFrame ordenado
            df_filtrado = df_ordenado.copy()
            if mun_selecionado != "Todos os Municípios":
                df_filtrado = df_filtrado[df_filtrado["Municipio"] == mun_selecionado]
            
            if busca_txt:
                import unicodedata
                def normalizar(t):
                    if not t: return ""
                    nfkd = unicodedata.normalize('NFKD', str(t))
                    return "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
                
                bairros_norm = df_filtrado["Bairro"].apply(normalizar)
                busca_norm = normalizar(busca_txt)
                df_filtrado = df_filtrado[bairros_norm.str.contains(busca_norm, na=False)]
                
            st.write("")
            st.write("#### 🏡 Lista de Bairros para Vínculo")
            
            if df_filtrado.empty:
                st.warning("Nenhum bairro encontrado com os filtros aplicados.")
            else:
                # Paginação
                itens_por_pagina = 15
                total_itens = len(df_filtrado)
                total_paginas = max((total_itens - 1) // itens_por_pagina + 1, 1)
                
                if "pagina_vinc" not in st.session_state:
                    st.session_state.pagina_vinc = 1
                if st.session_state.pagina_vinc > total_paginas:
                    st.session_state.pagina_vinc = total_paginas
                
                inicio = (st.session_state.pagina_vinc - 1) * itens_por_pagina
                fim = inicio + itens_por_pagina
                df_pagina = df_filtrado.iloc[inicio:fim]

                # Cabeçalhos da tabela interativa
                col_h_status, col_h_bairro, col_h_mun, col_h_acao = st.columns([1.5, 3.5, 3.5, 2.5])
                with col_h_status: st.write("**Status**")
                with col_h_bairro: st.write("**Bairro**")
                with col_h_mun: st.write("**Município**")
                with col_h_acao: st.write("**Ação**")
                st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)

                # Renderiza cada linha da tabela interativa
                for idx, row in df_pagina.iterrows():
                    b_id = int(row["ID_bairro"])
                    b_nome = row["Bairro"]
                    b_mun = row["Municipio"]
                    is_sel = b_id in st.session_state.selected_bairro_ids
                    
                    c_status, c_bairro, c_mun, c_acao = st.columns([1.5, 3.5, 3.5, 2.5])
                    
                    c_bairro.write(b_nome)
                    c_mun.write(b_mun)
                    
                    if is_sel:
                        c_status.write("🔗 **Vinculado**")
                        if c_acao.button("❌ Desvincular", key=f"btn_desv_{b_id}", width="stretch"):
                            st.session_state.selected_bairro_ids.discard(b_id)
                            st.rerun()
                    else:
                        c_status.write("⚪ Não Vinculado")
                        if c_acao.button("➕ Vincular", key=f"btn_vinc_{b_id}", width="stretch"):
                            st.session_state.selected_bairro_ids.add(b_id)
                            st.rerun()
                
                # Controles de paginação
                st.write("")
                col_pag_prev, col_pag_info, col_pag_next = st.columns([1, 2, 1])
                if col_pag_prev.button("⬅️ Anterior", disabled=(st.session_state.pagina_vinc == 1), width="stretch", key="pag_vinc_prev"):
                    st.session_state.pagina_vinc -= 1
                    st.rerun()
                
                col_pag_info.markdown(f"<p style='text-align: center; margin-top: 6px;'>Página <b>{st.session_state.pagina_vinc}</b> de <b>{total_paginas}</b> (Total: {total_itens} bairros)</p>", unsafe_allow_html=True)
                
                if col_pag_next.button("Próxima ➡️", disabled=(st.session_state.pagina_vinc == total_paginas), width="stretch", key="pag_vinc_next"):
                    st.session_state.pagina_vinc += 1
                    st.rerun()
            
            st.markdown("<hr style='margin: 20px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            c_salvar, c_cancelar = st.columns(2)
            if c_salvar.button("💾 Salvar Vínculos", width="stretch", key="upm_vinc_save"):
                db.atualizar_vinculo_bairros(dados["ID"], list(st.session_state.selected_bairro_ids))
                # Limpa estados temporários
                for k in ["selected_bairro_ids", "pagina_vinc", "ultimo_mun_filtro", "ultima_busca_txt", "vinc_mun_filtro", "vinc_default_mun"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state.sub_tela_upm = "listar"
                st.session_state.mensagem_sucesso = f"🔗 Bairros vinculados à UPM '{dados['UPM']}' com sucesso!"
                st.rerun()
                
            if c_cancelar.button("❌ Cancelar e Voltar", width="stretch", key="upm_vinc_cancel"):
                # Limpa estados temporários
                for k in ["selected_bairro_ids", "pagina_vinc", "ultimo_mun_filtro", "ultima_busca_txt", "vinc_mun_filtro", "vinc_default_mun"]:
                    if k in st.session_state:
                        del st.session_state[k]
                st.session_state.sub_tela_upm = "listar"; st.rerun()

# =====================================================================
# 3.5. TELA: MANUTENÇÃO DE SERVIÇOS (COMPLETA)
# =====================================================================
elif menu == "🔌 Manutenção de Serviços":
    st.title("🔌 Manutenção de Serviços")
    
    if st.session_state.mensagem_sucesso:
        st.success(st.session_state.mensagem_sucesso)
        st.session_state.mensagem_sucesso = None
        
    if st.session_state.sub_tela_ser == "listar":
        col_btn_cad, col_btn_mon = st.columns(2)
        if col_btn_cad.button("➕ Cadastrar Novo Serviço", width="stretch"):
            st.session_state.sub_tela_ser = "formulario"
            st.session_state.modo_form_ser = "cadastro"
            st.session_state.dados_sel_ser = {
                "ID": None, "Nome": "", "UrlLogin": "", "UrlConsulta": "", "UrlPdf": "", "Login": "", "Senha": "",
                "DuplaAutenticacao": "Não", "Tipo": "SROP", "Status": "Ativo"
            }
            st.rerun()
            
        if col_btn_mon.button("🖥️ Monitoramento de Sessões", width="stretch"):
            st.session_state.sub_tela_ser = "monitoramento"
            st.rerun()
            
        st.write("")
        df_ser = db.listar_dados("servicos")
        
        if "pagina_ser" not in st.session_state: st.session_state.pagina_ser = 1
        
        itens_por_pagina_ser = 10
        total_paginas_ser = max(1, (len(df_ser) - 1) // itens_por_pagina_ser + 1)
        if st.session_state.pagina_ser > total_paginas_ser: st.session_state.pagina_ser = total_paginas_ser
        
        start_idx_ser = (st.session_state.pagina_ser - 1) * itens_por_pagina_ser
        end_idx_ser = start_idx_ser + itens_por_pagina_ser
        df_ser_exibicao = df_ser.iloc[start_idx_ser:end_idx_ser]
        
        if df_ser.empty:
            st.info("Nenhum serviço cadastrado no banco de dados ainda.")
        else:
            st.subheader(f"Serviços Cadastrados (Página {st.session_state.pagina_ser} de {total_paginas_ser})")
            col_id, col_nome, col_status, col_acoes = st.columns([0.8, 3, 2, 4.2])
            with col_id: st.write("**ID**")
            with col_nome: st.write("**Nome do Serviço**")
            with col_status: st.write("**Situação**")
            with col_acoes: st.write("**Ações Disponíveis**")
            st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            for idx, row in df_ser_exibicao.iterrows():
                id_atual = row["ID"]
                nome_atual = row["Nome"]
                login_atual = row["Login"]
                url_login = row["UrlLogin"]
                url_consulta = row["UrlConsulta"]
                url_pdf = row["UrlPdf"]
                senha_cripto = row["Senha"]
                dupla_autenticacao = row.get("DuplaAutenticacao", "Não")
                tipo_servico = row.get("Tipo", "SROP")
                status_servico = row.get("Status", "Ativo")
                tempo_expiracao = row.get("Tempo_Expiracao_Horas", 4)
                
                c_id, c_nome, c_status, c_vis, c_edt, c_exc = st.columns([0.8, 3, 2, 1.2, 1.2, 1.8])
                c_id.write(f"`{id_atual}`")
                c_nome.write(nome_atual)
                
                # Renderiza status com um badge de cor correspondente
                if status_servico == "Ativo":
                    c_status.markdown("🟢 **Ativo**")
                else:
                    c_status.markdown("🔴 **Inativo**")
                
                if c_vis.button("👁️ Ver", key=f"vis_ser_{id_atual}", width="stretch"):
                    st.session_state.sub_tela_ser = "formulario"
                    st.session_state.modo_form_ser = "visualizar"
                    st.session_state.dados_sel_ser = {
                        "ID": id_atual, "Nome": nome_atual, "UrlLogin": url_login,
                        "UrlConsulta": url_consulta, "UrlPdf": url_pdf, "Login": login_atual,
                        "Senha": db.descriptografar_senha(senha_cripto),
                        "DuplaAutenticacao": dupla_autenticacao,
                        "Tipo": tipo_servico, "Status": status_servico,
                        "Tempo_Expiracao_Horas": tempo_expiracao
                    }
                    st.rerun()
                    
                if c_edt.button("✏️ Editar", key=f"edt_ser_{id_atual}", width="stretch"):
                    st.session_state.sub_tela_ser = "formulario"
                    st.session_state.modo_form_ser = "editar"
                    st.session_state.dados_sel_ser = {
                        "ID": id_atual, "Nome": nome_atual, "UrlLogin": url_login,
                        "UrlConsulta": url_consulta, "UrlPdf": url_pdf, "Login": login_atual,
                        "Senha": db.descriptografar_senha(senha_cripto),
                        "DuplaAutenticacao": dupla_autenticacao,
                        "Tipo": tipo_servico, "Status": status_servico,
                        "Tempo_Expiracao_Horas": tempo_expiracao
                    }
                    st.rerun()
                    
                if c_exc.button("🗑️ Excluir", key=f"exc_ser_{id_atual}", width="stretch", type="primary"):
                    st.session_state.sub_tela_ser = "formulario"
                    st.session_state.modo_form_ser = "excluir"
                    st.session_state.dados_sel_ser = {
                        "ID": id_atual, "Nome": nome_atual, "UrlLogin": url_login,
                        "UrlConsulta": url_consulta, "UrlPdf": url_pdf, "Login": login_atual,
                        "Senha": db.descriptografar_senha(senha_cripto),
                        "DuplaAutenticacao": dupla_autenticacao,
                        "Tipo": tipo_servico, "Status": status_servico,
                        "Tempo_Expiracao_Horas": tempo_expiracao
                    }
                    st.rerun()
                    
            st.write("")
            col_ant, col_e1, col_pag, col_e2, col_prox = st.columns([1, 1, 0.8, 1, 1])
            if col_ant.button("⬅️ Página Anterior", disabled=(st.session_state.pagina_ser <= 1), use_container_width=True, key="btn_ant_ser"):
                st.session_state.pagina_ser -= 1; st.rerun()
                
            def set_page_ser():
                st.session_state.pagina_ser = st.session_state.combo_pag_ser
                
            with col_pag:
                st.selectbox(
                    "Pular para a página", 
                    options=range(1, total_paginas_ser + 1), 
                    index=st.session_state.pagina_ser - 1,
                    key="combo_pag_ser",
                    on_change=set_page_ser,
                    label_visibility="collapsed"
                )
                
            if col_prox.button("Próxima Página ➡️", disabled=(st.session_state.pagina_ser >= total_paginas_ser), use_container_width=True, key="btn_prox_ser"):
                st.session_state.pagina_ser += 1; st.rerun()

    elif st.session_state.sub_tela_ser == "formulario":
        modo = st.session_state.modo_form_ser
        dados = st.session_state.dados_sel_ser
        campos_bloqueados = True if modo in ["visualizar", "excluir"] else False
        
        if modo == "cadastro": st.subheader("➕ Cadastrar Novo Serviço")
        elif modo == "visualizar": st.subheader(f"👁️ Visualizando Registro ID: {dados['ID']}")
        elif modo == "editar": st.subheader(f"✏️ Editando Registro ID: {dados['ID']}")
        elif modo == "excluir":
            st.subheader(f"⚠️ Confirmar Exclusão do Registro ID: {dados['ID']}")
            st.error(f"Atenção: Você está prestes a deletar o serviço '{dados['Nome']}'. Esta ação não pode ser desfeita.")

        novo_nome = st.text_input("Nome do Serviço", value=dados["Nome"], disabled=campos_bloqueados, key="input_ser_nome").strip()
        nova_url_login = st.text_input("Endereço da Tela de Login", value=dados["UrlLogin"], disabled=campos_bloqueados, key="input_ser_urllogin").strip()
        nova_url_consulta = st.text_input("Endereço da Tela de Consulta", value=dados["UrlConsulta"], disabled=campos_bloqueados, key="input_ser_urlconsulta").strip()
        nova_url_pdf = st.text_input("Endereço de Extração do PDF", value=dados["UrlPdf"], disabled=campos_bloqueados, key="input_ser_urlpdf").strip()
        novo_login = st.text_input("Login", value=dados["Login"], disabled=campos_bloqueados, key="input_ser_login").strip()
        nova_senha = st.text_input("Senha", value=dados["Senha"], type="password", disabled=campos_bloqueados, key="input_ser_senha").strip()
        
        lista_dupla = ["Não", "Sim"]
        idx_dupla = lista_dupla.index(dados["DuplaAutenticacao"]) if dados.get("DuplaAutenticacao") in lista_dupla else 0
        nova_dupla = st.selectbox("Dupla Autenticação", lista_dupla, index=idx_dupla, disabled=campos_bloqueados, key="input_ser_dupla")
        
        lista_tipo = ["SROP"]
        idx_tipo = lista_tipo.index(dados["Tipo"]) if dados.get("Tipo") in lista_tipo else 0
        novo_tipo = st.selectbox("Tipo", lista_tipo, index=idx_tipo, disabled=campos_bloqueados, key="input_ser_tipo")
        
        lista_status = ["Ativo", "Inativo"]
        idx_status = lista_status.index(dados["Status"]) if dados.get("Status") in lista_status else 0
        novo_status = st.selectbox("Situação", lista_status, index=idx_status, disabled=campos_bloqueados, key="input_ser_status")
        
        st.write("")
        novo_tempo_expiracao = st.number_input("Tempo Máximo de Sessão (Horas)", min_value=1, max_value=24, value=dados.get("Tempo_Expiracao_Horas", 4), disabled=campos_bloqueados, key="input_ser_tempo")
        
        st.write("")
        if modo == "cadastro":
            c_salvar, c_cancelar = st.columns(2)
            if c_salvar.button("💾 Salvar no Banco", key="btn_salvar_ser", width="stretch"):
                if novo_nome and nova_url_login and nova_url_consulta and nova_url_pdf:
                    sucesso = db.salvar_registro("servicos", {
                        "Nome": novo_nome, "UrlLogin": nova_url_login, "UrlConsulta": nova_url_consulta,
                        "UrlPdf": nova_url_pdf, "Login": novo_login, "Senha": nova_senha,
                        "DuplaAutenticacao": nova_dupla, "Tipo": novo_tipo, "Status": novo_status,
                        "Tempo_Expiracao_Horas": novo_tempo_expiracao
                    })
                    if sucesso:
                        st.session_state.sub_tela_ser = "listar"
                        st.session_state.mensagem_sucesso = f"🎉 Serviço '{novo_nome}' cadastrado com sucesso!"
                        st.rerun()
                    else: st.error(f"⚠️ Erro: O serviço '{novo_nome}' já existe!")
                else: st.error("Por favor, preencha todos os campos obrigatórios do formulário (Nome, Login URL, Consulta URL e PDF URL).")
            if c_cancelar.button("❌ Cancelar e Voltar", key="btn_cancelar_cad_ser", width="stretch"):
                st.session_state.sub_tela_ser = "listar"; st.rerun()
                    
        elif modo == "visualizar":
            if st.button("⬅️ Voltar para a Consulta", key="btn_voltar_vis_ser", width="stretch"):
                st.session_state.sub_tela_ser = "listar"; st.rerun()
                
        elif modo == "editar":
            c_atualizar, c_cancelar = st.columns(2)
            if c_atualizar.button("💾 Salvar Alterações", key="btn_update_ser", width="stretch"):
                if novo_nome and nova_url_login and nova_url_consulta and nova_url_pdf:
                    conn = sqlite3.connect("buscadados.db")
                    cursor = conn.cursor()
                    senha_criptografada = db.criptografar_senha(nova_senha)
                    cursor.execute(
                        "UPDATE servicos SET Nome = ?, UrlLogin = ?, UrlConsulta = ?, UrlPdf = ?, Login = ?, Senha = ?, DuplaAutenticacao = ?, Tipo = ?, Status = ?, Tempo_Expiracao_Horas = ? WHERE ID = ?",
                        (novo_nome, nova_url_login, nova_url_consulta, nova_url_pdf, novo_login, senha_criptografada, nova_dupla, novo_tipo, novo_status, novo_tempo_expiracao, dados["ID"])
                    )
                    conn.commit()
                    conn.close()
                    st.session_state.sub_tela_ser = "listar"
                    st.session_state.mensagem_sucesso = "✏️ Serviço alterado com sucesso!"
                    st.rerun()
                else: st.error("Por favor, preencha todos os campos obrigatórios do formulário (Nome, Login URL, Consulta URL e PDF URL).")
            if c_cancelar.button("❌ Cancelar", key="btn_cancelar_edit_ser", width="stretch"):
                st.session_state.sub_tela_ser = "listar"; st.rerun()
                
        elif modo == "excluir":
            c_deletar, c_voltar = st.columns(2)
            if c_deletar.button("🗑️ Sim, Excluir Registro", key="btn_delete_confirm_ser", width="stretch"):
                db.excluir_registro("servicos", dados["ID"])
                st.session_state.sub_tela_ser = "listar"
                st.session_state.mensagem_sucesso = f"🗑️ Serviço '{dados['Nome']}' removido!"
                st.rerun()
            if c_voltar.button("❌ Cancelar e Manter", key="btn_voltar_del_ser", width="stretch"):
                st.session_state.sub_tela_ser = "listar"; st.rerun()

    elif st.session_state.sub_tela_ser == "monitoramento":
        st.subheader("🖥️ Monitoramento Global de Sessões")
        
        col_voltar, col_limpar = st.columns(2)
        if col_voltar.button("⬅️ Voltar para Manutenção de Serviços", width="stretch"):
            st.session_state.sub_tela_ser = "listar"
            st.rerun()
        if col_limpar.button("🧹 Limpar Histórico de Inativos", width="stretch"):
            db.limpar_historico_inativo()
            st.session_state.mensagem_sucesso = "Todo o histórico de sessões antigas foi apagado com sucesso."
            st.rerun()
            
        st.write("")
        df_sessoes = db.listar_dados("servicos_sessoes")
        if df_sessoes.empty:
            st.info("🟢 Nenhuma sessão pendente. O sistema está limpo.")
        else:
            df_servicos = db.listar_dados("servicos")
            if not df_servicos.empty:
                df_sessoes = df_sessoes.merge(df_servicos[['ID', 'Nome']], left_on='Servico_ID', right_on='ID', how='left', suffixes=('', '_servico'))
                df_sessoes = df_sessoes.rename(columns={'Nome': 'Serviço'})
                
            # Ordena da sessão mais recente para a mais antiga (Ordem Decrescente)
            df_sessoes = df_sessoes.sort_values(by='Data_Login', ascending=False)
                
            from datetime import datetime
            
            for idx, row in df_sessoes.iterrows():
                id_sessao_db = row['ID']
                id_ser = row['Servico_ID']
                nome_ser = row.get('Serviço', f'Desconhecido (ID {id_ser})')
                data_login_str = row['Data_Login']
                status_sessao = row.get('Status', 'Ativa')
                
                try:
                    dt_login = datetime.strptime(data_login_str, '%Y-%m-%d %H:%M:%S')
                    logado_em_fmt = dt_login.strftime('%d/%m/%Y %H:%M:%S')
                    
                    if status_sessao == 'Ativa':
                        diff = datetime.now() - dt_login
                        total_seconds = int(diff.total_seconds())
                        hours = total_seconds // 3600
                        minutes = (total_seconds % 3600) // 60
                        seconds = total_seconds % 60
                        tempo_ativo_fmt = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    else:
                        tempo_ativo_fmt = "--:--:--"
                except:
                    logado_em_fmt = data_login_str
                    tempo_ativo_fmt = "?"

                if status_sessao == "Ativa":
                    icon = "🟢"
                    status_lbl = f"<span style='color: #166534;'>{status_sessao.upper()}</span>"
                else:
                    icon = "⚪"
                    status_lbl = f"<span style='color: #6c757d;'>{status_sessao.upper()}</span>"
                
                with st.container():
                    col_status, col_servico, col_logado, col_tempo, col_btn = st.columns([1.0, 2.0, 2.5, 1.5, 3.0])
                    
                    with col_status:
                        st.markdown(f"<div style='padding-top: 5px; font-size: 12px; color: #6c757d; text-transform: uppercase;'>Status</div><div style='padding-top: 2px; font-size: 15px;'><b>{icon} {status_lbl}</b></div>", unsafe_allow_html=True)
                    with col_servico:
                        st.markdown(f"<div style='padding-top: 5px; font-size: 12px; color: #6c757d; text-transform: uppercase;'>Serviço</div><div style='padding-top: 2px; font-size: 15px;'><b style='color: #343a40;'>{nome_ser}</b></div>", unsafe_allow_html=True)
                    with col_logado:
                        st.markdown(f"<div style='padding-top: 5px; font-size: 12px; color: #6c757d; text-transform: uppercase;'>Logado em</div><div style='padding-top: 2px; font-size: 15px;'><b style='color: #343a40;'>{logado_em_fmt}</b></div>", unsafe_allow_html=True)
                    with col_tempo:
                        st.markdown(f"<div style='padding-top: 5px; font-size: 12px; color: #6c757d; text-transform: uppercase;'>Tempo Ativo</div><div style='padding-top: 2px; font-size: 15px;'><b style='color: #343a40;'>{tempo_ativo_fmt}</b></div>", unsafe_allow_html=True)
                    
                    with col_btn:
                        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
                        if status_sessao == "Ativa":
                            cb_test, cb_kill = st.columns(2)
                            if cb_test.button("🔄 Testar", key=f"btn_test_sess_{id_sessao_db}", use_container_width=True):
                                with st.spinner("Ping..."):
                                    import automacao as aut
                                    import json
                                    
                                    # Pega URL de Consulta do serviço
                                    df_ser_url = db.listar_dados("servicos")
                                    url_consulta = df_ser_url[df_ser_url["ID"] == id_ser]["UrlConsulta"].iloc[0] if not df_ser_url.empty else ""
                                    
                                    # Pega os cookies
                                    sess_data_str = db.descriptografar_senha(row['Session_Data'])
                                    if sess_data_str != "Erro ao descriptografar":
                                        sess_obj = json.loads(sess_data_str)
                                        is_alive = aut.testar_conexao_srop(sess_obj, url_consulta)
                                        if is_alive:
                                            st.toast("✅ A sessão respondeu e está perfeitamente viva no SROP!", icon="✅")
                                        else:
                                            db.atualizar_status_sessao(id_sessao_db, "Expirada (Remota)")
                                            st.error("❌ Sessão morreu lá no servidor. Atualizando a grade...")
                                            st.rerun()
                                    else:
                                        st.error("Erro de descriptografia")
                                        
                            if cb_kill.button("🔴 Encerrar", key=f"btn_kill_sess_{id_sessao_db}", use_container_width=True):
                                db.limpar_sessao(id_ser)
                                st.session_state.mensagem_sucesso = f"A sessão '{nome_ser}' foi encerrada com sucesso."
                                st.rerun()
                        else:
                            if st.button("🗑️ Apagar", key=f"btn_kill_sess_{id_sessao_db}", use_container_width=True):
                                db.excluir_historico_sessao(id_sessao_db)
                                st.session_state.mensagem_sucesso = f"O registro de histórico foi apagado permanentemente."
                                st.rerun()
                                
                    st.markdown("<hr style='margin: 15px 0; border: none; border-top: 1px solid #e9ecef;'>", unsafe_allow_html=True)


# =====================================================================
# 4. TELA: IMPORTAÇÃO DE ARQUIVO DE DADOS
# =====================================================================
elif menu == "📥 Importar Dados Base":
    st.title("📥 Importação de Arquivo de Dados")
    st.write("Suba uma planilha XLS ou XLSX contendo as colunas **Bairro** e **Municipio** para mapear e gerar a respectiva coluna de **UPM** automaticamente.")
    
    uploaded_file = st.file_uploader("Escolha um arquivo XLS ou XLSX", type=["xls", "xlsx"])
    
    if uploaded_file is not None:
        try:
            # 1. Inspeciona os tipos de célula da segunda linha (primeira linha de dados) usando openpyxl
            import openpyxl
            import re
            uploaded_file.seek(0)
            wb = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
            ws = wb.active
            
            linhas = list(ws.iter_rows(min_row=1, max_row=2))
            wb.close()
            
            dtype_dict = {}
            colunas_data = []  # Colunas que o Excel armazena como data
            
            # Padrões de number_format que indicam que a célula é uma data
            padrao_data = re.compile(r'[dDmMyY].*[dDmMyY]')
            
            if len(linhas) >= 2:
                header_row = linhas[0]  # Linha 1: cabeçalhos
                data_row = linhas[1]    # Linha 2: primeira linha de dados
                
                for header_cell, data_cell in zip(header_row, data_row):
                    col_name = header_cell.value
                    if col_name is None:
                        continue
                    # Se a célula de dados é do tipo texto ('s') no Excel, forçar leitura como str
                    if data_cell.data_type == 's':
                        dtype_dict[col_name] = str
                    # Se a célula de dados é do tipo data ('d'), ou is_date, ou tem number_format de data
                    elif data_cell.data_type == 'd' or data_cell.is_date:
                        colunas_data.append(col_name)
                    elif data_cell.data_type == 'n' and data_cell.number_format and padrao_data.search(str(data_cell.number_format)):
                        colunas_data.append(col_name)
            
            # 2. Carrega os dados reais aplicando os dtypes detectados da planilha
            uploaded_file.seek(0)
            df_upload = pd.read_excel(uploaded_file, dtype=dtype_dict)
            
            # 3. Converte colunas de data que ficaram como número serial do Excel para datetime real
            #    Inclui as detectadas pelo openpyxl + fallback para qualquer coluna numérica inteira
            #    no range de datas seriais do Excel (cobre cenários que o openpyxl não detectou)
            for col in df_upload.columns:
                eh_coluna_data = col in colunas_data
                
                # Fallback: se a coluna não foi detectada pelo openpyxl mas contém apenas inteiros
                # no range de datas seriais do Excel (20000-80000 = anos 1954-2118), tratar como data
                if not eh_coluna_data and df_upload[col].dtype in ['int64', 'float64']:
                    valores_validos = df_upload[col].dropna()
                    if not valores_validos.empty:
                        todos_inteiros = all(float(v).is_integer() for v in valores_validos)
                        if todos_inteiros:
                            min_val = valores_validos.min()
                            max_val = valores_validos.max()
                            if 20000 < min_val and max_val < 80000:
                                eh_coluna_data = True
                                colunas_data.append(col)
                
                if eh_coluna_data:
                    def converter_data_serial(val):
                        if pd.isna(val):
                            return val
                        # Se já for datetime, manter como está
                        if isinstance(val, (pd.Timestamp, datetime)):
                            return val
                        # Se for número serial do Excel (int ou float), converter para datetime real
                        try:
                            n = float(val)
                            if 1 < n < 100000:
                                return pd.to_datetime(n - 2, unit='D', origin='1900-01-01')
                        except (ValueError, TypeError):
                            pass
                        # Se for string no formato DD/MM/AAAA, converter para datetime
                        try:
                            return pd.to_datetime(val, dayfirst=True)
                        except Exception:
                            pass
                        return val
                    df_upload[col] = df_upload[col].apply(converter_data_serial)
            
            # Guarda a lista de colunas de data para formatar na exportação
            st.session_state['colunas_data_detectadas'] = colunas_data
            
            # Verifica se a primeira coluna é RISP — se for, remove (será substituída por UPM)
            primeira_col = df_upload.columns[0]
            if str(primeira_col).strip().upper() == "RISP":
                df_upload = df_upload.drop(columns=[primeira_col])
            
            # Encontra colunas Bairro e Municipio de forma flexível (ignorando acentos e case)
            col_bairro = None
            col_municipio = None
            
            for col in df_upload.columns:
                col_norm = db.normalizar_texto(col)
                if col_norm == "bairro":
                    col_bairro = col
                elif col_norm == "municipio":
                    col_municipio = col
            
            if not col_bairro or not col_municipio:
                st.error("⚠️ Erro: A planilha enviada deve conter colunas chamadas **Bairro** e **Municipio** (ou Município).")
                st.info("Colunas encontradas no arquivo: " + ", ".join(df_upload.columns.tolist()))
            else:
                # Remove linhas onde bairro ou municipio estão vazios
                df_upload = df_upload.dropna(subset=[col_bairro, col_municipio])
                
                if df_upload.empty:
                    st.warning("⚠️ Atenção: A planilha enviada não contém linhas de dados válidas (bairro e município vazios).")
                else:
                    # Obtém o cache de UPMs na memória
                    # Obtém os caches na memória do banco de dados
                    mapa_upms = db.obter_mapeamento_upms()
                    mapa_nomes_mun = db.obter_mapeamento_nomes_municipios()
                    mapa_nomes_bai = db.obter_mapeamento_nomes_bairros()
                    mapa_alternativos_bai = db.obter_mapeamento_alternativo_bairros()
                    mapa_mun_todos = db.obter_municipios_com_bairro_todos_unico()
                    
                    lista_upms = []
                    novos_bairros = []
                    novos_municipios = []
                    
                    for idx, row in df_upload.iterrows():
                        b_orig = row[col_bairro]
                        m_orig = row[col_municipio]
                        
                        # 1. Padroniza e corrige o Município conforme as regras do usuário (TRIM + UPPER + apelidos)
                        m_padrao = db.padronizar_municipio(m_orig)
                        novos_municipios.append(m_padrao)
                        
                        # 2. Padroniza e corrige o Bairro (TRIM + UPPER + mojibake)
                        b_padrao = db.corrigir_mojibake(b_orig).strip().upper()
                        
                        # 3. Normaliza para fazer a busca no banco de dados
                        b_norm = db.normalizar_texto(b_padrao)
                        m_norm = db.normalizar_texto(m_padrao)
                        
                        # 4. Mapeamento de equivalências para obter o Bairro Oficial (sempre em UPPER)
                        if (b_norm, m_norm) in mapa_nomes_bai:
                            b_oficial = mapa_nomes_bai[(b_norm, m_norm)].upper().strip()
                        elif (b_norm, m_norm) in mapa_alternativos_bai:
                            b_oficial = mapa_alternativos_bai[(b_norm, m_norm)].upper().strip()
                            # Atualiza a chave normalizada de busca do bairro para obter a UPM correta
                            b_norm = db.normalizar_texto(b_oficial)
                        else:
                            b_oficial = b_padrao
                            
                        novos_bairros.append(b_oficial)
                        
                        # 5. Determina a UPM correspondente usando a chave de bairro (oficial ou equivalente)
                        upm_val = mapa_upms.get((b_norm, m_norm))
                        if not upm_val:
                            # Se não achou Bairro+Municipio, mas o Município possui apenas 'TODOS' cadastrado
                            if m_norm in mapa_mun_todos:
                                upm_val = mapa_mun_todos[m_norm]
                            else:
                                upm_val = "NI"
                                
                        lista_upms.append(upm_val)
                            
                    # Atualiza o DataFrame com as strings higienizadas e corretas
                    df_upload[col_bairro] = novos_bairros
                    df_upload[col_municipio] = novos_municipios
                    
                    # Cria a nova coluna UPM na primeira posição para ser facilmente visível
                    if "UPM" in df_upload.columns:
                        df_upload["UPM"] = lista_upms
                    else:
                        df_upload.insert(0, "UPM", lista_upms)
                    
                    # Mensagem de conclusão clara
                    st.success(f"🎉 Planilha carregada e processada com sucesso! {len(df_upload)} linhas válidas mapeadas.")
                    
                    st.subheader("Prévia dos Dados Processados")
                    # Exibe no Streamlit apenas as primeiras 100 linhas como prévia para performance
                    linhas_prev = min(100, len(df_upload))
                    st.write(f"Mostrando as primeiras {linhas_prev} de {len(df_upload)} linhas processadas:")
                    
                    df_preview = df_upload.head(linhas_prev).copy()
                    df_preview.index = range(1, len(df_preview) + 1)
                    
                    # Formata colunas de data como DD/MM/AAAA para exibição na grid
                    for col_dt in colunas_data:
                        if col_dt in df_preview.columns:
                            df_preview[col_dt] = df_preview[col_dt].apply(
                                lambda v: v.strftime('%d/%m/%Y') if isinstance(v, (pd.Timestamp, datetime)) else v
                            )
                    
                    st.dataframe(df_preview, width="stretch")
                    
                    # Cria o arquivo Excel em memória para download
                    import io
                    buffer = io.BytesIO()
                    with pd.ExcelWriter(buffer, engine='openpyxl', datetime_format='dd/mm/yyyy') as writer:
                        df_upload.to_excel(writer, index=False, sheet_name='Dados_Processados')
                        
                        # Aplica formato dd/mm/yyyy nas colunas de data detectadas
                        colunas_data_exp = st.session_state.get('colunas_data_detectadas', [])
                        if colunas_data_exp:
                            ws = writer.sheets['Dados_Processados']
                            from openpyxl.utils import get_column_letter
                            colunas_df = list(df_upload.columns)
                            for col_data_nome in colunas_data_exp:
                                if col_data_nome in colunas_df:
                                    col_idx = colunas_df.index(col_data_nome) + 1  # +1 pois Excel é 1-indexed
                                    col_letter = get_column_letter(col_idx)
                                    for row in range(2, len(df_upload) + 2):  # +2: header na linha 1
                                        cell = ws[f'{col_letter}{row}']
                                        cell.number_format = 'dd/mm/yyyy'
                    # Determina o nome do arquivo dinâmico (ROUBO E FURTO data_min A data_max - EXPORT.xlsx)
                    nome_arquivo = f"ROUBO E FURTO {datetime.today().strftime('%d-%m-%Y')} - EXPORT.xlsx"
                    col_data_fato = None
                    for col in df_upload.columns:
                        # Remove espaços e underlines para a comparação (Ex: "Data Fato" -> "datafato")
                        col_comparar = db.normalizar_texto(col).replace(" ", "").replace("_", "")
                        if col_comparar == "datafato":
                            col_data_fato = col
                            break
                    
                    if col_data_fato:
                        # Converte para datetime garantindo o padrão brasileiro (dia primeiro)
                        datas_validas = pd.to_datetime(df_upload[col_data_fato], dayfirst=True, errors='coerce').dropna()
                        if not datas_validas.empty:
                            data_min = datas_validas.min().strftime('%d-%m-%Y')
                            data_max = datas_validas.max().strftime('%d-%m-%Y')
                            nome_arquivo = f"ROUBO E FURTO {data_min} A {data_max} - EXPORT.xlsx"
                            
                    processed_data = buffer.getvalue()
                    
                    st.write("")
                    st.download_button(
                        label="📥 Baixar Planilha com Coluna UPM (.xlsx)",
                        data=processed_data,
                        file_name=nome_arquivo,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch"
                    )
                
        except Exception as e:
            st.error(f"⚠️ Erro ao ler ou processar o arquivo: {str(e)}")
    else:
        st.info("💡 Dica: Prepare uma planilha contendo as colunas 'Bairro' e 'Municipio' para cruzar com o banco de dados do sistema.")

# =====================================================================
# 4.5. TELA: EXTRAÇÃO DE PDFs (BO)
# =====================================================================
elif menu == "🤖 Robô de Extração (BO)":
    st.title("📥 Extração de Dados de BOs (PDF)")
    st.write("Faça o upload de um ou mais arquivos PDF de Boletins de Ocorrência para extrair dados automaticamente por seções e exportar o resultado para Excel.")

    uploaded_files = st.file_uploader("Escolha os arquivos PDF dos BOs", type=["pdf"], accept_multiple_files=True, key="bo_pdf_uploader")

    if uploaded_files:
        if st.button("🚀 Processar BOs Selecionados", type="primary", width="stretch", key="btn_processar_bo_pdfs"):
            try:
                import pypdf
                import extrair_bo as ex_bo
                
                # Inicializa ou garante que o banco está pronto
                db.inicializar_banco()
                
                # Carrega os mapeamentos e listas de bairros/municípios
                db_mappings = {
                    "mapa_upms": db.obter_mapeamento_upms(),
                    "mapa_nomes_mun": db.obter_mapeamento_nomes_municipios(),
                    "mapa_nomes_bai": db.obter_mapeamento_nomes_bairros(),
                    "mapa_alternativos_bai": db.obter_mapeamento_alternativo_bairros(),
                    "mapa_mun_todos": db.obter_municipios_com_bairro_todos_unico()
                }
                
                lista_municipios, bairros_por_mun = ex_bo.carregar_dados_banco()
                
                resultados = []
                progresso = st.progress(0)
                status_text = st.empty()
                
                total_arquivos = len(uploaded_files)
                for idx, uploaded_file in enumerate(uploaded_files):
                    status_text.write(f"Processando arquivo {idx+1} de {total_arquivos}: **{uploaded_file.name}**...")
                    
                    texto = ""
                    try:
                        texto = ex_bo.extrair_texto_pdf(uploaded_file)
                    except Exception as e:
                        texto = ""
                        st.error(f"Erro ao ler {uploaded_file.name}: {str(e)}")
                        
                    if not texto:
                        res = {
                            "ARQUIVO": uploaded_file.name,
                            "BO_NUMERO": "Erro na leitura",
                            "NARRATIVA": "Erro ao extrair texto do arquivo PDF.",
                            "PROVIDENCIAS": "NI"
                        }
                    else:
                        # Processa usando a lógica unificada do script extrair_bo
                        res = ex_bo.processar_texto_bo(
                            texto, 
                            uploaded_file.name, 
                            db_mappings, 
                            lista_municipios, 
                            bairros_por_mun
                        )
                    resultados.append(res)
                    progresso.progress((idx + 1) / total_arquivos)
                
                status_text.empty()
                st.success(f"🎉 Extração concluída! {len(resultados)} arquivos processados com sucesso.")
                
                df_res = pd.DataFrame(resultados)
                # Ordena as colunas usando a regra unificada centralizada no script
                df_res = ex_bo.ordenar_dataframe(df_res)
                
                # Ajusta o índice para iniciar em 1 para exibição amigável
                df_res.index = df_res.index + 1
                
                st.subheader("Prévia dos BOs Extraídos")
                st.dataframe(df_res, width="stretch")
                
                # Gera o buffer do Excel para download
                import io
                buffer_pdf_xlsx = io.BytesIO()
                with pd.ExcelWriter(buffer_pdf_xlsx, engine='openpyxl') as writer:
                    df_res.to_excel(writer, index=False, sheet_name='BOs_Extraidos')
                    
                nome_xlsx = f"BOs_Processados_{datetime.today().strftime('%d-%m-%Y')}.xlsx"
                
                st.download_button(
                    label="📥 Baixar Planilha de BOs (.xlsx)",
                    data=buffer_pdf_xlsx.getvalue(),
                    file_name=nome_xlsx,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    width="stretch",
                    key="btn_download_bo_xlsx"
                )
            except Exception as e:
                st.error(f"Erro ao processar os arquivos PDF: {str(e)}")

# =====================================================================
# 5. TELA: CARGA E CONFIGURAÇÕES
# =====================================================================
elif menu == "⚙️ Configurações":
    st.title("⚙️ Carga e Configurações")
    
    st.write("Gerencie a base de dados do sistema, baixe o arquivo de modelo para preenchimento, realize cargas em lote ou limpe o banco de dados completamente.")
    
    tab_carga, tab_export, tab_limpeza = st.tabs(["📥 Carga Geral de Dados", "📤 Exportar Banco", "⚠️ Redefinir Banco"])
    
    with tab_carga:
        st.subheader("1. Baixar Arquivo de Modelo")
        st.write("Baixe a planilha modelo contendo a estrutura correta para importar seus dados. Preencha as abas conforme necessário.")
        
        # Cria o modelo Excel em memória para download
        import io
        buffer_model = io.BytesIO()
        with pd.ExcelWriter(buffer_model, engine='openpyxl') as writer:
            pd.DataFrame(columns=["Municipio", "Estado"]).to_excel(writer, index=False, sheet_name="Municipios")
            pd.DataFrame(columns=["Bairro", "Municipio"]).to_excel(writer, index=False, sheet_name="Bairros")
            pd.DataFrame(columns=["Bairro_Oficial", "Municipio", "Nome_Alternativo"]).to_excel(writer, index=False, sheet_name="Nomes Alternativos")
            pd.DataFrame(columns=["UPM", "Descricao", "Bairro", "Municipio", "Estado"]).to_excel(writer, index=False, sheet_name="UPMs")
            pd.DataFrame(columns=["Nome", "UrlLogin", "UrlConsulta", "UrlPdf", "Login", "Senha", "DuplaAutenticacao", "Tipo", "Status"]).to_excel(writer, index=False, sheet_name="Servicos")
        processed_model = buffer_model.getvalue()
        
        st.download_button(
            label="📥 Baixar Modelo de Importação (.xlsx)",
            data=processed_model,
            file_name="modelo_carga_buscadados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        st.markdown("---")
        
        st.subheader("2. Enviar Arquivo Preenchido")
        arquivo_carga = st.file_uploader("Escolha o arquivo Excel (.xlsx) preenchido", type=["xlsx"], key="file_carga_geral")
        
        if arquivo_carga is not None:
            if st.button("🚀 Processar Carga em Lote", type="primary", width="stretch"):
                try:
                    with st.spinner("Processando importação..."):
                        xls = pd.ExcelFile(arquivo_carga)
                        abas = xls.sheet_names
                        
                        # Validação inicial de abas
                        required_sheets = ["Municipios", "Bairros", "Nomes Alternativos", "UPMs", "Servicos"]
                        missing = [s for s in required_sheets if s not in abas]
                        
                        if missing:
                            st.error(f"Erro: O arquivo de carga deve conter as abas: {', '.join(required_sheets)}. Abas ausentes no arquivo: {', '.join(missing)}")
                        else:
                            # Carrega os DataFrames
                            df_mun = pd.read_excel(xls, sheet_name="Municipios")
                            df_bai = pd.read_excel(xls, sheet_name="Bairros")
                            df_alt = pd.read_excel(xls, sheet_name="Nomes Alternativos")
                            df_upm = pd.read_excel(xls, sheet_name="UPMs")
                            df_serv = pd.read_excel(xls, sheet_name="Servicos")
                            
                            # Executa as cargas na ordem correta
                            res_mun = db.importar_municipios_lote(df_mun)
                            res_bai = db.importar_bairros_lote(df_bai)
                            res_alt = db.importar_nomes_alternativos_lote(df_alt)
                            res_upm = db.importar_upms_lote(df_upm)
                            res_serv = db.importar_servicos_lote(df_serv)
                            
                            st.success("🎉 Carga de dados realizada com sucesso!")
                            
                            # Exibe o resultado de forma visualmente rica
                            st.markdown("### Resumo da Carga")
                            col1, col2, col3, col4, col5 = st.columns(5)
                            with col1:
                                st.metric("Municípios", f"+{res_mun['inseridos']}", f"Ignorados: {res_mun['pulados']} | Erros: {res_mun['erros']}")
                            with col2:
                                st.metric("Bairros", f"+{res_bai['inseridos']}", f"Ignorados: {res_bai['pulados']} | Erros: {res_bai['erros']}")
                            with col3:
                                st.metric("Nomes Alternativos", f"+{res_alt['inseridos']}", f"Ignorados: {res_alt['pulados']} | Erros: {res_alt['erros']}")
                            with col4:
                                st.metric("UPMs Mapeadas", f"+{res_upm['inseridos']}", f"Ignorados: {res_upm['pulados']} | Erros: {res_upm['erros']}")
                            with col5:
                                st.metric("Serviços", f"+{res_serv['inseridos']}", f"Ignorados: {res_serv['pulados']} | Erros: {res_serv['erros']}")
                except Exception as e:
                    st.error(f"⚠️ Erro ao processar arquivo: {str(e)}")
                    
    with tab_export:
        st.subheader("📤 Exportar Todos os Dados (Backup em Excel)")
        st.write("Baixe um arquivo Excel contendo todos os dados atualmente cadastrados no banco (Municípios, Bairros, Nomes Alternativos, UPMs e Serviços). Este arquivo possui exatamente a mesma estrutura aceita na aba de Importação e pode ser usado para clonar ou restaurar o sistema.")
        
        # Como a geração pode demorar, fazemos com um botão antes do download real
        if st.button("🔄 Compilar Dados para Exportação", type="secondary", use_container_width=True):
            with st.spinner("Extraindo e formatando dados do banco..."):
                try:
                    conn_exp = sqlite3.connect("buscadados.db")
                    
                    df_mun_exp = pd.read_sql("SELECT Municipio, Estado FROM municipios", conn_exp)
                    df_bai_exp = pd.read_sql("SELECT Bairro, Municipio FROM bairros", conn_exp)
                    df_alt_exp = pd.read_sql("SELECT b.Bairro as Bairro_Oficial, b.Municipio, a.Nome_Alternativo FROM bairros_alternativos a JOIN bairros b ON a.Bairro_ID = b.ID", conn_exp)
                    df_upm_exp = pd.read_sql("SELECT UPM, Descricao, Bairro, Municipio, Estado FROM upms", conn_exp)
                    df_serv_exp = pd.read_sql("SELECT Nome, UrlLogin, UrlConsulta, UrlPdf, Login, Senha, DuplaAutenticacao, Tipo, Status FROM servicos", conn_exp)
                    
                    conn_exp.close()
                    
                    import io
                    buffer_export = io.BytesIO()
                    with pd.ExcelWriter(buffer_export, engine='openpyxl') as writer:
                        df_mun_exp.to_excel(writer, index=False, sheet_name="Municipios")
                        df_bai_exp.to_excel(writer, index=False, sheet_name="Bairros")
                        df_alt_exp.to_excel(writer, index=False, sheet_name="Nomes Alternativos")
                        df_upm_exp.to_excel(writer, index=False, sheet_name="UPMs")
                        df_serv_exp.to_excel(writer, index=False, sheet_name="Servicos")
                    
                    st.session_state.export_ready_data = buffer_export.getvalue()
                    st.success("✅ Banco compilado com sucesso! Clique no botão abaixo para baixar.")
                except Exception as e:
                    st.error(f"Erro ao compilar banco: {str(e)}")
                    
        if "export_ready_data" in st.session_state and st.session_state.export_ready_data:
            st.download_button(
                label="📦 Baixar Backup em Excel (.xlsx)",
                data=st.session_state.export_ready_data,
                file_name="backup_buscadados_completo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

    with tab_limpeza:
        st.subheader("🚨 Excluir Todos os Dados do Sistema")
        st.error("ATENÇÃO: Esta operação é irreversível e irá deletar TODOS os municípios, bairros, nomes alternativos, UPMs e vínculos cadastrados no banco de dados!")
        
        confirmacao = st.checkbox("Estou ciente e desejo apagar PERMANENTEMENTE todos os dados cadastrados.", key="confirmacao_reset_db")
        
        if st.button("🔴 Apagar Todos os Dados", disabled=not confirmacao, type="primary", width="stretch"):
            try:
                db.limpar_banco_dados()
                st.success("🔥 Todos os dados foram excluídos com sucesso. O banco de dados foi reiniciado.")
                st.balloons()
            except Exception as e:
                st.error(f"Erro ao limpar banco de dados: {str(e)}")

# =====================================================================
# 6. TELA DE EXECUÇÃO DINÂMICA DE SERVIÇOS
# =====================================================================
elif menu.startswith("servico_"):
    # Extrai o ID do serviço
    id_servico = int(menu.replace("servico_", ""))
    
    # Busca detalhes do serviço no banco
    conn = sqlite3.connect("buscadados.db")
    cursor = conn.cursor()
    cursor.execute("SELECT Nome, UrlLogin, UrlConsulta, UrlPdf, Login, Senha, DuplaAutenticacao, Tipo, Status FROM servicos WHERE ID = ?", (id_servico,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        st.error("⚠️ Serviço não encontrado.")
    else:
        nome, url_login, url_consulta, url_pdf, login_db, senha_db_cripto, dupla_autenticacao, tipo, status_db = row
        
        if status_db == "Inativo":
            st.error("⚠️ Este serviço está inativo no momento. Ative-o na tela de Manutenção de Serviços para poder executá-lo.")
            if st.button("⬅️ Voltar para Manutenção de Serviços", key="btn_voltar_inativo", width="stretch"):
                st.session_state.menu_override = None
                st.session_state.radio_selecionado = "🔌 Manutenção de Serviços"
                st.rerun()
            st.stop()
        
        st.title(f"🔌 Execução de Serviço: {nome}")
        st.write(f"Tipo de Serviço: **{tipo}**")
        
        # Só desenvolvemos o tipo SROP por enquanto
        if tipo != "SROP":
            st.warning(f"A integração para o tipo de serviço '{tipo}' não está implementada ainda. Apenas o tipo 'SROP' é suportado atualmente.")
        else:
            # Descriptografa a senha para usar ou exibir
            senha_db = db.descriptografar_senha(senha_db_cripto)
            
            cookie_key = f"srop_cookies_{id_servico}"
            result_key = f"resultado_exec_{id_servico}"
            
            # Tenta recuperar sessão ativa do banco caso não esteja na memória do Streamlit
            if cookie_key not in st.session_state:
                sessao_banco = db.obter_sessao_ativa(id_servico)
                if sessao_banco:
                    st.session_state[cookie_key] = sessao_banco["cookies"]
                    st.session_state[f"srop_login_time_{id_servico}"] = sessao_banco["data_login"]
            
            # Se não estiver conectado (sem cookies salvos)
            if cookie_key not in st.session_state:
                st.markdown("### 🔑 Credenciais e Login")
                
                # Se Login e Senha estiverem preenchidos no banco de dados, não exibe na tela
                has_credentials = bool(login_db.strip() and senha_db.strip())
                
                if has_credentials:
                    st.info("💡 As credenciais de acesso (Usuário e Senha) já estão pré-configuradas no banco de dados para este serviço e serão utilizadas automaticamente.")
                    usuario_exec = login_db.strip()
                    senha_exec = senha_db.strip()
                else:
                    st.warning("⚠️ Este serviço não possui Usuário e Senha pré-configurados no banco. Por favor, insira-os abaixo para executar o login.")
                    col_user, col_pass = st.columns(2)
                    with col_user:
                        usuario_exec = st.text_input("Usuário / Login", value="", key=f"exec_user_{id_servico}").strip()
                    with col_pass:
                        senha_exec = st.text_input("Senha", value="", type="password", key=f"exec_pass_{id_servico}").strip()
                
                codigo_mfa = ""
                if dupla_autenticacao == "Sim":
                    codigo_mfa = st.text_input("Código do Autenticador (MFA)", value="", placeholder="Ex: 123456", key=f"exec_mfa_{id_servico}").strip()
                
                st.write("")
                
                if st.button("🔑 Realizar Login no Serviço", type="primary", width="stretch", key=f"btn_login_{id_servico}"):
                    if not usuario_exec or not senha_exec:
                        st.error("⚠️ Erro: Usuário e Senha são necessários para realizar o acesso ao serviço.")
                    elif dupla_autenticacao == "Sim" and not codigo_mfa:
                        st.error("⚠️ Erro: A dupla autenticação está ativada. Por favor, preencha o Código do Autenticador (MFA).")
                    else:
                        with st.status("Autenticando no serviço...", expanded=True) as status_ui:
                            def atualizar_status_login(mensagem: str):
                                status_ui.update(label=mensagem, state="running", expanded=True)
                                st.write(mensagem)
                            
                            try:
                                import automacao as aut
                                session_state_data = aut.realizar_login_srop(
                                    url_login=url_login,
                                    usuario=usuario_exec,
                                    senha=senha_exec,
                                    codigo_mfa=codigo_mfa,
                                    dupla_autenticacao=(dupla_autenticacao == "Sim"),
                                    status_callback=atualizar_status_login
                                )
                                
                                if session_state_data:
                                    st.session_state[cookie_key] = session_state_data
                                    # Salva a sessão no banco
                                    db.salvar_sessao(id_servico, session_state_data)
                                    # Grava a data no streamlit para exibir na tela imediatamente
                                    from datetime import datetime
                                    st.session_state[f"srop_login_time_{id_servico}"] = datetime.now()
                                    
                                    status_ui.update(label="Login realizado com sucesso!", state="complete", expanded=True)
                                    st.success("🟢 Sessão iniciada e persistida com sucesso!")
                                    st.rerun()
                                else:
                                    status_ui.update(label="Falha ao obter estado de sessão.", state="error", expanded=True)
                                    st.error("❌ Não foi possível obter o estado da sessão de login.")
                            except Exception as error_login:
                                status_ui.update(label="Ocorreu um erro ao realizar o login.", state="error", expanded=True)
                                st.error(f"❌ {str(error_login)}")
            else:
                # Se estiver conectado (cookies salvos)
                sessao_info = "🟢 Conectado ao Serviço SROP"
                if f"srop_login_time_{id_servico}" in st.session_state:
                    from datetime import datetime
                    dt_login = st.session_state[f"srop_login_time_{id_servico}"]
                    if isinstance(dt_login, str):
                        try:
                            dt_login = datetime.strptime(dt_login, '%Y-%m-%d %H:%M:%S')
                        except:
                            dt_login = datetime.now()
                    diff = datetime.now() - dt_login
                    total_seconds = int(diff.total_seconds())
                    hours = total_seconds // 3600
                    minutes = (total_seconds % 3600) // 60
                    seconds = total_seconds % 60
                    tempo_ativo_fmt = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                    logado_em_fmt = dt_login.strftime('%d/%m/%Y %H:%M:%S')
                    sessao_info = f"🟢 Conectado ao Serviço SROP (Logado em: {logado_em_fmt} | Tempo Ativo: {tempo_ativo_fmt} | Limite: 4 Horas)"
                
                st.success(sessao_info)
                
                st.markdown("### 📅 Parâmetros de Consulta")
                from datetime import timedelta
                ontem = datetime.today() - timedelta(days=1)
                
                col_data_ini, col_data_fim = st.columns(2)
                with col_data_ini:
                    data_inicial = st.date_input("Data Inicial do Registro", value=ontem, format="DD/MM/YYYY", key=f"exec_dt_ini_{id_servico}")
                with col_data_fim:
                    data_final = st.date_input("Data Final do Registro", value=ontem, format="DD/MM/YYYY", key=f"exec_dt_fim_{id_servico}")
                
                st.write("")
                
                # Trava de Segurança para períodos longos
                from datetime import timedelta
                periodo_longo = (data_final - data_inicial) > timedelta(days=1)
                pode_executar = True
                
                if periodo_longo:
                    st.warning("⚠️ **Aviso de Sobrecarga:** O período selecionado é maior que 1 dia! Consultas longas podem retornar centenas de registros e demorar muito tempo para serem concluídas.")
                    if not st.checkbox("Estou ciente e desejo executar a consulta mesmo assim.", key=f"chk_ciente_{id_servico}"):
                        pode_executar = False
                
                col_btn_run, col_btn_cancel, col_btn_logoff = st.columns(3)
                
                with col_btn_run:
                    btn_run = st.button("🚀 Consultar e Extrair Dados", type="primary", use_container_width=True, disabled=not pode_executar, key=f"btn_run_{id_servico}")
                with col_btn_cancel:
                    placeholder_cancel = st.empty()
                    btn_cancel = placeholder_cancel.button("⏹️ Cancelar Extração Agora", use_container_width=True, disabled=not btn_run, key=f"btn_interrupt_{id_servico}")
                with col_btn_logoff:
                    btn_logoff = st.button("🔴 Encerrar Sessão", use_container_width=True, disabled=(btn_run), key=f"btn_logoff_{id_servico}")
                
                if btn_logoff:
                    with st.spinner("Enviando comando de logoff para o servidor..."):
                        import automacao as aut
                        aut.encerrar_sessao_srop(st.session_state[cookie_key], url_login)
                        db.limpar_sessao(id_servico)
                        st.session_state.pop(cookie_key, None)
                        st.session_state.pop(result_key, None)
                        st.session_state.pop(f"srop_login_time_{id_servico}", None)
                        st.session_state.pop(f"zip_{result_key}", None)
                    st.success("Sessão encerrada com sucesso no servidor e no banco!")
                    st.rerun()
                
                if btn_run:
                    import shutil, os
                    
                    st.info("💡 **A extração começou!** Se você perceber que colocou filtros errados ou quiser desistir, clique no botão **Cancelar Extração Agora** acima.")
                        
                    with st.status("Iniciando consulta e extração...", expanded=True) as status_ui:
                        def atualizar_status(mensagem: str):
                            status_ui.update(label=mensagem, state="running", expanded=True)
                            st.write(mensagem)
                        
                        # Pasta temporária para salvar os PDFs baixados
                        temp_dir = os.path.join(os.getcwd(), "dados_pdf_temp")
                        if os.path.exists(temp_dir):
                            shutil.rmtree(temp_dir, ignore_errors=True)
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        try:
                            import automacao as aut
                            import extrair_bo as ex_bo
                            
                            # Formata as datas para YYYY-MM-DD
                            data_ini_str = data_inicial.strftime("%Y-%m-%d")
                            data_fim_str = data_final.strftime("%Y-%m-%d")
                            
                            pdf_paths = aut.consultar_e_baixar_srop(
                                session_state=st.session_state[cookie_key],
                                url_consulta=url_consulta,
                                url_pdf_template=url_pdf,
                                data_inicial=data_ini_str,
                                data_final=data_fim_str,
                                temp_dir=temp_dir,
                                status_callback=atualizar_status
                            )
                            
                            if not pdf_paths:
                                status_ui.update(label="Integração finalizada.", state="complete", expanded=True)
                                st.warning("⚠️ Nenhum Boletim de Ocorrência foi retornado para o período selecionado.")
                                st.session_state.pop(result_key, None)
                            else:
                                atualizar_status(f"Processando {len(pdf_paths)} arquivos PDF baixados...")
                                
                                # Carrega os mapeamentos e listas de bairros/municípios do banco de dados
                                db_mappings = {
                                    "mapa_upms": db.obter_mapeamento_upms(),
                                    "mapa_nomes_mun": db.obter_mapeamento_nomes_municipios(),
                                    "mapa_nomes_bai": db.obter_mapeamento_nomes_bairros(),
                                    "mapa_alternativos_bai": db.obter_mapeamento_alternativo_bairros(),
                                    "mapa_mun_todos": db.obter_municipios_com_bairro_todos_unico()
                                }
                                
                                lista_municipios, bairros_por_mun = ex_bo.carregar_dados_banco()
                                
                                resultados = []
                                for idx, pdf_path in enumerate(pdf_paths):
                                    filename = os.path.basename(pdf_path)
                                    atualizar_status(f"Analisando texto do BO {idx+1}/{len(pdf_paths)}: {filename}...")
                                    
                                    texto = ""
                                    try:
                                        texto = ex_bo.extrair_texto_pdf(pdf_path)
                                    except Exception as e:
                                        st.error(f"Erro ao extrair texto do PDF {filename}: {str(e)}")
                                        
                                    if not texto:
                                        res = {
                                            "ARQUIVO": filename,
                                            "BO_NUMERO": "Erro na leitura",
                                            "NARRATIVA": "Erro ao extrair texto do arquivo PDF.",
                                            "PROVIDENCIAS": "NI"
                                        }
                                    else:
                                        # Processa usando o analisador unificado do script extrair_bo
                                        res = ex_bo.processar_texto_bo(
                                            texto,
                                            filename,
                                            db_mappings,
                                            lista_municipios,
                                            bairros_por_mun
                                        )
                                    resultados.append(res)
                                    
                                # Compila tudo em um DataFrame e ordena
                                df_res = pd.DataFrame(resultados)
                                df_res = ex_bo.ordenar_dataframe(df_res)
                                
                                # Ajusta o índice para iniciar em 1 para visualização
                                df_res.index = range(1, len(df_res) + 1)
                                
                                status_ui.update(label="Consulta e Extração concluídas com sucesso!", state="complete", expanded=True)
                                
                                # Guarda os resultados no session_state para persistir na tela após interações
                                st.session_state[result_key] = df_res
                                
                                # Comprime os PDFs baixados em um arquivo ZIP e guarda na sessão
                                import zipfile
                                import io
                                zip_buffer = io.BytesIO()
                                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                                    for pdf_path in pdf_paths:
                                        if os.path.exists(pdf_path):
                                            zip_file.write(pdf_path, os.path.basename(pdf_path))
                                
                                st.session_state[f"zip_{result_key}"] = zip_buffer.getvalue()
                                
                                st.success(f"🎉 Extração concluída! {len(resultados)} boletins processados com sucesso.")
                                
                        except Exception as error_exec:
                            status_ui.update(label="Ocorreu um erro na consulta.", state="error", expanded=True)
                            err_str = str(error_exec)
                            st.error(f"❌ {err_str}")
                            # Se a sessão expirou, removemos o estado da sessão para forçar novo login
                            if "Sessão expirada" in err_str:
                                st.session_state.pop(cookie_key, None)
                                db.limpar_sessao(id_servico)
                                st.warning("🔄 Sessão expirada no portal. O banco de dados foi limpo. Por favor, realize o login novamente.")
                                st.rerun()
                        finally:
                            # Limpa os PDFs temporários do servidor
                            if os.path.exists(temp_dir):
                                shutil.rmtree(temp_dir, ignore_errors=True)
                            # Desativa o botão de cancelar imediatamente após o término do processamento
                            placeholder_cancel.button("⏹️ Cancelar Extração Agora", use_container_width=True, disabled=True, key=f"btn_interrupt_done_{id_servico}")
            
            # Exibe o resultado e o botão de download se houver dados no session_state
            if result_key in st.session_state:
                df_result = st.session_state[result_key]
                
                st.markdown("---")
                st.subheader("📋 Boletins Extraídos da Consulta")
                st.dataframe(df_result, width="stretch")
                
                # Gera o arquivo Excel para Download
                import io
                buffer_xlsx = io.BytesIO()
                with pd.ExcelWriter(buffer_xlsx, engine='openpyxl') as writer:
                    df_result.to_excel(writer, index=False, sheet_name='BOs_SROP')
                    
                dt_ini_lbl = "consulta"
                dt_fim_lbl = "consulta"
                if f"exec_dt_ini_{id_servico}" in st.session_state:
                    dt_ini_lbl = st.session_state[f"exec_dt_ini_{id_servico}"].strftime('%d-%m-%Y')
                if f"exec_dt_fim_{id_servico}" in st.session_state:
                    dt_fim_lbl = st.session_state[f"exec_dt_fim_{id_servico}"].strftime('%d-%m-%Y')
                
                nome_download = f"SROP_BOs_Extraidos_{dt_ini_lbl}_a_{dt_fim_lbl}.xlsx"
                
                col_btn1, col_btn2 = st.columns(2)
                
                with col_btn1:
                    st.download_button(
                        label="📥 Baixar Planilha de BOs (.xlsx)",
                        data=buffer_xlsx.getvalue(),
                        file_name=nome_download,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key=f"btn_dl_srop_{id_servico}"
                    )
                    
                with col_btn2:
                    zip_key = f"zip_{result_key}"
                    if zip_key in st.session_state:
                        # O formato atualizado solicitado pelo usuário
                        nome_zip = f"srop_bo_por_data_registro_{dt_ini_lbl}-{dt_fim_lbl}.zip"
                        st.download_button(
                            label="🗂️ Baixar PDFs Analisados (.zip)",
                            data=st.session_state[zip_key],
                            file_name=nome_zip,
                            mime="application/zip",
                            use_container_width=True,
                            key=f"btn_dl_zip_{id_servico}"
                        )
