import streamlit as st
import queue
import threading
import time
import os
import re
import pyttsx3
import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, InvalidSessionIdException
import google.generativeai as genai

# --- Configuration ---
LOGIN_SITE_OPTIONS = {
    "EEE Site": "https://lms2.eee.saveetha.in/login/index.php",
    "CSE Site": "https://lms2.cse.saveetha.in/login/index.php",
    "AI Site": "https://lms2.ai.saveetha.in/login/index.php",
}
ACTIVITY_TYPES = ["Speech Submission", "Read-Aloud", "Quiz Automation"]
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# --- Utility Functions ---
def initialize_tts(logger):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 200)  # 200 wpm for ~30-40s on 100-120 words
        engine.setProperty('volume', 0.9)
        logger("Text-to-speech engine initialized.")
        return engine
    except Exception as e:
        logger(f"Failed to initialize pyttsx3: {e}", "error")
        raise Exception("Text-to-speech initialization failed.")

def setup_selenium(headless, logger):
    logger("Initializing Chrome WebDriver...")
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1920,1080")
    if headless:
        options.add_argument("--headless")
    try:
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        wait = WebDriverWait(driver, 20)
        logger("WebDriver initialized successfully.")
        return driver, wait
    except Exception as e:
        logger(f"Failed to initialize WebDriver: {e}", "error")
        return None, None

def navigate_with_retry(driver, wait, url, max_retries=3, delay=3, logger=None):
    for attempt in range(1, max_retries + 1):
        try:
            logger(f"Navigating to {url} (Attempt {attempt}/{max_retries})...")
            driver.get(url)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            return True
        except Exception as e:
            logger(f"Navigation error to {url}: {e}. Retrying in {delay}s...", "warning")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                logger(f"Max retries reached for {url}.", "error")
                driver.save_screenshot(f"navigation_failure_{url.replace('https://', '').replace('/', '_')}.png")
                return False
    return False

def login(driver, wait, username, password, login_url, logger):
    if not navigate_with_retry(driver, wait, login_url, logger=logger):
        logger("Failed to load login page.", "error")
        return False
    try:
        if "login" not in driver.current_url.lower():
            logger("Already logged in or redirected successfully.")
            return True
        wait.until(EC.visibility_of_element_located((By.ID, "username"))).send_keys(username)
        wait.until(EC.visibility_of_element_located((By.ID, "password"))).send_keys(password)
        login_button = wait.until(EC.element_to_be_clickable((By.ID, "loginbtn")))
        driver.execute_script("arguments[0].click();", login_button)
        logger("Login button clicked.")
        wait.until(EC.url_changes(login_url))
        if "login" in driver.current_url.lower():
            logger("Login failed. Check credentials.", "error")
            driver.save_screenshot("login_failure.png")
            return False
        logger("Login successful.")
        return True
    except Exception as e:
        logger(f"Login error: {e}", "error")
        driver.save_screenshot("login_error.png")
        return False

def ask_gemini(question, options, api_key, logger):
    if not api_key:
        logger("Error: Gemini API Key is not set.", "error")
        return ""
    option_letters = ['a', 'b', 'c', 'd']
    formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options)])
    prompt = (
        f"You are a multiple choice answering bot.\n"
        f"Read the question and options carefully.\n"
        f"Respond with ONLY the letter of the correct option ({', '.join(option_letters[:len(options)])}).\n\n"
        f"Question: {question}\n\nOptions:\n{formatted_options}\n\nAnswer:"
    )
    logger(f"Sending prompt to Gemini API for question: {question[:50]}...")
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(f"{GEMINI_API_URL}?key={api_key}", json=payload, headers=headers)
        response.raise_for_status()
        generated_text = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
        match = re.match(r"^\s*([a-d])", generated_text)
        if match and match.group(1) in option_letters[:len(options)]:
            return match.group(1)
        logger("No clear letter found, attempting fuzzy match...")
        best_score, best_letter = 0, ""
        for idx, opt in enumerate(options):
            score = fuzz.token_set_ratio(generated_text, opt.lower())
            if score > best_score and score >= 70:
                best_score, best_letter = score, option_letters[idx]
        if best_letter:
            logger(f"Fuzzy match selected: '{best_letter}' (score: {best_score})")
            return best_letter
        logger("Fuzzy match failed. No answer selected.", "warning")
        return ""
    except Exception as e:
        logger(f"Gemini API error: {e}", "error")
        return ""

# --- Activity Functions ---
def speech_submission(driver, wait, activity_url, api_key, logger):
    engine = initialize_tts(logger)
    try:
        if not navigate_with_retry(driver, wait, activity_url, logger=logger):
            raise Exception("Failed to load activity page.")
        for attempt in range(3):
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                break
            except:
                if attempt < 2:
                    logger("Retrying page load...", "warning")
                    driver.refresh()
                else:
                    raise Exception("Failed to load page after retries.")
        start_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Start']")))
        driver.execute_script("arguments[0].click();", start_button)
        logger("Clicked 'Start' button.")
        wait.until(EC.any_of(
            EC.presence_of_element_located((By.CLASS_NAME, "mod_solo_speakingtopic_readonly")),
            EC.presence_of_element_located((By.CLASS_NAME, "poodll_mediarecorder_minimal_start_button"))
        ))
        logger("Navigated to recording page.")
        topic = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "mod_solo_speakingtopic_readonly"))).text.strip()
        logger(f"Extracted topic: {topic}")
        target_words = [elem.text.strip() for elem in wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "mod_solo_targetwordtag")))]
        logger(f"Extracted target words: {target_words}")
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash')
            prompt = (
                f"Generate a concise speech (100-120 words) about '{topic}' in the context of AI. "
                f"Incorporate these target words naturally: {', '.join(target_words)}. "
                f"Ensure suitability for text-to-speech at 200 wpm, lasting 30-40 seconds. "
                f"Use an informative and engaging tone."
            )
            response = model.generate_content(prompt)
            speech_text = response.text.strip()
            logger(f"Gemini API response: {speech_text}")
        except Exception as e:
            logger(f"Gemini API error: {e}", "error")
            speech_text = f"The {topic.lower()} is a key AI concept using {', '.join(target_words)} for decision-making."
        def switch_to_iframe(selector):
            for iframe in driver.find_elements(By.TAG_NAME, "iframe"):
                try:
                    driver.switch_to.frame(iframe)
                    wait.until(EC.presence_of_element_located(selector))
                    logger(f"Found element in iframe.")
                    return True
                except:
                    driver.switch_to.default_content()
            logger("No iframe with element found.")
            return False
        record_button_selector = (By.CLASS_NAME, "poodll_mediarecorder_minimal_start_button")
        if switch_to_iframe(record_button_selector):
            logger("Found record button in iframe.")
        else:
            driver.switch_to.default_content()
        record_button = wait.until(EC.element_to_be_clickable(record_button_selector))
        driver.execute_script("arguments[0].click();", record_button)
        logger("Clicked 'Record' button.")
        try:
            wait.until(EC.alert_is_present(), 3)
            Alert(driver).accept()
            logger("Accepted microphone alert.")
        except:
            logger("No microphone alert found.")
        logger("Speaking text...")
        start_time = time.time()
        engine.say(speech_text)
        engine.runAndWait()
        elapsed_time = time.time() - start_time
        logger(f"Finished speaking in {elapsed_time:.2f} seconds.")
        driver.switch_to.default_content()
        stop_button_selector = (By.CLASS_NAME, "poodll_mediarecorder_minimal_stop_button")
        if switch_to_iframe(stop_button_selector):
            logger("Found stop button in iframe.")
        else:
            driver.switch_to.default_content()
        stop_button = wait.until(EC.element_to_be_clickable(stop_button_selector))
        driver.execute_script("arguments[0].click();", stop_button)
        logger("Clicked 'Stop' button.")
        next_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Next']")))
        driver.execute_script("arguments[0].click();", next_button)
        logger("Clicked 'Next' button.")
        with open("transcript_page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        logger("Saved transcript page source to 'transcript_page_source.html'.")
        wait.until(EC.any_of(
            EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and @id[contains(., 'dontwaitfortranscript')]]")),
            EC.presence_of_element_located((By.XPATH, "//textarea[@id[contains(., 'selftranscript')]]"))
        ))
        logger("Transcript page loaded.")
        try:
            checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @id[contains(., 'dontwaitfortranscript')]]")))
            logger("Checkbox found by ID.")
        except:
            checkbox = wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'I do not want to wait for the transcript')]/preceding-sibling::input[@type='checkbox']")))
            logger("Checkbox found using text-based XPath.")
        driver.execute_script("arguments[0].click();", checkbox)
        logger("Clicked 'I do not want to wait for the transcript' checkbox.")
        try:
            textarea = wait.until(EC.presence_of_element_located((By.ID, "68615e96ccfef68615e968b78270_selftranscript")))
            logger("Textarea found by ID.")
        except:
            textarea = wait.until(EC.presence_of_element_located((By.XPATH, "//textarea[@id[contains(., 'selftranscript')]]")))
            logger("Textarea found using XPath.")
        driver.execute_script("arguments[0].value = arguments[1];", textarea, speech_text)
        logger("Pasted text into textarea.")
        submit_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Submit']")))
        driver.execute_script("arguments[0].click();", submit_button)
        logger("Clicked 'Submit' button.")
        try:
            wait.until(EC.presence_of_element_located((By.XPATH, "//button[@class='btn' and text()='Done']")))
            logger("Done button appeared.")
        except:
            wait.until(EC.presence_of_element_located((By.ID, "68597ef3ee4d968597ef27bf6f70_button")))
            logger("Done button found by ID.")
        try:
            done_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Done']")))
        except:
            done_button = wait.until(EC.element_to_be_clickable((By.ID, "68597ef3ee4d968597ef27bf6f70_button")))
        driver.execute_script("arguments[0].click();", done_button)
        logger("Clicked 'Done' button.")
        return True
    except Exception as e:
        logger(f"Speech Submission error: {e}", "error")
        driver.save_screenshot("speech_submission_error.png")
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False
    finally:
        if engine:
            engine.stop()

def read_aloud(driver, wait, activity_url, logger):
    engine = initialize_tts(logger)
    try:
        if not navigate_with_retry(driver, wait, activity_url, logger=logger):
            raise Exception("Failed to load read-aloud page.")
        for attempt in range(3):
            try:
                wait.until(EC.presence_of_element_located((By.ID, "mod_readaloud_button_startnoshadow")))
                break
            except:
                if attempt < 2:
                    logger("Retrying page load due to missing element...", "warning")
                    driver.refresh()
                else:
                    raise Exception("Failed to load page after retries.")
        read_button = wait.until(EC.element_to_be_clickable((By.ID, "mod_readaloud_button_startnoshadow")))
        driver.execute_script("arguments[0].scrollIntoView(true);", read_button)
        try:
            read_button.click()
            logger("Clicked 'Read' button with Selenium.")
        except:
            driver.execute_script("arguments[0].click();", read_button)
            logger("Clicked 'Read' button with JavaScript.")
        def switch_to_iframe(selector):
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            if not iframes:
                logger("No iframes found.")
                return False
            for i, iframe in enumerate(iframes):
                try:
                    driver.switch_to.frame(iframe)
                    wait.until(EC.presence_of_element_located(selector))
                    logger(f"Switched to iframe {i}.")
                    return True
                except:
                    logger(f"Record button not found in iframe {i}, switching back.")
                    driver.switch_to.default_content()
            return False
        record_button_selector = (By.CSS_SELECTOR, "button.poodll_start-recording_readaloud[aria-label='Record']")
        record_success = False
        for attempt in range(3):
            try:
                if switch_to_iframe(record_button_selector):
                    logger("Found record button in iframe.")
                else:
                    driver.switch_to.default_content()
                    logger("Searching for record button in main content.")
                record_button = wait.until(EC.element_to_be_clickable(record_button_selector))
                driver.execute_script("arguments[0].scrollIntoView(true);", record_button)
                try:
                    record_button.click()
                    logger("Clicked 'Record' button with Selenium.")
                except:
                    driver.execute_script("arguments[0].click();", record_button)
                    logger("Clicked 'Record' button with JavaScript.")
                time.sleep(1)  # Wait for PoodLL initialization
                record_success = True
                break
            except Exception as e:
                logger(f"Record attempt {attempt + 1} failed: {e}", "warning")
                driver.switch_to.default_content()
                time.sleep(2)
        if not record_success:
            raise Exception("Failed to click 'Record' button after retries.")
        try:
            wait.until(EC.alert_is_present(), 3)
            Alert(driver).accept()
            logger("Accepted JavaScript microphone alert.")
        except:
            logger("No JavaScript alert found, continuing...")
        driver.switch_to.default_content()
        passage_elements = driver.find_elements(By.CLASS_NAME, "mod_readaloud_grading_passageword")
        passage_text = " ".join([elem.text for elem in passage_elements])
        logger(f"Extracted passage: {passage_text}")
        logger("Speaking text...")
        start_time = time.time()
        engine.say(passage_text)
        engine.runAndWait()
        elapsed_time = time.time() - start_time
        logger(f"Finished speaking in {elapsed_time:.2f} seconds.")
        stop_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.poodll_stop-recording_readaloud[aria-label='Stop']")))
        driver.execute_script("arguments[0].removeAttribute('disabled'); arguments[0].scrollIntoView(true);", stop_button)
        try:
            stop_button.click()
            logger("Clicked 'Stop' button with Selenium.")
        except:
            driver.execute_script("arguments[0].click();", stop_button)
            logger("Clicked 'Stop' button with JavaScript.")
        return True
    except Exception as e:
        logger(f"Read-Aloud error: {e}", "error")
        driver.save_screenshot("read_aloud_error.png")
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return False
    finally:
        if engine:
            engine.stop()

def quiz_automation(driver, wait, quiz_data, api_key, logger, stop_event):
    results = {}
    for quiz in quiz_data:
        if stop_event.is_set():
            logger("Automation stopped by user.", "warning")
            break
        quiz_url, target_score = quiz["url"], quiz["target_score"]
        logger(f"\n--- Processing quiz: {quiz_url} (Target Score: {target_score if target_score else 'N/A'}) ---", "info")
        score, attempts = process_quiz(driver, wait, quiz_url, target_score, api_key, logger, stop_event)
        results[quiz_url] = {"score": score, "attempts": attempts}
        logger(f"Completed quiz: {quiz_url}. Score: {score}, Attempts: {attempts}")
        time.sleep(2)
    return results

def process_quiz(driver, wait, quiz_url, target_score, api_key, logger, stop_event):
    attempts_made = 0
    final_score = 0.0
    max_attempts = 5
    while attempts_made < max_attempts:
        if stop_event.is_set():
            logger("Automation stopped during quiz.", "warning")
            break
        attempts_made += 1
        logger(f"--- Attempt {attempts_made}/{max_attempts} for quiz: {quiz_url} ---")
        try:
            if not navigate_with_retry(driver, wait, quiz_url, logger=logger):
                logger("Failed to load quiz page after retries.", "error")
                break
            try:
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                logger("Quiz already in progress, proceeding to questions.")
            except:
                quiz_button_xpath = (
                    "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | "
                    "//input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]"
                )
                try:
                    quiz_button = wait.until(EC.element_to_be_clickable((By.XPATH, quiz_button_xpath)))
                    driver.execute_script("arguments[0].click();", quiz_button)
                    logger("Clicked quiz start/continue button.")
                    try:
                        start_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt')] | //input[contains(@value,'Start attempt')]")))
                        driver.execute_script("arguments[0].click();", start_button)
                        logger("Clicked 'Start attempt' button.")
                    except:
                        logger("No 'Start attempt' button found, checking for question text.", "warning")
                    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                    logger("Quiz started successfully.")
                except:
                    logger("Quiz start/continue button not found.", "error")
                    driver.save_screenshot(f"quiz_start_attempt_{attempts_made}.png")
                    break
            question_count = 0
            while True:
                if stop_event.is_set():
                    logger("Stopped during question processing.", "warning")
                    break
                try:
                    question_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "qtext")))
                    answer_block = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
                    question_count += 1
                    logger(f"Processing Question {question_count}...")
                    soup = BeautifulSoup(answer_block.get_attribute('outerHTML'), 'html.parser')
                    option_texts = []
                    radio_elements = []
                    for inp in soup.find_all('input', {'type': 'radio'}):
                        option_id = inp.get('id')
                        if option_id:
                            label_text = ""
                            label_id = inp.get('aria-labelledby')
                            if label_id and (label_div := soup.find(id=label_id)):
                                label_text = label_div.get_text(strip=True)
                            elif soup.find('label', {'for': option_id}):
                                label_text = soup.find('label', {'for': option_id}).get_text(strip=True)
                            elif inp.find_next_sibling('label'):
                                label_text = inp.find_next_sibling('label').get_text(strip=True)
                            if label_text:
                                option_texts.append(label_text)
                                try:
                                    radio_elements.append(driver.find_element(By.ID, option_id))
                                except NoSuchElementException as e:
                                    logger(f"Could not find radio element for ID '{option_id}': {e}", "warning")
                                    option_texts.pop()
                    if not option_texts or len(option_texts) != len(radio_elements):
                        logger(f"Failed to parse options correctly for Q{question_count}.", "warning")
                        driver.save_screenshot(f"question_{question_count}_parsing_error.png")
                        break
                    question_text = question_element.text.strip()
                    answer_letter = ask_gemini(question_text, option_texts, api_key, logger)
                    logger(f"Gemini chose: '{answer_letter}' for Q{question_count}.")
                    if answer_letter and answer_letter in 'abcd'[:len(option_texts)]:
                        try:
                            answer_index = ord(answer_letter) - ord('a')
                            target_element = radio_elements[answer_index]
                            wait.until(EC.element_to_be_clickable(target_element))
                            driver.execute_script("arguments[0].click();", target_element)
                            logger(f"Clicked option {answer_letter} for Q{question_count}.")
                        except Exception as e:
                            logger(f"Error clicking option {answer_letter} for Q{question_count}: {e}", "error")
                            driver.save_screenshot(f"question_{question_count}_click_error.png")
                    else:
                        logger(f"No valid answer selected for Q{question_count}.", "warning")
                    try:
                        next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]")))
                        driver.execute_script("arguments[0].click();", next_btn)
                        logger("Clicked 'Next page'.")
                        wait.until(EC.any_of(
                            EC.presence_of_element_located((By.CLASS_NAME, "qtext")),
                            EC.presence_of_element_located((By.XPATH, "//input[@value='Finish attempt ...']"))
                        ))
                    except TimeoutException:
                        logger("No 'Next page' button found. Assuming last question.", "info")
                        break
                    except Exception as e:
                        logger(f"Error navigating to next page for Q{question_count}: {e}", "error")
                        driver.save_screenshot(f"question_{question_count}_navigation_error.png")
                        break
                except TimeoutException:
                    logger("No more questions found.", "info")
                    break
                except Exception as e:
                    logger(f"Error processing question {question_count}: {e}", "error")
                    driver.save_screenshot(f"question_{question_count}_processing_error.png")
                    break
            if stop_event.is_set():
                break
            try:
                finish_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@value='Finish attempt ...' and @name='next' and @id='mod_quiz-next-nav']")))
                driver.execute_script("arguments[0].click();", finish_btn)
                logger("Clicked 'Finish attempt'.")
                submit_btn1 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='submit' and contains(text(), 'Submit all and finish')] | //input[@type='submit' and contains(@value, 'Submit all and finish')]")))
                driver.execute_script("arguments[0].click();", submit_btn1)
                logger("Clicked first 'Submit all and finish'.")
                submit_btn2 = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and @data-action='save' and contains(text(), 'Submit all and finish')] | //input[@type='submit' and contains(@value, 'Submit all and finish')]")))
                driver.execute_script("arguments[0].click();", submit_btn2)
                logger("Clicked second 'Submit all and finish'.")
                finish_review_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@class='mod_quiz-next-nav' and contains(text(), 'Finish review')]")))
                driver.execute_script("arguments[0].click();", finish_review_btn)
                logger("Clicked 'Finish review'.")
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, "quizattemptsummary")))
                time.sleep(1)  # Allow table to render
                last_row = wait.until(EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'quizattemptsummary')]/tbody/tr[last()]/td[contains(@class, 'c2')]")))
                score_text = last_row.text.strip()
                logger(f"Raw score text: '{score_text}'.")
                match = re.search(r'(\d+\.?\d*)', score_text)
                if match:
                    final_score = float(match.group(1))
                    logger(f"Parsed score: {final_score}")
                else:
                    logger(f"Could not parse score from '{score_text}'.", "warning")
                    final_score = 0.0
                if target_score is None or final_score >= target_score:
                    logger(f"Attempt {attempts_made} score: {final_score}. Target {target_score if target_score else 'N/A'} achieved.")
                    break
                logger(f"Attempt {attempts_made} score: {final_score}. Target {target_score} not met. Retrying...", "warning")
            except Exception as e:
                logger(f"Quiz submission error: {e}", "error")
                driver.save_screenshot(f"quiz_submission_attempt_{attempts_made}.png")
                with open(f"quiz_submission_page_source_attempt_{attempts_made}.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                break
        except Exception as e:
            logger(f"Quiz attempt {attempts_made} failed: {e}", "error")
            driver.save_screenshot(f"quiz_attempt_{attempts_made}_error.png")
            with open(f"quiz_page_source_attempt_{attempts_made}.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            break
    return final_score, attempts_made

# --- Streamlit App ---
st.set_page_config(page_title="LMS Automation", layout="wide")
st.title("LMS Automation Bot")
log_container = st.container()
log_queue = queue.Queue()

def logger(message, tag=None):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ", time.localtime())
    log_queue.put((timestamp + str(message) + "\n", tag))

def process_log_queue():
    while not log_queue.empty():
        message, tag = log_queue.get()
        with log_container:
            if tag == "error":
                st.error(message)
            elif tag == "warning":
                st.warning(message)
            else:
                st.write(message)
    st.experimental_rerun()

with st.sidebar:
    with st.form("config_form"):
        activity_type = st.selectbox("Activity Type", ACTIVITY_TYPES)
        lms_site = st.selectbox("LMS Site", list(LOGIN_SITE_OPTIONS.keys()))
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        gemini_api_key = st.text_input("Gemini API Key", type="password")
        headless = st.checkbox("Run Headless", value=True)
        if activity_type == "Quiz Automation":
            st.subheader("Quiz URLs")
            quiz_url = st.text_input("Quiz URL")
            target_score = st.text_input("Target Score (Optional, e.g., 4.0)")
            if "quizzes" not in st.session_state:
                st.session_state.quizzes = []
            if st.form_submit_button("Add Quiz"):
                if quiz_url:
                    try:
                        score = float(target_score) if target_score and target_score != "e.g., 4.0" else None
                        st.session_state.quizzes.append({"url": quiz_url, "target_score": score})
                        st.success(f"Added quiz: {quiz_url}")
                    except ValueError:
                        st.error("Target score must be a number (e.g., 4.0).")
            for i, quiz in enumerate(st.session_state.quizzes):
                st.write(f"Quiz {i+1}: {quiz['url']} | Target Score: {quiz['target_score'] if quiz['target_score'] else 'N/A'}")
        else:
            activity_url = st.text_input("Activity URL")
        submit_button = st.form_submit_button("Start Automation")

if submit_button:
    if not (username and password and gemini_api_key):
        st.error("Please fill in all required fields (username, password, Gemini API key).")
    elif activity_type == "Quiz Automation" and not st.session_state.quizzes:
        st.error("Please add at least one quiz URL.")
    elif activity_type != "Quiz Automation" and not activity_url:
        st.error("Please provide an activity URL.")
    else:
        stop_event = threading.Event()
        driver, wait = setup_selenium(headless, logger)
        if not driver:
            st.error("Failed to initialize WebDriver. Check logs.")
        else:
            try:
                if not login(driver, wait, username, password, LOGIN_SITE_OPTIONS[lms_site], logger):
                    st.error("Login failed. Check credentials or network.")
                else:
                    if activity_type == "Speech Submission":
                        success = speech_submission(driver, wait, activity_url, gemini_api_key, logger)
                        st.success("Speech Submission completed successfully." if success else "Speech Submission failed. Check logs.")
                    elif activity_type == "Read-Aloud":
                        success = read_aloud(driver, wait, activity_url, logger)
                        st.success("Read-Aloud completed successfully." if success else "Read-Aloud failed. Check logs.")
                    else:
                        results = quiz_automation(driver, wait, st.session_state.quizzes, gemini_api_key, logger, stop_event)
                        summary = "Quiz Results:\n\n"
                        for url, data in results.items():
                            status = "Achieved" if (data['score'] >= (data.get('target_score', 0) or 0)) else "Not Achieved"
                            if not data.get('target_score'):
                                status = "Completed"
                            summary += f"Quiz: {url}\nScore: {data['score']} | Attempts: {data['attempts']} | Status: {status}\n\n"
                        st.write(summary)
            except Exception as e:
                logger(f"Automation error: {e}", "error")
                st.error("Automation failed. Check logs for details.")
            finally:
                try:
                    driver.quit()
                    logger("Browser closed.")
                except:
                    logger("Browser already closed or error during cleanup.", "warning")
        process_log_queue()
