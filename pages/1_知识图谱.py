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
        st.stop()

    # ===== 学习状态筛选 =====
    from src.supabase_client import get_current_user_id, get_supabase, get_user_threshold

    user_id = get_current_user_id()
    threshold = get_user_threshold()

    # 从 Supabase 拿该用户所有做过题的状态
    # 每个 term 的状态 = "该 term 下所有做过的卡片"的聚合
    term_status = {}  # term_id -> "done_need_review" | "done_mastered" | "undone"

    if user_id:
        sb = get_supabase()
        try:
            res = sb.table("learning_state").select("card_id, total_attempts, total_correct").eq("user_id", user_id).execute()
            # 按 term_id 聚合
            term_attempts = {}
            term_correct = {}
            for row in res.data:
                cid = row["card_id"]
                # card_id 形如 term_id:mode
                parts = cid.split(":")
                if len(parts) < 2:
                    continue
                tid = parts[0]
                term_attempts[tid] = term_attempts.get(tid, 0) + row.get("total_attempts", 0)
                term_correct[tid] = term_correct.get(tid, 0) + row.get("total_correct", 0)

            for t in terms_for_view:
                tid = t["id"]
                a = term_attempts.get(tid, 0)
                c = term_correct.get(tid, 0)
                if a == 0:
                    term_status[tid] = "undone"
                elif c / a < threshold:
                    term_status[tid] = "need_review"
                else:
                    term_status[tid] = "mastered"
        except Exception as e:
            st.warning(f"读学习状态失败：{e}")

    # 未登录时都算未做
    for t in terms_for_view:
        if t["id"] not in term_status:
            term_status[t["id"]] = "undone"

    # 筛选控件
    status_filter = st.multiselect(
        "筛选学习状态",
        ["未做", "需复习", "已掌握"],
        default=["未做", "需复习", "已掌握"],
        key="table_status_filter",
    )

    status_map = {
        "undone": "未做",
        "need_review": "需复习",
        "mastered": "已掌握",
    }

    allowed = set()
    if "未做" in status_filter:
        allowed.add("undone")
    if "需复习" in status_filter:
        allowed.add("need_review")
    if "已掌握" in status_filter:
        allowed.add("mastered")

    # 过滤后的术语
    filtered_terms = [t for t in terms_for_view if term_status[t["id"]] in allowed]

    # ===== 在结果中搜索 =====
    inner_query = st.text_input("在结果中搜索", "", key="table_inner_search")

    # 生成表格行
    rows = []
    for t in filtered_terms:
        en = t["english"].replace("_", " ")
        zh = t.get("chinese", "")
        st_label = status_map[term_status[t["id"]]]
        rows.append({"中文": zh, "英文": en, "状态": st_label})

    if inner_query.strip():
        q = inner_query.strip().lower()
        rows = [r for r in rows if q in r["中文"].lower() or q in r["英文"].lower()]

    # 按英文排序（A-Z）
    rows.sort(key=lambda r: r["英文"].lower())

    st.caption(f"共 {len(rows)} 条")

    # 显示表格
    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        height=min(700, 40 + len(rows) * 35),
    )

    # 下载
    csv = "中文,英文,状态\n" + "\n".join(
        f"{r['中文']},{r['英文']},{r['状态']}" for r in rows
    )
    st.download_button(
        "⬇️ 下载 CSV",
        data=csv.encode("utf-8-sig"),
        file_name="anatomy_terms.csv",
        mime="text/csv",
        key="download_csv",
    )
