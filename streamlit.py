# Install system dependencies and Google Chrome
!wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
!echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
!apt-get update
!apt-get install -y google-chrome-stable
!apt-get install -y xvfb
!apt-get update -y
!apt-get install -y wget unzip libxi6 libgconf-2-4
!wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
!dpkg -i google-chrome-stable_current_amd64.deb
!apt-get -f install -y

# Install Python dependencies
!pip install streamlit selenium beautifulsoup4 fuzzywuzzy python-Levenshtein webdriver-manager google-generativeai pyngrok

import streamlit as st
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from fuzzywuzzy import fuzz
from pyngrok import ngrok

# Streamlit Interface
st.title("Moodle Quiz Automation")
st.write("Enter the details below to automate your Moodle quiz.")

# Input fields
login_url = st.text_input("Moodle Login URL", placeholder="e.g., https://lms2.eee.saveetha.in/login/index.php")
quiz_url = st.text_input("Quiz URL", placeholder="e.g., https://lms2.eee.saveetha.in/mod/quiz/view.php?id=546")
username = st.text_input("Username")
password = st.text_input("Password", type="password")
gemini_api_key = st.text_input("Gemini API Key", type="password")
ngrok_auth_token = st.text_input("Ngrok Auth Token", type="password", placeholder="Enter your Ngrok auth token")
start_button = st.button("Start Quiz Automation")

# Instructions for Gemini API Key
with st.expander("How to Create a Gemini API Key"):
    st.markdown("""
    To use this script, you need a Gemini API key from Google. Follow these steps:
    
    1. **Visit Google AI Studio**:
       - Go to [Google AI Studio](https://aistudio.google.com/app/apikey).
       - Sign in with your Google account.
    
    2. **Generate API Key**:
       - Click **Create API Key**.
       - Copy the key (e.g., `XXXXXXXXXXXXXXXXXXXXXXXXXXX`).
    
    3. **Set Up Billing (if needed)**:
       - The Gemini 1.5 Flash API has a free tier (~1,500 requests/day).
       - For higher usage, enable billing in the [Google Cloud Console](https://console.cloud.google.com/).
       - Enable the **Generative Language API** in **APIs & Services > Credentials**.
    
    4. **Secure Your Key**:
       - Do not share the key publicly.
       - Paste it into the input field above.
    
    5. **Check Limits**:
       - The free tier supports ~1,500 requests/day, sufficient for a 20-question quiz.
       - See [Google’s documentation](https://ai.google.dev/docs) for details.
    """)

# Instructions for Ngrok
with st.expander("How to Get an Ngrok Auth Token"):
    st.markdown("""
    To run this app in Google Colab, you need an Ngrok auth token to expose the Streamlit server.
    
    1. **Sign Up for Ngrok**:
       - Go to [Ngrok](https://ngrok.com/) and create a free account.
    
    2. **Get Your Auth Token**:
       - After signing in, go to the [Ngrok Dashboard](https://dashboard.ngrok.com/get-started/your-authtoken).
       - Copy your auth token (e.g., `2abc123xyz...`).
    
    3. **Enter the Token**:
       - Paste the token into the input field above.
    
    4. **Free Tier Limits**:
       - The free tier is sufficient for temporary use. For persistent use, consider a paid plan.
    """)

# Main logic
if start_button:
    if not all([login_url, quiz_url, username, password, gemini_api_key, ngrok_auth_token]):
        st.error("Please fill in all input fields.")
    else:
        with st.spinner("Setting up Ngrok and starting quiz automation..."):
            # Set up Ngrok
            try:
                ngrok.set_auth_token(ngrok_auth_token)
                public_url = ngrok.connect(8501)
                st.write(f"Streamlit app is live at: {public_url}")
            except Exception as e:
                st.error(f"Failed to set up Ngrok: {e}")
                st.stop()

            # --- Gemini API Setup ---
            GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
            st.write("Gemini API key loaded. Ready to make API calls.")
            st.write("-" * 30)

            # --- Selenium Setup ---
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--log-level=3")
            chrome_options.binary_location = "/usr/bin/google-chrome"  # Ensure Chrome path

            st.write("Initializing WebDriver (Chrome Headless)...")
            try:
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                st.write("WebDriver initialized successfully.")
            except Exception as e:
                st.error(f"Failed to initialize WebDriver: {e}")
                st.stop()

            wait = WebDriverWait(driver, 60)
            st.write("-" * 30)

            # --- ask_gemini Function ---
            def ask_gemini(question, options):
                option_letters = ['a', 'b', 'c', 'd']
                formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options[:len(option_letters)])])
                prompt = (
                    "You are a multiple choice answering bot.\n"
                    "Read the question and the options below carefully.\n"
                    f"Your response should be ONLY the letter of the correct option ({', '.join(option_letters[:len(options)])}) and nothing else.\n\n"
                    f"Question: {question}\n\nOptions:\n{formatted_options}\n\nAnswer:"
                )
                st.write(f"\nSending prompt to Gemini API:\n---\n{prompt}\n---")
                headers = {
                    "Content-Type": "application/json",
                }
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ]
                }
                try:
                    response = requests.post(
                        f"{GEMINI_API_URL}?key={gemini_api_key}",
                        json=payload,
                        headers=headers
                    )
                    response.raise_for_status()
                    response_data = response.json()
                    generated_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
                    st.write(f"Gemini Raw Response: '{generated_text}'")
                    # Try direct letter match
                    potential_answer_match = re.match(r"^\s*([a-d])", generated_text)
                    if potential_answer_match:
                        direct_letter = potential_answer_match.group(1)
                        if direct_letter in option_letters[:len(options)]:
                            st.write(f"Parsed Direct Letter Match: {direct_letter}")
                            return direct_letter
                    # Try flexible letter match
                    flexible_match = re.search(r"\b([a-d])\b", generated_text)
                    if flexible_match:
                        found_letter = flexible_match.group(1)
                        if found_letter in option_letters[:len(options)]:
                            st.write(f"Parsed Flexible Letter Match: {found_letter}")
                            return found_letter
                    # Fallback to fuzzy matching
                    st.write("No clear letter found, attempting fuzzy match...")
                    best_match_letter, best_score = "", 0
                    for idx, opt in enumerate(options):
                        score = fuzz.token_set_ratio(generated_text, opt.lower())
                        if score > best_score:
                            best_score = score
                            best_match_letter = option_letters[idx]
                    fuzzy_threshold = 80
                    if best_score >= fuzzy_threshold:
                        st.write(f"Fuzzy fallback selected: '{best_match_letter}' (score: {best_score})")
                        return best_match_letter if best_match_letter in option_letters[:len(options)] else ""
                    else:
                        st.write(f"Fuzzy match score {best_score} below threshold {fuzzy_threshold}. Cannot determine answer.")
                        return ""
                except Exception as e:
                    st.error(f"Error during Gemini API call: {e}")
                    return ""

            st.write("-" * 30)

            # --- Login and Navigation ---
            try:
                st.write(f"Navigating to login page: {login_url}")
                driver.get(login_url)
                username_field = wait.until(EC.visibility_of_element_located((By.ID, 'username')))
                password_field = wait.until(EC.visibility_of_element_located((By.ID, 'password')))
                login_button = wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn')))
                username_field.send_keys(username)
                password_field.send_keys(password)
                login_button.click()
                st.write("Login attempted.")
                st.write("Login successful, redirected to dashboard.")
                time.sleep(2)
                st.write(f"Navigating to quiz page: {quiz_url}")
                driver.get(quiz_url)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "page-header-headings")))
                st.write("Arrived at quiz page.")
            except Exception as e:
                st.error(f"Login or quiz page navigation failed: {e}")
                with open("login_page_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                st.write("Page source saved to 'login_page_source.html' for debugging.")
                driver.quit()
                st.stop()

            # --- Handle Quiz Start/Continue ---
            def attempt_quiz_start(max_attempts=3):
                for attempt in range(1, max_attempts + 1):
                    st.write(f"\nAttempt {attempt}/{max_attempts} to start or continue quiz...")
                    try:
                        quiz_button_xpath = "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | //input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]"
                        quiz_button = wait.until(EC.element_to_be_clickable((By.XPATH, quiz_button_xpath)))
                        button_text = quiz_button.text or quiz_button.get_attribute('value')
                        st.write(f"Found button: '{button_text}'")
                        driver.execute_script("arguments[0].click();", quiz_button)
                        st.write("Clicked quiz start/continue button.")
                        time.sleep(3)
                        
                        # Check if already in quiz by looking for question text
                        try:
                            question_element = WebDriverWait(driver, 5).until(
                                EC.presence_of_element_located((By.CLASS_NAME, "qtext"))
                            )
                            st.write("Quiz already in progress, no 'Start attempt' button needed.")
                            return True
                        except:
                            # Look for 'Start attempt' confirmation button
                            st.write("Checking for 'Start attempt' confirmation button...")
                            try:
                                start_attempt_button = WebDriverWait(driver, 20).until(
                                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt')] | //input[contains(@value,'Start attempt')]"))
                                )
                                button_text = start_attempt_button.text or start_attempt_button.get_attribute('value')
                                st.write(f"Found and clicking 'Start attempt' confirmation button: '{button_text}'")
                                driver.execute_script("arguments[0].click();", start_attempt_button)
                                time.sleep(3)
                                # Verify quiz started by checking for question text
                                question_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                                st.write("Quiz started successfully, question text found.")
                                return True
                            except Exception as start_e:
                                st.write(f"No 'Start attempt' confirmation button found or failed to click: {start_e}")
                                # Double-check if quiz is already in progress
                                try:
                                    question_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                                    st.write("Quiz already in progress, proceeding without 'Start attempt' button.")
                                    return True
                                except Exception as quiz_e:
                                    st.write(f"Failed to confirm quiz start or progress: {quiz_e}")
                                    if attempt == max_attempts:
                                        st.write(f"Max attempts ({max_attempts}) reached. Saving page source for debugging.")
                                        with open("quiz_start_page_source.html", "w", encoding="utf-8") as f:
                                            f.write(driver.page_source)
                                        st.write("Page source saved to 'quiz_start_page_source.html' for debugging.")
                                        return False
                                    st.write("Retrying...")
                                    time.sleep(2)
                    except Exception as e:
                        st.write(f"Could not find quiz start/continue button: {e}")
                        # Fallback check for quiz in progress
                        try:
                            question_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                            st.write("Quiz already in progress, continuing.")
                            return True
                        except:
                            if attempt == max_attempts:
                                st.write(f"Max attempts ({max_attempts}) reached. Saving page source for debugging.")
                                with open("quiz_start_page_source.html", "w", encoding="utf-8") as f:
                                    f.write(driver.page_source)
                                st.write("Page source saved to 'quiz_start_page_source.html' for debugging.")
                                return False
                            st.write("Retrying...")
                            time.sleep(2)
                return False

            # Execute quiz start with retries
            st.write("-" * 30)
            if not attempt_quiz_start():
                st.error("Failed to start or continue quiz after retries. Exiting.")
                driver.quit()
                st.stop()

            st.write("-" * 30)

            # --- Process Quiz Questions ---
            page_count = 0
            finish_attempt_xpath = "//input[@value='Finish attempt ...' and @name='next' and @id='mod_quiz-next-nav']"
            while True:
                page_count += 1
                st.write(f"\n--- Processing Question Page {page_count} ---")
                
                # Process the current question (if any)
                try:
                    question_element = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.CLASS_NAME, "qtext"))
                    )
                    question_text = question_element.text.strip()
                    st.write(f"Question Text: {question_text[:200]}...")
                    answer_block_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
                    answer_html = answer_block_element.get_attribute('outerHTML')
                    soup = BeautifulSoup(answer_html, 'html.parser')
                    option_texts, radio_elements = [], []
                    all_inputs = soup.find_all('input', {'type': 'radio'})
                    for inp in all_inputs:
                        option_id = inp.get('id')
                        if option_id:
                            label_text = ""
                            label_id = inp.get('aria-labelledby')
                            if label_id and (label_div := soup.find(id=label_id)):
                                label_text = label_div.get_text(strip=True)
                            elif soup.find('label', {'for': option_id}):
                                label_text = soup.find('label', {'for': option_id}).get_text(strip=True)
                            elif inp.find_next_sibling('label'):
                                label_text = " ".join(inp.find_next_sibling('label').get_text(strip=True).split())
                            if label_text:
                                option_texts.append(label_text)
                                try:
                                    selenium_radio = driver.find_element(By.ID, option_id)
                                    radio_elements.append(selenium_radio)
                                except Exception as sel_e:
                                    st.write(f"Could not find Selenium element for ID '{option_id}': {sel_e}")
                                    option_texts.pop()
                                    continue
                    st.write(f"Parsed Options ({len(option_texts)}): {option_texts}")
                    if option_texts and len(option_texts) == len(radio_elements):
                        model_answer_letter = ask_gemini(question_text, option_texts)
                        st.write(f"Gemini's Chosen Letter: '{model_answer_letter}'")
                        clicked = False
                        if model_answer_letter and model_answer_letter in 'abcd'[:len(option_texts)]:
                            try:
                                answer_index = ord(model_answer_letter) - ord('a')
                                if 0 <= answer_index < len(radio_elements):
                                    target_element = radio_elements[answer_index]
                                    wait.until(EC.element_to_be_clickable(target_element))
                                    driver.execute_script("arguments[0].click();", target_element)
                                    st.write(f"Clicked option {model_answer_letter}: {option_texts[answer_index]}")
                                    clicked = True
                                else:
                                    st.write(f"Letter '{model_answer_letter}' out of bounds for options ({len(option_texts)}).")
                            except Exception as click_e:
                                st.write(f"Error clicking option {model_answer_letter}: {click_e}")
                        if not clicked:
                            st.write(f"Could not click an option for question {page_count}.")
                    else:
                        st.write("Warning: Failed to parse options or link to Selenium elements.")
                except Exception as e:
                    st.write(f"No question found or error processing question on page {page_count}: {e}")

                # Check if "Finish attempt ..." button is present
                try:
                    finish_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, finish_attempt_xpath)))
                    st.write("Found 'Finish attempt ...' button. Proceeding with quiz submission...")
                    # Execute quiz submission sequence
                    try:
                        driver.execute_script("arguments[0].click();", finish_btn)
                        st.write("Clicked 'Finish attempt ...' button.")
                        time.sleep(2)

                        # Step 1: Click first "Submit all and finish" button
                        submit_all_xpath1 = "//button[@type='submit' and contains(text(), 'Submit all and finish')]"
                        submit_all_btn1 = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, submit_all_xpath1)))
                        driver.execute_script("arguments[0].click();", submit_all_btn1)
                        st.write("Clicked first 'Submit all and finish' button.")
                        time.sleep(2)

                        # Step 2: Click second "Submit all and finish" button
                        submit_all_xpath2 = "//button[@type='button' and @data-action='save' and contains(text(), 'Submit all and finish')]"
                        submit_all_btn2 = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, submit_all_xpath2)))
                        driver.execute_script("arguments[0].click();", submit_all_btn2)
                        st.write("Clicked second 'Submit all and finish' button.")
                        time.sleep(2)

                        # Step 3: Click "Finish review" link
                        finish_review_xpath = "//a[@class='mod_quiz-next-nav' and contains(text(), 'Finish review')]"
                        finish_review_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, finish_review_xpath)))
                        driver.execute_script("arguments[0].click();", finish_review_btn)
                        st.write("Clicked 'Finish review' link.")
                        break  # Exit the while loop after submission
                    except Exception as submit_e:
                        st.error(f"Error during quiz submission sequence: {submit_e}")
                        with open("submit_page_source.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        st.write("Page source saved to 'submit_page_source.html' for debugging.")
                        break  # Exit loop to avoid infinite loop on submission failure
                except:
                    st.write("No 'Finish attempt ...' button found. Moving to next page...")
                    try:
                        next_xpath = "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"
                        next_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
                        driver.execute_script("arguments[0].click();", next_btn)
                        st.write("Clicked 'Next page'.")
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                        time.sleep(1)
                    except Exception as nav_e:
                        st.error(f"Error navigating to next page: {nav_e}")
                        with open(f"question_page_{page_count}_source.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        st.write(f"Page source saved to 'question_page_{page_count}_source.html' for debugging.")
                        break  # Exit loop to avoid infinite loop on navigation failure

            st.write("\n" + "=" * 50)
            st.success("Quiz processing completed.")
            if driver:
                driver.quit()
            st.write("WebDriver closed.")
            st.write("=" * 50)
