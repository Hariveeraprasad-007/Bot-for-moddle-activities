import os
import streamlit as st
from bot import run_bot  # Import the bot logic from bot.py

def main():
    st.title("Moodle Quiz Bot")
    st.write("Automate your Moodle quiz attempts with this bot. Enter your details below to get started.")
    
    # Form for user inputs
    with st.form("bot_form"):
        username = st.text_input(
            "Username",
            placeholder="Enter your Moodle username",
            help="Your Moodle login username"
        )
        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your Moodle password",
            help="Your Moodle login password"
        )
        quiz_url = st.text_input(
            "Quiz URL",
            placeholder="e.g., https://lms2.eee.saveetha.in/mod/quiz/view.php?id=551",
            help="Direct URL to the quiz page"
        )
        api_key = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="Enter your Gemini API key",
            help="Your Gemini API key is required for the bot to answer questions. Keep it secure and do not share it."
        )
        submit_button = st.form_submit_button("Start Bot")
    
    # Handle form submission
    if submit_button:
        if username and password and quiz_url and api_key:
            with st.spinner("Running the bot..."):
                try:
                    run_bot(username, password, quiz_url, api_key)
                    st.success("Bot has finished running successfully.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")
        else:
            st.error("Please fill in all fields, including the Gemini API key.")
    
    # Instructions section
    with st.expander("Instructions"):
        st.write("""
        ### How to Use the Bot
        1. **Enter your Moodle username and password** in the fields above.
        2. **Provide the URL of the quiz** you want to attempt. This should be the direct link to the quiz page on your Moodle site.
        3. **Enter your Gemini API key**. This is required for the bot to answer questions. **Keep your API key secure and do not share it.**
           - If you don’t have a Gemini API key, you can obtain one by visiting [Google AI Studio](https://ai.google.dev) and following the instructions to generate an API key.
        4. **Click 'Start Bot'** to begin the automation process.
        
        The bot will log in to your Moodle account, navigate to the quiz, and attempt to answer the questions using the Gemini API. Check the terminal for detailed progress logs if needed.
        """)

if __name__ == "__main__":
    main()
