import streamlit as st
import google.generativeai as genai

# 1. إعداد عنوان الصفحة الافتراضي
st.set_page_config(page_title="غرف المحادثات الاحترافية والمحمية", page_icon="💬", layout="centered")

st.title("غرف المحادثات الاحترافية والمحمية 💬")

# 2. وضع مفتاح الـ API الخاص بك في مكانه الصحيح والآمن بالأسفل:
# استخدام المفتاح السري المرفوع على موقع Streamlit بأمان دون كشفه
GEMINI_API_KEY=""
genai.configure(api_key=GEMINI_API_KEY)
    
    # استخدام موديل هجين وسريع ومجاني ممتاز للمحادثات
model = genai.GenerativeModel('gemini-1.5-flash')

    # 3. تهيئة مصفوفة تاريخ المحادثة (لمنع التكرار وحفظ السياق)
if "messages" not in st.session_state:
        st.session_state.messages = []

    # 4. عرض المحادثة السابقة بشكل مرتب ومحمي من التكرار
for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # 5. استقبال المدخلات الجديدة من المستخدم
if user_input := st.chat_input("اكتب استفسارك هنا..."):
        
        # عرض سؤال المستخدم فوراً وحفظه في الذاكرة
        with st.chat_message("user"):
            st.write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # توليد رد الذكاء الاصطناعي الفعلي بناءً على السؤال الحالي والتاريخ
        with st.chat_message("assistant"):
            with st.spinner("جاري التفكير..."):
                try:
                    # نرسل كامل المحادثة المخزنة في الذاكرة للـ API ليتذكر السياق كاملاً
                    formatted_history = []
                    for msg in st.session_state.messages[:-1]: # نرسل التاريخ القديم أولاً
                        role = "user" if msg["role"] == "user" else "model"
                        formatted_history.append({"role": role, "parts": [msg["content"]]})
                    
                    # بدء المحادثة مع إرسال التاريخ بمحاذاة صحيحة
                    chat = model.start_chat(history=formatted_history)
                    response = chat.send_message(user_input)
                    bot_response = response.text
                    
                    st.write(bot_response)
                except Exception as e:
                    bot_response = "عذراً، واجهت مشكلة في الاتصال بالخادم. تأكد من صحة مفتاح الـ API."
                    st.write(bot_response)
                    
        # حفظ رد البوت في الذاكرة لمنع تكراره عند كتابة سؤال جديد
        st.session_state.messages.append({"role": "assistant", "content": bot_response})
