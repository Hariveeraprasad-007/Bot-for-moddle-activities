import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
API_KEY = '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'

import re

def ask_gpt(question, options):
    context = "\n".join([f"{chr(97+i)}. {opt}" for i, opt in enumerate(options)])
    prompt = f"""You are a helpful assistant answering multiple-choice questions.

Q: {question}
Options:
{context}

Choose the correct option (a, b, c, or d) and explain your reasoning."""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://yourdomain.com",  # Optional
        "Content-Type": "application/json"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",  # Or use mistralai/mixtral-8x7b or anthropic/claude-2
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=30)
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]
        
        # Use a regular expression to extract the option letter (a, b, c, or d) from the response
        match = re.search(r'\b([abcd])\b', content.strip().lower())  # Looks for a single letter a, b, c, or d
        if match:
            answer = match.group(1)
            print("Model Response:", content)
            return answer
        else:
            print("Could not extract answer from response:", content)
            return ""
    except Exception as e:
        print("API error:", e)
        return ""

# Initialize WebDriver
driver = webdriver.Firefox()
wait = WebDriverWait(driver, 20)

# Login
driver.get("https://lms2.ai.saveetha.in/mod/quiz/view.php?id=1394")
wait.until(EC.presence_of_element_located((By.NAME, 'username'))).send_keys("23009466")
driver.find_element(By.NAME, 'password').send_keys("g26736")
driver.find_element(By.ID, 'loginbtn').click()
time.sleep(2)

# Handle start/restart/continue
quiz_button = wait.until(
    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')]"))
)
quiz_button.click()
time.sleep(2)
try:
    driver.find_element(By.ID, 'id_submitbutton').click()
except:
    pass

# Loop over questions
# Loop over questions
# Loop over questions
for i in range(10):
    try:
        time.sleep(2)
        question_text = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext"))).text

        answer_html = driver.find_element(By.CLASS_NAME, "answer").get_attribute('outerHTML')
        soup = BeautifulSoup(answer_html, 'html.parser')

        option_texts = []
        radio_elements = []

        all_inputs = soup.find_all('input', {'type': 'radio'})
        for inp in all_inputs:
            label_id = inp.get('aria-labelledby') or inp.get('aria-label') or ''
            label_div = soup.find(id=label_id)
            if label_div:
                option_texts.append(label_div.get_text(strip=True))
                try:
                    selenium_radio = driver.find_element(By.ID, inp.get('id'))
                    radio_elements.append(selenium_radio)
                except:
                    continue
        # Send question + options to GPT
        model_answer = ask_gpt(question_text, option_texts)

        # Match based on label
        clicked = False
        for j, text in enumerate(option_texts):
            if model_answer == chr(97+j):  # Compare with 'a', 'b', etc.
                radio_elements[j].click()
                print("Clicked:", text)
                clicked = True
                break
        if not clicked:
            print("Could not match model answer to any option.")

        if i == 9:
            finish = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt')]"))
            )
            finish.click()
        else:
            next_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"))
            )
            next_btn.click()

    except Exception as e:
        print(f"Error on Q{i+1}: {e}")
        break



driver.quit()
