import streamlit as st
from google import genai
from google.genai import types
import requests
import stripe
from datetime import datetime, timezone, timedelta
import hashlib
import secrets


# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Smart AI Platform",
    page_icon="🤖",
    layout="wide"
)


# =========================================================
# SECRETS
# =========================================================

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "").strip()
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_PRICE_ID = st.secrets.get("STRIPE_PRICE_ID", "").strip()

# أضف هذه لاحقًا إلى Secrets
APP_URL = st.secrets.get("APP_URL", "").strip()
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "").strip()


# =========================================================
# GEMINI
# =========================================================

client = None

if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        client = None

GEMINI_MODEL = "gemini-3.7-flash"


# =========================================================
# STRIPE
# =========================================================

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# =========================================================
# UI
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

.main-card {
    background: white;
    padding: 28px;
    border-radius: 22px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 8px 25px rgba(0,0,0,0.05);
    margin-bottom: 20px;
}

.login-container {
    max-width: 560px;
    margin: 45px auto;
    padding: 35px;
    background: white;
    border-radius: 24px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 10px 30px rgba(0,0,0,0.06);
}

.metric-card {
    background: white;
    padding: 22px;
    border-radius: 18px;
    border: 1px solid #e2e8f0;
    text-align: center;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "page" not in st.session_state:
    st.session_state.page = "chat"


# =========================================================
# PASSWORD FUNCTIONS
# =========================================================

def hash_password(password):

    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000
    ).hex()

    return f"{salt}:{password_hash}"


def verify_password(password, stored_hash):

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
# SUPABASE
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
                params=params,
                json=json_data,
                timeout=10
            )

        else:
            return []

        response.raise_for_status()

        return response.json()

    except Exception:
        return []


# =========================================================
# AI
# =========================================================

def generate_ai_stream(user_message):

    if client is None:
        yield "⚠️ محرك الذكاء الاصطناعي غير متصل حاليًا."
        return

    recent_messages = st.session_state.messages[-12:]

    transcript = []

    for message in recent_messages:

        if message["role"] == "user":
            transcript.append(
                f"العميل: {message['content']}"
            )

        elif message["role"] == "assistant":
            transcript.append(
                f"المساعد: {message['content']}"
            )

    transcript.append(
        f"العميل: {user_message}"
    )

    prompt = "\n\n".join(transcript)

    system_instruction = """
أنت المساعد الذكي الرسمي لمنصة Smart AI.

التعليمات:

- أجب باللغة التي يستخدمها العميل.
- كن سريعًا وواضحًا ومفيدًا.
- لا تخترع معلومات.
- لا تدّعي تنفيذ عملية لم تنفذها.
- إذا لم تعرف الإجابة قل ذلك بوضوح.
- استخدم العربية بطريقة طبيعية عندما يكون العميل عربيًا.
- لا تكرر السؤال.
- اجعل الإجابة سهلة القراءة.
"""

    try:

        stream = client.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                thinking_config=types.ThinkingConfig(
                    thinking_level="low"
                ),
                max_output_tokens=800
            )
        )

        for chunk in stream:

            if chunk.text:
                yield chunk.text

    except Exception:

        yield (
            "⚠️ حدث خطأ مؤقت أثناء الاتصال بالذكاء الاصطناعي. "
            "يرجى المحاولة مرة أخرى."
        )


# =========================================================
# STRIPE CHECKOUT
# =========================================================

def create_checkout_session(username):

    if not stripe.api_key:
        return None, "Stripe غير متصل."

    if not STRIPE_PRICE_ID:
        return None, "لم يتم إعداد STRIPE_PRICE_ID."

    if not APP_URL:
        return None, "لم يتم إعداد APP_URL."

    try:

        users = supabase_request(
            "users_subscriptions",
            "GET",
            params={
                "username": f"eq.{username}"
            }
        )

        user = users[0] if users else None

        if not user:
            return None, "لم يتم العثور على الحساب."

        customer_id = user.get("stripe_customer_id", "")

        if not customer_id:

            customer = stripe.Customer.create(
                description=f"User: {username}"
            )

            customer_id = customer.id

            supabase_request(
                "users_subscriptions",
                "PATCH",
                params={
                    "username": f"eq.{username}"
                },
                json_data={
                    "stripe_customer_id": customer_id
                }
            )

        session = stripe.checkout.Session.create(

            mode="subscription",

            customer=customer_id,

            line_items=[
                {
                    "price": STRIPE_PRICE_ID,
                    "quantity": 1
                }
            ],

            success_url=f"{APP_URL}?payment=success",

            cancel_url=f"{APP_URL}?payment=cancelled",

            metadata={
                "username": username
            }
        )

        return session.url, None

    except Exception as e:

        return None, str(e)


# =========================================================
# LOGOUT
# =========================================================

def logout():

    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.messages = []
    st.session_state.page = "chat"


# =========================================================
# SIDEBAR
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
            "💳 الاشتراك",
            use_container_width=True
        ):

            st.session_state.page = "subscription"
            st.rerun()

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
            "🔒 سجل الدخول للوصول إلى المنصة."
        )


# =========================================================
# LOGIN / REGISTER
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
        [
            "🔑 تسجيل الدخول",
            "✨ إنشاء حساب"
        ]
    )

    # LOGIN

    with login_tab:

        username = st.text_input(
            "اسم المستخدم",
            key="login_username"
        ).strip()

        password = st.text_input(
            "كلمة المرور",
            type="password",
            key="login_password"
        )

        if st.button(
            "🚀 دخول",
            type="primary",
            use_container_width=True
        ):

            # Admin
            if (
                username == "admin"
                and ADMIN_PASSWORD
                and secrets.compare_digest(
                    password,
                    ADMIN_PASSWORD
                )
            ):

                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.session_state.page = "admin"

                st.rerun()

            # Normal user

            users = supabase_request(
                "users_subscriptions",
                "GET",
                params={
                    "username": f"eq.{username}"
                }
            )

            user = users[0] if users else None

            if user:

                stored_password = user.get(
                    "password_hash",
                    ""
                )

                authenticated = False

                # الحسابات الجديدة
                if ":" in stored_password:

                    authenticated = verify_password(
                        password,
                        stored_password
                    )

                # الحسابات القديمة
                else:

                    if secrets.compare_digest(
                        password,
                        stored_password
                    ):

                        authenticated = True

                        # ترقية كلمة المرور القديمة
                        supabase_request(
                            "users_subscriptions",
                            "PATCH",
                            params={
                                "username": f"eq.{username}"
                            },
                            json_data={
                                "password_hash":
                                hash_password(password)
                            }
                        )

                if authenticated:

                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.page = "chat"

                    st.rerun()

            st.error(
                "❌ اسم المستخدم أو كلمة المرور غير صحيحة."
            )

    # REGISTER

    with register_tab:

        new_username = st.text_input(
            "اسم المستخدم الجديد",
            key="register_username"
        ).strip()

        new_password = st.text_input(
            "كلمة المرور الجديدة",
            type="password",
            key="register_password"
        )

        if st.button(
            "✨ إنشاء الحساب",
            type="primary",
            use_container_width=True
        ):

            if not new_username or not new_password:

                st.warning(
                    "يرجى إدخال جميع البيانات."
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
                        "❌ اسم المستخدم موجود مسبقًا."
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
                        "password_hash":
                            hash_password(new_password),
                        "subscription_status": "trial",
                        "stripe_customer_id":
                            customer_id,
                        "trial_end_date":
                            trial_end
                    }

                    result = supabase_request(
                        "users_subscriptions",
                        "POST",
                        json_data=payload
                    )

                    if result:

                        st.success(
                            "🎉 تم إنشاء الحساب بنجاح!"
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
# ADMIN
# =========================================================

if (
    st.session_state.username == "admin"
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

    trials = len([
        user for user in users
        if user.get("subscription_status") == "trial"
    ])

    paid = len([
        user for user in users
        if user.get("subscription_status") == "active"
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
                <h3>🆓 تجريبي</h3>
                <h2>{trials}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col3:

        st.markdown(
            f"""
            <div class="metric-card">
                <h3>💳 مدفوع</h3>
                <h2>{paid}</h2>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    if users:

        st.dataframe(
            users,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("لا يوجد مستخدمون حتى الآن.")

    st.stop()


# =========================================================
# SUBSCRIPTION
# =========================================================

if st.session_state.page == "subscription":

    st.title("💳 الاشتراك الشهري")

    st.markdown(
        """
        <div class="main-card">

        <h2>⭐ Smart AI Pro</h2>

        <p>
        احصل على وصول كامل إلى المساعد الذكي.
        </p>

        <ul>
            <li>🤖 ذكاء اصطناعي متقدم</li>
            <li>⚡ ردود Streaming سريعة</li>
            <li>🧠 ذاكرة للمحادثة</li>
            <li>🔐 حساب شخصي</li>
            <li>💳 اشتراك شهري آمن عبر Stripe</li>
        </ul>

        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        "💳 الاشتراك الآن",
        type="primary",
        use_container_width=True
    ):

        checkout_url, error = create_checkout_session(
            st.session_state.username
        )

        if checkout_url:

            st.success(
                "تم تجهيز صفحة الدفع الآمنة."
            )

            st.link_button(
                "🔐 الانتقال إلى Stripe للدفع",
                checkout_url,
                use_container_width=True
            )

        else:

            st.error(
                f"تعذر إنشاء عملية الدفع: {error}"
            )

    st.stop()


# =========================================================
# CHAT
# =========================================================

st.markdown(
    """
    <div class="main-card">

    <h1>🤖 المساعد الذكي</h1>

    <p>
    اسألني أي شيء وسأساعدك بأفضل إجابة ممكنة.
    </p>

    </div>
    """,
    unsafe_allow_html=True
)


# History

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# Input

user_input = st.chat_input(
    "اكتب سؤالك هنا..."
)


if user_input:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.chat_message("user"):

        st.markdown(user_input)

    with st.chat_message("assistant"):

        response = st.write_stream(
            generate_ai_stream(user_input)
        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response
        }
    )
