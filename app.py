import streamlit as st
import requests
import time

FASTAPI_SERVER_URL = "http://127.0.0.1:8000/query"

st.set_page_config(page_title="FastRAG", page_icon="🤖")
st.title("Chat with FastRAG Bot")

if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

if "user_input" not in st.session_state:
    st.session_state.user_input = ""

def get_bot_response(query):
    params = {'query': query}
    
    try:
        response = requests.get(FASTAPI_SERVER_URL, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if "answer" in data:
                return data["answer"], data["confidence"]
            else:
                return "Sorry, I couldn't find an answer.", None
        else:
            return f"Error: {response.status_code} - {response.text}", None
    except Exception as e:
        return f"An error occurred: {e}", None

user_query = st.text_input("Enter your query:", st.session_state.user_input)

if user_query != st.session_state.user_input:
    st.session_state.user_input = user_query

if st.button("Submit"):
    st.divider()
    st.header("Chat History")

    if user_query.strip():
        st.session_state.conversation_history.append(f"You: {user_query}")
        
        with st.spinner("FastRAG Bot is thinking..."):
            time.sleep(2)
            answer, confidence = get_bot_response(user_query)
        
        if confidence:
            st.session_state.conversation_history.append(f"Bot: {answer}<br>(Confidence: {confidence:.2f})")
        else:
            st.session_state.conversation_history.append(f"Bot: {answer}")

for message in st.session_state.conversation_history:
    if message.startswith("You:"):
        st.markdown(f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
            <div style="background-color:#111c29; padding:10px; border-radius:10px; max-width:70%; width:max-content;">
                <strong style="color: #565656;">You:</strong>
                <div>{message[4:]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    elif message.startswith("Bot:"):
        if "<br>" in message:
            answer, confidence = message.split("<br>")
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">
                <div style="background-color:#08182b; padding:10px; border-radius:10px; max-width:70%; width:max-content;">
                    <strong style="color: #565656;">FastRAG Bot:</strong>
                    <div>{answer[4:]}</div>
                    <div style="font-size: 0.9em; color: #289E3CFF;">{confidence}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">
                <div style="background-color:#08182b; padding:10px; border-radius:10px; max-width:70%; width:max-content;">
                    <strong>FastRAG Bot:</strong>
                    <div>{message[4:]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .streamlit-expanderHeader {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)
