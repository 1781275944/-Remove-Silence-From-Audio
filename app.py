import gradio as gr
import os
import shutil
import subprocess
import uuid
import json
from datetime import datetime
from pydub import AudioSegment
from pydub.silence import split_on_silence

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
    entry = {"path": path, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    if not os.path.exists(json_file_path):
        with open(json_file_path, 'w') as json_file:
            json.dump([], json_file)
    
    try:
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)
    except json.decoder.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        raise

    data.append(entry)
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)

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
        timestamp_str = entry["timestamp"]
        creation_date = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
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
    return float(duration_string)

def process_audio(audio_file, seconds=0.05):
    keep_silence = int(seconds * 1000)
    output_audio_file = process_file(audio_file, silence=keep_silence)
    store_path_in_json(output_audio_file)
    delete_old_files("stored_paths.json", max_age_hours=24)
    before = calculate_duration(audio_file)
    after = calculate_duration(output_audio_file)
    text = f"Duration before: {before:.2f} seconds, Duration after: {after:.2f} seconds"
    return output_audio_file, output_audio_file, text

# Enhancements to Gradio Interface
demo = gr.Interface(
    fn=process_audio, 
    inputs=[
        gr.Audio(label="Upload Audio", type="filepath", sources=['upload', 'microphone']),
        gr.Slider(minimum=0.0, maximum=5.0, step=0.01, label="Keep Silence Upto (In seconds)", value=0.05)
    ], 
    outputs=[
        gr.Audio(label="Play Audio"),
        gr.File(label="Download Audio File"),
        gr.Textbox(label="Duration")
    ],
    examples=[['./audio/audio.wav', 0.05]],
    cache_examples=True,
    theme="compact",  # Use a built-in Gradio theme, you can replace "compact" with others like "huggingface" for different styles
    title="Audio Silence Removal",  # Add title for your application
    description="Upload an audio file, and the system will remove silence segments based on the threshold.",  # Add a description
    allow_flagging="never",  # Disable flagging if you don't need it
)

demo.launch(debug=True)
