import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone

# 1. إعداد عنوان وتصميم الصفحة بألوان زاهية ومشرقة
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="💬", 
    layout="centered"
)

# تنسيق المظهر العصري الزاهي والمبهج (Light Mode)
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    .stChatInputContainer { border-radius: 12px; border: 1px solid #cbd5e1 !important; background-color: #ffffff !important;}
    h1 { color: #4f46e5 !important; text-align: center; font-family: 'Segoe UI', sans-serif; }
    p { text-align: center; color: #64748b; }
    .login-box { padding: 20px; border-radius: 12px; background-color: #ffffff; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05); }
    .file-box { padding: 10px; border-radius: 8px; background-color: #f0fdf4; margin-bottom: 10px; border: 1px dashed #22c55e; color: #166534; }
    .admin-box { padding: 12px; border-radius: 8px; background-color: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; margin-top: 10px; }
    .trial-box { padding: 10px; border-radius: 8px; background-color: #fef3c7; border: 1px solid #fde68a; color: #92400e; margin-bottom: 15px; text-align: center; font-weight: bold; }
    .pay-box { padding: 20px; border-radius: 12px; background-color: #fff1f2; border: 1px solid #fecdd3; color: #9f1239; text-align: center; }
    .room-btn { margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# إعداد مكتبة Stripe بالمفتاح السري لشركتكِ
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

# دالة مساعدة للاتصال بقاعدة بيانات Supabase عبر REST API
def supabase_request(endpoint, method="GET", json_data=None, params=None):
    url = f"{st.secrets['SUPABASE_URL']}/rest/v1/{endpoint}"
    headers = {
        "apikey": st.secrets["SUPABASE_KEY"],
        "Authorization": f"Bearer {st.secrets['SUPABASE_KEY']}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=json_data)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=json_data, params=params)
        return response.json()
    except Exception as e:
        return []

# 2. تهيئة حالات الذاكرة المؤقتة للمتصفح الحالي
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_subscribed" not in st.session_state:
    st.session_state.is_subscribed = False
if "days_left" not in st.session_state:
    st.session_state.days_left = 0

# تهيئة مخزن الغرف المتعددة في الذاكرة الحالية
if "chat_rooms" not in st.session_state:
    st.session_state.chat_rooms = {"محادثة افتراضية 1": []}
if "active_room" not in st.session_state:
    st.session_state.active_room = "محادثة افتراضية 1"

# 3. شاشة إدارة الحسابات السحابية (تسجيل دخول / إنشاء حساب جديد)
if not st.session_state.logged_in:
    st.title("🔐 بوابة الوصول للمنصة العالمية المدفوعة")
    st.write("سجّل حسابك الآن للحصول على 7 أيام تجريبية مجانية كاملة الميزات")
    
    tab1, tab2 = st.tabs(["🔑 تسجيل الدخول", "📝 إنشاء حساب جديد"])
    
    with tab1:
        with st.container():
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            username_input = st.text_input("اسم المستخدم", key="login_user").strip()
            password_input = st.text_input("كلمة المرور", type="password", key="login_pass")
            login_button = st.button("تسجيل الدخول", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if login_button:
                if username_input == "admin" and password_input == "admin123":
                    st.session_state.logged_in = True
                    st.session_state.username = "admin"
                    st.session_state.is_subscribed = True
                    st.success("تم دخول المسؤولة بنجاح!")
                    st.rerun()
                else:
                    user_data = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{username_input}"})
                    if user_data and user_data["password_hash"] == password_input:
                        u = user_data
                        st.session_state.logged_in = True
                        st.session_state.username = username_input
                        
                        trial_end = datetime.fromisoformat(u["trial_end_date"].replace("Z", "+00:00"))
                        now = datetime.now(timezone.utc)
                        delta = (trial_end - now).days + 1
                        st.session_state.days_left = max(0, delta)
                        
                        if u["subscription_status"] == "active" or st.session_state.days_left > 0:
                            st.session_state.is_subscribed = True
                        else:
                            st.session_state.is_subscribed = False
                            
                        st.success(f"مرحباً بك مجدداً {username_input}!")
                        st.rerun()
                    else:
                        st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                    
    with tab2:
        with st.container():
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            new_username = st.text_input("اختر اسم مستخدم جديد", key="reg_user").strip()
            new_password = st.text_input("اختر كلمة مرور", type="password", key="reg_pass")
            register_button = st.button("تأكيد وإنشاء الحساب", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if register_button:
                if not new_username or not new_password:
                    st.error("الرجاء ملء جميع الحقول أولاً!")
                else:
                    check_user = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{new_username}"})
                    if check_user:
                        st.error("اسم المستخدم هذا مسجل مسبقاً! اختر اسماً آخر.")
                    else:
                        try:
                            customer = stripe.Customer.create(description=f"User: {new_username}")
                            new_user_payload = {
                                "username": new_username,
                                "password_hash": new_password,
                                "subscription_status": "trial",
                                "stripe_customer_id": customer.id
                            }
                            supabase_request("users_subscriptions", "POST", json_data=new_user_payload)
                            st.success("🎉 تم إنشاء حسابك وحفظه بنجاح! اذهب لتبويب (تسجيل الدخول) للبدء فوراً.")
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء تهيئة الحساب المالي: {e}")

# 4. الشاشات بعد الدخول بنجاح (تفحص صلاحية الاشتراك)
else:
    if not st.session_state.is_subscribed:
        st.title("💳 انتهت الفترة التجريبية المجانية")
        st.markdown(f"<div class='pay-box'><h3>عذراً يا {st.session_state.username}، لقد انتهت الـ 7 أيام التجريبية لحسابك!</h3><p>يرجى الاشتراك لتفعيل الحساب ومتابعة استخدام ميزات المساعد الذكي ورفع الملفات الفائقة.</p></div>", unsafe_allow_html=True)
        
        try:
            user_data = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{st.session_state.username}"})
            customer_id = user_data["stripe_customer_id"] if user_data else None
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{'price': st.secrets["STRIPE_PRICE_ID"], 'quantity': 1}],
                mode='subscription',
                customer=customer_id,
                success_url=st.secrets.get("SUPABASE_URL", "https://stripe.com"),
                cancel_url="https://stripe.com",
            )
            st.markdown(f"<br><a href='{session.url}' target='_blank'><button style='width:100%; padding:12px; background-color:#4f46e5; color:white; border:none; border-radius:8px; font-size:18px; cursor:pointer; font-weight:bold;'>💳 اضغط هنا للدفع الآمن عبر Stripe وتفعيل الحساب</button></a>", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"خطأ في إنشاء رابط الدفع: {e}")
            
        if st.button("🚪 العودة للخارج", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    else:
        st.title("💬 غرف المحادثات الاحترافية العالمية")
        
        if st.session_state.username != "admin" and st.session_state.days_left > 0:
            st.markdown(f"<div class='trial-box'>⏱️ أنت الآن في الفترة التجريبية المجانية! متبقي لكِ: {st.session_state.days_left} أيام كاملة الميزات.</div>", unsafe_allow_html=True)
        elif st.session_state.username != "admin":
            st.markdown("<div class='trial-box' style='background-color:#dcfce7; border-color:#86efac; color:#166534;'>✅ اشتراكك مفعّل وحسابك بريميوم بالكامل!</div>", unsafe_allow_html=True)

        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')

        # القائمة الجانبية المحدثة (Sidebar)
        with st.sidebar:
            st.markdown(f"👤 الحساب الحالي: **{st.session_state.username}**")
            st.markdown("---")
            
            # ميزة الغرف المتعددة الجديدة (Multi-Chat Rooms)
            st.markdown("### 🗂️ غرف المحادثة الحالية")
            
            # زر إنشاء غرفة محادثة جديدة
            new_room_name = st.text_input("➕ اسم الغرفة الجديدة", placeholder="اكتب اسم الغرفة واضغط إنتر...")
