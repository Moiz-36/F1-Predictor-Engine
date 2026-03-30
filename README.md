This is a live race dashboard built using vibe coding. Instead of spending weeks on manual boilerplate, I teamed up with Gemini to ship a functional, high-quality predictive engine in record time. It’s about building at the speed of thought.

✨ The Vibe
AI-Augmented: Built with a "human-in-the-loop" approach to move fast and focus on the logic rather than the syntax.

Real-Time: Pulls live data from the OpenF1 API every 5 seconds.

Smart Scoring: Uses a weighted model to calculate who’s actually winning, accounting for tyre age, pit stops, and safety cars.

🚀 Quick Start
Install dependencies:

Bash
pip install flask requests
Run the engine:

Bash
python app.py
Open the cockpit: Go to http://127.0.0.1:5000 in your browser.

Enter a Session: Use 9158 (Bahrain 2023) or a 2026 China GP key to see it in action.

🛠️ How It Works
Data: Fetches telemetry, lap times, and race control messages.

Logic: A Python backend calculates win probability based on track position, tyre degradation, and historical pace.

UI: A modern dashboard with animated probability bars and live status indicators for Safety Cars or Red Flags.

🏁 Why This Way?
I built this to show that coding is changing. By using AI as an engineering partner, I can focus on the strategy of the race model while the AI ensures the execution is solid and fast.
