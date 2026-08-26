import streamlit as st
from google import genai
from google.genai import types
import requests
import stripe
from datetime import datetime, timezone, timedelta
import hashlib
import secrets


# =========================================================
# PAGE CONFIG
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
APP_URL = st.secrets.get("APP_URL", "").strip()
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "").strip()


# =========================================================
# GEMINI
# =========================================================

client = None

if GEMINI_API_KEY:
    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )
    except Exception as e:
        client = None
        st.session_state["gemini_init_error"] = str(e)


GEMINI_MODEL = "gemini-2.5-flash"


# =========================================================
# STRIPE
# =========================================================

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


# =========================================================
# DESIGN
# =========================================================

st.markdown(
    """
    <style>

    @import url(
        'https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;800'
    );

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

    </style>
    """,
    unsafe_allow_html=True
)


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
# PASSWORD HASHING
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

        calculated_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120000
        ).hex()

        return secrets.compare_digest(
            calculated_hash,
            saved_hash
        )

    except Exception:

        return False


# =========================================================
# SUPABASE REQUEST
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

    except Exception as e:

        st.session_state["last_supabase_error"] = str(e)

        return []


# =========================================================
# LOAD CHAT HISTORY
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

        content = message.get(
            "content",
            ""
        )

        if role in ["user", "assistant"] and content:

            history.append(
                {
                    "role": role,
                    "content": content
                }
            )

    return history


# =========================================================
# SAVE MESSAGE
# =========================================================

def save_message(
    username,
    role,
    content
):

    if not username or not content:
        return False

    payload = {
        "username": username,
        "role": role,
        "content": content
    }

    result = supabase_request(
        "chat_messages",
        "POST",
        json_data=payload
    )

    return bool(result)


# =========================================================
# DELETE CHAT
# =========================================================

def delete_chat_history(username):

    if not username:
        return False

    result = supabase_request(
        "chat_messages",
        "DELETE",
        params={
            "username": f"eq.{username}"
        }
    )

    return True


# =========================================================
# GEMINI STREAMING
# =========================================================

def generate_ai_stream(
    user_message,
    previous_messages
):

    if client is None:

        error = st.session_state.get(
            "gemini_init_error",
            "Gemini client لم يتم تهيئته."
        )

        yield (
            f"⚠️ تعذر تشغيل Gemini.\n\n"
            f"`{error}`"
        )

        return

    try:

        contents = []

        # إرسال آخر 6 رسائل فقط لتقليل زمن الطلب
        recent_messages = previous_messages[-6:]

        for message in recent_messages:

            role = message.get("role")

            content = message.get(
                "content",
                ""
            )

            if not content:
                continue

            gemini_role = (
                "user"
                if role == "user"
                else "model"
            )

            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[
                        types.Part(
                            text=content
                        )
                    ]
                )
            )

        # السؤال الحالي
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        text=user_message
                    )
                ]
            )
        )

        response_stream = (
            client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction="""
أنت المساعد الذكي الرسمي لمنصة Smart AI.

أجب بلغة المستخدم.

كن سريعًا ومباشرًا.

أعطِ معلومات مفيدة وواضحة.

لا تكرر السؤال.

لا تخترع معلومات.

إذا لم تعرف الإجابة قل ذلك بوضوح.

استخدم تنسيقًا سهل القراءة.

اجعل الإجابات مختصرة ما لم يطلب المستخدم التفصيل.
""",
                    max_output_tokens=500
                )
            )
        )

        got_text = False

        for chunk in response_stream:

            try:

                text = chunk.text

            except Exception:

                text = None

            if text:

                got_text = True

                yield text

        if not got_text:

            yield (
                "⚠️ Gemini لم يرجع نصًا في هذه المحاولة."
            )

    except Exception as e:

        yield (
            "⚠️ حدث خطأ أثناء الاتصال بـ Gemini.\n\n"
            f"**نوع الخطأ:** `{type(e).__name__}`\n\n"
            f"**التفاصيل:** `{e}`"
        )


# =========================================================
# STRIPE CHECKOUT
# =========================================================

def create_checkout_session(username):

    if not STRIPE_SECRET_KEY:

        return None, "STRIPE_SECRET_KEY غير موجود."

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

        return None, "الحساب غير موجود."

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

        checkout = stripe.checkout.Session.create(

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

        return checkout.url, None

    except Exception as e:

        return None, str(e)


# =========================================================
# LOGIN
# =========================================================

def login_user(
    username,
    password
):

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

    # الحسابات الجديدة
    if ":" in stored_password:

        authenticated = verify_password(
            password,
            stored_password
        )

    # الحسابات القديمة
    else:

        authenticated = secrets.compare_digest(
            password,
            stored_password
        )

        # ترقية كلمة المرور القديمة
        if authenticated:

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
# LOGOUT
# =========================================================

def logout():

    st.session_state.logged_in = False

    st.session_state.username = ""

    # لا نحذف المحادثات من Supabase
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
            "🔒 يرجى تسجيل الدخول."
        )


# =========================================================
# LOGIN / REGISTER
# =========================================================

if not st.session_state.logged_in:

    st.markdown(
        '<div class="login-container">',
        unsafe_allow_html=True
    )

    st.title(
        "🤖 Smart AI"
    )

    st.write(
        "منصة ذكاء اصطناعي متقدمة وسريعة."
    )

    login_tab, register_tab = st.tabs(
        [
            "🔑 تسجيل الدخول",
            "✨ إنشاء حساب"
        ]
    )

    # =====================================================
    # LOGIN TAB
    # =====================================================

    with login_tab:

        username = st.text_input(
            "👤 اسم المستخدم",
            key="login_username"
        ).strip()

        password = st.text_input(
            "🔒 كلمة المرور",
            type="password",
            key="login_password"
        )

        if st.button(
            "🚀 تسجيل الدخول",
            type="primary",
            use_container_width=True
        ):

            # ADMIN
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

            # USER
            elif login_user(
                username,
                password
            ):

                st.rerun()

            else:

                st.error(
                    "❌ اسم المستخدم أو كلمة المرور غير صحيحة."
                )

    # =====================================================
    # REGISTER TAB
    # =====================================================

    with register_tab:

        new_username = st.text_input(
            "👤 اسم المستخدم الجديد",
            key="register_username"
        ).strip()

        new_password = st.text_input(
            "🔒 كلمة المرور",
            type="password",
            key="register_password"
        )

        if st.button(
            "✨ إنشاء الحساب",
            type="primary",
            use_container_width=True
        ):

            if not new_username:

                st.warning(
                    "أدخل اسم المستخدم."
                )

            elif not new_password:

                st.warning(
                    "أدخل كلمة المرور."
                )

            elif len(new_password) < 8:

                st.warning(
                    "كلمة المرور يجب أن تحتوي على 8 أحرف على الأقل."
                )

            elif new_username.lower() == "admin":

                st.error(
                    "هذا الاسم محجوز للمسؤول."
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
                            "🎉 تم إنشاء الحساب بنجاح."
                        )

                        st.info(
                            "اذهب إلى تسجيل الدخول."
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
# ADMIN DASHBOARD
# =========================================================

if (
    st.session_state.username == "admin"
    and st.session_state.page == "admin"
):

    st.title(
        "📊 لوحة تحكم المسؤول"
    )

    users = supabase_request(
        "users_subscriptions",
        "GET"
    )

    if not isinstance(users, list):

        users = []

    total_users = len(users)

    trial_users = len(
        [
            user
            for user in users
            if user.get(
                "subscription_status"
            ) == "trial"
        ]
    )

    active_users = len(
        [
            user
            for user in users
            if user.get(
                "subscription_status"
            ) == "active"
        ]
    )

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
            "لا يوجد مستخدمون."
        )

    st.stop()


# =========================================================
# SUBSCRIPTION
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
        احصل على وصول كامل إلى منصة Smart AI.
        </p>

        <ul>
            <li>🤖 ذكاء اصطناعي متقدم</li>
            <li>⚡ ردود سريعة Streaming</li>
            <li>🧠 ذاكرة وحفظ المحادثات</li>
            <li>👤 حساب شخصي</li>
            <li>💳 اشتراك شهري عبر Stripe</li>
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
                "🔐 الانتقال إلى Stripe",
                checkout_url,
                use_container_width=True
            )

        else:

            st.error(
                error
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
    اسأل المساعد الذكي واحصل على إجابة سريعة.
    </p>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# SHOW HISTORY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# CHAT INPUT
# =========================================================

user_input = st.chat_input(
    "اكتب سؤالك هنا..."
)


if user_input:

    # نسخة من التاريخ قبل إضافة السؤال الحالي
    previous_messages = list(
        st.session_state.messages
    )

    # عرض السؤال
    with st.chat_message("user"):

        st.markdown(
            user_input
        )

    # حفظ السؤال محليًا
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

    # توليد الرد
    with st.chat_message("assistant"):

        bot_response = st.write_stream(
            generate_ai_stream(
                user_input,
                previous_messages
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
