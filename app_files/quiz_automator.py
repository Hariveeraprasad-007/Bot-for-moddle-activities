import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import json
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime, timedelta
import os

# Initialize driver as None at the global scope
driver = None

# Custom CSS for styling
st.markdown("""
<style>
body {
    font-family: 'Inter', sans-serif;
    background-color: #F8FAFC;
    color: #1F2937;
}
h1 {
    font-size: 2.5rem;
    font-weight: 700;
    color: #1E3A8A;
    text-align: center;
    margin-bottom: 0.5rem;
}
h2 {
    font-size: 1.5rem;
    font-weight: 600;
    color: #1E3A8A;
    margin-top: 2rem;
}
p {
    font-size: 1rem;
    color: #6B7280;
    text-align: center;
}
.form-container {
    background-color: white;
    padding: 2rem;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    max-width: 600px;
    margin: 0 auto;
}
.form-label {
    font-size: 1rem;
    font-weight: 500;
    color: #1F2937;
    margin-bottom: 0.5rem;
    display: block;
}
.form-input, .form-textarea, select {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid #D1D5DB;
    border-radius: 0.375rem;
    font-size: 1rem;
    color: #1F2937;
}
.form-input:focus, .form-textarea:focus, select:focus {
    outline: none;
    border-color: #10B981;
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}
.form-input::placeholder, .form-textarea::placeholder {
    color: #9CA3AF;
}
.form-input:focus::placeholder, .form-textarea:focus::placeholder {
    color: transparent;
}
button {
    width: 100%;
    padding: 0.75rem;
    background: linear-gradient(to right, #10B981, #34D399);
    color: white;
    font-weight: 600;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: transform 0.2s ease;
}
button:hover {
    transform: translateY(-2px);
}
.log-container {
    max-height: 200px;
    overflow-y: auto;
    background-color: white;
    padding: 1rem;
    border-radius: 0.375rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    margin-top: 1rem;
}
.success {
    color: #10B981;
}
.error {
    color: #EF4444;
}
.result-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
}
.result-table th, .result-table td {
    padding: 0.75rem;
    border: 1px solid #D1D5DB;
    text-align: left;
}
.result-table th {
    background-color: #F3F4F6;
    font-weight: 600;
    color: #1F2937;
}
.result-table td {
    background-color: white;
    color: #1F2937;
}
.expander-header {
    font-size: 1.25rem;
    font-weight: 600;
    color: #1E3A8A;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

# Main app logic
def main():
    global driver  # Declare driver as global to modify it

    # UI Header
    st.markdown('<h1>Moodle Quiz Automator</h1>', unsafe_allow_html=True)
    st.markdown('<p>Automate your Moodle quizzes with ease</p>', unsafe_allow_html=True)

    # Load user details
    user_details_file = "/workspaces/Bot-for-moddle-activities/user_details.json"
    user_details = {"username": "", "password": "", "gemini_api_key": ""}
    if os.path.exists(user_details_file):
        with open(user_details_file, "r") as f:
            user_details = json.load(f)

    # Form for user input
    with st.form(key="automation_form"):
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        login_url = st.selectbox("Select Login URL", [
            "https://lms2.ai.saveetha.in/login/index.php",
            "https://lms2.cse.saveetha.in/login/index.php",
            "https://lms2.eee.saveetha.in/login/index.php",
            "https://lms.saveetha.in/login/index.php"
        ], index=0)
        username = st.text_input("Username", value=user_details["username"], placeholder="Enter your username")
        password = st.text_input("Password", value=user_details["password"], type="password", placeholder="Enter your password")
        gemini_api_key = st.text_input("Gemini API Key", value=user_details["gemini_api_key"], type="password", placeholder="Enter your Gemini API key")
        quiz_urls = st.text_area("Quiz URLs (comma-separated)", value="https://lms2.ai.saveetha.in/mod/quiz/view.php?id=1790", placeholder="Enter quiz URLs, separated by commas")
        submit_button = st.form_submit_button("Start Automation")
        st.markdown('</div>', unsafe_allow_html=True)

    # Placeholder for progress updates
    progress_messages = []
    progress_container = st.empty()
    status_text = st.empty()
    progress_bar = st.progress(0)

    # Function to update progress messages
    def update_progress(message, is_error=False, duration=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if duration is not None:
            message = f"{message} ({duration:.2f}s)"
        formatted_message = f"[{timestamp}] {message}"
        progress_messages.append(formatted_message)
        with progress_container.container():
            st.markdown('<div class="log-container">', unsafe_allow_html=True)
            for msg in progress_messages[-5:]:
                if is_error:
                    st.markdown(f'<p class="error">{msg}</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p>{msg}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Function to call Gemini API
    def ask_gemini(question, options, gemini_api_key):
        start_time = time.time()
        option_letters = ["a", "b", "c", "d"]
        formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options[:4])])
        prompt = f"Question: {question}\n\nOptions:\n{formatted_options}\n\nAnswer with ONLY the letter of the correct option (a, b, c, d):"
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}",
                headers={"Content-Type": "application/json"},
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=10
            )
            response.raise_for_status()
            answer = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
            duration = time.time() - start_time
            if answer in option_letters[:len(options)]:
                update_progress("Gemini responded", duration=duration)
                return answer
            else:
                update_progress("Gemini returned invalid response", is_error=True, duration=duration)
                return ""
        except requests.RequestException as e:
            update_progress(f"Gemini API call failed: {str(e)}", is_error=True, duration=time.time() - start_time)
            return ""

    # Function to check for 503 errors
    def check_503(driver):
        try:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            return "503 Service Unavailable" in soup.get_text()
        except:
            return False

    # Form submission logic
    quiz_results = []
    if submit_button:
        if not (login_url and username and password and gemini_api_key and quiz_urls):
            update_progress("Please fill in all fields", is_error=True)
        else:
            # Save user details
            user_details = {"username": username, "password": password, "gemini_api_key": gemini_api_key}
            with open(user_details_file, "w") as f:
                json.dump(user_details, f, indent=4)

            # Initialize Selenium WebDriver
            try:
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
                update_progress("Selenium WebDriver initialized successfully")
            except Exception as e:
                update_progress(f"Failed to initialize WebDriver: {str(e)}", is_error=True)
                return  # Exit early if driver initialization fails

            try:
                # Login
                max_retries = 3
                start_time = time.time()
                driver.get(login_url)
                for attempt in range(max_retries):
                    if check_503(driver):
                        update_progress(f"503 detected during login, retrying (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        driver.refresh()
                        continue
                    break
                if check_503(driver):
                    update_progress("Failed to login after retries due to 503 error", is_error=True)
                    return
                driver.find_element(By.ID, "username").send_keys(username)
                driver.find_element(By.ID, "password").send_keys(password)
                driver.find_element(By.ID, "loginbtn").click()
                time.sleep(1)
                update_progress("Login successful", duration=time.time() - start_time)

                # Process quizzes
                quiz_url_list = [url.strip() for url in quiz_urls.split(",") if url.strip()]
                total_quizzes = len(quiz_url_list)
                for quiz_index, quiz_url in enumerate(quiz_url_list, 1):
                    update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Navigating to quiz")
                    start_time = time.time()
                    driver.get(quiz_url)
                    for attempt in range(max_retries):
                        if check_503(driver):
                            update_progress(f"503 detected on quiz page, retrying (attempt {attempt + 1}/{max_retries})")
                            time.sleep(2)
                            driver.refresh()
                            continue
                        break
                    if check_503(driver):
                        quiz_results.append({
                            "url": quiz_url,
                            "status": "Failed",
                            "marks": "N/A",
                            "error": "503 error on quiz page"
                        })
                        continue
                    update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Quiz page loaded", duration=time.time() - start_time)

                    # Start quiz
                    start_time = time.time()
                    try:
                        attempt_button = driver.find_element(By.XPATH, "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | //input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]")
                        attempt_button.click()
                        time.sleep(2)
                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Quiz started", duration=time.time() - start_time)
                    except Exception as e:
                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Failed to start quiz: {str(e)}", is_error=True)
                        quiz_results.append({
                            "url": quiz_url,
                            "status": "Failed",
                            "marks": "N/A",
                            "error": f"Failed to start quiz: {str(e)}"
                        })
                        continue

                    # Process questions
                    page_count = 0
                    while True:
                        page_count += 1
                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Processing question page {page_count}")
                        start_time = time.time()

                        # Save page source for debugging
                        with open(f"question_page_{quiz_index}_{page_count}_source.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)

                        # Extract question and options
                        soup = BeautifulSoup(driver.page_source, "html.parser")
                        question = soup.select_one(".qtext").get_text(strip=True) if soup.select_one(".qtext") else ""
                        options = [label.get_text(strip=True) for label in soup.select(".answer label") if label.get_text(strip=True)]
                        if not question or not options:
                            update_progress(f"[Quiz {quiz_index}/{total_quizzes}] No question found on page {page_count}", is_error=True)
                            break

                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Found question: {question[:50]}...")
                        answer_letter = ask_gemini(question, options, gemini_api_key)
                        if answer_letter:
                            try:
                                index = "abcd".index(answer_letter)
                                radio_buttons = driver.find_elements(By.CSS_SELECTOR, ".answer input[type='radio']")
                                if index < len(radio_buttons):
                                    radio_buttons[index].click()
                                    update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Selected option {answer_letter}")
                                else:
                                    update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Invalid option index", is_error=True)
                            except Exception as e:
                                update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Failed to select option: {str(e)}", is_error=True)
                        else:
                            update_progress(f"[Quiz {quiz_index}/{total_quizzes}] No answer from Gemini", is_error=True)

                        # Check for "Finish attempt ..."
                        try:
                            finish_button = driver.find_element(By.XPATH, "//input[@value='Finish attempt ...' and @name='next' and @id='mod_quiz-next-nav']")
                            finish_button.click()
                            time.sleep(1)
                            update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Clicked 'Finish attempt ...'")
                            break
                        except:
                            try:
                                next_button = driver.find_element(By.CSS_SELECTOR, "input[value='Next page']")
                                next_button.click()
                                time.sleep(2)
                                update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Clicked 'Next page'")
                            except Exception as e:
                                update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Failed to navigate: {str(e)}", is_error=True)
                                quiz_results.append({
                                    "url": quiz_url,
                                    "status": "Failed",
                                    "marks": "N/A",
                                    "error": f"Navigation failed: {str(e)}"
                                })
                                break

                    # Submit and finish
                    try:
                        driver.find_element(By.CSS_SELECTOR, "button[type='submit'][text='Submit all and finish']").click()
                        time.sleep(1)
                        driver.find_element(By.CSS_SELECTOR, "button[type='button'][data-action='save'][text='Submit all and finish']").click()
                        time.sleep(1)
                        driver.find_element(By.CSS_SELECTOR, "a.mod_quiz-next-nav[text='Finish review']").click()
                        time.sleep(1)
                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Quiz submitted")
                    except Exception as e:
                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Failed to submit quiz: {str(e)}", is_error=True)

                    # Extract marks
                    with open(f"marks_page_source_{quiz_index}.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                    table = soup.select_one("table.quizattemptsummary")
                    if table:
                        rows = table.select("tr.lastrow")
                        current_time = datetime.now()
                        latest_marks = "N/A"
                        latest_timestamp = None
                        for row in rows:
                            timestamp_text = row.select_one("td.c1 span.statedetails").get_text() if row.select_one("td.c1 span.statedetails") else ""
                            marks = row.select_one("td.c2").get_text(strip=True) if row.select_one("td.c2") else "N/A"
                            match = re.search(r"Submitted \w+, (\d+ \w+ \d{4}, \d+:\d+ [AP]M)", timestamp_text)
                            if match:
                                timestamp = datetime.strptime(match.group(1), "%d %B %Y, %I:%M %p")
                                time_diff = (current_time - timestamp).total_seconds() / 60
                                if time_diff < 10 and (latest_timestamp is None or timestamp > latest_timestamp):
                                    latest_marks = marks
                                    latest_timestamp = timestamp
                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Marks extracted: {latest_marks}")
                        quiz_results.append({
                            "url": quiz_url,
                            "status": "Completed",
                            "marks": latest_marks,
                            "error": None
                        })
                    else:
                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Failed to extract marks", is_error=True)
                        quiz_results.append({
                            "url": quiz_url,
                            "status": "Failed",
                            "marks": "N/A",
                            "error": "Failed to extract marks"
                        })

                # Display results
                status_text.markdown('<div class="success">All quizzes processed!</div>', unsafe_allow_html=True)
                progress_bar.empty()
                st.markdown('<p class="success">Processing complete!</p>', unsafe_allow_html=True)
                with st.expander("Quiz Results", expanded=True):
                    st.markdown('<div class="expander-header">Results Summary</div>', unsafe_allow_html=True)
                    if quiz_results:
                        table_html = """
                            <table class="result-table">
                                <tr>
                                    <th>Quiz URL</th>
                                    <th>Status</th>
                                    <th>Marks</th>
                                    <th>Error</th>
                                </tr>
                        """
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
                        table_html += "</table>"
                        st.markdown(table_html, unsafe_allow_html=True)
                    else:
                        st.markdown('<p class="error">No results to display.</p>', unsafe_allow_html=True)

            finally:
                # Cleanup: Only call driver.quit() if driver was initialized
                if driver is not None:
                    try:
                        driver.quit()
                        update_progress("Browser session closed successfully")
                    except Exception as e:
                        update_progress(f"Error closing browser session: {str(e)}", is_error=True)

if __name__ == "__main__":
    main()
