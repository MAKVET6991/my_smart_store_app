import streamlit as st
from google import genai
from google.genai import types
import requests
import stripe
from datetime import datetime, timezone, timedelta
import hashlib
import secrets
import re
import time


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
# 2. UI
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
    margin: 40px auto;
    padding: 35px;
    background: white;
    border-radius: 24px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 10px 30px rgba(0,0,0,0.06);
}

.chat-header {
    padding: 25px;
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

.plan-card {
    background: white;
    padding: 25px;
    border-radius: 20px;
    border: 1px solid #e2e8f0;
}

.file-box {
    padding: 18px;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# 3. SECRETS
# =========================================================

GEMINI_API_KEY = st.secrets.get(
    "GEMINI_API_KEY", ""
).strip()

SUPABASE_URL = st.secrets.get(
    "SUPABASE_URL", ""
).strip()

SUPABASE_KEY = st.secrets.get(
    "SUPABASE_KEY", ""
).strip()

STRIPE_SECRET_KEY = st.secrets.get(
    "STRIPE_SECRET_KEY", ""
).strip()

STRIPE_PRICE_ID = st.secrets.get(
    "STRIPE_PRICE_ID", ""
).strip()

APP_URL = st.secrets.get(
    "APP_URL", ""
).strip().rstrip("/")

ADMIN_PASSWORD = st.secrets.get(
    "ADMIN_PASSWORD", ""
).strip()

ADMIN_USERNAME = st.secrets.get(
    "ADMIN_USERNAME", "admin"
).strip()


# =========================================================
# 4. GEMINI
# =========================================================

client = None

if GEMINI_API_KEY:

    try:
        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    except Exception:
        client = None


# IMPORTANT:
# Correct official model name
GEMINI_MODEL = "gemini-3.6-flash"

# Fallback models if temporary 503 occurs
GEMINI_FALLBACK_MODELS = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite"
]


# =========================================================
# 5. STRIPE
# =========================================================

if STRIPE_SECRET_KEY:

    try:
        stripe.api_key = STRIPE_SECRET_KEY
    except Exception:
        pass


# =========================================================
# 6. SESSION STATE
# =========================================================

defaults = {
    "logged_in": False,
    "username": "",
    "messages": [],
    "page": "chat",
    "user_data": None,
    "uploaded_files": [],
    "checkout_message": "",
    "session_message_count": 0
}

for key, value in defaults.items():

    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# 7. PASSWORD
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


def verify_password(
    password: str,
    stored_hash: str
) -> bool:

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
# 8. USERNAME
# =========================================================

def valid_username(username):

    if not username:
        return False

    if len(username) < 3:
        return False

    if len(username) > 30:
        return False

    return bool(
        re.fullmatch(
            r"[A-Za-z0-9_.-]+",
            username
        )
    )


# =========================================================
# 9. SUPABASE
# =========================================================

def supabase_request(
    endpoint,
    method="GET",
    json_data=None,
    params=None
):

    if not SUPABASE_URL or not SUPABASE_KEY:
        return []

    url = (
        f"{SUPABASE_URL.rstrip('/')}"
        f"/rest/v1/{endpoint}"
    )

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
                timeout=15
            )

        elif method == "POST":

            response = requests.post(
                url,
                headers=headers,
                json=json_data,
                timeout=15
            )

        elif method == "PATCH":

            response = requests.patch(
                url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=15
            )

        else:
            return []

        response.raise_for_status()

        if not response.text:
            return []

        return response.json()

    except Exception:
        return []


# =========================================================
# 10. GET USER
# =========================================================

def get_user(username):

    if not username:
        return None

    users = supabase_request(
        "users_subscriptions",
        "GET",
        params={
            "username": f"eq.{username}",
            "limit": "1"
        }
    )

    if isinstance(users, list) and users:
        return users[0]

    return None


# =========================================================
# 11. UPDATE USER
# =========================================================

def update_user(username, data):

    return supabase_request(
        "users_subscriptions",
        "PATCH",
        json_data=data,
        params={
            "username": f"eq.{username}"
        }
    )


# =========================================================
# 12. TRIAL
# =========================================================

def trial_is_active(user):

    if not user:
        return False

    status = user.get(
        "subscription_status",
        ""
    )

    if status == "active":
        return True

    if status != "trial":
        return False

    trial_end = user.get(
        "trial_end_date"
    )

    if not trial_end:
        return False

    try:

        end_date = datetime.fromisoformat(
            trial_end.replace(
                "Z",
                "+00:00"
            )
        )

        return (
            datetime.now(timezone.utc)
            < end_date
        )

    except Exception:

        return False


def account_has_access(user):

    if not user:
        return False

    status = user.get(
        "subscription_status",
        ""
    )

    if status == "active":
        return True

    if status == "trial":
        return trial_is_active(user)

    return False


def days_left(user):

    if not user:
        return 0

    if user.get(
        "subscription_status"
    ) == "active":

        return None

    trial_end = user.get(
        "trial_end_date"
    )

    if not trial_end:
        return 0

    try:

        end_date = datetime.fromisoformat(
            trial_end.replace(
                "Z",
                "+00:00"
            )
        )

        seconds = (
            end_date -
            datetime.now(timezone.utc)
        ).total_seconds()

        return max(
            0,
            int(seconds / 86400)
        )

    except Exception:

        return 0


# =========================================================
# 13. STRIPE
# =========================================================

def create_checkout_session(username):

    if not STRIPE_SECRET_KEY:

        return None, "Stripe غير مفعّل."

    if not STRIPE_PRICE_ID:

        return None, "STRIPE_PRICE_ID غير موجود."

    if not APP_URL:

        return None, "APP_URL غير موجود."

    user = get_user(username)

    if not user:

        return None, "المستخدم غير موجود."

    try:

        customer_id = user.get(
            "stripe_customer_id",
            ""
        )

        if not customer_id:

            customer = stripe.Customer.create(
                description=f"Smart AI: {username}",
                metadata={
                    "username": username
                }
            )

            customer_id = customer.id

            update_user(
                username,
                {
                    "stripe_customer_id":
                        customer_id
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

            client_reference_id=username,

            metadata={
                "username": username
            },

            subscription_data={
                "metadata": {
                    "username": username
                }
            },

            success_url=(
                f"{APP_URL}"
                f"?payment=success"
                f"&session_id={{CHECKOUT_SESSION_ID}}"
            ),

            cancel_url=(
                f"{APP_URL}"
                f"?payment=cancelled"
            )
        )

        return session.url, None

    except Exception as e:

        return None, str(e)


def verify_payment(session_id, username):

    if not STRIPE_SECRET_KEY:
        return False

    try:

        session = stripe.checkout.Session.retrieve(
            session_id
        )

        if session.status != "complete":
            return False

        metadata = session.metadata or {}

        if metadata.get("username") != username:
            return False

        update_user(
            username,
            {
                "subscription_status":
                    "active",

                "stripe_customer_id":
                    session.customer or ""
            }
        )

        return True

    except Exception:

        return False


# =========================================================
# 14. GEMINI TEXT
# =========================================================

def build_prompt(user_message):

    recent = (
        st.session_state.messages[-12:]
    )

    conversation = []

    for message in recent:

        role = message.get("role")

        content = message.get(
            "content",
            ""
        )

        if role == "user":

            conversation.append(
                f"العميل: {content}"
            )

        elif role == "assistant":

            conversation.append(
                f"المساعد: {content}"
            )

    conversation.append(
        f"العميل: {user_message}"
    )

    return "\n".join(
        conversation
    )


SYSTEM_INSTRUCTION = """
أنت المساعد الذكي الرسمي لمنصة Smart AI.

القواعد:

1. أجب باللغة التي يستخدمها المستخدم.
2. كن سريعًا وواضحًا ومفيدًا.
3. كن احترافيًا.
4. لا تخترع معلومات.
5. لا تدّعي تنفيذ شيء لم تنفذه.
6. إذا كانت المعلومات غير مؤكدة وضّح ذلك.
7. عند تحليل الملفات والصور والصوت والفيديو،
   اشرح النتيجة بوضوح.
"""


# =========================================================
# 15. AI STREAM WITH FALLBACK
# =========================================================

def generate_ai_stream(user_message):

    if client is None:

        yield (
            "⚠️ مفتاح Gemini غير متصل. "
            "تحقق من GEMINI_API_KEY في Secrets."
        )

        return

    prompt = build_prompt(
        user_message
    )

    last_error = None

    for model in GEMINI_FALLBACK_MODELS:

        try:

            stream = (
                client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=
                            SYSTEM_INSTRUCTION,
                        temperature=0.4,
                        max_output_tokens=1200
                    )
                )
            )

            received = False

            for chunk in stream:

                text = getattr(
                    chunk,
                    "text",
                    None
                )

                if text:

                    received = True
                    yield text

            if received:
                return

        except Exception as e:

            last_error = str(e)

            error_text = last_error.lower()

            if (
                "503" in error_text
                or "unavailable" in error_text
                or "high demand" in error_text
            ):

                time.sleep(0.8)
                continue

            break

    yield (
        "⚠️ تعذر الاتصال بمحرك الذكاء الاصطناعي حاليًا. "
        "إذا كان الخطأ 503 فهذا يعني أن النموذج مشغول مؤقتًا. "
        "حاول مرة أخرى بعد لحظات."
    )


# =========================================================
# 16. MULTIMODAL FILE ANALYSIS
# =========================================================

def analyze_uploaded_file(
    uploaded_file,
    question
):

    if client is None:

        return (
            "⚠️ Gemini غير متصل. "
            "تحقق من GEMINI_API_KEY."
        )

    try:

        file_bytes = uploaded_file.getvalue()

        mime_type = (
            uploaded_file.type
            or "application/octet-stream"
        )

        prompt = (
            question
            if question
            else
            "حلل هذا الملف بالتفصيل "
            "واشرح أهم المعلومات الموجودة فيه."
        )

        # Gemini Files API
        uploaded = client.files.upload(
            file=uploaded_file,
            config={
                "mime_type": mime_type
            }
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[
                prompt,
                uploaded
            ],
            config=types.GenerateContentConfig(
                system_instruction=
                    SYSTEM_INSTRUCTION,
                temperature=0.3,
                max_output_tokens=1500
            )
        )

        return response.text

    except Exception as e:

        return (
            "⚠️ تعذر تحليل الملف.\n\n"
            f"التفاصيل: {str(e)}"
        )


# =========================================================
# 17. LOGOUT
# =========================================================

def logout():

    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.user_data = None
    st.session_state.messages = []
    st.session_state.uploaded_files = []
    st.session_state.page = "chat"
    st.session_state.session_message_count = 0


# =========================================================
# 18. PAYMENT RETURN
# =========================================================

payment = st.query_params.get(
    "payment"
)

session_id = st.query_params.get(
    "session_id"
)

if (
    payment == "success"
    and session_id
    and st.session_state.logged_in
):

    if verify_payment(
        session_id,
        st.session_state.username
    ):

        st.session_state.checkout_message = (
            "🎉 تم الدفع وتفعيل الاشتراك بنجاح."
        )

    else:

        st.session_state.checkout_message = (
            "⚠️ تعذر تأكيد عملية الدفع."
        )

    st.query_params.clear()


elif payment == "cancelled":

    st.session_state.checkout_message = (
        "تم إلغاء عملية الدفع."
    )

    st.query_params.clear()


# =========================================================
# 19. SIDEBAR
# =========================================================

with st.sidebar:

    st.title("🤖 Smart AI")

    if st.session_state.logged_in:

        st.success(
            f"👤 {st.session_state.username}"
        )

        # ADMIN IS ALWAYS ALLOWED
        if (
            st.session_state.username
            == ADMIN_USERNAME
        ):

            st.success(
                "👑 المسؤول"
            )

        else:

            user = get_user(
                st.session_state.username
            )

            st.session_state.user_data = user

            if user:

                if user.get(
                    "subscription_status"
                ) == "active":

                    st.success(
                        "💳 اشتراك نشط"
                    )

                elif trial_is_active(user):

                    st.info(
                        f"🎁 التجربة: "
                        f"{days_left(user)} يوم"
                    )

                else:

                    st.warning(
                        "انتهت التجربة."
                    )

        if st.button(
            "💬 المحادثة",
            use_container_width=True
        ):

            st.session_state.page = "chat"
            st.rerun()

        if st.button(
            "💳 الاشتراك",
            use_container_width=True
        ):

            st.session_state.page = "plans"
            st.rerun()

        if (
            st.session_state.username
            == ADMIN_USERNAME
        ):

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
            "🔒 سجل الدخول للوصول إلى المنصة."
        )


# =========================================================
# 20. LOGIN
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
        "منصة ذكية للمحادثة والذكاء الاصطناعي."
    )

    login_tab, register_tab = st.tabs(
        [
            "🔑 تسجيل الدخول",
            "✨ إنشاء حساب"
        ]
    )

    # -----------------------------------------------------
    # LOGIN
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
            "دخول",
            type="primary",
            use_container_width=True
        ):

            # =============================================
            # ADMIN LOGIN
            # =============================================

            if (
                username == ADMIN_USERNAME
                and ADMIN_PASSWORD
                and secrets.compare_digest(
                    password,
                    ADMIN_PASSWORD
                )
            ):

                st.session_state.logged_in = True
                st.session_state.username = (
                    ADMIN_USERNAME
                )
                st.session_state.page = "admin"

                st.success(
                    "👑 تم تسجيل دخول المسؤول."
                )

                st.rerun()

            # =============================================
            # NORMAL USER
            # =============================================

            user = get_user(
                username
            )

            if (
                user
                and verify_password(
                    password,
                    user.get(
                        "password_hash",
                        ""
                    )
                )
            ):

                st.session_state.logged_in = True

                st.session_state.username = (
                    username
                )

                st.session_state.user_data = user

                st.session_state.page = "chat"

                st.rerun()

            else:

                st.error(
                    "❌ اسم المستخدم أو كلمة المرور غير صحيحة."
                )

    # -----------------------------------------------------
    # REGISTER
    # -----------------------------------------------------

    with register_tab:

        new_username = st.text_input(
            "اسم المستخدم",
            key="register_username"
        ).strip()

        new_password = st.text_input(
            "كلمة المرور",
            type="password",
            key="register_password"
        )

        confirm_password = st.text_input(
            "تأكيد كلمة المرور",
            type="password",
            key="register_confirm_password"
        )

        if st.button(
            "إنشاء الحساب",
            type="primary",
            use_container_width=True
        ):

            if not valid_username(
                new_username
            ):

                st.warning(
                    "اسم المستخدم يجب أن يكون "
                    "3-30 حرفًا إنجليزية أو أرقامًا."
                )

            elif len(new_password) < 8:

                st.warning(
                    "كلمة المرور يجب أن تكون "
                    "8 أحرف على الأقل."
                )

            elif new_password != confirm_password:

                st.error(
                    "كلمتا المرور غير متطابقتين."
                )

            elif get_user(new_username):

                st.error(
                    "اسم المستخدم موجود مسبقًا."
                )

            else:

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

                    "stripe_customer_id":
                        "",

                    "subscription_status":
                        "trial",

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
                        "لديك 7 أيام مجانية."
                    )

                else:

                    st.error(
                        "❌ فشل إنشاء الحساب. "
                        "تحقق من Supabase."
                    )

    st.markdown(
        "</div>",
        unsafe_allow_html=True
    )

    st.stop()


# =========================================================
# 21. ADMIN DASHBOARD
# =========================================================

if (
    st.session_state.username
    == ADMIN_USERNAME
    and st.session_state.page
    == "admin"
):

    st.title(
        "👑 لوحة تحكم المسؤول"
    )

    st.success(
        "أنت مسجل كمسؤول — لا يحتاج حساب المسؤول إلى اشتراك."
    )

    users = supabase_request(
        "users_subscriptions",
        "GET"
    )

    if not isinstance(users, list):
        users = []

    total_users = len(users)

    trial_users = sum(
        1
        for u in users
        if trial_is_active(u)
    )

    paid_users = sum(
        1
        for u in users
        if u.get(
            "subscription_status"
        ) == "active"
    )

    expired_users = sum(
        1
        for u in users
        if not account_has_access(u)
    )

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "👥 المستخدمون",
            total_users
        )

    with c2:

        st.metric(
            "🎁 تجربة نشطة",
            trial_users
        )

    with c3:

        st.metric(
            "💳 مدفوعون",
            paid_users
        )

    with c4:

        st.metric(
            "⚠️ منتهون",
            expired_users
        )

    st.divider()

    st.subheader(
        "👥 جميع المستخدمين"
    )

    if users:

        display = []

        for user in users:

            display.append({

                "ID":
                    user.get("id"),

                "Username":
                    user.get("username"),

                "Status":
                    user.get(
                        "subscription_status"
                    ),

                "Trial End":
                    user.get(
                        "trial_end_date"
                    ),

                "Stripe":
                    user.get(
                        "stripe_customer_id"
                    ),

                "Created":
                    user.get(
                        "created_at"
                    )

            })

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "لا يوجد مستخدمون."
        )

    st.stop()


# =========================================================
# 22. PLANS
# =========================================================

if st.session_state.page == "plans":

    st.title(
        "💳 الاشتراك"
    )

    if st.session_state.checkout_message:

        st.success(
            st.session_state.checkout_message
        )

        st.session_state.checkout_message = ""

    st.markdown(
        """
        <div class="plan-card">

        <h2>⭐ Smart AI Pro</h2>

        <h1>$19.99 / شهر</h1>

        <p>✓ مساعد الذكاء الاصطناعي</p>
        <p>✓ تحليل الصور والملفات</p>
        <p>✓ استخدام موسع</p>
        <p>✓ أولوية أفضل</p>

        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button(
        "💳 اشترك الآن",
        type="primary",
        use_container_width=True
    ):

        url, error = create_checkout_session(
            st.session_state.username
        )

        if error:

            st.error(error)

        elif url:

            st.link_button(
                "فتح صفحة الدفع",
                url,
                use_container_width=True
            )

    st.stop()


# =========================================================
# 23. ACCESS CHECK
# =========================================================

# ADMIN ALWAYS HAS ACCESS
is_admin = (
    st.session_state.username
    == ADMIN_USERNAME
)

if not is_admin:

    current_user = get_user(
        st.session_state.username
    )

    st.session_state.user_data = current_user

    if not account_has_access(
        current_user
    ):

        st.title(
            "🔒 انتهت صلاحية الوصول"
        )

        st.warning(
            "انتهت التجربة المجانية أو لا يوجد اشتراك نشط."
        )

        if st.button(
            "💳 عرض الاشتراك",
            type="primary"
        ):

            st.session_state.page = "plans"
            st.rerun()

        st.stop()

else:

    current_user = None


# =========================================================
# 24. MAIN CHAT
# =========================================================

st.markdown(
    """
    <div class="chat-header">

    <h1>🤖 المساعد الذكي</h1>

    <p>
    اسأل Smart AI عن أي شيء.
    يمكنك أيضًا رفع الصور والملفات لتحليلها.
    </p>

    </div>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 25. STATUS
# =========================================================

if is_admin:

    st.success(
        "👑 وضع المسؤول — وصول كامل"
    )

else:

    if current_user.get(
        "subscription_status"
    ) == "active":

        st.success(
            "💳 اشتراكك نشط."
        )

    else:

        st.info(
            f"🎁 التجربة المجانية — "
            f"متبقي {days_left(current_user)} يوم."
        )


# =========================================================
# 26. FILE UPLOAD
# =========================================================

st.subheader(
    "📎 الملفات والصور والصوت والفيديو"
)

uploaded_file = st.file_uploader(
    "ارفع ملفًا للتحليل",
    type=[
        "jpg",
        "jpeg",
        "png",
        "webp",
        "pdf",
        "txt",
        "csv",
        "mp3",
        "wav",
        "mp4",
        "mov",
        "webm"
    ]
)

if uploaded_file:

    st.markdown(
        f"""
        <div class="file-box">
        📄 <b>{uploaded_file.name}</b><br>
        النوع: {uploaded_file.type}<br>
        الحجم: {uploaded_file.size / 1024:.1f} KB
        </div>
        """,
        unsafe_allow_html=True
    )

    file_question = st.text_input(
        "ماذا تريد أن أفعل بهذا الملف؟",
        placeholder="مثال: لخص الملف، حلل الصورة، اشرح الفيديو..."
    )

    if st.button(
        "🔍 تحليل الملف",
        type="primary"
    ):

        with st.spinner(
            "جاري تحليل الملف..."
        ):

            result = analyze_uploaded_file(
                uploaded_file,
                file_question
            )

        st.markdown(
            "### 🤖 النتيجة"
        )

        st.markdown(
            result
        )


# =========================================================
# 27. CHAT HISTORY
# =========================================================

for message in st.session_state.messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )


# =========================================================
# 28. CHAT INPUT
# =========================================================

user_input = st.chat_input(
    "اكتب سؤالك هنا..."
)

if user_input:

    user_input = user_input.strip()

    if not user_input:
        st.stop()

    MAX_SESSION_MESSAGES = 100

    if (
        st.session_state.session_message_count
        >= MAX_SESSION_MESSAGES
    ):

        st.error(
            "وصلت إلى الحد الأقصى لهذه الجلسة."
        )

        st.stop()

    st.session_state.session_message_count += 1

    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_input
        }
    )

    with st.chat_message(
        "user"
    ):

        st.markdown(
            user_input
        )

    with st.chat_message(
        "assistant"
    ):

        bot_response = st.write_stream(
            generate_ai_stream(
                user_input
            )
        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": bot_response
        }
    )
