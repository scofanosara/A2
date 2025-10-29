# app.py
import streamlit as st
import pandas as pd
from utils import load_principios, evaluate_arguments
import io
import csv
import datetime

st.set_page_config(page_title="Simulador Jurídico para Estudantes", layout="wide")
st.title("Simulador Jurídico para Estudantes ⚖️")

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

# Validação mínima de colunas (evita erro mais à frente)
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
# Ordena por inteiro quando possível
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
# IMPORTANTE: usar uma variável diferente ('side_choice') para evitar colisão
side_choice = st.radio("Você vai atuar como:", ["acusacao", "defesa"], index=0, key="side_radio")

st.markdown("### Digite os princípios / artigos / argumentos que você usaria")
user_text = st.text_area(
    'Escreva aqui (ex.: "invoco direito à saúde, dignidade da pessoa humana e a súmula tal")',
    height=160
)

# (Opcional) Debug: ver o que conta ponto para este caso/lado
with st.expander("Debug – ver o que conta ponto neste caso/lado (opcional)"):
    df_dbg = df_princ[
        (df_princ["case_id"].astype(str) == str(case_choice)) &
        (df_princ["side"].str.lower() == side_choice.lower())
    ][["side", "principle", "article", "weight", "keywords", "keywords_list"]]
    st.dataframe(df_dbg, use_container_width=True)

# -----------------------
# Avaliação
# -----------------------
if st.button("Avaliar argumentação"):
    with st.spinner("Avaliando..."):
        result = evaluate_arguments(case_choice, side_choice, user_text, df_princ)

    score = result["score"]
    st.success(f"Pontuação obtida: {score} pontos")

    st.markdown("#### Argumentos identificados (match automático)")
    if result["matched"]:
        for m in result["matched"]:
            st.write(f"- **{m['principle']}** — {m['article']} (peso {m['weight']})")
    else:
        st.info(
            "Nenhum princípio claramente identificado pelo algoritmo a partir do texto. "
            "Tente usar palavras-chave mais diretas (ex.: 'direito à saúde', 'CF 196', 'dignidade')."
        )

    st.markdown("#### Sugestões de princípios que você poderia ter usado")
    if result["recommended"]:
        for r in result["recommended"]:
            st.write(
                f"- **{r['principle']}** — {r['article']} (peso {r['weight']}) — "
                f"palavras-chave esperadas: {', '.join(r['keywords'])}"
            )
    else:
        st.write("Excelente — você citou todos os princípios principais previstos para sua posição.")

    st.markdown("#### O que a parte contrária pode alegar")
    if result["counterarguments"]:
        for c in result["counterarguments"]:
            st.write(
                f"- **{c['principle']}** — {c['article']} (peso {c['weight']}) — "
                f"palavras-chave: {', '.join(c['keywords'])}"
            )
    else:
        st.write("Não há argumentos catalogados para a outra parte neste caso.")

    # -----------------------
    # Relatório (CSV download)
    # -----------------------
    report_rows = []
    ts = datetime.datetime.now().isoformat(timespec="seconds")

    for m in result["matched"]:
        report_rows.append({
            "timestamp": ts,
            "case_id": case_choice,
            "case_title": case_info["case_title"],
            "side": side_choice,
            "status": "matched",
            "principle": m["principle"],
            "article": m["article"],
            "weight": m["weight"]
        })

    for r in result["recommended"]:
        report_rows.append({
            "timestamp": ts,
            "case_id": case_choice,
            "case_title": case_info["case_title"],
            "side": side_choice,
            "status": "recommended",
            "principle": r["principle"],
            "article": r["article"],
            "weight": r["weight"]
        })

    if report_rows:
        all_keys = set().union(*(row.keys() for row in report_rows))
        fieldnames = sorted(all_keys)

        sio = io.StringIO()
        writer = csv.DictWriter(sio, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in report_rows:
            writer.writerow(row)

        csv_bytes = sio.getvalue().encode("utf-8")
        st.download_button(
            "📥 Baixar relatório (CSV)",
            data=csv_bytes,
            file_name=f"relatorio_{case_choice}_{side_choice}.csv",
            mime="text/csv"
        )
    else:
        st.info("Nenhum dado para relatório.")

st.markdown("---")
st.write(
    "Dicas rápidas: escreva termos objetivos (ex.: 'CF 196', 'direito à saúde', 'furto', 'dignidade'). "
    "O algoritmo usa palavras-chave para identificar os princípios."
)
