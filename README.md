# Life Scouter

## Overview
Life Scouter is an AI-powered personal assistant built on LangGraph, featuring a decoupled Next.js 16 frontend and FastAPI backend with a two-level supervisor architecture.

## Setup Instructions

### Environment Setup
1. Copy `.env.example` to `.env`
2. Fill in your API keys (Gemini, Tavily) in the `.env` file.

### Running with Docker (Recommended)
You can run the entire application using Docker Compose:
```bash
docker-compose up --build
```
- The Next.js frontend will be available at `http://localhost:3000`.
- The FastAPI backend will be available at `http://localhost:8000` (docs at `/docs`).

### Local Development
To run the services locally without Docker:

**1. Backend (FastAPI)**
```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

**2. Frontend (Next.js)**
```bash
cd frontend
npm install
npm run dev
```
