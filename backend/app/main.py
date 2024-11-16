from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
from typing import List, Optional
import tempfile
import os 
from dotenv import load_dotenv
from .database import Database, Note
from .quiz import QuizGenerator


# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI(title="Audio Transcription API")
db = Database()
quiz_generator = QuizGenerator(openai.api_key)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Models
class NoteCreate(BaseModel):
    title: str
    note: str  # Changed from transcript to note
    tags: List[str]

class NoteResponse(BaseModel):
    id: int
    title: str
    note: str  # Changed from transcript to note
    tags: List[str]
    quiz: Optional[str]
    created_at: str  # This expects a string, so we need to format the datetime


class Config:
    from_attributes = True


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

@app.get("/tags/")
async def get_tags():
    """Get all unique tags used in notes."""
    try:
        # Get all notes and extract unique tags
        notes = db.get_notes()
        all_tags = set()
        for note in notes:
            all_tags.update(note.tags)
        return {"tags": sorted(list(all_tags))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/notes/", response_model=NoteResponse)
async def create_note(note: NoteCreate):
    """Create a new note with transcript and tags."""
    try:
        # Generate quiz for the note
        quiz = quiz_generator.generate_quiz(note.note)
        
        # Save note with generated quiz
        note_id = db.insert_note(
            title=note.title,
            transcript=note.transcript,
            tags=note.tags,
            quiz=quiz.json()
        )
        
        # Retrieve and return the created note
        created_note = db.get_note_by_id(note_id)
        return created_note
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes/", response_model=List[NoteResponse])
async def get_notes(limit: int = 50, offset: int = 0):
    """Retrieve all notes with pagination."""
    try:
        notes = db.get_notes(limit=limit, offset=offset)
        # Convert datetime to string format that matches frontend expectations
        return [
            NoteResponse(
                id=note.id,
                title=note.title,
                note=note.note,
                tags=note.tags,
                quiz=note.quiz,
                created_at=note.created_at.isoformat()
            ) for note in notes
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/notes/{note_id}", response_model=NoteResponse)
async def get_note(note_id: int):
    """Retrieve a specific note by ID."""
    note = db.get_note_by_id(note_id)
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    return note

@app.get("/notes/search/", response_model=List[NoteResponse])
async def search_notes(q: str = "", tags: Optional[List[str]] = None):
    """Search notes by content and tags."""
    try:
        notes = db.search_notes(q, tags)
        return [
            NoteResponse(
                id=note.id,
                title=note.title,
                note=note.note,
                tags=note.tags,
                quiz=note.quiz,
                created_at=note.created_at.isoformat()
            ) for note in notes
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Keep your existing transcribe endpoint, but update it to use the new database
# Updated transcribe endpoint
@app.post("/transcribe/")
async def transcribe_audio(
    file: UploadFile,
    title: str = Form(...),
    note_style: str = Form("detailed"),
    template_name: str = Form(None),
    tags: str = Form("")
):
    """Transcribe audio and generate formatted notes."""
    try:
        # Create a temporary file to store the uploaded content
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        # Transcribe audio
        with open(temp_file_path, "rb") as audio_file:
            transcription = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )

        # Clean up the temporary file
        os.unlink(temp_file_path)

        # Prepare the template and prompt
        selected_template = TEMPLATES.get(template_name, None)
        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        prompt = f"""
            Given the below transcript, you have several tasks:
            1. Format the notes based on the selected note style: {note_style}.
            2. Use the following custom formatting template if provided: {selected_template or "No template provided."}
            3. Incorporate the following tags for categorization: {', '.join(tags_list)}.
            4. Ensure the output is in markdown format with structured content, such as headers, lists, tables, bullet points, etc.
            **Important note: Due to markdown rendering limitations, specifically for mathematical formulas, do not use markdown/latex syntax. Instead, use plain text representation.**
            Also ensure that the generated text is in really good formatting, with good headings, bullet points, line breaks to enhance readability, etc.
            Here's the transcript: {transcription.text}
        """

        # Generate formatted notes
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        formatted_notes = response.choices[0].message.content

        # Generate quiz
        quiz = quiz_generator.generate_quiz(formatted_notes)
        quiz_json = quiz.json()

        # Save note in database
        note_id = db.insert_note(
            title=title,
            note=formatted_notes,
            tags=tags_list,
            quiz=quiz_json
        )

        # Get the created note
        created_note = db.get_note_by_id(note_id)
        
        # Return the note data
        return {
            "id": created_note.id,
            "title": created_note.title,
            "note": created_note.note,
            "tags": created_note.tags,
            "quiz": created_note.quiz,
            "created_at": created_note.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))