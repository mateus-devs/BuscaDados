import os
import pandas as pd
import time

def executar_scraping(df: pd.DataFrame, limite: int) -> pd.DataFrame:
    """
    Simula a busca web baseada em Cidade e Bairro para criar a coluna 'Empresa'.
    """
    # Cria a coluna caso ela não exista
    if 'Empresa' not in df.columns:
        df['Empresa'] = None
        
    # Processa apenas o limite de linhas definido no Streamlit
    for index, row in df.head(limite).iterrows():
        cidade = row.get('Cidade', 'Não Informada')
        bairro = row.get('Bairro', 'Não Informado')
        
        # Simula o tempo de uma busca real na internet (1 segundo)
        time.sleep(1) 
        
        # Simulação do nome da empresa encontrado na web
        resultado_fake = f"Empresa Exemplo de {bairro}" 
        
        df.at[index, 'Empresa'] = resultado_fake
        
    return df

def analisar_colunas_openai(df: pd.DataFrame) -> pd.DataFrame:
    """
    Simulação da OpenAI. Processa os dados localmente sem gastar créditos
    e sem precisar de chave de API por enquanto.
    """
    if 'Analise_IA' not in df.columns:
        df['Analise_IA'] = None

    for index, row in df.iterrows():
        if pd.isna(row.get('Empresa')):
            continue
            
        # Simula o tempo de resposta da IA
        time.sleep(0.5)
        
        # Apenas uma resposta simulada baseada nos seus dados
        df.at[index, 'Analise_IA'] = "Setor Simulado (Sem API OpenAI)"
            
    return df
