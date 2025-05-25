import os
import time
import asyncio
import aiohttp
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse

async def ask_gemini(question, options, api_key, max_retries=2):
    """
    Queries the Gemini API asynchronously to get the correct answer.
    
    Args:
        question (str): The quiz question.
        options (list): List of answer options.
        api_key (str): The Gemini API key.
        max_retries (int): Maximum retries for API call failures.
    
    Returns:
        str: The letter of the chosen answer (e.g., 'a', 'b', 'c', 'd') or empty string if failed.
    """
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
    option_letters = ['a', 'b', 'c', 'd']
    formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options[:len(option_letters)])])
    prompt = (
        f"Question: {question}\nOptions:\n{formatted_options}\nAnswer with ONLY the letter (a, b, c, or d):"
    )
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(max_retries):
            try:
                async with session.post(
                    f"{GEMINI_API_URL}?key={api_key}",
                    json=payload,
                    headers=headers,
                    timeout=3  # Reduced timeout
                ) as response:
                    response.raise_for_status()
                    response_data = await response.json()
                    generated_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
                    print(f"Gemini Response: '{generated_text}'")
                    
                    # Prioritize direct letter match
                    match = re.match(r"^\s*([a-d])\s*$", generated_text)
                    if match:
                        letter = match.group(1)
                        if letter in option_letters[:len(options)]:
                            return letter
                    
                    # Fallback to any letter in text
                    match = re.search(r"\b([a-d])\b", generated_text)
                    if match:
                        letter = match.group(1)
                        if letter in option_letters[:len(options)]:
                            return letter
                    
                    print("No valid letter found in response.")
                    return ""
            except Exception as e:
                print(f"API call failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    return ""
                await asyncio.sleep(0.2)  # Brief retry delay
    
    return ""

def attempt_quiz_start(driver, wait, max_attempts=2):
    """
    Attempts to start or continue the quiz by locating and clicking the appropriate button.
    
    Args:
        driver: The Selenium WebDriver instance.
        wait: The WebDriverWait instance.
        max_attempts (int): Maximum number of attempts to find and click the button.
    
    Returns:
        bool: True if the quiz was successfully started or continued, False otherwise.
    """
    for attempt in range(1, max_attempts + 1):
        print(f"Attempt {attempt}/{max_attempts} to start/continue quiz...")
        try:
            quiz_button_css = "button[value*='Attempt quiz'], input[value*='Attempt quiz'], button[value*='Continue your attempt'], input[value*='Continue your attempt']"
            quiz_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, quiz_button_css)))
            driver.execute_script("arguments[0].click();", quiz_button)  # JavaScript click for speed
            print("Clicked quiz start/continue button.")
            
            # Check if quiz started
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".qtext")))
                print("Quiz started successfully.")
                return True
            except:
                print("Checking for 'Start attempt' confirmation...")
                try:
                    start_attempt_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[value*='Start attempt'], input[value*='Start attempt']")))
                    driver.execute_script("arguments[0].click();", start_attempt_button)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".qtext")))
                    print("Quiz started via confirmation.")
                    return True
                except Exception as e:
                    print(f"Failed to start quiz: {e}")
        except Exception as e:
            print(f"Could not find quiz button: {e}")
        if attempt == max_attempts:
            print("Failed to start quiz after max attempts.")
            return False
    return False

async def run_bot(username, password, quiz_url, api_key):
    """
    Main function to run the Moodle quiz bot with optimized performance.
    
    Args:
        username (str): Moodle username.
        password (str): Moodle password.
        quiz_url (str): URL of the quiz page.
        api_key (str): Gemini API key.
    
    Raises:
        ValueError: If any input is empty or invalid.
    """
    # Input validation
    if not all([username, password, quiz_url, api_key]):
        raise ValueError("All inputs (username, password, quiz_url, api_key) must be provided.")
    if not quiz_url.startswith(("http://", "https://")):
        raise ValueError("Quiz URL must start with http:// or https://")

    # Optimized Selenium setup
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--blink-settings=imagesEnabled=false")
    chrome_options.page_load_strategy = 'eager'  # Load DOM faster
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.implicitly_wait(2)  # Implicit wait for faster element lookup
    wait = WebDriverWait(driver, 5)  # Reduced timeout
    
    try:
        # Derive login URL
        parsed_url = urlparse(quiz_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        login_url = f"{base_url}/login/index.php"
        print(f"Login URL: {login_url}")
        
        # Login
        print("Navigating to login page...")
        driver.get(login_url)
        username_field = wait.until(EC.visibility_of_element_located((By.ID, 'username')))
        password_field = wait.until(EC.visibility_of_element_located((By.ID, 'password')))
        login_button = wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn')))
        username_field.send_keys(username)
        password_field.send_keys(password)
        driver.execute_script("arguments[0].click();", login_button)  # JavaScript click
        print("Login attempted.")
        
        # Navigate to quiz
        print(f"Navigating to quiz: {quiz_url}")
        driver.get(quiz_url)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".page-header-headings")))
        print("Arrived at quiz page.")
        
        # Start quiz
        if not attempt_quiz_start(driver, wait):
            print("Failed to start quiz. Exiting.")
            return
        
        # Process quiz questions
        page_count = 0
        finish_attempt_css = "input[value='Finish attempt ...'][name='next'][id='mod_quiz-next-nav']"
        while True:
            page_count += 1
            print(f"\nProcessing Question Page {page_count}")
            try:
                question_element = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".qtext")))
                question_text = question_element.text.strip()
                print(f"Question: {question_text[:100]}...")
                
                answer_block = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".answer")))
                answer_html = answer_block.get_attribute('outerHTML')
                soup = BeautifulSoup(answer_html, 'html.parser')
                option_texts, radio_elements = [], []
                
                # Optimized parsing
                for inp in soup.select('input[type="radio"]'):
                    option_id = inp.get('id')
                    if option_id:
                        label_text = ""
                        label_id = inp.get('aria-labelledby')
                        if label_id and (label_div := soup.find(id=label_id)):
                            label_text = label_div.get_text(strip=True)
                        elif (label := soup.find('label', {'for': option_id})):
                            label_text = label.get_text(strip=True)
                        if label_text:
                            option_texts.append(label_text)
                            radio_elements.append(driver.find_element(By.ID, option_id))
                
                if option_texts and radio_elements:
                    model_answer_letter = await ask_gemini(question_text, option_texts, api_key)
                    if model_answer_letter in 'abcd'[:len(option_texts)]:
                        answer_index = ord(model_answer_letter) - ord('a')
                        driver.execute_script("arguments[0].click();", radio_elements[answer_index])
                        print(f"Selected option {model_answer_letter}: {option_texts[answer_index]}")
                    else:
                        print("No valid answer received from Gemini.")
            except Exception as e:
                print(f"Error on page {page_count}: {e}")
            
            # Navigate to next page or finish
            try:
                finish_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, finish_attempt_css)))
                print("Finishing quiz...")
                driver.execute_script("arguments[0].click();", finish_btn)
                
                submit_all_btn1 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']:contains('Submit all and finish')")))
                driver.execute_script("arguments[0].click();", submit_all_btn1)
                
                submit_all_btn2 = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='button'][data-action='save']:contains('Submit all and finish')")))
                driver.execute_script("arguments[0].click();", submit_all_btn2)
                
                finish_review_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a.mod_quiz-next-nav:contains('Finish review')")))
                driver.execute_script("arguments[0].click();", finish_review_btn)
                print("Quiz submitted successfully.")
                break
            except:
                try:
                    next_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Next page'], button:contains('Next page')")))
                    driver.execute_script("arguments[0].click();", next_btn)
                    print("Moved to next page.")
                except:
                    print("No more pages or error navigating. Exiting.")
                    break
    
    finally:
        driver.quit()
        print("WebDriver closed.")

if __name__ == "__main__":
    # For local testing (replace with your credentials)
    asyncio.run(run_bot("test_user", "test_pass", "https://lms2.eee.saveetha.in/mod/quiz/view.php?id=551", "your_api_key"))