import streamlit as st
from google import genai
from google.genai import types
import requests
import stripe
from datetime import datetime, timezone, timedelta
import hashlib
import secrets


# =========================================================
# 1. إعداد الصفحة
# =========================================================

st.set_page_config(
    page_title="Smart AI Platform",
    page_icon="🤖",
    layout="wide"
)


# =========================================================
# 2. قراءة Secrets
# =========================================================

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "").strip()
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "").strip()
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "").strip()
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY", "").strip()
STRIPE_PRICE_ID = st.secrets.get("STRIPE_PRICE_ID", "").strip()

APP_URL = st.secrets.get("APP_URL", "").strip()
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "").strip()


# =========================================================
# 3. Gemini
# =========================================================

client = None

if GEMINI_API_KEY:

    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception:
        client = None


GEMINI_MODEL = "gemini-2.5-flash"


# =========================================================
# 4. Stripe
# =========================================================

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# =========================================================
# 5. التصميم
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
# 6. Session State
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
# 7. تشفير كلمات المرور
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
# 8. Supabase
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

        elif method == "DELETE":

            response = requests.delete(
                url,
                headers=headers,
                params=params,
                timeout=10
            )

        else:

            return []

        response.raise_for_status()

        if response.text:
            return response.json()

        return []

    except Exception:

        return []


# =========================================================
# 9. تحميل المحادثات المحفوظة
# =========================================================

def load_chat_history(username):

    result = supabase_request(
        "chat_messages",
        "GET",
        params={
            "username": f"eq.{username}",
            "order": "created_at.asc"
        }
    )

    if not isinstance(result, list):
        return []

    history = []

    for message in result:

        role = message.get("role")

        if role not in ["user", "assistant"]:
            continue

        history.append({
            "role": role,
            "content": message.get(
                "content",
                ""
            )
        })

    return history


# =========================================================
# 10. حفظ رسالة
# =========================================================

def save_message(username, role, content):

    payload = {
        "username": username,
        "role": role,
        "content": content
    }

    return supabase_request(
        "chat_messages",
        "POST",
        json_data=payload
    )


# =========================================================
# 11. حذف المحادثة يدويًا
# =========================================================

def delete_chat_history(username):

    return supabase_request(
        "chat_messages",
        "DELETE",
        params={
            "username": f"eq.{username}"
        }
    )


# =========================================================
# 12. Gemini Streaming
# =========================================================

def generate_ai_stream(user_message):

    if client is None:

        yield (
            "⚠️ محرك الذكاء الاصطناعي غير متصل حاليًا."
        )

        return

    try:

        stream = client.models.generate_content_stream(

            model=GEMINI_MODEL,

            contents=user_message,

            config=types.GenerateContentConfig(

                system_instruction="""
أنت المساعد الذكي الرسمي لمنصة Smart AI.

القواعد:

- أجب بلغة المستخدم.
- كن سريعًا ومباشرًا.
- أعطِ إجابات مفيدة وواضحة.
- لا تكرر السؤال.
- لا تخترع معلومات.
- إذا لم تعرف شيئًا قل ذلك بوضوح.
- استخدم تنسيقًا سهل القراءة.
""",

                max_output_tokens=500
            )
        )

        for chunk in stream:

            if chunk.text:

                yield chunk.text

    except Exception as e:

    yield f"⚠️ خطأ Gemini الحقيقي: {type(e)._name_}: {e}"
        )


# =========================================================
# 13. Stripe Checkout
# =========================================================

def create_checkout_session(username):

    if not stripe.api_key:

        return None, "Stripe غير متصل."

    if not STRIPE_PRICE_ID:

        return None, "STRIPE_PRICE_ID غير موجود."

    if not APP_URL:

        return None, "APP_URL غير موجود."

    users = supabase_request(
        "users_subscriptions",
        "GET",
        params={
            "username": f"eq.{username}"
        }
    )

    if not users:

        return None, "لم يتم العثور على الحساب."

    user = users[0]

    customer_id = user.get(
        "stripe_customer_id",
        ""
    )

    try:

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

            success_url=(
                f"{APP_URL}?payment=success"
            ),

            cancel_url=(
                f"{APP_URL}?payment=cancelled"
            ),

            metadata={
                "username": username
            }
        )

        return session.url, None

    except Exception as e:

        return None, str(e)


# =========================================================
# 14. تسجيل الخروج
# =========================================================

def logout():

    st.session_state.logged_in = False
    st.session_state.username = ""

    # مهم:
    # لا نحذف messages من Supabase.
    # فقط نفرغ الذاكرة المؤقتة للجلسة الحالية.

    st.session_state.messages = []

    st.session_state.page = "chat"


# =========================================================
# 15. تسجيل الدخول
# =========================================================

def login_user(username, password):

    users = supabase_request(
        "users_subscriptions",
        "GET",
        params={
            "username": f"eq.{username}"
        }
    )

    if not users:

        return False

    user = users[0]

    stored_password = user.get(
        "password_hash",
        ""
    )

    authenticated = False

    # الحسابات الجديدة المشفرة
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

            # ترقية كلمة المرور تلقائيًا
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

        st.session_state.messages = (
            load_chat_history(username)
        )

        st.session_state.page = "chat"

        return True

    return False


# =========================================================
# 16. Sidebar
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

        if st.button(
            "💳 الاشتراك",
            use_container_width=True
        ):

            st.session_state.page = "subscription"

            st.rerun()

        st.divider()

        if st.button(
            "🗑️ حذف جميع المحادثات",
            use_container_width=True
        ):

            delete_chat_history(
                st.session_state.username
            )

            st.session_state.messages = []

            st.success(
                "تم حذف المحادثات."
            )

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
# 17. شاشة Login
# =========================================================

if not st.session_state.logged_in:

    st.markdown(
        '<div class="login-container">',
        unsafe_allow_html=True
    )

    st.title(
        "🤖 Smart AI Platform"
    )

    st.write(
        "منصة ذكية للمحادثة وحلول الذكاء الاصطناعي."
    )

    login_tab, register_tab = st.tabs(
        [
            "🔑 تسجيل الدخول",
            "✨ إنشاء حساب"
        ]
    )

    # -----------------------------------------------------
    # Login
    # -----------------------------------------------------

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

                st.session_state.messages = []

                st.session_state.page = "admin"

                st.rerun()

            elif login_user(
                username,
                password
            ):

                st.rerun()

            else:

                st.error(
                    "❌ اسم المستخدم أو كلمة المرور غير صحيحة."
                )

    # -----------------------------------------------------
    # Register
    # -----------------------------------------------------

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
                        "username":
                            f"eq.{new_username}"
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
                                description=
                                    f"User: {new_username}"
                            )

                            customer_id = customer.id

                        except Exception:

                            customer_id = ""

                    trial_end = (
                        datetime.now(timezone.utc)
                        + timedelta(days=7)
                    ).isoformat()

                    payload = {

                        "username":
                            new_username,

                        "password_hash":
                            hash_password(
                                new_password
                            ),

                        "subscription_status":
                            "trial",

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
# 18. Admin Dashboard
# =========================================================

if (
    st.session_state.username == "admin"
    and st.session_state.page == "admin"
):

    st.title(
        "📊 لوحة الإدارة"
    )

    users = supabase_request(
        "users_subscriptions",
        "GET"
    )

    if not isinstance(users, list):

        users = []

    total_users = len(users)

    trial_users = len([
        user
        for user in users
        if user.get(
            "subscription_status"
        ) == "trial"
    ])

    active_users = len([
        user
        for user in users
        if user.get(
            "subscription_status"
        ) == "active"
    ])

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "👥 المستخدمون",
            total_users
        )

    with col2:

        st.metric(
            "🆓 التجربة",
            trial_users
        )

    with col3:

        st.metric(
            "💳 المشتركين",
            active_users
        )

    st.divider()

    if users:

        st.dataframe(
            users,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "لا يوجد مستخدمون حتى الآن."
        )

    st.stop()


# =========================================================
# 19. صفحة الاشتراك
# =========================================================

if st.session_state.page == "subscription":

    st.title(
        "💳 Smart AI Pro"
    )

    st.markdown(
        """
        <div class="main-card">

        <h2>⭐ الاشتراك الشهري</h2>

        <p>
        احصل على وصول كامل إلى المساعد الذكي.
        </p>

        <ul>
            <li>🤖 ذكاء اصطناعي متقدم</li>
            <li>⚡ ردود سريعة Streaming</li>
            <li>🧠 ذاكرة وحفظ المحادثات</li>
            <li>👤 حساب شخصي</li>
            <li>💳 اشتراك شهري آمن عبر Stripe</li>
            <li>🆓 تجربة مجانية لمدة 7 أيام</li>
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

        checkout_url, error = (
            create_checkout_session(
                st.session_state.username
            )
        )

        if checkout_url:

            st.link_button(
                "🔐 الانتقال إلى Stripe للدفع",
                checkout_url,
                use_container_width=True
            )

        else:

            st.error(
                f"تعذر إنشاء الدفع: {error}"
            )

    st.stop()


# =========================================================
# 20. المحادثة
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


# =========================================================
# 21. عرض المحادثة
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# 22. استقبال سؤال جديد
# =========================================================

user_input = st.chat_input(
    "اكتب سؤالك هنا..."
)


if user_input:

    # حفظ سؤال المستخدم محليًا
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    # حفظ السؤال في Supabase
    save_message(
        st.session_state.username,
        "user",
        user_input
    )

    with st.chat_message("user"):

        st.markdown(
            user_input
        )

    # توليد الرد
    with st.chat_message("assistant"):

        bot_response = st.write_stream(
            generate_ai_stream(
                user_input
            )
        )

    # حفظ الرد محليًا
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": bot_response
        }
    )

    # حفظ الرد في Supabase
    save_message(
        st.session_state.username,
        "assistant",
        bot_response
    )
