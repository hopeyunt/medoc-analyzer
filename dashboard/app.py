import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

API_URL = os.getenv("API_URL", "http://api:8000/api/v1")

st.set_page_config(page_title="MedDoc Analyzer", page_icon="🏥", layout="wide")

# --- Session state ---
if "token" not in st.session_state:
    st.session_state.token = None


def api(method, path, **kwargs):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    r = getattr(requests, method)(f"{API_URL}{path}", headers=headers, **kwargs)
    return r


# --- Auth pages ---
def login_page():
    st.title("MedDoc Analyzer")
    st.caption("Анализ качества медицинской документации")
    tab1, tab2 = st.tabs(["Войти", "Зарегистрироваться"])

    with tab1:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Пароль", type="password")
            if st.form_submit_button("Войти", use_container_width=True):
                r = api("post", "/auth/login", json={"email": email, "password": password})
                if r.status_code == 200:
                    st.session_state.token = r.json()["access_token"]
                    st.rerun()
                else:
                    st.error("Неверный email или пароль")

    with tab2:
        with st.form("register"):
            full_name = st.text_input("Полное имя")
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Пароль", type="password", key="reg_pass")
            if st.form_submit_button("Зарегистрироваться", use_container_width=True):
                r = api("post", "/auth/register", json={"full_name": full_name, "email": email, "password": password})
                if r.status_code == 201:
                    st.success("Аккаунт создан! Войдите.")
                else:
                    st.error(r.json().get("detail", "Ошибка"))


# --- Main app ---
def main_page():
    user_r = api("get", "/users/me")
    if user_r.status_code != 200:
        st.session_state.token = None
        st.rerun()
    user = user_r.json()

    balance_r = api("get", "/billing/balance")
    balance = balance_r.json() if balance_r.status_code == 200 else {}

    # Sidebar
    with st.sidebar:
        st.title("MedDoc Analyzer")
        st.markdown(f"**{user['full_name']}**")
        st.markdown(f"Уровень: **{balance.get('loyalty_level', 'Bronze')}**")
        st.metric("Кредиты", f"{balance.get('credits', 0):.1f}")
        if balance.get("discount_percent", 0) > 0:
            st.info(f"Скидка: {balance['discount_percent']}%")

        st.divider()
        page = st.radio("Навигация", ["Анализ документа", "История", "Пополнить баланс"])
        if st.button("Выйти"):
            st.session_state.token = None
            st.rerun()

    # Pages
    if page == "Анализ документа":
        st.header("Анализ медицинского документа")
        st.info("Не вводите персональные данные пациентов (ФИО, даты рождения, телефоны)")

        text = st.text_area("Вставьте текст документа", height=300, placeholder="История болезни, выписной эпикриз...")

        if st.button("Анализировать", type="primary", use_container_width=True):
            if not text.strip():
                st.warning("Введите текст документа")
            else:
                with st.spinner("Отправляем на анализ..."):
                    r = api("post", "/predictions/", json={"text": text})
                if r.status_code == 202:
                    pred = r.json()
                    st.success(f"Задача создана (ID: {pred['id']}). Обновите страницу через несколько секунд.")
                elif r.status_code == 402:
                    st.error("Недостаточно кредитов. Пополните баланс.")
                else:
                    st.error(r.json().get("detail", "Ошибка"))

    elif page == "История":
        st.header("История анализов")
        r = api("get", "/predictions/")
        if r.status_code == 200:
            preds = r.json()
            if not preds:
                st.info("Анализов пока нет")
            else:
                completed = [p for p in preds if p["status"] == "completed"]
                if completed:
                    scores = [p["quality_score"] for p in completed if p["quality_score"]]
                    if scores:
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Всего анализов", len(completed))
                        col2.metric("Средний балл", f"{sum(scores)/len(scores):.1f}")
                        col3.metric("Потрачено кредитов", sum(p["credits_charged"] for p in preds))

                        df = pd.DataFrame([{"ID": p["id"], "Балл": p["quality_score"],
                                           "Тип": p["document_type"], "Дата": p["created_at"][:10]} for p in completed])
                        fig = px.bar(df, x="ID", y="Балл", color="Тип", title="Качество документов")
                        st.plotly_chart(fig, use_container_width=True)

                for pred in preds[:10]:
                    with st.expander(f"#{pred['id']} — {pred['status']} — {pred['created_at'][:10]}"):
                        if pred.get("result"):
                            r_data = pred["result"]
                            st.metric("Балл качества", f"{r_data.get('quality_score', 0):.0f}/100")
                            if r_data.get("remarks"):
                                st.warning("\n".join(r_data["remarks"]))
                            if r_data.get("pii_warnings"):
                                st.error("\n".join(r_data["pii_warnings"]))

    elif page == "Пополнить баланс":
        st.header("Пополнение баланса")
        with st.form("deposit"):
            amount = st.number_input("Сумма кредитов", min_value=1.0, value=10.0, step=1.0)
            if st.form_submit_button("Пополнить", use_container_width=True):
                r = api("post", "/billing/deposit", json={"amount": amount})
                if r.status_code == 200:
                    st.success(f"Баланс пополнен на {amount} кредитов!")
                    st.rerun()
                else:
                    st.error("Ошибка пополнения")

        st.divider()
        st.subheader("История транзакций")
        r = api("get", "/billing/transactions")
        if r.status_code == 200:
            txs = r.json()
            if txs:
                df = pd.DataFrame([{"Дата": t["created_at"][:10], "Сумма": t["amount"],
                                    "Тип": t["type"], "Баланс после": t["balance_after"]} for t in txs])
                st.dataframe(df, use_container_width=True)


# --- Entry point ---
if st.session_state.token:
    main_page()
else:
    login_page()
