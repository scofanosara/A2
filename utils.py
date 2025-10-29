# utils.py
import pandas as pd
import re
import difflib
import unicodedata
from typing import List, Dict, Any

# =============================
# Normalização
# =============================

def _strip_accents(s: str) -> str:
    if s is None:
        return ""
    return "".join(c for c in unicodedata.normalize('NFD', s) if not unicodedata.combining(c))

def normalize_text(text: str) -> str:
    text = (text or "").casefold()
    text = _strip_accents(text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_tokens(text: str) -> List[str]:
    return normalize_text(text).split()

# =============================
# Base de dados
# =============================

def _split_kws(s: str) -> List[str]:
    parts = [p.strip() for p in str(s or "").split(";") if p.strip()]
    return [normalize_text(p) for p in parts]

def load_principios(path: str = "data/principios.csv") -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str).fillna("")

    # weight numérico
    if "weight" in df.columns:
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(1).astype(int)
    else:
        df["weight"] = 1

    # checagem de colunas obrigatórias
    required = {"case_id", "case_title", "case_description", "side",
                "principle", "article", "weight", "keywords"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltam colunas no CSV: {', '.join(sorted(missing))}")

    # keywords enriquecidas com principle e article (cobre quem digita 'art 196', etc.)
    df["keywords_list"] = df.apply(
        lambda r: list(dict.fromkeys(
            _split_kws(r.get("keywords", "")) +
            _split_kws(r.get("principle", "")) +
            _split_kws(r.get("article", ""))
        )),
        axis=1
    )
    return df

# =============================
# Matching
# =============================

def match_by_keywords(user_text: str, keywords_list: List[str], threshold: float = 0.80) -> bool:
    """
    True se alguma keyword casa com o texto do usuário (substring direta ou fuzzy).
    Faz pré-processamento uma única vez por chamada.
    """
    norm = normalize_text(user_text)
    tokens = extract_tokens(user_text)

    for kw in keywords_list:
        if not kw:
            continue

        # 1) substring direta
        if kw in norm:
            return True

        # 2) fuzzy por tokens individuais
        if difflib.get_close_matches(kw, tokens, n=1, cutoff=threshold):
            return True

        # 3) fuzzy para expressões multi-palavra (janelas deslizantes)
        kw_tokens = kw.split()
        if len(kw_tokens) > 1:
            for i in range(len(tokens) - len(kw_tokens) + 1):
                seq = " ".join(tokens[i:i + len(kw_tokens)])
                if difflib.SequenceMatcher(None, seq, kw).ratio() >= threshold:
                    return True
    return False

# =============================
# Avaliação
# =============================

def evaluate_arguments(case_id: Any, side: str, user_text: str,
                       df_principios: pd.DataFrame, threshold: float = 0.80) -> Dict[str, Any]:
    """
    Retorna:
      - score: soma dos pesos dos princípios identificados
      - matched: lista de itens identificados
      - recommended: lista de itens relevantes não mencionados
      - counterarguments: itens do lado oposto (para preparar réplica)
    """
    case_str = str(case_id)
    side_norm = normalize_text(side)

    df_case_all = df_principios[df_principios["case_id"].astype(str) == case_str]
    df_case = df_case_all[df_case_all["side"].str.casefold().apply(normalize_text) == side_norm]

    matched: List[Dict[str, Any]] = []
    recommended: List[Dict[str, Any]] = []
    score = 0

    # evita recalcular match para o mesmo índice
    found_cache: Dict[int, bool] = {}

    for idx, row in df_case.iterrows():
        found = match_by_keywords(user_text, row["keywords_list"], threshold=threshold)
        found_cache[idx] = found
        if found:
            w = int(row.get("weight", 1))
            score += w
            matched.append({
                "principle": row["principle"],
                "article": row["article"],
                "weight": w,
                "matched_keyword_sample": ";".join(row["keywords_list"][:2])
            })

    for idx, row in df_case.iterrows():
        if not found_cache.get(idx, False):
            recommended.append({
                "principle": row["principle"],
                "article": row["article"],
                "weight": int(row.get("weight", 1)),
                "keywords": row["keywords_list"]
            })

    # contra-argumentos: tudo do outro lado
    df_other_side = df_case_all[df_case_all["side"].str.casefold().apply(normalize_text) != side_norm]
    counterarguments = [{
        "principle": r["principle"],
        "article": r["article"],
        "weight": int(r.get("weight", 1)),
        "keywords": r["keywords_list"]
    } for _, r in df_other_side.iterrows()]

    return {
        "score": score,
        "matched": matched,
        "recommended": recommended,
        "counterarguments": counterarguments
    }
