from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import openai
from dotenv import load_dotenv
import os
from pydub import AudioSegment
import tempfile

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Allow CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust origins as needed for security
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile):
    """
    Endpoint to handle audio transcription and structured note generation.
    Accepts an audio file, processes it using OpenAI Whisper, and streams the GPT-generated notes.
    """
    try:
        # Convert the uploaded audio file to a supported format (MP3)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            audio = AudioSegment.from_file(file.file)
            audio.export(temp_file.name, format="mp3")
            temp_file.close()

        # Perform transcription using OpenAI Whisper
        with open(temp_file.name, "rb") as converted_file:
            transcription = openai.audio.transcriptions.create(
                model="whisper-1",
                file=converted_file,
                language="en"
            )

        # Prepare the prompt
        prompt = f"""
        Given the below transcript, You have three tasks:
        1. Identify what the transcript is from (a lecture, an educational video, a conversation, etc.)
        2. Figure out the key points and concepts discussed in the transcript while considering what the transcript is taken from, so the insights from a conversation will be different from those of a lecture.
        3. Write thorough structured notes that incorporate every important concept that is mentioned. You can add information from your knowledge to fill the gaps.
        Provide your output in markdown, and use all necessary structures like headers, lists, tables, bullet points, equations, etc. Note that your final output should be the formatted notes and only the formatted notes, not a single extra token.
        Here's the transcript: {transcription['text']}
        """

        # Stream chat completion and return the response
        def chat_stream():
            stream = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for chunk in stream:
                if "content" in chunk.choices[0].delta:
                    yield chunk.choices[0].delta["content"]

        return StreamingResponse(chat_stream(), media_type="text/markdown")

    except Exception as e:
        return {"error": str(e)}
