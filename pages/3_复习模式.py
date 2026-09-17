import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="复习模式", page_icon="🔁", layout="wide")

from src.ui import load_style
load_style()

from src.knowledge.loader import load_terms, get_chapters
from src.learning.scheduler import (
    get_need_review_cards,
    get_or_create_card,
    review_card,
)
from src.learning.question import generate_questions_for_term, ALL_MODES

st.title("🔁 复习模式")
from src.supabase_client import get_user_threshold
_thr = get_user_threshold()
_threshold_pct = int(round(get_user_threshold() * 100))
st.caption(f"这里收录「做过的题里，累计正确率 < {_threshold_pct}%」的卡片。答对后会重新评估。")

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


# ============ 拿需复习的卡片 ============
need_review_ids = get_need_review_cards()

if not need_review_ids:
    st.success("🎉 没有需要复习的卡片。去「练习模式」做一些题吧。")
    st.stop()


# ============ 从 cardId 反推 termId ============
# cardId 形如：
#   "sternocleidomastoid:meaning-to-term"   → term 类，前缀是 term id
#   "sterno:meaning"                         → morpheme 类，前缀是 morpheme id
# 对 morpheme 类，我们需要知道它属于哪个 term（可能有多个）

all_terms = load_terms()
term_by_id = {t["id"]: t for t in all_terms}

# 收集需要复习的 term ids（仅 term 类 cardId）
term_ids_to_review = set()
morpheme_ids_to_review = set()

for cid in need_review_ids:
    parts = cid.split(":")
    if len(parts) != 2:
        continue
    name, mode = parts
    if mode == "meaning":
        morpheme_ids_to_review.add(name)
    else:
        term_ids_to_review.add(name)

# morpheme 类的卡片，需要找出所有含该 morpheme 的 term
for m_id in morpheme_ids_to_review:
    for t in all_terms:
        if m_id in t.get("morphemes", []):
            term_ids_to_review.add(t["id"])

# 现在只需要对这些 term 生成题目
candidate_questions = []
for tid in term_ids_to_review:
    candidate_questions.extend(generate_questions_for_term(tid, ALL_MODES))

# 过滤：只保留需复习的 cardId 对应的题目
need_set = set(need_review_ids)
review_qs_all = [q for q in candidate_questions if q["id"] in need_set]

if not review_qs_all:
    st.warning("需复习的卡片找不到对应题目（可能数据变了）。")
    st.stop()


# ============ 初始化状态 ============
if "review_started" not in st.session_state:
    st.session_state.review_started = False
    st.session_state.review_questions = []
    st.session_state.review_current = 0
    st.session_state.review_correct_count = 0
    st.session_state.review_answered = False


# ============ 设置阶段 ============
if not st.session_state.review_started:
    st.info(f"当前有 **{len(review_qs_all)}** 道题需要复习。")

    # 第一步：章节
    st.subheader("第一步：选择章节")
    chapters = st.multiselect(
        "章节",
        get_chapters(),
        default=get_chapters(),
        label_visibility="collapsed",
        key="review_chapters",
    )

    if not chapters:
        st.warning("请至少选择一个章节。")
        st.stop()

    chapter_terms = [t for t in all_terms if t.get("chapter") in chapters]
    term_ids_in_chapters = {t["id"] for t in chapter_terms}

    candidates = [q for q in review_qs_all if q["termId"] in term_ids_in_chapters]

    # 第二步：术语
    st.subheader("第二步：选择术语")

    unique_terms = {}
    for q in candidates:
        tid = q["termId"]
        if tid not in unique_terms and tid in term_by_id:
            unique_terms[tid] = term_by_id[tid]

    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("全选", key="review_select_all_btn"):
            st.session_state["_review_select_all_flag"] = "all"
        if st.button("清空", key="review_clear_all_btn"):
            st.session_state["_review_select_all_flag"] = "none"

    flag = st.session_state.get("_review_select_all_flag")
    if flag == "none":
        default_ids = []
    else:
        default_ids = list(unique_terms.keys())

    selected_term_ids = st.multiselect(
        "术语",
        list(unique_terms.keys()),
        default=default_ids,
        format_func=lambda x: (
            f"{unique_terms[x]['english']} · {unique_terms[x]['chinese']}"
            if x in unique_terms else x
        ),
        label_visibility="collapsed",
        key="review_terms_select",
    )

    # 第三步：题型
    st.subheader("第三步：选择题型")

    available_modes = []
    for q in candidates:
        if q["mode"] not in available_modes:
            available_modes.append(q["mode"])

    if not available_modes:
        available_modes = ALL_MODES

    selected_modes = st.multiselect(
        "题型",
        available_modes,
        default=available_modes,
        format_func=lambda x: MODE_LABELS.get(x, x),
        label_visibility="collapsed",
        key="review_modes_select",
    )

    # 预览
    filtered = [
        q for q in candidates
        if q["termId"] in selected_term_ids and q["mode"] in selected_modes
    ]

    st.divider()
    st.caption(f"筛选后共有 **{len(filtered)}** 道题。")

    if st.button("开始复习", type="primary", key="review_start_btn"):
        if not filtered:
            st.warning("筛选后没有题目。")
        else:
            st.session_state.review_questions = filtered
            st.session_state.review_current = 0
            st.session_state.review_correct_count = 0
            st.session_state.review_answered = False
            st.session_state.review_started = True
            st.rerun()


# ============ 答题阶段 ============
else:
    qs = st.session_state.review_questions
    i = st.session_state.review_current

    if i >= len(qs):
        st.success(
            f"🎉 复习完成！共 {len(qs)} 题，正确 {st.session_state.review_correct_count} 题。"
        )
        if st.button("再复习一轮", key="review_restart"):
            st.session_state.review_started = False
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

    with st.form(key=f"review_form_{i}", clear_on_submit=False):
        answer = st.text_input(
            "你的答案",
            key=f"review_answer_{i}",
            disabled=st.session_state.review_answered,
        )
        submit = st.form_submit_button(
            "提交",
            type="primary",
            disabled=st.session_state.review_answered,
        )

    if submit and answer:
        st.session_state.review_answered = True
        correct = answer.strip().lower() in [e.lower() for e in q["expected"]]
    
        if correct:
            st.session_state.review_correct_count += 1
            st.success("✓ 正确")
        else:
            st.error(f"✗ 错误，参考答案：{q['display']}")
    
        get_or_create_card(q["id"])
        review_card(q["id"], rating="good" if correct else "again", correct=correct)
    
        # 答对 → 立即跳下一题
        if correct:
            st.session_state.review_current += 1
            st.session_state.review_answered = False
            st.rerun()
    
    # 答错 → 显示"下一题"按钮，等用户手动确认
    if st.session_state.review_answered:
        st.divider()
        if st.button("下一题 →", type="primary", key=f"review_next_{i}"):
            st.session_state.review_current += 1
            st.session_state.review_answered = False
            st.rerun()
