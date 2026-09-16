"""
根据选中的术语和题型，动态生成题目。
"""

from src.knowledge.loader import load_terms, load_morphemes

ALL_MODES = [
    "meaning-to-term",
    "term-to-meaning",
    "morpheme-meaning",
    "decomposition",
    "construction",
]


def generate_questions_for_term(term_id, modes=None):
    if modes is None:
        modes = ALL_MODES

    terms = load_terms()
    morphemes = load_morphemes()

    term = next((t for t in terms if t["id"] == term_id), None)
    if not term:
        return []

    questions = []
    has = lambda m: m in modes

    if has("meaning-to-term"):
        questions.append({
            "id": f"{term['id']}:meaning-to-term",
            "termId": term["id"],
            "mode": "meaning-to-term",
            "prompt": f"「{term['chinese']}」的英文是？",
            "expected": [term["english"]],
            "display": term["english"],
        })

    if has("term-to-meaning"):
        questions.append({
            "id": f"{term['id']}:term-to-meaning",
            "termId": term["id"],
            "mode": "term-to-meaning",
            "prompt": f"「{term['english']}」的中文是？",
            "expected": [term["chinese"]],
            "display": term["chinese"],
        })

    if has("morpheme-meaning"):
        for m_id in term.get("morphemes", []):
            m = morphemes.get(m_id)
            if not m:
                continue
            if m.get("meaning", "").startswith("("):
                continue

            expected = [m["meaning"]]
            if m.get("chinese"):
                expected.append(m["chinese"])

            questions.append({
                "id": f"{m_id}:meaning",
                "termId": term["id"],
                "mode": "morpheme-meaning",
                "prompt": f"「{m_id}」这个词根是什么意思？（中英文都接受）",
                "expected": expected,
                "display": f"{m['meaning']} / {m.get('chinese', '')}",
            })

    if has("decomposition") and term.get("morphemes"):
        questions.append({
            "id": f"{term['id']}:decomposition",
            "termId": term["id"],
            "mode": "decomposition",
            "prompt": f"把「{term['english']}」拆成词根（用 + 连接，按顺序）",
            "expected": [" + ".join(term["morphemes"])],
            "display": " + ".join(term["morphemes"]),
        })

    if has("construction") and len(term.get("morphemes", [])) >= 2:
        parts = []
        for m_id in term["morphemes"]:
            m = morphemes.get(m_id, {})
            parts.append(f"{m_id} ({m.get('chinese') or m.get('meaning', '?')})")
        questions.append({
            "id": f"{term['id']}:construction",
            "termId": term["id"],
            "mode": "construction",
            "prompt": "把下面几个词根拼成解剖学术语：\n" + " + ".join(parts),
            "expected": [term["english"]],
            "display": term["english"],
        })

    return questions


def generate_questions(term_ids, modes=None):
    import random
    all_q = []
    for tid in term_ids:
        all_q.extend(generate_questions_for_term(tid, modes))
    random.shuffle(all_q)
    return all_q