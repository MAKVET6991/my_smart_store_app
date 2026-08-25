import streamlit as st
import google.generativeai as genai

# 1. إعداد عنوان وتصميم الصفحة بألوان زاهية ومشرقة
st.set_page_config(
    page_title="منصة المحادثة الاحترافية الذكية", 
    page_icon="💬", 
    layout="centered"
)

# تنسيق المظهر العصري الزاهي والمبهج (Light Mode)
st.markdown("""
    <style>
    /* تغيير خلفية التطبيق إلى لون زاهي ومريح */
    .stApp { 
        background-color: #f8fafc; 
        color: #1e293b; 
    }
    /* تحسين شكل صندوق المدخلات */
    .stChatInputContainer { 
        border-radius: 12px; 
        border: 1px solid #cbd5e1 !important; 
        background-color: #ffffff !important;
    }
    /* تنسيق العناوين بألوان حيوية */
    h1 { 
        color: #4f46e5 !important; 
        text-align: center;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    p { 
        text-align: center; 
        color: #64748b; 
    }
    /* صناديق الواجهة الزاهية */
    .login-box { 
        padding: 20px; 
        border-radius: 12px; 
        background-color: #ffffff; 
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
    }
    .file-box { 
        padding: 10px; 
        border-radius: 8px; 
        background-color: #f0fdf4; 
        margin-bottom: 10px; 
        border: 1px dashed #22c55e;
        color: #166534;
    }
    .admin-box {
        padding: 12px;
        border-radius: 8px;
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        color: #1e40af;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# 2. تهيئة قواعد البيانات المؤقتة في الذاكرة
if "registered_users" not in st.session_state:
    st.session_state.registered_users = {
        "admin": "admin123",
        "user1": "pass123"
    }

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_chats" not in st.session_state:
    st.session_state.user_chats = {}

# 3. شاشة إدارة الحسابات (تسجيل دخول / إنشاء حساب جديد)
if not st.session_state.logged_in:
    st.title("🔐 بوابة الوصول للمنصة الذكية")
    st.write("مرحباً بكِ في منصتكِ الرقمية بحلتها الزاهية الجديدة")
    
    tab1, tab2 = st.tabs(["🔑 تسجيل الدخول", "📝 إنشاء حساب جديد"])
    
    # قسم تسجيل الدخول
    with tab1:
        with st.container():
            st.markdown('<div class="login-box">', unsafe_allow_html=True)
            username_input = st.text_input("اسم المستخدم", key="login_user")
            password_input = st.text_input("كلمة المرور", type="password", key="login_pass")
            login_button = st.button("تسجيل الدخول", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            if login_button:
                if username_input in st.session_state.registered_users and st.session_state.registered_users[username_input] == password_input:
                    st.session_state.logged_in = True
                    st.session_state.username = username_input
                    if username_input not in st.session_state.user_chats:
                        st.session_state.user_chats[username_input] = []
                    st.success(f"تم تسجيل الدخول بنجاح! جاري الانتقال...")
                    st.rerun()
                else:
                    st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")
                    
    # قسم إنشاء حساب جديد وحفظه تلقائياً
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
                elif new_username in st.session_state.registered_users:
                    st.error("اسم المستخدم هذا مسجل مسبقاً!")
                else:
                    st.session_state.registered_users[new_username] = new_password
                    st.session_state.user_chats[new_username] = [] 
                    st.success("🎉 تم إنشاء الحساب بنجاح! يمكنك الآن الذهاب لتبويب تسجيل الدخول.")

# 4. شاشة المحادثة والتحكم (تفتح بعد الدخول بنجاح)
else:
    st.title("💬 غرف المحادثات الاحترافية")
    st.write(f"مرحباً بكِ يا *{st.session_state.username}* في فضاء عملكِ الذكي")

    # جلب مفتاح الـ API من إعدادات السيرفر الآمنة لـ Streamlit
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-3.6-flash')

    current_messages = st.session_state.user_chats[st.session_state.username]

    # القائمة الجانبية الزاهية (Sidebar)
    with st.sidebar:
        st.markdown(f"👤 الحساب الحالي: *{st.session_state.username}*")
        st.markdown("---")
        
        # لوحة تحكم الـ Admin السرية (تظهر فقط إذا كان المستخدم هو admin)
        if st.session_state.username == "admin":
            st.markdown("### 👑 لوحة تحكم المسؤولة")
            st.markdown('<div class="admin-box"><b>قائمة المستخدمين المسجلين حالياً:</b></div>', unsafe_allow_html=True)
            for user in st.session_state.registered_users.keys():
                st.write(f"• {user}")
            st.markdown("---")
        
        # ميزة رفع الملفات والصور
        st.markdown("### 📂 تحليل الملفات والصور")
        uploaded_file = st.file_uploader("ارفع ملف أو صورة للتحليل", type=["pdf", "txt", "jpg", "jpeg", "png"])
        
        file_context = ""
        if uploaded_file is not None:
            st.markdown('<div class="file-box">✅ تم تحميل الملف بنجاح! يمكنك الاستفسار عنه الآن.</div>', unsafe_allow_html=True)
            if uploaded_file.type == "text/plain":
                file_context = "\n[محتوى الملف المرفوع]:\n" + str(uploaded_file.read(), "utf-8")
            elif uploaded_file.type == "application/pdf":
                file_context = f"\n[مكتبة النظام]: تم إرفاق ملف PDF باسم ({uploaded_file.name}). يرجى المساعدة في الإجابة على الأسئلة المتعلقة به."
            else:
                st.image(uploaded_file, caption="المعاينة المرفوعة", use_container_width=True)
                file_context = "\n[ملاحظة للموديل]: تم إرفاق صورة مع المحادثة، يرجى تحليل محتواها البصري والإجابة بدقة."

        st.markdown("---")
        st.markdown("### 🛠️ أدوات التحكم")
        
        if st.button("🗑️ مسح هذه المحادثة", use_container_width=True):
            st.session_state.user_chats[st.session_state.username] = []
            st.rerun()
            
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    # عرض المحادثة السابقة
    for message in current_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # استقبال المدخلات والدمج مع الملف المرفوع
    if user_input := st.chat_input("اكتب استفسارك هنا..."):
        full_prompt = user_input + file_context if file_context else user_input

        with st.chat_message("user"):
            st.write(user_input)
        current_messages.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("جاري التحليل والتفكير..."):
                try:
                    formatted_history = []
                    for msg in current_messages[:-1]:
                        role = "user" if msg["role"] == "user" else "model"
                        formatted_history.append({"role": role, "parts": [msg["content"]]})
                    
                    chat = model.start_chat(history=formatted_history)
                    response = chat.send_message(full_prompt)
                    bot_response = response.text
                    
                    st.write(bot_response)
                    current_messages.append({"role": "assistant", "content": bot_response})
                    st.session_state.user_chats[st.session_state.username] = current_messages
                    
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالخادم: {e}")
