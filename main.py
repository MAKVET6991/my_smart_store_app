import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone, timedelta

# 1. إعدادات الهيكل والتصميم العصري (UI/UX)
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="🤖", 
    layout="wide"
)

# تنسيقات الألوان الاحترافية ولون خط أبيض ناصع لحقل الكتابة
st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: #e2e8f0; font-family: system-ui, sans-serif; }
    h1, h2, h3 { color: #f1f5f9 !important; text-align: center !important; font-weight: 700 !important; }
    p { text-align: center !important; color: #94a3b8; }
    .login-container { max-width: 450px; margin: 40px auto; padding: 30px; background: #1e293b; border-radius: 12px; border: 1px solid #334155; }
    
    /* لون خط حقل الكتابة ليصبح أبيض وواضح */
    .stChatInputContainer { border-radius: 10px !important; border: 1px solid #4f46e5 !important; background-color: #1e293b !important; }
    .stChatInputContainer textarea { color: #ffffff !important; font-size: 1rem !important; }
    
    .room-active { background: #4f46e5 !important; color: white !important; font-weight: bold; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 5px; }
    .stChatMessage { background-color: #1e293b !important; border-radius: 10px !important; padding: 12px !important; margin-bottom: 10px !important; }
    .stButton>button { border-radius: 10px !important; }
    
    /* صناديق الإحصاءات بلوحة التحكم */
    .stat-box { background-color: #1e293b; padding: 25px; border-radius: 12px; border: 1px solid #334155; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.2); }
    .stat-box h3 { color: #94a3b8 !important; font-size: 1.2rem !important; margin-bottom: 10px !important; }
    .stat-box h2 { color: #818cf8 !important; font-size: 2.2rem !important; margin: 0 !important; }
    </style>
""", unsafe_allow_html=True)

# إعداد مفاتيح الخدمات الخارجية
stripe.api_key = st.secrets.get("STRIPE_SECRET_KEY", "")
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-pro")
except:
    model = None

# دالة الاستدعاء المعدلة والمضمونة لجلب بيانات المستخدمين
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

# --- القائمة الجانبية الثابتة (Sidebar Navigation) ---
st.sidebar.title("📁 التحكم والمنصة")

if st.session_state.logged_in:
    st.sidebar.markdown(f"👤 **الحساب:** {st.session_state.username}")
    if st.session_state.username == "admin":
        st.sidebar.markdown("⭐ **الرتبة:** مسؤول النظام العام")
    else:
        st.sidebar.markdown(f"⏳ المتبقي المالي: **{st.session_state.days_left}** يوم")
    
    st.sidebar.markdown("---")
    
    # ميزات المستخدمين العاديين فقط
    if st.session_state.username != "admin":
        with st.sidebar.form("room_form", clear_on_submit=True):
            r_title = st.text_input("اسم الغرفة الجديدة:").strip()
            add_btn = st.form_submit_button("➕ إنشاء غرفة", use_container_width=True)
            if add_btn and r_title and r_title not in st.session_state.chat_rooms:
                st.session_state.chat_rooms[r_title] = []
                st.session_state.active_room = r_title
                st.rerun()

        st.sidebar.markdown("### الغرف الحالية:")
        for room in list(st.session_state.chat_rooms.keys()):
            if room == st.session_state.active_room:
                st.sidebar.markdown(f'<div class="room-active">💬 {room}</div>', unsafe_allow_html=True)
            else:
                if st.sidebar.button(f"📄 {room}", key=f"r_{room}", use_container_width=True):
                    st.session_state.active_room = room
                    st.rerun()
        st.sidebar.markdown("---")

    # زر تسجيل الخروج الثابت
    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.is_subscribed = False
        st.rerun()
else:
    st.sidebar.info("🔒 يرجى الدخول لإظهار الغرف والتحكم.")

# --- منطقة العرض والأقسام الرئيسية بالمنتصف ---
if not st.session_state.logged_in:
    st.markdown("<h1>⚡ المنصة الذكية المتكاملة</h1>", unsafe_allow_html=True)
    st.markdown("<p>سجل دخولك الآن للوصول إلى أدوات الذكاء الاصطناعي وغرف التحكم</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 تسجيل الدخول", "📝 حساب جديد"])
    
    with tab1:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        user_in = st.text_input("اسم المستخدم", key="u_login").strip()
        pass_in = st.text_input("كلمة المرور", type="password", key="p_login")
        btn_login = st.button("🚀 دخول آمن", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if btn_login:
            if user_in == "admin" and pass_in == "admin123":
                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.session_state.is_subscribed = True
                st.rerun()
            else:
                res = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{user_in}"})
                
                # 🛠️ الحل النهائي والأكيد: استخراج الحساب الصحيح سواء رجعت الاستجابة كقائمة أو قاموس
                user_data = None
                if isinstance(res, list) and len(res) > 0:
                    user_data = res[0]
                elif isinstance(res, dict):
                    user_data = res
                
                # مطابقة البيانات الحقيقية المستخرجة والسماح للمستخدم بالولوج
                if user_data and user_data.get("password_hash") == pass_in:
                    st.session_state.logged_in = True
                    st.session_state.username = user_in
                    st.session_state.is_subscribed = True
                    
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
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
                    
    with tab2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        reg_user = st.text_input("اختر اسم مستخدم جديد", key="u_reg").strip()
        reg_pass = st.text_input("اختر كلمة مرور جديدة", type="password", key="p_reg")
        btn_reg = st.button("✨ إنشاء الحساب وتفعيله", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if btn_reg and reg_user and reg_pass:
            res = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{reg_user}"})
            if isinstance(res, list) and len(res) > 0:
                st.error("❌ اسم المستخدم مسجل مسبقاً! اختر اسماً آخر.")
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
                    st.success("🎉 تم إنشاء حسابك بنجاح! توجه الآن لتبويب (تسجيل الدخول).")
                except Exception as e:
                    st.error(f"حدث خطأ أثناء التهيئة: {e}")

else:
    # 👑 أولاً: لوحة المسؤول (Admin Dashboard)
    if st.session_state.username == "admin":
        st.markdown("<h1>📊 لوحة تحكم المسؤول العام (Admin)</h1>", unsafe_allow_html=True)
