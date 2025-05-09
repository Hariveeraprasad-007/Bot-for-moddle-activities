from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import pyttsx3
import time

# Setup text-to-speech
engine = pyttsx3.init()
engine.setProperty('rate', 150)

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

options = Options()
options.set_preference("permissions.default.microphone", 1)
options.set_preference("media.navigator.permission.disabled", True)
options.set_preference("media.navigator.streams.fake", False)  # Set to True for fake mic (testing)

driver = webdriver.Firefox(options=options)

wait = WebDriverWait(driver, 30)

# Login
driver.get("https://lms2.ai.saveetha.in/mod/readaloud/view.php?id=36854")
wait.until(EC.presence_of_element_located((By.ID, 'username'))).send_keys("23009466")
wait.until(EC.presence_of_element_located((By.ID, 'password'))).send_keys("g26736")
wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn'))).click()
# Click "Start Attempt" button
wait.until(EC.element_to_be_clickable((By.ID, 'mod_readaloud_button_startnoshadow'))).click()


# Switch to iframe if needed and click start button
# Wait until the button is present and not disabled
try:
    def button_enabled(driver):
        btn = driver.find_element(By.CLASS_NAME, "poodll_test-recording_readaloud")
        return btn.is_enabled() and "pmr_disabled" not in btn.get_attribute("class")

    wait.until(button_enabled)

    # Now find and click it
    start_button = driver.find_element(By.CLASS_NAME, "poodll_test-recording_readaloud")
    start_button.click()
    print("✅ Recording started.")
except Exception as e:
    print("❌ Could not find or click the recording button:", e)


# Extract passage
driver.switch_to.default_content()
try:
    container = wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'mod_readaloud_passage_cont')))
    elements = container.find_elements(By.XPATH, ".//span[contains(@class, 'mod_readaloud_grading_passageword') or contains(@class, 'mod_readaloud_grading_passagespace')]")
    full_text = ''.join([el.text for el in elements])
    print("Extracted Text:\n", full_text)
    engine.say(full_text)
    engine.runAndWait()
except Exception as e:
    print("❌ Failed to extract or read the passage:", str(e))

# Stop recording
try:
    driver.switch_to.default_content()
    stop_button = wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'poodll_stop-recording_readaloud')))
    stop_button.click()
    print("✅ Recording stopped.")
except Exception as e:
    print("❌ Failed to stop recording:", str(e))

time.sleep(2)
driver.quit()
