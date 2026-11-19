import os
import re

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

MODEL = "openai/gpt-oss-20b"
CHUNK_CHARS = 6000          # approx. characters of transcript per LLM call
LANGUAGES = ["en", "hi", "mr"]

MAP_PROMPT = """You are given one part of a YouTube video transcript.
Each part begins with its timestamp in [MM:SS] format.

List the 2 to 4 main topics discussed in this part. Use exactly this format, one topic per line:
[MM:SS] Topic name - one-line description

Use only information present in the transcript. Do not add outside facts.

TRANSCRIPT PART (starts at {start}):
{text}
"""

REDUCE_PROMPT = """Below are topic notes from a YouTube video, in order of time.

Write the answer in exactly this format:

**Summary**
Write exactly 5 lines, one sentence per line, describing the video.

**Main topics with timestamps**
- [MM:SS] Topic name - short description
(list every important topic from the notes, in time order)

Use only the notes below. Do not invent details.

NOTES:
{notes}
"""


def extract_video_id(url: str):
    """Return the 11-character YouTube video ID from common URL formats, or None."""
    match = re.search(r"(?:v=|youtu\.be/|shorts/|embed/)([0-9A-Za-z_-]{11})", url)
    return match.group(1) if match else None


def fetch_transcript(video_id: str):
    """Fetch transcript snippets. Supports both youtube-transcript-api 1.x and 0.6.x."""
    try:
        api = YouTubeTranscriptApi()                      # version 1.x
        fetched = api.fetch(video_id, languages=LANGUAGES)
        return [{"text": s.text, "start": s.start} for s in fetched]
    except AttributeError:                                 # version 0.6.x fallback
        data = YouTubeTranscriptApi.get_transcript(video_id, languages=LANGUAGES)
        return [{"text": d["text"], "start": d["start"]} for d in data]


def fmt_time(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def make_chunks(snippets):
    """Group transcript snippets into chunks of about CHUNK_CHARS, keeping each chunk's start time."""
    chunks, buf, buf_start, length = [], [], None, 0
    for snip in snippets:
        if buf_start is None:
            buf_start = snip["start"]
        buf.append(snip["text"])
        length += len(snip["text"]) + 1
        if length >= CHUNK_CHARS:
            chunks.append((buf_start, " ".join(buf)))
            buf, buf_start, length = [], None, 0
    if buf:
        chunks.append((buf_start, " ".join(buf)))
    return chunks


def ask_llm(client: Groq, prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


def summarize(client: Groq, chunks, progress):
    notes = []
    total = len(chunks) + 1
    for i, (start, text) in enumerate(chunks, start=1):
        prompt = MAP_PROMPT.format(start=fmt_time(start), text=text)
        notes.append(ask_llm(client, prompt))
        progress.progress(i / total, text=f"Analysing part {i} of {len(chunks)}...")

    progress.progress(len(chunks) / total, text="Writing final summary...")
    final = ask_llm(client, REDUCE_PROMPT.format(notes="\n\n".join(notes)))
    progress.progress(1.0, text="Done!")
    return final


# ---------------- UI ----------------
st.set_page_config(page_title="YouTube Video Summarizer", page_icon="🎬")
st.title("🎬 YouTube Video Summarizer")
st.write("Paste a YouTube link to get a 5-line summary and the main topics with timestamps.")

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    api_key = st.sidebar.text_input("Groq API key", type="password")

url = st.text_input("YouTube video URL", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Summarize", type="primary"):
    if not api_key:
        st.error("Please enter your Groq API key in the sidebar or in the .env file.")
        st.stop()

    video_id = extract_video_id(url.strip())
    if not video_id:
        st.error("That does not look like a valid YouTube link.")
        st.stop()

    with st.spinner("Fetching transcript..."):
        try:
            snippets = fetch_transcript(video_id)
        except Exception as e:
            st.error(f"Could not get the transcript. The video may have no captions. Details: {e}")
            st.stop()

    if not snippets:
        st.error("The transcript is empty.")
        st.stop()

    chunks = make_chunks(snippets)
    client = Groq(api_key=api_key)
    progress = st.progress(0.0, text="Starting...")

    try:
        result = summarize(client, chunks, progress)
    except Exception as e:
        st.error(f"The LLM call failed: {e}")
        st.stop()

    st.video(f"https://www.youtube.com/watch?v={video_id}")
    st.markdown(result)
    st.caption(f"Transcript length: {len(snippets)} segments, processed in {len(chunks)} chunk(s).")