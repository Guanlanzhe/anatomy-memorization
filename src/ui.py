"""UI 相关的公共函数。"""

import streamlit as st
from pathlib import Path

CSS_FILE = Path(__file__).parent.parent / "assets" / "style.css"


def load_style():
    """在页面顶部调用，注入自定义 CSS。"""
    if CSS_FILE.exists():
        css = CSS_FILE.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)