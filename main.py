import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from transformers import pipeline
from fuzzywuzzy import fuzz
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
import torch

# Load Zero-Shot Classification pipeline
classifier = pipeline("zero-shot-classification", model="syedkhalid076/DeBERTa-Zero-Shot-Classification")

def ask_mcq_zero_shot(question_text, options):
    try:
        result = classifier(question_text, candidate_labels=options)
        print("Scores:", list(zip(result['labels'], result['scores'])))  # Debug: show label and score
        top_option = result['labels'][0]
        if top_option in options:
            return options.index(top_option)
        else:
            return -1
    except Exception as e:
        print(f"Model Error: {e}")
        return -1

def auto_quiz_lms():
    # Get input from user
    username = input("Enter your LMS username: ")
    password = input("Enter your LMS password: ")
    quiz_url = input("Enter the quiz URL: ")
    num_pages_to_process = int(input("Enter number of quiz pages to process: "))

    login_url = "https://lms2.cse.saveetha.in/login/index.php"

    # Setup headless Chrome
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    wait = WebDriverWait(driver, 30)

    # Login process
    driver.get(login_url)
    wait.until(EC.presence_of_element_located((By.ID, 'username'))).send_keys(username)
    wait.until(EC.presence_of_element_located((By.ID, 'password'))).send_keys(password)
    wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn'))).click()
    time.sleep(5)

    # Open quiz
    driver.get(quiz_url)
    time.sleep(3)

    # Start or continue quiz
    try:
        quiz_button_xpath = "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | //input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]"
        quiz_button = wait.until(EC.element_to_be_clickable((By.XPATH, quiz_button_xpath)))
        quiz_button.click()
        time.sleep(3)
        try:
            start_attempt_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt')] | //input[contains(@value,'Start attempt')]"))
            )
            start_attempt_button.click()
            time.sleep(3)
        except:
            pass
    except Exception as e:
        print("Quiz already in progress or error:", e)

    # Main answer loop
    for i in range(num_pages_to_process):
        print(f"\n--- Page {i+1}/{num_pages_to_process} ---")
        try:
            question_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "qtext")))
            question_text = question_element.text.strip()

            answer_block_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
            answer_html = answer_block_element.get_attribute('outerHTML')
            soup = BeautifulSoup(answer_html, 'html.parser')

            option_texts = []
            radio_elements = []

            all_inputs = soup.find_all('input', {'type': 'radio'})
            for inp in all_inputs:
                option_id = inp.get('id')
                if not option_id:
                    continue
                label_text = ""
                label_id = inp.get('aria-labelledby')
                if label_id:
                    label_div = soup.find(id=label_id)
                    if label_div:
                        label_text = label_div.get_text(strip=True)
                elif soup.find('label', {'for': option_id}):
                    label_text = soup.find('label', {'for': option_id}).get_text(strip=True)
                elif inp.find_next_sibling('label'):
                    label_text = inp.find_next_sibling('label').get_text(strip=True)
                if label_text:
                    option_texts.append(label_text)
                    try:
                        radio_element = driver.find_element(By.ID, option_id)
                        radio_elements.append(radio_element)
                    except:
                        print(f"Radio input ID {option_id} not found.")

            if len(option_texts) >= 2:
                answer_index = ask_mcq_zero_shot(question_text, option_texts)
                if 0 <= answer_index < len(radio_elements):
                    radio_elements[answer_index].click()
                    print(f"Answered: {chr(65 + answer_index)} - {option_texts[answer_index][:50]}...")
                else:
                    print("Model failed to answer confidently.")
            else:
                print("Not enough options found.")

            next_button = wait.until(EC.element_to_be_clickable((By.NAME, "next")))
            next_button.click()
            time.sleep(2)

        except Exception as e:
            print(f"Error on page {i+1}: {e}")
            break

    print("\nQuiz completed or interrupted.")
    driver.quit()

    # Clean up GPU memory
    torch.cuda.empty_cache()

# Run the quiz bot
auto_quiz_lms()
