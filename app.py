# app.py
from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import subprocess
import uuid

app = Flask(__name__)

# ElevenLabs API Key (set in Render dashboard)
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Voice IDs (you can change these)
VOICE_IDS = {
    "en": "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "ro": "flq6f7yk4E4fJM5XTYuZ",  # Cristian
    "it": "2EhwvHne01cHImMSzzrf"   # Diego
}

# Ensure folders exist
os.makedirs("videos", exist_ok=True)
os.makedirs("audio", exist_ok=True)

@app.route('/generate', methods=['POST'])
def generate_video():
    data = request.json
    text = data.get('text', '')
    lang = data.get('language', 'en').lower()
    title = data.get('title', 'story').replace(' ', '_')

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Generate unique ID
    video_id = str(uuid.uuid4())[:8]

    # Step 1: Generate AI Voice with ElevenLabs
    voice_id = VOICE_IDS.get(lang, VOICE_IDS['en'])
    audio_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    audio_headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    audio_data = {
        "text": text,
        "voice_settings": {
            "stability": 0.75,
            "similarity_boost": 0.75
        }
    }

    try:
        audio_response = requests.post(audio_url, headers=audio_headers, json=audio_data)
        audio_response.raise_for_status()
    except Exception as e:
        return jsonify({"error": f"Voice generation failed: {str(e)}"}), 500

    audio_file = f"audio/{video_id}_{lang}.mp3"
    with open(audio_file, "wb") as f:
        f.write(audio_response.content)

    # Step 2: Run FFmpeg to create video
    output_file = f"videos/output_{video_id}_{lang}.mp4"

    # FFmpeg command: audio + background + subtitles
    cmd = [
        "ffmpeg", "-y",
        "-i", audio_file,
        "-i", "background.mp4",
        "-filter_complex",
        "[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2[v];"
        "[v]format=yuv420p[vout]",
        "-map", "[vout]", "-map", "0:a",
        "-c:v", "libx264", "-c:a", "aac", "-shortest", output_file
    ]

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Video creation failed: {str(e)}"}), 500

    # Step 3: Return video URL
    video_url = f"https://your-video-api.onrender.com/videos/output_{video_id}_{lang}.mp4"
    return jsonify({"video_url": video_url, "video_id": video_id})

# Serve video files
@app.route('/videos/<filename>')
def serve_video(filename):
    return send_from_directory("videos", filename)

if __name__ == '__main__':
    app.run(port=5000)