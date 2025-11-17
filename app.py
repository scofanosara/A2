import streamlit as st
from utils import load_principios, evaluate_arguments

st.set_page_config(page_title="Simulador Jurídico para Estudantes", layout="wide")
st.title("Simulador Jurídico para Estudantes")

# -----------------------
# Fonte de dados (sidebar)
# -----------------------
st.sidebar.header("Fonte de dados")
use_sample = st.sidebar.checkbox("Usar base padrão (data/principios.csv)", True)
uploaded = st.sidebar.file_uploader("Ou envie um CSV próprio", type=["csv"])

if uploaded is not None:
    df_princ = load_principios(uploaded)
elif use_sample:
    df_princ = load_principios("data/principios.csv")
else:
    st.warning("Selecione 'Usar base padrão' ou faça upload de um CSV para continuar.")
    st.stop()

# Validação mínima de colunas
required = {"case_id", "case_title", "case_description", "side",
            "principle", "article", "weight", "keywords"}
missing = required - set(df_princ.columns)
if missing:
    st.error(f"Faltam colunas no CSV: {', '.join(sorted(missing))}")
    st.stop()

# -----------------------
# Seleção de caso
# -----------------------
cases = (
    df_princ[["case_id", "case_title", "case_description"]]
    .drop_duplicates()
    .copy()
)

# Tentar ordenar por inteiro
try:
    cases["case_id_int"] = cases["case_id"].astype(int)
    cases = cases.sort_values("case_id_int")
except Exception:
    cases = cases.sort_values("case_id")

case_map = {str(r["case_id"]): r for _, r in cases.iterrows()}

if not case_map:
    st.error("Nenhum caso disponível na base selecionada.")
    st.stop()

st.sidebar.header("Selecione o caso")
case_choice = st.sidebar.selectbox(
    "Caso",
    options=list(case_map.keys()),
    format_func=lambda x: f'Caso {x} — {case_map[x]["case_title"]}'
)
case_info = case_map[case_choice]
st.subheader(f'Caso {case_choice}: {case_info["case_title"]}')
st.write(case_info["case_description"])

# -----------------------
# Entrada do usuário
# -----------------------
side_choice = st.radio(
    "Você vai atuar como:",
    ["acusacao", "defesa"],
    index=0
)

st.markdown("### Digite seus argumentos")
user_text = st.text_area(
    "Descreva os princípios e artigos que fundamentam sua argumentação:",
    height=160
)

# -----------------------
# Avaliação
# -----------------------
if st.button("Avaliar argumentação"):
    if not user_text.strip():
        st.warning("Por favor, digite sua argumentação antes de avaliar.")
        st.stop()

    with st.spinner("Analisando..."):
        result = evaluate_arguments(case_choice, side_choice, user_text, df_princ)

    score = result["score"]
    max_score = result["max_score"]

    if max_score > 0:
        # Formatação brasileira: 3,0/10,0
        score_str = f"{score:.1f}".replace(".", ",")
        max_str = f"{max_score:.1f}".replace(".", ",")
        st.success(f"Pontuação obtida: {score_str}/{max_str} pontos")
    else:
        st.warning(
            "Não há keywords cadastradas para este caso e lado na base. "
            "Verifique o CSV (coluna 'keywords')."
        )

    st.markdown("#### Argumentos identificados")
    if result["matched"]:
        for m in result["matched"]:
            st.write(
                f"- **{m['principle']}** — {m['article']}"
            )
    else:
        st.info(
            "Nenhum princípio identificado. Tente usar palavras-chave mais diretas "
            "(ex.: 'dignidade', 'igualdade material', 'Art. 5º')."
        )

    st.markdown("#### Sugestões de aprimoramento")
    if result["recommended"]:
        for r in result["recommended"]:
            st.write(
                f"- **{r['principle']}** — {r['article']}"
            )
    else:
        st.write("Você citou todos os princípios principais cadastrados para sua posição.")

    st.markdown("#### Argumentos da parte contrária")
    if result["counterarguments"]:
        for c in result["counterarguments"]:
            st.write(
                f"- **{c['principle']}** — {c['article']}"
            )
    else:
        st.write("Não há argumentos catalogados para a outra parte neste caso.")

st.markdown("---")
st.write(
    "Dica: use termos objetivos como 'CF 5º', 'dignidade', 'igualdade material', "
    "para facilitar a identificação automática dos princípios."
)
