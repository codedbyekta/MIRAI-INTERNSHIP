import streamlit as st

# Title and Instructions
st.title("Identity Echo Interface")

st.write(
    "Welcome! Enter your name and a message below, then click "
    "'Transmit' to send your transmission."
)

# User Inputs
user_name = st.text_input("Enter your Name")

user_message = st.text_input("Enter your Message")

# Button
if st.button("Transmit"):

    # Check if Name is empty
    if user_name.strip() == "":
        st.error("Please provide your name.")

    # Check if Message is empty
    elif user_message.strip() == "":
        st.warning("Please type a message to transmit.")

    # Success
    else:
        st.success(
            f"Transmission successful! Greetings, {user_name}. "
            f"We received your message: {user_message}"
        )

        # Advanced Challenge
        total_characters = len(user_message)
        token_count = total_characters / 4

        st.info(
            f"System Check: Your message will consume approximately "
            f"{token_count:.2f} tokens from our context window."
        )