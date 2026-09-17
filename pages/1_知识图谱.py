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

# ============ 顶层 tab：图谱 / 表格 ============
tab_graph, tab_table = st.tabs(["🕸 图谱", "📋 表格"])


# ============================================================
# 通用：选章节或词根
# ============================================================
def pick_filter():
    """返回 (mode, value, terms_list)。
    mode: 'chapter' | 'morpheme'
    value: 章节名 或 词根 id
    terms_list: 过滤后的术语列表
    """
    mode = st.radio(
        "模式",
        ["按章节", "按词根"],
        horizontal=True,
        key="filter_mode",
    )

    terms_for_view = []

    if mode == "按章节":
        chapters = get_chapters()
        chapter = st.selectbox("选择章节", chapters, key="chapter_select")
        terms_for_view = get_terms_by_chapter(chapter)
        return "chapter", chapter, terms_for_view

    else:
        morphemes = load_morphemes()

        query = st.text_input("搜索词根（支持词根 / 英文 / 中文）", "", key="morph_query")

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
            return "morpheme", None, []

        options = sorted(filtered.keys())
        morpheme_id = st.selectbox(
            "选择词根",
            options,
            format_func=lambda x: f"{x} · {filtered[x].get('chinese', '')} · {filtered[x].get('meaning', '')}",
            key="morph_select",
        )

        all_terms = load_terms()
        terms_for_view = [t for t in all_terms if morpheme_id in t.get("morphemes", [])]
        st.caption(f"找到 {len(terms_for_view)} 个包含「{morpheme_id}」的术语")
        return "morpheme", morpheme_id, terms_for_view


# ============================================================
# Tab 1：图谱
# ============================================================
with tab_graph:
    col_a, col_b = st.columns([1, 3])
    with col_a:
        mode = st.radio(
            "显示模式",
            ["按章节", "按词根"],
            horizontal=False,
            key="graph_filter_mode",
        )

    terms_for_view = []

    with col_b:
        if mode == "按章节":
            chapters = get_chapters()
            chapter = st.selectbox("选择章节", chapters, key="graph_chapter")
            terms_for_view = get_terms_by_chapter(chapter)

        else:
            morphemes = load_morphemes()
            query = st.text_input("搜索词根（支持词根 / 英文 / 中文）", "", key="graph_morph_query")

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
                key="graph_morph_select",
            )

            all_terms = load_terms()
            terms_for_view = [t for t in all_terms if morpheme_id in t.get("morphemes", [])]
            st.caption(f"找到 {len(terms_for_view)} 个包含「{morpheme_id}」的术语")

    if not terms_for_view:
        st.info("没有可显示的术语。")
    else:
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


# ============================================================
# Tab 2：表格
# ============================================================
with tab_table:
    mode = st.radio(
        "显示模式",
        ["按章节", "按词根"],
        horizontal=True,
        key="table_filter_mode",
    )

    terms_for_view = []

    if mode == "按章节":
        chapters = get_chapters()
        chapter = st.selectbox("选择章节", chapters, key="table_chapter")
        terms_for_view = get_terms_by_chapter(chapter)

    else:
        morphemes = load_morphemes()
        query = st.text_input("搜索词根（支持词根 / 英文 / 中文）", "", key="table_morph_query")

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
            key="table_morph_select",
        )

        all_terms = load_terms()
        terms_for_view = [t for t in all_terms if morpheme_id in t.get("morphemes", [])]
        st.caption(f"找到 {len(terms_for_view)} 个包含「{morpheme_id}」的术语")

    if not terms_for_view:
        st.info("没有可显示的术语。")
    else:
        # 搜索框（在表格内部再次过滤）
        inner_query = st.text_input("在结果中搜索", "", key="table_inner_search")

        rows = []
        for t in terms_for_view:
            en = t["english"].replace("_", " ")
            zh = t.get("chinese", "")
            rows.append({"中文": zh, "英文": en})

        if inner_query.strip():
            q = inner_query.strip().lower()
            rows = [r for r in rows if q in r["中文"].lower() or q in r["英文"].lower()]

        st.caption(f"共 {len(rows)} 条")

        # 显示为表格
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
            height=min(700, 40 + len(rows) * 35),
        )

        # 下载按钮
        import json as _json
        csv = "中文,英文\n" + "\n".join(f"{r['中文']},{r['英文']}" for r in rows)
        st.download_button(
            "⬇️ 下载 CSV",
            data=csv.encode("utf-8-sig"),
            file_name="anatomy_terms.csv",
            mime="text/csv",
            key="download_csv",
        )
