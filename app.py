# app.py
import streamlit as st
import pandas as pd
from utils import load_principios, evaluate_arguments
from io import BytesIO
import csv
import datetime

st.set_page_config(page_title="Simulador Jurídico para Estudantes", layout="wide")
st.title("Simulador Jurídico para Estudantes ⚖️")

# Load data
DATA_PATH = "data/principios.csv"
df_princ = load_principios(DATA_PATH)

st.sidebar.header("Fonte de dados")
use_sample = st.sidebar.checkbox("Usar base padrão (principios.csv)", True)
uploaded = st.sidebar.file_uploader("Substituir base (CSV)", type=["csv"])
if uploaded is not None:
    df_princ = load_principios(uploaded)

# Select case
cases = df_princ[["case_id","case_title","case_description"]].drop_duplicates().sort_values("case_id")
case_map = {str(r["case_id"]): r for _, r in cases.iterrows()}

st.sidebar.header("Selecione o caso")
case_choice = st.sidebar.selectbox("Caso", options=list(case_map.keys()), format_func=lambda x: f'Caso {x} — {case_map[x]["case_title"]}')
case_info = case_map[case_choice]
st.subheader(f'Caso {case_choice}: {case_info["case_title"]}')
st.write(case_info["case_description"])

# Side selection
side = st.radio("Você vai atuar como:", ["acusacao", "defesa"], index=1)

st.markdown("### Digite os princípios / artigos / argumentos que você usaria")
user_text = st.text_area("Escreva aqui (ex.: \"invoco direito à saúde, dignidade da pessoa humana e a súmula tal\")", height=160)

if st.button("Avaliar argumentação"):
    with st.spinner("Avaliando..."):
        result = evaluate_arguments(case_choice, side, user_text, df_princ)
    score = result["score"]
    st.success(f"Pontuação obtida: {score} pontos")
    st.markdown("#### Argumentos identificados (match automático)")
    if result["matched"]:
        for m in result["matched"]:
            st.write(f"- **{m['principle']}** — {m['article']} (peso {m['weight']})")
    else:
        st.info("Nenhum princípio claramente identificado pelo algoritmo a partir do texto. Tente usar palavras-chave mais diretas (ex.: 'direito à saúde', 'CF 196', 'dignidade').")
    st.markdown("#### Sugestões de princípios que você poderia ter usado")
    if result["recommended"]:
        for r in result["recommended"]:
            st.write(f"- **{r['principle']}** — {r['article']} (peso {r['weight']}) — palavras-chave esperadas: {', '.join(r['keywords'])}")
    else:
        st.write("Excelente — você citou todos os princípios principais previstos para sua posição.")
    st.markdown("#### O que a parte contrária pode alegar")
    if result["counterarguments"]:
        for c in result["counterarguments"]:
            st.write(f"- **{c['principle']}** — {c['article']} (peso {c['weight']}) — palavras-chave: {', '.join(c['keywords'])}")
    else:
        st.write("Não há argumentos catalogados para a outra parte neste caso.")
    # Build a small report CSV for download
    report_rows = []
    ts = datetime.datetime.now().isoformat(timespec='seconds')
    for m in result["matched"]:
        report_rows.append({
            "timestamp": ts,
            "case_id": case_choice,
            "case_title": case_info["case_title"],
            "side": side,
            "principle_matched": m["principle"],
            "article": m["article"],
            "weight": m["weight"]
        })
    # recommended
    for r in result["recommended"]:
        report_rows.append({
            "timestamp": ts,
            "case_id": case_choice,
            "case_title": case_info["case_title"],
            "side": side,
            "principle_suggested": r["principle"],
            "article": r["article"],
            "weight": r["weight"]
        })
    if report_rows:
        csv_buf = BytesIO()
        fieldnames = list(report_rows[0].keys())
        writer = csv.DictWriter(csv_buf, fieldnames=fieldnames)
        writer.writeheader()
        for rr in report_rows:
            writer.writerow(rr)
        csv_buf.seek(0)
        st.download_button("📥 Baixar relatório (CSV)", data=csv_buf, file_name=f"relatorio_{case_choice}_{side}.csv", mime="text/csv")
    else:
        st.info("Nenhum dado para relatório.")

st.markdown("---")
st.write("Dicas rápidas: escreva termos objetivos (ex.: 'CF 196', 'direito à saúde', 'furto', 'dignidade'). O algoritmo usa palavras-chave para identificar os princípios.")
