import gradio as gr
import os
import shutil
import subprocess
import uuid
import json
from datetime import datetime
from pydub import AudioSegment
from pydub.silence import split_on_silence

# 自定义样式
css = """
body {
    background-color: #2f2f2f;
    color: #fff;
    font-family: 'Arial', sans-serif;
    text-align: center;
}

.gradio-container {
    background-color: #333;
    padding: 30px;
    border-radius: 10px;
    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
}

.gradio-button {
    background-color: #ff6200;
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    border: none;
    font-size: 18px;
}

.gradio-button:hover {
    background-color: #ff8000;
}

.gradio-file {
    margin-top: 20px;
    background-color: #444;
    border-radius: 5px;
    padding: 20px;
}
"""

def mp3_to_wav(mp3_file, wav_file):
    audio = AudioSegment.from_mp3(mp3_file)
    audio.export(wav_file, format="wav")

def remove_silence(file_path, output_path, minimum_silence=50):
    file_name = os.path.basename(file_path)
    audio_format = "wav"
    sound = AudioSegment.from_file(file_path, format=audio_format)
    audio_chunks = split_on_silence(sound, min_silence_len=100, silence_thresh=-45, keep_silence=minimum_silence)
    combined = AudioSegment.empty()
    for chunk in audio_chunks:
        combined += chunk
    combined.export(output_path, format=audio_format)
    return output_path

def process_file(upload_audio_path, silence=50):
    base_path = os.path.dirname(upload_audio_path)
    base_file_name = os.path.basename(upload_audio_path)
    file_name_without_extension, file_extension = os.path.splitext(base_file_name)
    random_uuid = str(uuid.uuid4())[:8]
    if file_extension.lower() == ".mp3":
        new_file_name = f"{random_uuid}.wav"
        save_path = os.path.join(base_path, new_file_name)
        mp3_to_wav(upload_audio_path, save_path)
    elif file_extension.lower() == ".wav":
        new_file_name = f"{random_uuid}{file_extension}"
        save_path = os.path.join(base_path, new_file_name)
        shutil.copy(upload_audio_path, save_path)
    else:
        raise ValueError("Unsupported file format. Please upload an MP3 or WAV file.")
    output_path = os.path.join(base_path, f"{file_name_without_extension}_{random_uuid}.wav")
    remove_silence(save_path, output_path, minimum_silence=silence)
    return output_path

def store_path_in_json(path, json_file_path="stored_paths.json"):
    entry = {
        "path": path,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    if not os.path.exists(json_file_path):
        with open(json_file_path, 'w') as json_file:
            json.dump([], json_file)
    with open(json_file_path, 'r') as json_file:
        try:
            data = json.load(json_file)
        except json.decoder.JSONDecodeError:
            data = []
    data.append(entry)
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)

def process_audio(audio_file, seconds=0.05, password=""):
    if password != "vip123":
        return None, None, "❌ Invalid VIP password."

    keep_silence = int(seconds * 1000)
    output_audio_file = process_file(audio_file, silence=keep_silence)
    store_path_in_json(output_audio_file)
    delete_old_files("stored_paths.json", max_age_hours=24)
    before = calculate_duration(audio_file)
    after = calculate_duration(output_audio_file)
    summary = f"✅ Duration before: {before:.2f} s, after: {after:.2f} s"
    return output_audio_file, output_audio_file, summary

with gr.Blocks(title="✨ Remove Silence From Audio", css=css) as demo:
    gr.Markdown("# 🎧 Remove Silence From Audio\nUpload your audio and get it cleaned!")
    with gr.Row():
        with gr.Column():
            audio_in = gr.Audio(label="🎵 Upload Audio", type="filepath", sources=["upload", "microphone"])
            silence_input = gr.Number(label="🔕 Keep Silence (seconds)", value=0.05)
            password_input = gr.Textbox(label="🔐 VIP Password", type="password", placeholder="Enter VIP Code")
            submit_btn = gr.Button("🚀 Submit")
        with gr.Column():
            audio_out = gr.Audio(label="🎼 Cleaned Audio")
            download_file = gr.File(label="📥 Download")
            duration_box = gr.Textbox(label="📊 Result")

    submit_btn.click(fn=process_audio, inputs=[audio_in, silence_input, password_input], outputs=[audio_out, download_file, duration_box])
    gr.Markdown("💡 Default VIP password: `vip123`")

demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
