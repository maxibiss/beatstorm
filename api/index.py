from fastapi import FastAPI
from fastapi.responses import FileResponse
import mido
import os
import random
import time

import json

app = FastAPI()

# --- Music Theory Constants ---

# Scale Intervals (Expanded)
SCALES = {
    # Basic
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    # Exotic / Advanced
    "harmonic minor": [0, 2, 3, 5, 7, 8, 11],
    "double harmonic major": [0, 1, 4, 5, 7, 8, 11],
    "phrygian dominant": [0, 1, 4, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10], # Same as natural minor
    "natural minor": [0, 2, 3, 5, 7, 8, 10],
    "melodic minor": [0, 2, 3, 5, 7, 9, 11],
    "major (7th focused)": [0, 2, 4, 5, 7, 9, 11] # Maps to Major
}

# Flavor Notes (Interval indices to emphasize)
FLAVOR_NOTES = {
    "phrygian": [1],    # b2
    "phrygian dominant": [1, 2], # b2, 3
    "lydian": [3],      # #4
    "harmonic minor": [6], # 7 (Leading tone)
    "dorian": [5]       # 6 (Major 6th)
}

# Load Config
# Configs are now in the same directory as this script for Vercel compatibility
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "style_config.json")
try:
    with open(CONFIG_PATH, "r") as f:
        STYLE_DATA = json.load(f)["styles"]
        
    CHORD_PATH = os.path.join(os.path.dirname(__file__), "chord_progressions.json")
    with open(CHORD_PATH, "r") as f:
        CHORD_DATA = json.load(f)["progressions"]
except Exception as e:
    print(f"Error loading config: {e}")
    STYLE_DATA = {}
    CHORD_DATA = {}

# Fallback Legacy Config (if needed)
LEGACY_STYLE_CONFIG = {
    "boombap": {"scale": "dorian", "root": 60, "swing": True, "tempo_range": (85, 95)},
    "trap": {"scale": "minor", "root": 58, "swing": False, "tempo_range": (130, 150)},
    "drill": {"scale": "phrygian", "root": 58, "swing": False, "tempo_range": (140, 145)},
    "storch": {"scale": "minor", "root": 60, "swing": False, "tempo_range": (90, 100)},
    "edm": {"scale": "major", "root": 60, "swing": False, "tempo_range": (120, 128)},
    "flume": {"scale": "blues", "root": 60, "swing": True, "tempo_range": (80, 110)},
    "dilla": {"scale": "dorian", "root": 61, "swing": True, "swing_amt": 0.58, "tempo_range": (88, 92)}
}

DRUM_MAP = {
    "kick": 36,
    "snare": 38,
    "hat_closed": 42,
    "hat_open": 46,
    "clap": 39
}

TICKS_PER_BEAT = 480

NOTE_NAME_TO_MIDI = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, 
    "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, 
    "A#": 10, "Bb": 10, "B": 11
}

# --- Name Generation ---
ADJECTIVES = ["Crimson", "Midnight", "Neon", "Dusty", "Electric", "Silent", "Hidden", "Cosmic", "Urban", "Vintage", "Liquid", "Solar", "Broken", "Golden", "Dark", "Hollow", "Vivid", "Static", "Digital", "Analog"]
NOUNS = ["Echo", "Vibe", "Pulse", "Dream", "Shadow", "Loop", "Storm", "Drift", "Flow", "Signal", "Noise", "Haze", "Groove", "Wave", "Rider", "Soul", "Glitch", "Mode", "Vision", "Sequence"]

def generate_track_name(style, scale, bpm, root_name):
    adj = random.choice(ADJECTIVES)
    noun = random.choice(NOUNS)
    # Random suffix like X92, 007, etc
    suffix = f"{random.choice(['A','X','Z','V'])}{random.randint(10,99)}"
    
    # Format: AdjectiveNoun_Style_RootScale_BPM_Suffix
    # Clean scale name (remove spaces)
    clean_scale = scale.title().replace(" ", "")
    title = f"{adj}{noun}_{style.title()}_{root_name}{clean_scale}_{bpm}_{suffix}"
    return title

# --- Helper Functions ---

def get_style_context(style_name):
    # Normalize style name lookup
    # Only map if exists in JSON, else fallback
    # JSON keys are like "Boom Bap", user passes "boombap"
    
    # Map lowercase id to Display Name for JSON lookup
    ID_MAP = {
        "boombap": "Boom Bap", "trap": "Trap", "drill": "Drill",
        "storch": "Storch", "edm": "EDM", "flume": "Flume", "dilla": "Dilla"
    }
    
    display_name = ID_MAP.get(style_name, "Boom Bap")
    data = STYLE_DATA.get(display_name)
    
    if not data:
        # Fallback
        return LEGACY_STYLE_CONFIG.get(style_name, LEGACY_STYLE_CONFIG["boombap"])

    # Dynamic Selection
    root_name = random.choice(data["roots"])
    scale_name = random.choice(data["scales"]).lower()
    
    # Calculate midi root (Octave 4 = 60 starts at C4)
    # 60 is C4
    base_midi = 60 + NOTE_NAME_TO_MIDI.get(root_name, 0)
    # Ensure it's not too high
    if base_midi > 71: base_midi -= 12
    
    # Merge with legacy props for swing/tempo logic
    # (We rely on legacy config for non-theory props for now)
    legacy = LEGACY_STYLE_CONFIG.get(style_name, {})
    
    return {
        "root": base_midi,
        "root_name": root_name,
        "scale": scale_name,
        "swing": legacy.get("swing", False),
        "swing_amt": legacy.get("swing_amt", 0.55),
        "tempo_range": legacy.get("tempo_range", (90, 100))
    }

def get_scale_notes(root, scale_name, octaves=2):
    intervals = SCALES.get(scale_name, SCALES["minor"])
    notes = []
    for oct in range(octaves):
        base = root + (oct * 12)
        for interval in intervals:
            notes.append(base + interval)
    return notes

def add_note(events, note, beat_pos, velocity, duration, channel, style_cfg):
    # Dilla Swing Logic
    tick_pos = int(beat_pos * TICKS_PER_BEAT)
    
    swing_amt = style_cfg.get("swing_amt", 0.55) if style_cfg.get("swing") else 0
    
    # 8th note swing
    beat_int = int(beat_pos)
    fraction = beat_pos - beat_int
    
    if swing_amt > 0:
        # Check for off-beat 8th
        if abs(fraction - 0.5) < 0.05:
            tick_pos = int((beat_int + swing_amt) * TICKS_PER_BEAT)
            
    # Humanize velocity
    velocity = max(1, min(127, velocity + random.randint(-5, 5)))
    
    # Humanize timing (slight)
    tick_pos += random.randint(-10, 10)
    if tick_pos < 0: tick_pos = 0

    events.append({"tick": tick_pos, "type": "note_on", "note": note, "velocity": velocity, "channel": channel})
    events.append({"tick": tick_pos + int(duration * TICKS_PER_BEAT), "type": "note_off", "note": note, "velocity": 0, "channel": channel})

# --- Generators ---

def generate_drums(events, style, context, bars):
    # Channel 9 (0-indexed = 10)
    channel = 9
    cfg = context
    
    k = DRUM_MAP["kick"]
    s = DRUM_MAP["snare"]
    h = DRUM_MAP["hat_closed"]
    c = DRUM_MAP["clap"] # Use for Trap/Drill snare
    
    if style in ["trap", "drill"]:
        snare_note = c
    else:
        snare_note = s

    # Randomized patterns per bar
    for bar in range(bars):
        offset = bar * 4
        
        # Hi-Hats
        # Basic 8ths or 16ths
        res = 0.5 # 8th notes
        if style in ["trap", "drill", "edm"]:
             res = 0.25 # 16th notes
        
        steps = int(4 / res)
        for i in range(steps):
             # Randomize removal for variety
            if random.random() > 0.1:
                # Trap rolls
                if style == "trap" and random.random() < 0.15:
                    # 32nd notes roll
                    base_pos = offset + (i * res)
                    for r in range(4):
                        # Softer rolls
                        add_note(events, h, base_pos + (r*0.0625), 60, 0.06, channel, cfg)
                else:
                    # Velocity Logic
                    if style in ["boombap", "dilla"]:
                        # High dynamic range (Ghost notes)
                        # Randomize heavily between 50 and 90
                        vel = random.randint(50, 95)
                        if i % 2 == 0: vel += 10 # Slight accent on grid
                        vel = min(vel, 105)
                    else:
                        # Standard Accents
                        # Lower base from 100/70 to 85/60
                        vel = 85 if (i % 2 == 0) else 60
                        
                    add_note(events, h, offset + (i * res), vel, 0.1, channel, cfg)

        # Kick & Snare Context
        # Standard Backbeat
        add_note(events, snare_note, offset + 1, 110, 0.2, channel, cfg)
        add_note(events, snare_note, offset + 3, 110, 0.2, channel, cfg)
        
        # Kick Pattern
        add_note(events, k, offset + 0, 120, 0.2, channel, cfg)
        
        # Style specific additions
        if style == "boombap" or style == "dilla":
            # Kicks on offbeats
            if random.random() > 0.4: add_note(events, k, offset + 2.5, 100, 0.2, channel, cfg)
            if random.random() > 0.6: add_note(events, k, offset + 1.5, 90, 0.2, channel, cfg)
            
        elif style == "trap":
            if random.random() > 0.5: add_note(events, k, offset + 2.75, 110, 0.2, channel, cfg)
            if random.random() > 0.5: add_note(events, k, offset + 3.5, 100, 0.2, channel, cfg)
            
        elif style == "drill":
            # Drill has snare on 4th beat of half-time (beat 2 of measure?) No usually beat 3 or 4 
            # UK Drill: Snare on 3 and 8 (in 8/4) -> Beat 1.5 and 3.5? No, typically beat 3.
            # Let's keep simple backbeat but add ghost snares
            if random.random() > 0.6: add_note(events, k, offset + 3.5, 95, 0.2, channel, cfg)
            
        elif style == "edm":
            # 4 on the floor
            add_note(events, k, offset + 1, 120, 0.2, channel, cfg)
            add_note(events, k, offset + 2, 120, 0.2, channel, cfg)
            add_note(events, k, offset + 3, 120, 0.2, channel, cfg)

def generate_bass(events, context, bars):
    # Channel 0
    channel = 0
    # Context is now the dict
    cfg = context 
    style_name_dummy = "boombap" # Placeholder if needed
    
    root = cfg["root"] - 24 # Drop 2 octaves
    scale = get_scale_notes(root, cfg["scale"], 1)
    
    # Simple probability-based sequencer
    for bar in range(bars):
        offset = bar * 4
        
        # Root note on 1 is common
        add_note(events, scale[0], offset + 0, 100, 0.8, channel, cfg)
        
        # Random hits (Generic logic reuse)
        # We need style info? Since 'context' has merged data, we can check props
        # BUT we lost the 'style name' string for specific branching (trap vs boombap)
        # We should pass style name AND context or just attach style name to context.
        # Let's assume passed context has everything or handle generic behavior.
        
        # NOTE: For now, Bass logic was heavily style-branched. 
        # I rely on just generic behavior or randomization unless I pass style name too.
        # Let's just make Bass generic "Root + Fifth + Octave" for safety
        # OR bring back style name.
        
        if random.random() > 0.4:
            add_note(events, random.choice(scale), offset + 1.5, 85, 0.4, channel, cfg)
        if random.random() > 0.4:
            add_note(events, random.choice(scale), offset + 3, 90, 0.4, channel, cfg)

def generate_rhythm_motif(bars=1):
    """
    Generates a rhythmic pattern (offsets) for a given number of bars.
    Prefers on-beat and 8th notes, with occasional syncopation.
    """
    rhythm = []
    current_beat = 0
    end_beat = bars * 4
    
    while current_beat < end_beat:
        # Weighted duration choice: 
        # 0.5 (8th) = 50%, 1.0 (Quarter) = 30%, 0.25 (16th) = 10%, 1.5 (Dotted) = 10%
        r = random.random()
        if r < 0.5: dur = 0.5
        elif r < 0.8: dur = 1.0
        elif r < 0.9: dur = 0.25
        else: dur = 1.5
        
        # Don't hold note into next beat pattern awkwardly
        if current_beat + dur > end_beat:
            dur = end_beat - current_beat
            
        rhythm.append({"beat": current_beat, "duration": dur})
        
        # Gap chance (Rest) - 20%
        # If we didn't add a rest, current_beat advances by dur
        # If we want a rest, we add to current_beat but don't append a note event?
        # Simpler: The rhythm list defines where NOTES start.
        # We need to decide the gap to next note.
        
        # Advance time
        current_beat += dur
        
        # Occasional rest
        if random.random() < 0.15:
            current_beat += random.choice([0.5, 1.0])
            
    return rhythm

def generate_melodic_phrase(scale, start_note, rhythm_pattern):
    """
    Maps a rhythm pattern to notes using a 'Random Walk' approach.
    Avoids large jumps; prefers stepwise motion.
    """
    phrase = []
    current_note = start_note
    scale_len = len(scale)
    
    # Find index of start_note in scale (approximate)
    try:
        current_idx = scale.index(current_note)
    except ValueError:
        current_idx = 0 # Fallback
        
    for hit in rhythm_pattern:
        # Random Walk: -2, -1, 0, +1, +2 steps in scale
        step = random.choices([-2, -1, 0, 1, 2], weights=[0.1, 0.3, 0.2, 0.3, 0.1])[0]
        
        # Bounce off boundaries
        next_idx = current_idx + step
        if next_idx < 0: next_idx = 1
        if next_idx >= scale_len: next_idx = scale_len - 2
        
        current_idx = next_idx
        note = scale[current_idx]
        
        phrase.append({"beat": hit["beat"], "duration": hit["duration"], "note": note})
        
    return phrase

def generate_melody(events, context, bars):
    # Channel 1
    channel = 1
    cfg = context
    root = cfg["root"]
    scale_name = cfg["scale"]
    
    # Expanded range (2 octaves)
    scale = get_scale_notes(root, scale_name, 2)
    
    # Flavor Note Emphasis
    flavors = FLAVOR_NOTES.get(scale_name, [])
    
    # --- Form: A - A' - A - B (Call & Response) ---
    
    # 1. Generate Motif A (1 Bar Rhythm)
    rhythm_a = generate_rhythm_motif(bars=1)
    
    # 2. Generate Melody for A
    # Start near the middle of the scale
    start_seed = scale[len(scale)//2]
    phrase_a = generate_melodic_phrase(scale, start_seed, rhythm_a)
    
    # 3. Construct the 4-bar Loop
    loop_events = []
    
    # Bar 1: Phrase A (Statement)
    loop_events.extend(phrase_a)
    
    # Bar 2: Phrase A' (Repetition/Variation)
    # Same rhythm words, slightly different pitch contour?
    # Or strict repetition? Let's do strict repetition with end variation.
    phrase_a_prime = generate_melodic_phrase(scale, start_seed, rhythm_a) 
    # Use slight mutation of A instead of fresh gen?
    # Let's shift A' up/down a scale degree?
    # For now, fresh walk with same rhythm is good.
    for n in phrase_a_prime:
        n["beat"] += 4 # Shift to bar 2
    loop_events.extend(phrase_a_prime)
    
    # Bar 3: Phrase A (Restatement)
    phrase_a_restated = []
    for n in phrase_a:
        # Copy dict
        new_n = n.copy()
        new_n["beat"] += 8 # Shift to bar 3
        phrase_a_restated.append(new_n)
    loop_events.extend(phrase_a_restated)
    
    # Bar 4: Phrase B (Resolution/Turnaround)
    # Different rhythm often longer notes or resolving to root
    rhythm_b = generate_rhythm_motif(bars=1)
    # Force end on root?
    phrase_b = generate_melodic_phrase(scale, scale[0], rhythm_b)
    # Last note overwrite to root
    if phrase_b:
        phrase_b[-1]["note"] = scale[0] # Resolve
        phrase_b[-1]["duration"] = 2.0  # Hold
        
    for n in phrase_b:
        n["beat"] += 12
    loop_events.extend(phrase_b)
    
    # 4. Apply to global events (Repeat for total bars)
    # 'loop_events' covers 4 bars.
    
    for bar_chunk in range(0, bars, 4):
        chunk_offset = bar_chunk * 4
        
        for ev in loop_events:
            # Final probability check for Flavor
            note = ev["note"]
            if flavors and random.random() < 0.2:
                 # Inject flavor occasionally
                 f_idx = random.choice(flavors)
                 if f_idx < len(scale): note = scale[f_idx]

            add_note(events, note, chunk_offset + ev["beat"], 90, ev["duration"], channel, cfg)

def generate_chords(events, context, bars):
    # Channel 2
    channel = 2
    cfg = context
    root = cfg["root"] - 12 # Mid-range
    scale = get_scale_notes(root, cfg["scale"], 2)
    
    # Select Progression
    # Just pick random category for now, or mix
    categories = list(CHORD_DATA.keys()) if CHORD_DATA else []
    if categories:
        cat = random.choice(categories)
        progression = random.choice(CHORD_DATA[cat])
    else:
        progression = [0, 3, 4, 0] # Fallback
        
    print(f"Selected Chord Progression ({cat}): {progression}")
    
    # Generate Chords
    current_bar = 0
    prog_idx = 0
    
    # We want to fill 'bars' amount of time
    total_beats = bars * 4
    current_beat = 0
    
    while current_beat < total_beats:
        degree_idx = progression[prog_idx % len(progression)]
        
        # Harmonic Rhythm: Randomize duration (2 beats or 4 beats)
        # 70% chance of 4 beats (1 bar), 30% chance of 2 beats (half bar)
        duration = 4
        if random.random() < 0.3:
            duration = 2
            
        # Ensure we don't overflow total length
        if current_beat + duration > total_beats:
            duration = total_beats - current_beat
            
        # Create Chord
        chord_notes = []
        if degree_idx < len(scale): chord_notes.append(scale[degree_idx])
        if degree_idx + 2 < len(scale): chord_notes.append(scale[degree_idx+2])
        if degree_idx + 4 < len(scale): chord_notes.append(scale[degree_idx+4])
        
        # Add Notes
        offset = current_beat
        for note in chord_notes:
             add_note(events, note, offset, 70, duration, channel, cfg)
             
        current_beat += duration
        prog_idx += 1

@app.get("/api/generate")
def generate_midi(style: str, bpm: int, bars: int = 4, chords: bool = False):
    mid = mido.MidiFile()
    
    # 3 Tracks: Bass, Melody, Drums, Chords
    # Mido tracks are just lists of messages. 
    # For Format 1 MIDI, we can have separate tracks.
    # But for simplicity, we can put everything in one track or separate.
    # Let's do separate tracks for cleaner import in DAWs.
    
    # Track 0: Meta (Tempo, Time Sig)
    track_meta = mido.MidiTrack()
    mid.tracks.append(track_meta)
    track_meta.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm)))
    track_meta.append(mido.MetaMessage('time_signature', numerator=4, denominator=4))

    # Pattern Generation
    # Dynamic Context
    context = get_style_context(style)
    # Log for debugging (print to console)
    print(f"Generating {style} | Root: {context['root']} | Scale: {context['scale']}")

    # Pattern Generation
    all_events = []
    generate_drums(all_events, style, context, bars)
    
    # Pass context instead of style name where applicable?
    # Our generators take "style" str and look up config internally.
    # We should update them to accept config dict OR override their lookup.
    
    # Refactoring generators to accept optional 'config_override' would be best,
    # but to be less invasive, let's just modify the generators to cal get_style_context
    # OR pass the config dict directly.
    
    # Let's pass the context dict. But existing function signatures are (events, style, bars).
    # I will modify the calls to pass the dict if I update the functions.
    
    # Actually, simpler: Update the functions to take 'style_context' 
    # But wait, generators define their own channel/config logic.
    # Let's Modify the generators now to take 'context'
    
    generate_bass(all_events, context, bars)
    generate_melody(all_events, context, bars)
    
    if chords:
        generate_chords(all_events, context, bars)
    
    # Sort all events by tick
    all_events.sort(key=lambda x: x["tick"])
    
    # Let's split into tracks: Drums (Ch 9/10), Bass (Ch 0), Melody (Ch 1), Chords (Ch 2)
    # Re-sort events into specific track lists
    tracks_events = {0: [], 1: [], 2: [], 9: []} # Bass, Melody, Chords, Drums
    
    for e in all_events:
        ch = e["channel"]
        if ch not in tracks_events: tracks_events[ch] = []
        tracks_events[ch].append(e)
        
    # Write to Mido Tracks
    for ch, events in tracks_events.items():
        track = mido.MidiTrack()
        mid.tracks.append(track)
        
        # Add Track Name
        if ch == 9: name = "Drums"
        elif ch == 0: name = "Bass"
        elif ch == 1: name = "Melody"
        else: name = "Chords"
        track.append(mido.MetaMessage('track_name', name=name))
        
        last_tick = 0
        events.sort(key=lambda x: x["tick"])
        
        for e in events:
            delta = e["tick"] - last_tick
            if delta < 0: delta = 0
            track.append(mido.Message(e["type"], note=e["note"], velocity=e["velocity"], time=delta, channel=ch))
            last_tick = e["tick"]
    
    # Save
    temp_dir = "/tmp" if os.path.exists("/tmp") else os.path.dirname(__file__)
    if not os.path.exists("/tmp"):
        import tempfile
        temp_dir = tempfile.gettempdir()

    output_file = os.path.join(temp_dir, f"beat_{int(time.time())}.mid")
    mid.save(output_file)
    
    # Generate Creative Filename
    filename = f"{generate_track_name(style, context['scale'], bpm, context['root_name'])}.mid"
    
    # Return with explicit filename in content-disposition
    return FileResponse(
        output_file, 
        media_type="audio/midi", 
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
