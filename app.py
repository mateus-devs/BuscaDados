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
            background-color: #f8f9fa !important;
            padding: 12px 16px !important;
            border-radius: 8px !important;
            margin-bottom: 8px !important;
            border: 1px solid #e9ecef !important;
            transition: all 0.2s ease-in-out !important;
            cursor: pointer !important;
            width: 100% !important;
            display: flex !important;
            align-items: center !important;
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label:hover {
            background-color: #e2e6ea !important;
            border-color: #dae0e5 !important;
            transform: translateX(4px);
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label[data-checked="true"] {
            background-color: #ff4b4b !important;
            border-color: #ff4b4b !important;
            color: white !important;
            font-weight: bold !important;
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label span[data-testid="stRadioButtonChoiceIndicator"] {
            display: none !important;
        }
        div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label div[data-testid="stWidgetMarkdownInsideRadio"] {
            padding-left: 0px !important;
            margin-left: 0px !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- CONTROLE DE MENSAGENS E ESTADOS ---
if "mensagem_sucesso" not in st.session_state: st.session_state.mensagem_sucesso = None

if "sub_tela_mun" not in st.session_state: st.session_state.sub_tela_mun = "listar"
if "sub_tela_bai" not in st.session_state: st.session_state.sub_tela_bai = "listar"
if "sub_tela_upm" not in st.session_state: st.session_state.sub_tela_upm = "listar"

if "modo_form_mun" not in st.session_state: st.session_state.modo_form_mun = "cadastro"
if "modo_form_bai" not in st.session_state: st.session_state.modo_form_bai = "cadastro"
if "modo_form_upm" not in st.session_state: st.session_state.modo_form_upm = "cadastro"

if "dados_sel_mun" not in st.session_state: st.session_state.dados_sel_mun = {"ID": None, "Municipio": "", "Estado": "MT - Mato Grosso"}
if "dados_sel_bai" not in st.session_state: st.session_state.dados_sel_bai = {"ID": None, "Bairro": "", "Municipio": ""}
if "dados_sel_upm" not in st.session_state: st.session_state.dados_sel_upm = {"ID": None, "UPM": "", "Descricao": "", "Bairro": "", "Municipio": "", "Estado": ""}

# --- MENU LATERAL ESQUERDO ---
st.sidebar.title("🤖 BuscaDados")
st.sidebar.subheader("Menu Principal")

menu = st.sidebar.radio(
    "Selecione uma opção:",
    ["Manutenção de Município", "Manutenção de Bairro", "Manutenção de UPMs", "Importação de Arquivo de Dados"],
    label_visibility="collapsed"
)

# =====================================================================
# 1. TELA: MANUTENÇÃO DE MUNICÍPIO (COMPLETA)
# =====================================================================
if menu == "Manutenção de Município":
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
        
        if df_mun.empty:
            st.info("Nenhum município cadastrado no banco de dados ainda.")
        else:
            st.subheader("Municípios Cadastrados")
            col_id, col_nome, col_est, col_acoes = st.columns([0.8, 3, 3, 3.2])
            with col_id: st.write("**ID**")
            with col_nome: st.write("**Município**")
            with col_est: st.write("**Estado**")
            with col_acoes: st.write("**Ações Disponíveis**")
            st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            for idx, row in df_mun.iterrows():
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
elif menu == "Manutenção de Bairro":
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
            
            st.write("")
            st.subheader("Bairros Cadastrados")
            
            if df_bai.empty:
                st.warning("Nenhum bairro encontrado para os filtros selecionados.")
            else:
                col_id, col_nome, col_mun, col_acoes = st.columns([0.8, 2.5, 2.5, 4.2])
                with col_id: st.write("**ID**")
                with col_nome: st.write("**Bairro**")
                with col_mun: st.write("**Município Vinculado**")
                with col_acoes: st.write("**Ações Disponíveis**")
                st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
                
                for idx, row in df_bai.iterrows():
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
elif menu == "Manutenção de UPMs":
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
        
        if df_upm.empty:
            st.info("Nenhuma UPM cadastrada no banco de dados ainda.")
        else:
            st.subheader("UPMs Cadastradas")
            col_id, col_upm, col_desc, col_vis, col_edt, col_vinc, col_exc = st.columns([0.8, 2.2, 3.6, 1.1, 1.1, 1.1, 1.1])
            with col_id: st.write("**ID**")
            with col_upm: st.write("**UPM**")
            with col_desc: st.write("**Descrição**")
            with col_vis: st.write("**Ver**")
            with col_edt: st.write("**Editar**")
            with col_vinc: st.write("**Vincular**")
            with col_exc: st.write("**Excluir**")
            st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            for idx, row in df_upm.iterrows():
                id_atual = row["ID"]
                upm_atual = row["UPM"]
                desc_atual = row.get("Descricao", "")
                
                c_id, c_upm, c_desc, c_vis, c_edt, c_vinc, c_exc = st.columns([0.8, 2.2, 3.6, 1.1, 1.1, 1.1, 1.1])
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
# 4. TELA: IMPORTAÇÃO DE ARQUIVO DE DADOS
# =====================================================================
elif menu == "Importação de Arquivo de Dados":
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
                        upm_val = mapa_upms.get((b_norm, m_norm), "NI")
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
                    processed_data = buffer.getvalue()
                    
                    st.write("")
                    st.download_button(
                        label="📥 Baixar Planilha com Coluna UPM (.xlsx)",
                        data=processed_data,
                        file_name="planilha_com_upms.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        width="stretch"
                    )
                
        except Exception as e:
            st.error(f"⚠️ Erro ao ler ou processar o arquivo: {str(e)}")
    else:
        st.info("💡 Dica: Prepare uma planilha contendo as colunas 'Bairro' e 'Municipio' para cruzar com o banco de dados do sistema.")
