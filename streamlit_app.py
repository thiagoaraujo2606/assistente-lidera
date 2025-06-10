import streamlit as st
import pandas as pd
import google.generativeai as genai
import altair as alt
from datetime import datetime
import json

# --- CONFIGURAÇÃO DA PÁGINA E API ---
st.set_page_config(
    page_title="Assistente Lidera Assessments",
    page_icon="📊",
    layout="wide"
)

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
    gemini_configurado = True
except Exception:
    gemini_configurado = False

# --- FUNÇÕES DE LÓGICA DE ANÁLISE (A maioria sem alterações) ---
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
            natural_val = pd.to_numeric(dados_df[coluna_natural].iloc[0], errors='coerce')
            work_val = pd.to_numeric(dados_df[coluna_work].iloc[0], errors='coerce')
            if pd.notna(natural_val) and pd.notna(work_val):
                adaptacao = abs(work_val - natural_val)
                resultados[fator] = { "Natural": natural_val, "Adaptado": work_val, "Adaptação": adaptacao, "Nível de Esforço": classificar_esforco(adaptacao) }
    return resultados

def criar_grafico_disc(dados_analise_disc):
    dados_grafico = []
    for fator, valores in dados_analise_disc.items():
        dados_grafico.append({"Fator": fator, "Tipo de Perfil": "Natural", "Pontuação": valores["Natural"]})
        dados_grafico.append({"Fator": fator, "Tipo de Perfil": "Adaptado", "Pontuação": valores["Adaptado"]})
    df_grafico = pd.DataFrame(dados_grafico)
    grafico = alt.Chart(df_grafico).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('Fator:N', title='Fator DISC', sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y('Pontuação:Q', title='Pontuação'),
        color=alt.Color('Tipo de Perfil:N', title='Tipo de Perfil', scale=alt.Scale(range=['#2A70B8', '#FF4B4B'])),
        xOffset='Tipo de Perfil:N'
    ).properties(title='Comparativo de Perfis DISC: Natural vs. Adaptado')
    return grafico

# --- CORREÇÃO: Função de relatório agora pede e processa JSON ---
def gerar_relatorio_final(dados_df):
    with st.spinner('Analisando dados e consultando a IA...'):
        analise_disc_data = analisar_disc(dados_df)
        resumo_para_ia = f"**Análise Comportamental (DISC):** {analise_disc_data}"
        
        prompt_final = f"""
        Aja como o Assistente de Análise Virtual da Lidera Assessments. Sua tarefa é gerar o conteúdo para um relatório de análise combinada.
        **Sua resposta deve ser OBRIGATORIAMENTE um objeto JSON válido.**
        O JSON deve ter chaves para cada um dos 12 itens do relatório. O valor de cada chave deve ser o texto correspondente para aquela seção.
        Use os dados estruturados fornecidos para elaborar o conteúdo de cada seção.
        REGRAS: Refira-se ao indivíduo sempre como "O(A) Avaliado(a)". Substitua "scores" por "pontuações".

        DADOS ESTRUTURADOS PARA ANÁLISE:
        {resumo_para_ia}

        ESTRUTURA JSON OBRIGATÓRIA (preencha os valores):
        {{
          "objetivo_analise": "...",
          "data_avaliacao": "{datetime.now().strftime('%d/%m/%Y')}",
          "dados_considerados": "...",
          "profissoes_compativeis": "...",
          "parecer_geral": "...",
          "correspondencia_cargo": "...",
          "vantagens_fortes": "...",
          "oportunidades_melhoria": "...",
          "analise_disc": "...",
          "analise_vieses": "Dados não fornecidos para esta análise.",
          "analise_qp": "Dados não fornecidos para esta análise.",
          "importante": "Em resumo, a análise combinada destas avaliações, embora valiosa, exige uma abordagem cautelosa e multifacetada..."
        }}
        """
        try:
            response = model.generate_content(prompt_final)
            # Limpa e parseia a resposta JSON da IA
            json_text = response.text.strip().replace("```json", "").replace("```", "")
            report_data = json.loads(json_text)
            return report_data, analise_disc_data
        except (json.JSONDecodeError, Exception) as e:
            st.error(f"Houve um erro ao processar a resposta da IA. Detalhes: {e}")
            st.text_area("Resposta bruta da IA", response.text)
            return None, None

def responder_chat(pergunta, relatorio_gerado_dict, dados_pessoa):
    # Converte o dicionário do relatório em texto para o contexto
    relatorio_texto = "\n".join([f"**{key.replace('_', ' ').title()}**: {value}" for key, value in relatorio_gerado_dict.items()])
    base_conhecimento = f"""
    CONTEXTO PRINCIPAL: O RELATÓRIO GERADO
    ---
    {relatorio_texto}
    ---
    REGRAS DE ANÁLISE: A "Adaptação" DISC é a diferença absoluta entre Natural e Adaptado. > 3.0 é "Potencial estresse".
    DADOS BRUTOS:
    {dados_pessoa.to_string()}
    """
    prompt_chat = f"""
    Você é um assistente especialista que ajuda a interpretar um relatório de avaliação.
    Sua fonte primária de conhecimento é o contexto fornecido. Priorize respostas baseadas nele.
    Para saudações ou perguntas gerais, responda de forma amigável e concisa.

    Base de Conhecimento: {base_conhecimento}
    Pergunta do Usuário: "{pergunta}"
    Sua Resposta:
    """
    try:
        response = model.generate_content(prompt_chat)
        return response.text
    except Exception as e:
        return f"Ocorreu um erro na IA do chat: {e}"

# --- INTERFACE GRÁFICA (UI) FINAL ---

st.title("Assistente de Análise Virtual Personalizado")
st.caption("Lidera Assessments®")

# CORREÇÃO: Injeta CSS para o layout do chat
st.markdown("""
<style>
    .chat-container {
        display: flex;
        flex-direction: column;
    }
    .chat-message {
        padding: 0.75rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        max-width: 100%;
        word-wrap: break-word;
    }
    .user-message {
        background-color: #fce8cc;
        align-self: flex-end;
    }
    .assistant-message {
        background-color: #fcf3e6;
        align-self: flex-start;
    }
    .st-expander > div:first-child > div:first-child p {
    font-weight: bold !important;
    font-size: 2em !important; /* Aumenta em 10% */
    }        
</style>
""", unsafe_allow_html=True)


if 'analise_completa' not in st.session_state:
    st.session_state.analise_completa = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

uploaded_file = st.file_uploader("Para começar, carregue o arquivo CSV com os dados da avaliação", type=["csv"])

if uploaded_file is not None:
    dados_brutos = pd.read_csv(uploaded_file)
    st.markdown("---")
    st.subheader("Seleção de Perfil")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        pessoa_selecionada = st.selectbox("Escolha o perfil para analisar", options=dados_brutos['Assessment Taker Name'].unique())
    with col2:
        analyze_button = st.button("Gerar Relatório 📈", type="primary", use_container_width=True, disabled=not gemini_configurado)

    if analyze_button:
        dados_pessoa = dados_brutos[dados_brutos['Assessment Taker Name'] == pessoa_selecionada]
        if not dados_pessoa.empty:
            report_data_dict, analise_disc_detalhada = gerar_relatorio_final(dados_pessoa)
            if report_data_dict:
                st.session_state.analise_completa = {
                    "relatorio_dict": report_data_dict,
                    "grafico_disc_data": analise_disc_detalhada,
                    "dados_pessoa": dados_pessoa
                }
                st.session_state.chat_history = [{
                    "role": "assistant",
                    "content": "Olá! O relatório foi gerado. Use o chat abaixo para tirar dúvidas sobre os resultados."
                }]
        else:
            st.error("Não foi possível encontrar os dados para a pessoa selecionada.")
            st.session_state.analise_completa = None

if st.session_state.analise_completa:
    st.markdown("---")
    st.header(f"Resultados da Análise para: {st.session_state.analise_completa['dados_pessoa']['Assessment Taker Name'].iloc[0]}")
    
    report_dict = st.session_state.analise_completa["relatorio_dict"]
    
    # 1. Relatório Formatado com Expanders
    st.subheader("📄 Relatório Completo")
    titulos = {
        "objetivo_analise": "🎯 Objetivo da Análise", "data_avaliacao": "📅 Data da Avaliação Mais Recente",
        "dados_considerados": "🗂️ Dados Considerados", "profissoes_compativeis": "🚀 Potenciais Profissões Compatíveis",
        "parecer_geral": "💡 Parecer Geral da Análise", "correspondencia_cargo": "👔 Nível de Correspondência com o Cargo",
        "vantagens_fortes": "🌟 Vantagens e Pontos Fortes", "oportunidades_melhoria": "🌱 Oportunidades de Melhoria",
        "analise_disc": "🔄 Análise de Estresse e Adaptação DISC", "analise_vieses": "🔍 Análise de Vieses",
        "analise_qp": "🧠 Análise de QP e Sabotadores", "importante": "❗ Importante"
    }
    for key, titulo in titulos.items():
        with st.expander(titulo, expanded=True):
            st.markdown(report_dict.get(key, "Não disponível."))
    
    st.markdown("---")

    # 2. Gráfico
    st.subheader("📊 Análise Gráfica")
    if st.session_state.analise_completa["grafico_disc_data"]:
        grafico = criar_grafico_disc(st.session_state.analise_completa["grafico_disc_data"])
        st.altair_chart(grafico, use_container_width=True)
    
    st.markdown("---")

    # 3. Chat Interativo
    st.subheader("💬 Converse com a IA sobre este Relatório")

    chat_container = st.container(height=400)
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for message in st.session_state.chat_history:
            role_class = "user-message" if message["role"] == "user" else "assistant-message"
            st.markdown(f'<div class="chat-message {role_class}">{message["content"]}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

if st.session_state.analise_completa:
    if prompt := st.chat_input("Faça uma pergunta sobre o relatório..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        response = responder_chat(
            prompt, 
            st.session_state.analise_completa["relatorio_dict"], 
            st.session_state.analise_completa["dados_pessoa"]
        )
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

if not gemini_configurado:
    st.warning("A funcionalidade de IA está desabilitada. Configure a chave de API para prosseguir.")