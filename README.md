# Bot-for-moddle-activities

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








```python
import os
import time
# requests is imported but not used in the provided script
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re
from transformers import pipeline

# Import necessary modules for Chrome and webdriver_manager
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

# Initialize Hugging Face text-generation pipeline
from fuzzywuzzy import fuzz

# Load model
# NOTE: flan-t5-xl is a large model and requires significant RAM/VRAM.
# It might be slow or cause memory issues on standard free Colab instances.
# Consider a smaller model like 'google/flan-t5-large' or 'google/flan-t5-base'
# if you encounter resource problems.
qa_pipeline = pipeline("text2text-generation", model="google/flan-t5-large")

def ask_gpt(question, options):
    """
    Uses the text-generation pipeline to answer a multiple-choice question.
    Includes direct letter matching and fuzzy matching fallback.
    """
    # Create lettered options (a-d)
    option_letters = ['a', 'b', 'c', 'd']
    # Ensure we don't try to format more options than available
    formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options[:len(option_letters)])])

    # Prompt with clearer instruction
    # Only include letters for available options
    valid_letters_prompt = ", ".join(option_letters[:len(options)])
    prompt = (
        "You are a helpful assistant. Please choose the most accurate answer from the following options.\n"
        f"Q: {question}\nOptions:\n{formatted_options}\n"
        "Answer: (Please choose a letter from a, b, c, or d, based on the most likely option)"
    )

    print(f"\nSending prompt to model:\n---\n{prompt}\n---")

    try:
        # Adjust max_new_tokens if needed, but 5 should be enough for a letter
        result = qa_pipeline(prompt, max_new_tokens=5, num_return_sequences=1)[0]['generated_text'].strip().lower()
        print(f"Model Raw Response: '{result}'")

        # Direct match if letter is clearly in result and is a valid option letter
        for i, letter in enumerate(option_letters[:len(options)]):
             if result.startswith(letter) or result == letter:
                 print(f"Direct letter match: {letter}")
                 return letter # Return the matched valid letter

        # If no direct letter match, try fuzzy match fallback: compare model answer to options
        print("No direct letter match, attempting fuzzy match...")
        best_match_letter = ""
        best_score = 0
        # Ensure we only compare to the available options
        for idx, opt in enumerate(options):
            score = fuzz.partial_ratio(result, opt.lower())
            print(f"  Fuzzy score for option '{option_letters[idx]}. {opt[:50]}...': {score}")
            if score > best_score:
                best_score = score
                best_match_letter = option_letters[idx]

        # Set a threshold for fuzzy match confidence
        fuzzy_threshold = 70 # You might need to adjust this threshold (e.g., 60-80)

        if best_score >= fuzzy_threshold:
            print(f"Fuzzy fallback selected: '{best_match_letter}' (score: {best_score})")
            return best_match_letter
        else:
            print(f"Fuzzy match score {best_score} below threshold {fuzzy_threshold}. Cannot determine answer.")
            return "" # Return empty string if no confident answer found

    except Exception as e:
        print(f"Error during GPT prediction or fuzzy matching: {e}")
        return "" # Return empty string on error


# --- Selenium Code ---

# Setup Chrome options for headless mode
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless") # Run in headless mode
chrome_options.add_argument("--no-sandbox") # Bypass OS security model, crucial in some environments
chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
# If using Xvfb (optional setup step)
# chrome_options.add_argument("--display=:99")

# Initialize WebDriver using webdriver_manager
print("Initializing WebDriver (Chrome Headless)...")
try:
    # Use ChromeDriverManager to get the correct chromedriver executable
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    print("WebDriver initialized successfully.")
except Exception as e:
    print(f"Failed to initialize WebDriver: {e}")
    print("Please ensure Chrome browser and compatible chromedriver are installed/available.")
    # Exit gracefully if WebDriver fails to initialize
    exit()


wait = WebDriverWait(driver, 30) # Increased wait time

# Login
login_url = "https://lms2.cse.saveetha.in/login/index.php" # Standard Moodle login page
quiz_url = "https://lms2.cse.saveetha.in/mod/quiz/view.php?id=500" # Your target quiz

try:
    print(f"Navigating to login page: {login_url}")
    driver.get(login_url)

    # Assuming standard Moodle login fields
    username_field = wait.until(EC.presence_of_element_located((By.ID, 'username')))
    password_field = wait.until(EC.presence_of_element_located((By.ID, 'password')))
    login_button = wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn')))

    username_field.send_keys("23009466")
    password_field.send_keys("g26736")
    login_button.click()
    print("Login attempted.")
    time.sleep(5) # Give time for login redirection

    # Verify successful login by navigating to the quiz page directly
    # Moodle usually redirects correctly after login, but direct navigation is safer
    print(f"Navigating to quiz page after login: {quiz_url}")
    driver.get(quiz_url)
    time.sleep(3) # Give time for the quiz page to load

except Exception as e:
    print(f"Login or initial quiz page navigation failed: {e}")
    driver.quit()
    exit() # Exit if login/initial page load fails

# Handle start/restart/continue
try:
    print("Looking for quiz attempt buttons...")
    # Use a more robust XPath that checks button or input text
    quiz_button_xpath = "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | //input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]"
    quiz_button = wait.until(EC.element_to_be_clickable((By.XPATH, quiz_button_xpath)))
    print(f"Found button: '{quiz_button.text or quiz_button.get_attribute('value')}'")
    quiz_button.click()
    print("Clicked quiz start/continue button.")
    time.sleep(5) # Give time for the quiz page to load

    # Check if there's an initial confirmation (e.g., "Start attempt")
    try:
        start_attempt_button = WebDriverWait(driver, 10).until(
             EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt')] | //input[contains(@value,'Start attempt')]"))
        )
        print("Found and clicking 'Start attempt' confirmation button.")
        start_attempt_button.click()
        time.sleep(3)
    except:
        print("No 'Start attempt' confirmation button found or needed.")
        pass # No confirmation needed

except Exception as e:
    print(f"Could not find quiz start/continue or initial confirmation button: {e}")
    # Check if we are already inside the quiz
    try:
        # Look for elements typically present inside a quiz attempt
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
        print("Appears to be already in quiz attempt, continuing.")
    except:
        print("Not in quiz and cannot find start button. Exiting.")
        driver.quit()
        exit()


# Process questions page by page
# Assuming 20 pages based on your original loop range
num_pages_to_process = 20 # Adjust this based on the actual number of question pages

for i in range(num_pages_to_process):
    print(f"\n--- Processing Question Page {i+1}/{num_pages_to_process} ---")
    try:
        # Wait for the question text to be visible
        question_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "qtext")))
        question_text = question_element.text.strip()
        print(f"Question Text: {question_text[:150]}...") # Print a snippet

        # Wait for the answer block
        answer_block_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
        answer_html = answer_block_element.get_attribute('outerHTML')
        soup = BeautifulSoup(answer_html, 'html.parser')

        option_texts = []
        radio_elements = [] # Selenium elements corresponding to the options

        # Find all radio button inputs
        all_inputs = soup.find_all('input', {'type': 'radio'})

        for inp in all_inputs:
            option_id = inp.get('id')
            if option_id:
                label_text = ""
                # Try different ways to find the associated label text
                label_id = inp.get('aria-labelledby')
                if label_id:
                    label_div = soup.find(id=label_id)
                    if label_div:
                        label_text = label_div.get_text(strip=True)
                elif soup.find('label', {'for': option_id}):
                     label_text = soup.find('label', {'for': option_id}).get_text(strip=True)
                # Fallback: check the immediate following sibling label
                elif inp.find_next_sibling('label'):
                    label_text = inp.find_next_sibling('label').get_text(strip=True)

                if label_text:
                    option_texts.append(label_text)
                    # Find the actual Selenium element by ID
                    try:
                        selenium_radio = driver.find_element(By.ID, option_id)
                        radio_elements.append(selenium_radio)
                    except Exception as sel_e:
                         print(f"Could not find Selenium element for input ID '{option_id}': {sel_e}")
                         # If we fail to find the element, remove the option text we just added
                         if option_texts:
                              option_texts.pop()
                         continue # Skip this option if Selenium element not found

        print(f"Parsed Options ({len(option_texts)}): {option_texts}")

        # Check if parsing was successful
        if not option_texts or len(option_texts) != len(radio_elements):
            print("Warning: Failed to parse options or link them to Selenium elements for this question.")
            # Decide how to handle this: skip question, try to navigate anyway?
            # For now, we'll print a warning and attempt to navigate to the next page
            # (or finish if it's the last page). The question will likely be unanswered.

        else: # Only ask model and click if options were successfully parsed
            model_answer_letter = ask_gpt(question_text, option_texts)
            print(f"Model's Chosen Letter: '{model_answer_letter}'")

            clicked = False
            if model_answer_letter:
                try:
                    # Convert letter (a, b, c, d) to index (0, 1, 2, 3)
                    answer_index = ord(model_answer_letter) - ord('a')
                    if 0 <= answer_index < len(radio_elements):
                        # Ensure element is visible and clickable before clicking
                        wait.until(EC.visibility_of(radio_elements[answer_index]))
                        wait.until(EC.element_to_be_clickable(radio_elements[answer_index]))
                        # Use JavaScript click as it's sometimes more reliable for radio buttons
                        driver.execute_script("arguments[0].click();", radio_elements[answer_index])
                        print(f"Successfully clicked option {model_answer_letter}: {option_texts[answer_index]}")
                        clicked = True
                    else:
                        print(f"Model returned letter '{model_answer_letter}' which is out of bounds for available options ({len(option_texts)}).")
                except Exception as click_e:
                    print(f"Error clicking radio button for option {model_answer_letter}: {click_e}")
            else:
                print("Model did not provide a confident answer letter.")

            if not clicked:
                print("Could not click an option for this question.")


        # Navigate to the next page or finish
        if i == num_pages_to_process - 1:
            print("Attempting to finish quiz...")
            finish_xpath = "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt')]"
            finish_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, finish_xpath)))
            finish_btn.click()
            print("Clicked 'Finish attempt'.")

            # Look for 'Submit all and finish' confirmation(s)
            try:
                print("Looking for 'Submit all and finish' confirmation...")
                submit_all_xpath = "//button[contains(text(),'Submit all and finish')] | //input[contains(@value,'Submit all and finish')]"
                # There might be two confirmation steps
                submit_all_btn1 = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, submit_all_xpath)))
                submit_all_btn1.click()
                print("Clicked first 'Submit all and finish'.")
                # Wait briefly in case there's a second confirmation
                time.sleep(2)
                try:
                     submit_all_btn2 = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, submit_all_xpath)))
                     submit_all_btn2.click()
                     print("Clicked second 'Submit all and finish'.")
                except:
                     print("No second 'Submit all and finish' confirmation found or needed.")

            except Exception as submit_e:
                print(f"Could not find or click 'Submit all and finish' confirmation button(s): {submit_e}")

        else:
            print("Moving to next page...")
            next_xpath = "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"
            next_btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
            next_btn.click()
            print("Clicked 'Next page'.")
            time.sleep(3) # Give time for the next page to load

    except Exception as e:
        print(f"An unexpected error occurred during processing Question Page {i+1}: {e}")
        # If any error occurs during page processing, try to move to the next page
        # or finish attempt to avoid getting stuck, then continue the loop.
        try:
             if i == num_pages_to_process - 1:
                print("Attempting to finish quiz after error...")
                finish_xpath = "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt')]"
                finish_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, finish_xpath)))
                finish_btn.click()
             else:
                 print("Attempting to go to next page after error...")
                 next_xpath = "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"
                 next_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
                 next_btn.click()
                 time.sleep(3)
        except Exception as nav_e:
             print(f"Error navigating after previous error: {nav_e}")


print("\nQuiz processing completed (or stopped due to errors).")
# It's good practice to quit the driver when done
driver.quit()
print("WebDriver closed.")
```
