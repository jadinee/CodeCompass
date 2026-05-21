# CodeCompass 🧭
> Move Beyond Tutorials. Learn Through Building.

## What It Does
CodeCompass is an AI mentor that helps you understand what you built with AI tools. Drop a GitHub URL or paste your code, and CodeCompass analyzes your project, identifies your knowledge gaps, and gives you a personalized learning path.

## How It Works
1. User sends a GitHub repo or code to the Discord bot
2. RocketRide pipeline runs 3 AI steps:
   - **Step 1:** Analyze the project
   - **Step 2:** Identify knowledge gaps
   - **Step 3:** Generate personalized learning guide
3. Bot responds with a mentor-style breakdown

## Tech Stack
- **AI:** Claude (Anthropic) via 3-step RocketRide pipeline
- **Messaging:** Discord bot (Photon Spectrum)
- **Pipeline:** RocketRide visual workflow (VS Code)
- **GitHub Fetching:** GitHub API

## Setup
1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your keys
3. Run `pip install -r requirements.txt`
4. Start the RocketRide pipeline in VS Code
5. Run `python3 bot.py`

## Demo
Type `!analyze https://github.com/yourname/yourrepo` in Discord to get started.

## Built At
HackWithSeattle 2026
