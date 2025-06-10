import streamlit as st
import pandas as pd
import google.generativeai as genai

# --- CONFIGURAÇÃO DA API DO GEMINI ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    gemini_configurado = True
except Exception as e:
    st.error(f"Erro ao configurar a API do Gemini: {e}. Verifique seu arquivo .streamlit/secrets.toml")
    gemini_configurado = False

# --- FUNÇÕES DE LÓGICA DE ANÁLISE (Sem alterações) ---

def classificar_esforco(valor_adaptacao):
    if valor_adaptacao <= 1.0: return "Baixo esforço de adaptação"
    if 1.0 < valor_adaptacao <= 2.0: return "Esforço de adaptação moderado"
    if 2.0 < valor_adaptacao <= 2.9: return "Esforço de adaptação moderado alto"
    if valor_adaptacao >= 3.0: return "Potencial estresse"
    return "Indefinido"

def analisar_disc(dados_df):
    resultados = {}
    fatores_disc = ["Dominador", "Influenciador", "Estabilidade", "Conformidade"]
    for fator in fatores_disc:
        coluna_natural, coluna_work = f"{fator} Natural", f"{fator} Work"
        if coluna_natural in dados_df.columns and coluna_work in dados_df.columns:
            natural_val = dados_df[coluna_natural].iloc[0]
            work_val = dados_df[coluna_work].iloc[0]
            adaptacao = abs(work_val - natural_val)
            resultados[fator] = {
                "Natural": natural_val,
                "Adaptado": work_val,
                "Adaptação": adaptacao,
                "Nível de Esforço": classificar_esforco(adaptacao)
            }
    return resultados

def analisar_motivadores(dados_df):
    resultados = {"Paixões": [], "Menores Motivadores": []}
    motivadores = ["Conhecimento e Descoberta:", "Retorno sobre Investimento (ROI):", "Estética:", "Ajudar os Outros:", "Princípios Orientadores:", "Liderança:", "Paz e Harmonia:"]
    for m in motivadores:
        if m in dados_df.columns:
            score = dados_df[m].iloc[0]
            if score > 7.0:
                resultados["Paixões"].append(f"{m.replace(':', '')} ({score})")
    return resultados

def analisar_axiologia(dados_df):
    resultados = {"Pontos Fortes": [], "Oportunidades de Melhoria": []}
    competencias = ["Foco no Cliente", "Autoconfiança", "Liderando outros"]
    for c in competencias:
        if c in dados_df.columns:
            score = dados_df[c].iloc[0]
            if score > 6.7:
                resultados["Pontos Fortes"].append(f"{c} ({score})")
            else:
                resultados["Oportunidades de Melhoria"].append(f"{c} ({score})")
    if 'Confiabilidade (Reliability)' in dados_df.columns:
        resultados["Confiabilidade"] = dados_df['Confiabilidade (Reliability)'].iloc[0]
    return resultados

def gerar_relatorio_final(dados_df):
    with st.spinner('Realizando análises e consultando a IA para gerar o relatório completo...'):
        analise_disc_data = analisar_disc(dados_df)
        analise_motivadores_data = analisar_motivadores(dados_df)
        analise_axiologia_data = analisar_axiologia(dados_df)
        resumo_para_ia = f"""
        **Dados do(a) Avaliado(a):** - Nome: {dados_df['Assessment Taker Name'].iloc[0]}
        **Análise Comportamental (DISC):** - Análise de Adaptação e Estresse: {analise_disc_data}
        **Análise Motivacional:** - Paixões (motivadores > 7.0): {analise_motivadores_data['Paixões']}
        **Análise de Competências (Axiologia):** - Confiabilidade (Reliability): {analise_axiologia_data.get('Confiabilidade', 'N/A')} - Pontos Fortes (competências > 6.7): {analise_axiologia_data['Pontos Fortes']} - Oportunidades de Melhoria: {analise_axiologia_data['Oportunidades de Melhoria']}
        """
        prompt_final = f"""
        Aja como o Assistente de Análise Virtual da Lidera Assessments, conforme o manual de identidade fornecido.
        Sua tarefa é gerar um relatório de análise combinada para um(a) avaliado(a).
        Use os dados estruturados fornecidos abaixo para preencher os 12 itens do relatório. Siga rigorosamente a estrutura e a formatação solicitadas no manual.
        Seja profissional, objetivo e use os dados para justificar suas conclusões. Refira-se ao indivíduo sempre como "O(A) Avaliado(a)".

        **DADOS ESTRUTURADOS PARA ANÁLISE:**
        {resumo_para_ia}

        **ESTRUTURA FINAL DO RELATÓRIO (Sequência Obrigatória):**
        Gere um relatório que contenha exatamente os seguintes 12 títulos, nesta ordem. Elabore o conteúdo de cada item com base nos dados fornecidos.

        1.  **Objetivo da Análise**
        2.  **Data da Avaliação Mais Recente** (Use a data de hoje para este exemplo)
        3.  **Dados Considerados** (Resuma as principais pontuações de cada avaliação)
        4.  **Potenciais Profissões Compatíveis** (Sugira com base nos pontos fortes)
        5.  **Parecer Geral da Análise** (Crie um resumo geral)
        6.  **Nível de Correspondência com o Cargo** (Assuma um cargo genérico de 'Liderança' e justifique)
        7.  **Vantagens e Pontos Fortes para a Função**
        8.  **Oportunidades de Melhoria**
        9.  **Análise de Estresse e Adaptação DISC** (Detalhe a análise dos fatores DISC)
        10. **Análise dos Vieses Comportamentais da Axiologia** (Como não temos dados de viés, informe "Dados não fornecidos para esta análise")
        11. **Análise do QP e a influência dos Sabotadores** (Informe "Dados não fornecidos para esta análise")
        12. **Importante** (Use o texto obrigatório do seu manual)
        """
        try:
            response = model.generate_content(prompt_final)
            return response.text
        except Exception as e:
            return f"Ocorreu um erro na IA: {e}"

# --- INTERFACE GRÁFICA (UI) ---
st.set_page_config(layout="wide")
st.title("Assistente de Análise Virtual - Lidera Assessments")

uploaded_file = st.file_uploader("Carregue aqui o arquivo CSV com os dados combinados", type=["csv"])

if uploaded_file is not None:
    try:
        dados_brutos = pd.read_csv(uploaded_file)
        
        with st.expander("Visualizar Dados Carregados"):
            st.dataframe(dados_brutos)

        # --- LÓGICA CORRIGIDA ---
        # 1. O SELETOR DE PESSOA FICA FORA DO BOTÃO
        pessoa_selecionada = st.selectbox(
            "Selecione o(a) avaliado(a) para analisar:",
            options=dados_brutos['Assessment Taker Name'].unique()
        )

        # 2. O BOTÃO APENAS DISPARA A AÇÃO
        if st.button("Gerar Relatório de Análise"):
            # Filtra os dados da pessoa que foi SELECIONADA
            dados_pessoa = dados_brutos[dados_brutos['Assessment Taker Name'] == pessoa_selecionada]

            if not dados_pessoa.empty and gemini_configurado:
                relatorio_final = gerar_relatorio_final(dados_pessoa)
                
                st.subheader(f"Relatório para: {pessoa_selecionada}")
                st.markdown(relatorio_final)
            else:
                st.error("Não foi possível gerar o relatório. Verifique os dados ou a configuração da API.")

    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")