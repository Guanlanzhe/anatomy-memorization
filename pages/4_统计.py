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