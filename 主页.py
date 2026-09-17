import sys
from pathlib import Path

# 把项目根目录加入 sys.path，保证能 import src
ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st

# ========== 登录门卫 ==========
from src.supabase_client import sign_in, sign_up, sign_out

def login_gate():
    """未登录则显示登录/注册界面，登录后返回 True。"""
    if st.session_state.get("user_id"):
        return True

    st.markdown("""
    <h1 style='text-align: center; color: #4A90E2; margin-top: 80px;'>
    🧠 Anatomy Memory
    </h1>
    <p style='text-align: center; color: #6B7280; font-size: 16px; margin-bottom: 40px;'>
    系统解剖学术语学习平台
    </p>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["登录", "注册"])

        with tab1:
            email = st.text_input("邮箱", key="login_email")
            password = st.text_input("密码", type="password", key="login_pwd")
            if st.button("登录", type="primary", use_container_width=True):
                ok, result = sign_in(email, password)
                if ok:
                    st.session_state["user_id"] = result
                    st.session_state["user_email"] = email
                    st.rerun()
                else:
                    st.error(f"登录失败：{result}")

        with tab2:
            email_r = st.text_input("邮箱", key="reg_email")
            password_r = st.text_input("密码（至少6位）", type="password", key="reg_pwd")
            if st.button("注册", type="primary", use_container_width=True):
                if len(password_r) < 6:
                    st.error("密码至少 6 位")
                else:
                    ok, result = sign_up(email_r, password_r)
                    if ok:
                        st.success("注册成功！请到「登录」标签登录。")
                    else:
                        st.error(f"注册失败：{result}")

    return False


if not login_gate():
    st.stop()
# ========== 登录门卫结束 ==========

st.set_page_config(page_title="主页", page_icon="🧠", layout="wide")

# 注入自定义字体 CSS
from src.ui import load_style
load_style()


# ============ 头部 ============
st.markdown("""
<h1 style='text-align: center; color: #4A90E2; margin-bottom: 8px;'>
🧠 Anatomy Memory
</h1>
<p style='text-align: center; color: #6B7280; font-size: 16px; margin-bottom: 32px;'>
系统解剖学术语学习平台
</p>
""", unsafe_allow_html=True)

# ============ 用户信息 + 登出 ============
col1, col2, col3 = st.columns([6, 2, 1])
with col2:
    st.caption(f"👤 {st.session_state.get('user_email', '')}")
with col3:
    if st.button("登出", key="logout_btn"):
        sign_out()
        st.session_state.clear()
        st.rerun()


# ============ 两个主入口卡片 ============
col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 28px; border-radius: 14px; color: white; margin-bottom: 16px;'>
        <h2 style='margin: 0 0 8px 0; color: white;'>🕸 知识图谱</h2>
        <p style='margin: 0; opacity: 0.9; font-size: 14px; line-height: 1.6;'>
            按章节或词根查看术语之间的关系网络。<br>
            支持搜索、拖拽、缩放。
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/1_知识图谱.py", label="进入知识图谱 →", icon="🕸", use_container_width=True)

with col2:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                padding: 28px; border-radius: 14px; color: white; margin-bottom: 16px;'>
        <h2 style='margin: 0 0 8px 0; color: white;'>📝 练习模式</h2>
        <p style='margin: 0; opacity: 0.9; font-size: 14px; line-height: 1.6;'>
            自己选择章节和术语，动态生成题目。<br>
            答完后用 FSRS 安排下次复习。
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/2_练习模式.py", label="进入练习模式 →", icon="📝", use_container_width=True)


# ============ 学习状态 ============
st.divider()
st.subheader("📊 学习状态")

from src.learning.scheduler import get_stats

stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("总卡片", stats["total"])
col2.metric("今日到期", stats["due"])
col3.metric("学习中", stats["learning"])
col4.metric("复习中", stats["review"])


# ============ 复习 + 统计 入口 ============
st.divider()

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);
                padding: 22px; border-radius: 14px; color: white; margin-bottom: 12px;'>
        <h3 style='margin: 0 0 6px 0; color: white;'>🔁 复习模式</h3>
        <p style='margin: 0; opacity: 0.9; font-size: 13px; line-height: 1.5;'>
            集中突破弱项卡片。
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/3_复习模式.py", label="进入复习模式 →", icon="🔁", use_container_width=True)

with col2:
    st.markdown("""
    <div style='background: linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%);
                padding: 22px; border-radius: 14px; color: white; margin-bottom: 12px;'>
        <h3 style='margin: 0 0 6px 0; color: white;'>📊 学习统计</h3>
        <p style='margin: 0; opacity: 0.9; font-size: 13px; line-height: 1.5;'>
            查看总体正确率、分题型正确率。
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/4_统计.py", label="查看学习统计 →", icon="📊", use_container_width=True)
