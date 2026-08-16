import streamlit as st
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

st.title("THE MULTIVERSE OF CHATBOTS")
st.write("Choose a personality and chat with the AI.")

st.sidebar.title("App Settings")

personality = st.sidebar.selectbox(
    "Who do you want to talk to?",
    [
        "An expert Hacker",
        "An angry Ravi Shastri",
        "A crazy Ronaldo fan",
        "Sherlock Holmes",
        "Iron Man",
        "Motivational Coach",
        "Funny Stand-up Comedian",
        "College Professor",
        "A panicked college student at 3 AM",
        "A 1920s Mafia Boss",
        "A highly sarcastic fitness coach"
    ]
)

intensity = st.sidebar.slider(
    "Intensity Level",
    min_value=1,
    max_value=10,
    value=5
)

# TASK 1: Initialize the Memory Vault
if "messages" not in st.session_state:
    st.session_state.messages = []

# TASK 2: Render the Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# TASK 3: Upgrade the Input UI
if user_message := st.chat_input("Say something..."):

    # TASK 4: Save the User Message to Memory
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    with st.chat_message("user"):
        st.markdown(user_message)

    ai_prompt = f"""
You are acting as {personality}.

Your personality intensity level is {intensity} out of 10.

At low intensity, be mildly in character.
At high intensity, strongly express the personality
in your tone, attitude, vocabulary, and reactions.

Stay completely in character while replying.

User Message:
{user_message}
"""

    with st.spinner("Connecting to the Multiverse..."):

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=ai_prompt
        )

        ai_response = response.text

    with st.chat_message("assistant"):
        st.markdown(ai_response)

    # TASK 4: Save the AI Response to Memory
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": ai_response
        }
    )