import gradio as gr
import os
import shutil
import subprocess
import uuid
import json
from datetime import datetime



from pydub import AudioSegment

def mp3_to_wav(mp3_file, wav_file):
    # Load the MP3 file
    audio = AudioSegment.from_mp3(mp3_file)

    # Export the audio to WAV format
    audio.export(wav_file, format="wav")
    
from pydub import AudioSegment
from pydub.silence import split_on_silence
import os
 
def remove_silence(file_path,output_path,minimum_silence=50):
    # Extract file name and format from the provided path
    file_name = os.path.basename(file_path)
    audio_format = "wav"

    # Reading and splitting the audio file into chunks
    sound = AudioSegment.from_file(file_path, format=audio_format)
    audio_chunks = split_on_silence(sound,
                                    min_silence_len=100,
                                    silence_thresh=-45,
                                    keep_silence=minimum_silence) 

    # Putting the file back together
    combined = AudioSegment.empty()
    for chunk in audio_chunks:
        combined += chunk


    combined.export(output_path, format=audio_format)

    return output_path

def process_file(upload_audio_path,silence=50):
  base_path = os.path.dirname(upload_audio_path)
  base_file_name = os.path.basename(upload_audio_path)
  file_name_without_extension, file_extension = os.path.splitext(base_file_name)
  random_uuid = str(uuid.uuid4())[:8]
  if file_extension.lower() == ".mp3":
    new_file_name = f"{random_uuid}.wav"
    save_path= os.path.join(base_path, new_file_name)
    mp3_to_wav(upload_audio_path, save_path)
  elif file_extension.lower() == ".wav":
    new_file_name = f"{random_uuid}{file_extension}"
    save_path= os.path.join(base_path, new_file_name)
    shutil.copy(upload_audio_path,save_path)
  else:
    raise ValueError("Unsupported file format. Please upload an MP3 or WAV file.")
  output_path=os.path.join(base_path, f"{file_name_without_extension}_{random_uuid}.wav")
  remove_silence(save_path,output_path,minimum_silence=silence)
  return output_path

def store_path_in_json(path, json_file_path="stored_paths.json"):
    # Create a dictionary with the path and timestamp
    entry = {
        "path": path,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # If the JSON file doesn't exist, create it with an empty list
    if not os.path.exists(json_file_path):
        with open(json_file_path, 'w') as json_file:
            json.dump([], json_file)

    try:
        # Read existing entries from the JSON file
        with open(json_file_path, 'r') as json_file:
            data = json.load(json_file)
    except json.decoder.JSONDecodeError as e:
        print(f"Error decoding JSON file: {e}")
        print(f"Content of JSON file: {json_file.read()}")
        raise  # Reraise the exception after printing for further analysis

    # Append the new entry to the list
    data.append(entry)

    # Write the updated list back to the JSON file
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=2)

    # print(f"Path '{path}' stored in '{json_file_path}' with timestamp '{entry['timestamp']}'.")

import os
import json
from datetime import datetime, timedelta

def delete_old_files(json_filename, max_age_hours):
    # Load JSON data
    if os.path.exists(json_filename):
        with open(json_filename, 'r') as json_file:
            data = json.load(json_file)
    else:
        # No data in the JSON file, nothing to delete
        return

    # Get the current date and time
    now = datetime.now()

    # Loop through the entries in the JSON file
    updated_data = []
    for entry in data:
        path = entry["path"]
        timestamp_str = entry["timestamp"]
        creation_date = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')

        # Check if the file is older than the specified max age in hours
        if (now - creation_date).total_seconds() / 3600 > max_age_hours:
            # Delete the file if it exists
            if os.path.exists(path):
                os.remove(path)
            
            # Skip this entry in the updated data
            continue

        # Keep the entry in the updated data
        updated_data.append(entry)

    # Save the updated JSON data
    with open(json_filename, 'w') as json_file:
        json.dump(updated_data, json_file, indent=2)


import subprocess

def calculate_duration(file_path):
    # Calculate the duration of an audio or video file using ffprobe
    ffprobe_command = f"ffprobe -i {file_path} -show_entries format=duration -v quiet -of csv=p=0"
    duration_string = subprocess.check_output(ffprobe_command, shell=True, text=True)
    duration = float(duration_string)
    return duration





 
import subprocess
import json
import os






def process_audio(audio_file,seconds=0.05):
    keep_silence=int(seconds * 1000)
    # Process the uploaded audio file
    output_audio_file= process_file(audio_file,silence=keep_silence)

    # Store the processed file path in a JSON file
    store_path_in_json(output_audio_file)

    # Delete files older than 24 hours
    delete_old_files("stored_paths.json", max_age_hours=24)
    before=calculate_duration(audio_file)
    after=calculate_duration(output_audio_file)
    text=f"Duration before: {before:.2f} seconds, Duration after: {after:.2f} seconds"
    return output_audio_file,output_audio_file,text



demo = gr.Interface(process_audio, 
                    [gr.Audio(label="Upload Audio",type="filepath",sources=['upload', 'microphone']),
                    gr.Number(label="Keep Silence Upto (In seconds)",value=0.05)], 
                    [gr.Audio(label="Play Audio"),gr.File(label="Download Audio File"),gr.Textbox(label="Duration")],    
                    examples=[['./audio/audio.wav',0.05]],
                    cache_examples=True)

demo.launch(debug=True)

