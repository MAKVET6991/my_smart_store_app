import streamlit as st
from google import genai
from google.genai import types
import requests
import stripe
from datetime import datetime, timezone, timedelta
import hashlib
import secrets

# =========================================================
# 1. PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Smart AI Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# 2. PROFESSIONAL UI
# =========================================================

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif;
}

.stApp {
    background: #f8fafc;
}

h1, h2, h3 {
    font-weight: 800 !important;
}

.login-container {
    max-width: 560px;
    margin: 50px auto;
    padding: 35px;
    background: white;
    border-radius: 24px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 10px 30px rgba(0,0,0,0.06);
}

.chat-header {
    padding: 20px;
    border-radius: 18px;
    background: white;
    border: 1px solid #e2e8f0;
    margin-bottom: 20px;
}

.metric-card {
    background: white;
    padding: 22px;
    border-radius: 18px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. SECRETS
# =========================================================

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "").strip()
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "").strip()

# =========================================================
# 4. GEMINI CLIENT
# =========================================================

client = None

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        st.error("تعذر تشغيل محرك الذكاء الاصطناعي.")
        client = None

# Gemini 3.7 Flash = powerful current workhorse
GEMINI_MODEL = "gemini-3.7-flash"

# =========================================================
# 5. STRIPE
# =========================================================

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# =========================================================
# 6. SESSION STATE
# =========================================================

defaults = {
    "logged_in": False,
    "username": "",
    "messages": [],
    "page": "chat"
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =========================================================
# 7. PASSWORD SECURITY
# =========================================================

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000
    ).hex()

    return f"{salt}:{password_hash}"


def verify_password(password: str, stored_hash: str) -> bool:

    try:
        salt, saved_hash = stored_hash.split(":")

        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120000
        ).hex()

        return secrets.compare_digest(
            calculated,
            saved_hash
        )

    except Exception:
        return False


# =========================================================
# 8. SUPABASE
# =========================================================

def supabase_request(
    endpoint,
    method="GET",
    json_data=None,
    params=None
):

    if not SUPABASE_URL or not SUPABASE_KEY:
        return []

    url = f"{SUPABASE_URL}/rest/v1/{endpoint}"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    try:

        if method == "GET":

            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=10
            )

        elif method == "POST":

            response = requests.post(
                url,
                headers=headers,
                json=json_data,
                timeout=10
            )

        elif method == "PATCH":

            response = requests.patch(
                url,
                headers=headers,
                json=json_data,
                params=params,
                timeout=10
            )

        else:
            return []

        response.raise_for_status()

        return response.json()

    except requests.RequestException:
        return []

    except Exception:
        return []


# =========================================================
# 9. AI STREAM
# =========================================================

def generate_ai_stream(user_message):

    if client is None:
        yield "⚠️ محرك الذكاء الاصطناعي غير متصل حاليًا."
        return

    # نرسل فقط عددًا محدودًا من الرسائل القديمة
    # لتقليل حجم الطلب وتسريع الاستجابة.
    recent_messages = st.session_state.messages[-12:]

    conversation = []

    for message in recent_messages:

        role = message["role"]

        if role == "user":
            conversation.append(
                f"العميل: {message['content']}"
            )

        elif role == "assistant":
            conversation.append(
                f"المساعد: {message['content']}"
            )

    conversation.append(
        f"العميل: {user_message}"
    )

    prompt = "\n".join(conversation)

    system_instruction = """
أنت المساعد الذكي الرسمي لهذه المنصة.

قواعدك:

1. أجب باللغة التي يستخدمها العميل.
2. كن واضحًا ومختصرًا ومفيدًا.
3. لا تدّعي أنك نفذت إجراءً لم تنفذه.
4. إذا لم تكن تعرف الإجابة، قل ذلك بوضوح.
5. لا تخترع أسعارًا أو بيانات أو معلومات عن الشركة.
6. استخدم تنسيقًا واضحًا وسهل القراءة.
7. تعامل مع العميل باحترافية.
"""

    try:

        stream = client.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4,
                max_output_tokens=800
            )
        )

        for chunk in stream:

            text = getattr(chunk, "text", None)

            if text:
                yield text

    except Exception as e:

        yield (
            "⚠️ حدث خطأ أثناء الاتصال بمحرك الذكاء الاصطناعي. "
            "يرجى المحاولة مرة أخرى."
        )


# =========================================================
# 10. LOGOUT
# =========================================================

def logout():

    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.messages = []
    st.session_state.page = "chat"

# =========================================================
# 11. SIDEBAR
# =========================================================

with st.sidebar:

    st.title("🤖 Smart AI")

    if st.session_state.logged_in:

        st.success(
            f"👤 {st.session_state.username}"
        )

        if st.button(
            "💬 المحادثة",
            use_container_width=True
        ):
            st.session_state.page = "chat"
            st.rerun()

        if st.session_state.username == "admin":

            if st.button(
                "📊 لوحة الإدارة",
                use_container_width=True
            ):
                st.session_state.page = "admin"
                st.rerun()

        st.divider()

        if st.button(
            "🗑️ مسح المحادثة",
            use_container_width=True
        ):
            st.session_state.messages = []
            st.rerun()

        if st.button(
            "🚪 تسجيل الخروج",
            use_container_width=True
        ):
            logout()
            st.rerun()

    else:

        st.info(
            "🔒 قم بتسجيل الدخول للوصول إلى المنصة."
        )


# =========================================================
# 12. LOGIN / REGISTER
# =========================================================

if not st.session_state.logged_in:

    st.markdown(
        '<div class="login-container">',
        unsafe_allow_html=True
    )

    st.title("🤖 Smart AI Platform")

    st.write(
        "منصة ذكية للمحادثة وحلول الذكاء الاصطناعي."
    )

    login_tab, register_tab = st.tabs(
        ["🔑 تسجيل الدخول", "✨ إنشاء حساب"]
    )

    # ---------------- LOGIN ----------------

    with login_tab:

        username = st.text_input(
            "اسم المستخدم",
            key="login_username"
        )

        password = st.text_input(
            "كلمة المرور",
            type="password",
            key="login_password"
        )

        if st.button(
            "دخول",
            type="primary",
            use_container_width=True
        ):

            # Admin password يجب وضعه في Secrets
            admin_username = st.secrets.get(
                "ADMIN_USERNAME",
                "admin"
            )

            admin_password_hash = st.secrets.get(
                "ADMIN_PASSWORD_HASH",
                ""
            )

            if (
                username == admin_username
                and admin_password_hash
                and verify_password(
                    password,
                    admin_password_hash
                )
            ):

                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.session_state.page = "admin"

                st.rerun()

            else:

                users = supabase_request(
                    "users_subscriptions",
                    "GET",
                    params={
                        "username": f"eq.{username}"
                    }
                )

                user = users[0] if users else None

                if (
                    user
                    and verify_password(
                        password,
                        user.get("password_hash", "")
                    )
                ):

                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.page = "chat"

                    st.rerun()

                else:

                    st.error(
                        "❌ اسم المستخدم أو كلمة المرور غير صحيحة."
                    )

    # ---------------- REGISTER ----------------

    with register_tab:

        new_username = st.text_input(
            "اسم المستخدم الجديد",
            key="register_username"
        )

        new_password = st.text_input(
            "كلمة المرور",
            type="password",
            key="register_password"
        )

        if st.button(
            "إنشاء الحساب",
            type="primary",
            use_container_width=True
        ):

            if not new_username or not new_password:

                st.warning(
                    "يرجى إدخال اسم المستخدم وكلمة المرور."
                )

            elif len(new_password) < 8:

                st.warning(
                    "كلمة المرور يجب أن تكون 8 أحرف على الأقل."
                )

            else:

                existing = supabase_request(
                    "users_subscriptions",
                    "GET",
                    params={
                        "username": f"eq.{new_username}"
                    }
                )

                if existing:

                    st.error(
                        "اسم المستخدم موجود مسبقًا."
                    )

                else:

                    customer_id = ""

                    if stripe.api_key:

                        try:

                            customer = stripe.Customer.create(
                                description=f"User: {new_username}"
                            )

                            customer_id = customer.id

                        except Exception:
                            customer_id = ""

                    trial_end = (
                        datetime.now(timezone.utc)
                        + timedelta(days=7)
                    ).isoformat()

                    payload = {
                        "username": new_username,
                        "password_hash": hash_password(
                            new_password
                        ),
                        "subscription_status": "trial",
                        "stripe_customer_id": customer_id,
                        "trial_end_date": trial_end
                    }

                    result = supabase_request(
                        "users_subscriptions",
                        "POST",
                        json_data=payload
                    )

                    if result:

                        st.success(
                            "🎉 تم إنشاء الحساب بنجاح. "
                            "يمكنك الآن تسجيل الدخول."
                        )

                    else:

                        st.error(
                            "تعذر إنشاء الحساب."
                        )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )

    st.stop()


# =========================================================
# 13. ADMIN DASHBOARD
# =========================================================

if (
    st.session_state.logged_in
    and st.session_state.username == "admin"
    and st.session_state.page == "admin"
):

    st.title("📊 لوحة الإدارة")

    users = supabase_request(
        "users_subscriptions",
        "GET"
    )

    if not isinstance(users, list):
        users = []

    total_users = len(users)

    active_users = len([
        u for u in users
        if u.get("subscription_status") in
        ["active", "trial"]
    ])

    paid_users = len([
        u for u in users
        if u.get("subscription_status") == "active"
    ])

    col1, col2, col3 = st.columns(3)

    with col1:

        st.markdown(
            f"""
            <div class="metric-card">
                <h3>👥 المستخدمون</h3>
                <h2>{total_users}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:

        st.markdown(
            f"""
            <div class="metric-card">
                <h3>🟢 نشطون</h3>
                <h2>{active_users}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="metric-card">
                <h3>💳 مشتركون مدفوعون</h3>
                <h2>{paid_users}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    st.subheader("👥 المستخدمون")

    if users:

        st.dataframe(
            users,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("لا توجد بيانات مستخدمين حتى الآن.")

    st.stop()


# =========================================================
# 14. MAIN CHAT
# =========================================================

st.markdown(
    """
    <div class="chat-header">
        <h1>🤖 المساعد الذكي</h1>
        <p>
        اسألني أي شيء وسأحاول مساعدتك بأفضل إجابة ممكنة.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

# عرض التاريخ السابق

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# 15. CHAT INPUT
# =========================================================

user_input = st.chat_input(
    "اكتب سؤالك هنا..."
)

if user_input:

    # سؤال العميل
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.chat_message("user"):

        st.markdown(user_input)

    # رد AI
    with st.chat_message("assistant"):

        bot_response = st.write_stream(
            generate_ai_stream(user_input)
        )

    # حفظ الرد
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": bot_response
        }
    )
