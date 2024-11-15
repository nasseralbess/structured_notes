import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import requests
import io
import tempfile

st.title("Real-time Audio Transcription and Note-Taking")

class AudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_buffer = io.BytesIO()

    def recv_audio(self, frame):
        # Append audio frames to buffer
        self.audio_buffer.write(frame.to_ndarray().tobytes())

# Initialize the audio processor for recording
processor = webrtc_streamer(
    key="audio-stream",
    mode=WebRtcMode.SENDRECV,  # Use WebRtcMode enum
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
)

if processor.audio_processor:
    st.write("Recording... Press 'Stop' to end recording.")

    if st.button("Process Audio"):
        # Save audio to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_file.write(processor.audio_processor.audio_buffer.getvalue())
        temp_file.close()

        # Send recorded audio to FastAPI server
        with open(temp_file.name, "rb") as audio_file:
            response = requests.post(
                "http://127.0.0.1:8000/transcribe/",  # Update to deployed server URL
                files={"file": audio_file},
            )

        # Display the processed output as Markdown
        st.markdown(response.text)

        # Clean up temporary file
        processor.audio_processor.audio_buffer = io.BytesIO()
