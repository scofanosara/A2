# utils.py
import pandas as pd
import re
import difflib

def load_principios(path="data/principios.csv"):
    df = pd.read_csv(path, dtype=str).fillna("")
    # convert weight to numeric if possible
    if "weight" in df.columns:
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(1).astype(int)
    else:
        df["weight"] = 1
    df["keywords_list"] = df["keywords"].apply(lambda s: [k.strip().lower() for k in s.split(";") if k.strip()])
    return df

def normalize_text(text):
    text = text.lower()
    text = re.sub(r'[^a-z0-9à-úç\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_tokens(text):
    text = normalize_text(text)
    tokens = text.split()
    return tokens

def match_by_keywords(user_text, keywords_list, threshold=0.8):
    """
    Retorna True se alguma keyword aparece no texto do usuário com correspondência exata ou fuzzy.
    Usa correspondência exata de substring e, se não, difflib para aproximação entre palavras.
    """
    norm = normalize_text(user_text)
    for kw in keywords_list:
        if kw in norm:
            return True
        # fuzzy match: compare kw to tokens or sequences
        tokens = extract_tokens(norm)
        # check close matches among tokens
        close = difflib.get_close_matches(kw, tokens, n=1, cutoff=threshold)
        if close:
            return True
        # check if kw is multiword: try sliding windows
        kw_tokens = kw.split()
        if len(kw_tokens) > 1:
            for i in range(len(tokens)-len(kw_tokens)+1):
                seq = " ".join(tokens[i:i+len(kw_tokens)])
                if difflib.SequenceMatcher(None, seq, kw).ratio() >= threshold:
                    return True
    return False

def evaluate_arguments(case_id, side, user_text, df_principios):
    """
    Retorna:
     - score_total
     - matched_rows (list of dicts)
     - missing_recommendations (list of dicts)
    """
    df_case = df_principios[(df_principios["case_id"].astype(str)==str(case_id)) & (df_principios["side"].str.lower()==side.lower())]
    # If there are no entries for that side => recommend the other side's principles as cross-check
    df_case_all = df_principios[df_principios["case_id"].astype(str)==str(case_id)]
    matched = []
    score = 0
    for idx, row in df_case.iterrows():
        kw_list = row["keywords_list"]
        found = match_by_keywords(user_text, kw_list)
        if found:
            score += int(row.get("weight",1))
            matched.append({
                "principle": row["principle"],
                "article": row["article"],
                "weight": int(row.get("weight",1)),
                "matched_keyword_sample": ";".join(kw_list[:2])
            })
    # Recommendations: which important principles for this side were NOT mentioned by the user
    recommended = []
    for idx, row in df_case.iterrows():
        kw_list = row["keywords_list"]
        found = match_by_keywords(user_text, kw_list)
        if not found:
            recommended.append({
                "principle": row["principle"],
                "article": row["article"],
                "weight": int(row.get("weight",1)),
                "keywords": kw_list
            })
    # Also provide "contra-argumentos" (o que a outra parte pode alegar):
    contra = []
    df_other_side = df_case_all[df_case_all["side"].str.lower() != side.lower()]
    for idx, row in df_other_side.iterrows():
        contra.append({
            "principle": row["principle"],
            "article": row["article"],
            "weight": int(row.get("weight",1)),
            "keywords": row["keywords_list"]
        })
    return {
        "score": score,
        "matched": matched,
        "recommended": recommended,
        "counterarguments": contra
    }
