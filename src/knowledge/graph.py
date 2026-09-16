"""
从 terms.json 和 morphemes.json 构建节点-边结构，供 Streamlit 渲染。
"""

from src.knowledge.loader import load_terms, load_morphemes


def build_graph(terms=None, morphemes=None):
    """
    返回 (nodes, edges)。
    nodes: [{"id": ..., "label": ..., "type": "term"|"morpheme"}]
    edges: [{"source": ..., "target": ...}]
    """
    if terms is None:
        terms = load_terms()
    if morphemes is None:
        morphemes = load_morphemes()

    nodes = []
    edges = []
    seen_nodes = set()

    for t in terms:
        tid = f"term:{t['id']}"
        if tid not in seen_nodes:
            nodes.append({
                "id": tid,
                "label": t["english"],
                "type": "term",
                "chinese": t.get("chinese", ""),
                "chapter": t.get("chapter", ""),
            })
            seen_nodes.add(tid)

        for m_id in t.get("morphemes", []):
            mid = f"morph:{m_id}"
            if mid not in seen_nodes:
                m = morphemes.get(m_id, {})
                nodes.append({
                    "id": mid,
                    "label": m_id,
                    "type": "morpheme",
                    "meaning": m.get("meaning", ""),
                    "chinese": m.get("chinese", ""),
                })
                seen_nodes.add(mid)

            edges.append({
                "source": mid,
                "target": tid,
                "relation": "composes",
            })

    return nodes, edges