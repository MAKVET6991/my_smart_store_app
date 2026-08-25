import streamlit as st
import google.generativeai as genai

# 1. إعداد عنوان الصفحة الافتراضي
st.set_page_config(page_title="غرف المحادثات الاحترافية للموظفين", page_icon="💬", layout="centered")
st.title("💬 غرف المحادثات الاحترافية للموظفين")
st.write("مرحباً بك في النسخة التجريبية الأولى من منصتك الخاصة")

# 2. جلب مفتاح الـ API من إعدادات السيرفر الآمنة لـ Streamlit
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY)

# 3. استخدام موديل هجين وسريع ومجاني ممتاز للمحادثات
model = genai.GenerativeModel('models/gemini-3.6-flash')

# 4. تهيئة مصفوفة تاريخ المحادثة لمنع التكرار وحفظ الجلسة
if "messages" not in st.session_state:
    st.session_state.messages = []

# 5. عرض المحادثة السابقة بشكل مرتب ومحمي من التكرار
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# 6. استقبال المدخلات الجديدة من المستخدم وبدء الذكاء الاصطناعي
if user_input := st.chat_input("اكتب استفسارك هنا..."):

    # عرض سؤال المستخدم فوراً وحفظه في الذاكرة
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    # توليد رد الذكاء الاصطناعي الفعلي بناءً على السياق الحالي والتاريخ
    with st.chat_message("assistant"):
        with st.spinner("جاري التفكير..."):
            try:
                # لتذكر السياق كاملاً، يرسل السيرفر كامل المحادثة المخزنة في الذاكرة
                formatted_history = []
                for msg in st.session_state.messages[:-1]:
                    role = "user" if msg["role"] == "user" else "model"
                    formatted_history.append({"role": role, "parts": [msg["content"]]})
                
                # بدء المحادثة مع إرسال تاريخ محادثة صحيح
                chat = model.start_chat(history=formatted_history)
                response = chat.send_message(user_input)
                bot_response = response.text
                
                st.write(bot_response)
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
                
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بالخادم: {e}")
