import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone, timedelta

# 1. إعادة إعداد عنوان وتصميم الصفحة
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="💬", 
    layout="wide"
)

# تنسيق المظهر العصري للمنصة
st.markdown("""
    <style>
    .stApp { background-color: #1e293b; color: #f8fafc; }
    .stChatInputContainer { 
        border-radius: 12px; 
        border: 2px solid #4f46e5 !important; 
        background-color: #334155 !important;
    }
    .stChatInputContainer textarea { color: #ffffff !important; }
    h1, h2, h3 { color: #818cf8 !important; text-align: center !important; font-family: 'Segoe UI', sans-serif; }
    p, .stMarkdown { text-align: center !important; color: #94a3b8; }
    .login-box { padding: 20px; border-radius: 12px; background-color: #334155; border: 1px solid #475569; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); margin: 0 auto; max-width: 500px; }
    .file-box { padding: 10px; border-radius: 8px; background-color: #064e3b; margin-bottom: 10px; border: 1px dashed #10b981; color: #a7f3d0; }
    .stChatMessage { background-color: #334155 !important; border-radius: 10px; margin-bottom: 10px; padding: 10px; color: #f8fafc !important; }
    .room-active { background-color: #4f46e5 !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 8px; text-align: center; margin-bottom: 5px; }
    </style>
""", unsafe_allow_html=True)

# إعداد مفتاح Stripe
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

# دالة التعامل مع قاعدة بيانات Supabase
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
        
        res_json = response.json()
        if isinstance(res_json, list) and len(res_json) > 0:
            return res_json[0]
        return res_json
    except Exception as e:
        return None

# تهيئة متغيرات الجلسة (Session State)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_subscribed" not in st.session_state:
    st.session_state.is_subscribed = False
if "days_left" not in st.session_state:
    st.session_state.days_left = 0
if "chat_rooms" not in st.session_state or not st.session_state.chat_rooms:
    st.session_state.chat_rooms = {"المحادثة الرئيسية 🌟": []}
if "active_room" not in st.session_state or st.session_state.active_room not in st.session_state.chat_rooms:
    st.session_state.active_room = "المحادثة الرئيسية 🌟"
if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""

# بوابة تسجيل الدخول وإنشاء الحسابات
if not st.session_state.logged_in:
    st.title("🔐 بوابة الوصول للمنصة العالمية المدفوعة")
    st.write("سجّل حسابك الآن للحصول على 7 أيام تجريبية مجانية كاملة الميزات")
    
    tab1, tab2 = st.tabs(["🔑 تسجيل الدخول", "📝 إنشاء حساب جديد"])
    
    with tab1:
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
                st.success("تم دخول المسؤول بنجاح!")
                st.rerun()
            else:
                user_data = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{username_input}"})
                if user_data and user_data.get("password_hash") == password_input:
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    
                    try:
                        trial_end_str = user_data.get("trial_end_date")
                        if trial_end_str:
                            trial_end = datetime.fromisoformat(trial_end_str.replace("Z", "+00:00"))
                        else:
                            trial_end = datetime.now(timezone.utc) + timedelta(days=7)
                        
                        now = datetime.now(timezone.utc)
                        st.session_state.days_left = max(0, (trial_end - now).days + 1)
                    except:
                        st.session_state.days_left = 7
                    
                    st.session_state.is_subscribed = True
                    st.success(f"مرحباً بك مجدداً {username_input}!")
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                
    with tab2:
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
                        future_trial = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                        
                        new_user_payload = {
                            "username": new_username,
                            "password_hash": new_password,
                            "subscription_status": "trial",
                            "stripe_customer_id": customer.id,
                            "trial_end_date": future_trial
                        }
                        supabase_request("users_subscriptions", "POST", json_data=new_user_payload)
                        st.success("🎉 تم إنشاء حسابك بنجاح! اذهب لتبويب (تسجيل الدخول).")
                    except Exception as e:
                        st.error(f"حدث خطأ أثناء تهيئة الحساب المالي: {e}")

# تشغيل ميزات المنصة بالكامل بعد الدخول الصحيح
else:
    payment_link_url = ""
    if st.session_state.username != "admin" and st.session_state.days_left <= 0:
        st.session_state.is_subscribed = False
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
            payment_link_url = session.url
        except:
            pass

    # إعداد شريط غرف المحادثة الجانبي
    st.sidebar.title("💬 غرف المحادثة")
    
    with st.sidebar.form("add_room_form", clear_on_submit=True):
        r_title = st.text_input("اسم الغرفة الجديدة:").strip()
        submit_room = st.form_submit_button("إضافة غرفة")
        
        if submit_room and r_title:
            if r_title not in st.session_state.chat_rooms:
                st.session_state.chat_rooms[r_title] = []
                st.session_state.active_room = r_title
                st.success(f"تم إنشاء غرفة: {r_title}")
                st.rerun()
            else:
                st.warning("هذه الغرفة موجودة بالفعل!")

    # التنقل بين الغرف المتوفرة
    for room in list(st.session_state.chat_rooms.keys()):
        if room == st.session_state.active_room:
            st.sidebar.markdown(f'<div class="room-active">{room}</div>', unsafe_allow_html=True)
        else:
            if st.sidebar.button(room, key=f"btn_{room}", use_container_width=True):
                st.session_state.active_room = room
                st.rerun()

    # واجهة عرض المحادثة والرسائل
    st.title(f"🤖 {st.session_state.active_room}")
    
    for msg in st.session_state.chat_rooms[st.session_state.active_room]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    # التحكم بصلاحيات الإرسال بناءً على حالة الاشتراك (القسم المصلح بالكامل)
    if not st.session_state.is_subscribed:
        st.warning("⚠️ انتهت الفترة التجريبية. يرجى تجديد الاشتراك للمتابعة.")
        if payment_link_url:
            st.link_button("💳 اضغط هنا للدفع وتفعيل الاشتراك", payment_link_url, use_container_width=True)
    else:
        user_input = st.chat_input("اكتب رسالتك هنا...")
        if user_input:
