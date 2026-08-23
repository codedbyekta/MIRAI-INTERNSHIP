import streamlit as st
from google import genai
import os
from dotenv import load_dotenv

st.title("THE MULTIVERSE OF CHATBOTS")
st.write("Choose a personality and chat with the AI.")

# Task 1: Sidebar Integration
st.sidebar.title("App Settings")

personality = st.sidebar.selectbox(
    "Who do you want to talk to?",
    # TASK 2: PERSONA EXPANSION
    # Added more creative personalities
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

# Task 3: Intensity Slider
intensity = st.sidebar.slider(
    "Intensity Level",
    min_value=1,
    max_value=10
)

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

user_message = st.text_input("Say something:")

if st.button("SEND"):

    if user_message:

        # Task 5: Dynamic Avatars
        if personality == "An expert Hacker":
            bot_avatar = "💻"

        elif personality == "An angry Ravi Shastri":
            bot_avatar = "🏏"

        elif personality == "A crazy Ronaldo fan":
            bot_avatar = "⚽"

        elif personality == "Sherlock Holmes":
            bot_avatar = "🔎"

        elif personality == "Iron Man":
            bot_avatar = "🤖"

        elif personality == "Motivational Coach":
            bot_avatar = "💪"

        elif personality == "Funny Stand-up Comedian":
            bot_avatar = "🎤"

        elif personality == "College Professor":
            bot_avatar = "👨‍🏫"

        elif personality == "A panicked college student at 3 AM":
            bot_avatar = "😰"

        elif personality == "A 1920s Mafia Boss":
            bot_avatar = "🕴️"

        elif personality == "A highly sarcastic fitness coach":
            bot_avatar = "🏋️"

        # Task 3: Prompt Engineering
        ai_instructions = (
            f"You are acting as {personality}. "
            f"Your personality intensity level is {intensity} out of 10. "
            f"Act out this personality according to the intensity level. "
            f"At low intensity, be mildly in character. "
            f"At high intensity, strongly express the personality in your "
            f"tone, attitude, vocabulary, and reactions. "
            f"Respond to the user's message while staying completely in character.\n\n"
            f"User: {user_message}"
        )

        with st.spinner("Connecting to the multiverse..."):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=ai_instructions
            )

        # Task 4: Chat UI
        with st.chat_message("user"):
            st.write(user_message)

        # Task 5: Use Dynamic Avatar
        with st.chat_message("assistant", avatar=bot_avatar):
            st.write(response.text)

    else:
        st.warning("Please type a message first.")
