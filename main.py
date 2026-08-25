import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone, timedelta

# 1. إعداد هيكل الصفحة الأساسي بتصميم العرض الكامل
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="🤖", 
    layout="wide"
)

# 2. هندسة التصميم والمظهر العصري (CSS) ليحاكي المنصات العالمية
st.markdown("""
    <style>
    /* تحسين الخلفية العامة والخطوط */
    .stApp { 
        background-color: #0f172a; 
        color: #e2e8f0; 
        font-family: 'Inter', 'Segoe UI', system-ui, sans-serif; 
    }
    
    /* تحسين تصميم العناوين والنصوص */
    h1, h2, h3 { 
        color: #f1f5f9 !important; 
        text-align: center !important; 
        font-weight: 700 !important;
    }
    p, .stMarkdown { 
        text-align: center !important;
        color: #94a3b8; 
    }
    
    /* صندوق الدخول المطور */
    .login-container {
        max-width: 480px;
        margin: 40px auto;
        padding: 30px;
        background: #1e293b;
        border-radius: 16px;
        border: 1px solid #334155;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    }
    
    /* شريط المحادثة السفلي العصري */
    .stChatInputContainer { 
        border-radius: 14px !important; 
        border: 1px solid #4f46e5 !important; 
        background-color: #1e293b !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15) !important;
    }
    .stChatInputContainer textarea { color: #f8fafc !important; }
    
    /* غرف المحادثة الجانبية */
    .room-active { 
        background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%) !important; 
        color: #ffffff !important; 
        font-weight: 600; 
        border-radius: 10px; 
        padding: 12px; 
        text-align: right; 
        margin-bottom: 8px;
        box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2);
    }
    
    /* بطاقات الرسائل */
    .stChatMessage { 
        background-color: #1e293b !important; 
        border-radius: 12px !important; 
        border: 1px solid #27272a !important;
        padding: 14px !important; 
        margin-bottom: 12px !important;
    }
    
    /* تحسين أزرار القائمة الجانبية */
    .stButton>button {
        border-radius: 10px !important;
        transition: all 0.2s ease-in-out !important;
    }
    </style>
""", unsafe_allow_html=True)

# إعداد مفتاح ماستر لـ Stripe
stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

# دالة التعامل المحترفة والآمنة مع قاعدة بيانات Supabase
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
            return res_json[0] # إرجاع المستخدم الأول مباشرة
        return res_json
    except Exception as e:
        return None

# تهيئة متغيرات الحفاظ على حالة الجلسة (Session State)
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_subscribed" not in st.session_state:
    st.session_state.is_subscribed = False
if "days_left" not in st.session_state:
    st.session_state.days_left = 0
if "chat_rooms" not in st.session_state or not st.session_state.chat_rooms:
    st.session_state.chat_rooms = {"✨ المحادثة الرئيسية 🌟": []}
if "active_room" not in st.session_state or st.session_state.active_room not in st.session_state.chat_rooms:
    st.session_state.active_room = "✨ المحادثة الرئيسية 🌟"

# --- الحالة الأولى: المستخدم لم يسجل دخوله بعد (عرض صفحة الدخول فقط ونخفي القائمة الجانبية تماماً) ---
if not st.session_state.logged_in:
    st.markdown("<h1 style='margin-top: 50px;'>⚡ المنصة الذكية المتكاملة</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem;'>سجل دخولك الآن للوصول إلى أدوات الذكاء الاصطناعي الفائقة</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 تسجيل الدخول لحسابك", "📝 فتح حساب جديد"])
    
    with tab1:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        username_input = st.text_input("👤 اسم المستخدم", key="login_user").strip()
        password_input = st.text_input("🔒 كلمة المرور", type="password", key="login_pass")
        login_button = st.button("🚀 تسجيل الدخول الآمن", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if login_button:
            if username_input == "admin" and password_input == "admin123":
                st.session_state.logged_in = True
                st.session_state.username = "admin"
                st.session_state.is_subscribed = True
                st.success("🎯 تم دخول لوحة الإدارة بنجاح!")
                st.rerun()
            else:
                user_data = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{username_input}"})
                if user_data and isinstance(user_data, dict) and user_data.get("password_hash") == password_input:
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
                    st.success(f"👋 مرحباً بك مجدداً {username_input}!")
                    st.rerun()
                else:
                    st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة.")
                
    with tab2:
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        new_username = st.text_input("👤 اختر اسم مستخدم فريد", key="reg_user").strip()
        new_password = st.text_input("🔒 اختر كلمة مرور قوية", type="password", key="reg_pass")
        register_button = st.button("✨ إنشاء الحساب وتفعيله", use_container_width=True, type="secondary")
        st.markdown('</div>', unsafe_allow_html=True)
        
        if register_button:
            if not new_username or not new_password:
                st.error("⚠️ الرجاء كتابة البيانات كاملة أولاً!")
            else:
                check_user = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{new_username}"})
                if check_user:
                    st.error("❌ اسم المستخدم مسجل بالفعل!")
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
                        st.success("🎉 تم إنشاء حسابك بنجاح! انتقل الآن إلى تبويب (تسجيل الدخول) للولوج مباشرة.")
                    except Exception as e:
                        st.error(f"حدث خطأ أثناء الإعداد: {e}")

# --- الحالة الثانية: تم تسجيل الدخول بنجاح (تظهر الميزات والرسائل وزر الخروج بالكامل) ---
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

    # إعداد القائمة الجانبية الأنيقة لإدارة الغرف وحالة الحساب
    st.sidebar.markdown(f"### 👤 الحساب: {st.session_state.username}")
    if st.session_state.username != "admin":
        st.sidebar.markdown(f"⏳ الأيام التجريبية المتبقية: **{st.session_state.days_left}** يوم")
    
    st.sidebar.markdown("<hr style='margin: 10px 0; border-color: #334155;'>", unsafe_allow_html=True)
    st.sidebar.markdown("### 📁 غرف المحادثة")
    
    with st.sidebar.form("add_room_form", clear_on_submit=True):
        r_title = st.text_input("🆕 اسم الغرفة الجديدة:").strip()
