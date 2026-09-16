"""
Supabase 客户端 + 认证封装。
"""

import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    """获取 Supabase 客户端（单例）。"""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def get_current_user_id():
    """从 session 里拿到当前登录用户的 UUID。未登录返回 None。"""
    return st.session_state.get("user_id")


def sign_up(email: str, password: str):
    """注册。返回 (success, user_id_or_error)。"""
    sb = get_supabase()
    try:
        res = sb.auth.sign_up({"email": email, "password": password})
        if res.user:
            return True, res.user.id
        return False, "注册失败，请检查邮箱格式"
    except Exception as e:
        return False, str(e)


def sign_in(email: str, password: str):
    """登录。返回 (success, user_id_or_error)。"""
    sb = get_supabase()
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            return True, res.user.id
        return False, "登录失败"
    except Exception as e:
        return False, str(e)


def sign_out():
    """登出。"""
    sb = get_supabase()
    try:
        sb.auth.sign_out()
    except Exception:
        pass