import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
from transformers import pipeline

# Replace with your Hugging Face API token

# Initialize Hugging Face text-generation pipeline
pipe = pipeline("text2text-generation", model="google/flan-t5-large")# You can change to any model, e.g., "openai/gpt-3"

def ask_gpt(question, options):
    context = "\n".join([f"{chr(97+i)}. {opt}" for i, opt in enumerate(options)])
    prompt = f"""You are a helpful assistant answering multiple-choice questions.

Q: {question}
Options:
{context}

Choose the correct option (a, b, c, or d) and explain your reasoning. Start your answer with the letter of the correct option (a, b, c, or d)."""

    result = pipe(prompt, max_length=256, num_return_sequences=1)
    output_text = result[0]['generated_text']
    print("Model Response:", output_text)

    # Look for single-letter at start OR in "answer: a" etc.
    match = re.search(r'^([abcd])\b', output_text.strip().lower())
    if not match:
        match = re.search(r'answer\s*[:\-]?\s*([abcd])\b', output_text.strip().lower())

    if match:
        answer = match.group(1)
        print("Extracted Answer:", answer)
        return answer
    else:
        print("Could not extract answer letter from response:", output_text)
        return ""



# --- Rest of your Selenium code ---

# Initialize WebDriver
driver = webdriver.Firefox()
wait = WebDriverWait(driver, 20)

# Login
driver.get("https://lms2.cse.saveetha.in/mod/quiz/view.php?id=500")
try:
    wait.until(EC.presence_of_element_located((By.NAME, 'username'))).send_keys("23009466")
    driver.find_element(By.NAME, 'password').send_keys("g26736")
    driver.find_element(By.ID, 'loginbtn').click()
    time.sleep(3) # Give time for login redirection
except Exception as e:
    print(f"Login failed: {e}")
    driver.quit()
    exit() # Exit if login fails

# Handle start/restart/continue
try:
    quiz_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')]"))
    )
    quiz_button.click()
    time.sleep(3) # Give time for the quiz page to load
except Exception as e:
    print(f"Could not find quiz start/continue button: {e}")
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]")))
        print("Appears to be already in quiz, continuing.")
    except:
        print("Not in quiz and cannot find start button. Exiting.")
        driver.quit()
        exit()

try:
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'id_submitbutton'))).click()
    print("Clicked confirmation button.")
except:
    print("No initial confirmation button found or needed.")
    pass

for i in range(20): # Assuming 10 questions and one question per page
    print(f"\n--- Processing Question Page {i+1} ---")
    try:
        question_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "qtext")))
        question_text = question_element.text.strip()
        print(f"Question Text: {question_text[:100]}...")

        answer_block_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
        answer_html = answer_block_element.get_attribute('outerHTML')
        soup = BeautifulSoup(answer_html, 'html.parser')

        option_texts = []
        radio_elements = []

        all_inputs = soup.find_all('input', {'type': 'radio'})

        for inp in all_inputs:
            option_id = inp.get('id')
            if option_id:
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
                        selenium_radio = driver.find_element(By.ID, option_id)
                        radio_elements.append(selenium_radio)
                    except Exception as sel_e:
                        print(f"Could not find Selenium element for input ID {option_id}: {sel_e}")
                        if option_texts:
                            option_texts.pop()
                        continue

        print("Parsed Options:", option_texts)

        if not option_texts or not radio_elements or len(option_texts) != len(radio_elements):
            print("Failed to parse options or elements for this question.")
            try:
                if i == 19:
                    print("Attempting to finish quiz on error...")
                    finish = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt')]"))
                    )
                    finish.click()
                else:
                    print("Attempting to go to next page despite error...")
                    next_btn = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"))
                    )
                    next_btn.click()
            except Exception as nav_e:
                print(f"Error navigating after question processing error: {nav_e}")
            continue

        model_answer_letter = ask_gpt(question_text, option_texts)

        clicked = False
        if model_answer_letter:
            try:
                answer_index = ord(model_answer_letter) - ord('a')
                if 0 <= answer_index < len(radio_elements):
                    wait.until(EC.visibility_of(radio_elements[answer_index]))
                    wait.until(EC.element_to_be_clickable(radio_elements[answer_index]))
                    driver.execute_script("arguments[0].click();", radio_elements[answer_index])
                    print(f"Clicked option {model_answer_letter}: {option_texts[answer_index]}")
                    clicked = True
                else:
                    print(f"Model returned letter '{model_answer_letter}' which is out of bounds for available options ({len(option_texts)}).")
            except Exception as click_e:
                print(f"Error clicking radio button for option {model_answer_letter}: {click_e}")

        if not clicked:
            print("Could not match model answer to any option or click failed.")

        if i == 19:
            print("Attempting to finish quiz...")
            finish = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt')]"))
            )
            finish.click()
            try:
                print("Looking for 'Submit all and finish' confirmation...")
                submit_all_btn1 = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Submit all and finish')]"))
                )
                submit_all_btn1.click()

                submit_all_btn2 = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Submit all and finish')]"))
                )
                submit_all_btn2.click()
            except Exception as submit_e:
                print(f"Could not find or click 'Submit all and finish' confirmation button(s): {submit_e}")
        else:
            print("Moving to next page...")
            next_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"))
            )
            next_btn.click()

    except Exception as e:
        print(f"An unexpected error occurred during processing Question Page {i+1}: {e}")

print("\nQuiz processing completed (or stopped due to error).")
driver.quit()
