import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

st.set_page_config(page_title="学习统计", page_icon="📊", layout="wide")

from src.ui import load_style
load_style()

from src.learning.scheduler import get_card_stats

st.title("📊 学习统计")

if not st.session_state.get("user_id"):
    st.info("💡 未登录。登录后可以看到自己的学习统计。")
    st.page_link("主页.py", label="← 去主页登录", icon="🏠")

from src.supabase_client import get_user_threshold, set_user_threshold

# ============ 复习阈值设置 ============
st.subheader("⚙️ 复习阈值设置")

current_threshold = get_user_threshold()

new_threshold_pct = st.slider(
    "累计正确率低于该值的题目，会被归入「需复习」",
    min_value=0,
    max_value=100,
    value=int(round(current_threshold * 100)),
    step=1,
    format="%d%%",
)

new_threshold = new_threshold_pct / 100.0

# 显示为百分比
st.caption(f"当前阈值：**{new_threshold_pct}%**（低于此值的题会进入复习模式）")

if abs(new_threshold - current_threshold) > 1e-6:
    if st.button("💾 保存设置", type="primary"):
        set_user_threshold(new_threshold)
        st.success(f"已保存：阈值设为 {new_threshold_pct}%")
        st.rerun()

st.divider()

stats = get_card_stats()

MODE_LABELS = {
    "meaning-to-term": "中文 → 英文",
    "term-to-meaning": "英文 → 中文",
    "morpheme-meaning": "词根含义",
    "decomposition": "拆解词根",
    "construction": "拼装术语",
}

# ============ 概览卡片 ============
col1, col2, col3 = st.columns(3)
col1.metric("🔴 需复习", stats["need_review"])
col2.metric("🟢 已掌握", stats["mastered"])
col3.metric("⚪ 未做", stats["not_done"])

st.write("")

col1, col2, col3 = st.columns(3)
col1.metric("做题次数", stats["total_attempts"])
col2.metric("总正确率", f"{stats['overall_rate']*100:.1f}%")
col3.metric(
    "已做过",
    stats["need_review"] + stats["mastered"],
)

st.divider()

# ============ 分题型正确率 ============
st.subheader("分题型正确率")

for mode, m in stats["by_mode"].items():
    label = MODE_LABELS.get(mode, mode)
    if m["attempts"] == 0:
        st.write(f"**{label}**　—　（未做过）")
    else:
        st.write(
            f"**{label}**　—　{m['correct']} / {m['attempts']} = "
            f"**{m['rate']*100:.1f}%**"
        )

st.divider()

st.caption("「需复习」= 做过的题里，累计正确率 < 50%。去「复习模式」专门练这些题。")
