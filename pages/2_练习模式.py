import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="练习模式", page_icon="📝", layout="wide")

from src.ui import load_style
load_style()

from src.knowledge.loader import get_chapters, get_terms_by_chapter
from src.learning.question import generate_questions, ALL_MODES
from src.learning.scheduler import get_or_create_card, review_card

st.title("📝 练习模式")

if not st.session_state.get("user_id"):
    st.warning("⚠️ 你当前未登录，做题记录不会被保存。")
    st.page_link("主页.py", label="← 去主页登录", icon="🏠")


MODE_LABELS = {
    "meaning-to-term": "中文 → 英文",
    "term-to-meaning": "英文 → 中文",
    "morpheme-meaning": "词根含义",
    "decomposition": "拆解词根",
    "construction": "拼装术语",
}


# ============ 初始化状态 ============
if "started" not in st.session_state:
    st.session_state.started = False
    st.session_state.questions = []
    st.session_state.current = 0
    st.session_state.correct_count = 0
    st.session_state.answered = False
    st.session_state.last_correct = None


# ============ 阶段 1：设置 ============
if not st.session_state.started:
    with st.container():
        st.subheader("第一步：选择章节")
        chapters = st.multiselect(
            "章节",
            get_chapters(),
            default=get_chapters(),
            label_visibility="collapsed",
        )

    if chapters:
        terms = []
        for c in chapters:
            terms.extend(get_terms_by_chapter(c))

        with st.container():
            st.subheader("第二步：选择术语")
            col1, col2 = st.columns([1, 5])
            with col1:
                if st.button("全选"):
                    st.session_state["_select_all_terms"] = True
                if st.button("清空"):
                    st.session_state["_select_all_terms"] = False

            default_ids = [t["id"] for t in terms[:20]]
            if st.session_state.get("_select_all_terms") is True:
                default_ids = [t["id"] for t in terms]
            elif st.session_state.get("_select_all_terms") is False:
                default_ids = []

            term_ids = st.multiselect(
                "术语",
                [t["id"] for t in terms],
                default=default_ids,
                format_func=lambda x: next(
                    (f"{t['english']} · {t['chinese']}" for t in terms if t["id"] == x),
                    x,
                ),
                label_visibility="collapsed",
            )

        with st.container():
            st.subheader("第三步：选择题型")
            modes = st.multiselect(
                "题型",
                ALL_MODES,
                default=["meaning-to-term", "term-to-meaning"],
                format_func=lambda x: MODE_LABELS.get(x, x),
                label_visibility="collapsed",
            )

        st.divider()
        if st.button("开始练习", type="primary"):
            if term_ids and modes:
                qs = generate_questions(term_ids, modes)
                if not qs:
                    st.warning("没有生成任何题目。")
                else:
                    st.session_state.questions = qs
                    st.session_state.current = 0
                    st.session_state.correct_count = 0
                    st.session_state.answered = False
                    st.session_state.started = True
                    st.rerun()
            else:
                st.warning("请至少选择一个术语和一个题型。")


# ============ 阶段 2：答题 ============
else:
    qs = st.session_state.questions
    i = st.session_state.current

    if i >= len(qs):
        st.success(f"🎉 完成！共 {len(qs)} 题，正确 {st.session_state.correct_count} 题，"
                   f"正确率 {round(st.session_state.correct_count / len(qs) * 100)}%")
        if st.button("再来一轮"):
            st.session_state.started = False
            st.session_state.current = 0
            st.rerun()
        st.stop()

    q = qs[i]

    st.progress(i / len(qs))
    col1, col2 = st.columns([1, 5])
    with col1:
        st.markdown(f"**[{MODE_LABELS.get(q['mode'], q['mode'])}]**")
    with col2:
        st.markdown(f"**{i + 1} / {len(qs)}**")

    st.markdown(f"### {q['prompt']}")

    answer = st.text_input(
        "你的答案",
        key=f"answer_{i}",
        disabled=st.session_state.answered,
        placeholder="输入答案后按回车或点击提交",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        submit = st.button("提交", type="primary", disabled=st.session_state.answered)

    if submit and answer:
        st.session_state.answered = True
        correct = answer.strip().lower() in [e.lower() for e in q["expected"]]
        st.session_state.last_correct = correct

        if correct:
            st.session_state.correct_count += 1
            st.success("✓ 正确")
        else:
            st.error(f"✗ 错误，参考答案：{q['display']}")

        card_id = q["id"]
        get_or_create_card(card_id)
        review_card(card_id, rating="good" if correct else "again", correct=correct)

    if st.session_state.answered:
        st.divider()
        if st.button("下一题 →", type="primary"):
            st.session_state.current += 1
            st.session_state.answered = False
            st.rerun()