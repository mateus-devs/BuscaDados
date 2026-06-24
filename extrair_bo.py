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

def extrair_texto_pdf(pdf_source) -> str:
    """Extrai todo o texto contido em um arquivo PDF (caminho ou objeto) utilizando pypdf."""
    texto = ""
    try:
        reader = pypdf.PdfReader(pdf_source)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                texto += page_text + "\n"
    except Exception as e:
        source_name = getattr(pdf_source, 'name', str(pdf_source))
        print(f"Erro ao ler o PDF '{source_name}': {str(e)}")
    return texto

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

def segmentar_texto(texto: str) -> dict:
    """Segmenta o texto completo do BO em grupos/seções para evitar colisões de campos."""
    markers = [
        ("COMUNICANTE", ["COMUNICANTE"]),
        ("NATUREZA", ["NATUREZA DA OCORRÊNCIA", "NATUREZA DA OCORRENCIA", "NATUREZA"]),
        ("LOCAL", ["LOCAL DO FATO", "LOCAL"]),
        ("VITIMA", ["VÍTIMA BRASILEIRA", "VITIMA BRASILEIRA", "VÍTIMA", "VITIMA"]),
        ("SUSPEITO", ["SUSPEITO BRASILEIRO", "SUSPEITO BRASILEIRA", "SUSPEITO", "SUSPEITOS"]),
        ("ENVOLVIDO", ["OUTROS ENVOLVIDOS", "ENVOLVIDO", "ENVOLVIDOS"]),
        ("TESTEMUNHA", ["TESTEMUNHA", "TESTEMUNHAS"]),
        ("VEICULO", ["MATERIAL DO VEÍCULO", "MATERIAL DO VEICULO", "MATERIAL VEÍCULO", "MATERIAL VEICULO", "MATERIAIS DIVERSOS", "MATERIAL DIVERSO", "MATERIAIS", "MATERIAL", "VEÍCULO", "VEICULO"]),
        ("NARRATIVA", ["NARRATIVA", "HISTÓRICO DA OCORRÊNCIA", "HISTORICO DA OCORRENCIA", "HISTÓRICO", "HISTORICO", "RELATO DO FATO"]),
        ("PROVIDENCIAS", ["PROVIDÊNCIAS", "PROVIDENCIAS", "PROVIDENCIA", "PROVIDÊNCIA"])
    ]
    
    secoes_keys = {
        "COMUNICANTE": ["Nome Completo", "Nome", "CPF", "RG", "Sexo", "Telefone", "Mãe", "Mae", "Pai"],
        "NATUREZA": ["Natureza", "Título", "Titulo", "Legislação", "Legislacao", "Forma"],
        "LOCAL": ["Data", "Hora", "Tipo Local", "Logradouro", "Bairro", "Município", "Municipio", "UF"],
        "VITIMA": ["Nome Completo", "Nome", "CPF", "RG", "Sexo", "Idade", "Mãe", "Mae", "Pai", "Natureza"],
        "SUSPEITO": ["Nome Completo", "Nome", "CPF", "RG", "Sexo", "Idade", "Modus", "Natureza"],
        "ENVOLVIDO": ["Nome Completo", "Nome", "CPF", "RG", "Sexo", "Idade"],
        "TESTEMUNHA": ["Nome Completo", "Nome", "CPF", "RG", "Sexo", "Idade"],
        "VEICULO": ["Placa", "Marca", "Modelo", "Cor", "Chassi", "Material", "Quantidade", "Unidade", "Grupo", "Situação", "Situacao"],
        "NARRATIVA": [],
        "PROVIDENCIAS": []
    }
    
    found_sections = []
    for key, aliases in markers:
        keys_esperadas = secoes_keys.get(key, [])
        for alias in aliases:
            # Padrão mais tolerante que permite decorações não-alfanuméricas (como asteriscos, hífens)
            # no início e fim da linha da seção
            pattern = rf'(?:^|\n)[^\w\d]*({re.escape(alias)})[^\w\d]*(?=\n|$)'
            matches = list(re.finditer(pattern, texto, re.IGNORECASE))
            if not matches:
                continue
                
            # Disambiguação de múltiplas correspondências
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
                        
                if best_match is None or max_keys_found == 0:
                    best_match = matches[-1]
            
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

def extrair_pares_chave_valor(secao_text: str) -> dict:
    """Extrai todos os pares chave-valor de uma seção, tratando múltiplos pares na mesma linha."""
    pares = {}
    if not secao_text:
        return pares
        
    # Lista predefinida de chaves estáticas encontradas nos templates de BO
    known_keys = [
        "Data", "Hora", "Tipo Local", "Descrição", "Descricao", "Logradouro", "Km", 
        "Número", "Numero", "Complemento", "Bairro", "Município", "Municipio", "UF", 
        "Ponto Ref", "Ponto de Referência", "Ponto Referência", "Ponto Referencia", 
        "Longitude", "Latitude", "Nome Completo", "Nome", "CPF", "RG", "Sexo", 
        "Data Nascimento", "Telefone", "Mãe", "Mae", "Pai", "Placa", "Marca/Modelo", 
        "Marca", "Modelo", "Cor", "Chassi", "Ano Fabricação", "Ano Modelo", "Ano",
        # Novos campos da segunda imagem:
        "Nome Social", "Nome da Mãe", "Nome da Mae", "Nome do Pai", "E-mail", "Email",
        "Nacionali", "Nacionalidade", "Naturalidade", "Nascimento", "Idade", 
        "Est. Civil", "Estado Civil", "Escolaridade", "Or. Sexual", "Orientação Sexual", 
        "Orientacao Sexual", "Data Emissão", "Data Emissao", "Órgão Ex", "Orgao Ex", 
        "Órgão Expedidor", "Orgao Expedidor", "Órgão Emissor", "Orgao Emissor",
        "Órgão Exp", "Orgao Exp", "Org. Exp", "Org. Exp.", "Orgão Ex", "Orgão Exp",
        "Orgão Expedidor", "Orgão Emissor", "Profissão", "Profissao",
        # Campos de Natureza da Ocorrência da terceira/quarta imagem:
        "Título", "Titulo", "Legislação", "Legislacao", "Forma", 
        "Meios Empr", "Meios Empr.", "Meios Empregados", "Motivação", "Motivacao",
        # Campos de Vítima da terceira/quarta imagem:
        "Tipo Defic", "Tipo Defic.", "Tipo de Deficiência", "Tipo de Deficiencia",
        "Característ", "Caracterist", "Características", "Caracteristicas", "Característica", "Caracteristica",
        "Natureza(s) vinculada(s) a VÍTIMA", "Natureza(s) vinculada(s) a VITIMA", "Naturezas vinculadas",
        # Campos de Material Veículo da terceira/quarta imagem:
        "Material", "Renavam", "País Licenc", "Pais Licenc", "País Licenc.", "Pais Licenc.",
        "País de Licenciamento", "Pais de Licenciamento",
        "Mun/UF Empl", "Mun/UF Empl.", "Mun/UF Emplec", "Mun/UF Emplec.",
        "Município/UF de Emplacamento", "Municipio/UF de Emplacamento",
        "Fabricação", "Fabricacao", "Licenciamento", "Combustível", "Combustivel",
        "Espécie", "Especie", "Categoria", "Tração", "Tracao", "Tipo", "Situação", "Situacao",
        "Material de",
        # Campos do Suspeito:
        "Modus Operan", "Modus Operandi", "Natureza(s) vinculada(s) ao suspeito", "Natureza(s) vinculada(s) ao SUSPEITO", "Naturezas vinculadas ao suspeito",
        # Campos de Materiais Diversos adicionais:
        "Quantidade", "Unidade", "Grupo"
    ]
    
    # Ordena pelo tamanho decrescente para priorizar casamentos mais longos (ex: Nome Completo antes de Nome)
    sorted_keys = sorted(known_keys, key=len, reverse=True)
    key_pattern = r'\b(' + '|'.join([re.escape(k) for k in sorted_keys]) + r')\.*:'
        
    lines = secao_text.split('\n')
    last_empty_key = None
    last_active_key = None
    
    # Marcadores de seções para evitar que sejam anexados a campos anteriores
    secoes_nomes = {
        "COMUNICANTE", "NATUREZA DA OCORRÊNCIA", "NATUREZA DA OCORRENCIA", "NATUREZA", 
        "LOCAL DO FATO", "LOCAL", "VÍTIMA", "VITIMA", "SUSPEITO", "SUSPEITOS", 
        "OUTROS ENVOLVIDOS", "ENVOLVIDO", "ENVOLVIDOS", "TESTEMUNHA", "TESTEMUNHAS",
        "MATERIAL DO VEÍCULO", "MATERIAL DO VEICULO", "MATERIAL VEÍCULO", "MATERIAL VEICULO", 
        "MATERIAIS DIVERSOS", "MATERIAL DIVERSO", "MATERIAIS", "MATERIAL", "VEÍCULO", "VEICULO", 
        "NARRATIVA", "HISTÓRICO DA OCORRÊNCIA", "HISTORICO DA OCORRENCIA", "HISTÓRICO", 
        "HISTORICO", "RELATO DO FATO", "PROVIDÊNCIAS", "PROVIDENCIAS", "PROVIDENCIA", "PROVIDÊNCIA"
    }
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Pula linhas de cabeçalho ou separadores para evitar associá-las como valor da linha anterior
        if (line.startswith('**') and line.endswith('**')) or re.match(r'^[\-\s\*\+=]+$', line):
            continue
            
        # Pula se a linha for um marcador de seção
        if line.upper() in secoes_nomes:
            last_empty_key = None
            last_active_key = None
            continue
            
        # Encontra as correspondências das chaves conhecidas na linha
        matches = list(re.finditer(key_pattern, line, re.IGNORECASE))
        
        if not matches:
            # Se não houver chaves na linha mas tivermos uma chave pendente sem valor,
            # associamos essa linha inteira como valor dela
            if last_empty_key:
                pares[last_empty_key] = line.strip()
                last_active_key = last_empty_key
                last_empty_key = None
            elif last_active_key:
                # Se houver uma chave ativa anterior, concatena essa linha como continuação dela
                v_atual = pares.get(last_active_key, "")
                if v_atual:
                    pares[last_active_key] = v_atual + " " + line.strip()
                else:
                    pares[last_active_key] = line.strip()
            continue
            
        # Se encontrou novas chaves, a chave pendente é descartada
        last_empty_key = None
        
        # Extrai o valor de cada chave baseado nos offsets das correspondências na linha
        for idx, match in enumerate(matches):
            key_name = match.group(1).strip()
            start_val_idx = match.end(0)
            
            if idx + 1 < len(matches):
                end_val_idx = matches[idx + 1].start(0)
                val = line[start_val_idx:end_val_idx]
            else:
                val = line[start_val_idx:]
                
            key_clean = key_name.strip('. ')
            if key_clean:
                # Resolve duplicidades de UF na mesma seção com base no contexto da linha
                if key_clean.upper() == "UF":
                    line_upper = line.upper()
                    if "NATURALIDADE" in line_upper:
                        key_clean = "UF_NATURALIDADE"
                    elif "RG" in line_upper or "EMISSAO" in line_upper or "EX" in line_upper:
                        key_clean = "UF_RG"
                
                val_stripped = val.strip()
                pares[key_clean] = val_stripped
                last_active_key = key_clean
                
                # Se for o último match da linha e o valor estiver vazio, marca como pendente para a próxima linha
                if idx == len(matches) - 1 and not val_stripped:
                    last_empty_key = key_clean
                    last_active_key = None
                    
    return pares

def processar_secao_chave_valor(secao_text: str, prefixo_grupo: str) -> dict:
    """Extrai pares chave-valor de uma seção, normalizando chaves e aplicando padronizações do sistema."""
    pares_brutos = extrair_pares_chave_valor(secao_text)
    pares_processados = {}
    for k, v in pares_brutos.items():
        chave_normalizada = normalizar_nome_chave(k)
        if chave_normalizada:
            nome_coluna = f"{prefixo_grupo}{chave_normalizada}"
            valor_limpo = limpar_campo_extraido(v)
            
            # Aplica padronização específica de Bairro e Município nas chaves detectadas
            if "MUNICIPIO" in chave_normalizada:
                valor_limpo = db.padronizar_municipio(valor_limpo)
            elif "BAIRRO" in chave_normalizada:
                valor_limpo = db.corrigir_mojibake(valor_limpo).strip().upper()
                
            pares_processados[nome_coluna] = valor_limpo
    return pares_processados

def carregar_dados_banco():
    """Carrega dados do banco SQLite para aplicação do algoritmo de fallback."""
    df_m = db.listar_dados("municipios")
    lista_municipios = df_m["Municipio"].tolist() if not df_m.empty else []
    
    df_b = db.listar_dados("bairros")
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

def remover_cabecalhos_rodapes(texto: str) -> str:
    """Remove cabeçalhos e rodapés repetidos do texto das páginas do PDF para permitir continuidade."""
    patterns = [
        r'^ESTADO DE MATO GROSSO',
        r'^SECRETARIA DE ESTADO',
        r'^POLÍCIA JUD',
        r'^POLICIA JUD',
        r'^DELEGAC',
        r'^BOLETIM DE OCORRÊNCIA',
        r'^BOLETIM DE OCORRENCIA',
        r'^ELABORADO POR',
        r'^EDITADO POR',
        r'^DATA/HORA DA COMUNICA',  # Sem acentos para ser 100% robusto a variações
        r'^DATA/HORA DA COMUNICACAO',
        r'^IMPRESSO EM',
        r'^IMPRESSO POR',
        r'^Telefone:.*E-Mail',      # Linha de contato da delegacia
        r'delvirtual@pjc\.mt\.gov\.br',  # Email da delegacia virtual em qualquer parte da linha
        # Paginações ancoradas no início e fim para não casar no meio de frases narradas
        r'^Pág\s*[:\.]?\s*\d+\s*de\s*\d+$',
        r'^Página\s*\d+\s*de\s*\d+$',
        r'^PÁGINA\s*\d+\s*/\s*\d+$',
        r'^PAGINA\s*\d+\s*/\s*\d+$',
        r'AVALIE NOSSO ATENDIMENTO',  # Únicos do rodapé
        r'DOCUMENTO DE EMISSÃO GRATUITA',
        r'DOCUMENTO DE EMISSAO GRATUITA',
        r'^SGO\s*-',
        r'^SISP\s*-',
        r'^PJC\s*-',
        r'^PJC/MT',
        r'^PJC-MT',
        r'^SESP/MT',
        r'^SESP-MT',
        r'^Sistema Geral de Ocorrências',
        r'^Sistema Geral de Ocorrencias',
        r'^_+$',
        # Rodapé de assinatura eletrônica e QR Code
        r'Documento assinado eletronicamente',
        r'Assinatura eletr[oô]nica',
        r'Documento assinado digitalmente',
        r'[Vv]alida[cç][aã]o pelo c[oó]digo',
        r'[Vv]alida[cç][aã]o pelo QR',
        r'[Cc]have de valida[cç][aã]o',
        r'^QR\s*Code',
        r'^QRCODE',
        # Novos padrões para limpar completamente o rodapé dinâmico da delegacia e autenticação
        r'hor[aáàâ]rio\s+oficial\s+de',
        r'validar-boletim',
        r'código identificador',
        r'codigo identificador',
        r'-\s*BAIRRO:.*-\s*MATO\s+GROSSO'
    ]
    
    # Marcadores de seção para remover repetições de cabeçalhos de página
    secoes_nomes = {
        "COMUNICANTE", "NATUREZA DA OCORRÊNCIA", "NATUREZA DA OCORRENCIA", "NATUREZA", 
        "LOCAL DO FATO", "LOCAL", "VÍTIMA", "VITIMA", "SUSPEITO", "SUSPEITOS", 
        "OUTROS ENVOLVIDOS", "ENVOLVIDO", "ENVOLVIDOS", "TESTEMUNHA", "TESTEMUNHAS",
        "MATERIAL DO VEÍCULO", "MATERIAL DO VEICULO", "MATERIAL VEÍCULO", "MATERIAL VEICULO", 
        "MATERIAIS DIVERSOS", "MATERIAL DIVERSO", "MATERIAIS", "MATERIAL", "VEÍCULO", "VEICULO", 
        "NARRATIVA", "HISTÓRICO DA OCORRÊNCIA", "HISTORICO DA OCORRENCIA", "HISTÓRICO", 
        "HISTORICO", "RELATO DO FATO", "PROVIDÊNCIAS", "PROVIDENCIAS", "PROVIDENCIA", "PROVIDÊNCIA"
    }
    cleaned_lines = []
    for line in texto.split('\n'):
        line_strip = line.strip()
        if not line_strip:
            cleaned_lines.append(line)
            continue
            
        # Remove símbolos e pontuações do início da linha para permitir casar com a âncora ^
        line_clean = re.sub(r'^[^\w\d]+', '', line_strip)
        
        is_header_footer = False
        for pat in patterns:
            if re.search(pat, line_clean, re.IGNORECASE) or re.search(pat, line_strip, re.IGNORECASE):
                is_header_footer = True
                break
        if not is_header_footer:
            cleaned_lines.append(line)
            
    return '\n'.join(cleaned_lines)

def processar_texto_bo(texto: str, filename: str, db_mappings: dict, lista_municipios: list, bairros_por_mun: dict) -> dict:
    """Processa o texto extraído de um BO (do PDF) dinamicamente por seções chave-valor."""
    # Corrige Mojibake do texto extraído para garantir correspondência exata
    texto = db.corrigir_mojibake(texto)
    
    # 2. Dicionário inicial com metadados
    bo_dict = {}
    bo_dict["ARQUIVO"] = filename
    bo_dict["BO_NUMERO"] = extrair_bo_numero(texto)
    
    # Extrai data e hora de registro do cabeçalho original antes de limpar
    data_reg, hora_reg = extrair_datas_registro(texto)
    bo_dict["DATA_DO_REGISTRO"] = data_reg
    bo_dict["HORA_DO_REGISTRO"] = hora_reg
    
    # Limpa cabeçalhos e rodapés repetidos para permitir continuidade
    texto_limpo = remover_cabecalhos_rodapes(texto)
    
    # 1. Segmenta o BO em seções com texto limpo
    secoes = segmentar_texto(texto_limpo)
    
    # 3. Processa cada seção dinamicamente aplicando prefixos
    bo_dict.update(processar_secao_chave_valor(secoes.get("COMUNICANTE", ""), "COMUNICANTE_"))
    bo_dict.update(processar_secao_chave_valor(secoes.get("NATUREZA", ""), "NATUREZA_DA_OCORRENCIA_"))
    
    # Processa seção local com fallback heurístico para Bairro e Município
    local_pares = processar_secao_chave_valor(secoes.get("LOCAL", ""), "LOCAL_DO_FATO_")
    bairro_key = "LOCAL_DO_FATO_BAIRRO"
    municipio_key = "LOCAL_DO_FATO_MUNICIPIO"
    if bairro_key not in local_pares or municipio_key not in local_pares:
        mun_fall, bairro_fall = aplicar_fallback_municipio_bairro(texto, lista_municipios, bairros_por_mun)
        if bairro_key not in local_pares and bairro_fall:
            local_pares[bairro_key] = bairro_fall.upper()
        if municipio_key not in local_pares and mun_fall:
            local_pares[municipio_key] = db.padronizar_municipio(mun_fall)
    bo_dict.update(local_pares)
    
    bo_dict.update(processar_secao_chave_valor(secoes.get("VITIMA", ""), "VITIMA_"))
    bo_dict.update(processar_secao_chave_valor(secoes.get("SUSPEITO", ""), "SUSPEITO_"))
    bo_dict.update(processar_secao_chave_valor(secoes.get("ENVOLVIDO", ""), "ENVOLVIDO_"))
    bo_dict.update(processar_secao_chave_valor(secoes.get("TESTEMUNHA", ""), "TESTEMUNHA_"))
    bo_dict.update(processar_secao_chave_valor(secoes.get("VEICULO", ""), "MATERIAL_DO_VEICULO_"))
    
    # 4. Adiciona blocos de texto livre normalizando quebras de linha e espaços extras
    bo_dict["NARRATIVA"] = normalizar_espacos(secoes.get("NARRATIVA", "NI"))
    bo_dict["PROVIDENCIAS"] = normalizar_espacos(secoes.get("PROVIDENCIAS", "NI"))
    
    return bo_dict

def processar_pdf(pdf_path: str, db_mappings: dict, lista_municipios: list, bairros_por_mun: dict) -> dict:
    """Extrai dados de um único PDF de BO."""
    texto = extrair_texto_pdf(pdf_path)
    if not texto:
        return {
            "ARQUIVO": os.path.basename(pdf_path),
            "BO_NUMERO": "Erro na leitura",
            "NARRATIVA": "Erro ao extrair conteúdo do PDF.",
            "PROVIDENCIAS": "NI"
        }
    return processar_texto_bo(texto, os.path.basename(pdf_path), db_mappings, lista_municipios, bairros_por_mun)

def ordenar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Ordena as colunas do DataFrame para um formato padronizado e profissional."""
    ordem_pref = [
        "ARQUIVO",
        "BO_NUMERO",
        "DATA_DO_REGISTRO",
        "HORA_DO_REGISTRO",
        
        # COMUNICANTE
        "COMUNICANTE_NOME",
        "COMUNICANTE_NOME_COMPLETO",
        "COMUNICANTE_NOME_SOCIAL",
        "COMUNICANTE_CPF",
        "COMUNICANTE_RG",
        "COMUNICANTE_UF_RG",
        "COMUNICANTE_ORGAO_EXPEDIDOR",
        "COMUNICANTE_ORGAO_EX",
        "COMUNICANTE_ORGAO_EMISSOR",
        "COMUNICANTE_ORGAO_EXP",
        "COMUNICANTE_ORG_EXP",
        "COMUNICANTE_DATA_EMISSAO",
        "COMUNICANTE_NASCIMENTO",
        "COMUNICANTE_DATA_NASCIMENTO",
        "COMUNICANTE_IDADE",
        "COMUNICANTE_ESTADO_CIVIL",
        "COMUNICANTE_EST_CIVIL",
        "COMUNICANTE_NACIONALIDADE",
        "COMUNICANTE_NACIONALI",
        "COMUNICANTE_NATURALIDADE",
        "COMUNICANTE_UF_NATURALIDADE",
        "COMUNICANTE_ESCOLARIDADE",
        "COMUNICANTE_PROFISSAO",
        "COMUNICANTE_SEXO",
        "COMUNICANTE_ORIENTACAO_SEXUAL",
        "COMUNICANTE_OR_SEXUAL",
        "COMUNICANTE_NOME_DA_MAE",
        "COMUNICANTE_MAE",
        "COMUNICANTE_NOME_DO_PAI",
        "COMUNICANTE_PAI",
        "COMUNICANTE_EMAIL",
        "COMUNICANTE_E_MAIL",
        "COMUNICANTE_TELEFONE",
        "COMUNICANTE_LOGRADOURO",
        "COMUNICANTE_NUMERO",
        "COMUNICANTE_COMPLEMENTO",
        "COMUNICANTE_BAIRRO",
        "COMUNICANTE_MUNICIPIO",
        "COMUNICANTE_UF",
        
        # NATUREZA DA OCORRÊNCIA
        "NATUREZA_DA_OCORRENCIA_NATUREZA",
        "NATUREZA_DA_OCORRENCIA_DELITO",
        "NATUREZA_DA_OCORRENCIA_TITULO",
        "NATUREZA_DA_OCORRENCIA_LEGISLACAO",
        "NATUREZA_DA_OCORRENCIA_FORMA",
        "NATUREZA_DA_OCORRENCIA_MEIOS_EMPR",
        "NATUREZA_DA_OCORRENCIA_MEIOS_EMPREGADOS",
        "NATUREZA_DA_OCORRENCIA_MOTIVACAO",
        
        # LOCAL DO FATO
        "LOCAL_DO_FATO_DATA",
        "LOCAL_DO_FATO_HORA",
        "LOCAL_DO_FATO_TIPO_LOCAL",
        "LOCAL_DO_FATO_DESCRICAO",
        "LOCAL_DO_FATO_LOGRADOURO",
        "LOCAL_DO_FATO_KM",
        "LOCAL_DO_FATO_NUMERO",
        "LOCAL_DO_FATO_COMPLEMENTO",
        "LOCAL_DO_FATO_BAIRRO",
        "LOCAL_DO_FATO_MUNICIPIO",
        "LOCAL_DO_FATO_UF",
        "LOCAL_DO_FATO_PONTO_REF",
        "LOCAL_DO_FATO_LONGITUDE",
        "LOCAL_DO_FATO_LATITUDE",
        
        # VÍTIMA
        "VITIMA_NOME",
        "VITIMA_NOME_COMPLETO",
        "VITIMA_NOME_SOCIAL",
        "VITIMA_CPF",
        "VITIMA_RG",
        "VITIMA_UF_RG",
        "VITIMA_ORGAO_EXPEDIDOR",
        "VITIMA_ORGAO_EX",
        "VITIMA_ORGAO_EMISSOR",
        "VITIMA_ORGAO_EXP",
        "VITIMA_ORG_EXP",
        "VITIMA_DATA_EMISSAO",
        "VITIMA_NASCIMENTO",
        "VITIMA_DATA_NASCIMENTO",
        "VITIMA_IDADE",
        "VITIMA_ESTADO_CIVIL",
        "VITIMA_EST_CIVIL",
        "VITIMA_NACIONALIDADE",
        "VITIMA_NACIONALI",
        "VITIMA_NATURALIDADE",
        "VITIMA_UF_NATURALIDADE",
        "VITIMA_ESCOLARIDADE",
        "VITIMA_PROFISSAO",
        "VITIMA_SEXO",
        "VITIMA_ORIENTACAO_SEXUAL",
        "VITIMA_OR_SEXUAL",
        "VITIMA_TIPO_DEFIC",
        "VITIMA_TIPO_DE_DEFICIENCIA",
        "VITIMA_CARACTERIST",
        "VITIMA_CARACTERISTICAS",
        "VITIMA_NOME_DA_MAE",
        "VITIMA_MAE",
        "VITIMA_NOME_DO_PAI",
        "VITIMA_PAI",
        "VITIMA_EMAIL",
        "VITIMA_E_MAIL",
        "VITIMA_TELEFONE",
        "VITIMA_LOGRADOURO",
        "VITIMA_KM",
        "VITIMA_NUMERO",
        "VITIMA_COMPLEMENTO",
        "VITIMA_BAIRRO",
        "VITIMA_MUNICIPIO",
        "VITIMA_UF",
        "VITIMA_PONTO_REF",
        "VITIMA_NATUREZA_S_VINCULADA_S_A_VITIMA",
        "VITIMA_NATUREZAS_VINCULADAS",
        
        # SUSPEITO
        "SUSPEITO_NOME",
        "SUSPEITO_NOME_COMPLETO",
        "SUSPEITO_NOME_SOCIAL",
        "SUSPEITO_CPF",
        "SUSPEITO_RG",
        "SUSPEITO_UF_RG",
        "SUSPEITO_ORGAO_EXPEDIDOR",
        "SUSPEITO_ORGAO_EX",
        "SUSPEITO_ORGAO_EMISSOR",
        "SUSPEITO_ORGAO_EXP",
        "SUSPEITO_ORG_EXP",
        "SUSPEITO_DATA_EMISSAO",
        "SUSPEITO_NASCIMENTO",
        "SUSPEITO_DATA_NASCIMENTO",
        "SUSPEITO_IDADE",
        "SUSPEITO_ESTADO_CIVIL",
        "SUSPEITO_EST_CIVIL",
        "SUSPEITO_NACIONALIDADE",
        "SUSPEITO_NACIONALI",
        "SUSPEITO_NATURALIDADE",
        "SUSPEITO_UF_NATURALIDADE",
        "SUSPEITO_ESCOLARIDADE",
        "SUSPEITO_PROFISSAO",
        "SUSPEITO_SEXO",
        "SUSPEITO_ORIENTACAO_SEXUAL",
        "SUSPEITO_OR_SEXUAL",
        "SUSPEITO_NOME_DA_MAE",
        "SUSPEITO_MAE",
        "SUSPEITO_NOME_DO_PAI",
        "SUSPEITO_PAI",
        "SUSPEITO_EMAIL",
        "SUSPEITO_E_MAIL",
        "SUSPEITO_TELEFONE",
        "SUSPEITO_LOGRADOURO",
        "SUSPEITO_NUMERO",
        "SUSPEITO_COMPLEMENTO",
        "SUSPEITO_BAIRRO",
        "SUSPEITO_MUNICIPIO",
        "SUSPEITO_UF",
        "SUSPEITO_MODUS_OPERAN",
        "SUSPEITO_MODUS_OPERANDI",
        "SUSPEITO_NATUREZA_S_VINCULADA_S_AO_SUSPEITO",
        "SUSPEITO_NATUREZAS_VINCULADAS_AO_SUSPEITO",
        
        # ENVOLVIDO
        "ENVOLVIDO_NOME",
        "ENVOLVIDO_NOME_COMPLETO",
        "ENVOLVIDO_NOME_SOCIAL",
        "ENVOLVIDO_CPF",
        "ENVOLVIDO_RG",
        "ENVOLVIDO_UF_RG",
        "ENVOLVIDO_ORGAO_EXPEDIDOR",
        "ENVOLVIDO_ORGAO_EX",
        "ENVOLVIDO_ORGAO_EMISSOR",
        "ENVOLVIDO_ORGAO_EXP",
        "ENVOLVIDO_ORG_EXP",
        "ENVOLVIDO_DATA_EMISSAO",
        "ENVOLVIDO_NASCIMENTO",
        "ENVOLVIDO_DATA_NASCIMENTO",
        "ENVOLVIDO_IDADE",
        "ENVOLVIDO_ESTADO_CIVIL",
        "ENVOLVIDO_EST_CIVIL",
        "ENVOLVIDO_NACIONALIDADE",
        "ENVOLVIDO_NACIONALI",
        "ENVOLVIDO_NATURALIDADE",
        "ENVOLVIDO_UF_NATURALIDADE",
        "ENVOLVIDO_ESCOLARIDADE",
        "ENVOLVIDO_PROFISSAO",
        "ENVOLVIDO_SEXO",
        "ENVOLVIDO_ORIENTACAO_SEXUAL",
        "ENVOLVIDO_OR_SEXUAL",
        "ENVOLVIDO_NOME_DA_MAE",
        "ENVOLVIDO_MAE",
        "ENVOLVIDO_NOME_DO_PAI",
        "ENVOLVIDO_PAI",
        "ENVOLVIDO_EMAIL",
        "ENVOLVIDO_E_MAIL",
        "ENVOLVIDO_TELEFONE",
        "ENVOLVIDO_LOGRADOURO",
        "ENVOLVIDO_NUMERO",
        "ENVOLVIDO_COMPLEMENTO",
        "ENVOLVIDO_BAIRRO",
        "ENVOLVIDO_MUNICIPIO",
        "ENVOLVIDO_UF",
        
        # TESTEMUNHA
        "TESTEMUNHA_NOME",
        "TESTEMUNHA_NOME_COMPLETO",
        "TESTEMUNHA_NOME_SOCIAL",
        "TESTEMUNHA_CPF",
        "TESTEMUNHA_RG",
        "TESTEMUNHA_UF_RG",
        "TESTEMUNHA_ORGAO_EXPEDIDOR",
        "TESTEMUNHA_ORGAO_EX",
        "TESTEMUNHA_ORGAO_EMISSOR",
        "TESTEMUNHA_ORGAO_EXP",
        "TESTEMUNHA_ORG_EXP",
        "TESTEMUNHA_DATA_EMISSAO",
        "TESTEMUNHA_NASCIMENTO",
        "TESTEMUNHA_DATA_NASCIMENTO",
        "TESTEMUNHA_IDADE",
        "TESTEMUNHA_ESTADO_CIVIL",
        "TESTEMUNHA_EST_CIVIL",
        "TESTEMUNHA_NACIONALIDADE",
        "TESTEMUNHA_NACIONALI",
        "TESTEMUNHA_NATURALIDADE",
        "TESTEMUNHA_UF_NATURALIDADE",
        "TESTEMUNHA_ESCOLARIDADE",
        "TESTEMUNHA_PROFISSAO",
        "TESTEMUNHA_SEXO",
        "TESTEMUNHA_ORIENTACAO_SEXUAL",
        "TESTEMUNHA_OR_SEXUAL",
        "TESTEMUNHA_NOME_DA_MAE",
        "TESTEMUNHA_MAE",
        "TESTEMUNHA_NOME_DO_PAI",
        "TESTEMUNHA_PAI",
        "TESTEMUNHA_EMAIL",
        "TESTEMUNHA_E_MAIL",
        "TESTEMUNHA_TELEFONE",
        "TESTEMUNHA_LOGRADOURO",
        "TESTEMUNHA_NUMERO",
        "TESTEMUNHA_COMPLEMENTO",
        "TESTEMUNHA_BAIRRO",
        "TESTEMUNHA_MUNICIPIO",
        "TESTEMUNHA_UF",
        
        # MATERIAL DO VEÍCULO
        "MATERIAL_DO_VEICULO_MATERIAL",
        "MATERIAL_DO_VEICULO_PLACA",
        "MATERIAL_DO_VEICULO_RENAVAM",
        "MATERIAL_DO_VEICULO_CHASSI",
        "MATERIAL_DO_VEICULO_PAIS_LICENC",
        "MATERIAL_DO_VEICULO_PAIS_DE_LICENCIAMENTO",
        "MATERIAL_DO_VEICULO_MUN_UF_EMPL",
        "MATERIAL_DO_VEICULO_MUNICIPIO_UF_DE_EMPLACAMENTO",
        "MATERIAL_DO_VEICULO_MARCA_MODELO",
        "MATERIAL_DO_VEICULO_MARCA",
        "MATERIAL_DO_VEICULO_FABRICACAO",
        "MATERIAL_DO_VEICULO_ANO_FABRICACAO",
        "MATERIAL_DO_VEICULO_MODELO",
        "MATERIAL_DO_VEICULO_ANO_MODELO",
        "MATERIAL_DO_VEICULO_LICENCIAMENTO",
        "MATERIAL_DO_VEICULO_COR",
        "MATERIAL_DO_VEICULO_COMBUSTIVEL",
        "MATERIAL_DO_VEICULO_ESPECIE",
        "MATERIAL_DO_VEICULO_CATEGORIA",
        "MATERIAL_DO_VEICULO_TRACAO",
        "MATERIAL_DO_VEICULO_TIPO",
        "MATERIAL_DO_VEICULO_SITUACAO",
        "MATERIAL_DO_VEICULO_MATERIAL_DE",
        
        # TEXTO LIVRE
        "NARRATIVA",
        "PROVIDENCIAS"
    ]
    
    colunas_existentes = [c for c in ordem_pref if c in df.columns]
    colunas_extras = [c for c in df.columns if c not in colunas_existentes]
    return df[colunas_existentes + colunas_extras]

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
    
    if not arquivos:
        print(f"Nenhum arquivo PDF encontrado na pasta '{pasta_origem}'.")
        return
        
    print(f"Encontrados {len(arquivos)} arquivos PDF. Iniciando extração dinâmica por seções...")
    
    resultados = []
    for idx, arq in enumerate(arquivos, 1):
        print(f"[{idx}/{len(arquivos)}] Processando: {os.path.basename(arq)}...")
        res = processar_pdf(arq, db_mappings, lista_municipios, bairros_por_mun)
        resultados.append(res)
        
    df = pd.DataFrame(resultados)
    df = ordenar_dataframe(df)
    
    try:
        with pd.ExcelWriter(arquivo_excel, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="BOs_Extraidos")
    except Exception as e:
        print(f"Erro ao salvar a planilha Excel '{arquivo_excel}': {str(e)}")
        return
        
    print(f"\nSucesso! {len(resultados)} BOs processados e salvos em: '{arquivo_excel}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rotina de Extração Dinâmica de Dados de BOs em PDF para Excel.")
    parser.add_argument(
        "--pasta", "-p", 
        default="dados_pdf",
        help="Pasta contendo os arquivos PDF dos BOs. Padrão: 'dados_pdf'"
    )
    parser.add_argument(
        "--saida", "-s",
        default=f"BOs_Processados_{datetime.today().strftime('%d-%m-%Y')}.xlsx",
        help="Nome do arquivo Excel de saída."
    )
    
    args = parser.parse_args()
    
    if args.pasta == "dados_pdf" and not os.path.exists("dados_pdf"):
        os.makedirs("dados_pdf")
        print("Pasta padrão 'dados_pdf' criada. Coloque seus PDFs nela.")
        
    processar_pasta_bo(args.pasta, args.saida)
