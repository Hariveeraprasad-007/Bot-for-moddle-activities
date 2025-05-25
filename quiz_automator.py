import streamlit as st
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
from datetime import datetime
import json
import os

# Streamlit configuration
st.set_page_config(page_title="Moodle Quiz Automator", layout="wide")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .container { max-width: 600px; margin: 0 auto; padding: 20px; background: #F8FAFC; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .title { font-size: 24px; font-weight: 700; color: #1F2937; margin-bottom: 8px; text-align: center; }
    .subtitle { font-size: 16px; color: #6B7280; margin-bottom: 24px; text-align: center; }
    .form-card { background: #FFFFFF; padding: 24px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .stButton>button { 
        background: linear-gradient(90deg, #10B981, #059669); 
        color: white; 
        border: none; 
        padding: 12px 24px; 
        border-radius: 6px; 
        font-weight: 600; 
        transition: transform 0.2s, box-shadow 0.2s; 
        width: 100%; 
    }
    .stButton>button:hover { 
        transform: translateY(-2px); 
        box-shadow: 0 4px 12px rgba(16,185,129,0.3); 
    }
    .stButton>button:disabled { 
        background: #D1D5DB; 
        cursor: not-allowed; 
    }
    .stTextInput>div>input, .stTextArea>div>textarea, .stSelectbox>div>select { 
        border: 1px solid #E5E7EB; 
        border-radius: 6px; 
        padding: 12px; 
        font-size: 16px; 
        color: #1F2937; 
    }
    .stTextInput>div>input:focus, .stTextArea>div>textarea:focus, .stSelectbox>div>select:focus { 
        border-color: #1E3A8A; 
        box-shadow: 0 0 0 3px rgba(30,58,138,0.1); 
    }
    .stTextInput>div>input::placeholder, .stTextArea>div>textarea::placeholder { 
        color: #9CA3AF; 
        opacity: 1; 
    }
    .stTextInput>div>input:focus::placeholder, .stTextArea>div>textarea:focus::placeholder { 
        opacity: 0; 
    }
    .error { color: #EF4444; font-weight: 500; font-size: 14px; }
    .success { color: #10B981; font-weight: 500; font-size: 14px; }
    .progress { color: #1E3A8A; font-size: 14px; }
    .log-container { 
        background: #FFFFFF; 
        padding: 16px; 
        border-radius: 8px; 
        max-height: 200px; 
        overflow-y: auto; 
        border: 1px solid #E5E7EB; 
        margin-top: 16px; 
    }
    .expander-header { font-size: 16px; font-weight: 600; color: #1F2937; }
    .result-table { width: 100%; border-collapse: collapse; margin-top: 16px; }
    .result-table th, .result-table td { padding: 12px; text-align: left; border-bottom: 1px solid #E5E7EB; }
    .result-table th { background: #F1F5F9; font-weight: 600; color: #1F2937; }
    .result-table td { color: #1F2937; }
    .stSelectbox label, .stTextInput label, .stTextArea label { font-size: 14px; font-weight: 500; color: #1F2937; margin-bottom: 8px; }
    @media (max-width: 640px) {
        .container { padding: 16px; }
        .stTextInput, .stTextArea, .stSelectbox { margin-bottom: 16px; }
    }
    </style>
""", unsafe_allow_html=True)

# Load or initialize user details
user_details_file = "/workspaces/Bot-for-moddle-activities/user_details.json"
if os.path.exists(user_details_file):
    with open(user_details_file, "r") as f:
        user_details = json.load(f)
else:
    user_details = {"username": "", "password": "", "gemini_api_key": ""}

# Interface
st.markdown("""
    <div class="container">
        <div class="title">Moodle Quiz Automator</div>
        <div class="subtitle">Automate your Moodle quizzes with ease and track progress in real time</div>
    </div>
""", unsafe_allow_html=True)

with st.container():
    with st.form("quiz_form", clear_on_submit=False):
        st.markdown('<div class="form-card">', unsafe_allow_html=True)
        st.markdown('<div class="expander-header">Enter Quiz Details</div>', unsafe_allow_html=True)

        # Login URL dropdown
        login_url_options = [
            "https://lms2.ai.saveetha.in/login/index.php",
            "https://lms2.cse.saveetha.in/login/index.php",
            "https://lms2.eee.saveetha.in/login/index.php",
            "https://lms.saveetha.in/login/index.php"
        ]
        login_url = st.selectbox(
            "Moodle Login URL",
            options=login_url_options,
            index=login_url_options.index("https://lms2.ai.saveetha.in/login/index.php"),
            placeholder="Select Moodle login URL",
            help="Choose the Moodle login URL for your institution"
        )

        # Other inputs
        username = st.text_input(
            "Username",
            value=user_details["username"],
            placeholder="Enter your username",
            help="Your Moodle username (e.g., 23009466)"
        )
        password = st.text_input(
            "Password",
            type="password",
            value=user_details["password"],
            placeholder="Enter your password",
            help="Your Moodle password"
        )
        gemini_api_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=user_details["gemini_api_key"],
            placeholder="Enter your Gemini API key",
            help="Your Google Gemini API key"
        )
        quiz_urls = st.text_area(
            "Quiz URLs (comma-separated)",
            value="https://lms2.ai.saveetha.in/mod/quiz/view.php?id=1790",
            placeholder="e.g., https://lms2.ai.saveetha.in/mod/quiz/view.php?id=1790",
            help="Enter quiz URLs, separated by commas"
        )

        submit_button = st.form_submit_button("Start Automation", help="Click to start automating your quizzes")
        st.markdown('</div>', unsafe_allow_html=True)

# Instructions
with st.expander("How to Get a Gemini API Key", expanded=False):
    st.markdown("""
        1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey) and sign in with your Google account.
        2. Click **Create API Key** and copy the generated key.
        3. For higher usage limits, enable billing in [Google Cloud Console](https://console.cloud.google.com/) and activate the **Generative Language API**.
        4. Paste the key in the form above. The free tier supports ~1,500 requests/day.
    """)

# Save user details on submit
if submit_button:
    if username or password or gemini_api_key:
        user_details["username"] = username or user_details["username"]
        user_details["password"] = password or user_details["password"]
        user_details["gemini_api_key"] = gemini_api_key or user_details["gemini_api_key"]
        with open(user_details_file, "w") as f:
            json.dump(user_details, f, indent=4)

# Gemini function
def ask_gemini(question, options, gemini_api_key):
    start_time = time.time()
    option_letters = ['a', 'b', 'c', 'd']
    formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options[:len(option_letters)])])
    prompt = (
        f"Question: {question}\n\nOptions:\n{formatted_options}\n\nAnswer with ONLY the letter of the correct option ({', '.join(option_letters[:len(options)])}):"
    )
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}",
            json=payload,
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        generated_text = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
        match = re.match(r"^\s*([a-d])", generated_text)
        return match.group(1) if match and match.group(1) in option_letters[:len(options)] else "", time.time() - start_time
    except Exception:
        return "", time.time() - start_time

# Check for 503 error
def check_503(driver):
    try:
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        return bool(soup.find(string=re.compile(r'503\s*Service\s*Unavailable', re.I)))
    except:
        return False

# Main logic
if submit_button:
    if not all([login_url, quiz_urls, username, password, gemini_api_key]):
        st.markdown('<p class="error">Please fill in all fields to proceed.</p>', unsafe_allow_html=True)
    else:
        quiz_url_list = [url.strip() for url in quiz_urls.split(",") if url.strip()]
        if not quiz_url_list:
            st.markdown('<p class="error">No valid quiz URLs provided.</p>', unsafe_allow_html=True)
        else:
            quiz_results = []
            progress_bar = st.progress(0, text="Initializing...")
            status_text = st.empty()
            progress_log = st.empty()

            # Initialize progress log
            progress_messages = []

            def update_progress(message, quiz_index=None, total_quizzes=None, duration=None):
                timestamp = datetime.now().strftime("%H:%M:%S")
                if quiz_index is not None and total_quizzes is not None:
                    prefix = f"[Quiz {quiz_index}/{total_quizzes}] "
                else:
                    prefix = ""
                if duration is not None:
                    message = f"{message} ({duration:.2f}s)"
                progress_messages.append(f"[{timestamp}] {prefix}{message}")
                progress_log.markdown(
                    '<div class="log-container">' + "<br>".join(progress_messages[-5:]) + '</div>',
                    unsafe_allow_html=True
                )

            # Selenium setup
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            try:
                driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
                wait = WebDriverWait(driver, 15)
            except Exception as e:
                st.markdown(f'<p class="error">Failed to initialize WebDriver: {e}</p>', unsafe_allow_html=True)
                st.stop()

            # Login
            try:
                start_time = time.time()
                update_progress("Logging in...")
                driver.get(login_url)
                max_retries = 3
                for attempt in range(max_retries):
                    if check_503(driver):
                        update_progress(f"503 detected during login, retrying (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        driver.refresh()
                        continue
                    break
                else:
                    st.markdown('<p class="error">Failed to bypass 503 error during login</p>', unsafe_allow_html=True)
                    driver.quit()
                    st.stop()
                wait.until(EC.visibility_of_element_located((By.ID, 'username'))).send_keys(username)
                wait.until(EC.visibility_of_element_located((By.ID, 'password'))).send_keys(password)
                wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn'))).click()
                time.sleep(1)
                update_progress("Login successful", duration=time.time() - start_time)
            except Exception as e:
                st.markdown(f'<p class="error">Login failed: {e}</p>', unsafe_allow_html=True)
                with open("login_page_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                st.write("Debug: Page source saved to 'login_page_source.html'")
                driver.quit()
                st.stop()

            # Process quizzes
            for quiz_index, quiz_url in enumerate(quiz_url_list, 1):
                status_text.markdown(f'<div class="progress">Processing Quiz {quiz_index}/{len(quiz_url_list)}: {quiz_url}</div>', unsafe_allow_html=True)
                progress_bar.progress(quiz_index / len(quiz_url_list), text=f"Processing Quiz {quiz_index}/{len(quiz_url_list)}")
                result = {"url": quiz_url, "status": "Failed", "marks": "N/A", "error": None}

                try:
                    start_time = time.time()
                    update_progress(f"Navigating to quiz", quiz_index, len(quiz_url_list))
                    driver.get(quiz_url)
                    max_retries = 3
                    for attempt in range(max_retries):
                        if check_503(driver):
                            update_progress(f"503 detected for quiz page, retrying (attempt {attempt + 1}/{max_retries})", quiz_index, len(quiz_url_list))
                            time.sleep(2)
                            driver.refresh()
                            continue
                        break
                    else:
                        result["error"] = "Failed to bypass 503 error for quiz page"
                        quiz_results.append(result)
                        continue
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "page-header-headings")))
                    update_progress("Quiz page loaded", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                except Exception as e:
                    result["error"] = f"Failed to navigate to quiz: {e}"
                    quiz_results.append(result)
                    continue

                # Start quiz
                try:
                    start_time = time.time()
                    update_progress(f"Attempting to start quiz", quiz_index, len(quiz_url_list))
                    quiz_button_xpath = "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | //input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]"
                    quiz_button = wait.until(EC.element_to_be_clickable((By.XPATH, quiz_button_xpath)))
                    driver.execute_script("arguments[0].click();", quiz_button)
                    time.sleep(1)
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                    update_progress("Quiz started", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                except:
                    try:
                        start_attempt_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt')] | //input[contains(@value,'Start attempt')]")))
                        driver.execute_script("arguments[0].click();", start_attempt_button)
                        time.sleep(2)
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                        update_progress("Quiz started after confirmation", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                    except Exception as e:
                        result["error"] = f"Could not start quiz: {e}"
                        with open(f"quiz_start_page_source_{quiz_index}.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        st.write(f"Debug: Page source for quiz {quiz_index} saved to 'quiz_start_page_source_{quiz_index}.html'")
                        quiz_results.append(result)
                        continue

                # Process questions
                page_count = 0
                finish_attempt_xpath = "//input[@value='Finish attempt ...' and @name='next' and @id='mod_quiz-next-nav']"
                while True:
                    page_count += 1
                    start_time = time.time()
                    update_progress(f"Processing question page {page_count}", quiz_index, len(quiz_url_list))
                    max_retries = 3
                    for attempt in range(max_retries):
                        if check_503(driver):
                            update_progress(f"503 detected on question page {page_count}, retrying (attempt {attempt + 1}/{max_retries})", quiz_index, len(quiz_url_list))
                            time.sleep(2)
                            driver.refresh()
                            continue
                        break
                    else:
                        update_progress(f"Failed to bypass 503 error on question page {page_count}", quiz_index, len(quiz_url_list))
                        st.markdown(f'<p class="error">Failed to bypass 503 error for question {page_count} in quiz {quiz_index}</p>', unsafe_allow_html=True)
                        break

                    try:
                        question_element = WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.CLASS_NAME, "qtext"))
                        )
                        question_text = question_element.text.strip()
                        update_progress(f"Found question: {question_text[:50]}...", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                        start_time = time.time()
                        answer_block = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
                        soup = BeautifulSoup(answer_block.get_attribute('outerHTML'), 'html.parser')
                        option_texts, radio_elements = [], []
                        for inp in soup.find_all('input', {'type': 'radio'}):
                            option_id = inp.get('id')
                            if option_id:
                                label_text = ""
                                if label_id := inp.get('aria-labelledby'):
                                    if label_div := soup.find(id=label_id):
                                        label_text = label_div.get_text(strip=True)
                                elif soup.find('label', {'for': option_id}):
                                    label_text = soup.find('label', {'for': option_id}).get_text(strip=True)
                                elif inp.find_next_sibling('label'):
                                    label_text = " ".join(inp.find_next_sibling('label').get_text(strip=True).split())
                                if label_text:
                                    option_texts.append(label_text)
                                    try:
                                        radio_elements.append(driver.find_element(By.ID, option_id))
                                    except:
                                        option_texts.pop()
                                        continue
                        update_progress(f"Parsed options", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                        if option_texts and len(option_texts) == len(radio_elements):
                            update_progress(f"Found {len(option_texts)} options: {', '.join(option_texts[:2])}...", quiz_index, len(quiz_url_list))
                            start_time = time.time()
                            model_answer_letter, gemini_duration = ask_gemini(question_text, option_texts, gemini_api_key)
                            update_progress(f"Gemini responded", quiz_index, len(quiz_url_list), duration=gemini_duration)
                            if model_answer_letter in 'abcd'[:len(option_texts)]:
                                answer_index = ord(model_answer_letter) - ord('a')
                                if 0 <= answer_index < len(radio_elements):
                                    start_time = time.time()
                                    wait.until(EC.element_to_be_clickable(radio_elements[answer_index]))
                                    driver.execute_script("arguments[0].click();", radio_elements[answer_index])
                                    update_progress(f"Selected option {model_answer_letter}: {option_texts[answer_index][:50]}...", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                                else:
                                    update_progress(f"Invalid Gemini response: {model_answer_letter} out of bounds", quiz_index, len(quiz_url_list))
                                    st.markdown(f'<p class="error">Failed to select option for question {page_count} in quiz {quiz_index}: Invalid Gemini response</p>', unsafe_allow_html=True)
                            else:
                                update_progress(f"Gemini returned invalid/no response: {model_answer_letter}", quiz_index, len(quiz_url_list))
                                st.markdown(f'<p class="error">Failed to select option for question {page_count} in quiz {quiz_index}: Invalid Gemini response</p>', unsafe_allow_html=True)
                        else:
                            update_progress("No valid options found for question", quiz_index, len(quiz_url_list))
                            st.markdown(f'<p class="error">No valid options found for question {page_count} in quiz {quiz_index}</p>', unsafe_allow_html=True)
                    except Exception as e:
                        update_progress(f"No question found on page {page_count}: {e}", quiz_index, len(quiz_url_list), duration=time.time() - start_time)

                    try:
                        start_time = time.time()
                        finish_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, finish_attempt_xpath))
                        )
                        update_progress("Found 'Finish attempt ...' button", quiz_index, len(quiz_url_list))
                        driver.execute_script("arguments[0].click();", finish_btn)
                        time.sleep(1)
                        update_progress("Clicked 'Finish attempt ...'", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                        start_time = time.time()
                        submit_all_btn1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(text(), 'Submit all and finish')]")))
                        driver.execute_script("arguments[0].click();", submit_all_btn1)
                        time.sleep(1)
                        update_progress("Clicked first 'Submit all and finish'", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                        start_time = time.time()
                        submit_all_btn2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @data-action='save' and contains(text(), 'Submit all and finish')]")))
                        driver.execute_script("arguments[0].click();", submit_all_btn2)
                        time.sleep(1)
                        update_progress("Clicked second 'Submit all and finish'", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                        start_time = time.time()
                        finish_review_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='mod_quiz-next-nav' and contains(text(), 'Finish review')]")))
                        driver.execute_script("arguments[0].click();", finish_review_btn)
                        time.sleep(1)
                        update_progress("Clicked 'Finish review'", quiz_index, len(quiz_url_list), duration=time.time() - start_time)

                        # Extract marks
                        try:
                            start_time = time.time()
                            update_progress("Extracting marks...", quiz_index, len(quiz_url_list))
                            max_retries = 3
                            for attempt in range(max_retries):
                                if check_503(driver):
                                    update_progress(f"503 detected during marks extraction, retrying (attempt {attempt + 1}/{max_retries})", quiz_index, len(quiz_url_list))
                                    time.sleep(2)
                                    driver.refresh()
                                    continue
                                break
                            else:
                                result["error"] = "Failed to bypass 503 error during marks extraction"
                                quiz_results.append(result)
                                break
                            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.quizattemptsummary")))
                            soup = BeautifulSoup(table.get_attribute('outerHTML'), 'html.parser')
                            rows = soup.find_all('tr', class_='lastrow')
                            current_time = datetime.now()
                            latest_marks = "N/A"
                            latest_timestamp = None
                            for row in rows:
                                try:
                                    timestamp_cell = row.find('td', class_='c1')
                                    marks_cell = row.find('td', class_='c2')
                                    if timestamp_cell and marks_cell:
                                        timestamp_text = timestamp_cell.find('span', class_='statedetails').get_text(strip=True)
                                        marks = marks_cell.get_text(strip=True)
                                        timestamp_match = re.search(r"Submitted\s+\w+,\s+(\d+\s+\w+\s+\d{4},\s+\d+:\d+\s+[AP]M)", timestamp_text)
                                        if timestamp_match:
                                            timestamp = datetime.strptime(timestamp_match.group(1), "%d %B %Y, %I:%M %p")
                                            time_diff = (current_time - timestamp).total_seconds() / 60
                                            if time_diff < 10 and (latest_timestamp is None or timestamp > latest_timestamp):
                                                latest_marks = marks
                                                latest_timestamp = timestamp
                                except:
                                    continue
                            update_progress(f"Marks extracted: {latest_marks}", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                            result["status"] = "Completed"
                            result["marks"] = latest_marks
                            quiz_results.append(result)
                            break
                        except Exception as e:
                            result["error"] = f"Failed to extract marks: {e}"
                            with open(f"marks_page_source_{quiz_index}.html", "w", encoding="utf-8") as f:
                                f.write(driver.page_source)
                            st.write(f"Debug: Page source for quiz {quiz_index} saved to 'marks_page_source_{quiz_index}.html'")
                            quiz_results.append(result)
                            break
                    except:
                        start_time = time.time()
                        update_progress("No 'Finish attempt ...' button found, checking for next page", quiz_index, len(quiz_url_list))
                        try:
                            next_btn = WebDriverWait(driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, "//input[@value='Next page']"))
                            )
                            driver.execute_script("arguments[0].click();", next_btn)
                            max_retries = 3
                            for attempt in range(max_retries):
                                if check_503(driver):
                                    update_progress(f"503 detected after next page click, retrying (attempt {attempt + 1}/{max_retries})", quiz_index, len(quiz_url_list))
                                    time.sleep(2)
                                    driver.refresh()
                                    continue
                                break
                            else:
                                update_progress(f"Failed to bypass 503 error after next page click", quiz_index, len(quiz_url_list))
                                st.markdown(f'<p class="error">Failed to bypass 503 error for question {page_count} in quiz {quiz_index}</p>', unsafe_allow_html=True)
                                break
                            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                            update_progress("Clicked 'Next page'", quiz_index, len(quiz_url_list), duration=time.time() - start_time)
                        except Exception as e:
                            result["error"] = f"Failed to navigate to next page: {e}"
                            with open(f"question_page_{quiz_index}_{page_count}_source.html", "w", encoding="utf-8") as f:
                                f.write(driver.page_source)
                            st.write(f"Debug: Page source for quiz {quiz_index} page {page_count} saved to 'question_page_{quiz_index}_{page_count}_source.html'")
                            quiz_results.append(result)
                            break

            # Display results
            status_text.markdown('<div class="success">All quizzes processed!</div>', unsafe_allow_html=True)
            progress_bar.empty()
            st.markdown('<p class="success">Processing complete!</p>', unsafe_allow_html=True)
            with st.expander("Quiz Results", expanded=True):
                st.markdown('<div class="expander-header">Results Summary</div>', unsafe_allow_html=True)
                if quiz_results:
                    st.markdown("""
                        <table class="result-table">
                            <tr>
                                <th>Quiz URL</th>
                                <th>Status</th>
                                <th>Marks</th>
                                <th>Error</th>
                            </tr>
                    """, unsafe_allow_html=True)
                for result in quiz_results:
                    status_icon = "✅" if result["status"] == "Completed" else "❌"
                    error_text = result["error"] if result["error"] else "-"
                    table_html += f"""
                    <tr>
                    <td>{result['url'][:50]}...</td>
                    <td>{status_icon} {result['status']}</td>
                    <td>{result['marks']}</td>
                    <td>{error_text}</td>
                    </tr>
                    """
                    table_html += """
                    </table>
                    <a href="#quiz-results">Quiz Results</a>
                    """
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
                    st.markdown('<p class="error">No results to display.</p>', unsafe_allow_html=True)

driver.quit()
