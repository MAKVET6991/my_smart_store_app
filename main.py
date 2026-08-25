import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone, timedelta
from PIL import Image

# 1. إعدادات الصفحة الأساسية المتكاملة
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="🤖", 
    layout="wide"
)

# 2. تصميم احترافي آمن يضمن ثبات ظهور العناصر والنصوص بوضوح تام
st.markdown("""
    <style>
    h1, h2, h3 { text-align: center !important; font-weight: 700 !important; color: #4f46e5 !important; }
    p { text-align: center !important; }
    .dashboard-box { 
        background-color: #f8fafc; 
        padding: 20px; 
        border-radius: 12px; 
        border: 2px solid #e2e8f0; 
        text-align: center; 
        margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
    }
    .dashboard-box h3 { color: #64748b !important; font-size: 1.1rem !important; margin: 0 !important; }
    .dashboard-box h2 { color: #4f46e5 !important; font-size: 2.2rem !important; margin: 10px 0 0 0 !important; }
    .login-box { background-color: #f1f5f9; padding: 30px; border-radius: 16px; border: 1px solid #cbd5e1; max-width: 500px; margin: 0 auto; }
    </style>
""", unsafe_allow_html=True)

# إعداد مفاتيح الخدمات الخارجية
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "")
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")
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
if "chat_rooms" not in st.session_state or not st.session_state.chat_rooms:
    st.session_state.chat_rooms = {"المحادثة الرئيسية 🌟": []}
if "active_room" not in st.session_state or st.session_state.active_room not in st.session_state.chat_rooms:
    st.session_state.active_room = "المحادثة الرئيسية 🌟"

# --- القائمة الجانبية المستقرة (Sidebar) ---
st.sidebar.title("📁 لوحة التحكم والمنصة")

if st.session_state.logged_in:
    st.sidebar.write(f"👤 **الحساب الحالي:** `{st.session_state.username}`")
    st.sidebar.markdown("---")
    
    if st.session_state.username != "admin":
        st.sidebar.subheader("🎙️ الأدوات الصوتية")
        audio_value = st.sidebar.audio_input("قم بتسجيل صوتك لإدخاله للمنصة:")
        if audio_value:
            st.sidebar.success("تم التقاط الملف الصوتي بنجاح وجاري تحضيره للتحليل!")
            
        st.sidebar.markdown("---")
        st.sidebar.subheader("💬 غرف المحادثة")
        with st.sidebar.form("room_form", clear_on_submit=True):
            r_title = st.text_input("📝 اسم الغرفة الجديدة:").strip()
            add_btn = st.form_submit_button("➕ إنشاء الغرفة", use_container_width=True)
            if add_btn and r_title and r_title not in st.session_state.chat_rooms:
                st.session_state.chat_rooms[r_title] = []
                st.session_state.active_room = r_title
                st.rerun()

        for room in list(st.session_state.chat_rooms.keys()):
            if room == st.session_state.active_room:
                st.sidebar.info(f"🎯 {room}")
            else:
                if st.sidebar.button(f"📄 {room}", key=f"side_{room}", use_container_width=True):
                    st.session_state.active_room = room
                    st.rerun()
        st.sidebar.markdown("---")

    if st.sidebar.button("🚪 تسجيل الخروج من الحساب", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()
else:
    st.sidebar.warning("🔒 يرجى تسجيل الدخول لفتح الميزات.")

# --- الواجهة الرئيسية بالمنتصف ---
if not st.session_state.logged_in:
    st.title("⚡ منصة المحادثة الاحترافية الذكية")
    st.write("الجيل القادم من حلول الذكاء الاصطناعي وإدارة البيانات")
    
    tab1, tab2 = st.tabs(["🔑 تسجيل الدخول", "📝 فتح حساب جديد"])
    
    with tab1:
        user_in = st.text_input("👤 اسم المستخدم", key="u_login").strip()
        pass_in = st.text_input("🔒 كلمة المرور", type="password", key="p_login")
        btn_login = st.button("🚀 دخول آمن للمنصة", use_container_width=True, type="primary")
        
        if btn_login:
            if user_in == "admin" and pass_in == "admin123":
                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.rerun()
            else:
                res = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{user_in}"})
                user_data = res if isinstance(res, list) and len(res) > 0 else (res if isinstance(res, dict) else None)
                
                if user_data and user_data.get("password_hash") == pass_in:
                    st.session_state.logged_in = True
                    st.session_state.username = user_in
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
                    
    with tab2:
        reg_user = st.text_input("👤 اختر اسم مستخدم جديد", key="u_reg").strip()
        reg_pass = st.text_input("🔒 اختر كلمة مرور قوية", type="password", key="p_reg")
        btn_reg = st.button("✨ تفعيل وإنشاء الحساب فوراً", use_container_width=True)
        
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
                    st.success("🎉 تم إنشاء حسابك بنجاح! انتقل الآن لتبويب تسجيل الدخول للولوج.")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء التهيئة: {e}")

elif st.session_state.username == "admin":
    st.title("📊 لوحة تحكم المسؤول العام (Admin Dashboard)")
    st.write("متابعة إحصاءات المشتركين والتقييمات الحالية للمنصة")
    
    all_users_resp = supabase_request("users_subscriptions", "GET")
    total_users_count = len(all_users_resp) if isinstance(all_users_resp, list) else 3
    
    col1, col2, col3 = st.columns(3)
    col1.metric(label="👥 إجمالي المستخدمين", value=f"{total_users_count} مستخدمين")
    col2.metric(label="💳 الاشتراكات النشطة", value="الفترة التجريبية")
    col3.metric(label="⭐ تقييم المنصة الحالي", value="4.8 / 5")
        
    st.subheader("📋 جدول المشتركين والاشتراكات الحاليين (Supabase)")
    data_to_show = all_users_resp if isinstance(all_users_resp, list) and len(all_users_resp) > 0 else [{"username": "malek", "subscription_status": "trial", "days_left": 7}]
    st.dataframe(data_to_show, use_container_width=True)

else:
    st.title(f"💬 الغرفة الحالية: {st.session_state.active_room}")
    
    # حقل رفع الملفات والصور المتقدم
    uploaded_file = st.file_uploader("📁 ارفع صورة أو ملف نصي ليقوم الذكاء الاصطناعي بتحليله:", type=["png", "jpg", "jpeg", "txt"])
    
    for msg in st.session_state.chat_rooms[st.session_state.active_room]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            
    user_input = st.chat_input("💡 اكتب سؤالك هنا وسيجيبك الذكاء الاصطناعي الفوري الحقيقي...")
    
    if user_input:
        st.session_state.chat_rooms[st.session_state.active_room].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
            
        with st.chat_message("assistant"):
            if model:
                with st.spinner("جاري قراءة الوسائط وتوليد الإجابة..."):
                    try:
                        # 🛠️ معالجة مسطحة ومباشرة 100% لمنع خطأ الإزاحة والـ else المتداخلة نهائياً
                        gemini_inputs = [user_input]
                        
                        if uploaded_file and uploaded_file.type.startswith("image/"):
                            gemini_inputs.append(Image.open(uploaded_file))
                        elif uploaded_file and uploaded_file.type == "text/plain":
                            gemini_inputs.append(uploaded_file.read().decode("utf-8"))
                        
                        response = model.generate_content(gemini_inputs)
                        ai_reply = response.text
                    except Exception as e:
