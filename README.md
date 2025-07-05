
🤖 Bot for Moodle Activities (Saveetha LMS Automation)
This project is a smart automation bot built using Python, Selenium, and Google Gemini AI. It automates various routine activities on Saveetha Moodle LMS  such as quizzes, SOLO speaking tasks, and read-aloud exercises.

Instead of manually doing repetitive LMS work, the bot does everything for you — faster, smarter, and with the help of AI.

🧩 Activities Automated by the Bot
1. 🎯 Quiz Automation (quiz_automator.py)
Logs into your LMS account.

Opens quizzes one by one.

Uses Gemini AI to read and understand each question.

Automatically selects the most suitable answer.

Submits the quiz.

If a target score is set, it will retry until it reaches that score.

Comes with a GUI interface — no coding needed to run it.

✅ Saves hours when you have lots of quizzes to complete.

2. 🗣️ SOLO Speaking Task Automation (read.py)
Logs into Moodle and opens the SOLO speaking activity.

Extracts the topic and target words.

Uses Gemini AI to generate a meaningful short speech (100–120 words).

Uses a text-to-speech engine (pyttsx3) to speak the response aloud.

Records the spoken text using VB-Audio Cable.

Submits the audio and transcript automatically.

🎓 Saves your voice and effort while delivering high-quality, AI-generated content.

3. 📖 Read Aloud Task Automation (readaloud.py)
Logs into Moodle and opens the “Read Aloud” activity.

Extracts the passage you need to read.

Speaks it out loud using AI voice (Text-to-Speech).

Starts and stops the recording automatically.

Submits the task.

🧑‍🎓 Perfect for completing read-alouds, even if you're in a noisy environment or feeling tired.

🎙️ How to Use VB-Audio Cable (For read.py & readaloud.py)
To complete speaking tasks, the bot must record AI-generated speech into Moodle's microphone-based recorder. This is done using VB-Audio Cable, which acts like a virtual mic.

🔧 What is VB-Audio Cable?
It's a tool that allows your system’s speaker output (TTS voice) to be used as microphone input — essential for automated recording.

✅ Steps to Install
Download from: https://vb-audio.com/Cable/

Extract and install it as Administrator.

Restart your system.

🎤 Set as Default Microphone
Go to Control Panel → Sound → Recording tab.

Set VB-Audio Cable as the default microphone.

Now, when the bot plays speech, Moodle will think you’re speaking!

🧪 Built-in Check
Both read.py and readaloud.py:

Check if VB-Audio Cable is installed.

Test audio routing automatically.

Fall back to your physical mic (with a warning) if VB-Cable is not available.

💡 Why I Built This Project
Main Goal: Save time and use that time for upskilling.

Instead of spending hours doing the same LMS tasks — which students often complete with ChatGPT or other tools anyway — I built a smart bot to automate everything using Python and AI.

This helped me:

Complete my tasks efficiently.

Learn real-world skills (Selenium, Gemini API, GUI in Python).

Build a meaningful personal project.

🙏 My Honest Intent
This project is built:

✅ For personal productivity and learning.

✅ To reduce repetitive effort and invest that time in learning new things.

✅ As a showcase project — not to break any academic rules.

⚠️ I want to make it very clear:

I respect my college and its systems.

I am not doing this against the college.

This bot is only used for my own tasks, and not for misuse.

I’ve just built a tool to help me work smarter, not to cheat or bypass learning.

👨‍💻 Who Can Use This?
Saveetha University students on LMS (AI / CSE / EEE).

Students who use AI tools like ChatGPT or Gemini already.

Anyone who wants to explore Python, automation, and real-world AI integration.

Developers looking for a project that combines AI + Selenium + TTS.

🏁 Final Note
If you're someone who:

Wants to save time ⏳

Believes in upskilling daily 💪

Uses AI smartly and responsibly 🧠

Loves building cool projects 🚀

Then you’ll find this project useful and inspiring.
