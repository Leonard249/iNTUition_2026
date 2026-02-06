# iNTUition_2026 startup

# Backend Setup

cd backend
uv sync
ollama pull qwen2.5vl:7b
ollama serve
uv run run.py

# Backend Testing (Optional)

uv run test_api.py

# Frontend Setup

cd frontend

# 1. Download required library (run this command inside frontend folder)

curl -L -o html2canvas.min.js https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js

# 2. Install in Chrome

# a. Open chrome://extensions

# b. Toggle "Developer mode" (top right)

# c. Click "Load unpacked"

# d. Select the 'frontend' folder

# Usage

# 1. Open a website (e.g. Shopee)

# 2. Click Extension Icon -> Analyze Page

# 3. Use Microphone to speak commands
