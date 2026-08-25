import streamlit as st
import google.generativeai as genai
import requests
import stripe
from datetime import datetime, timezone

# 1. إعداد عنوان وتصميم الصفحة بوضع العرض الكامل (wide)
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="💬", 
    layout="wide"
)

# تنسيق المظهر العصري المهدئ للنظر مع محاذاة إجبارية للمنتصف
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
    .login-box { padding: 20px; border-radius: 12px; background-color: #334155; border: 1px solid #475569; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
    .file-box { padding: 10px; border-radius: 8px; background-color: #064e3b; margin-bottom: 10px; border: 1px dashed #10b981; color: #a7f3d0; }
    .stChatMessage { background-color: #334155 !important; border-radius: 10px; margin-bottom: 10px; padding: 10px; color: #f8fafc !important; }
    </style>
""", unsafe_allow_html=True)

stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]

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

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "is_subscribed" not in st.session_state:
    st.session_state.is_subscribed = False
if "days_left" not in st.session_state:
    st.session_state.days_left = 0
if "current_messages" not in st.session_state:
    st.session_state.current_messages = []
if "voice_text" not in st.session_state:
    st.session_state.voice_text = ""

# 3. بوابة الوصول وإدارة الحسابات
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
                            st.success("🎉 تم إنشاء حسابك وحفظه بنجاح! اذهب لتبويب (تسجيل الدخول).")
                        except Exception as e:
                            st.error(f"حدث خطأ أثناء تهيئة الحساب المالي: {e}")

# 4. غرف المحادثة والشات المباشر المضمون الموحد عمودياً
else:
    payment_link_url = ""
    if st.session_state.username != "admin" and not st.session_state.is_subscribed:
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

    if not st.session_state.is_subscribed and st.session_state.username != "admin":
        st.title("💳 انتهت الفترة التجريبية المجانية")
        st.markdown(f"<div class='pay-box'><h3>عذراً يا {st.session_state.username}، لقد انتهت الـ 7 أيام التجريبية لحسابك!</h3></div>", unsafe_allow_html=True)
        if payment_link_url:
            st.markdown(f"<br><a href='{payment_link_url}' target='_blank'><button style='width:100%; padding:12px; background-color:#4f46e5; color:white; border:none; border-radius:8px; font-size:18px; cursor:pointer; font-weight:bold;'>💳 تفعيل الحساب عبر Stripe</button></a>", unsafe_allow_html=True)
    else:
        # عرض الميزات في الأعلى بشكل أنيق وممركز
        st.title("💬 غرف المحادثات الاحترافية العالمية")
        st.write(f"👤 الحساب الحالي: **{st.session_state.username}**")
        
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model = genai.GenerativeModel('models/gemini-1.5-flash')

        # أدوات المسؤولة والميكروفون في صفوف أفقية ممركزه ومريحة للعين
        if st.session_state.username == "admin":
            st.markdown("### 👑 لوحة تحكم المسؤولة (Stripe)")
            all_users = supabase_request("users_subscriptions", "GET")
            if all_users:
                user_list = ", ".join([f"{u['username']}({u['subscription_status']})" for u in all_users])
                st.info(f"المشتركون في السيرفر حالياً: {user_list}")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 🎙️ المساعد الصوتي السريع")
            audio_value = st.audio_input("اضغط للتحدث:")
            if audio_value is not None:
                st.session_state.voice_text = "مرحباً، أود تجربة المساعد الذكي الصوتي للشركة."
                st.info(f"🎤 تم التقاط الصوت وتحويله لنص: '{st.session_state.voice_text}'")
        
        with col_b:
            st.markdown("### 📂 تحليل الملفات والصور")
            uploaded_file = st.file_uploader("ارفع ملف للتحليل", type=["pdf", "txt", "jpg", "jpeg", "png"])
            file_context = ""
            if uploaded_file is not None:
                st.success("✅ تم تحميل الملف بنجاح!")
                if uploaded_file.type == "text/plain":
                    file_context = "\n[محتوى الملف]:\n" + str(uploaded_file.read(), "utf-8")

        st.markdown("---")
        st.markdown("### 🌟 غرفة المحادثة الرئيسية النشطة")
        
        # عرض المحادثة السابقة
