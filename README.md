# ResumeCritic - Setup Guide

This guide will help you get both the backend and frontend running.

## Prerequisites

- Python 3.9+ installed
- Node.js and npm installed

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

### 1.4 Download spaCy language model (if not already installed)
```bash
python -m spacy download en_core_web_sm
```

### 1.5 Start the backend server
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
- Verify that spaCy model is installed: `python -m spacy download en_core_web_sm`

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

