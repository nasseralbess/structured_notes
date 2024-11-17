# app.py
import streamlit as st
from st_audiorec import st_audiorec
import requests
from datetime import datetime
import json
from typing import List, Optional

# Configuration
API_BASE_URL = "http://localhost:8000"

# Initialize session state
if 'current_note' not in st.session_state:
    st.session_state.current_note = None
if 'quiz_active' not in st.session_state:
    st.session_state.quiz_active = False
if 'quiz_answers' not in st.session_state:
    st.session_state.quiz_answers = {}

def format_date(date_str: str) -> str:
    date = datetime.fromisoformat(date_str)
    return date.strftime("%B %d, %Y %I:%M %p")

class NotesApp:
    def __init__(self):
        st.set_page_config(
            page_title="Smart Notes Transcriber",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        st.markdown(
            """
            <style>
            button, [role="button"], .stButton button, select, .stSelectbox div {
                cursor: pointer !important;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        self.setup_sidebar()
        
    def setup_sidebar(self):
        st.sidebar.title("Navigation")
        self.page = st.sidebar.radio(
            "Choose a page",
            ["Create Note", "View Notes", "Take Quiz"]
        )
        if 'page' in st.session_state:
            self.page = st.session_state.page
        
        try:
            # Fetch and display saved notes in sidebar
            response = requests.get(f"{API_BASE_URL}/notes/")
            if response.status_code == 200:
                notes = response.json()
                if notes:
                    st.sidebar.subheader("Recent Notes")
                    for note in notes[:5]:
                        if st.sidebar.button(
                            f"{note['title']} ({format_date(note['created_at'])})",
                            key=f"note_{note['id']}"
                        ):
                            st.session_state.current_note = note
        except requests.exceptions.RequestException:
            st.sidebar.error("Could not connect to the server.")
        
    def render_create_note_page(self):
        st.title("Create New Note")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Note title
            title = st.text_input("Note Title", key="note_title")
            
            # Audio input options
            audio_option = st.radio(
                "Choose an audio input option:",
                ("Record Audio", "Upload Audio File")
            )
            
            wav_audio_data = None
            if audio_option == "Record Audio":
                wav_audio_data = st_audiorec()
            
            audio_file = None
            if audio_option == "Upload Audio File":
                audio_file = st.file_uploader("Upload an audio file", type=["wav", "mp3"])
            
            # Preview audio
            if wav_audio_data is not None:
                st.audio(wav_audio_data, format="audio/wav")
            elif audio_file is not None:
                st.audio(audio_file, format="audio/wav")
        
        with col2:
            st.subheader("Transcription Options")
            
            # Note style selection
            note_style = st.selectbox(
                "Note Style",
                ["Detailed", "Summary", "Bullet Points"],
                key="note_style"
            )
            
            # Initialize template_name
            template_name = "None"
            
            # Template selection
            try:
                response = requests.get(f"{API_BASE_URL}/templates/")
                if response.status_code == 200:
                    templates = response.json()["templates"]
                    template_name = st.selectbox(
                        "Select Template",
                        ["None"] + templates,
                        key="template_selection"
                    )
            except requests.exceptions.RequestException:
                st.error("Could not fetch templates.")
            
            # Tags input
            default_tags = ["lecture", "meeting", "interview", "research", "other"]
            selected_tags = st.multiselect(
                "Tags",
                default_tags,
                key="tags"
            )
            
            # Custom tag input
            custom_tag = st.text_input("Add custom tag")
            if custom_tag and st.button("Add Tag"):
                selected_tags.append(custom_tag)
        
        # Generate button
        if st.button("Generate", type="primary"):
            if not title:
                st.error("Please provide a title for your note.")
                return
                
            if not (wav_audio_data or audio_file):
                st.error("Please provide audio input.")
                return
            
            # Prepare the audio data
            audio_data = wav_audio_data if wav_audio_data else audio_file.read()
            
            # Create form data
            files = {"file": ("audio_input", audio_data, "audio/wav")}
            data = {
                "title": title,
                "note_style": note_style,
                "template_name": template_name if template_name != "None" else "",
                "tags": ",".join(selected_tags),
            }
            
            try:
                with st.spinner("Transcribing audio..."):
                    response = requests.post(
                        f"{API_BASE_URL}/transcribe/",
                        files=files,
                        data=data
                    )
                    
                    if response.status_code == 200:
                        note_data = response.json()
                        st.success("Transcription completed!")
                        
                        # Display the transcription
                        st.subheader("Generated Notes")
                        st.markdown(note_data["note"])
                        
                        # Download options
                        st.download_button(
                            label="Download as Markdown",
                            data=note_data["note"],
                            file_name=f"{title.lower().replace(' ', '_')}.md",
                            mime="text/markdown"
                        )

                        # Show quiz option
                        if st.button("Take Quiz"):
                            st.session_state.current_note = note_data
                            st.session_state.quiz_active = True
                            st.experimental_rerun()
                    else:
                        st.error(f"Failed to transcribe audio: {response.text}")
            except requests.exceptions.RequestException as e:
                st.error(f"Connection error: {str(e)}")
    
    def render_view_notes_page(self):
        st.title("View Notes")
        
        # Add search and filter as an expander instead of the main view
        with st.expander("Search & Filter"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                search_query = st.text_input("Search notes", key="search_notes")
            
            with col2:
                try:
                    response = requests.get(f"{API_BASE_URL}/tags/")
                    if response.status_code == 200:
                        available_tags = response.json()["tags"]
                        filter_tags = st.multiselect("Filter by tags", available_tags)
                except requests.exceptions.RequestException:
                    st.error("Could not fetch tags.")
                    filter_tags = []
            
            # Only show search results if search is active
            if search_query or filter_tags:
                # Add search parameters
                params = {}
                if search_query:
                    params['q'] = search_query
                if filter_tags:
                    params['tags'] = filter_tags
                    
                try:
                    response = requests.get(f"{API_BASE_URL}/notes/search/", params=params)
                    notes = response.json() if response.status_code == 200 else []
                except requests.exceptions.RequestException:
                    st.error("Could not fetch search results.")
                    notes = []
            else:
                # Show all notes by default
                try:
                    response = requests.get(f"{API_BASE_URL}/notes/")
                    notes = response.json() if response.status_code == 200 else []
                except requests.exceptions.RequestException:
                    st.error("Could not fetch notes.")
                    notes = []
        
        # Display notes
        if not notes:
            st.info("No notes found.")
            return
        
        # Create a grid layout for notes
        col1, col2 = st.columns(2)
        for i, note in enumerate(notes):
            with (col1 if i % 2 == 0 else col2):
                with st.container():
                    st.markdown(f"### {note['title']}")
                    st.caption(f"Created: {format_date(note['created_at'])}")
                    
                    if note['tags']:
                        st.markdown("**Tags:** " + ", ".join(note['tags']))
                    
                    with st.expander("View Note"):
                        st.markdown(note['note'])
                        
                        col1b, col2b, col3b = st.columns([1, 1, 1])
                        with col1b:
                            if st.button("Take Quiz", key=f"quiz_{note['id']}"):
                                st.session_state.current_note = note
                                st.session_state.page = "Take Quiz"  
                                st.experimental_rerun()
                        
                        with col2b:
                            st.download_button(
                                "Download Notes",
                                note['note'],
                                file_name=f"{note['title'].lower().replace(' ', '_')}.md",
                                mime="text/markdown"
                            )
                        
                        with col3b:
                            if st.button("Share", key=f"share_{note['id']}"):
                                st.code(f"{API_BASE_URL}/notes/{note['id']}")
                                st.success("Link copied to clipboard!")
                    st.divider()
    
    def render_quiz_page(self):
        st.title("Quiz Mode")
        
        if not st.session_state.current_note:
            st.warning("Please select a note from the 'View Notes' page to take a quiz.")
            if st.button("Go to View Notes"):
                self.page = "View Notes"
                st.experimental_rerun()
            return
        
        note = st.session_state.current_note
        
        try:
            if not note.get('quiz'):
                st.error("No quiz available for this note.")
                return
                
            quiz_data = json.loads(note['quiz'])
            if not quiz_data or 'questions' not in quiz_data:
                st.error("Invalid quiz format.")
                return
            
            st.subheader(f"Quiz for: {note['title']}")
            
            if 'quiz_answers' not in st.session_state:
                st.session_state.quiz_answers = {}
            if 'quiz_submitted' not in st.session_state:
                st.session_state.quiz_submitted = False
            
            # Display questions
            for i, question in enumerate(quiz_data['questions']):
                st.write(f"\n**Question {i + 1}:** {question['question']}")
                
                # Create a unique key for each question
                answer_key = f"quiz_{note['id']}_q_{i}"
                
                # Radio button for answer selection
                options = question['options']
                selected_option = st.radio(
                    "Choose your answer:",
                    options,
                    key=answer_key,
                    index=st.session_state.quiz_answers.get(answer_key, 0)
                )
                
                # Store the selected answer
                if selected_option:
                    selected_index = options.index(selected_option)
                    st.session_state.quiz_answers[answer_key] = selected_index
                
                # Show feedback if quiz is submitted
                if st.session_state.quiz_submitted:
                    correct_index = question['correct_answer']
                    if st.session_state.quiz_answers.get(answer_key) == correct_index:
                        st.success("✅ Correct!")
                    else:
                        st.error("❌ Incorrect")
                        st.info(f"The correct answer was: {options[correct_index]}")
                    st.write(f"**Explanation:** {question['explanation']}")
                
                st.divider()
            
            # Submit and Reset buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Submit Answers", disabled=st.session_state.quiz_submitted):
                    st.session_state.quiz_submitted = True
                    st.experimental_rerun()
            
            with col2:
                if st.button("Reset Quiz"):
                    st.session_state.quiz_submitted = False
                    st.session_state.quiz_answers = {}
                    st.experimental_rerun()
            
            # Show score if submitted
            if st.session_state.quiz_submitted:
                correct_count = sum(
                    1 for i, q in enumerate(quiz_data['questions'])
                    if st.session_state.quiz_answers.get(f"quiz_{note['id']}_q_{i}") == q['correct_answer']
                )
                total = len(quiz_data['questions'])
                score = (correct_count / total) * 100
                st.success(f"Your Score: {correct_count}/{total} ({score:.1f}%)")
                
        except json.JSONDecodeError:
            st.error("Error: Invalid quiz data format")
        except Exception as e:
            st.error(f"An error occurred while loading the quiz: {str(e)}")
    
    def main(self):
        try:
            if self.page == "Create Note":
                self.render_create_note_page()
            elif self.page == "View Notes":
                self.render_view_notes_page()
            elif self.page == "Take Quiz":
                self.render_quiz_page()
        except Exception as e:
            st.error(f"An unexpected error occurred: {str(e)}")
            st.error("Please try refreshing the page.")

if __name__ == "__main__":
    app = NotesApp()
    app.main()