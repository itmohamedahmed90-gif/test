"""
components/auth_forms.py

UI only — no SQL here. Forms call services/auth_service.py and, on
success, mutate st.session_state then st.rerun() immediately, per the
state-altering-operation rule. Using st.form means the DB write
(register_user / verify_credentials) happens once on submit, not on
every keystroke rerun.
"""

from __future__ import annotations

import streamlit as st

from services.auth_service import AuthError, login, register_user, verify_credentials


def render_login_form() -> None:
    with st.form("login_form", clear_on_submit=False):
        st.subheader("Log in")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        submitted = st.form_submit_button("Log in", use_container_width=True)

    if submitted:
        try:
            user = verify_credentials(email, password)
        except AuthError as e:
            st.error(str(e))
        else:
            login(user)
            st.rerun()


def render_register_form() -> None:
    with st.form("register_form", clear_on_submit=False):
        st.subheader("Create an account")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Password", type="password", key="register_password")
        password_confirm = st.text_input(
            "Confirm password", type="password", key="register_password_confirm"
        )
        submitted = st.form_submit_button("Create account", use_container_width=True)

    if submitted:
        if password != password_confirm:
            st.error("Passwords do not match.")
            return
        try:
            user = register_user(email, password)
        except AuthError as e:
            st.error(str(e))
        else:
            login(user)
            st.success("Account created.")
            st.rerun()


def render_auth_gate() -> None:
    """Top-level auth screen: tabs for login vs. register."""
    st.title("Resume Generator")
    tab_login, tab_register = st.tabs(["Log in", "Register"])
    with tab_login:
        render_login_form()
    with tab_register:
        render_register_form()
