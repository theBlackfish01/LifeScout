# Life Scouter

## Overview
Life Scouter is an AI-powered personal assistant built on LangGraph and Chainlit, featuring a two-level supervisor architecture.

## Setup Instructions

### Environment Setup
1. Copy `.env.example` to `.env`
2. Fill in your API keys (Gemini, Tavily) in the `.env` file.

### Running with Docker (Recommended)
You can run the entire application using Docker Compose:
```bash
docker-compose up --build
```
The application will be available at `http://localhost:8000`.

### Local Development
If you prefer running locally with a virtual environment:
1. Create and activate a virtual environment (`python -m venv .venv` and `source .venv/bin/activate` or `.venv\Scripts\activate` on Windows).
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `chainlit run app.py -w`
