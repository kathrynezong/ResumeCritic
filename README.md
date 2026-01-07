# ResumeCritic

**AI-Powered Resume Analysis Platform**

ResumeCritic is a full-stack web application that analyzes resumes against job descriptions using multiple AI-powered techniques: semantic similarity analysis, keyword matching, and Google Gemini AI evaluation. The project uses a **FastAPI** backend and a **Next.js (TypeScript)** frontend to deliver an interactive experience for users looking to optimize their resumes.

---

## Features

- **Multi-Method Analysis:** Combines semantic similarity, keyword matching, and AI-powered evaluation for comprehensive resume analysis
- **Smart Keyword Extraction:** Extracts technical keywords only from requirement sections (requirements, must-haves, nice-to-haves, etc.) using a comprehensive whitelist of technical terms
- **Semantic Similarity Scoring:** Uses sentence transformers (all-MiniLM-L6-v2) to understand meaning beyond exact keyword matches
- **AI-Powered Insights:** Google Gemini AI provides detailed analysis including:
  - Technical skills match scoring
  - Experience level assessment
  - Education and qualifications evaluation
  - Domain knowledge analysis
  - Strengths and improvement areas
  - Overall recommendation (STRONG_MATCH, GOOD_MATCH, PARTIAL_MATCH, WEAK_MATCH)
- **PDF Support:** Extracts text from PDF resumes using pdfplumber
- **OR Group Handling:** Intelligently handles alternative requirements (e.g., "Python or Java")
- **Weighted Scoring:** Requirements sections weighted 3x more important than nice-to-have sections
- **Modern UI:** Clean, responsive interface built with TailwindCSS and TypeScript
- **Theme Support:** Dark/light mode toggle using `next-themes`

---

## Setup Guide

This guide will help you get both the backend and frontend running.

### Prerequisites

- Python 3.9+ installed
- Node.js and npm installed
- Google Gemini API key (optional, for AI analysis - get one at https://makersuite.google.com/app/apikey)

## Step 1: Backend Setup

### 1.1 Navigate to backend directory
```bash
cd backend
```

### 1.2 Activate virtual environment (if you have one)
On Windows:
```bash
venv\Scripts\activate
```

On Mac/Linux:
```bash
source venv/bin/activate
```

### 1.3 Install dependencies
```bash
pip install -r requirements.txt
```

### 1.4 Start the backend server
```bash
uvicorn app.main:app --reload --port 8000
```

You should see output like:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Keep this terminal window open!** The backend needs to keep running.

## Step 2: Frontend Setup

### 2.1 Open a NEW terminal window
(Keep the backend terminal running)

### 2.2 Navigate to frontend directory
```bash
cd frontend
```

### 2.3 Install dependencies (if not already done)
```bash
npm install
```

### 2.4 Start the frontend development server
```bash
npm run dev
```

You should see output like:
```
- ready started server on 0.0.0.0:3000
```

## Step 3: View the Application

Open your browser and go to:
**http://localhost:3000**

You should see the ResumeCritic interface!

## Restarting the Backend

If you need to restart the backend:

1. **Stop the server**: In the backend terminal, press `Ctrl+C`
2. **Start it again**: Run `uvicorn app.main:app --reload --port 8000`

The `--reload` flag means the server will automatically restart when you make code changes.

## Troubleshooting

### Backend won't start
- Make sure you're in the `backend` directory
- Check that your virtual environment is activated
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Make sure port 8000 is not already in use

### Frontend won't start
- Make sure you're in the `frontend` directory
- Try deleting `node_modules` and running `npm install` again
- Check that port 3000 is not already in use

### API connection errors
- Make sure the backend is running on port 8000
- Check that the `.env` file exists in the `backend` directory with your `GEMINI_API_KEY`
- If Gemini API is not configured, the app will still work but AI analysis will be disabled

## Quick Commands Reference

**Backend:**
```bash
cd backend
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Mac/Linux
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm run dev
```

**View app:**
- Open http://localhost:3000 in your browser

---

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Uvicorn** - ASGI server
- **sentence-transformers** - Semantic similarity using all-MiniLM-L6-v2 model
- **scikit-learn** - Cosine similarity calculations
- **pdfplumber** - PDF text extraction
- **google-genai** - Google Gemini AI integration
- **numpy** - Numerical operations

### Frontend
- **Next.js 16** - React framework with server-side rendering
- **React 19** - UI library
- **TypeScript** - Type-safe JavaScript
- **TailwindCSS 4** - Utility-first CSS framework
- **next-themes** - Theme management

### AI & NLP
- **Sentence Transformers** - For semantic similarity analysis
- **Google Gemini** - For comprehensive resume evaluation and insights
- **Rule-based Keyword Matching** - Technical keyword extraction from requirement sections

---

## Demo

![ResumeCritic Demo](images/demo.png)

