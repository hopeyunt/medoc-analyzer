import time
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import os

API_URL = os.getenv("API_URL", "http://api:8000/api/v1")

st.set_page_config(page_title="MedDoc Analyzer", page_icon="🏥", layout="wide")

if "token" not in st.session_state:
    st.session_state.token = None


def api(method, path, **kwargs):
    headers = {}
    if st.session_state.token:
        headers["Authorization"] = f"Bearer {st.session_state.token}"
    r = getattr(requests, method)(f"{API_URL}{path}", headers=headers, **kwargs)
    return r


# ---------------------------------------------------------------------------
# Страница входа / регистрации
# ---------------------------------------------------------------------------

def login_page():
    st.title("MedDoc Analyzer")
    st.caption("Редактор медицинской документации с AI-улучшением")
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
                r = api("post", "/auth/register", json={
                    "full_name": full_name, "email": email, "password": password
                })
                if r.status_code == 201:
                    st.success("Аккаунт создан! Войдите.")
                else:
                    st.error(r.json().get("detail", "Ошибка"))


# ---------------------------------------------------------------------------
# Страница: Улучшение текста (главная фича)
# ---------------------------------------------------------------------------

def page_improve():
    st.header("Улучшение медицинского документа")
    st.info(
        "Вставьте черновик документа. Система автоматически: "
        "скроет персональные данные, структурирует текст по разделам, "
        "дополнит недостающие разделы шаблонами."
    )

    text = st.text_area(
        "Черновик документа",
        height=250,
        placeholder="Пациент жалуется на боли в груди, давление 160/100, назначен бисопролол...",
    )

    col1, col2 = st.columns([1, 3])
    with col1:
        submit = st.button("Улучшить документ", type="primary", use_container_width=True)

    if submit:
        if not text.strip():
            st.warning("Введите текст документа")
            return

        with st.spinner("Отправляем на обработку..."):
            r = api("post", "/improve/", json={"text": text})

        if r.status_code == 402:
            st.error("Недостаточно кредитов. Пополните баланс.")
            return
        elif r.status_code != 202:
            st.error(r.json().get("detail", "Ошибка"))
            return

        item_id = r.json()["id"]
        st.session_state[f"improve_pending_{item_id}"] = True

        # ждём результата (макс 30 секунд)
        with st.spinner("Обрабатываем..."):
            for _ in range(15):
                time.sleep(2)
                check = api("get", f"/improve/{item_id}")
                if check.status_code == 200:
                    data = check.json()
                    if data["status"] == "completed":
                        _show_improvement_result(data)
                        return
                    elif data["status"] == "failed":
                        st.error("Ошибка при обработке. Попробуйте ещё раз.")
                        return

        st.warning(f"Обработка занимает больше времени. Результат будет в разделе «История» (ID: {item_id})")


def _show_improvement_result(data: dict):
    st.success("Готово!")

    import json
    missing = json.loads(data.get("missing_sections") or "[]")
    pii_warnings = json.loads(data.get("pii_warnings") or "[]")
    method = data.get("method", "rules")

    if pii_warnings:
        st.warning("Персональные данные обнаружены и заменены:\n" + "\n".join(pii_warnings))

    if missing:
        st.info("Отсутствующие разделы заполнены шаблонами: " + ", ".join(missing))

    badge = "🤖 AI (Claude)" if method == "llm" else "📋 Шаблон"
    st.caption(f"Метод улучшения: {badge}")

    st.subheader("Улучшенный документ")
    improved = data.get("improved_text", "")
    st.text_area("Скопируйте результат:", value=improved, height=350, key="result_text")

    # собираем обратную связь — это помогает дообучать модель
    st.divider()
    st.subheader("Оцените результат")
    col1, col2 = st.columns(2)
    with col1:
        rating = st.slider("Качество улучшения", 1, 5, 4)
    with col2:
        accepted = st.checkbox("Использовал этот вариант", value=True)

    if st.button("Отправить оценку"):
        fb_r = api("post", f"/improve/{data['id']}/feedback", json={
            "rating": rating,
            "accepted": accepted,
        })
        if fb_r.status_code == 200:
            st.success("Спасибо! Ваша оценка помогает улучшать систему.")


# ---------------------------------------------------------------------------
# Страница: Анализ документа (оценка качества)
# ---------------------------------------------------------------------------

def page_analyze():
    st.header("Оценка качества документа")
    st.caption("Проверяет наличие обязательных разделов и выводит балл качества")

    text = st.text_area("Текст документа", height=250)

    if st.button("Проверить качество", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("Введите текст")
            return

        with st.spinner("Анализируем..."):
            r = api("post", "/predictions/", json={"text": text})

        if r.status_code == 202:
            pred = r.json()
            st.success(f"Задача #{pred['id']} создана. Результат появится в «История анализов» через несколько секунд.")
        elif r.status_code == 402:
            st.error("Недостаточно кредитов.")
        else:
            st.error(r.json().get("detail", "Ошибка"))


# ---------------------------------------------------------------------------
# Страница: История
# ---------------------------------------------------------------------------

def page_history():
    st.header("История")
    tab1, tab2 = st.tabs(["Улучшения текста", "Анализы качества"])

    with tab1:
        r = api("get", "/improve/")
        if r.status_code == 200:
            items = r.json()
            if not items:
                st.info("Улучшений пока нет. Перейдите в «Улучшение документа».")
            else:
                for item in items[:15]:
                    status_icon = {"completed": "✅", "pending": "⏳", "processing": "🔄", "failed": "❌"}.get(item["status"], "?")
                    with st.expander(f"{status_icon} #{item['id']} — {item['created_at'][:10]} — {item['credits_charged']:.2f} кредитов"):
                        if item.get("improved_text"):
                            st.text_area("Результат", value=item["improved_text"], height=200, key=f"hist_{item['id']}")
                        if item.get("user_rating"):
                            st.caption(f"Ваша оценка: {'⭐' * item['user_rating']}")

    with tab2:
        r = api("get", "/predictions/")
        if r.status_code == 200:
            preds = r.json()
            if not preds:
                st.info("Анализов пока нет.")
            else:
                completed = [p for p in preds if p["status"] == "completed" and p.get("quality_score")]
                if completed:
                    scores = [p["quality_score"] for p in completed]
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Всего анализов", len(completed))
                    col2.metric("Средний балл", f"{sum(scores)/len(scores):.1f}")
                    col3.metric("Потрачено кредитов", f"{sum(p['credits_charged'] for p in preds):.2f}")

                    df = pd.DataFrame([{
                        "ID": p["id"], "Балл": p["quality_score"],
                        "Тип": p.get("document_type", "—"), "Дата": p["created_at"][:10]
                    } for p in completed])
                    fig = px.bar(df, x="ID", y="Балл", color="Тип", title="Балл качества по документам")
                    st.plotly_chart(fig, use_container_width=True)

                for pred in preds[:10]:
                    status_icon = {"completed": "✅", "pending": "⏳", "failed": "❌"}.get(pred["status"], "?")
                    with st.expander(f"{status_icon} #{pred['id']} — {pred['status']} — {pred['created_at'][:10]}"):
                        if pred.get("result"):
                            rd = pred["result"]
                            st.metric("Балл качества", f"{rd.get('quality_score', 0):.0f}/100")
                            if rd.get("remarks"):
                                st.warning("\n".join(rd["remarks"]))


# ---------------------------------------------------------------------------
# Страница: Биллинг
# ---------------------------------------------------------------------------

def page_billing():
    st.header("Пополнение баланса")

    with st.form("deposit"):
        amount = st.number_input("Сумма кредитов", min_value=1.0, value=10.0, step=5.0)
        st.caption("1 кредит = 1 улучшение или анализ документа")
        if st.form_submit_button("Пополнить", use_container_width=True):
            r = api("post", "/billing/deposit", json={"amount": amount})
            if r.status_code == 200:
                st.success(f"Баланс пополнен на {amount:.0f} кредитов!")
                st.rerun()
            else:
                st.error("Ошибка пополнения")

    st.divider()
    st.subheader("История транзакций")
    r = api("get", "/billing/transactions")
    if r.status_code == 200:
        txs = r.json()
        if txs:
            df = pd.DataFrame([{
                "Дата": t["created_at"][:10],
                "Сумма": t["amount"],
                "Тип": t["type"],
                "Баланс после": t["balance_after"],
            } for t in txs])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Транзакций пока нет.")


# ---------------------------------------------------------------------------
# Главная страница — сайдбар + роутинг
# ---------------------------------------------------------------------------

def main_page():
    user_r = api("get", "/users/me")
    if user_r.status_code != 200:
        st.session_state.token = None
        st.rerun()
    user = user_r.json()

    balance_r = api("get", "/billing/balance")
    balance = balance_r.json() if balance_r.status_code == 200 else {}

    with st.sidebar:
        st.title("MedDoc")
        st.markdown(f"**{user['full_name']}**")
        level = balance.get("loyalty_level", "Bronze")
        level_icons = {"Bronze": "🥉", "Silver": "🥈", "Gold": "🥇"}
        st.markdown(f"Уровень: {level_icons.get(level, '')} **{level}**")
        st.metric("Кредиты", f"{balance.get('credits', 0):.1f}")
        if balance.get("discount_percent", 0) > 0:
            st.success(f"Скидка: {balance['discount_percent']}%")

        st.divider()
        page = st.radio(
            "Навигация",
            ["Улучшение документа", "Оценка качества", "История", "Пополнить баланс"],
        )
        if st.button("Выйти"):
            st.session_state.token = None
            st.rerun()

    if page == "Улучшение документа":
        page_improve()
    elif page == "Оценка качества":
        page_analyze()
    elif page == "История":
        page_history()
    elif page == "Пополнить баланс":
        page_billing()


if st.session_state.token:
    main_page()
else:
    login_page()
