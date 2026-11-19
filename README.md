# YouTube Video Summarizer

**Roll No:** 2 | **Problem Statement:** 2 – YouTube Video Summarizer

## Problem
Long lecture videos are hard to revise from. This app takes a YouTube link, fetches the video's transcript, and generates a short 5-line summary along with the main topics and their timestamps.

## Tech Stack
- Python 3.10+
- Streamlit (web interface)
- youtube-transcript-api (transcript fetching)
- Groq API with `openai/gpt-oss-20b` (LLM)
- python-dotenv (API key handling)

## How to Run
1. Clone the repository and open the folder.
2. Create a virtual environment and install the requirements:
   python -m venv venv
   venv\Scripts\activate # Windows
   source venv/bin/activate # Mac/Linux
   pip install -r requirements.txt
3. Copy `.env.example` to `.env` and add your Groq API key:
      GROQ_API_KEY=your_key_here
4. Run the app:
   python -m streamlit run app.py
5. Paste a YouTube link and click **Summarize**.

## How It Works
1. Extract the video ID from the URL.
2. Fetch the transcript (English, Hindi, or Marathi captions).
3. Split the transcript into chunks of about 6,000 characters, keeping each chunk's start time.
4. Ask the LLM for the main topics with timestamps in each chunk (map step).
5. Ask the LLM to combine the notes into a 5-line summary and a timestamped topic list (reduce step).

## Limitations
- Works only for videos that have captions or auto-generated subtitles.
- Free API tiers have rate limits, so very long videos may take longer.
