import mido
import requests
import os
import shutil

# Request a generated MIDI
url = "http://localhost:8000/api/generate?style=trap&bpm=140&bars=8"
response = requests.get(url, stream=True)

if response.status_code != 200:
    print(f"FAILED: Status {response.status_code}")
    exit(1)

temp_file = "test_beat.mid"
with open(temp_file, 'wb') as f:
    response.raw.decode_content = True
    shutil.copyfileobj(response.raw, f)

# Analyze MIDI
mid = mido.MidiFile(temp_file)
print(f"Tracks: {len(mid.tracks)}")

track_names = []
channels_found = set()

for i, track in enumerate(mid.tracks):
    t_name = ""
    for msg in track:
        if msg.type == 'track_name':
            t_name = msg.name
        if msg.type == 'note_on':
            channels_found.add(msg.channel)
    track_names.append(t_name)
    print(f"Track {i}: {t_name} | Events: {len(track)}")

print(f"Channels Found: {channels_found}")

# Validation
if "Drums" not in track_names:
    print("FAILED: No Drum track found")
if "Bass" not in track_names:
    print("FAILED: No Bass track found")
if "Melody" not in track_names:
    print("FAILED: No Melody track found")
    
if 9 not in channels_found: # Channel 10 is 9 zero-indexed
    print("FAILED: No Channel 10 (Drums) found")

print("SUCCESS: MIDI structure verified")
os.remove(temp_file)
