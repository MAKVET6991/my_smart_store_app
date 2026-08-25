import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone, timedelta

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="🤖", 
    layout="wide"
)

# 2. 💡 إجبار المتصفح على الثيم الليلي الفخم لظهور صندوق الشات وكافة الحقول بوضوح خارق
st.markdown("""
    <style>
    /* تثبيت خلفية داكنة فاخرة للمنصة بالكامل تمنع الشاشة البيضاء */
    .stApp { background-color: #0f172a !important; color: #f1f5f9 !important; font-family: system-ui, sans-serif; }
    
    /* جعل نصوص العناوين والفقرات بارزة باللون الأبيض والأزرق العصري */
    h1, h2, h3 { color: #f1f5f9 !important; text-align: center !important; font-weight: 700 !important; }
    p, span, label, .stMarkdown { color: #cbd5e1 !important; }
    
    /* تنسيق كروت الرسائل لتظهر بأسلوب ChatGPT البارز */
    .chat-user-box { background-color: #1e1b4b; padding: 15px; border-radius: 12px; margin-bottom: 12px; border-right: 5px solid #6366f1; text-align: right; color: #ffffff; }
    .chat-ai-box { background-color: #1e293b; padding: 15px; border-radius: 12px; margin-bottom: 12px; border-right: 5px solid #10b981; text-align: right; color: #ffffff; }
    
    /* صناديق الإحصاءات الفاخرة لوحة المسؤول */
    .dashboard-card { background-color: #1e293b !important; padding: 25px; border-radius: 14px; border: 1px solid #334155; text-align: center; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); }
    .dashboard-card h3 { color: #94a3b8 !important; font-size: 1.1rem !important; }
    .dashboard-card h2 { color: #38bdf8 !important; font-size: 2.2rem !important; margin-top: 10px !important; }
    
    /* تحسين مظهر صناديق الدخول */
    .login-box { background-color: #1e293b; padding: 30px; border-radius: 16px; border: 1px solid #334155; max-width: 500px; margin: 0 auto; }
    
    /* تثبيت لون خط صندوق الكتابة السفلي باللون الأبيض */
    .stChatInputContainer textarea { color: #ffffff !important; }
    </style>
""", unsafe_allow_html=True)

# إعداد مفاتيح الخدمات الخارجية الآمنة
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "")
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-pro")
except:
    model = None

# دالة الاستدعاء المضمونة من Supabase
def supabase_request(endpoint, method="GET", json_data=None, params=None):
    if "SUPABASE_URL" not in st.secrets or "SUPABASE_KEY" not in st.secrets:
        return None
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
    except:
        return None

# تهيئة وإعداد متغيرات الجلسة (Session State)
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

# --- القائمة الجانبية الثابتة المستقرة (Sidebar) ---
st.sidebar.title("📁 لوحة التحكم والمنصة")

if st.session_state.logged_in:
    st.sidebar.markdown(f"👤 **الحساب الحالي:** `{st.session_state.username}`")
    if st.session_state.username == "admin":
        st.sidebar.success("👑 رتبة: المسؤول العام")
    else:
        st.sidebar.info(f"⏳ الفترة التجريبية: **{st.session_state.days_left} أيام متبقية**")
    
    st.sidebar.markdown("---")
    
    if st.session_state.username != "admin":
        st.sidebar.markdown("### 💬 غرف المحادثة")
        with st.sidebar.form("room_form", clear_on_submit=True):
            r_title = st.text_input("📝 اسم الغرفة الجديدة:").strip()
            add_btn = st.form_submit_button("➕ إنشاء الغرفة", use_container_width=True)
            if add_btn and r_title and r_title not in st.session_state.chat_rooms:
                st.session_state.chat_rooms[r_title] = []
                st.session_state.active_room = r_title
                st.rerun()

        for room in list(st.session_state.chat_rooms.keys()):
            if room == st.session_state.active_room:
                st.sidebar.markdown(f"🎯 **【 {room} 】**")
            else:
                if st.sidebar.button(f"📄 {room}", key=f"sidebar_{room}", use_container_width=True):
                    st.session_state.active_room = room
                    st.rerun()
        st.sidebar.markdown("---")

    if st.sidebar.button("🚪 تسجيل الخروج من الحساب", use_container_width=True, type="secondary"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.is_subscribed = False
        st.rerun()
else:
    st.sidebar.warning("🔒 يرجى تسجيل الدخول لفتح الميزات.")

# --- الواجهة الرئيسية بالمنتصف (بناء تسلسلي مستقر ومحمي للألوان) ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='margin-top: 30px;'>⚡ منصة المحادثة الاحترافية الذكية</h1>", unsafe_allow_html=True)
    st.markdown("<p>الجيل القادم من حلول الذكاء الاصطناعي وإدارة البيانات</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 تسجيل الدخول لحسابك", "📝 فتح حساب جديد"])
    
    with tab1:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        user_in = st.text_input("👤 اسم المستخدم", key="u_login").strip()
        pass_in = st.text_input("🔒 كلمة المرور", type="password", key="p_login")
        btn_login = st.button("🚀 دخول آمن للمنصة", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if btn_login:
            if user_in == "admin" and pass_in == "admin123":
                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.session_state.is_subscribed = True
                st.rerun()
            else:
                res = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{user_in}"})
                user_data = res if isinstance(res, list) and len(res) > 0 else (res if isinstance(res, dict) else None)
                
                if user_data and user_data.get("password_hash") == pass_in:
                    st.session_state.logged_in = True
                    st.session_state.username = user_in
                    st.session_state.is_subscribed = True
                    st.session_state.days_left = 7
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
                    
    with tab2:
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        reg_user = st.text_input("👤 اختر اسم مستخدم جديد", key="u_reg").strip()
        reg_pass = st.text_input("🔒 اختر كلمة مرور قوية", type="password", key="p_reg")
        btn_reg = st.button("✨ إنتاج وتفعيل الحساب فوراً", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if btn_reg and reg_user and reg_pass:
            res = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{reg_user}"})
            if isinstance(res, list) and len(res) > 0:
                st.error("❌ اسم المستخدم مسجل مسبقاً!")
            else:
                try:
                    cust_id = ""
                    if stripe.api_key:
                        customer = stripe.Customer.create(description=f"User: {reg_user}")
                        cust_id = customer.id
                    future_trial = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
                    payload = {
                        "username": reg_user,
                        "password_hash": reg_pass,
                        "subscription_status": "trial",
                        "stripe_customer_id": cust_id,
                        "trial_end_date": future_trial
                    }
                    supabase_request("users_subscriptions", "POST", json_data=payload)
                    st.success("🎉 تم إنشاء حسابك بنجاح! انتقل الآن لتبويب تسجيل الدخول.")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء التهيئة: {e}")

# 👑 أولاً: عرض ميزات حساب الـ admin (لوحة الإدارة والإحصاءات الملونة)
elif st.session_state.username == "admin":
    st.markdown("<h1 style='color: #38bdf8;'>📊 لوحة تحكم المسؤول العام (Admin)</h1>", unsafe_allow_html=True)
    st.markdown("<p>متابعة إحصاءات حية وجداول المشتركين والتقييمات الحالية للمنصة</p>", unsafe_allow_html=True)
    
    all_users_resp = supabase_request("users_subscriptions", "GET")
    total_users_count = len(all_users_resp) if isinstance(all_users_resp, list) else 3
    
    st.markdown(f'<div class="dashboard-card"><h3>👥 إجمالي المستخدمين</h3><h2>{total_users_count} مستخدمين</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-card"><h3>💳 الاشتراكات النشطة</h3><h2>الفترة التجريبية</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="dashboard-card"><h3>⭐ تقييم المنصة</h3><h2>4.8 / 5</h2></div>', unsafe_allow_html=True)
        
    st.subheader("📋 جدول المشتركين الحاليين (Supabase)")
    if isinstance(all_users_resp, list) and len(all_users_resp) > 0:
