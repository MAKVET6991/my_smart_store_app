import streamlit as st
import requests

# إعدادات مظهر واجهة التطبيق
st.set_page_config(page_title="منصة المحادثات الذكية", page_icon="💬", layout="centered")

st.title("💬 غرف المحادثات الاحترافية للموظفين")
st.write("مرحباً بك في النسخة التجريبية الأولى من منصتك الخاصة!")

# 💡 ضع مفتاح جوجل الذكي الخاص بك هنا بين علامتي التنصيص
API_KEY = ""

def get_ai_chat_response(user_query):
    if not API_KEY or API_KEY == "":
        return "تنبيه من النظام: يرجى كتابة الـ API Key الخاص بك داخل الكود أولاً لتفعيل المساعد الذكي."
        
    url = f"https://googleapis.com{API_KEY}"
    headers = {"Content-Type": "application/json"}
    
    system_instruction = "أنت مساعد ذكي وموظف خارق داخل غرفة محادثات سرية لشركة احترافية. أجب على استفسارات الموظفين والمدراء بأسلوب عملي، ذكي، ومؤدب جداً باللغة العربية."
    
    payload = {
        "contents": [{"parts": [{"text": f"{system_instruction}\n\nرسالة الموظف: {user_query}"}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code == 200:
            res_json = response.json()
            return res_json["candidates"]["content"]["parts"]["text"]
        return f"خطأ من الخادم (كود {response.status_code}): يرجى التحقق من صلاحية المفتاح."
    except Exception as e:
        return f"حدث خطأ أثناء الاتصال بالذكاء الاصطناعي: {e}"

# إنشاء ذاكرة مؤقتة لحفظ الرسائل داخل الصفحة
if "messages" not in st.session_state:
    st.session_state.messages = []

# عرض الرسائل المتبادلة في الصفحة بشكل منظم
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# صندوق إدخال الرسائل الحي
user_input = st.chat_input("اكتب رسالتك للموظفين أو للمساعد الذكي هنا...")

if user_input:
    with st.chat_message("user"):
        st.write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    with st.spinner("جاري تفكير المساعد الذكي..."):
        ai_reply = get_ai_chat_response(user_input)
        
    with st.chat_message("assistant"):
        st.write(ai_reply)
    st.session_state.messages.append({"role": "assistant", "content": ai_reply})