import streamlit as st
import google.generativeai as genai
import requests

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
    </style>
""", unsafe_allow_html=True)

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
        return response.json()
    except Exception as e:
        st.error(f"خطأ في الاتصال بقاعدة البيانات: {e}")
        return []

# 2. تهيئة حالات الذاكرة المؤقتة للمتصفح الحالي
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "current_messages" not in st.session_state:
    st.session_state.current_messages = []

# 3. شاشة إدارة الحسابات السحابية (تسجيل دخول / إنشاء حساب جديد)
if not st.session_state.logged_in:
    st.title("🔐 بوابة الوصول للمنصة العالمية")
    st.write("مرحباً بكِ في فضاء عملكِ السحابي المحمي")
    
    tab1, tab2 = st.tabs(["🔑 تسجيل الدخول", "📝 إنشاء حساب جديد"])
    
    # قسم تسجيل الدخول وقراءة البيانات من السيرفر
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
                    st.success("تم دخول المسؤولة بنجاح!")
                    st.rerun()
                else:
                    # فحص الحساب في قاعدة البيانات السحابية الحقيقية Supabase
                    user_data = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{username_input}"})
                    if user_data and user_data[0]["password_hash"] == password_input:
                        st.session_state.logged_in = True
                        st.session_state.username = username_input
                        st.success(f"تم تسجيل الدخول بنجاح! مرحباً {username_input}")
                        st.rerun()
                    else:
                        st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                    
    # قسم إنشاء حساب جديد وحفظه سحابياً للأبد
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
                    # التحقق أولاً من عدم تكرار الاسم في السيرفر
                    check_user = supabase_request("users_subscriptions", "GET", params={"username": f"eq.{new_username}"})
                    if check_user:
                        st.error("اسم المستخدم هذا مسجل مسبقاً عالمياً! اختر اسماً آخر.")
                    else:
                        # إدخال الحساب الجديد تلقائياً وحفظه في الجدول السحابي للأبد مع فترة 7 أيام تجريبية
                        new_user_payload = {
                            "username": new_username,
                            "password_hash": new_password,
                            "subscription_status": "trial"
                        }
                        supabase_request("users_subscriptions", "POST", json_data=new_user_payload)
                        st.success("🎉 تم إنشاء حسابكِ السحابي وحفظه بنجاح! يمكنكِ الآن الدخول من تبويب تسجيل الدخول.")

# 4. شاشة المحادثة والملفات السحابية (بعد الدخول)
else:
    st.title("💬 غرف المحادثات الاحترافية العالمية")
    st.write(f"مرحباً بكِ يا *{st.session_state.username}* في المنصة السحابية المؤمنة")

    # جلب مفتاح الـ API لـ Gemini من الإعدادات الآمنة
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-3.6-flash')

    # القائمة الجانبية الزاهية (Sidebar)
    with st.sidebar:
        st.markdown(f"👤 الحساب الحالي: *{st.session_state.username}*")
        st.markdown("---")
        
        # لوحة تحكم الـ Admin الحقيقية لقراءة المشتركين من قاعدة البيانات السحابية مباشرة
        if st.session_state.username == "admin":
            st.markdown("### 👑 لوحة تحكم المسؤولة (Supabase)")
            st.markdown('<div class="admin-box"><b>المشتركين المسجلين في السيرفر للأبد:</b></div>', unsafe_allow_html=True)
            all_users = supabase_request("users_subscriptions", "GET")
            if all_users:
                for u in all_users:
                    st.write(f"• {u['username']} ({u['subscription_status']})")
            else:
                st.write("• لا يوجد مستخدمين مسجلين بعد.")
            st.markdown("---")
        
        # ميزة رفع الملفات والصور
        st.markdown("### 📂 تحليل الملفات والصور")
        uploaded_file = st.file_uploader("ارفع ملف أو صورة للتحليل", type=["pdf", "txt", "jpg", "jpeg", "png"])
        
        file_context = ""
        if uploaded_file is not None:
            st.markdown('<div class="file-box">✅ تم تحميل الملف بنجاح! يمكنك الاستفسار عنه الآن.</div>', unsafe_allow_html=True)
            if uploaded_file.type == "text/plain":
                file_context = "\n[محتوى الملف]:\n" + str(uploaded_file.read(), "utf-8")
            elif uploaded_file.type == "application/pdf":
                file_context = f"\n[مكتبة النظام]: تم إرفاق ملف PDF باسم ({uploaded_file.name}). يرجى مساعدتي في تحليل محتواه والإجابة عنه."
            else:
                st.image(uploaded_file, caption="المعاينة المرفوعة", use_container_width=True)
                file_context = "\n[ملاحظة بصريّة]: تم إرفاق صورة مع المحادثة، يرجى تحليلها والإجابة بدقة."

        st.markdown("---")
        st.markdown("### 🛠️ أدوات التحكم")
        
        if st.button("🗑️ مسح هذه المحادثة", use_container_width=True):
            st.session_state.current_messages = []
            st.rerun()
            
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.current_messages = []
            st.rerun()

    # عرض المحادثة الحالية للمستخدم
    for message in st.session_state.current_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # استقبال المدخلات والدمج مع الملف المرفوع
    if user_input := st.chat_input("اكتب استفسارك هنا..."):
        full_prompt = user_input + file_context if file_context else user_input

        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.current_messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("جاري التحليل والتفكير..."):
                try:
                    formatted_history = []
                    for msg in st.session_state.current_messages[:-1]:
                        role = "user" if msg["role"] == "user" else "model"
                        formatted_history.append({"role": role, "parts": [msg["content"]]})
                    
                    chat = model.start_chat(history=formatted_history)
                    response = chat.send_message(full_prompt)
                    bot_response = response.text
                    
                    st.write(bot_response)
                    st.session_state.current_messages.append({"role": "assistant", "content": bot_response})
                    
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالخادم: {e}")
