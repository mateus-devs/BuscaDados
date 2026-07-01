import os
import re
import argparse
import sys
import pandas as pd
from datetime import datetime
import pypdf
import unicodedata

# Garante que podemos importar o módulo banco se executado de fora do diretório do projeto
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

try:
    import banco as db
except ImportError:
    print("Erro: Não foi possível importar 'banco.py'. Certifique-se de executar o script na pasta do projeto.")
    sys.exit(1)

def extrair_texto_pdf(pdf_source, layout_id: int = 1) -> str:
    """Extrai todo o texto contido em um arquivo PDF, com detecção inteligente de cabeçalhos."""
    try:
        reader = pypdf.PdfReader(pdf_source)
        pages_lines = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                pages_lines.append(lines)
                
        if not pages_lines:
            return ""
            
        # Busca nomes de grupos para não apagar por acidente
        nomes_grupos = set()
        grupos_df = db.listar_grupos(layout_id)
        if not grupos_df.empty:
            nomes_grupos = {str(g).strip().upper() for g in grupos_df["Nome_Grupo"]}
            
        # Detecção Dinâmica de Cabeçalhos e Rodapés
        header_counts = {}
        if len(pages_lines) > 1:
            for lines in pages_lines:
                for line in lines[:4]: # Top 4 linhas
                    ls = line.strip().upper()
                    if len(ls) > 5 and ':' not in ls and ls not in nomes_grupos:
                        header_counts[ls] = header_counts.get(ls, 0) + 1
                        
        headers_to_remove = {line for line, count in header_counts.items() if count > 1}
        
        texto_final = ""
        for lines in pages_lines:
            for i, line in enumerate(lines):
                ls = line.strip().upper()
                if i < 4 and ls in headers_to_remove:
                    continue # Remove o cabeçalho dinâmico
                texto_final += line + "\n"
                
        return texto_final
    except Exception as e:
        source_name = getattr(pdf_source, 'name', str(pdf_source))
        print(f"Erro ao ler o PDF '{source_name}': {str(e)}")
        return ""

def normalizar_espacos(texto: str) -> str:
    """Substitui sequências de espaços e quebras de linha por um único espaço."""
    return re.sub(r'\s+', ' ', texto).strip()

def limpar_campo_extraido(val: str) -> str:
    """Limpa prefixos comuns (de, do, da, em, no, na) e pontuações de campos extraídos."""
    if not val:
        return ""
    val = val.strip()
    # Remove prefixos comuns no início (case-insensitive)
    val = re.sub(r'^(?:de|do|da|em|no|na)\s+', '', val, flags=re.IGNORECASE)
    # Remove pontuações e espaços nas extremidades
    val = val.strip(' \t\n\r.,;:\"\'')
    return val

def normalizar_nome_chave(texto: str) -> str:
    """Normaliza o nome de um campo para formato de coluna de banco de dados (UPPERCASE_WITH_UNDERLINE)."""
    if not texto:
        return ""
    t = str(texto).strip()
    nfkd = unicodedata.normalize('NFKD', t)
    sem_acento = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Substitui caracteres especiais, espaços, barras por underline
    nome_chave = re.sub(r'[^A-Za-z0-9]', '_', sem_acento)
    # Remove múltiplos underlines seguidos e pontuações nas pontas
    nome_chave = re.sub(r'_+', '_', nome_chave)
    return nome_chave.strip('_').upper()

def extrair_bo_numero(texto: str) -> str:
    """Extrai o número do boletim de ocorrência."""
    patterns = [
        r'(?:BOLETIM\s+DE\s+OCORRÊNCIA|BOLETIM\s+DE\s+OCORRENCIA|BOLETIM|BO)\s*(?:Nº|Nº|N[oº\.]|NRO)?\s*[:\-\s]*\s*(\d{4}\.\d+|\d+/\d+|\d+-\d+|\d+)',
        r'(?:BO\s*N[oº\.]|BO\s*Nº|BO|Nº\s*BO)\s*[:\-\s]*\s*(\d{4}\.\d+|\d+/\d+|\d+-\d+|\d+)',
        r'(?:REGISTRO|Nº\s+REGISTRO|REGISTRO\s+NRO|REGISTRO\s+Nº|NRO\s+REGISTRO)\s*[:\-\s]*\s*(\d{4}\.\d+|\d+/\d+|\d+-\d+|\d+)',
        r'Nº\s*(?:de\s*)?Controle\s*[:\-\s]*\s*(\d{4}\.\d+|\d+/\d+|\d+-\d+|\d+)',
        r'Boletim\s*[:\-\s]*\s*(\d{4}\.\d+|\d+/\d+|\d+-\d+|\d+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "NI"


def segmentar_texto(texto: str, layout_id: int) -> dict:
    """Segmenta o texto completo do BO em grupos dinamicamente baseados no layout."""
    grupos_df = db.listar_grupos(layout_id)
    if grupos_df.empty:
        return {}
        
    markers = []
    secoes_keys = {}
    
    for _, row in grupos_df.iterrows():
        key = normalizar_nome_chave(row["Nome_Grupo"])
        nome_grupo = str(row["Nome_Grupo"]).strip()
        aliases = [nome_grupo]
        
        nome_limpo = re.sub(r'^\d+[\.\-]\s*', '', nome_grupo)
        if nome_limpo != nome_grupo:
            aliases.append(nome_limpo)
            
        markers.append((key, aliases))
        
        if row["Tem_Itens"]:
            itens_df = db.listar_itens(row["ID"])
            secoes_keys[key] = itens_df["Palavra_Busca"].tolist() if not itens_df.empty else []
        else:
            secoes_keys[key] = []
            
    found_sections = []
    for key, aliases in markers:
        keys_esperadas = secoes_keys.get(key, [])
        for alias in aliases:
            pattern = rf'(?:^|\n)[^\w\d]*({re.escape(alias)})[^\w\d]*(?=\n|$)'
            matches = list(re.finditer(pattern, texto, re.IGNORECASE))
            if not matches:
                continue
                
            best_match = None
            if len(matches) == 1:
                best_match = matches[0]
            else:
                max_keys_found = -1
                for match in matches:
                    start_pos = match.start(1)
                    end_pos = match.end(1)
                    contexto = texto[end_pos:end_pos + 400]
                    
                    keys_found = 0
                    for k in keys_esperadas:
                        if re.search(rf'\b{re.escape(k)}\b.*:', contexto, re.IGNORECASE):
                            keys_found += 1
                    
                    if keys_found > max_keys_found:
                        max_keys_found = keys_found
                        best_match = match
                        
                    # Se encontrou ao menos 1 chave, já confirmamos que este é o cabeçalho real.
                    # Paramos no PRIMEIRO cabeçalho real para evitar que continuações em outras páginas 
                    # roubem o início da seção caso tenham mais chaves.
                    if keys_found > 0:
                        break
                        
                if best_match is None or max_keys_found == 0:
                    best_match = matches[0]  # Se não achou chaves, pega a PRIMEIRA ocorrência do cabeçalho
            
            if best_match:
                start_idx = best_match.start(1)
                end_idx = best_match.end(0)
                found_sections.append((start_idx, end_idx, key))
                break
                
    found_sections.sort(key=lambda x: x[0])
    
    sections_content = {}
    for i in range(len(found_sections)):
        current_start, current_end_label, key = found_sections[i]
        if i + 1 < len(found_sections):
            next_start, _, _ = found_sections[i+1]
            content = texto[current_end_label:next_start]
        else:
            content = texto[current_end_label:]
        content_clean = re.sub(r'^[:\-\s\t]+', '', content).strip()
        sections_content[key] = content_clean
        
    return sections_content

def extrair_pares_chave_valor(secao_text: str, layout_id: int, grupo_id: int) -> dict:
    """Extrai todos os pares chave-valor de uma seção baseado no layout dinâmico."""
    pares = {}
    if not secao_text: return pares
    
    itens_df = db.listar_itens(grupo_id)
    if itens_df.empty: return pares
    
    known_keys = itens_df["Palavra_Busca"].tolist()
    
    # Remove as chaves de metadados especiais do parser normal de texto
    for special in ["*ARQUIVO*", "*BO_NUMERO*", "*DATA_DO_REGISTRO*", "*HORA_DO_REGISTRO*"]:
        if special in known_keys:
            known_keys.remove(special)
            
    extrair_bruto = False
    if "*TEXTO_BRUTO*" in known_keys:
        extrair_bruto = True
        known_keys.remove("*TEXTO_BRUTO*")
        if not known_keys:
            # Se SÓ tem o TEXTO_BRUTO, não precisa rodar a extração regex
            res_bruto = {}
            for _, row in itens_df.iterrows():
                if row["Palavra_Busca"] == "*TEXTO_BRUTO*":
                    if int(row.get("Exportar_Excel", 1)) == 1:
                        nome_col = normalizar_nome_chave(row["Nome_Item_Excel"])
                        res_bruto[nome_col] = secao_text.strip()
            return res_bruto
    
    # Mapeia chaves base (antes do |) para as chaves completas (com contexto)
    base_keys_map = {}
    for k in known_keys:
        base_k = k.split('|')[0].strip()
        if base_k not in base_keys_map:
            base_keys_map[base_k] = []
        base_keys_map[base_k].append(k)
        
    sorted_keys = sorted(list(base_keys_map.keys()), key=len, reverse=True)
    if not sorted_keys: return pares
    
    key_pattern = r'\b(' + '|'.join([re.escape(k) for k in sorted_keys]) + r')\.*:'
    
    # Pattern para detectar campos (barreiras) automáticas: palavras que começam com Maiúscula, seguidas de dois pontos.
    UPPER = r'A-ZÁÉÍÓÚÂÊÔÃÕÇ'
    WORD = r'A-Za-zÀ-ÿ0-9/º°\-.'
    # Pattern 1: Tem ponto(s) antes do dois-pontos. Aceita qualquer palavra no meio.
    p1 = rf'\b([{UPPER}][{WORD}]*(?:\s+[{WORD}]+)*)\s*(?:\.{{2,}}:|\.:)'
    # Pattern 2: Não tem ponto (só dois-pontos). Exige Title Case ou preposições comuns.
    p2 = rf'\b([{UPPER}][{WORD}]*(?:\s+(?:[{UPPER}][{WORD}]*|de|da|do|dos|das|e|ou))*)\s*:'
    barrier_pattern = rf'(?:{p1}|{p2})'
    
    grupos_df = db.listar_grupos(layout_id)
    secoes_nomes = set([g.upper() for g in grupos_df["Nome_Grupo"]])
    
    lines = secao_text.split('\n')
    last_empty_key = None
    last_active_key = None
    
    for line in lines:
        line = line.strip()
        if not line: continue
            
        if (line.startswith('**') and line.endswith('**')) or re.match(r'^[\-\s\*\+=]+$', line):
            continue
            
        if line.upper() in secoes_nomes:
            last_empty_key = None
            last_active_key = None
            continue
            
        matches = list(re.finditer(key_pattern, line, re.IGNORECASE))
        
        if not matches:
            # Verifica se a linha inteira parece ser um novo campo (barreira) não mapeado
            if re.search(r'^\s*' + barrier_pattern, line):
                # Se achou um campo não mapeado, quebra a continuação de multilinhas
                last_active_key = None
                last_empty_key = None
                continue
                
            if last_empty_key:
                pares[last_empty_key] = line.strip()
                last_active_key = last_empty_key
                last_empty_key = None
            elif last_active_key:
                v_atual = pares.get(last_active_key, "")
                pares[last_active_key] = f"{v_atual} {line.strip()}"
            continue
            
        # Ordena matches e extrai valores
        matches.sort(key=lambda x: x.start())
        for i in range(len(matches)):
            match = matches[i]
            chave_encontrada = match.group(1)
            # Para casamentos insensíveis a maiúsculas/minúsculas, pegamos a chave base original
            chave_base = next((k for k in sorted_keys if k.lower() == chave_encontrada.lower()), chave_encontrada)
            
            # Resolve o contexto (se houver | na configuração)
            possiveis_chaves = base_keys_map.get(chave_base, [chave_base])
            chave_padrao = possiveis_chaves[0]
            if len(possiveis_chaves) > 1:
                # Prioriza a chave cujo contexto (palavra após o |) exista na linha
                for pk in possiveis_chaves:
                    if '|' in pk:
                        contexto = pk.split('|')[1].strip()
                        if contexto.upper() in line.upper():
                            chave_padrao = pk
                            break
            val_start = match.end()
            if i + 1 < len(matches):
                val_end = matches[i+1].start()
                valor_bruto = line[val_start:val_end]
            else:
                valor_bruto = line[val_start:]
                
            # NOVIDADE: Verifica se há alguma "barreira implícita" dentro do valor_bruto na mesma linha
            barrier_match = re.search(barrier_pattern, valor_bruto)
            if barrier_match:
                valor_bruto = valor_bruto[:barrier_match.start()]
                
            valor_limpo = limpar_campo_extraido(valor_bruto)
            if valor_limpo:
                pares[chave_padrao] = valor_limpo
                last_active_key = chave_padrao
                last_empty_key = None
            else:
                last_empty_key = chave_padrao
                last_active_key = None

    resultado = {}
    for pb, valor in pares.items():
        # Busca todas as especificações dessa Palavra_Busca no itens_df para suportar duplicados
        for _, row in itens_df.iterrows():
            if row["Palavra_Busca"] == pb:
                if int(row.get("Exportar_Excel", 1)) == 1:
                    nome_col = normalizar_nome_chave(row["Nome_Item_Excel"])
                    resultado[nome_col] = valor
            
    if extrair_bruto:
        for _, row in itens_df.iterrows():
            if row["Palavra_Busca"] == "*TEXTO_BRUTO*":
                if int(row.get("Exportar_Excel", 1)) == 1:
                    nome_col = normalizar_nome_chave(row["Nome_Item_Excel"])
                    resultado[nome_col] = secao_text.strip()
            
    return resultado

def carregar_dados_banco():
    """Carrega dados do banco SQLite para aplicação do algoritmo de fallback."""
    df_m = db.listar_dados("municipios")
    lista_municipios = df_m["Municipio"].tolist() if not df_m.empty else []
    
    df_b = db.listar_bairros_com_municipio()
    bairros_por_mun = {}
    if not df_b.empty:
        for _, row in df_b.iterrows():
            m_norm = db.normalizar_texto(row["Municipio"])
            if m_norm not in bairros_por_mun:
                bairros_por_mun[m_norm] = []
            bairros_por_mun[m_norm].append(row["Bairro"])
            
    return lista_municipios, bairros_por_mun

def aplicar_fallback_municipio_bairro(texto: str, lista_municipios: list, bairros_por_mun: dict):
    """Varre o texto completo para encontrar o Município e o Bairro caso a Regex falhe."""
    text_norm = db.normalizar_texto(texto)
    
    detected_mun = None
    sorted_muns = sorted(lista_municipios, key=len, reverse=True)
    for mun in sorted_muns:
        mun_norm = db.normalizar_texto(mun)
        if mun_norm in text_norm:
            detected_mun = mun
            break
            
    detected_bairro = None
    if detected_mun:
        m_norm = db.normalizar_texto(detected_mun)
        bairros = bairros_por_mun.get(m_norm, [])
        sorted_bairros = sorted(bairros, key=len, reverse=True)
        for bairro in sorted_bairros:
            if len(bairro) <= 2:
                continue
            bairro_norm = db.normalizar_texto(bairro)
            if bairro_norm in text_norm:
                detected_bairro = bairro
                break
                
    return detected_mun, detected_bairro

def extrair_datas_registro(texto: str) -> tuple:
    """Extrai a data e hora do registro a partir da linha IMPRESSO EM."""
    match = re.search(r'IMPRESSO\s+EM\s*(\d{2}/\d{2}/\d{4})\s*às\s*(\d{2}:\d{2})', texto, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "NI", "NI"

def processar_secao_chave_valor(pares_extraidos: dict, prefixo_grupo: str) -> dict:
    """O layout agora define o nome exato. Não concatenamos mais prefixos."""
    return pares_extraidos

def remover_cabecalhos_rodapes(texto: str, layout_id: int) -> str:
    """Remove cabeçalhos e rodapés repetidos."""
    patterns = [
        r'^ESTADO DE MATO GROSSO', r'^SECRETARIA DE ESTADO', r'^POLÍCIA JUD', r'^POLICIA JUD',
        r'^DELEGAC', r'^BOLETIM DE OCORRÊNCIA', r'^BOLETIM DE OCORRENCIA', r'^ELABORADO POR',
        r'^EDITADO POR', r'^DATA/HORA DA COMUNICA', r'^DATA/HORA DA COMUNICACAO',
        r'^IMPRESSO EM', r'^IMPRESSO POR', r'^Telefone:.*E-Mail', r'delvirtual@pjc\.mt\.gov\.br',
        r'^Pág\s*[:\.]?\s*\d+\s*de\s*\d+$', r'^Página\s*\d+\s*de\s*\d+$',
        r'^PÁGINA\s*\d+\s*/\s*\d+$', r'^PAGINA\s*\d+\s*/\s*\d+$', r'AVALIE NOSSO ATENDIMENTO',
        r'DOCUMENTO DE EMISSÃO GRATUITA', r'DOCUMENTO DE EMISSAO GRATUITA', r'^SGO\s*-',
        r'^SISP\s*-', r'^PJC\s*-', r'^PJC/MT', r'^PJC-MT', r'^SESP/MT', r'^SESP-MT',
        r'^POL[IÍ]CIA\s*-', r'^POL[IÍ]CIA\s+MILITAR', r'^POL[IÍ]CIA\s+CIVIL',
        r'^PM\s*-', r'^BPM\s*-', r'^CBM\s*-',
        r'^Sistema Geral de Ocorrências', r'^Sistema Geral de Ocorrencias', r'^_+$',
        r'Documento assinado eletronicamente', r'Assinatura eletr[oô]nica', r'Documento assinado digitalmente',
        r'[Vv]alida[cç][aã]o pelo c[oó]digo', r'[Vv]alida[cç][aã]o pelo QR', r'[Cc]have de valida[cç][aã]o',
        r'^QR\s*Code', r'^QRCODE', r'hor[aáàâ]rio\s+oficial\s+de', r'validar-boletim',
        r'código identificador', r'codigo identificador', r'-\s*BAIRRO:.*-\s*MATO\s+GROSSO'
    ]
    
    cleaned_lines = []
    for line in texto.split('\n'):
        line_strip = line.strip()
        if not line_strip:
            cleaned_lines.append(line)
            continue
        line_clean = re.sub(r'^[^\w\d]+', '', line_strip)
        is_header_footer = False
        for pat in patterns:
            if re.search(pat, line_clean, re.IGNORECASE) or re.search(pat, line_strip, re.IGNORECASE):
                is_header_footer = True
                break
        if not is_header_footer:
            cleaned_lines.append(line)
    return '\n'.join(cleaned_lines)

def formatar_faixa_horario(hora_str: str) -> str:
    """Analise a hora recebida no padrão HH:MM e retorne a faixa de 3 horas correspondente."""
    if not hora_str:
        return ""
    time_match = re.search(r'(\d{1,2}):(\d{2})', hora_str)
    if not time_match:
        return ""
    try:
        hora = int(time_match.group(1))
        minuto = int(time_match.group(2))
        if 0 <= hora < 24 and 0 <= minuto < 60:
            faixas = [
                "00:00 AS 02:59",
                "03:00 AS 05:59",
                "06:00 AS 08:59",
                "09:00 AS 11:59",
                "12:00 AS 14:59",
                "15:00 AS 17:59",
                "18:00 AS 20:59",
                "21:00 AS 23:59"
            ]
            return faixas[hora // 3]
    except Exception:
        pass
    return ""

def formatar_periodo_dia(hora_str: str) -> str:
    """Analise a hora recebida no padrão HH:MM e retorne o nome do turno correspondente (MADRUGADA, MATUTINO, VESPERTINO, NOTURNO)."""
    if not hora_str:
        return ""
    time_match = re.search(r'(\d{1,2}):(\d{2})', hora_str)
    if not time_match:
        return ""
    try:
        hora = int(time_match.group(1))
        minuto = int(time_match.group(2))
        if 0 <= hora < 24 and 0 <= minuto < 60:
            if 0 <= hora <= 5:
                return "MADRUGADA"
            elif 6 <= hora <= 11:
                return "MATUTINO"
            elif 12 <= hora <= 17:
                return "VESPERTINO"
            elif 18 <= hora <= 23:
                return "NOTURNO"
    except Exception:
        pass
    return ""

def calcular_formula_data(formula: str, bo_dict: dict) -> str:
    """Resolve fórmulas como *DIA:DATA_DO_FATO* extraindo porções da data de origem, *FIXO:valor* ou *CONCAT:col1,col2,...*."""
    # Resolve fórmula de valor fixo do tipo *FIXO:valor*
    match_fixo = re.match(r'^\*FIXO:(.*)\*$', formula)
    if match_fixo:
        return match_fixo.group(1)

    # Resolve fórmula de concatenação do tipo *CONCAT:col1,col2,col3,...*
    formula_clean = formula.strip()
    match_concat = re.match(r'^\*?CONCAT:(.*)\*?$', formula_clean, re.IGNORECASE)
    if match_concat:
        # Divide por vírgula, limpa os espaços e normaliza as chaves das colunas
        colunas_origem = [normalizar_nome_chave(c.strip()) for c in match_concat.group(1).split(',')]
        valores = []
        for col in colunas_origem:
            val = bo_dict.get(col)
            if val and isinstance(val, str) and val.strip():
                valores.append(val.strip())
        # Retorna os valores concatenados separados por vírgula e espaço
        return ", ".join(valores)

    match = re.match(r'^\*(DIA_SEMANA|DIA|MES|ANO|HORA|FAIXA_HORA|PERIODO_HORA):(.+)\*$', formula)
    if not match:
        return None
        
    operacao = match.group(1)
    coluna_fonte = normalizar_nome_chave(match.group(2))
    
    val_fonte = bo_dict.get(coluna_fonte)
    if not val_fonte or not isinstance(val_fonte, str):
        return ""
        
    # Extração de hora (HH)
    if operacao == "HORA":
        time_match = re.search(r'(\d{1,2}):(\d{2})', val_fonte)
        if time_match:
            hora_str = time_match.group(1)
            if len(hora_str) == 1:
                hora_str = "0" + hora_str
            return hora_str
        return ""

    # Classificação em faixas de 3 horas ou períodos do dia
    if operacao == "FAIXA_HORA":
        return formatar_faixa_horario(val_fonte)
    elif operacao == "PERIODO_HORA":
        return formatar_periodo_dia(val_fonte)
        
    # Busca por formato de data brasileira (DD/MM/YYYY)
    date_match = re.search(r'(\d{2})/(\d{2})/(\d{4})', val_fonte)
    if not date_match:
        return ""
        
    dia_str, mes_str, ano_str = date_match.groups()
    try:
        dt = datetime(int(ano_str), int(mes_str), int(dia_str))
    except ValueError:
        return ""
        
    if operacao == "DIA_SEMANA":
        dias_semana_map = {
            0: "SEGUNDA-FEIRA",
            1: "TERÇA-FEIRA",
            2: "QUARTA-FEIRA",
            3: "QUINTA-FEIRA",
            4: "SEXTA-FEIRA",
            5: "SÁBADO",
            6: "DOMINGO"
        }
        return dias_semana_map[dt.weekday()]
    elif operacao == "DIA":
        return dia_str
    elif operacao == "MES":
        return mes_str
    elif operacao == "ANO":
        return ano_str
        
    return ""

def processar_texto_bo(texto: str, filename: str, layout_id: int, db_mappings: dict, lista_municipios: list, bairros_por_mun: dict) -> dict:
    """Processa o texto extraído de um BO (do PDF) dinamicamente por seções chave-valor do Layout."""
    texto = db.corrigir_mojibake(texto)
    
    # 1. Carrega as chaves de metadados especiais do layout (se configuradas)
    conn = db.obter_conexao()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.Nome_Item_Excel, i.Palavra_Busca, i.Exportar_Excel 
        FROM layout_itens i 
        JOIN layout_grupos g ON i.Grupo_ID = g.ID 
        WHERE g.Layout_ID = %s 
          AND i.Palavra_Busca IN ('*ARQUIVO*', '*BO_NUMERO*', '*DATA_DO_REGISTRO*', '*HORA_DO_REGISTRO*')
    """, (layout_id,))
    special_items = cursor.fetchall()
    conn.close()
    
    mapa_especial = {row[1]: (row[0], int(row[2]) == 1) for row in special_items}
    
    # Define mapeamentos e chaves de exibição dinâmicas
    cfg_arquivo = mapa_especial.get("*ARQUIVO*", ("ARQUIVO", True))
    cfg_bo = mapa_especial.get("*BO_NUMERO*", ("BO_NUMERO", True))
    cfg_data = mapa_especial.get("*DATA_DO_REGISTRO*", ("DATA_DO_REGISTRO", True))
    cfg_hora = mapa_especial.get("*HORA_DO_REGISTRO*", ("HORA_DO_REGISTRO", True))
    
    bo_dict = {}
    
    if cfg_arquivo[1]:
        bo_dict[normalizar_nome_chave(cfg_arquivo[0])] = filename
    if cfg_bo[1]:
        bo_dict[normalizar_nome_chave(cfg_bo[0])] = extrair_bo_numero(texto)
        
    if cfg_data[1] or cfg_hora[1]:
        data_reg, hora_reg = extrair_datas_registro(texto)
        if cfg_data[1]:
            bo_dict[normalizar_nome_chave(cfg_data[0])] = data_reg
        if cfg_hora[1]:
            bo_dict[normalizar_nome_chave(cfg_hora[0])] = hora_reg
            
    grupos_df = db.listar_grupos(layout_id)
    if grupos_df.empty:
        return bo_dict
        
    texto_limpo = remover_cabecalhos_rodapes(texto, layout_id)
    secoes = segmentar_texto(texto_limpo, layout_id)
    
    for _, row in grupos_df.iterrows():
        key = normalizar_nome_chave(row["Nome_Grupo"])
        texto_secao = secoes.get(key, "")
        
        if row["Tem_Itens"]:
            pares_extraidos = extrair_pares_chave_valor(texto_secao, layout_id, row["ID"])
            bo_dict.update(pares_extraidos)
            
            # Fallback heurístico para municípios e bairros se a seção for "LOCAL"
            if "LOCAL" in key:
                itens_df = db.listar_itens(row["ID"])
                bairro_key = None
                municipio_key = None
                bairro_export = True
                municipio_export = True
                if not itens_df.empty:
                    for _, item in itens_df.iterrows():
                        if "BAIRRO" in item["Palavra_Busca"].upper() or "BAIRRO" in item["Nome_Item_Excel"].upper():
                            bairro_key = normalizar_nome_chave(item["Nome_Item_Excel"])
                            bairro_export = int(item.get("Exportar_Excel", 1)) == 1
                        if "MUNIC" in item["Palavra_Busca"].upper() or "MUNIC" in item["Nome_Item_Excel"].upper():
                            municipio_key = normalizar_nome_chave(item["Nome_Item_Excel"])
                            municipio_export = int(item.get("Exportar_Excel", 1)) == 1
                            
                if bairro_key and municipio_key:
                    precisa_bairro = bairro_export and (bairro_key not in bo_dict)
                    precisa_municipio = municipio_export and (municipio_key not in bo_dict)
                    
                    if precisa_bairro or precisa_municipio:
                        mun_fall, bairro_fall = aplicar_fallback_municipio_bairro(texto, lista_municipios, bairros_por_mun)
                        if precisa_bairro and bairro_fall:
                            bo_dict[bairro_key] = bairro_fall.upper()
                        if precisa_municipio and mun_fall:
                            bo_dict[municipio_key] = db.padronizar_municipio(mun_fall)
        else:
            if int(row.get("Exportar_Excel", 1)) == 1:
                bo_dict[key] = normalizar_espacos(texto_secao)
            
    # Lógica de fórmulas dinâmicas pós-extração
    try:
        conn_frm = db.obter_conexao()
        cursor_frm = conn_frm.cursor()
        cursor_frm.execute("""
            SELECT i.Nome_Item_Excel, i.Palavra_Busca, i.Exportar_Excel 
            FROM layout_itens i 
            JOIN layout_grupos g ON i.Grupo_ID = g.ID 
            WHERE g.Layout_ID = %s 
              AND i.Palavra_Busca LIKE '*%%:%%*'
        """, (layout_id,))
        formula_items = cursor_frm.fetchall()
        conn_frm.close()
        
        for nome_col, formula, exportar_excel in formula_items:
            if int(exportar_excel) == 1:
                val_calc = calcular_formula_data(formula, bo_dict)
                if val_calc is not None:
                    bo_dict[normalizar_nome_chave(nome_col)] = val_calc
    except Exception as formula_err:
        pass
            
    return bo_dict

def processar_pdf(pdf_path: str, layout_id: int, db_mappings: dict, lista_municipios: list, bairros_por_mun: dict) -> dict:
    """Extrai dados de um único PDF de BO."""
    texto = extrair_texto_pdf(pdf_path, layout_id)
    if not texto:
        return {
            "ARQUIVO": os.path.basename(pdf_path),
            "BO_NUMERO": "Erro na leitura",
            "NARRATIVA": "Erro ao extrair conteúdo do PDF.",
            "PROVIDENCIAS": "NI"
        }
    return processar_texto_bo(texto, os.path.basename(pdf_path), layout_id, db_mappings, lista_municipios, bairros_por_mun)

def ordenar_dataframe(df: pd.DataFrame, layout_id: int) -> pd.DataFrame:
    """Ordena as colunas do DataFrame para um formato padronizado conforme o Layout."""
    # Busca todos os itens ativos (normais e fórmulas/especiais)
    conn = db.obter_conexao()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT i.Nome_Item_Excel, i.Ordem_Excel, i.Palavra_Busca, i.ID
        FROM layout_itens i 
        JOIN layout_grupos g ON i.Grupo_ID = g.ID 
        WHERE g.Layout_ID = %s AND i.Exportar_Excel = 1
    """, (layout_id,))
    itens_db = cursor.fetchall()
    
    # Busca todos os grupos ativos sem sub-itens (colunas diretas)
    cursor.execute("""
        SELECT Nome_Grupo, Ordem_Excel, '*TEXTO_BRUTO*', ID
        FROM layout_grupos
        WHERE Layout_ID = %s AND Tem_Itens = 0 AND Exportar_Excel = 1
    """, (layout_id,))
    grupos_db = cursor.fetchall()
    
    # Busca se existem itens de metadados especiais mapeados no banco (ativos ou não) para evitar fallback indevido
    cursor.execute("""
        SELECT i.Palavra_Busca 
        FROM layout_itens i 
        JOIN layout_grupos g ON i.Grupo_ID = g.ID 
        WHERE g.Layout_ID = %s 
          AND i.Palavra_Busca IN ('*ARQUIVO*', '*BO_NUMERO*', '*DATA_DO_REGISTRO*', '*HORA_DO_REGISTRO*')
    """, (layout_id,))
    especiais_mapeados = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    # Junta ambos em uma única lista
    colunas_candidatas = []
    for nome, ordem_e, palavra, iid in itens_db:
        colunas_candidatas.append({
            "nome": normalizar_nome_chave(nome),
            "nome_original": nome,
            "ordem_excel": ordem_e,
            "palavra": palavra,
            "id": iid
        })
    for nome, ordem_e, palavra, iid in grupos_db:
        colunas_candidatas.append({
            "nome": normalizar_nome_chave(nome),
            "nome_original": nome,
            "ordem_excel": ordem_e,
            "palavra": palavra,
            "id": iid
        })
        
    # Ordena pelo Ordem_Excel (crescente) e pelo ID (estável)
    colunas_candidatas.sort(key=lambda x: (x["ordem_excel"], x["id"]))
    
    mapeamento_exibicao = {}
    for c in colunas_candidatas:
        mapeamento_exibicao[c["nome"]] = c["nome_original"]
    
    ordem_pref = []
    # Adiciona metadados estáticos antigos apenas como fallback se não estiverem mapeados de forma alguma no banco (ativos ou inativos)
    if "*ARQUIVO*" not in especiais_mapeados:
        ordem_pref.append("ARQUIVO")
        mapeamento_exibicao["ARQUIVO"] = "ARQUIVO"
    if "*BO_NUMERO*" not in especiais_mapeados:
        ordem_pref.append("BO_NUMERO")
        mapeamento_exibicao["BO_NUMERO"] = "BO_NUMERO"
    if "*DATA_DO_REGISTRO*" not in especiais_mapeados:
        ordem_pref.append("DATA_DO_REGISTRO")
        mapeamento_exibicao["DATA_DO_REGISTRO"] = "DATA_DO_REGISTRO"
    if "*HORA_DO_REGISTRO*" not in especiais_mapeados:
        ordem_pref.append("HORA_DO_REGISTRO")
        mapeamento_exibicao["HORA_DO_REGISTRO"] = "HORA_DO_REGISTRO"
        
    for c in colunas_candidatas:
        nome_norm = c["nome"]
        if nome_norm not in ordem_pref:
            ordem_pref.append(nome_norm)
            
    # Cria uma cópia do DataFrame para evitar SettingWithCopyWarning
    df = df.copy()
    
    # Cria no DataFrame as colunas parametrizadas para exportação que estão ausentes (sem informação)
    for col in ordem_pref:
        if col not in df.columns:
            df[col] = ""
            
    colunas_existentes = [c for c in ordem_pref if c in df.columns]
    colunas_extras = [c for c in df.columns if c not in colunas_existentes]
    df_ordenado = df[colunas_existentes + colunas_extras]
    return df_ordenado.rename(columns=mapeamento_exibicao)

def processar_pasta_bo(pasta_origem: str, arquivo_excel: str):
    """Varre uma pasta contendo PDFs, processa cada BO e salva em planilha Excel."""
    if not os.path.exists(pasta_origem):
        print(f"Erro: A pasta '{pasta_origem}' não existe.")
        return
        
    db.inicializar_banco()
    
    db_mappings = {
        "mapa_upms": db.obter_mapeamento_upms(),
        "mapa_nomes_mun": db.obter_mapeamento_nomes_municipios(),
        "mapa_nomes_bai": db.obter_mapeamento_nomes_bairros(),
        "mapa_alternativos_bai": db.obter_mapeamento_alternativo_bairros(),
        "mapa_mun_todos": db.obter_municipios_com_bairro_todos_unico()
    }
    
    lista_municipios, bairros_por_mun = carregar_dados_banco()
    arquivos = [os.path.join(pasta_origem, f) for f in os.listdir(pasta_origem) if f.lower().endswith('.pdf')]
    if not arquivos: return
    
    layout_id = 1
    
    resultados = []
    for arq in arquivos:
        res = processar_pdf(arq, layout_id, db_mappings, lista_municipios, bairros_por_mun)
        resultados.append(res)
        
    df = pd.DataFrame(resultados)
    df = ordenar_dataframe(df, layout_id)
    
    with pd.ExcelWriter(arquivo_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="BOs_Extraidos")

    processar_pasta_bo(args.pasta, args.saida)
