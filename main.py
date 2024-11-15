from fastapi import FastAPI, UploadFile, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from dotenv import load_dotenv
import tempfile
import os
from fastapi.websockets import WebSocket

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Allow CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class TemplateUpload(BaseModel):
    name: str
    content: str


# In-memory storage for templates
TEMPLATES = {}

# Endpoint for uploading custom templates
@app.post("/templates/upload/")
async def upload_template(template: TemplateUpload):
    """Upload custom formatting templates."""
    TEMPLATES[template.name] = template.content
    return {"message": "Template uploaded successfully.", "template_name": template.name}


@app.get("/templates/")
async def get_templates():
    """Retrieve a list of available templates."""
    return {"templates": list(TEMPLATES.keys())}


@app.post("/transcribe/")
async def transcribe_audio(
    file: UploadFile, 
    note_style: str = Form("detailed"), 
    template_name: str = Form(None), 
    tags: str = Form("")
):
    """
    Transcribe audio file and generate notes with customization options.
    - `note_style`: The style of notes (summary, detailed, bullet points).
    - `template_name`: The name of a pre-uploaded custom formatting template.
    - `tags`: Comma-separated tags for categorization.
    """
    try:
        # Create a temporary file to store the uploaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_file.write(await file.read())  # Write uploaded file content
            temp_file_path = temp_file.name

        # Use the temporary file with open()
        with open(temp_file_path, "rb") as audio_file:
            transcription = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,  # Pass the file object opened in binary mode
                language="en"
            )

        # Clean up the temporary file
        os.unlink(temp_file_path)


        # Prepare the template and prompt
        selected_template = TEMPLATES.get(template_name, None)
        tags_list = tags.split(",") if tags else []

        prompt = f"""
            Given the below transcript, you have several tasks:
            1. Format the notes based on the selected note style: {note_style}.
            2. Use the following custom formatting template if provided: {selected_template or "No template provided."}
            3. Incorporate the following tags for categorization: {', '.join(tags_list)}.
            4. Ensure the output is in markdown format with structured content, such as headers, lists, tables, bullet points, etc.
            Here's the transcript: {transcription.text}
        """

        # Stream chat completion and return response
        def chat_stream():
            stream = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content

        return StreamingResponse(chat_stream(), media_type="text/markdown")
    except Exception as e:
        print(e)
        return JSONResponse({"error": f"Unexpected error: {str(e)}"}, status_code=500)


@app.get("/tags/")
async def get_tags():
    """Retrieve a list of commonly used tags."""
    # Example: This could fetch from a database or predefined list
    common_tags = ["lecture", "video", "conversation", "science", "math", "history"]
    return {"tags": common_tags}
