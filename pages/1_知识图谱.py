import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

st.set_page_config(page_title="知识图谱", page_icon="🕸", layout="wide")

from src.ui import load_style
load_style()

from src.knowledge.loader import (
    load_terms,
    load_morphemes,
    get_chapters,
    get_terms_by_chapter,
)
from src.knowledge.graph import build_graph

st.title("🕸 知识图谱")


# ============ 模式选择 ============
col_a, col_b = st.columns([1, 3])
with col_a:
    mode = st.radio("显示模式", ["按章节", "按词根"])

terms_for_view = []

with col_b:
    if mode == "按章节":
        chapters = get_chapters()
        chapter = st.selectbox("选择章节", chapters)
        terms_for_view = get_terms_by_chapter(chapter)

    else:
        morphemes = load_morphemes()

        query = st.text_input("搜索词根（支持词根 / 英文 / 中文）", "")

        q = query.strip().lower()
        if q:
            filtered = {
                k: v for k, v in morphemes.items()
                if q in k.lower()
                or q in v.get("meaning", "").lower()
                or q in v.get("chinese", "")
            }
        else:
            filtered = morphemes

        if not filtered:
            st.warning("没有匹配的词根")
            st.stop()

        options = sorted(filtered.keys())
        morpheme_id = st.selectbox(
            "选择词根",
            options,
            format_func=lambda x: f"{x} · {filtered[x].get('chinese', '')} · {filtered[x].get('meaning', '')}",
        )

        all_terms = load_terms()
        terms_for_view = [t for t in all_terms if morpheme_id in t.get("morphemes", [])]
        st.caption(f"找到 {len(terms_for_view)} 个包含「{morpheme_id}」的术语")


# ============ 建图 ============
if not terms_for_view:
    st.info("没有可显示的术语。")
    st.stop()

nodes_data, edges_data = build_graph(terms=terms_for_view)

nodes = []
edges = []

FONT_FACE = "Times New Roman, DengXian, 等线"

for n in nodes_data:
    if n["type"] == "term":
        color = "#4A90E2"
        size = 30
        en = n["label"].replace("_", " ")
        zh = n.get("chinese", "")
        label = en
        tooltip = f"【Term】{en}\n{zh}"
    else:
        color = "#F5A623"
        size = 24
        en = n["label"]
        zh = n.get("chinese", "")
        label = en
        tooltip = f"【Morpheme】{en}\n{zh}"

    nodes.append(Node(
        id=n["id"],
        label=label,
        size=size,
        color=color,
        title=tooltip,
        font={"size": 14, "face": FONT_FACE, "strokeWidth": 2, "strokeColor": "#ffffff"},
    ))

for e in edges_data:
    edges.append(Edge(source=e["source"], target=e["target"], color="#cccccc"))


# ============ 渲染 ============
config = Config(
    width="100%",
    height=700,
    directed=True,
    physics=True,
    hierarchical=False,
    nodeHighlightBehavior=True,
    highlightColor="#F7A7A6",
    collapsible=False,
    nodeSpacing=250,
    springLength=200,
    springConstant=0.05,
    damping=0.9,
    maxVelocity=50,
    minVelocity=1,
    timestep=0.5,
)

agraph(nodes=nodes, edges=edges, config=config)

st.caption(f"共 {len(nodes)} 个节点 · {len(edges)} 条边　🟠 Morpheme　🔵 Term")
st.caption("提示：鼠标悬停节点显示中英文详情。")


# ============ 术语明细 ============
with st.expander("术语明细", expanded=False):
    for t in terms_for_view:
        en = t["english"].replace("_", " ")
        zh = t.get("chinese", "")
        morphemes_str = " + ".join(t.get("morphemes", [])) or "（无）"
        st.markdown(f"**{en}**　·　{zh}　—　`{morphemes_str}`")