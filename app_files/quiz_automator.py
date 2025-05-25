import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup
import requests
import re
from datetime import datetime, timedelta
import pandas as pd
from io import StringIO

# Initialize driver as None at the global scope
driver = None

# Custom CSS for enhanced styling
st.markdown("""
<style>
:root {
    --background-color: #F8FAFC;
    --text-color: #1F2937;
    --primary-color: #1E3A8A;
    --success-color: #10B981;
    --error-color: #EF4444;
    --border-color: #D1D5DB;
    --input-focus-color: #10B981;
    --table-header-bg: #F3F4F6;
    --table-row-bg: white;
    --table-row-hover-bg: #E5E7EB;
}

@media (prefers-color-scheme: dark) {
    :root {
        --background-color: #1F2937;
        --text-color: #F8FAFC;
        --primary-color: #60A5FA;
        --success-color: #34D399;
        --error-color: #F87171;
        --border-color: #4B5563;
        --input-focus-color: #34D399;
        --table-header-bg: #374151;
        --table-row-bg: #2D3748;
        --table-row-hover-bg: #4B5563;
    }
}

body {
    font-family: 'Inter', sans-serif;
    background-color: var(--background-color);
    color: var(--text-color);
    margin: 0;
    padding: 0;
}

h1 {
    font-size: 3rem;
    font-weight: 800;
    color: var(--primary-color);
    text-align: center;
    margin-bottom: 0.5rem;
    animation: fadeIn 1s ease-in;
}

p.subtitle {
    font-size: 1.2rem;
    color: var(--text-color);
    opacity: 0.7;
    text-align: center;
    margin-bottom: 2rem;
}

.form-container {
    background-color: var(--table-row-bg);
    padding: 2rem;
    border-radius: 0.5rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    max-width: 700px;
    margin: 0 auto 2rem auto;
}

.form-label {
    font-size: 1rem;
    font-weight: 500;
    color: var(--text-color);
    margin-bottom: 0.5rem;
    display: block;
}

.form-input, .form-textarea, select {
    width: 100%;
    padding: 0.75rem;
    margin-bottom: 1rem;
    border: 1px solid var(--border-color);
    border-radius: 0.375rem;
    font-size: 1rem;
    color: var(--text-color);
    background-color: var(--background-color);
}

.form-input:focus, .form-textarea:focus, select:focus {
    outline: none;
    border-color: var(--input-focus-color);
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.form-input::placeholder, .form-textarea::placeholder {
    color: var(--border-color);
    opacity: 0.7;
}

.form-input:focus::placeholder, .form-textarea:focus::placeholder {
    color: transparent;
}

.button-container {
    display: flex;
    gap: 1rem;
}

button.primary {
    flex: 1;
    padding: 0.75rem;
    background: linear-gradient(to right, var(--success-color), #34D399);
    color: white;
    font-weight: 600;
    border: none;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: transform 0.2s ease;
}

button.secondary {
    flex: 1;
    padding: 0.75rem;
    background: var(--border-color);
    color: var(--text-color);
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
    background-color: var(--table-row-bg);
    padding: 1rem;
    border-radius: 0.375rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    margin-top: 1rem;
    margin-bottom: 2rem;
}

.success {
    color: var(--success-color);
}

.success::before {
    content: "✔ ";
}

.error {
    color: var(--error-color);
}

.error::before {
    content: "✘ ";
}

.result-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
}

.result-table th, .result-table td {
    padding: 1rem;
    border: 1px solid var(--border-color);
    text-align: left;
}

.result-table th {
    background-color: var(--table-header-bg);
    font-weight: 600;
    color: var(--text-color);
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.result-table th:hover {
    background-color: var(--table-row-hover-bg);
}

.result-table td {
    background-color: var(--table-row-bg);
    color: var(--text-color);
}

.result-table tr:hover {
    background-color: var(--table-row-hover-bg);
}

.expander-header {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--primary-color);
    margin-bottom: 1rem;
}

.section-spacing {
    margin-bottom: 3rem;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Modal styles */
.modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal-content {
    background: var(--table-row-bg);
    padding: 2rem;
    border-radius: 0.5rem;
    max-width: 80%;
    max-height: 80%;
    overflow-y: auto;
    position: relative;
}

.close-button {
    position: absolute;
    top: 1rem;
    right: 1rem;
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--text-color);
}
</style>
""", unsafe_allow_html=True)

# Main app logic
def main():
    global driver  # Declare driver as global to modify it

    # UI Header
    st.markdown('<h1>Moodle Quiz Automator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Automate your Moodle quizzes with ease</p>', unsafe_allow_html=True)

    # Initialize session state for user details and other data
    if "user_details" not in st.session_state:
        st.session_state.user_details = {"username": "", "password": "", "gemini_api_key": ""}
    if "progress_messages" not in st.session_state:
        st.session_state.progress_messages = []
    if "quiz_results" not in st.session_state:
        st.session_state.quiz_results = []
    if "show_modal" not in st.session_state:
        st.session_state.show_modal = False
    if "sort_column" not in st.session_state:
        st.session_state.sort_column = None
    if "sort_ascending" not in st.session_state:
        st.session_state.sort_ascending = True

    # Form for user input
    user_details = st.session_state.user_details
    with st.form(key="automation_form"):
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<label class="form-label" for="login_url">Login URL</label>', unsafe_allow_html=True)
        login_url = st.selectbox("Select Login URL", [
            "https://lms2.ai.saveetha.in/login/index.php",
            "https://lms2.cse.saveetha.in/login/index.php",
            "https://lms2.eee.saveetha.in/login/index.php",
            "https://lms.saveetha.in/login/index.php"
        ], index=0, key="login_url")
        st.markdown('<label class="form-label" for="username">Username</label>', unsafe_allow_html=True)
        username = st.text_input("Username", value=user_details["username"], placeholder="Enter your username", key="username")
        st.markdown('<label class="form-label" for="password">Password</label>', unsafe_allow_html=True)
        password = st.text_input("Password", value=user_details["password"], type="password", placeholder="Enter your password", key="password")
        st.markdown('<label class="form-label" for="gemini_api_key">Gemini API Key</label>', unsafe_allow_html=True)
        gemini_api_key = st.text_input("Gemini API Key", value=user_details["gemini_api_key"], type="password", placeholder="Enter your Gemini API key", key="gemini_api_key")
        st.markdown('<label class="form-label" for="quiz_urls">Quiz URLs (comma-separated)</label>', unsafe_allow_html=True)
        quiz_urls = st.text_area("Quiz URLs", placeholder="Enter quiz URLs, separated by commas", key="quiz_urls")  # Removed default value
        st.markdown('<div class="button-container">', unsafe_allow_html=True)
        submit_button = st.form_submit_button("Start Automation", type="primary")
        clear_button = st.form_submit_button("Clear Form", type="secondary")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Handle clear form button
    if clear_button:
        st.session_state.user_details = {"username": "", "password": "", "gemini_api_key": ""}
        st.session_state.quiz_results = []
        st.session_state.progress_messages = []
        st.rerun()

    # Placeholder for progress updates
    progress_container = st.empty()
    status_text = st.empty()
    progress_bar = st.empty()

    # Function to update progress messages
    def update_progress(message, is_error=False, duration=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if duration is not None:
            message = f"{message} ({duration:.2f}s)"
        formatted_message = f"[{timestamp}] {message}"
        st.session_state.progress_messages.append((formatted_message, is_error))
        with progress_container.container():
            st.markdown('<div class="log-container">', unsafe_allow_html=True)
            for msg, error in st.session_state.progress_messages[-5:]:
                if error:
                    st.markdown(f'<p class="error">{msg}</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p class="success">{msg}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        if st.button("Show Full Log"):
            st.session_state.show_modal = True

    # Modal for full log
    if st.session_state.show_modal:
        with st.container():
            st.markdown('<div class="modal">', unsafe_allow_html=True)
            st.markdown('<div class="modal-content">', unsafe_allow_html=True)
            if st.button("✕", key="close_modal", help="Close"):
                st.session_state.show_modal = False
                st.rerun()
            st.markdown('<h3>Full Log</h3>', unsafe_allow_html=True)
            for msg, error in st.session_state.progress_messages:
                if error:
                    st.markdown(f'<p class="error">{msg}</p>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<p class="success">{msg}</p>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
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
    if submit_button:
        if not (login_url and username and password and gemini_api_key and quiz_urls):
            update_progress("Please fill in all fields", is_error=True)
        else:
            # Update session state with user details
            user_details = {"username": username, "password": password, "gemini_api_key": gemini_api_key}
            st.session_state.user_details.update(user_details)

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
                    # Update progress bar
                    progress = quiz_index / total_quizzes
                    progress_bar.progress(progress)

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
                        st.session_state.quiz_results.append({
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
                        st.session_state.quiz_results.append({
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
                                st.session_state.quiz_results.append({
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
                        st.session_state.quiz_results.append({
                            "url": quiz_url,
                            "status": "Completed",
                            "marks": latest_marks,
                            "error": None
                        })
                    else:
                        update_progress(f"[Quiz {quiz_index}/{total_quizzes}] Failed to extract marks", is_error=True)
                        st.session_state.quiz_results.append({
                            "url": quiz_url,
                            "status": "Failed",
                            "marks": "N/A",
                            "error": "Failed to extract marks"
                        })

                # Display results
                status_text.markdown('<div class="success">All quizzes processed!</div>', unsafe_allow_html=True)
                progress_bar.empty()
                st.markdown('<p class="success section-spacing">Processing complete!</p>', unsafe_allow_html=True)

            finally:
                # Cleanup: Only call driver.quit() if driver was initialized
                if driver is not None:
                    try:
                        driver.quit()
                        update_progress("Browser session closed successfully")
                    except Exception as e:
                        update_progress(f"Error closing browser session: {str(e)}", is_error=True)

    # Display results
    with st.expander("Quiz Results", expanded=False):
        st.markdown('<div class="expander-header">Results Summary</div>', unsafe_allow_html=True)
        if st.session_state.quiz_results:
            # Convert results to DataFrame for sorting
            df = pd.DataFrame(st.session_state.quiz_results)

            # Sorting logic
            def sort_table(column):
                if st.session_state.sort_column == column:
                    st.session_state.sort_ascending = not st.session_state.sort_ascending
                else:
                    st.session_state.sort_column = column
                    st.session_state.sort_ascending = True
                sort_direction = st.session_state.sort_ascending
                df_sorted = df.sort_values(by=column, ascending=sort_direction)
                st.session_state.quiz_results = df_sorted.to_dict('records')

            # Table headers with sorting
            table_html = """
                <table class="result-table">
                    <tr>
                        <th onclick="sortTable('url')">Quiz URL ↕</th>
                        <th onclick="sortTable('status')">Status ↕</th>
                        <th onclick="sortTable('marks')">Marks ↕</th>
                        <th onclick="sortTable('error')">Error ↕</th>
                    </tr>
            """
            # Add JavaScript for sorting
            st.markdown("""
            <script>
            function sortTable(column) {
                var event = new CustomEvent('sortTableEvent', { detail: column });
                window.dispatchEvent(event);
            }
            </script>
            """, unsafe_allow_html=True)

            # Listen for JavaScript events
            sort_event = st._get_widget_ui_value("sortTableEvent", None)
            if sort_event:
                sort_table(sort_event)

            # Add rows
            for result in st.session_state.quiz_results:
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

            # Download button for results
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name="quiz_results.csv",
                mime="text/csv",
            )
        else:
            st.markdown('<p class="error">No results to display.</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
