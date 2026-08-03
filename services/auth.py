"""
管理员认证服务
"""

import streamlit as st
import config


def check_login(username: str, password: str) -> bool:
    """验证管理员登录"""
    return username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD


def login_required():
    """
    验证当前会话是否已通过管理员登录。
    如未登录，显示登录页面并阻止后续操作。
    返回 True 表示已登录，False 表示未登录。
    """
    if "admin_logged_in" not in st.session_state:
        st.session_state["admin_logged_in"] = False

    if not st.session_state["admin_logged_in"]:
        show_login_page()
        return False
    return True


def show_login_page():
    """渲染管理员登录页面"""
    st.title("后台管理登录")

    with st.form("login_form"):
        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")
        submitted = st.form_submit_button("登录", use_container_width=True)

        if submitted:
            if check_login(username, password):
                st.session_state["admin_logged_in"] = True
                st.success("登录成功，正在跳转...")
                st.rerun()
            else:
                st.error("用户名或密码错误，请重试")
