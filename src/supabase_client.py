"""
Supabase 客户端 + 认证 + 用户设置。
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


def sign_in(identifier: str, password: str):
    """登录。identifier 可以是邮箱，也可以是纯用户名。"""
    sb = get_supabase()

    # 如果输入的不是标准邮箱格式，就拼接伪邮箱后缀
    if "@" not in identifier:
        email = f"{identifier}@anatomy.local"
    else:
        email = identifier

    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            return True, res.user.id
        return False, "登录失败"
    except Exception as e:
        return False, str(e)


def sign_out():
    """登出。"""
    try:
        sb = get_supabase()
        sb.auth.sign_out()
    except Exception:
        pass


def get_user_threshold() -> float:
    """拿当前用户的复习阈值。没有记录就返回默认 0.5。"""
    user_id = get_current_user_id()
    if not user_id:
        return 0.5

    sb = get_supabase()
    try:
        res = sb.table("user_settings").select("review_threshold").eq("user_id", user_id).execute()
        if res.data:
            return float(res.data[0]["review_threshold"])
    except Exception:
        pass
    return 0.5


def set_user_threshold(value: float):
    """设置当前用户的复习阈值。"""
    user_id = get_current_user_id()
    if not user_id:
        return

    sb = get_supabase()
    sb.table("user_settings").upsert({
        "user_id": user_id,
        "review_threshold": float(value),
    }).execute()
