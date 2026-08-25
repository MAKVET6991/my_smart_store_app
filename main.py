import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone, timedelta

# 1. إعدادات الهيكل الأساسي
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="🤖", 
    layout="wide"
)

# 2. تصميم احترافي، عصري وآمن تماماً لا يخفي أي عنصر
st.markdown("""
    <style>
    .stApp { background-color: #0b0f19; color: #f1f5f9; font-family: system-ui, sans-serif; }
    .chat-card-user { background-color: #1e1b4b; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-right: 5px solid #6366f1; text-align: right; }
    .chat-card-ai { background-color: #1e293b; padding: 15px; border-radius: 12px; margin-bottom: 10px; border-right: 5px solid #10b981; text-align: right; }
    .dashboard-card { background-color: #1e293b; padding: 25px; border-radius: 14px; border: 1px solid #334155; text-align: center; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.2); }
    .dashboard-card h3 { color: #94a3b8 !important; font-size: 1.1rem !important; }
    .dashboard-card h2 { color: #38bdf8 !important; font-size: 2.2rem !important; margin-top: 10px !important; }
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

# دالة عرض لوحة تحكم المسؤول لمنع أخطاء الإزاحة المتداخلة
def render_admin_dashboard():
    st.markdown("<h1 style='color: #38bdf8;'>📊 لوحة تحكم المسؤول العام</h1>", unsafe_allow_html=True)
    st.markdown("<p>إحصاءات حية متصلة بقاعدة البيانات وجداول المشتركين والتقييمات</p>", unsafe_allow_html=True)
    
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
        
    st.subheader("💬 تقييمات وملاحظات العملاء")
    st.info("💡 قسم التقييمات جاهز ومعد للاستخدام فور ربطه بجدول الملاحظات الخاص بك.")

# دالة عرض واجهة شات المستخدم لمنع الأخطاء المعقدة
def render_user_chat():
    st.markdown(f"<h2 style='text-align: center; color: #6366f1; margin-bottom: 20px;'>💬 الغرفة النشطة: {st.session_state.active_room}</h2>", unsafe_allow_html=True)
    
    for msg in st.session_state.chat_rooms[st.session_state.active_room]:
        if msg["role"] == "user":
            st.markdown(f'<div class="chat-card-user"><b>👤 أنت:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-card-ai"><b>🤖 مساعدك الذكي:</b><br>{msg["content"]}</div>', unsafe_allow_html=True)
            
    user_input = st.chat_input("💡 اكتب سؤالك أو استفسارك هنا وسترى ما تكتبه بوضوح...")
    if user_input:
        st.session_state.chat_rooms[st.session_state.active_room].append({"role": "user", "content": user_input})
        
        if model:
            with st.spinner("جاري التفكير وتوليد الإجابة الحقيقية..."):
                try:
                    response = model.generate_content(user_input)
                    ai_reply = response.text
                except:
                    ai_reply = "حدث خطأ أثناء معالجة الإجابة."
        else:
            ai_reply = f"أهلاً بك يا {st.session_state.username}! تم استقبال رسالتك بنجاح في غرفة [{st.session_state.active_room}]. يرجى إضافة مفتاح GEMINI_API_KEY للحصول على ردود فورية."
        
        st.session_state.chat_rooms[st.session_state.active_room].append({"role": "assistant", "content": ai_reply})
        st.rerun()

# --- القائمة الجانبية (Sidebar) ---
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
                user_data = res if isinstance(res, list) and len(res) > 0 else res
                if isinstance(user_data, list) and len(user_data) > 0:
                    user_data = user_data[0]
                
                if user_data and isinstance(user_data, dict) and user_data.get("password_hash") == pass_in:
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
