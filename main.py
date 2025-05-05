import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
# from dotenv import load_dotenv # No longer needed if key is hardcoded
import re

# load_dotenv() # No longer needed

# !! WARNING: Hardcoding API keys is insecure. Use environment variables (.env) instead. !!
# Replace 'sk-YOUR_HARDCODED_API_KEY_HERE' with your actual OpenRouter API key.
API_KEY = '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'

def ask_gpt(question, options):
    context = "\n".join([f"{chr(97+i)}. {opt}" for i, opt in enumerate(options)])
    prompt = f"""You are a helpful assistant answering multiple-choice questions.

Q: {question}
Options:
{context}

Choose the correct option (a, b, c, or d) and explain your reasoning. Just provide the letter first, then the explanation."""

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "HTTP-Referer": "https://yourdomain.com",  # Optional - replace with your domain
        "Content-Type": "application/json"
    }

    data = {
        # Changed the model to DeepSeek Chat on OpenRouter
        "model": "meta-llama/llama-4-maverick:free", # Or another DeepSeek model supported by OpenRouter like 'deepseek/coder' if applicable
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        res = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data, timeout=60) # Increased timeout
        res.raise_for_status()
        content = res.json()["choices"][0]["message"]["content"]

        # Use a regular expression to extract the option letter (a, b, c, or d) from the beginning of the response
        # Adjusted regex to look for the letter likely at the start
        match = re.search(r'^\s*([abcd])\b', content.strip().lower()) # Looks for the letter at the start of the stripped string
        if match:
            answer = match.group(1)
            print("Model Response:", content)
            print("Extracted Answer:", answer)
            return answer
        else:
            print("Could not extract answer letter from response:", content)
            return ""
    except Exception as e:
        print(f"API error: {e}")
        # Attempt to print response body if available for debugging HTTP errors
        if 'res' in locals():
             try:
                 print("Response body:", res.text)
             except:
                 pass
        return ""

# --- Rest of your Selenium code ---

# Initialize WebDriver
# Ensure you have geckodriver installed and in your PATH
driver = webdriver.Firefox()
wait = WebDriverWait(driver, 20)

# Login
driver.get("https://lms2.ai.saveetha.in/mod/quiz/view.php?id=1394")
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
    # Look for any of the common buttons to start/continue the quiz
    quiz_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')]"))
    )
    quiz_button.click()
    time.sleep(3) # Give time for the quiz page to load
except Exception as e:
    print(f"Could not find quiz start/continue button: {e}")
    # Check if already in quiz (e.g., "Next page" button exists)
    try:
        wait.until(EC.presence_of_element_located((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]")))
        print("Appears to be already in quiz, continuing.")
    except:
        print("Not in quiz and cannot find start button. Exiting.")
        driver.quit()
        exit()


try:
    # This click might be for a confirmation page after clicking "Start attempt"
    # Use a short wait as it might not always appear
    WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, 'id_submitbutton'))).click()
    print("Clicked confirmation button.")
except:
    print("No initial confirmation button found or needed.")
    pass # Quiz might start directly

# Loop over questions
# Moodle pages usually contain one question each or a few
# We'll loop assuming we navigate page by page for 10 questions.
# Adjust the range if the quiz structure is different (e.g., all questions on one page)
for i in range(10): # Assuming 10 questions and one question per page
    print(f"\n--- Processing Question Page {i+1} ---")
    try:
        # Wait for the question text to be visible on the new page
        question_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "qtext")))
        question_text = question_element.text.strip() # Strip whitespace
        print(f"Question Text: {question_text[:100]}...") # Print first 100 chars

        # Wait for the answer block to be present and visible
        answer_block_element = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
        answer_html = answer_block_element.get_attribute('outerHTML')
        soup = BeautifulSoup(answer_html, 'html.parser')

        option_texts = []
        radio_elements = [] # This will store Selenium WebElement objects

        # Find all radio inputs within the answer block using BeautifulSoup
        all_inputs = soup.find_all('input', {'type': 'radio'})

        # Iterate through parsed options and find the corresponding Selenium element
        for inp in all_inputs:
            option_id = inp.get('id')
            if option_id:
                # Find the label text associated with the input
                label_text = ""
                # Moodle often uses aria-labelledby linking to a div containing the text
                label_id = inp.get('aria-labelledby')
                if label_id:
                     label_div = soup.find(id=label_id)
                     if label_div:
                         label_text = label_div.get_text(strip=True)
                # Fallback: Check for a direct <label> tag associated by 'for' attribute
                elif soup.find('label', {'for': option_id}):
                     label_text = soup.find('label', {'for': option_id}).get_text(strip=True)
                # Fallback: Check next sibling (sometimes label is right after input)
                elif inp.find_next_sibling('label'):
                    label_text = inp.find_next_sibling('label').get_text(strip=True)


                if label_text:
                    option_texts.append(label_text)
                    try:
                        # Find the actual Selenium radio button element by its ID
                        selenium_radio = driver.find_element(By.ID, option_id)
                        radio_elements.append(selenium_radio)
                    except Exception as sel_e:
                        print(f"Could not find Selenium element for input ID {option_id}: {sel_e}")
                        # If the Selenium element isn't found, the lists will be misaligned.
                        # It's better to skip this option entirely if we can't interact with it.
                        # We need to remove the last added text to keep lists in sync.
                        if option_texts: # Check if list is not empty before popping
                            option_texts.pop()
                        continue # Skip to next input found by BeautifulSoup


        print("Parsed Options:", option_texts)

        if not option_texts or not radio_elements or len(option_texts) != len(radio_elements):
            print("Failed to parse options or elements for this question.")
            # Decide how to handle: skip, try next question, or break
            # For now, we'll print error and proceed to next page attempt
            # You might want to break depending on desired behavior
            try:
                 if i == 9: # Attempt to finish if this is the last question number
                     print("Attempting to finish quiz on error...")
                     finish = WebDriverWait(driver, 10).until(
                         EC.element_to_be_clickable((By.XPATH, "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt')]"))
                     )
                     finish.click()
                 else: # Attempt to go to next page if not the last question number
                     print("Attempting to go to next page despite error...")
                     next_btn = WebDriverWait(driver, 10).until(
                         EC.element_to_be_clickable((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"))
                     )
                     next_btn.click()
            except Exception as nav_e:
                 print(f"Error navigating after question processing error: {nav_e}")
                 break # Break if navigation fails
            continue # Continue to next loop iteration (which tries to process the next page)


        # Send question + options to GPT
        model_answer_letter = ask_gpt(question_text, option_texts)

        # Click the corresponding radio button based on the model's answer letter
        clicked = False
        if model_answer_letter:
            try:
                # Convert the letter ('a', 'b', 'c') to an index (0, 1, 2)
                answer_index = ord(model_answer_letter) - ord('a')
                if 0 <= answer_index < len(radio_elements):
                    # Check if the element is visible and clickable before clicking
                    wait.until(EC.visibility_of(radio_elements[answer_index]))
                    wait.until(EC.element_to_be_clickable(radio_elements[answer_index]))
                    driver.execute_script("arguments[0].click();", radio_elements[answer_index]) # Use JS click as a fallback/more reliable click
                    print(f"Clicked option {model_answer_letter}: {option_texts[answer_index]}")
                    clicked = True
                else:
                    print(f"Model returned letter '{model_answer_letter}' which is out of bounds for available options ({len(option_texts)}).")
            except Exception as click_e:
                print(f"Error clicking radio button for option {model_answer_letter}: {click_e}")

        if not clicked:
            print("Could not match model answer to any option or click failed.")
            # Optional: As a fallback, you could select a default answer like the first one
            # try:
            #     if radio_elements:
            #         driver.execute_script("arguments[0].click();", radio_elements[0])
            #         print("Clicked the first option as a fallback.")
            # except Exception as fb_e:
            #     print(f"Fallback click failed: {fb_e}")


        # Navigate to the next question page or finish
        if i == 9: # Assuming 10 questions total, index 9 is the last one
            print("Attempting to finish quiz...")
            finish = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt')]"))
            )
            finish.click()
            # Add waiting for the confirmation page if it exists
            try:
                 print("Looking for 'Submit all and finish' confirmation...")
                 # Wait for the first confirmation button
                 submit_all_btn1 = WebDriverWait(driver, 10).until(
                     EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Submit all and finish')]"))
                 )
                 submit_all_btn1.click()
                 print("Clicked first 'Submit all and finish'.")

                 # Wait for the final confirmation button
                 submit_all_btn2 = WebDriverWait(driver, 10).until(
                     EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Submit all and finish')]"))
                 )
                 submit_all_btn2.click()
                 print("Clicked final 'Submit all and finish'.")

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
        # If a critical error happens (like element not found), you might want to stop
        # break # Uncomment to stop on any unexpected error
        # continue # Uncomment to try processing the next question page despite the error

print("\nQuiz processing completed (or stopped due to error).")
driver.quit()
