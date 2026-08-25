import streamlit as st
import google.generativeai as genai

# 1. إعداد عنوان وتصميم الصفحة
st.set_page_config(
    page_title="منصة المحادثة الاحترافية", 
    page_icon="💬", 
    layout="centered"
)

# تنسيق المظهر العصري الفخم الداكن (Dark Mode)
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stChatInputContainer { border-radius: 12px; border: 1px solid #1f2937 !important; }
    h1 { color: #6366f1 !important; text-align: center; }
    p { text-align: center; color: #9ca3af; }
    .login-box { padding: 20px; border-radius: 10px; background-color: #1f2937; border: 1px solid #374151; }
    </style>
""", unsafe_allow_html=True)

# 2. إعداد الذاكرة وتخزين المستخدمين والمحادثات
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "user_chats" not in st.session_state:
    # قاعدة بيانات محلية مؤقتة لتخزين محادثات كل مستخدم بشكل منفصل
    st.session_state.user_chats = {}

# قائمة الحسابات المصرح لها بالدخول (يمكنك تعديلها أو إضافة عملاء جدد هنا)
USER_CREDENTIALS = {
    "admin": "admin123",       # المستخدم الأول وكلمة مروره
    "user1": "pass123",       # العميل المشترك الأول
    "employee": "work2026"    # موظف بالشركة
}

# 3. شاشة تسجيل الدخول
if not st.session_state.logged_in:
    st.title("🔐 تسجيل الدخول للمنصة الذكية")
    st.write("الرجاء إدخال بيانات حسابك للوصول إلى غرف المحادثات المحمية")
    
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        username_input = st.text_input("اسم المستخدم")
        password_input = st.text_input("كلمة المرور", type="password")
        login_button = st.button("تسجيل الدخول", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if login_button:
            if username_input in USER_CREDENTIALS and USER_CREDENTIALS[username_input] == password_input:
                st.session_state.logged_in = True
                st.session_state.username = username_input
                # إنشاء مساحة محادثة فارغة للمستخدم إذا كانت أول مرة يدخل فيها
                if username_input not in st.session_state.user_chats:
                    st.session_state.user_chats[username_input] = []
                st.success(f"مرحباً بك مجدداً {username_input}! جاري تحويلك...")
                st.rerun()
            else:
                st.error("اسم المستخدم أو كلمة المرور غير صحيحة!")

# 4. شاشة المحادثة (تظهر فقط بعد تسجيل الدخول بنجاح)
else:
    st.title("💬 غرف المحادثات الاحترافية")
    st.write(f"مرحباً بك يا *{st.session_state.username}* في منصتك المخصصة")

    # جلب مفتاح الـ API من إعدادات السيرفر الآمنة لـ Streamlit
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('models/gemini-3.6-flash')

    # جلب المحادثات الخاصة بهذا المستخدم تحديداً لحفظها عند العودة
    current_messages = st.session_state.user_chats[st.session_state.username]

    # القائمة الجانبية (Sidebar)
    with st.sidebar:
        st.markdown(f"👤 الحساب الحالي: *{st.session_state.username}*")
        st.markdown("---")
        st.markdown("### 🛠️ أدوات التحكم")
        
        # زر مسح المحادثة للمستخدم الحالي فقط
        if st.button("🗑️ مسح هذه المحادثة", use_container_width=True):
            st.session_state.user_chats[st.session_state.username] = []
            st.rerun()
            
        # زر تسجيل الخروج والعودة للشاشة الرئيسية
        if st.button("🚪 تسجيل الخروج", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.rerun()

    # عرض المحادثة السابقة الخاصة بالمستخدم الحالي
    for message in current_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # استقبال المدخلات الجديدة من المستخدم وبدء الذكاء الاصطناعي
    if user_input := st.chat_input("اكتب استفسارك هنا..."):

        # عرض سؤال المستخدم فوراً وحفظه في الذاكرة المخصصة له
        with st.chat_message("user"):
            st.write(user_input)
        current_messages.append({"role": "user", "content": user_input})

        # توليد رد الذكاء الاصطناعي الفعلي بناءً على السياق الحالي والتاريخ
        with st.chat_message("assistant"):
            with st.spinner("جاري التفكير..."):
                try:
                    formatted_history = []
                    for msg in current_messages[:-1]:
                        role = "user" if msg["role"] == "user" else "model"
                        formatted_history.append({"role": role, "parts": [msg["content"]]})
                    
                    chat = model.start_chat(history=formatted_history)
                    response = chat.send_message(user_input)
                    bot_response = response.text
                    
                    st.write(bot_response)
                    current_messages.append({"role": "assistant", "content": bot_response})
                    
                    # تحديث قاعدة البيانات المؤقتة بعد الرد
                    st.session_state.user_chats[st.session_state.username] = current_messages
                    
                except Exception as e:
                    st.error(f"حدث خطأ أثناء الاتصال بالخادم: {e}")
