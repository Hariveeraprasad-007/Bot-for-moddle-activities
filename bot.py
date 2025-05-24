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
from urllib.parse import urlparse

def ask_gemini(question, options, api_key):
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyAear1HYgtw7Pt3IM8QwKAH5XK-AWvburs"
    option_letters = ['a', 'b', 'c', 'd']
    formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options[:len(option_letters)])])
    prompt = (
        "You are a multiple choice answering bot.\n"
        "Read the question and the options below carefully.\n"
        f"Your response should be ONLY the letter of the correct option ({', '.join(option_letters[:len(options)])}) and nothing else.\n\n"
        f"Question: {question}\n\nOptions:\n{formatted_options}\n\nAnswer:"
    )
    print(f"\nSending prompt to Gemini API:\n---\n{prompt}\n---")
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={api_key}",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        response_data = response.json()
        generated_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
        print(f"Gemini Raw Response: '{generated_text}'")
        potential_answer_match = re.match(r"^\s*([a-d])", generated_text)
        if potential_answer_match:
            direct_letter = potential_answer_match.group(1)
            if direct_letter in option_letters[:len(options)]:
                print(f"Parsed Direct Letter Match: {direct_letter}")
                return direct_letter
        flexible_match = re.search(r"\b([a-d])\b", generated_text)
        if flexible_match:
            found_letter = flexible_match.group(1)
            if found_letter in option_letters[:len(options)]:
                print(f"Parsed Flexible Letter Match: {found_letter}")
                return found_letter
        print("No clear letter found, attempting fuzzy match...")
        best_match_letter, best_score = "", 0
        for idx, opt in enumerate(options):
            score = fuzz.token_set_ratio(generated_text, opt.lower())
            if score > best_score:
                best_score = score
                best_match_letter = option_letters[idx]
        fuzzy_threshold = 80
        if best_score >= fuzzy_threshold:
            print(f"Fuzzy fallback selected: '{best_match_letter}' (score: {best_score})")
            return best_match_letter if best_match_letter in option_letters[:len(options)] else ""
        else:
            print(f"Fuzzy match score {best_score} below threshold {fuzzy_threshold}. Cannot determine answer.")
            return ""
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        return ""

def attempt_quiz_start(driver, wait, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        print(f"\nAttempt {attempt}/{max_attempts} to start or continue quiz...")
        try:
            quiz_button_xpath = "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | //input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]"
            quiz_button = wait.until(EC.element_to_be_clickable((By.XPATH, quiz_button_xpath)))
            button_text = quiz_button.text or quiz_button.get_attribute('value')
            print(f"Found button: '{button_text}'")
            driver.execute_script("arguments[0].click();", quiz_button)
            print("Clicked quiz start/continue button.")
            time.sleep(3)
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                print("Quiz already in progress or started successfully.")
                return True
            except:
                print("Checking for 'Start attempt' confirmation button...")
                try:
                    start_attempt_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt')] | //input[contains(@value,'Start attempt')]")))
                    button_text = start_attempt_button.text or start_attempt_button.get_attribute('value')
                    print(f"Found and clicking 'Start attempt' confirmation button: '{button_text}'")
                    driver.execute_script("arguments[0].click();", start_attempt_button)
                    time.sleep(3)
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                    print("Quiz started successfully, question text found.")
                    return True
                except Exception as e:
                    print(f"Failed to start quiz: {e}")
                    if attempt == max_attempts:
                        with open("quiz_start_page_source.html", "w", encoding="utf-8") as f:
                            f.write(driver.page_source)
                        print("Page source saved to 'quiz_start_page_source.html'.")
                        return False
        except Exception as e:
            print(f"Could not find quiz button: {e}")
            if attempt == max_attempts:
                return False
            time.sleep(2)
    return False

def run_bot(username, password, quiz_url, api_key):
    # Selenium setup
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--log-level=3")
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    wait = WebDriverWait(driver, 60)
    
    try:
        # Derive login URL from quiz URL
        parsed_url = urlparse(quiz_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        login_url = f"{base_url}/login/index.php"
        print(f"Derived login URL: {login_url}")
        
        # Login
        print(f"Navigating to login page: {login_url}")
        driver.get(login_url)
        username_field = wait.until(EC.visibility_of_element_located((By.ID, 'username')))
        password_field = wait.until(EC.visibility_of_element_located((By.ID, 'password')))
        login_button = wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn')))
        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()
        print("Login attempted.")
        time.sleep(2)
        
        # Navigate to quiz
        print(f"Navigating to quiz page: {quiz_url}")
        driver.get(quiz_url)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "page-header-headings")))
        print("Arrived at quiz page.")
        
        # Start quiz
        if not attempt_quiz_start(driver, wait):
            print("Failed to start quiz. Exiting.")
            return
        
        # Process quiz questions
        page_count = 0
        finish_attempt_xpath = "//input[@value='Finish attempt ...' and @name='next' and @id='mod_quiz-next-nav']"
        while True:
            page_count += 1
            print(f"\n--- Processing Question Page {page_count} ---")
            try:
                question_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "qtext")))
                question_text = question_element.text.strip()
                print(f"Question Text: {question_text[:200]}...")
                answer_block = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
                answer_html = answer_block.get_attribute('outerHTML')
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
                        if label_text:
                            option_texts.append(label_text)
                            radio_elements.append(driver.find_element(By.ID, option_id))
                if option_texts:
                    model_answer_letter = ask_gemini(question_text, option_texts, api_key)
                    if model_answer_letter in 'abcd'[:len(option_texts)]:
                        answer_index = ord(model_answer_letter) - ord('a')
                        driver.execute_script("arguments[0].click();", radio_elements[answer_index])
                        print(f"Clicked option {model_answer_letter}: {option_texts[answer_index]}")
            except Exception as e:
                print(f"Error processing question on page {page_count}: {e}")
            
            # Check for finish or next page
            try:
                finish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, finish_attempt_xpath)))
                print("Finishing quiz...")
                driver.execute_script("arguments[0].click();", finish_btn)
                time.sleep(2)
                submit_all_btn1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(text(), 'Submit all and finish')]")))
                driver.execute_script("arguments[0].click();", submit_all_btn1)
                time.sleep(2)
                submit_all_btn2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @data-action='save' and contains(text(), 'Submit all and finish')]")))
                driver.execute_script("arguments[0].click();", submit_all_btn2)
                time.sleep(2)
                finish_review_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='mod_quiz-next-nav' and contains(text(), 'Finish review')]")))
                driver.execute_script("arguments[0].click();", finish_review_btn)
                print("Quiz submitted successfully.")
                break
            except:
                try:
                    next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]")))
                    driver.execute_script("arguments[0].click();", next_btn)
                    print("Clicked 'Next page'.")
                    time.sleep(1)
                except:
                    print("No more pages or error navigating. Exiting.")
                    break
    
    finally:
        if driver:
            driver.quit()
            print("WebDriver closed.")

if __name__ == "__main__":
    run_bot("23004568", "v46662", "https://lms2.eee.saveetha.in/mod/quiz/view.php?id=551", "")