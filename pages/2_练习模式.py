import sys
import random
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="练习模式", page_icon="📝", layout="wide")

from src.ui import load_style
load_style()

from src.knowledge.loader import get_chapters, get_terms_by_chapter
from src.learning.question import (
    generate_questions_for_term,
    ALL_MODES,
)
from src.learning.scheduler import get_or_create_card, review_card
from src.supabase_client import get_current_user_id, get_supabase

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


# ============ 进度存取 ============
def get_progress(chapter: str) -> int:
    """拿用户在该章节的进度索引。未登录或没记录返回 0。"""
    user_id = get_current_user_id()
    if not user_id:
        return 0
    sb = get_supabase()
    try:
        res = sb.table("user_progress").select("last_question_index").eq("user_id", user_id).eq("chapter", chapter).execute()
        if res.data:
            return int(res.data[0]["last_question_index"])
    except Exception:
        pass
    return 0


def set_progress(chapter: str, index: int):
    """保存用户在该章节的进度索引。"""
    user_id = get_current_user_id()
    if not user_id:
        return
    sb = get_supabase()
    try:
        sb.table("user_progress").upsert({
            "user_id": user_id,
            "chapter": chapter,
            "last_question_index": int(index),
        }).execute()
    except Exception:
        pass


# ============ 初始化状态 ============
if "started" not in st.session_state:
    st.session_state.started = False
    st.session_state.questions = []
    st.session_state.current = 0
    st.session_state.correct_count = 0
    st.session_state.answered = False
    st.session_state.last_correct = None
    st.session_state.active_chapter = None


# ============ 阶段 1：设置 ============
if not st.session_state.started:

    # 第一步：章节
    st.subheader("第一步：选择章节")
    chapters = st.multiselect(
        "章节",
        get_chapters(),
        default=[],
        label_visibility="collapsed",
        key="ch_select",
    )

    if not chapters:
        st.info("请选择至少一个章节。")
        st.stop()

    # 收集该章节所有术语（保持原始顺序）
    all_terms = []
    for c in chapters:
        all_terms.extend(get_terms_by_chapter(c))

    # 第二步：术语选择模式
    st.subheader("第二步：选择术语")

    mode = st.radio(
        "选择模式",
        ["手动选择", "顺序选择", "随机选择", "未做选择"],
        horizontal=True,
        label_visibility="collapsed",
        key="term_mode",
    )

    term_ids = []

    # -------- 模式 1：手动选择 --------
    if mode == "手动选择":
        col1, col2 = st.columns([1, 5])
        with col1:
            if st.button("全选", key="sel_all"):
                st.session_state["_manual_all"] = True
            if st.button("清空", key="clr_all"):
                st.session_state["_manual_all"] = False

        if st.session_state.get("_manual_all") is True:
            default_ids = [t["id"] for t in all_terms]
        elif st.session_state.get("_manual_all") is False:
            default_ids = []
        else:
            default_ids = [t["id"] for t in all_terms]

        term_ids = st.multiselect(
            "术语",
            [t["id"] for t in all_terms],
            default=default_ids,
            format_func=lambda x: next(
                (f"{t['english']} · {t['chinese']}" for t in all_terms if t["id"] == x),
                x,
            ),
            label_visibility="collapsed",
            key="manual_terms",
        )

    # -------- 模式 2：顺序选择 --------
    elif mode == "顺序选择":
        if len(chapters) != 1:
            st.warning("顺序选择只支持单个章节，请只选一个章节。")
            st.stop()

        chapter = chapters[0]
        progress = get_progress(chapter)

        if progress >= len(all_terms):
            st.success(f"🎉 你已经做完了「{chapter}」全部 {len(all_terms)} 道题！")
            if st.button("从头开始"):
                set_progress(chapter, 0)
                st.rerun()
            st.stop()

        st.info(f"当前章节「{chapter}」共 {len(all_terms)} 道题，你上次做到第 **{progress + 1}** 题。")

        start_from = st.number_input(
            "从第几题开始",
            min_value=1,
            max_value=len(all_terms),
            value=progress + 1,
            step=1,
        )
        st.session_state["_seq_start"] = start_from - 1
        term_ids = [t["id"] for t in all_terms]

    # -------- 模式 3：随机选择 --------
    elif mode == "随机选择":
        st.caption("从所选章节里随机抽取 N 道题。")
        n = st.number_input(
            "抽取数量",
            min_value=1,
            max_value=len(all_terms),
            value=min(20, len(all_terms)),
            step=1,
        )
        st.session_state["_rand_n"] = int(n)
        term_ids = [t["id"] for t in all_terms]

    # -------- 模式 4：未做选择 --------
    elif mode == "未做选择":
        st.caption("只筛选「从未做过」的题。选择题型后实时更新。")

        # 先选题型（因为未做判定依赖题型）
        st.markdown("**先选择题型：**")
        modes_for_filter = st.multiselect(
            "题型",
            ALL_MODES,
            default=["meaning-to-term", "term-to-meaning"],
            format_func=lambda x: MODE_LABELS.get(x, x),
            label_visibility="collapsed",
            key="undone_modes",
        )

        if not modes_for_filter:
            st.warning("请至少选择一个题型。")
            st.stop()

        # 查当前用户已做过的卡片
        user_id = get_current_user_id()
        done_card_ids = set()
        if user_id:
            sb = get_supabase()
            try:
                res = sb.table("learning_state").select("card_id").eq("user_id", user_id).execute()
                done_card_ids = {r["card_id"] for r in res.data}
            except Exception:
                pass

        # 筛选未做过的 term
        undone_terms = []
        for t in all_terms:
            # 只要该 term 对应题型下有一条"没做过"，就算未做
            has_undone = False
            for m in modes_for_filter:
                card_id = f"{t['id']}:{m}"
                if card_id not in done_card_ids:
                    has_undone = True
                    break
            if has_undone:
                undone_terms.append(t)

        st.info(f"「{'+'.join(chapters)}」里，所选题型下未做过的术语：**{len(undone_terms)}** 个。")

        if not undone_terms:
            st.success("🎉 所选题型下没有未做过的术语。")
            st.stop()

        term_ids = [t["id"] for t in undone_terms]
        st.session_state["_undone_modes"] = modes_for_filter

    # 第三步：题型（顺序/随机/手动模式显示）
    if mode in ("手动选择", "顺序选择", "随机选择"):
        st.subheader("第三步：选择题型")
        modes = st.multiselect(
            "题型",
            ALL_MODES,
            default=["meaning-to-term", "term-to-meaning"],
            format_func=lambda x: MODE_LABELS.get(x, x),
            label_visibility="collapsed",
            key="main_modes",
        )
    else:
        # 未做模式已经在上面选过了
        modes = st.session_state.get("_undone_modes", [])

    # 生成题目
    st.divider()

    if st.button("开始练习", type="primary"):
        if not term_ids or not modes:
            st.warning("请至少选择一个术语和一个题型。")
            st.stop()

        # 生成题目（顺序：按 term_ids 顺序 + 每个 term 内按 modes 顺序）
        all_qs = []
        for tid in term_ids:
            all_qs.extend(generate_questions_for_term(tid, modes))

        # 处理不同模式
        if mode == "顺序选择":
            # 截取从起始索引开始
            chapter = chapters[0]
            start_idx = st.session_state.get("_seq_start", 0)
            # 找 start_idx 对应的 term 在 all_qs 里的位置
            start_tid = all_terms[start_idx]["id"]
            # 过滤到 start_tid 之后的题目
            idx_in_qs = 0
            for i, q in enumerate(all_qs):
                if q["termId"] == start_tid:
                    idx_in_qs = i
                    break
            all_qs = all_qs[idx_in_qs:]
            st.session_state.active_chapter = chapter

        elif mode == "随机选择":
            n = st.session_state.get("_rand_n", 20)
            all_qs = random.sample(all_qs, min(n, len(all_qs)))

        # 手动选择、未做选择：不打乱，保持顺序

        if not all_qs:
            st.warning("没有生成任何题目。")
            st.stop()

        st.session_state.questions = all_qs
        st.session_state.current = 0
        st.session_state.correct_count = 0
        st.session_state.answered = False
        st.session_state.started = True
        st.rerun()


# ============ 阶段 2：答题 ============
else:
    qs = st.session_state.questions
    i = st.session_state.current

    if i >= len(qs):
        st.success(f"🎉 完成！共 {len(qs)} 题，正确 {st.session_state.correct_count} 题，"
                   f"正确率 {round(st.session_state.correct_count / len(qs) * 100)}%")

        # 顺序模式下，保存进度
        if st.session_state.active_chapter:
            new_idx = get_progress(st.session_state.active_chapter) + len(qs)
            set_progress(st.session_state.active_chapter, new_idx)

        if st.button("再来一轮"):
            st.session_state.started = False
            st.session_state.current = 0
            st.session_state.active_chapter = None
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

    with st.form(key=f"answer_form_{i}", clear_on_submit=False):
        answer = st.text_input(
            "你的答案",
            key=f"answer_{i}",
            disabled=st.session_state.answered,
            placeholder="输入答案后按回车或点击提交",
        )
        submit = st.form_submit_button(
            "提交",
            type="primary",
            disabled=st.session_state.answered,
        )

    if submit and answer:
        st.session_state.answered = True
        correct = answer.strip().lower() in [e.lower() for e in q["expected"]]

        if correct:
            st.session_state.correct_count += 1
            st.success("✓ 正确")
        else:
            st.error(f"✗ 错误，参考答案：{q['display']}")

        card_id = q["id"]
        get_or_create_card(card_id)
        review_card(card_id, rating="good" if correct else "again", correct=correct)

        # 答对 → 直接跳
        if correct:
            st.session_state.current += 1
            st.session_state.answered = False
            st.rerun()

    # 答错 → 等用户手动点
    if st.session_state.answered:
        st.divider()
        if st.button("下一题 →", type="primary", key=f"next_{i}"):
            st.session_state.current += 1
            st.session_state.answered = False
            st.rerun()
