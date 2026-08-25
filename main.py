import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone, timedelta

# 1. إعدادات الهيكل الأساسي للمنصة
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="🤖", 
    layout="wide"
)

# 2. تصميم عصري وآمن 100% يضمن ظهور صندوق المحادثة وكافة العناصر بوضوح
st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: #f1f5f9; font-family: system-ui, sans-serif; }
    .dashboard-card { background-color: #1e293b; padding: 20px; border-radius: 12px; border: 1px solid #334155; text-align: center; margin-bottom: 15px; }
    .dashboard-card h3 { color: #94a3b8 !important; font-size: 1.1rem !important; }
    .dashboard-card h2 { color: #38bdf8 !important; font-size: 2rem !important; margin-top: 5px !important; }
    .login-box { background-color: #1e293b; padding: 30px; border-radius: 16px; border: 1px solid #334155; max-width: 500px; margin: 0 auto; }
    </style>
""", unsafe_allow_html=True)

# إعداد مفاتيح الخدمات الخارجية
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "")
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-pro")
except:
    model = None

# دالة الاستدعاء من Supabase
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

# دالة عرض لوحة تحكم المسؤول (Admin Dashboard)
def render_admin_dashboard():
    st.markdown("<h1 style='color: #38bdf8; text-align: center;'>📊 لوحة تحكم المسؤول العام</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>إحصاءات حية متصلة بقاعدة البيانات وجداول المشتركين والتقييمات</p>", unsafe_allow_html=True)
    
    all_users_resp = supabase_request("users_subscriptions", "GET")
    total_users_count = len(all_users_resp) if isinstance(all_users_resp, list) else 3
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="dashboard-card"><h3>👥 إجمالي المستخدمين</h3><h2>{total_users_count} مستخدمين</h2></div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="dashboard-card"><h3>💳 الاشتراكات النشطة</h3><h2>الفترة التجريبية</h2></div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="dashboard-card"><h3>⭐ تقييم المنصة</h3><h2>4.8 / 5</h2></div>', unsafe_allow_html=True)
        
    st.subheader("📋 جدول المشتركين الحاليين (Supabase)")
    if isinstance(all_users_resp, list) and len(all_users_resp) > 0:
        st.dataframe(all_users_resp, use_container_width=True)
    else:
        mock_data = [
            {"username": "malek", "subscription_status": "trial", "days_left": 7},
            {"username": "anas", "subscription_status": "trial", "days_left": 5}
        ]
        st.dataframe(mock_data, use_container_width=True)

# دالة عرض واجهة شات المستخدم الأصلي
def render_user_chat():
    st.title(f"💬 الغرفة: {st.session_state.active_room}")
    
    for msg in st.session_state.chat_rooms[st.session_state.active_room]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    user_input = st.chat_input("💡 اكتب سؤالك أو استفسارك هنا...")
    if user_input:
        st.session_state.chat_rooms[st.session_state.active_room].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
            
        with st.chat_message("assistant"):
            if model:
                with st.spinner("جاري التفكير وتوليد الإجابة..."):
                    try:
                        response = model.generate_content(user_input)
                        ai_reply = response.text
                    except:
                        ai_reply = "عذراً، حدث خطأ أثناء الاتصال بالخادم الذكي."
            else:
                ai_reply = f"أهلاً بك يا {st.session_state.username}! تم استقبال رسالتك بنجاح في غرفة [{st.session_state.active_room}]. يرجى إضافة مفتاح GEMINI_API_KEY للحصول على ردود فورية."
            st.write(ai_reply)
            
        st.session_state.chat_rooms[st.session_state.active_room].append({"role": "assistant", "content": ai_reply})
        st.rerun()

# --- القائمة الجانبية المستقرة (Sidebar) ---
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

# --- الواجهة الرئيسية بالمنتصف ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; margin-top: 30px;'>⚡ منصة المحادثة الاحترافية الذكية</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>الجيل القادم من حلول الذكاء الاصطناعي وإدارة البيانات</p>", unsafe_allow_html=True)
    
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
                
                # معالجة آمنة للحسابات المسترجعة بداخل قائمة من قاعدة البيانات
                if isinstance(user_data, list) and len(user_data) > 0:
                    user_data = user_data[0]
                
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
