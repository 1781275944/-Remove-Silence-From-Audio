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
    background-color: #fafafa;
    color: #333;
    font-family: 'Arial', sans-serif;
    text-align: center;
    padding: 20px;
}

.gradio-container {
    background-color: #fff;
    padding: 40px;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
    max-width: 800px;
    margin: auto;
}

h1 {
    font-size: 36px;
    color: #2d2d2d;
    margin-bottom: 30px;
}

.gradio-button {
    background-color: #4CAF50;
    color: white;
    padding: 15px 25px;
    border-radius: 10px;
    border: none;
    font-size: 18px;
    transition: background-color 0.3s ease;
}

.gradio-button:hover {
    background-color: #45a049;
}

.gradio-file, .gradio-number {
    margin-top: 20px;
    background-color: #f1f1f1;
    border-radius: 10px;
    padding: 15px;
}

.gradio-textbox {
    margin-top: 20px;
    background-color: #f1f1f1;
    border-radius: 10px;
    padding: 15px;
}

footer {
    margin-top: 30px;
    font-size: 12px;
    color: #666;
}
"""

# Audio processing functions
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

def process_audio(audio_file, seconds=0.05):
    keep_silence = int(seconds * 1000)
    output_audio_file = process_file(audio_file, silence=keep_silence)
    store_path_in_json(output_audio_file)
    delete_old_files("stored_paths.json", max_age_hours=24)
    before = calculate_duration(audio_file)
    after = calculate_duration(output_audio_file)
    text = f"✅ Duration before: {before:.2f} s, after: {after:.2f} s"
    return output_audio_file, output_audio_file, text

def delete_old_files(json_filename, max_age_hours):
    if os.path.exists(json_filename):
        with open(json_filename, 'r') as json_file:
            data = json.load(json_file)
    else:
        return
    now = datetime.now()
    updated_data = []
    for entry in data:
        path = entry["path"]
        creation_date = datetime.strptime(entry["timestamp"], '%Y-%m-%d %H:%M:%S')
        if (now - creation_date).total_seconds() / 3600 > max_age_hours:
            if os.path.exists(path):
                os.remove(path)
            continue
        updated_data.append(entry)
    with open(json_filename, 'w') as json_file:
        json.dump(updated_data, json_file, indent=2)

def calculate_duration(file_path):
    ffprobe_command = f"ffprobe -i {file_path} -show_entries format=duration -v quiet -of csv=p=0"
    duration_string = subprocess.check_output(ffprobe_command, shell=True, text=True)
    duration = float(duration_string)
    return duration

# Gradio UI setup
with gr.Blocks(css=css) as demo:
    gr.Markdown("# 🎧 Audio Silence Removal Tool\nUpload an audio file, adjust silence threshold, and download the cleaned audio!")
    with gr.Row():
        with gr.Column():
            audio_in = gr.Audio(label="🎵 Upload Audio", type="filepath", sources=["upload", "microphone"])
            silence_input = gr.Number(label="🔕 Keep Silence (seconds)", value=0.05)
            submit_btn = gr.Button("🚀 Process Audio")
        with gr.Column():
            audio_out = gr.Audio(label="🎼 Processed Audio")
            download_file = gr.File(label="📥 Download")
            duration_box = gr.Textbox(label="📊 Audio Duration")

    submit_btn.click(fn=process_audio, inputs=[audio_in, silence_input], outputs=[audio_out, download_file, duration_box])
    gr.Markdown("💡 The tool removes silence parts in the audio and provides the cleaned version!")

# Launch the app
demo.launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", 7860)))
