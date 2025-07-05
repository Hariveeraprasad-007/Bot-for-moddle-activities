# 🤖 Bot for Moodle Activities (Saveetha LMS Automation)

This project is a **smart automation bot** built using Python, Selenium, and Google Gemini AI. It automates various routine activities on **Saveetha Moodle LMS** such as quizzes, SOLO speaking tasks, and read-aloud exercises.

Instead of manually doing repetitive LMS work, the bot does everything for you — faster, smarter, and with the help of AI.

---

## 🧩 Activities Automated by the Bot

### 🎯 1. Quiz Automation (`quiz_automator.py`)

- Logs into your LMS account using your credentials.
- Opens quizzes one by one and reads the questions.
- Uses **Google Gemini AI** to understand and select the correct answers.
- Automatically clicks the correct options and submits the quiz.
- Supports **target scores** — the bot can retry until the desired score is achieved.
- Comes with a **GUI interface** — no code editing needed.

> ✅ Saves hours when you have multiple quizzes to complete.

---

### 🗣️ 2. SOLO Speaking Task Automation (`read.py`)

- Logs into Moodle and opens the SOLO speaking activity.
- Extracts the **topic** and **target words**.
- Uses **Gemini AI** to generate a meaningful short speech (100–120 words).
- Uses a text-to-speech engine (`pyttsx3`) to speak the response.
- Records the audio using **VB-Audio Cable**.
- Submits the audio and transcript automatically.

> 🎓 Saves your voice and effort while delivering high-quality, AI-generated responses.

---

### 📖 3. Read Aloud Task Automation (`readaloud.py`)

- Logs into Moodle and opens the “Read Aloud” activity.
- Extracts the passage you need to read.
- Converts the passage into human-like speech using TTS.
- Starts and stops the recording automatically.
- Submits the activity.

> 🧑‍🎓 Perfect for completing read-alouds in noisy or busy environments.

---

## 🎙️ How to Use VB-Audio Cable (for `read.py` and `readaloud.py`)

### 🔧 What is VB-Audio Cable?

**VB-Audio Cable** is a virtual audio device that allows your system’s speaker output (AI-generated voice) to be used as microphone input — essential for automating speaking tasks on Moodle.

### ✅ Installation Steps

1. Download from: [https://vb-audio.com/Cable/](https://vb-audio.com/Cable/)
2. Extract the ZIP file.
3. Run `VBCABLE_Setup.exe` or `VBCABLE_Setup_x64.exe` as Administrator.
4. Click **Install Driver**.
5. Restart your system.

### 🎤 Set as Default Microphone

- Go to `Control Panel → Sound → Recording tab`.
- Set **VB-Audio Cable** as your **default microphone**.
- Keep your regular speakers as the default playback device.

Now when the bot speaks using TTS, Moodle will think you’re speaking through a mic!

### 🧪 Built-in Audio Test

Both `read.py` and `readaloud.py`:
- Automatically detect VB-Audio Cable.
- Test the audio routing.
- Warn and fall back to your physical mic if VB is not available.

---

## 💡 Why I Built This Project

> **Main Goal:** Save time and use that time for **upskilling**.

Instead of spending hours doing LMS tasks — which many students already use ChatGPT or Gemini for — I built this bot to **automate it smartly** and learn real-world tech skills.

This helped me:
- Complete tasks efficiently.
- Learn Selenium, AI API usage, and GUI programming.
- Build a strong personal project for my portfolio.

---

## 🙏 My Honest Intent

This bot was created:
- ✅ For personal use and learning purposes.
- ✅ To reduce repetitive effort and focus more on skill development.
- ✅ As a self-made tech project — **not for breaking rules**.

> ⚠️ I want to clearly state:
- I **respect my college** and its systems.
- This project is **not built to harm, cheat, or bypass** any academic responsibilities.
- It is meant to automate **already AI-assisted work**, using smart methods.

---

## 👨‍💻 Who Can Use This?

- Students at **Saveetha University** using LMS (AI, CSE, EEE).
- Anyone who already uses AI tools for LMS tasks.
- Developers learning Selenium, automation, and Gemini API.
- People looking to save time and upskill faster.

---

## 🏁 Final Note

If you're someone who:

- ⏳ Wants to save time  
- 💪 Believes in upskilling daily  
- 🧠 Uses AI smartly and responsibly  
- 🚀 Loves building useful projects  

Then this bot is something you'll find **powerful and inspiring**.

---

> Feel free to star ⭐ the repo if this project helped you — and fork it to build your own!

