# 🧠 ATLAS MCQ Assistant

ATLAS MCQ Assistant is an AI-powered realtime multiple-choice question (MCQ) solver and learning companion designed for students preparing for technical interviews, coding rounds, and practice assessments.

It captures your screen or processes uploaded screenshots, extracts the question details through OCR, and presents the correct answer option, subject topic, a confidence rating, and a clear step-by-step reasoning via OpenAI's GPT-4.1-mini.

---

## 🚀 Key Features

* **Realtime Screen Share Analysis**: Continuously grab frames from any browser tab or window (using Web Media Stream) to process new questions immediately.
* **Auto-Capture Timer Mode**: Auto-capture screen every 5 seconds for a completely hands-free experience.
* **Dual OCR/Vision Pipeline**: Uses Tesseract locally for low-latency text parsing, falling back automatically to high-accuracy GPT Vision if text elements are blurry.
* **Topic Classification**: Auto-classifies questions into DSA, Database Management (DBMS), Computer Networks (CN), Operating Systems (OS), React, Java, Spring Boot, System Design, or Aptitude.
* **Modern Dark UI**: Fluid dark dashboard with beautiful HSL indigo color highlights, smooth slide-up card transitions, and glowing visual metrics.

---

## 🛠️ Architecture

* **Frontend**: React (Vite) + Tailwind CSS (v3) + WebSockets
* **Backend**: FastAPI + Uvicorn + WebSockets
* **OCR**: Tesseract OCR / PIL Image Preprocessing
* **AI Model**: OpenAI `gpt-4.1-mini` (Vision and JSON mode)
* **Database**: SQLite with `aiosqlite` async connection pool

---

## ⚡ Quick Start

### 1. Requirements
* Install **Python 3.10+** and **Node.js 18+**.
* Install Tesseract OCR:
  * **Windows**: Download UB Mannheim installer. Install to `C:\Program Files\Tesseract-OCR\tesseract.exe`.
  * **Mac/Linux**: Install using Homebrew/apt: `brew install tesseract` / `sudo apt-get install tesseract-ocr`.

### 2. Startup Backend Server
```bash
cd backend
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env # Add your OPENAI_API_KEY in .env

uvicorn app.main:app --reload --port 8000
```

### 3. Startup Frontend Client
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

### 4. Startup Transparent Electron Overlay (On Top Layer)
To launch the app as a floating, transparent companion dashboard that sits always on top of your practice quiz or browser windows:
```bash
# In a separate terminal inside the frontend folder
npm run electron
```
* **Always-On-Top Layer**: Keeps the overlay on top of proctored exam windows or browsers.
* **Draggable Window**: Grab the header "Companion overlay" to reposition the widget anywhere.
* **Window Controls**: Customize top bar settings (Minimize, Pin / Unpin Always-on-Top, Close).
