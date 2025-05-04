from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from transformers import pipeline

# Initialize the Hugging Face question-answering model (using a better model like RoBERTa)
generator = pipeline("question-answering", model="roberta-base")

# Setup Firefox WebDriver
driver = webdriver.Firefox()

# Login
driver.get("https://lms2.ai.saveetha.in/mod/quiz/view.php?id=1394")  # Use your quiz URL
WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.NAME, 'username'))).send_keys("23009466")
driver.find_element(By.NAME, 'password').send_keys("g26736")
driver.find_element(By.ID, 'loginbtn').click()
time.sleep(2)

# Wait for the quiz button (either Start, Re-attempt, or Continue last attempt)
quiz_button = WebDriverWait(driver, 30).until(
    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')]"))
)

button_text = quiz_button.text.strip()
if button_text == "Continue your attempt":
    # If the button is "Continue last attempt", click it directly
    quiz_button.click()
    print("Clicked 'Continue last attempt' to continue the quiz.")
elif button_text.lower() in ['start attempt', 're-attempt quiz']:
    # If it's "Start attempt" or "Re-attempt", click the button
    quiz_button.click()
    driver.find_element(By.ID,'id_submitbutton').click()
    print(f"Clicked '{button_text}' to start the quiz.")
    
    # Now, after clicking "Start attempt" or "Re-attempt", we need to wait for the page to load and click the "Start attempt" button again

wait = WebDriverWait(driver, 10)

# Proceed with questions as usual
for i in range(10):  # Assuming 10 questions
    time.sleep(2)

    try:
        wait = WebDriverWait(driver, 10)
        question_text = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext"))).text

        # Get the 4 answer options and radio buttons
        option_elements = driver.find_elements(By.CSS_SELECTOR, ".answer div")[:4]  # Only the first 4 options
        radio_buttons = driver.find_elements(By.CSS_SELECTOR, ".answer input[type='radio']")[:4]  # Only the first 4 radio buttons

        options = [opt.text.strip() for opt in option_elements if opt.text.strip()]  # Remove any empty text elements

        # If there are less than 4 options, print a message
        if len(options) < 4:
            print(f"Warning: Less than 4 options found for question {i+1}.")

        # Ensure there are no duplicate options
        options = list(set(options))

        # Handle the case when there are still less than 4 options after removing duplicates
        while len(options) < 4:
            options.append("Empty Option")  # Adding filler options to make the list length 4

        context = " ".join(options)  # Use all options as context for the model

        # Use Hugging Face to find the best answer
        result = generator(question=question_text, context=context)
        model_answer = result['answer'].strip().lower()

        print(f"\nQ{i+1}: {question_text}")
        print("Options:", options)
        print("Model Answer:", model_answer)

        # Match model answer to one of the options
        clicked = False
        for j, opt in enumerate(options):
            if model_answer in opt.lower():  # Case-insensitive matching
                radio_buttons[j].click()
                print(f"Clicked option: {options[j]}")
                clicked = True
                break

        if not clicked:
            print("Model answer not matched with any option.")

        # Click next or finish
        if i == 9:
            finish_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Finish attempt ...'] | //button[contains(text(), 'Finish attempt ...')]"))
            )
            finish_button.click()
            print("Clicked 'Finish attempt'.")
        else:
            next_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"))
            )
            next_button.click()
            print("Clicked 'Next page'.")

    except Exception as e:
        print(f"Error on question {i+1}: {e}")
        break

driver.quit()
