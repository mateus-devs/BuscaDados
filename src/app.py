import streamlit as st
import pandas as pd
import src.banco as db
import sqlite3

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
        if st.button("➕ Cadastrar Novo Município", use_container_width=True):
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
                
                if c_vis.button("👁️ Ver", key=f"vis_mun_{id_atual}", use_container_width=True):
                    st.session_state.sub_tela_mun = "formulario"; st.session_state.modo_form_mun = "visualizar"
                    st.session_state.dados_sel_mun = {"ID": id_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()
                    
                if c_edt.button("✏️ Editar", key=f"edt_mun_{id_atual}", use_container_width=True):
                    st.session_state.sub_tela_mun = "formulario"; st.session_state.modo_form_mun = "editar"
                    st.session_state.dados_sel_mun = {"ID": id_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()
                    
                if c_exc.button("🗑️ Excluir", key=f"exc_mun_{id_atual}", use_container_width=True, type="primary"):
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
            if c_salvar.button("💾 Salvar no Banco", key="btn_salvar_mun", use_container_width=True):
                if novo_mun:
                    if db.salvar_registro("municipios", {"Municipio": novo_mun, "Estado": estado_mun}):
                        st.session_state.sub_tela_mun = "listar"; st.session_state.mensagem_sucesso = f"🎉 Município '{novo_mun}' cadastrado com sucesso!"; st.rerun()
                    else: st.error(f"⚠️ Erro: O município '{novo_mun}' já existe!")
                else: st.error("Por favor, digite o nome do município.")
            if c_cancelar.button("❌ Cancelar e Voltar", key="btn_cancelar_cad_mun", use_container_width=True):
                st.session_state.sub_tela_mun = "listar"; st.rerun()
                    
        elif modo == "visualizar":
            if st.button("⬅️ Voltar para a Consulta", key="btn_voltar_vis_mun", use_container_width=True):
                st.session_state.sub_tela_mun = "listar"; st.rerun()
                
        elif modo == "editar":
            c_atualizar, c_cancelar = st.columns(2)
            if c_atualizar.button("💾 Salvar Alterações", key="btn_update_mun", use_container_width=True):
                if novo_mun:
                    conn = sqlite3.connect("buscadados.db"); cursor = conn.cursor()
                    cursor.execute("UPDATE municipios SET Municipio = ?, Estado = ? WHERE ID = ?", (novo_mun, estado_mun, dados["ID"]))
                    conn.commit(); conn.close()
                    st.session_state.sub_tela_mun = "listar"; st.session_state.mensagem_sucesso = "✏️ Município alterado com sucesso!"; st.rerun()
                else: st.error("O nome do município não pode ficar em branco.")
            if c_cancelar.button("❌ Cancelar", key="btn_cancelar_edit_mun", use_container_width=True):
                st.session_state.sub_tela_mun = "listar"; st.rerun()
                
        elif modo == "excluir":
            c_deletar, c_voltar = st.columns(2)
            if c_deletar.button("🗑️ Sim, Excluir Registro", key="btn_delete_confirm_mun", use_container_width=True):
                db.excluir_registro("municipios", dados["ID"])
                st.session_state.sub_tela_mun = "listar"; st.session_state.mensagem_sucesso = f"🗑️ Município '{dados['Municipio']}' removido!"; st.rerun()
            if c_voltar.button("❌ Cancelar e Manter", key="btn_voltar_del_mun", use_container_width=True):
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
        if st.button("➕ Cadastrar Novo Bairro", use_container_width=True):
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
                col_id, col_nome, col_mun, col_acoes = st.columns([0.8, 3, 3, 3.2])
                with col_id: st.write("**ID**")
                with col_nome: st.write("**Bairro**")
                with col_mun: st.write("**Município Vinculado**")
                with col_acoes: st.write("**Ações Disponíveis**")
                st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
                
                for idx, row in df_bai.iterrows():
                    id_atual = row["ID"]
                    bai_atual = row["Bairro"]
                    mun_atual = row["Municipio"]
                    
                    c_id, c_nome, c_mun, c_vis, c_edt, c_exc = st.columns([0.8, 3, 3, 1, 1, 1.2])
                    c_id.write(f"`{id_atual}`")
                    c_nome.write(bai_atual)
                    c_mun.text(mun_atual)
                    
                    if c_vis.button("👁️ Ver", key=f"vis_bai_{id_atual}", use_container_width=True):
                        st.session_state.sub_tela_bai = "formulario"; st.session_state.modo_form_bai = "visualizar"
                        st.session_state.dados_sel_bai = {"ID": id_atual, "Bairro": bai_atual, "Municipio": mun_atual}; st.rerun()
                    if c_edt.button("✏️ Editar", key=f"edt_bai_{id_atual}", use_container_width=True):
                        st.session_state.sub_tela_bai = "formulario"; st.session_state.modo_form_bai = "editar"
                        st.session_state.dados_sel_bai = {"ID": id_atual, "Bairro": bai_atual, "Municipio": mun_atual}; st.rerun()
                    if c_exc.button("🗑️ Excluir", key=f"exc_bai_{id_atual}", use_container_width=True, type="primary"):
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
            "Vincular ao @Municipio", 
            lista_formatada if lista_formatada else ["Cadastre um município primeiro antes de continuar"], 
            index=idx_padrao, 
            disabled=campos_bloqueados, 
            key="sel_mun_bai_form"
        )
        
        st.write("")
        if modo == "cadastro":
            c_s, c_c = st.columns(2)
            if c_s.button("💾 Salvar Bairro", key="btn_salvar_bairro_db", use_container_width=True):
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
            if c_c.button("❌ Cancelar e Voltar", key="btn_cancelar_cad_bai", use_container_width=True): 
                st.session_state.sub_tela_bai = "listar"; st.rerun()
                
        elif modo == "visualizar":
            if st.button("⬅️ Voltar para a Consulta", key="btn_voltar_vis_bai", use_container_width=True): 
                st.session_state.sub_tela_bai = "listar"; st.rerun()
                
        elif modo == "editar":
            c_up, c_cc = st.columns(2)
            if c_up.button("💾 Salvar Alterações", key="btn_update_bairro_db", use_container_width=True):
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
            if c_cc.button("❌ Cancelar", key="btn_cancelar_edit_bai", use_container_width=True): 
                st.session_state.sub_tela_bai = "listar"; st.rerun()
                
        elif modo == "excluir":
            c_del, c_v = st.columns(2)
            if c_del.button("🗑️ Sim, Excluir Registro", key="btn_delete_confirm_bai", use_container_width=True):
                db.excluir_registro("bairros", dados["ID"])
                st.session_state.sub_tela_bai = "listar"
                st.session_state.mensagem_sucesso = f"🗑️ Bairro '{dados['Bairro']}' removido com sucesso!"
                st.rerun()
                if c_v.button("❌ Cancelar e Manter", key="btn_voltar_del_bai", use_container_width=True):
                    st.session_state.sub_tela_bai = "listar";
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
        if st.button("➕ Cadastrar Nova UPM", use_container_width=True):
            st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "cadastro"
            st.session_state.dados_sel_upm = {"ID": None, "UPM": "", "Descricao": "", "Bairro": "", "Municipio": "", "Estado": ""}; st.rerun()
            
        st.write("")
        df_upm = db.listar_dados("upms")
        
        if df_upm.empty:
            st.info("Nenhuma UPM cadastrada no banco de dados ainda.")
        else:
            st.subheader("UPMs Cadastradas")
            col_id, col_upm, col_bai, col_mun, col_vis, col_edt, col_vinc, col_exc = st.columns([0.8, 2.3, 2.3, 2.3, 1, 1, 1, 1.2])
            with col_id: st.write("**ID**")
            with col_upm: st.write("**UPM**")
            with col_bai: st.write("**Bairro**")
            with col_mun: st.write("**Município**")
            with col_vis: st.write("**Ver**")
            with col_edt: st.write("**Editar**")
            with col_vinc: st.write("**Vincular**")
            with col_exc: st.write("**Excluir**")
            st.markdown("<hr style='margin: 0px 0px 10px 0px; border-color: #f0f2f6;'>", unsafe_allow_html=True)
            
            for idx, row in df_upm.iterrows():
                id_atual = row["ID"]
                upm_atual = row["UPM"]
                desc_atual = row.get("Descricao", "")
                bai_atual = row["Bairro"]
                mun_atual = row["Municipio"]
                est_atual = row["Estado"]
                
                c_id, c_upm, c_bai, c_mun, c_vis, c_edt, c_vinc, c_exc = st.columns([0.8, 2.3, 2.3, 2.3, 1, 1, 1, 1.2])
                c_id.write(f"`{id_atual}`"); c_upm.write(upm_atual); c_bai.write(bai_atual); c_mun.write(mun_atual)
                
                if c_vis.button("👁️ Ver", key=f"vis_upm_{id_atual}", use_container_width=True):
                    st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "visualizar"
                    st.session_state.dados_sel_upm = {"ID": id_atual, "UPM": upm_atual, "Descricao": desc_atual, "Bairro": bai_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()
                if c_edt.button("✏️ Editar", key=f"edt_upm_{id_atual}", use_container_width=True):
                    st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "editar"
                    st.session_state.dados_sel_upm = {"ID": id_atual, "UPM": upm_atual, "Descricao": desc_atual, "Bairro": bai_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()
                if c_vinc.button("🔗 Vincular", key=f"vinc_upm_{id_atual}", use_container_width=True):
                    st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "vincular"
                    st.session_state.dados_sel_upm = {"ID": id_atual, "UPM": upm_atual, "Descricao": desc_atual, "Bairro": bai_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()
                if c_exc.button("🗑️ Excluir", key=f"exc_upm_{id_atual}", use_container_width=True, type="primary"):
                    st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "excluir"
                    st.session_state.dados_sel_upm = {"ID": id_atual, "UPM": upm_atual, "Descricao": desc_atual, "Bairro": bai_atual, "Municipio": mun_atual, "Estado": est_atual}; st.rerun()

    elif st.session_state.sub_tela_upm == "formulario":
        modo = st.session_state.modo_form_upm; dados = st.session_state.dados_sel_upm
        campos_bloqueados = True if modo in ["visualizar", "excluir"] else False
        
        if modo == "cadastro": st.subheader("➕ Cadastrar Nova UPM")
        elif modo == "visualizar": st.subheader(f"👁️ Visualizando UPM ID: {dados['ID']}")
        elif modo == "editar": st.subheader(f"✏️ Editando UPM ID: {dados['ID']}")
        elif modo == "excluir": st.subheader(f"⚠️ Confirmar Exclusão da UPM ID: {dados['ID']}"); st.error(f"Apagar a UPM '{dados['UPM']}'?")
        elif modo == "vincular": st.subheader(f"🔗 Vincular Bairros à UPM ID: {dados['ID']}")

        nome_upm = st.text_input("Nome/Identificador da UPM", value=dados["UPM"], disabled=campos_bloqueados or modo == "vincular", key="upm_nome_in").strip()
        descricao_upm = st.text_area("Descrição da UPM", value=dados.get("Descricao", ""), disabled=campos_bloqueados or modo == "vincular", key="upm_desc_in", height=120).strip()
        
        df_b = db.listar_dados("bairros"); df_m = db.listar_dados("municipios")

        if modo == "vincular":
            if df_b.empty:
                st.warning("Cadastre bairros antes de criar vínculos.")
            else:
                df_bairros_completo = df_b.merge(df_m, on="Municipio", how="left")
                df_bairros_completo["Exibicao"] = df_bairros_completo["Bairro"] + " (" + df_bairros_completo["Municipio"] + ")"
                lista_exibicao = df_bairros_completo["Exibicao"].tolist()

                bairros_vinculados = db.listar_bairros_vinculados(dados["ID"])
                selecionados_padrao = []
                if not bairros_vinculados.empty:
                    selecionados_padrao = (bairros_vinculados["Bairro"] + " (" + bairros_vinculados["Municipio"] + ")").tolist()

                selecionados = st.multiselect("Selecione os bairros a vincular", lista_exibicao, default=selecionados_padrao, key="upm_bairros_vinc")
                st.write("")
                if not bairros_vinculados.empty:
                    st.subheader("Bairros atualmente vinculados")
                    st.table(bairros_vinculados[["Bairro", "Municipio"]])

                c_s, c_c = st.columns(2)
                if c_s.button("💾 Salvar Vínculos", use_container_width=True, key="upm_vinc_save"):
                    selecionados_ids = []
                    for item in selecionados:
                        linha = df_bairros_completo[df_bairros_completo["Exibicao"] == item]
                        if not linha.empty:
                            selecionados_ids.append(int(linha.iloc[0]["ID"]))
                    db.atualizar_vinculo_bairros(dados["ID"], selecionados_ids)
                    st.session_state.sub_tela_upm = "listar"
                    st.session_state.mensagem_sucesso = f"🔗 Bairros vinculados à UPM '{dados['UPM']}'!"
                    st.rerun()
                if c_c.button("❌ Voltar", use_container_width=True, key="upm_vinc_cancel"):
                    st.session_state.sub_tela_upm = "listar"; st.rerun()

            st.write("")
            if not df_b.empty and not df_m.empty:
                st.write("#### UPM selecionada")
                st.text_input("Nome/Identificador da UPM", value=dados["UPM"], disabled=True, key="upm_vinc_nome")
                st.text_area("Descrição da UPM", value=dados.get("Descricao", ""), disabled=-True, key="upm_vinc_desc", height=100)

            if modo == "cadastro":
                c_s, c_c = st.columns(2)
                if c_s.button("💾 Salvar UPM", use_container_width=True, key="upm_sav_b"):
                    if nome_upm:
                        if db.salvar_registro("upms", {"UPM": nome_upm, "Descricao": descricao_upm, "Bairro": "", "Municipio": "", "Estado": ""}):
                            st.session_state.sub_tela_upm = "listar"; st.session_state.mensagem_sucesso = f"🎉 UPM '{nome_upm}' cadastrada!"; st.rerun()
                        else: st.error("⚠️ Esta UPM já existe!")
                if c_c.button("❌ Voltar", use_container_width=True, key="upm_bck_b"): st.session_state.sub_tela_upm = "listar"; st.rerun()

            else:
                if not df_b.empty and not df_m.empty:
                    df_bairros_completo = df_b.merge(df_m, on="Municipio", how="left")
                    df_bairros_completo["Exibicao"] = df_bairros_completo["Bairro"] + " (" + df_bairros_completo["Municipio"] + ")"
                    lista_exibicao = df_bairros_completo["Exibicao"].tolist()
                    
                    str_busca = f"{dados['Bairro']} ({dados['Municipio']})"
                    idx_upm = lista_exibicao.index(str_busca) if str_busca in lista_exibicao else 0
                    
                    bairro_selecionado_string = st.selectbox("Pesquise e escolha o Bairro", lista_exibicao, index=idx_upm, disabled=campos_bloqueados, key="upm_b_sel")
                    dados_bairro_escolhido = df_bairros_completo[df_bairros_completo["Exibicao"] == bairro_selecionado_string].iloc[0]
                    
                    st.write("### Informações Vinculadas Automaticamente")
                    col_b, col_m, col_e = st.columns(3)
                    col_b.text_input("Bairro", value=dados_bairro_escolhido["Bairro"], disabled=True, key="upm_b_v")
                    col_m.text_input("Município", value=dados_bairro_escolhido["Municipio"], disabled=True, key="upm_m_v")
                    col_e.text_input("Estado", value=dados_bairro_escolhido["Estado"], disabled=True, key="upm_e_v")
                    
                    st.write("")
                    if modo == "visualizar":
                        if st.button("⬅️ Voltar", use_container_width=True, key="upm_v_b"): st.session_state.sub_tela_upm = "listar"; st.rerun()
                        if st.button("🔗 Vincular Bairros à UPM", use_container_width=True, key="upm_v_b_link"): st.session_state.sub_tela_upm = "formulario"; st.session_state.modo_form_upm = "vincular"; st.rerun()
                    elif modo == "editar":
                        c_s, c_c = st.columns(2)
                        if c_s.button("💾 Salvar Alterações", use_container_width=True, key="upm_edt_b"):
                            conn = sqlite3.connect("buscadados.db"); cursor = conn.cursor()
                            cursor.execute("UPDATE upms SET UPM = ?, Descricao = ?, Bairro = ?, Municipio = ?, Estado = ? WHERE ID = ?", (nome_upm, descricao_upm, dados_bairro_escolhido["Bairro"], dados_bairro_escolhido["Municipio"], dados_bairro_escolhido["Estado"], dados["ID"]))
                            conn.commit(); conn.close()
                            st.session_state.sub_tela_upm = "listar"; st.session_state.mensagem_sucesso = "✏️ UPM modificada!"; st.rerun()
                        if c_c.button("❌ Cancelar", use_container_width=True, key="upm_can_b"): st.session_state.sub_tela_upm = "listar"; st.rerun()
                    elif modo == "excluir":
                        c_s, c_c = st.columns(2)
                        if c_s.button("🗑️ Sim, Deletar", use_container_width=True, key="upm_del_b"):
                            db.excluir_registro("upms", dados["ID"])
                            st.session_state.sub_tela_upm = "listar"; st.session_state.mensagem_sucesso = "🗑️ UPM deletada!"; st.rerun()
                        if c_c.button("❌ Cancelar", use_container_width=True, key="upm_man_b"): st.session_state.sub_tela_upm = "listar"; st.rerun()
                else:
                    st.warning("Cadastre bairros e municípios primeiro.")
                    if st.button("⬅️ Voltar", use_container_width=True, key="upm_err_b"): st.session_state.sub_tela_upm = "listar"; st.rerun()

# =====================================================================
# 4. TELA: IMPORTAÇÃO DE ARQUIVO DE DADOS
# =====================================================================
elif menu == "Importação de Arquivo de Dados":
    st.title("📥 Importação de Arquivo de Dados")
    st.info("Módulo estrutural pronto para receber a engenharia de dados do Power BI.")
