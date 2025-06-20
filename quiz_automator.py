import os
import time
import requests
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import re
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

# Selenium imports (ensure these are installed: pip install selenium webdriver-manager beautifulsoup4 requests fuzzywwuzzy)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException, InvalidSessionIdException

# Import necessary WebDriver services for webdriver_manager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

# --- Configuration ---
# Gemini API Key - IMPORTANT: In a production environment, load this securely from environment variables.
# For Tkinter, we can ask the user to input it if not found in env.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "") 
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Predefined login site options
LOGIN_SITE_OPTIONS = {
    "EEE Site": "https://lms2.eee.saveetha.in/login/index.php",
    "CSE Site": "https://lms2.cse.saveetha.in/login/index.php",
    "AI Site": "https://lms2.ai.saveetha.in/login/index.php",
}

# Predefined browser driver options
BROWSER_OPTIONS = {
    "Chrome": "chrome",
    "Firefox": "firefox",
    "Edge": "edge",
    "Safari": "safari", # Safari driver is typically built-in on macOS
}

# --- Global WebDriver and Wait objects ---
# These will be managed within the App class
driver = None
wait = None

# --- Utility Functions (Adapted for GUI logging) ---

class GuiLogger:
    """A custom logger that redirects print statements to a Tkinter scrolledtext widget."""
    def __init__(self, text_widget, message_queue):
        self.text_widget = text_widget
        self.message_queue = message_queue
        self.flush = self.do_nothing # Add a flush method for compatibility

    def write(self, message):
        self.message_queue.put(message)

    def do_nothing(self):
        pass # Placeholder for flush

# --- ask_gemini Function (Integrated into App class or passed logger) ---
def ask_gemini(question, options, logger_func):
    """
    Sends a multiple-choice question to the Gemini API and returns the chosen option letter.
    Includes robust parsing for Gemini's response and a fuzzy matching fallback.
    """
    global GEMINI_API_KEY # Use global to access the key which might be set by GUI
    if not GEMINI_API_KEY:
        logger_func("Error: Gemini API Key is not set. Please provide it in the GUI.", "error")
        return ""

    option_letters = ['a', 'b', 'c', 'd']
    formatted_options = "\n".join([f"{letter}. {opt}" for letter, opt in zip(option_letters, options)])
    
    prompt = (
        "You are a multiple choice answering bot.\n"
        "Read the question and the options below carefully.\n"
        f"Your response should be ONLY the letter of the correct option ({', '.join(option_letters[:len(options)])}) and nothing else.\n\n"
        f"Question: {question}\n\nOptions:\n{formatted_options}\n\nAnswer:"
    )
    logger_func(f"Sending prompt to Gemini API for question: {question[:50]}...")
    
    headers = {
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            json=payload,
            headers=headers
        )
        response.raise_for_status() 
        response_data = response.json()
        
        generated_text = response_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
        
        potential_answer_match = re.match(r"^\s*([a-d])", generated_text)
        if potential_answer_match:
            direct_letter = potential_answer_match.group(1)
            if direct_letter in option_letters[:len(options)]:
                return direct_letter
        
        flexible_match = re.search(r"\b([a-d])\b", generated_text)
        if flexible_match:
            found_letter = flexible_match.group(1)
            if found_letter in option_letters[:len(options)]:
                return found_letter
        
        logger_func("No clear letter found, attempting fuzzy match...")
        best_match_letter, best_score = "", 0
        fuzzy_threshold = 70
        
        for idx, opt in enumerate(options):
            score = fuzz.token_set_ratio(generated_text, opt.lower())
            if score > best_score:
                best_score = score
                best_match_letter = option_letters[idx]
        
        if best_score >= fuzzy_threshold:
            logger_func(f"Fuzzy fallback selected: '{best_match_letter}' (score: {best_score})")
            return best_match_letter if best_match_letter in option_letters[:len(options)] else ""
        else:
            logger_func(f"Fuzzy match score {best_score} below threshold {fuzzy_threshold}. Cannot determine answer.", "warning")
            return ""
            
    except requests.exceptions.RequestException as req_e:
        logger_func(f"Network or HTTP error during Gemini API call: {req_e}", "error")
        return ""
    except (KeyError, IndexError) as parse_e:
        logger_func(f"Error parsing Gemini API response structure: {parse_e}. Response: {response_data}", "error")
        return ""
    except Exception as e:
        logger_func(f"An unexpected error occurred during Gemini API call: {e}", "error")
        return ""


class QuizAutomationApp:
    def __init__(self, master):
        self.master = master
        master.title("Quiz Automation Bot")
        master.geometry("1000x800")

        self.driver = None
        self.wait = None
        self.automation_thread = None
        self.stop_event = threading.Event()
        self.log_queue = queue.Queue() # Queue for thread-safe logging

        self._create_widgets()
        self._setup_logging()
        self._process_log_queue() # Start checking the log queue

        # Populate initial values (if desired)
        self.username_entry.insert(0, "")
        self.password_entry.insert(0, "")
        self.headless_var.set(True) # Default to headless

    def _create_widgets(self):
        """Creates all GUI widgets and arranges them."""
        # --- Settings Frame ---
        settings_frame = ttk.LabelFrame(self.master, text="Settings", padding="10")
        settings_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        settings_frame.columnconfigure(1, weight=1)

        # Browser Driver
        ttk.Label(settings_frame, text="Browser Driver:").grid(row=0, column=0, sticky="w", pady=2)
        self.browser_driver_combobox = ttk.Combobox(settings_frame, values=list(BROWSER_OPTIONS.keys()), state="readonly")
        self.browser_driver_combobox.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.browser_driver_combobox.set("Chrome") # Default selection
        self.browser_driver_combobox.bind("<<ComboboxSelected>>", self._on_browser_selected)

        # Headless Mode
        self.headless_var = tk.BooleanVar()
        self.headless_checkbox = ttk.Checkbutton(settings_frame, text="Run Headless (No UI)", variable=self.headless_var)
        self.headless_checkbox.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        # LMS Site
        ttk.Label(settings_frame, text="LMS Site:").grid(row=2, column=0, sticky="w", pady=2)
        self.lms_site_combobox = ttk.Combobox(settings_frame, values=list(LOGIN_SITE_OPTIONS.keys()), state="readonly")
        self.lms_site_combobox.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.lms_site_combobox.set("EEE Site") # Default selection

        # Credentials
        ttk.Label(settings_frame, text="Username:").grid(row=3, column=0, sticky="w", pady=2)
        self.username_entry = ttk.Entry(settings_frame)
        self.username_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(settings_frame, text="Password:").grid(row=4, column=0, sticky="w", pady=2)
        self.password_entry = ttk.Entry(settings_frame, show="*") # Show stars for password
        self.password_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=2)

        # Gemini API Key
        ttk.Label(settings_frame, text="Gemini API Key:").grid(row=5, column=0, sticky="w", pady=2)
        self.gemini_key_entry = ttk.Entry(settings_frame, show="*")
        self.gemini_key_entry.grid(row=5, column=1, sticky="ew", padx=5, pady=2)
        self.gemini_key_entry.insert(0, GEMINI_API_KEY) # Pre-fill if from env var

        # --- Quiz URLs Frame ---
        quiz_frame = ttk.LabelFrame(self.master, text="Quiz URLs", padding="10")
        quiz_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        quiz_frame.columnconfigure(0, weight=1)
        quiz_frame.columnconfigure(1, weight=0) # Target Score column
        self.master.rowconfigure(1, weight=1) # Allow quiz frame to expand

        # Quiz Listbox
        self.quiz_listbox_frame = ttk.Frame(quiz_frame)
        self.quiz_listbox_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=5)
        self.quiz_listbox_frame.rowconfigure(0, weight=1)
        self.quiz_listbox_frame.columnconfigure(0, weight=1)

        self.quiz_listbox = tk.Listbox(self.quiz_listbox_frame, height=8, selectmode=tk.SINGLE)
        self.quiz_listbox.grid(row=0, column=0, sticky="nsew")
        quiz_scrollbar = ttk.Scrollbar(self.quiz_listbox_frame, orient="vertical", command=self.quiz_listbox.yview)
        quiz_scrollbar.grid(row=0, column=1, sticky="ns")
        self.quiz_listbox.config(yscrollcommand=quiz_scrollbar.set)

        # Add/Remove Quiz Buttons and Entry
        add_quiz_frame = ttk.Frame(quiz_frame)
        add_quiz_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        add_quiz_frame.columnconfigure(0, weight=1) # Allow URL entry to expand

        ttk.Label(add_quiz_frame, text="Quiz URL:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.quiz_url_entry = ttk.Entry(add_quiz_frame)
        self.quiz_url_entry.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        
        ttk.Label(add_quiz_frame, text="Target Score (Optional):").grid(row=0, column=1, sticky="w", padx=2, pady=2)
        self.quiz_target_score_entry = ttk.Entry(add_quiz_frame, width=15) # Adjusted width slightly
        self.quiz_target_score_entry.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        self.quiz_target_score_entry.insert(0, "e.g., 4.0") # More specific placeholder
        self.quiz_target_score_entry.bind("<FocusIn>", self._clear_target_score_placeholder)
        self.quiz_target_score_entry.bind("<FocusOut>", self._restore_target_score_placeholder)

        # Store references to these buttons
        self.add_quiz_button = ttk.Button(add_quiz_frame, text="Add Quiz", command=self._add_quiz)
        self.add_quiz_button.grid(row=1, column=2, padx=2, pady=2)
        self.remove_quiz_button = ttk.Button(add_quiz_frame, text="Remove Selected", command=self._remove_quiz)
        self.remove_quiz_button.grid(row=1, column=3, padx=2, pady=2)
        
        self.quizzes_data = [] # Stores (url, target_score) tuples

        # --- Control Buttons ---
        control_frame = ttk.Frame(self.master, padding="10")
        control_frame.grid(row=2, column=0, padx=10, pady=5, sticky="ew")
        control_frame.columnconfigure(0, weight=1)
        control_frame.columnconfigure(1, weight=1)

        self.start_button = ttk.Button(control_frame, text="Start Automation", command=self._start_automation)
        self.start_button.grid(row=0, column=0, sticky="ew", padx=5)
        self.stop_button = ttk.Button(control_frame, text="Stop Automation", command=self._stop_automation, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=1, sticky="ew", padx=5)

        # --- Log Output Frame ---
        log_frame = ttk.LabelFrame(self.master, text="Logs", padding="10")
        log_frame.grid(row=0, column=1, rowspan=3, padx=10, pady=10, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state="disabled", width=70, height=30)
        self.log_text.grid(row=0, column=0, sticky="nsew")

        self.master.columnconfigure(0, weight=1)
        self.master.columnconfigure(1, weight=2)
        self.master.rowconfigure(0, weight=0) # Settings frame fixed size
        self.master.rowconfigure(1, weight=1) # Quiz frame expands
        self.master.rowconfigure(2, weight=0) # Control frame fixed size

    def _setup_logging(self):
        """Sets up the custom logger to redirect output to the GUI."""
        self.logger = GuiLogger(self.log_text, self.log_queue)
        self.log_text.tag_config("error", foreground="red")
        self.log_text.tag_config("warning", foreground="orange")
        self.log_text.tag_config("info", foreground="blue")


    def _process_log_queue(self):
        """Periodically checks the log queue and updates the text widget."""
        while not self.log_queue.empty():
            message = self.log_queue.get()
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, message)
            self.log_text.see(tk.END) # Scroll to the end
            self.log_text.config(state="disabled")
        self.master.after(100, self._process_log_queue) # Check every 100ms

    def log(self, message, tag=None):
        """Thread-safe logging function for the GUI."""
        # Add timestamp
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ", time.localtime())
        self.log_queue.put(timestamp + str(message) + "\n")
        # Tags for coloring are not directly implemented in GuiLogger.write,
        # but the `tag` argument is kept for future expansion if needed.

    def _on_browser_selected(self, event):
        """Enables/disables headless checkbox based on Safari selection."""
        selected_browser = self.browser_driver_combobox.get()
        if selected_browser == "Safari":
            self.headless_var.set(False)
            self.headless_checkbox.config(state=tk.DISABLED)
            self.log("Safari browser does not support headless mode.", "warning")
        else:
            self.headless_checkbox.config(state=tk.NORMAL)

    def _clear_target_score_placeholder(self, event):
        if self.quiz_target_score_entry.get() == "e.g., 4.0":
            self.quiz_target_score_entry.delete(0, tk.END)
            self.quiz_target_score_entry.config(fg="black")

    def _restore_target_score_placeholder(self, event):
        if not self.quiz_target_score_entry.get():
            self.quiz_target_score_entry.insert(0, "e.g., 4.0")
            self.quiz_target_score_entry.config(fg="grey")

    def _add_quiz(self):
        """Adds a quiz URL and optional target score to the list."""
        url = self.quiz_url_entry.get().strip()
        target_score_str = self.quiz_target_score_entry.get().strip()

        if not url:
            messagebox.showwarning("Input Error", "Quiz URL cannot be empty.")
            return

        target_score = None
        if target_score_str and target_score_str != "e.g., 4.0":
            try:
                target_score = float(target_score_str)
            except ValueError:
                messagebox.showwarning("Input Error", "Target score must be a number (e.g., 4.0).")
                return

        display_text = f"URL: {url}"
        if target_score is not None:
            display_text += f" | Target Score: {target_score}"
        else:
            display_text += " | Single Attempt"

        self.quiz_listbox.insert(tk.END, display_text)
        self.quizzes_data.append({"url": url, "target_score": target_score})
        self.quiz_url_entry.delete(0, tk.END)
        self.quiz_target_score_entry.delete(0, tk.END)
        self._restore_target_score_placeholder(None) # Restore placeholder

    def _remove_quiz(self):
        """Removes the selected quiz from the list."""
        selected_indices = self.quiz_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Error", "Please select a quiz to remove.")
            return
        
        # Delete from listbox first, then from data list
        for index in selected_indices[::-1]: # Iterate backwards to avoid index issues
            self.quiz_listbox.delete(index)
            del self.quizzes_data[index]

    def _start_automation(self):
        """Starts the quiz automation in a separate thread."""
        global GEMINI_API_KEY # Access global variable
        GEMINI_API_KEY = self.gemini_key_entry.get().strip()
        if not GEMINI_API_KEY:
            messagebox.showerror("Configuration Error", "Please enter your Gemini API Key.")
            return

        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        selected_lms_site_name = self.lms_site_combobox.get()
        login_url = LOGIN_SITE_OPTIONS.get(selected_lms_site_name)
        selected_browser_name = self.browser_driver_combobox.get()
        driver_type = BROWSER_OPTIONS.get(selected_browser_name)
        headless = self.headless_var.get()

        if not (username and password and login_url and driver_type):
            messagebox.showerror("Input Error", "Please fill in all required login and browser details.")
            return
        if not self.quizzes_data:
            messagebox.showerror("Input Error", "Please add at least one quiz URL.")
            return

        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END) # Clear previous logs
        self.log_text.config(state="disabled")

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self._set_input_states("disabled")
        self.stop_event.clear() # Clear stop event for new run

        # Start automation in a new thread
        self.automation_thread = threading.Thread(
            target=self._run_automation_thread,
            args=(username, password, login_url, driver_type, headless, self.quizzes_data)
        )
        self.automation_thread.start()

    def _stop_automation(self):
        """Signals the automation thread to stop and cleans up."""
        self.log("Stopping automation gracefully...", "warning")
        self.stop_event.set() # Set the event to signal the thread to stop
        # Attempt to quit the driver immediately, might fail if driver is already crashed/closed
        if self.driver:
            try:
                self.driver.quit()
                self.log("Browser closed by stop command.")
            except InvalidSessionIdException:
                self.log("Browser session already closed.", "info")
            except Exception as e:
                self.log(f"Error closing browser during stop: {e}", "error")
            self.driver = None 
            self.wait = None
        self.master.after(0, lambda: self.start_button.config(state=tk.NORMAL))
        self.master.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
        self.master.after(0, lambda: self._set_input_states("normal"))
        self.log("Automation stopped.")
        messagebox.showinfo("Automation Status", "Automation Stopped: Process halted by user.")


    def _set_input_states(self, state):
        """Sets the state of input widgets."""
        self.browser_driver_combobox.config(state=state if state == "normal" else "disabled")
        self.headless_checkbox.config(state=state)
        self.lms_site_combobox.config(state=state if state == "normal" else "disabled")
        self.username_entry.config(state=state)
        self.password_entry.config(state=state)
        self.gemini_key_entry.config(state=state)
        self.quiz_url_entry.config(state=state)
        self.quiz_target_score_entry.config(state=state)
        
        # Use direct references to buttons
        self.add_quiz_button.config(state=state)
        self.remove_quiz_button.config(state=state)


    def _run_automation_thread(self, username, password, login_url, driver_type, headless, quizzes_data):
        """This function runs in a separate thread to perform the automation."""
        global driver, wait # Access global driver/wait for setup_selenium
        
        self.log("Initializing Selenium WebDriver...")
        driver, wait = self._setup_selenium(driver_type, headless)
        if not driver:
            self.log("Selenium WebDriver failed to initialize. Automation aborted.", "error")
            messagebox.showerror("Automation Error", "Selenium WebDriver failed to initialize. Please check logs.")
            self._reset_gui_state()
            return

        self.log("Attempting to log in...")
        if not self._login(username, password, login_url):
            self.log("Login failed. Automation aborted. Check logs for details (e.g., login_failure.png).", "error")
            messagebox.showerror("Login Failed", "Login Failed! Please check your credentials and network connection.")
            self._reset_gui_state()
            return

        results = {}
        for quiz_data in quizzes_data:
            if self.stop_event.is_set():
                self.log("Automation gracefully stopped by user.", "warning")
                break

            quiz_url = quiz_data["url"]
            target_score = quiz_data["target_score"]
            self.log(f"\n--- Processing quiz: {quiz_url} (Target Score: {target_score if target_score is not None else 'N/A'}) ---", "info")
            
            quiz_final_score, quiz_attempts = self._main_quiz_processor(quiz_url, target_score=target_score)
            results[quiz_url] = {"score": quiz_final_score, "attempts": quiz_attempts}
            
            # Removed individual quiz messagebox calls here
            # if quiz_final_score >= (target_score if target_score is not None else 0):
            #      messagebox.showinfo("Quiz Completed", f"Quiz Completed: {quiz_url}!\nFinal Score: {quiz_final_score} after {quiz_attempts} attempt(s).")
            # else:
            #      messagebox.showerror("Quiz Automation Error", f"Quiz Automation Error for {quiz_url}!\nFinal Score: {quiz_final_score} after {quiz_attempts} attempt(s). Target was {target_score}.")

            self.log(f"Completed processing for {quiz_url}. Result: Score={quiz_final_score}, Attempts={quiz_attempts}")
            time.sleep(2) # Short pause between quizzes

        self.log("\n" + "="*50)
        self.log("All quiz processing completed.")
        self.log("--- Final Quiz Results ---")
        final_summary_message = "All quizzes processed:\n\n" # Added extra newline for better formatting
        for url, data in results.items():
            # Formatting for the final summary message
            status = "Achieved Target" if (data['score'] >= (quizzes_data[next(i for i, q in enumerate(quizzes_data) if q['url'] == url)]['target_score'] if quizzes_data[next(i for i, q in enumerate(quizzes_data) if q['url'] == url)]['target_score'] is not None else 0)) else "Did Not Reach Target"
            if quizzes_data[next(i for i, q in enumerate(quizzes_data) if q['url'] == url)]['target_score'] is None:
                status = "Single Attempt Finished"
            
            final_summary_message += f"Quiz: {url}\n"
            final_summary_message += f"  Score: {data['score']} | Attempts: {data['attempts']}\n"
            final_summary_message += f"  Status: {status}\n\n"
            self.log(f"Quiz URL: {url}")
            self.log(f"  Final Score (Corrected Questions): {data['score']}")
            self.log(f"  Attempts Made: {data['attempts']}")
            self.log("-" * 20)
        self.log("="*50)
        
        if not self.stop_event.is_set(): # Only show final success alert if not stopped manually
            messagebox.showinfo("Automation Status: All Quizzes Completed", final_summary_message)

        self._reset_gui_state()

    def _reset_gui_state(self):
        """Resets GUI elements after automation completes or stops."""
        self.log("Cleaning up WebDriver...", "info")
        if self.driver:
            try:
                self.driver.quit()
            except InvalidSessionIdException:
                self.log("Browser session already closed during cleanup.", "info")
            except Exception as e:
                self.log(f"Error quitting driver: {e}", "error")
            self.driver = None
            self.wait = None
        
        self.master.after(0, lambda: self.start_button.config(state=tk.NORMAL))
        self.master.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
        self.master.after(0, lambda: self._set_input_states("normal"))
        self.log("WebDriver closed.")
        self.log("Automation finished.")

    # --- Selenium Helper Functions (now instance methods) ---

    def _navigate_with_retry(self, url, max_retries=3, delay=5):
        """Attempts to navigate to a URL with retry logic for network errors."""
        for attempt in range(1, max_retries + 1):
            if self.stop_event.is_set():
                self.log(f"Navigation to {url} aborted by stop command.", "warning")
                return False
            try:
                self.log(f"Navigating to {url} (Attempt {attempt}/{max_retries})...")
                self.driver.get(url)
                # Check for common error pages that might not raise an exception immediately
                if "503 Service Unavailable" in self.driver.page_source or \
                   "This site can’t be reached" in self.driver.page_source or \
                   "ERR_CONNECTION_REFUSED" in self.driver.page_source:
                    raise WebDriverException(f"Page returned a known error (e.g., 503, connection refused) for {url}")
                return True
            except (WebDriverException, requests.exceptions.ConnectionError) as e:
                self.log(f"Navigation error to {url}: {e}. Retrying in {delay} seconds...", "warning")
                if attempt < max_retries:
                    time.sleep(delay)
                else:
                    self.log(f"Max retries reached for navigation to {url}.", "error")
                    self.driver.save_screenshot(f"navigation_failure_{url.replace('https://', '').replace('/', '_')}.png")
                    return False
            except Exception as e:
                self.log(f"An unexpected error occurred during navigation to {url}: {e}", "error")
                return False
        return False


    def _setup_selenium(self, driver_type, headless_mode):
        """Initializes and returns the WebDriver and WebDriverWait objects based on driver_type."""
        self.log(f"Initializing WebDriver ({driver_type.capitalize()} {'Headless' if headless_mode else 'Visible'} mode)...")
        
        options = None
        if driver_type in ["chrome", "edge", "firefox"]:
            if driver_type == "chrome":
                options = webdriver.ChromeOptions()
            elif driver_type == "edge":
                options = webdriver.EdgeOptions()
            elif driver_type == "firefox":
                options = webdriver.FirefoxOptions()
            
            if headless_mode:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--log-level=3")
            options.add_argument("--window-size=1920,1080") # Set a default window size for headless

        try:
            if driver_type == "chrome":
                service = ChromeService(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=options)
            elif driver_type == "firefox":
                service = FirefoxService(GeckoDriverManager().install())
                self.driver = webdriver.Firefox(service=service, options=options)
            elif driver_type == "edge":
                service = EdgeService(EdgeChromiumDriverManager().install())
                self.driver = webdriver.Edge(service=service, options=options)
            elif driver_type == "safari":
                if headless_mode:
                    self.log("Safari does not support headless mode via Selenium. Running in visible mode.", "warning")
                self.driver = webdriver.Safari()
            else:
                self.log(f"Unsupported driver type: {driver_type}", "error")
                return None, None

            self.wait = WebDriverWait(self.driver, 60) # Increased wait time
            if not headless_mode:
                self.driver.maximize_window()
            self.log(f"WebDriver for {driver_type.capitalize()} initialized successfully.")
            return self.driver, self.wait
        except WebDriverException as e:
            self.log(f"Failed to initialize WebDriver for {driver_type}: {e}", "error")
            self.log(f"Please ensure {driver_type.capitalize()} browser is installed and up-to-date.", "error")
            self.log(f"Also, confirm that the corresponding WebDriver ({driver_type}driver, geckodriver) is compatible with your browser version and is in your system's PATH, or handled by webdriver_manager.", "error")
            return None, None
        except Exception as e:
            self.log(f"An unexpected error occurred during {driver_type} WebDriver setup: {e}", "error")
            return None, None

    def _login(self, username, password, login_url):
        """Handles the login process."""
        if self.stop_event.is_set(): return False
        self.log(f"Attempting to navigate to login page: {login_url}")
        if not self._navigate_with_retry(login_url):
            self.log("Failed to load login page after multiple retries.", "error")
            return False

        try:
            # Check if already logged in (e.g., redirected away from login page)
            if "login" not in self.driver.current_url.lower():
                self.log("Already logged in or redirected successfully.")
                return True

            username_field = self.wait.until(EC.visibility_of_element_located((By.ID, 'username')))
            password_field = self.wait.until(EC.visibility_of_element_located((By.ID, 'password')))
            login_button = self.wait.until(EC.element_to_be_clickable((By.ID, 'loginbtn')))
            
            username_field.send_keys(username)
            password_field.send_keys(password)
            login_button.click()
            self.log("Login button clicked.")
            
            self.wait.until(EC.url_changes(login_url) or EC.presence_of_element_located((By.CLASS_NAME, 'alert-danger')))

            if "login" in self.driver.current_url.lower():
                self.log("Login failed after submission. Check username/password.", "error")
                self.driver.save_screenshot("login_failure.png")
                with open("login_page_source_error.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                return False
            else:
                self.log("Login successful.")
                return True
                
        except TimeoutException:
            self.log("Timeout during login. Required page elements not found or page did not load in time.", "error")
            self.driver.save_screenshot("login_timeout.png")
            with open("login_page_source_error.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            return False
        except Exception as e:
            self.log(f"An unexpected error occurred during login process: {e}", "error")
            self.driver.save_screenshot("login_error.png")
            with open("login_page_source_error.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            return False

    def _get_quiz_details(self, quiz_url, max_attempts=3):
        """
        Navigates to the quiz URL and attempts to start or continue the quiz.
        Returns True if quiz is successfully started/continued, False otherwise.
        """
        if self.stop_event.is_set(): return False
        self.log(f"Attempting to navigate to quiz page: {quiz_url}")
        if not self._navigate_with_retry(quiz_url):
            self.log("Failed to load quiz page after multiple retries.", "error")
            return False
        
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "page-header-headings")))
            self.log("Arrived at quiz page.")
        except TimeoutException:
            self.log(f"Timeout reaching quiz page: {quiz_url}. Page did not load.", "error")
            self.driver.save_screenshot("quiz_page_load_timeout.png")
            return False
        except Exception as e:
            self.log(f"Error navigating to quiz URL {quiz_url}: {e}", "error")
            self.driver.save_screenshot("quiz_url_navigation_error.png")
            return False

        for attempt in range(1, max_attempts + 1):
            if self.stop_event.is_set(): return False
            self.log(f"Attempt {attempt}/{max_attempts} to start or continue quiz...")
            try:
                try:
                    question_element = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "qtext"))
                    )
                    self.log("Quiz already in progress, proceeding to questions.")
                    return True
                except TimeoutException:
                    self.log("Not currently on a question page, looking for quiz start/continue buttons.")
                    quiz_button_xpath = (
                        "//button[contains(text(),'Attempt quiz') or contains(text(),'Re-attempt quiz') or contains(text(),'Continue your attempt')] | "
                        "//input[contains(@value,'Attempt quiz') or contains(@value,'Re-attempt quiz') or contains(@value,'Continue your attempt')]"
                    )
                    quiz_button = self.wait.until(EC.element_to_be_clickable((By.XPATH, quiz_button_xpath)))
                    self.driver.execute_script("arguments[0].click();", quiz_button)
                    self.log("Clicked quiz start/continue button.")
                    time.sleep(3)
                    
                    try:
                        start_attempt_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Start attempt')] | //input[contains(@value,'Start attempt')]"))
                        )
                        self.driver.execute_script("arguments[0].click();", start_attempt_button)
                        self.log("Clicked 'Start attempt' confirmation button.")
                        time.sleep(3)
                        
                        self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                        self.log("Quiz started successfully.")
                        return True
                    except TimeoutException:
                        self.log("No 'Start attempt' confirmation button found or not needed. Checking for question text directly.", "warning")
                        try:
                            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                            self.log("Quiz started successfully without explicit 'Start attempt' confirmation.")
                            return True
                        except TimeoutException:
                            self.log("Quiz did not start, 'qtext' element not found after clicking initial button.", "error")
                            self.driver.save_screenshot(f"quiz_start_fail_attempt_{attempt}.png")
                    except Exception as start_e:
                        self.log(f"An error occurred with 'Start attempt' button: {start_e}", "error")
                        self.driver.save_screenshot(f"quiz_start_button_error_attempt_{attempt}.png")
            except TimeoutException:
                self.log(f"Quiz start/continue button not found on attempt {attempt}.", "warning")
                self.driver.save_screenshot(f"quiz_start_button_timeout_attempt_{attempt}.png")
                try:
                    self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")))
                    self.log("Quiz already in progress, proceeding.")
                    return True
                except TimeoutException:
                    self.log("No question found, quiz likely not active or finished.", "warning")
                    self.driver.save_screenshot(f"quiz_start_no_qtext_attempt_{attempt}.png")
            except Exception as e:
                self.log(f"An unexpected error occurred during quiz start/continue: {e}", "error")
                self.driver.save_screenshot(f"quiz_start_general_error_attempt_{attempt}.png")
            
            if attempt < max_attempts:
                self.log("Retrying quiz start/continue in 2 seconds...")
                time.sleep(2)
            else:
                self.log(f"Max attempts ({max_attempts}) reached for quiz start/continue. Saving page source for debugging.", "error")
                with open("quiz_start_final_page_source.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
        return False

    def _process_single_question(self, question_number):
        """
        Extracts question and options, asks Gemini, clicks the answer, and moves to next page.
        Returns True if successful, False otherwise (e.g., if submission buttons are found).
        """
        if self.stop_event.is_set(): return False
        try:
            question_element = self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "qtext")))
            answer_block_element = self.wait.until(EC.visibility_of_element_located((By.CLASS_NAME, "answer")))
            
            question_text = question_element.text.strip()
            self.log(f"Processing Question {question_number}...")
            
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
                    if label_id and (label_div := soup.find(id=label_id)):
                        label_text = label_div.get_text(strip=True)
                    elif soup.find('label', {'for': option_id}):
                        label_text = soup.find('label', {'for': option_id}).get_text(strip=True)
                    elif inp.find_next_sibling('label'):
                        label_text = " ".join(inp.find_next_sibling('label').get_text(strip=True).split())
                    
                    if label_text:
                        option_texts.append(label_text)
                        try:
                            selenium_radio = self.driver.find_element(By.ID, option_id)
                            radio_elements.append(selenium_radio)
                        except NoSuchElementException as sel_e:
                            self.log(f"Could not find Selenium element for ID '{option_id}': {sel_e}", "error")
                            option_texts.pop()
                            continue
            
            if not option_texts or len(option_texts) != len(radio_elements):
                self.log("Warning: Failed to parse options or link to Selenium elements correctly for current question.", "warning")
                return False
                
            model_answer_letter = ask_gemini(question_text, option_texts, self.log)
            self.log(f"Gemini chose: '{model_answer_letter}' for Q{question_number}.")
            
            clicked = False
            if model_answer_letter and model_answer_letter in 'abcd'[:len(option_texts)]:
                try:
                    answer_index = ord(model_answer_letter) - ord('a')
                    if 0 <= answer_index < len(radio_elements):
                        target_element = radio_elements[answer_index]
                        self.wait.until(EC.element_to_be_clickable(target_element))
                        self.driver.execute_script("arguments[0].click();", target_element)
                        self.log(f"Clicked option {model_answer_letter} for Q{question_number}.")
                        clicked = True
                    else:
                        self.log(f"Letter '{model_answer_letter}' out of bounds for options for Q{question_number}.", "warning")
                except Exception as click_e:
                    self.log(f"Error clicking option {model_answer_letter} for Q{question_number}: {click_e}", "error")
            
            if not clicked:
                self.log(f"Could not click an option for question {question_number}. Proceeding.", "warning")
                self.driver.save_screenshot(f"question_{question_number}_no_click.png")

            try:
                next_xpath = "//input[@value='Next page'] | //button[contains(text(), 'Next page')]"
                next_btn = WebDriverWait(self.driver, 5).until(EC.element_to_be_clickable((By.XPATH, next_xpath)))
                self.driver.execute_script("arguments[0].click();", next_btn)
                self.log("Clicked 'Next page'.")
                self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "qtext")) or EC.presence_of_element_located((By.XPATH, "//input[@value='Finish attempt ...']")))
                time.sleep(1)
                return True
            except TimeoutException:
                self.log("No 'Next page' button found. Assuming last question or navigation issue.", "info")
                return False 
            except Exception as nav_e:
                self.log(f"Error navigating to next page: {nav_e}", "error")
                self.driver.save_screenshot(f"question_{question_number}_navigation_error.png")
                return False

        except TimeoutException:
            self.log(f"Timeout: Question or answer block not found on current page for Q{question_number}.", "warning")
            return False
        except Exception as e:
            self.log(f"Error processing question {question_number}: {e}", "error")
            self.driver.save_screenshot(f"question_{question_number}_processing_error.png")
            return False

    def _submit_quiz(self):
        """
        Handles the sequence of submitting the quiz and finishing the review.
        Returns True on successful submission, False otherwise.
        """
        if self.stop_event.is_set(): return False
        self.log("Attempting to submit quiz...")
        try:
            finish_attempt_xpath = "//input[@value='Finish attempt ...' and @name='next' and @id='mod_quiz-next-nav']"
            finish_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, finish_attempt_xpath)))
            self.log("Found 'Finish attempt ...' button, clicking.")
            self.driver.execute_script("arguments[0].click();", finish_btn)
            time.sleep(2)

            submit_all_xpath1 = "//button[@type='submit' and contains(text(), 'Submit all and finish')] | //input[@type='submit' and contains(@value, 'Submit all and finish')]"
            submit_all_btn1 = self.wait.until(EC.element_to_be_clickable((By.XPATH, submit_all_xpath1)))
            self.log("Found first 'Submit all and finish' button, clicking.")
            self.driver.execute_script("arguments[0].click();", submit_all_btn1)
            time.sleep(2)

            submit_all_xpath2 = "//button[@type='button' and @data-action='save' and contains(text(), 'Submit all and finish')] | //input[@type='submit' and contains(@value, 'Submit all and finish')]"
            submit_all_btn2 = self.wait.until(EC.element_to_be_clickable((By.XPATH, submit_all_xpath2)))
            self.log("Found second 'Submit all and finish' button, clicking.")
            self.driver.execute_script("arguments[0].click();", submit_all_btn2)
            time.sleep(5)

            finish_review_xpath = "//a[@class='mod_quiz-next-nav' and contains(text(), 'Finish review')]"
            finish_review_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, finish_review_xpath)))
            self.log("Found 'Finish review' link, clicking.")
            self.driver.execute_script("arguments[0].click();", finish_review_btn)
            time.sleep(3)

            self.log("Quiz submission sequence completed successfully.")
            return True
        except TimeoutException:
            self.log("Timeout during quiz submission sequence. Some buttons/links not found.", "error")
            self.driver.save_screenshot("quiz_submission_timeout.png")
            with open("submit_page_source_timeout.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            return False
        except Exception as e:
            self.log(f"An error occurred during quiz submission: {e}", "error")
            self.driver.save_screenshot("quiz_submission_error.png")
            with open("submit_page_source_error.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            return False

    def _get_current_score(self):
        """
        Extracts the current score (corrected questions count) from the quiz overview page.
        It now specifically targets the 'cell c2' of the last row (most recent attempt).
        """
        if self.stop_event.is_set(): return 0.0
        self.log("Attempting to get current score (corrected questions count) from last attempt...")
        try:
            self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'quizattemptsummary')))
            time.sleep(1) # Give a moment for the new row to render in the DOM

            last_row_element = self.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, "//table[contains(@class, 'quizattemptsummary')]/tbody/tr[last()]")
                )
            )
            # self.log(f"Found last attempt row HTML: {last_row_element.get_attribute('outerHTML')[:200]}...") # Keep for deep debugging if needed

            score_element = last_row_element.find_element(By.XPATH, "./td[contains(@class, 'c2')]")
            
            score_text = score_element.text.strip()
            self.log(f"Raw corrected questions text found: '{score_text}' from last row.")

            match = re.search(r'(\d+\.?\d*)', score_text)
            if match:
                score = float(match.group(1))
                self.log(f"Parsed corrected questions count: {score}")
                return score
            else:
                self.log(f"Could not parse numeric score from text: '{score_text}'.", "warning")
                self.driver.save_screenshot("corrected_score_parsing_failure.png")
                return 0.0
                
        except TimeoutException:
            self.log("Timeout: Could not find corrected questions score element (last row, cell c2) on the page.", "error")
            self.driver.save_screenshot("corrected_score_element_timeout.png")
            with open("score_page_source_timeout.html", "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            return 0.0
        except Exception as e:
            self.log(f"An error occurred while getting the corrected questions count from the last row: {e}", "error")
            self.driver.save_screenshot("corrected_score_general_error.png")
            return 0.0

    def _main_quiz_processor(self, quiz_url, target_score=None, max_attempts=5):
        """
        Processes a single quiz, including retries if a target score is specified.
        Returns (final_score, total_attempts) for the quiz.
        """
        self.log(f"\n{'='*50}\nStarting processing for quiz: {quiz_url}\n{'='*50}", "info")
        
        attempts_made = 0
        final_score = 0.0
        quiz_status_message = ""
        quiz_success = False

        while attempts_made < max_attempts:
            if self.stop_event.is_set():
                quiz_status_message = "Automation stopped by user during quiz."
                break
            attempts_made += 1
            self.log(f"--- Starting attempt {attempts_made}/{max_attempts} for quiz: {quiz_url} ---")
            
            if not self._get_quiz_details(quiz_url):
                self.log(f"Failed to start/continue quiz at {quiz_url}. Skipping further attempts for this quiz.", "error")
                quiz_status_message = f"Failed to start/continue quiz."
                break
                
            question_count = 0
            quiz_questions_answered = False
            while True:
                if self.stop_event.is_set():
                    quiz_status_message = "Automation stopped by user during quiz questions."
                    break
                try:
                    question_element_on_page = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "qtext"))
                    )
                    
                    if question_element_on_page:
                        question_count += 1
                        if not self._process_single_question(question_count):
                            self.log("Failed to process question, checking for submission buttons.", "warning")
                            quiz_questions_answered = True # Assume current page questions handled, move to submission logic
                            break
                    else:
                        self.log("No more question text elements found. Proceeding to submission check.", "info")
                        quiz_questions_answered = True
                        break
                except TimeoutException:
                    self.log("No question element found on current page within timeout. Assuming end of quiz questions.", "info")
                    quiz_questions_answered = True
                    break
                except Exception as e:
                    self.log(f"An unexpected error occurred during question processing loop: {e}", "error")
                    self.driver.save_screenshot(f"question_loop_error_page_{question_count}.png")
                    quiz_questions_answered = False
                    quiz_status_message = "Error during question processing."
                    break
            
            if self.stop_event.is_set(): break # Check stop event after inner loop
            if not quiz_questions_answered and not self.stop_event.is_set():
                self.log("Quiz questions were not fully answered due to an error. Abandoning current attempt.", "error")
                quiz_status_message = "Quiz questions incomplete due to an error."
                break

            if not self._submit_quiz():
                self.log(f"Failed to submit quiz successfully on attempt {attempts_made}. Skipping further attempts for this quiz.", "error")
                quiz_status_message = "Failed to submit quiz."
                break
                
            current_score = self._get_current_score()
            final_score = current_score
            
            self.log(f"Attempt {attempts_made} finished. Score: {current_score}")

            if target_score is None:
                quiz_status_message = "Finished single attempt."
                quiz_success = True
                break
            elif current_score >= target_score:
                quiz_status_message = f"Target score ({target_score}) achieved or surpassed! Score: {current_score}"
                quiz_success = True
                break
            else:
                self.log(f"Target score ({target_score}) not met. Current score: {current_score}. Retrying...", "warning")
                quiz_status_message = f"Target score ({target_score}) not met. Retrying..."
        
        self.log(f"\nFinished processing quiz {quiz_url}. Final Score: {final_score} after {attempts_made} attempt(s).")
        return final_score, attempts_made


# --- Main Application Execution ---
if __name__ == "__main__":
    root = tk.Tk()
    app = QuizAutomationApp(root)
    root.mainloop()

