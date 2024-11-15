import streamlit as st
from st_audiorec import st_audiorec
import requests

st.set_page_config(page_title="Audio Recorder", layout="centered")

# Header
st.title("Audio Recorder")

# Option to record audio or upload a file
audio_option = st.radio("Choose an audio input option:", ("Record Audio", "Upload Audio File"))

# Audio recording with st_audiorec
wav_audio_data = None
if audio_option == "Record Audio":
    wav_audio_data = st_audiorec()

# Audio file upload
audio_file = None
if audio_option == "Upload Audio File":
    audio_file = st.file_uploader("Upload an audio file", type=["wav", "mp3"])

# If there's audio data (from recording or file upload), play it
if wav_audio_data is not None:
    st.audio(wav_audio_data, format="audio/wav")
elif audio_file is not None:
    st.audio(audio_file, format="audio/wav")

# Form for transcription options
st.subheader("Transcription Options")
note_style = st.selectbox("Note Style", ["Detailed", "Summary", "Bullet Points"])
template_name = st.text_input("Template Name (Optional)")
tags = st.text_input("Tags (e.g., lecture, math)")

# Button to generate transcription
if st.button("Generate"):
    if wav_audio_data or audio_file:
        # Use the audio data (from recording or uploaded file)
        audio_data = wav_audio_data if wav_audio_data else audio_file.read()

        # Send the audio file to the transcription server
        files = {"file": ("audio_input", audio_data, "audio/wav")}
        data = {
            "note_style": note_style,
            "template_name": template_name,
            "tags": tags,
        }
        response = requests.post("http://localhost:8000/transcribe/", files=files, data=data)
        
        # Render the transcription result using Markdown
        if response.status_code == 200:
            st.markdown(response.text)
        else:
            st.error("Failed to transcribe audio. Please try again.")
    else:
        st.warning("Please record or upload audio before generating transcription.")
