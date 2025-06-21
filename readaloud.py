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

# Validate audio devices and test routing
def check_audio_devices():
    devices = sd.query_devices()
    print("Available audio devices:")
    for i, device in enumerate(devices):
        print(f"{i}: {device['name']}, Input Channels: {device['max_input_channels']}, Output Channels: {device['max_output_channels']}")
    vb_audio = [d for d in devices if "CABLE" in d['name'].upper()]
    if vb_audio:
        print("VB-Audio Cable detected:", vb_audio[0]['name'])
        return vb_audio[0]['name'], True
    else:
        print("WARNING: VB-Audio Cable not found. Falling back to default microphone.")
        mic = [d for d in devices if d['max_input_channels'] > 0 and "Intel" in d['name']]
        if mic:
            print("Using fallback microphone:", mic[0]['name'])
            return mic[0]['name'], False
        raise Exception("No suitable input device found. Install VB-Audio Cable or ensure a microphone is available.")

def test_audio_routing(device_name, is_vb_audio):
    print(f"Testing audio routing with {device_name}...")
    engine = pyttsx3.init()
    engine.setProperty('rate', 180)
    engine.say("Testing audio routing")
    fs = 44100
    with sd.InputStream(device=device_name, samplerate=fs, channels=1) as stream:
        recording = sd.rec(int(3 * fs), samplerate=fs, channels=1, device=device_name)
        engine.runAndWait()
        sd.wait()
    max_amplitude = np.max(np.abs(recording))
    print(f"Test recording max amplitude: {max_amplitude:.4f}")
    if max_amplitude < 0.01:
        raise Exception(f"Audio routing test failed with {device_name}. No audio detected. Check device settings.")
    print("Audio routing test passed.")

# Initialize pyttsx3
engine = pyttsx3.init()
engine.setProperty('rate', 180)  # 180 wpm for ~40s on 120 words
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
        print("WARNING: Using physical microphone. Audio may not route correctly without VB-Audio Cable.")
    test_audio_routing(audio_device, is_vb_audio)

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

    # Navigate to read-aloud page
    driver.get("https://lms2.ai.saveetha.in/mod/readaloud/view.php?id=30184")
    print("Navigated to read-aloud page")

    # Handle 503 errors
    retries = 5
    for attempt in range(retries):
        try:
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "mod_readaloud_button_startnoshadow")))
            break
        except:
            if attempt < retries - 1:
                print("Retrying due to page load issue...")
                time.sleep(5)
                driver.refresh()
            else:
                raise Exception("Failed to load page after retries")

    # Click "Read" button
    read_button = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.ID, "mod_readaloud_button_startnoshadow"))
    )
    driver.execute_script("arguments[0].scrollIntoView(true);", read_button)
    try:
        read_button.click()
        print("Clicked 'Read' button with Selenium")
    except:
        driver.execute_script("arguments[0].click();", read_button)
        print("Clicked 'Read' button with JavaScript")

    # Check for iframes
    def switch_to_iframe_with_button():
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if not iframes:
            print("No iframes found")
            return False
        for i, iframe in enumerate(iframes):
            try:
                driver.switch_to.frame(iframe)
                print(f"Switched to iframe {i}")
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button.poodll_start-recording_readaloud[aria-label='Record']"))
                )
                return True
            except:
                print(f"Record button not found in iframe {i}, switching back")
                driver.switch_to.default_content()
        return False

    # Click "Record" button with retries
    record_success = False
    for attempt in range(3):
        try:
            if switch_to_iframe_with_button():
                print("Found record button in iframe")
            else:
                driver.switch_to.default_content()
                print("Searching for record button in main content")
            
            record_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.poodll_start-recording_readaloud[aria-label='Record']"))
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

    # Extract text
    driver.switch_to.default_content()
    passage_elements = driver.find_elements(By.CLASS_NAME, "mod_readaloud_grading_passageword")
    passage_text = " ".join([elem.text for elem in passage_elements])
    print("Extracted passage:", passage_text)

    # Speak text
    print("Speaking text directly...")
    start_time = time.time()
    engine.say(passage_text)
    engine.runAndWait()
    elapsed_time = time.time() - start_time
    print(f"Finished speaking in {elapsed_time:.2f} seconds")

    # Click "Stop" button
    try:
        stop_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.poodll_stop-recording_readaloud[aria-label='Stop']"))
        )
        driver.execute_script("arguments[0].removeAttribute('disabled')", stop_button)
        driver.execute_script("arguments[0].scrollIntoView(true);", stop_button)
        try:
            stop_button.click()
            print("Clicked 'Stop' button with Selenium")
        except:
            driver.execute_script("arguments[0].click();", stop_button)
            print("Clicked 'Stop' button with JavaScript")
    except Exception as e:
        print(f"Failed to click 'Stop' button: {e}")
        with open("page_source.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        driver.save_screenshot("error_screenshot.png")
        print("Saved page source to 'page_source.html' and screenshot to 'error_screenshot.png'")
        raise

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