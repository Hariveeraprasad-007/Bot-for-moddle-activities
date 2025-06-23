from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.alert import Alert
import pyttsx3
import sounddevice as sd
import numpy as np
import time
import os

# Simulate Gemini API response (replace with actual Gemini API call)
def generate_gemini_response(topic, target_words):
    response = (
        f"The {topic.lower()} is a fascinating concept in AI. It evaluates {target_words[0]} to make decisions. "
        f"The {target_words[1]} determines the {target_words[2]}, reflecting {target_words[3]}. "
        f"The agent performs an {target_words[4]} to achieve {target_words[5]}. "
        f"This process {target_words[6]} to quantify the {target_words[7]}. "
        f"In summary, the {topic.lower()} optimizes decision-making by balancing preferences and outcomes."
    )
    return response

# Validate audio devices
def check_audio_devices():
    devices = sd.query_devices()
    print("Available audio devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device['name']}, Input Channels: {device['max_input_channels']}, Output Channels: {device['max_output_channels']}")
    vb_audio = [d for d in devices if "vb-audio" in d['name'].lower() or "cable" in d['name'].lower()]
    if vb_audio:
        print("VB-Audio Cable detected:", vb_audio[0]['name'])
        return vb_audio[0]['name'], True
    else:
        print("WARNING: VB-Audio Cable not found. Using default microphone.")
        mic = [d for d in devices if d['max_input_channels'] > 0 and "intel" in d['name'].lower()]
        if mic:
            print("Using fallback microphone:", mic[0]['name'])
            return mic[0]['name'], False
        raise Exception("No suitable input device found. Install VB-Audio Cable or ensure a microphone is available.")

# Test audio routing
def test_audio_routing(device_name, is_vb_audio):
    print(f"Testing audio routing with device: {device_name}...")
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.say("Testing voice input")
    fs = 44100
    with sd.InputStream(device=device_name, samplerate=fs, channels=2) as stream:
        recording = sd.rec(int(2 * fs), samplerate=fs, channels=2, device=device_name)
        engine.runAndWait()
        sd.wait()
    max_amplitude = np.max(np.abs(recording))
    print(f"Test recording max amplitude = {max_amplitude:.4f}")
    if max_amplitude < 0.001:
        print(f"Warning: {device_name} test failed - no audio input detected. Check your audio settings.")
    else:
        print("Audio input test passed OK.")

# Initialize pyttsx3
engine = pyttsx3.init()
engine.setProperty('rate', 180)  # 180 wpm for ~40–50s on 120–150 words
engine.setProperty('volume', 0.9)

# Initialize Chrome WebDriver
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--use-fake-ui-for-media-stream")
options.add_argument("--disable-notifications")
driver = webdriver.Chrome(options=options)

try:
    # Validate audio setup
    audio_device, is_vb_audio = check_audio_devices()
    if not is_vb_audio:
        print("WARNING: Using physical microphone")
        test_audio_routing(audio_device, is_vb_audio)
    else:
        print("VB-Audio detected; skipping test.")

    # Navigate to login page
    driver.get("https://lms2.ai.saveetha.in/login/index.php")
    print("Navigated to login page")

    # Enter login credentials
    username = "23009466"  # Replace with your username
    password = "1554"  # Replace with your password
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)

    # Click login button
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "loginbtn"))
    )
    login_button.click()
    print("Clicked login button")

    # Verify login
    try:
        WebDriverWait(driver, 10).until(EC.url_contains("saveetha.in"))
        print("Login successful")
    except:
        raise Exception("Login failed. Check credentials or network.")

    # Navigate to initial activity page
    activity_url = "https://lms2.ai.saveetha.in/mod/solo/attempt/manageattempts.php?id=32323&attemptid=0&stepno=1"
    driver.get(activity_url)
    print("Navigated to initial activity page")

    # Handle 503 errors
    retries = 5
    for attempt in range(retries):
        try:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            break
        except:
            if attempt < retries - 1:
                print("Retrying due to page load issue...")
                time.sleep(5)
                driver.refresh()
            else:
                raise Exception("Failed to load page after retries")

    # Click start button to navigate to next page
    start_button = None
    try:
        start_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "68568c7dad64b68568c7d75c4d70_button"))
        )
    except:
        start_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Start']"))
        )
    driver.execute_script("arguments[0].scrollIntoView(true);", start_button)
    try:
        start_button.click()
        print("Clicked 'Start' button with Selenium")
    except:
        print("Selenium click failed, attempting JavaScript click")
        driver.execute_script("arguments[0].click();", start_button)
        print("Clicked 'Start' button with JavaScript")

    # Wait for navigation to new page (check for topic or recording button)
    WebDriverWait(driver, 30).until(
        EC.any_of(
            EC.presence_of_element_located((By.CLASS_NAME, "mod_solo_speakingtopic_readonly")),
            EC.presence_of_element_located((By.CLASS_NAME, "poodll_mediarecorder_minimal_start_button"))
        )
    )
    print("Navigated to recording page")

    # Extract topic
    topic_element = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, "mod_solo_speakingtopic_readonly"))
    )
    topic = topic_element.text.strip()
    print("Extracted topic:", topic)

    # Wait briefly to ensure DOM stability
    time.sleep(2)

    # Extract target words with a fresh lookup
    target_word_elements = WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "mod_solo_targetwordtag"))
    )
    target_words = [elem.text.strip() for elem in target_word_elements]
    print("Extracted target words:", target_words)

    # Generate response with Gemini
    speech_text = generate_gemini_response(topic, target_words)
    print("Generated speech text:", speech_text)

    # Check for iframes
    def switch_to_iframe_with_element(selector):
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if not iframes:
            print("No iframes found")
            return False
        for i, iframe in enumerate(iframes):
            try:
                driver.switch_to.frame(iframe)
                print(f"Switched to iframe {i}")
                WebDriverWait(driver, 5).until(EC.presence_of_element_located(selector))
                return True
            except:
                print(f"Element not found in iframe {i}, switching back")
                driver.switch_to.default_content()
        return False

    # Click record button
    record_success = False
    record_button_selector = (By.CLASS_NAME, "poodll_mediarecorder_minimal_start_button")
    for attempt in range(3):
        try:
            if switch_to_iframe_with_element(record_button_selector):
                print("Found record button in iframe")
            else:
                driver.switch_to.default_content()
                print("Searching for record button in main content")
            
            record_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(record_button_selector)
            )
            driver.execute_script("arguments[0].scrollIntoView(true);", record_button)
            try:
                record_button.click()
                print("Clicked 'Record' button with Selenium")
            except:
                print("Selenium click failed, attempting JavaScript click")
                driver.execute_script("arguments[0].click();", record_button)
                print("Clicked 'Record' button with JavaScript")
            time.sleep(1)  # Wait for PoodLL initialization
            record_success = True
            break
        except Exception as e:
            print(f"Record attempt {attempt + 1} failed: {e}")
            driver.switch_to.default_content()
            time.sleep(2)
    
    if not record_success:
        raise Exception("Failed to click 'Record' button after retries")

    # Handle JavaScript alert
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = Alert(driver)
        alert.accept()
        print("Accepted JavaScript microphone alert")
    except:
        print("No JavaScript alert found, continuing...")

    # Speak text
    print("Speaking text directly...")
    start_time = time.time()
    engine.say(speech_text)
    engine.runAndWait()
    elapsed_time = time.time() - start_time
    print(f"Finished speaking in {elapsed_time:.2f} seconds")

    # Click stop button with retry logic
    driver.switch_to.default_content()
    stop_button_selector = (By.CLASS_NAME, "poodll_mediarecorder_minimal_stop_button")
    stop_success = False
    for attempt in range(3):
        try:
            if switch_to_iframe_with_element(stop_button_selector):
                print("Found stop button in iframe")
            else:
                driver.switch_to.default_content()
                print("Searching for stop button in main content")
            
            stop_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(stop_button_selector)
            )
            # Ensure button is visible and not disabled
            if "disabled" not in stop_button.get_attribute("class") and stop_button.is_displayed():
                driver.execute_script("arguments[0].scrollIntoView(true);", stop_button)
                time.sleep(2)  # Wait for animation/state change
                try:
                    stop_button.click()
                    print("Clicked 'Stop' button with Selenium")
                    stop_success = True
                    break
                except:
                    print("Selenium click failed, attempting JavaScript click")
                    driver.execute_script("arguments[0].click();", stop_button)
                    print("Clicked 'Stop' button with JavaScript")
                    stop_success = True
                    break
            else:
                print(f"Stop button attempt {attempt + 1} not interactable, retrying...")
                time.sleep(2)
        except Exception as e:
            print(f"Stop button attempt {attempt + 1} failed: {e}")
            driver.switch_to.default_content()
            time.sleep(2)
    
    if not stop_success:
        raise Exception("Failed to click 'Stop' button after retries")

    # Click next button with wait
    driver.switch_to.default_content()
    next_button = None
    try:
        next_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.ID, "6857cec0497296857cec0110d680_button"))
        )
    except:
        next_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Next']"))
        )
    driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
    try:
        next_button.click()
        print("Clicked 'Next' button with Selenium")
    except:
        print("Selenium click failed, attempting JavaScript click")
        driver.execute_script("arguments[0].click();", next_button)
        print("Clicked 'Next' button with JavaScript")

    # Wait for textarea to be populated with text
    textarea = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "6857d0f18732f6857d0f162f0c79_selftranscript"))
    )
    WebDriverWait(driver, 60).until(
        lambda d: len(d.find_element(By.ID, "6857d0f18732f6857d0f162f0c79_selftranscript").get_attribute("value").strip().split()) > 5
    )
    print("Textarea populated with auto-generated transcript")

    # Click submit button with retry logic
    submit_success = False
    submit_button_selector = (By.ID, "68597e59804b068597e590239f70_button")
    for attempt in range(3):
        try:
            submit_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable(submit_button_selector)
            )
            if submit_button.is_displayed() and "disabled" not in submit_button.get_attribute("class"):
                driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                try:
                    submit_button.click()
                    print("Clicked 'Submit' button with Selenium")
                    submit_success = True
                    break
                except:
                    print("Selenium click failed, attempting JavaScript click")
                    driver.execute_script("arguments[0].click();", submit_button)
                    print("Clicked 'Submit' button with JavaScript")
                    submit_success = True
                    break
            else:
                print(f"Submit button attempt {attempt + 1} not interactable, retrying...")
                time.sleep(2)
        except Exception as e:
            print(f"Submit button attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    
    if not submit_success:
        raise Exception("Failed to click 'Submit' button after retries")

    # Click done button
    done_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "68597ef3ee4d968597ef27bf6f70_button"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", done_button)
    try:
        done_button.click()
        print("Clicked 'Done' button with Selenium")
    except:
        print("Selenium click failed, attempting JavaScript click")
        driver.execute_script("arguments[0].click();", done_button)
        print("Clicked 'Done' button with JavaScript")

except Exception as e:
    print(f"An error occurred: {e}")
    with open("page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    driver.save_screenshot("error_screenshot.png")
    print("Saved page source to 'page_source.html' and screenshot to 'error_screenshot.png'")

finally:
    # Clean up
    time.sleep(2)
    driver.quit()
    print("Browser closed")
