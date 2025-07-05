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
import google.generativeai as genai

# Configure Gemini API
GEMINI_API_KEY = ""  # Replace with your Gemini API key
genai.configure(api_key=GEMINI_API_KEY)

# Generate response using Gemini API
def generate_gemini_response(topic, target_words):
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = (
            f"Generate a concise speech (100-120 words) about '{topic}' in the context of AI. "
            f"Incorporate these target words naturally: {', '.join(target_words)}. "
            f"Ensure suitability for text-to-speech at 200 wpm, lasting 30-40 seconds. "
            f"Use an informative and engaging tone."
        )
        response = model.generate_content(prompt)
        speech_text = response.text.strip()
        print("Gemini API response:", speech_text)
        return speech_text
    except Exception as e:
        print(f"Error with Gemini API: {e}")
        fallback = f"The {topic.lower()} is a key AI concept using {', '.join(target_words)} for decision-making."
        return fallback

# Validate audio devices
def check_audio_devices():
    devices = sd.query_devices()
    print("Available audio devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device['name']}, Input: {device['max_input_channels']}, Output: {device['max_output_channels']}")
    vb_audio = next((d for d in devices if "vb-audio" in d['name'].lower() or "cable" in d['name'].lower()), None)
    if vb_audio:
        print("VB-Audio Cable detected:", vb_audio['name'])
        return vb_audio['name'], True
    print("WARNING: VB-Audio Cable not found. Using default microphone.")
    mic = next((d for d in devices if d['max_input_channels'] > 0 and "intel" in d['name'].lower()), None)
    if mic:
        print("Using fallback microphone:", mic['name'])
        return mic['name'], False
    raise Exception("No suitable input device found. Install VB-Audio Cable or ensure a microphone is available.")

# Test audio routing
def test_audio_routing(device_name, is_vb_audio):
    print(f"Testing audio routing with {device_name}...")
    engine = pyttsx3.init()
    engine.setProperty('rate', 200)
    engine.say("Testing audio routing")
    fs = 44100
    with sd.InputStream(device=device_name, samplerate=fs, channels=1) as stream:
        recording = sd.rec(int(fs), samplerate=fs, channels=1, device=device_name)
        engine.runAndWait()
        sd.wait()
    max_amplitude = np.max(np.abs(recording))
    print(f"Test recording max amplitude: {max_amplitude:.4f}")
    if max_amplitude < 0.01:
        print(f"WARNING: Audio routing test failed with {device_name}. Check device settings.")
    else:
        print("Audio routing test passed.")
    return engine

# Initialize Chrome WebDriver
options = Options()
options.add_argument("--start-maximized")
options.add_argument("--no-sandbox")
options.add_argument("--use-fake-ui-for-media-stream")
options.add_argument("--disable-notifications")
driver = webdriver.Chrome(options=options)
engine = None

try:
    # Validate audio setup
    audio_device, is_vb_audio = check_audio_devices()
    if not is_vb_audio:
        print("WARNING: Using physical microphone. Audio may not route correctly without VB-Audio Cable.")
    engine = test_audio_routing(audio_device, is_vb_audio)
    engine.setProperty('rate', 200)  # 200 wpm for ~30-40s on 100-120 words
    engine.setProperty('volume', 0.9)

    # Navigate to login page
    driver.get("https://lms2.ai.saveetha.in/login/index.php")
    print("Navigated to login page")

    # Enter login credentials
    username = ""  # Replace with your username
    password = ""  # Replace with your password
    driver.find_element(By.ID, "username").send_keys(username)
    driver.find_element(By.ID, "password").send_keys(password)

    # Click login button
    login_button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "loginbtn"))
    )
    login_button.click()
    print("Clicked login button")

    # Verify login
    WebDriverWait(driver, 10).until(EC.url_contains("saveetha.in"))
    print("Login successful")

    # Navigate to initial activity page
    driver.get("https://lms2.ai.saveetha.in/mod/solo/attempt/manageattempts.php?id=32323&attemptid=0&stepno=1")
    print("Navigated to initial activity page")

    # Handle 503 errors
    for attempt in range(5):
        try:
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            break
        except:
            if attempt < 4:
                print("Retrying due to page load issue...")
                driver.refresh()
            else:
                raise Exception("Failed to load page after retries")

    # Click start button
    start_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Start']"))
    )
    driver.execute_script("arguments[0].click();", start_button)
    print("Clicked 'Start' button")

    # Wait for recording page
    WebDriverWait(driver, 20).until(
        EC.any_of(
            EC.presence_of_element_located((By.CLASS_NAME, "mod_solo_speakingtopic_readonly")),
            EC.presence_of_element_located((By.CLASS_NAME, "poodll_mediarecorder_minimal_start_button"))
        )
    )
    print("Navigated to recording page")

    # Extract topic
    topic_element = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CLASS_NAME, "mod_solo_speakingtopic_readonly"))
    )
    topic = topic_element.text.strip()
    print("Extracted topic:", topic)

    # Extract target words
    target_words = [elem.text.strip() for elem in WebDriverWait(driver, 20).until(
        EC.presence_of_all_elements_located((By.CLASS_NAME, "mod_solo_targetwordtag"))
    )]
    print("Extracted target words:", target_words)

    # Generate response with Gemini
    speech_text = generate_gemini_response(topic, target_words)
    print("Generated speech text:", speech_text)

    # Check for iframes
    def switch_to_iframe_with_element(selector):
        for i, iframe in enumerate(driver.find_elements(By.TAG_NAME, "iframe")):
            try:
                driver.switch_to.frame(iframe)
                WebDriverWait(driver, 3).until(EC.presence_of_element_located(selector))
                print(f"Switched to iframe {i}")
                return True
            except:
                driver.switch_to.default_content()
        print("No iframe with element found")
        return False

    # Click record button
    record_button_selector = (By.CLASS_NAME, "poodll_mediarecorder_minimal_start_button")
    if switch_to_iframe_with_element(record_button_selector):
        print("Found record button in iframe")
    else:
        driver.switch_to.default_content()
        print("Searching for record button in main content")
    record_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(record_button_selector))
    driver.execute_script("arguments[0].click();", record_button)
    print("Clicked 'Record' button")

    # Handle JavaScript alert
    try:
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        Alert(driver).accept()
        print("Accepted JavaScript microphone alert")
    except:
        print("No JavaScript alert found")

    # Speak text
    print("Speaking text...")
    start_time = time.time()
    engine.say(speech_text)
    engine.runAndWait()
    print(f"Finished speaking in {time.time() - start_time:.2f} seconds")

    # Click stop button
    driver.switch_to.default_content()
    stop_button_selector = (By.CLASS_NAME, "poodll_mediarecorder_minimal_stop_button")
    if switch_to_iframe_with_element(stop_button_selector):
        print("Found stop button in iframe")
    else:
        driver.switch_to.default_content()
        print("Searching for stop button in main content")
    stop_button = WebDriverWait(driver, 20).until(EC.element_to_be_clickable(stop_button_selector))
    driver.execute_script("arguments[0].click();", stop_button)
    print("Clicked 'Stop' button")

    # Click next button
    next_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Next']"))
    )
    driver.execute_script("arguments[0].click();", next_button)
    print("Clicked 'Next' button")

    # Save page source for debugging
    with open("transcript_page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("Saved transcript page source to 'transcript_page_source.html'")

    # Wait for transcript page
    WebDriverWait(driver, 30).until(
        EC.any_of(
            EC.presence_of_element_located((By.XPATH, "//input[@type='checkbox' and @id[contains(., 'dontwaitfortranscript')]]")),
            EC.presence_of_element_located((By.XPATH, "//textarea[@id[contains(., 'selftranscript')]]"))
        )
    )
    print("Transcript page loaded")

    # Click checkbox
    try:
        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@type='checkbox' and @id[contains(., 'dontwaitfortranscript')]]"))
        )
        print("Checkbox found by ID")
    except:
        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'I do not want to wait for the transcript')]/preceding-sibling::input[@type='checkbox']"))
        )
        print("Checkbox found using text-based XPath")
    driver.execute_script("arguments[0].click();", checkbox)
    print("Clicked 'I do not want to wait for the transcript' checkbox")

    # Paste text into textarea
    try:
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "68615e96ccfef68615e968b78270_selftranscript"))
        )
        print("Textarea found by ID")
    except:
        textarea = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@id[contains(., 'selftranscript')]]"))
        )
        print("Textarea found using XPath")
    driver.execute_script("arguments[0].value = arguments[1];", textarea, speech_text)
    print("Pasted text into textarea")

    # Click submit button
    submit_button = WebDriverWait(driver, 20).until(
        EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Submit']"))
    )
    driver.execute_script("arguments[0].click();", submit_button)
    print("Clicked 'Submit' button")

    # Wait for Done button
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//button[@class='btn' and text()='Done']"))
        )
        print("Done button appeared")
    except:
        print("Done button not found, trying ID")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.ID, "68597ef3ee4d968597ef27bf6f70_button"))
        )
        print("Done button found by ID")

    # Click done button
    try:
        done_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@class='btn' and text()='Done']"))
        )
    except:
        done_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.ID, "68597ef3ee4d968597ef27bf6f70_button"))
        )
    driver.execute_script("arguments[0].click();", done_button)
    print("Clicked 'Done' button")

except Exception as e:
    print(f"An error occurred: {e}")
    with open("page_source.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    driver.save_screenshot("error_screenshot.png")
    print("Saved page source to 'page_source.html' and screenshot to 'error_screenshot.png'")

finally:
    if engine:
        engine.stop()
    driver.quit()
    print("Browser closed")
