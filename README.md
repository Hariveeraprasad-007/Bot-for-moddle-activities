# Bot-for-moddle-activities
## LINK FOR THE APP:
'''
https://vigilant-fiesta-97jqp9xpv9xxh7p4p-8501.app.github.dev/
'''
```bash
!pip install selenium webdriver_manager transformers fuzzywuzzy beautifulsoup4
```

```bash
# Download Google's signing key and add it to the list of trusted keys
!wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
# Note: apt-key is deprecated, newer systems might prefer using /etc/apt/keyrings/
# Newer method:
# !wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-archive.gpg
# !echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-archive.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list > /dev/null


# Add the Google Chrome repository to your sources list
!echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list

# Update the package list *again* to include packages from the new repository
!apt-get update

# Now install Google Chrome Stable
!apt-get install -y google-chrome-stable

# Install Xvfb (still a good idea for headless environments, though you found it's already installed)
!apt-get install -y xvfb
```

```bash
!pip install -U bitsandbytes
```


```bash
# Authenticate with Hugging Face
from huggingface_hub import login, notebook_login

try:
    # Attempt login interactively for notebooks
    notebook_login()
    print("Hugging Face authentication successful!")
except Exception as e:
    print(f"Hugging Face authentication failed: {e}")
    print("Please try logging in manually if needed.")
    # Fallback for non-notebook environments (less common in Colab/Jupyter)
    # login()
```



```python
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
import torch
from accelerate import Accelerator
from transformers import BitsAndBytesConfig
from huggingface_hub import login, notebook_login
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from fuzzywuzzy import fuzz

# --- Hugging Face Authentication ---
print("Attempting to authenticate with Hugging Face Hub...")
try:
    notebook_login()
    print("Hugging Face authentication successful!")
except Exception as e:
    print(f"Hugging Face authentication failed: {e}")
    print("Please set HF_TOKEN or authenticate manually.")
    exit()

print("-" * 30)

# --- Selenium Setup ---
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--log-level=3")

print("Initializing WebDriver (Chrome Headless)...")
try:
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("WebDriver initialized successfully.")
except Exception as e:
    print(f"Failed to initialize WebDriver: {e}")
    exit()

wait = WebDriverWait(driver, 60)

print("-" * 30)

# --- Model Loading with Quantization ---
model_id = "mistralai/Mistral-7B-Instruct-v0.2"
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
)

print(f"Loading model: {model_id} with 4-bit quantization...")
try:
    qa_pipeline = pipeline(
        "text-generation",
        model=model_id,
        model_kwargs={
            "quantization_config": bnb_config,
            "torch_dtype": torch.bfloat16,
            "low_cpu_mem_usage": True
        },
        device_map="auto",
    )
    print("Model loaded successfully.")
except Exception as e:
    print(f"Error loading model {model_id}: {e}")
    if driver:
        driver.quit()
    exit()

print("-" * 30)

# --- ask_gpt Function ---
def ask_gpt(question, options):
    option_letters = ['a', 'b', 'c', 'd']
    formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options[:len(option_letters)])])
    prompt = (
        "You are a multiple choice answering bot.\n"
        "Read the question and the options below carefully.\n"
        f"Your response should be ONLY the letter of the correct option ({', '.join(option_letters[:len(options)])}) and nothing else.\n\n"
        f"Question: {question}\n\nOptions:\n{formatted_options}\n\nAnswer:"
    )
    print(f"\nSending prompt to model:\n---\n{prompt}\n---")
    try:
        outputs = qa_pipeline(prompt, max_new_tokens=15, do_sample=False)
        generated_text = outputs[0]['generated_text']
        prompt_end_index = generated_text.rfind(prompt)
        response_text = generated_text[prompt_end_index + len(prompt):].strip().lower() if prompt_end_index != -1 else generated_text.strip().lower()
        print(f"Model Raw Response Part: '{response_text}'")
        potential_answer_match = re.match(r"^\s*([a-d])", response_text)
        if potential_answer_match:
            direct_letter = potential_answer_match.group(1)
            if direct_letter in option_letters[:len(options)]:
                print(f"Parsed Direct Letter Match: {direct_letter}")
                return direct_letter
        flexible_match = re.search(r"\b([a-d])\b", response_text)
        if flexible_match:
            found_letter = flexible_match.group(1)
            if found_letter in option_letters[:len(options)]:
                print(f"Parsed Flexible Letter Match: {found_letter}")
                return found_letter
        print("No clear letter found, attempting fuzzy match...")
        best_match_letter, best_score = "", 0
        for idx, opt in enumerate(options):
            score = fuzz.token_set_ratio(response_text, opt.lower())
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
        print(f"Error during model prediction: {e}")
        return ""

print("-" * 30)

# --- Login and Navigation ---
login_url = "https://lms2.cse.saveetha.in/login/index.php"
quiz_url = "https://lms2.cse.saveetha.in/mod/quiz/view.php?id=500"

try:
    print(f"Navigating to login page: {login_url}")
    driver.get(login_url)
    username_field = wait.until(EC.visibility_of_element_located((By.ID, 'username')))
    password_field = wait.until(EC.visibility_of_element_located((By.ID, 'password')))
    login_button = wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn')))
    username_field.send_keys("23009466")
    password_field.send_keys("1554")
    login_button.click()
    print("Login attempted.")
    print("Login successful, redirected to dashboard.")
    time.sleep(2)
    print(f"Navigating to quiz page: {quiz_url}")
    driver.get(quiz_url)
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "page-header-headings")))
    print("Arrived at quiz page.")
except Exception as e:
    print(f"Login or quiz page navigation failed: {e}")
    driver.quit()
    exit()

# --- Handle Quiz Start/Continue (Fixed Section) ---
try:
    print("Looking for quiz attempt buttons...")
    quiz_button_xpath = "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | //input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]"
    quiz_button = wait.until(EC.element_to_be_clickable((By.XPATH, quiz_button_xpath)))
    print(f"Found button: '{quiz_button.text or quiz_button.get_attribute('value')}'")
    quiz_button.click()
    print("Clicked quiz start/continue button.")
    time.sleep(3)
    try:
        start_attempt_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt')] | //input[contains(@value,'Start attempt')]"))
        )
        print("Found and clicking 'Start attempt' confirmation button.")
        start_attempt_button.click()
        time.sleep(3)
    except:
        print("No 'Start attempt' confirmation button found or needed.")
except Exception as e:
    print(f"Could not find quiz start/continue button: {e}")
    try:
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
        print("Quiz already in progress, continuing.")
    except:
        print("Not in quiz and cannot find start button. Exiting.")
        driver.quit()
        exit()

print("-" * 30)

# --- Process Quiz Questions ---
num_pages_to_process = 20
for i in range(num_pages_to_process):
    print(f"\n--- Processing Question Page {i+1}/{num_pages_to_process} ---")
    try:
        question_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "qtext")))
        question_text = question_element.text.strip()
        print(f"Question Text: {question_text[:200]}...")
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
                        print(f"Could not find Selenium element for ID '{option_id}': {sel_e}")
                        option_texts.pop()
                        continue
        print(f"Parsed Options ({len(option_texts)}): {option_texts}")
        if option_texts and len(option_texts) == len(radio_elements):
            model_answer_letter = ask_gpt(question_text, option_texts)
            print(f"Model's Chosen Letter: '{model_answer_letter}'")
            clicked = False
            if model_answer_letter and model_answer_letter in 'abcd'[:len(option_texts)]:
                try:
                    answer_index = ord(model_answer_letter) - ord('a')
                    if 0 <= answer_index < len(radio_elements):
                        target_element = radio_elements[answer_index]
                        wait.until(EC.element_to_be_clickable(target_element))
                        driver.execute_script("arguments[0].click();", target_element)
                        print(f"Clicked option {model_answer_letter}: {option_texts[answer_index]}")
                        clicked = True
                    else:
                        print(f"Letter '{model_answer_letter}' out of bounds for options ({len(option_texts)}).")
                except Exception as click_e:
                    print(f"Error clicking option {model_answer_letter}: {click_e}")
            if not clicked:
                print(f"Could not click an option for question {i+1}.")
        else:
            print("Warning: Failed to parse options or link to Selenium elements.")
        print("-" * 20)
        if i == num_pages_to_process - 1:
            print("Attempting to finish quiz...")
            finish_xpath = "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt')]"
            finish_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, finish_xpath)))
            driver.execute_script("arguments[0].click();", finish_btn)
            print("Clicked 'Finish attempt'.")
            try:
                print("Looking for 'Submit all and finish' confirmation...")
                submit_all_xpath = "//button[contains(text(),'Submit all and finish')] | //input[contains(@value,'Submit all and finish')]"
                submit_all_btn1 = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, submit_all_xpath)))
                driver.execute_script("arguments[0].click();", submit_all_btn1)
                print("Clicked first 'Submit all and finish'.")
                try:
                    submit_all_btn2 = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, submit_all_xpath)))
                    driver.execute_script("arguments[0].click();", submit_all_btn2)
                    print("Clicked second 'Submit all and finish'.")
                except:
                    print("No second 'Submit all and finish' confirmation needed.")
            except Exception as submit_e:
                print(f"Could not submit quiz: {submit_e}")
        else:
            print("Moving to next page...")
            next_xpath = "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"
            next_btn = WebDriverWait(driver, 20).until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
            driver.execute_script("arguments[0].click();", next_btn)
            print("Clicked 'Next page'.")
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
            time.sleep(1)
    except Exception as e:
        print(f"Error processing Question Page {i+1}: {e}")
        try:
            if i == num_pages_to_process - 1:
                print("Attempting to finish quiz after error...")
                finish_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, finish_xpath)))
                driver.execute_script("arguments[0].click();", finish_btn)
            else:
                print("Attempting next page after error...")
                next_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(3)
        except Exception as nav_e:
            print(f"Navigation error after previous error: {nav_e}")

print("\n" + "=" * 50)
print("Quiz processing completed.")
if driver:
    driver.quit()
print("WebDriver closed.")
print("=" * 50)
```
