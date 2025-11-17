import pandas as pd
import re
import difflib
import unicodedata
from typing import List, Dict, Any


# =============================
# Normalização
# =============================

def _strip_accents(s: str) -> str:
    """Remove acentos de uma string."""
    if s is None:
        return ""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if not unicodedata.combining(c)
    )


def normalize_text(text: str) -> str:
    """Normaliza texto: minúsculas, sem acentos, só letras/números/espaço."""
    text = (text or "").casefold()
    text = _strip_accents(text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_tokens(text: str) -> List[str]:
    """Quebra o texto normalizado em tokens (palavras)."""
    return normalize_text(text).split()


# =============================
# Base de dados
# =============================

def _split_kws(s: str) -> List[str]:
    """Divide string de keywords usando ';' ou ',' e normaliza cada termo."""
    parts = re.split(r"[;,]", str(s or ""))
    parts = [p.strip() for p in parts if p.strip()]
    return [normalize_text(p) for p in parts]


def load_principios(path_or_buffer="data/principios.csv") -> pd.DataFrame:
    """
    Lê o CSV de princípios.

    Aceita tanto:
    - caminho de arquivo (str), quanto
    - objetos tipo UploadedFile (Streamlit) ou buffer similar.
    """
    df = pd.read_csv(path_or_buffer, dtype=str).fillna("")

    # Mantém a coluna weight como numérica (metadado, não usada no score)
    if "weight" in df.columns:
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce").fillna(1.0)
    else:
        df["weight"] = 1.0

    required = {
        "case_id", "case_title", "case_description", "side",
        "principle", "article", "weight", "keywords"
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltam colunas no CSV: {', '.join(sorted(missing))}")

    # keywords_list: combina keywords + principle + article, já normalizados
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
# Matching helpers
# =============================

def _keyword_matches(norm_text: str,
                     tokens: List[str],
                     kw: str,
                     threshold: float = 0.80) -> bool:
    """Verifica se UMA keyword casa com o texto do usuário."""
    if not kw:
        return False

    # 1) substring direta
    if kw in norm_text:
        return True

    # 2) fuzzy por tokens individuais
    if difflib.get_close_matches(kw, tokens, n=1, cutoff=threshold):
        return True

    # 3) fuzzy para expressões multi-palavra (janelas deslizantes)
    kw_tokens = kw.split()
    if len(kw_tokens) > 1 and len(tokens) >= len(kw_tokens):
        for i in range(len(tokens) - len(kw_tokens) + 1):
            seq = " ".join(tokens[i:i + len(kw_tokens)])
            if difflib.SequenceMatcher(None, seq, kw).ratio() >= threshold:
                return True

    return False


def match_by_keywords(user_text: str,
                      keywords_list: List[str],
                      threshold: float = 0.80) -> bool:
    """
    Retorna True se alguma keyword da lista casa com o texto do usuário.
    (Wrapper usando _keyword_matches).
    """
    norm = normalize_text(user_text)
    tokens = extract_tokens(user_text)

    for kw in keywords_list:
        if _keyword_matches(norm, tokens, kw, threshold):
            return True
    return False


# =============================
# Avaliação
# =============================

def evaluate_arguments(case_id: Any,
                       side: str,
                       user_text: str,
                       df_principios: pd.DataFrame,
                       threshold: float = 0.80) -> Dict[str, Any]:
    """
    Avalia a argumentação do usuário para um dado caso e lado.

    Regra de pontuação:
      - Considera todas as keywords do caso + lado.
      - Cada keyword vale o mesmo número de pontos.
      - Se todas forem identificadas, a pontuação total é 10 pontos.

    Retorna:
        - score: pontos obtidos (0 a 10)
        - max_score: pontos máximos possíveis (10, se houver keywords)
        - matched: lista de princípios encontrados (pelo menos uma keyword)
        - recommended: princípios não encontrados (nenhuma keyword)
        - counterarguments: princípios do lado oposto
    """
    case_str = str(case_id)
    side_norm = normalize_text(side)

    # Filtra o caso
    df_case_all = df_principios[
        df_principios["case_id"].astype(str) == case_str
    ]

    # Filtra pelo lado (acusacao/defesa)
    df_case = df_case_all[
        df_case_all["side"].astype(str).apply(normalize_text) == side_norm
    ]

    matched: List[Dict[str, Any]] = []
    recommended: List[Dict[str, Any]] = []

    # Se não houver linhas para esse caso/lado, nota máxima é 0
    if df_case.empty:
        counterarguments = []
        df_other_side = df_case_all[
            df_case_all["side"].astype(str).apply(normalize_text) != side_norm
        ]
        for _, r in df_other_side.iterrows():
            counterarguments.append({
                "principle": r["principle"],
                "article": r["article"],
                "weight": float(r.get("weight", 1.0)),
                "keywords": r["keywords_list"],
            })
        return {
            "score": 0.0,
            "max_score": 0.0,
            "matched": [],
            "recommended": [],
            "counterarguments": counterarguments,
        }

    # --------------------------
    # Construção da base de keywords
    # --------------------------
    # Lista de todas as keywords (normalizadas) para este caso/lado, sem duplicata
    all_keywords: List[str] = []
    for _, row in df_case.iterrows():
        for kw in row["keywords_list"]:
            if kw and kw not in all_keywords:
                all_keywords.append(kw)

    total_keywords = len(all_keywords)
    if total_keywords > 0:
        max_score = 10.0
        points_per_keyword = max_score / total_keywords
    else:
        max_score = 0.0
        points_per_keyword = 0.0

    # --------------------------
    # Matching por keyword
    # --------------------------
    norm_user = normalize_text(user_text)
    tokens_user = extract_tokens(user_text)

    matched_keywords = set()
    for kw in all_keywords:
        if _keyword_matches(norm_user, tokens_user, kw, threshold):
            matched_keywords.add(kw)

    # Pontuação total: keywords acertadas * valor por keyword
    score = points_per_keyword * len(matched_keywords)

    # --------------------------
    # Princípios "matched" e "recommended"
    # --------------------------
    found_cache: Dict[int, bool] = {}

    for idx, row in df_case.iterrows():
        row_kws = row["keywords_list"]
        found = any(kw in matched_keywords for kw in row_kws)
        found_cache[idx] = found
        if found:
            matched.append({
                "principle": row["principle"],
                "article": row["article"],
            })

    for idx, row in df_case.iterrows():
        if not found_cache.get(idx, False):
            recommended.append({
                "principle": row["principle"],
                "article": row["article"],
                "keywords": row["keywords_list"],
            })

    # --------------------------
    # Argumentos da parte contrária
    # --------------------------
    df_other_side = df_case_all[
        df_case_all["side"].astype(str).apply(normalize_text) != side_norm
    ]
    counterarguments = [
        {
            "principle": r["principle"],
            "article": r["article"],
            "weight": float(r.get("weight", 1.0)),
            "keywords": r["keywords_list"],
        }
        for _, r in df_other_side.iterrows()
    ]

    return {
        "score": float(score),
        "max_score": float(max_score),
        "matched": matched,
        "recommended": recommended,
        "counterarguments": counterarguments,
    }
