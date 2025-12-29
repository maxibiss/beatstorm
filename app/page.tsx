'use client';

import { useState, useRef, useEffect } from 'react';
import * as Tone from 'tone';
import { Midi } from '@tonejs/midi';

const STYLES = [
  { id: 'boombap', name: 'Boom Bap', description: 'Classic 90s hip hop rhythms' },
  { id: 'trap', name: 'Trap', description: 'Heavy 808s and fast hi-hats' },
  { id: 'drill', name: 'Drill', description: 'Dark, sliding bass and syncopation' },
  { id: 'storch', name: 'Storch', description: 'Melodic piano driven bounce' },
  { id: 'edm', name: 'EDM', description: 'Four-on-the-floor dance energy' },
  { id: 'flume', name: 'Flume', description: 'Experimental heavy swing future bass' },
  { id: 'dilla', name: 'Dilla', description: 'Drunk swing and micro-timing (58%)' },
];

export default function Home() {
  const [selectedStyle, setSelectedStyle] = useState(STYLES[0].id);
  const [bpm, setBpm] = useState(90);
  const [bars, setBars] = useState(4);
  const [includeChords, setIncludeChords] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isBeatReady, setIsBeatReady] = useState(false);
  const [midiUrl, setMidiUrl] = useState<string | null>(null);
  const [songTitle, setSongTitle] = useState<string | null>(null);

  // Audio Refs
  const synths = useRef<any[]>([]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupAudio();
    };
  }, []);

  const cleanupAudio = () => {
    Tone.Transport.stop();
    Tone.Transport.cancel(); // Clear scheduled events
    synths.current.forEach(synth => synth.dispose());
    synths.current = [];
    setIsPlaying(false);
  };

  const initializeAudio = async () => {
    await Tone.start();
    console.log('Audio context started');
  };

  const generateBeat = async () => {
    // 1. Cleanup previous
    cleanupAudio();
    await initializeAudio();
    setIsGenerating(true);
    setIsBeatReady(false);
    setMidiUrl(null);
    setSongTitle(null);

    try {
      // 2. Fetch
      const response = await fetch(`/api/generate?style=${selectedStyle}&bpm=${bpm}&bars=${bars}&chords=${includeChords}`);
      if (!response.ok) throw new Error('Generation failed');

      // Filename
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `beatstorm_${selectedStyle}.mid`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) filename = match[1];
      }
      setSongTitle(filename.replace('.mid', ''));

      // Blob
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      setMidiUrl(url);

      // 3. Parse and Schedule
      const arrayBuffer = await blob.arrayBuffer();
      const midi = new Midi(arrayBuffer);
      setupSynthsAndSchedule(midi);

      setIsBeatReady(true);

    } catch (error) {
      console.error('Error:', error);
      alert('Error: ' + error);
    } finally {
      setIsGenerating(false);
    }
  };

  const setupSynthsAndSchedule = (midi: Midi) => {
    // Drum Synth (Kick - 909 Style)
    const drumSynth = new Tone.MembraneSynth({
      pitchDecay: 0.05,
      octaves: 10,
      oscillator: { type: "sine" },
      envelope: { attack: 0.001, decay: 0.4, sustain: 0.01, release: 1.4, attackCurve: "exponential" }
    }).toDestination();
    drumSynth.volume.value = 5;

    // HiHat Synth
    const hatSynth = new Tone.MetalSynth({
      frequency: 250,
      envelope: { attack: 0.001, decay: 0.05, release: 0.01 },
      harmonicity: 3.1,
      modulationIndex: 16,
      resonance: 3000,
      octaves: 1.0
    } as any).toDestination();
    hatSynth.volume.value = -10;

    // Bass Synth
    const bassSynth = new Tone.MonoSynth({
      oscillator: { type: "triangle" },
      envelope: { attack: 0.05, decay: 0.5, release: 1 }
    }).toDestination();

    // Melody Synth
    const melodySynth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: "sine" },
      envelope: { attack: 0.01, decay: 0.1, sustain: 0.1, release: 1 }
    }).toDestination();
    melodySynth.volume.value = -5;

    // Snare Synth
    const snareSynth = new Tone.NoiseSynth({
      noise: { type: "white" },
      envelope: { attack: 0.001, decay: 0.2, sustain: 0 }
    }).toDestination();
    snareSynth.volume.value = -5;

    // Chord Synth
    const chordSynth = new Tone.PolySynth(Tone.Synth, {
      oscillator: { type: "fatsawtooth", count: 3, spread: 30 },
      envelope: { attack: 0.1, decay: 0.2, sustain: 0.5, release: 1 },
    }).toDestination();
    chordSynth.volume.value = -8;

    synths.current = [drumSynth, hatSynth, bassSynth, melodySynth, snareSynth, chordSynth];

    // Schedule
    Tone.Transport.bpm.value = bpm;
    Tone.Transport.loop = true;
    Tone.Transport.loopStart = 0;
    Tone.Transport.loopEnd = midi.duration;

    midi.tracks.forEach(track => {
      track.notes.forEach(note => {
        Tone.Transport.schedule((time) => {
          if (track.channel === 9) {
            if (note.midi === 36) drumSynth.triggerAttackRelease(note.name, note.duration, time, note.velocity);
            else if (note.midi === 42 || note.midi === 46) {
              const dur = Math.max(note.duration, 0.03);
              hatSynth.triggerAttackRelease(note.name, dur, time, note.velocity);
            }
            else snareSynth.triggerAttackRelease(note.duration, time, note.velocity);
          }
          else if (track.channel === 0) bassSynth.triggerAttackRelease(note.name, note.duration, time, note.velocity);
          else if (track.channel === 2) chordSynth.triggerAttackRelease(note.name, note.duration, time, note.velocity);
          else melodySynth.triggerAttackRelease(note.name, note.duration, time, note.velocity);
        }, note.time);
      });
    });
  };

  const togglePlayback = async () => {
    await Tone.start();
    if (isPlaying) {
      Tone.Transport.stop();
      setIsPlaying(false);
    } else {
      Tone.Transport.start();
      setIsPlaying(true);
    }
  };

  const downloadBeat = () => {
    if (!midiUrl) return;
    const a = document.createElement('a');
    a.href = midiUrl;
    a.download = songTitle ? `${songTitle}.mid` : `beatstorm_${selectedStyle}.mid`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <main className="flex-1 flex flex-col items-center justify-center p-8 gap-12 max-w-4xl mx-auto w-full">
      <header className="text-center space-y-4">
        <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent">
          Beat-Storm
        </h1>
        <p className="text-muted-foreground text-lg">
          AI-Powered MIDI Engine with Instant Preview
        </p>
        {songTitle && (
          <div className="animate-in fade-in slide-in-from-top-4 duration-500 mt-4">
            <span className="text-2xl font-mono text-cyan-400 font-bold drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]">
              {songTitle}
            </span>
          </div>
        )}
      </header>

      <section className="w-full space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">

        {/* Style Selector */}
        <div className="space-y-4">
          <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Select Style</label>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
            {STYLES.map((style) => (
              <button
                key={style.id}
                onClick={() => setSelectedStyle(style.id)}
                className={`
                  relative p-4 rounded-xl border text-left transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]
                  ${selectedStyle === style.id
                    ? 'border-primary bg-card/80 shadow-[0_0_20px_-5px_rgba(255,255,255,0.3)] ring-1 ring-primary/50'
                    : 'border-muted bg-card/40 hover:bg-card/60 hover:border-muted-foreground/50'}
                `}
              >
                <div className="font-semibold">{style.name}</div>
                <div className="text-xs text-muted-foreground mt-1">{style.description}</div>
                {selectedStyle === style.id && (
                  <div className="absolute inset-0 bg-primary/5 rounded-xl pointer-events-none" />
                )}
              </button>
            ))}
          </div>
        </div>

        {/* BPM and Bars */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="space-y-4 bg-card/30 p-6 rounded-2xl border border-muted/50">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Tempo (BPM)</label>
              <span className="text-2xl font-mono font-bold text-primary">{bpm}</span>
            </div>
            <input
              type="range"
              min="60"
              max="180"
              value={bpm}
              onChange={(e) => setBpm(Number(e.target.value))}
              className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
            />
          </div>

          <div className="space-y-4">
            <label className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Length</label>
            <div className="grid grid-cols-3 gap-4 h-[calc(100%-2rem)]">
              {[4, 8, 16].map((b) => (
                <button
                  key={b}
                  onClick={() => setBars(b)}
                  className={`
                    rounded-xl border text-center transition-all duration-200 font-semibold flex items-center justify-center text-lg
                    ${bars === b
                      ? 'border-primary bg-primary/10 text-primary ring-1 ring-primary/50'
                      : 'border-muted bg-card/40 hover:bg-card/60'}
                  `}
                >
                  {b} Bars
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Options */}
        <div className="flex items-center justify-center gap-4 p-4 bg-card/30 rounded-xl border border-muted/50">
          <label className="flex items-center gap-3 cursor-pointer group">
            <div className={`
                    w-6 h-6 rounded-md border flex items-center justify-center transition-all duration-200
                    ${includeChords ? 'bg-primary border-primary text-primary-foreground' : 'border-muted-foreground/50 group-hover:border-primary/50'}
                `}>
              {includeChords && <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
            </div>
            <input
              type="checkbox"
              className="hidden"
              checked={includeChords}
              onChange={(e) => setIncludeChords(e.target.checked)}
            />
            <span className="font-medium">Enable Chords</span>
          </label>
        </div>

        {/* Controls */}
        <div className="pt-8 flex flex-col md:flex-row gap-4">

          {/* Generate Button */}
          <button
            onClick={generateBeat}
            disabled={isGenerating}
            className={`
              flex-1 py-4 text-xl font-bold rounded-2xl transition-all duration-300
              ${isGenerating
                ? 'bg-muted cursor-not-allowed text-muted-foreground'
                : 'bg-primary text-primary-foreground hover:bg-white hover:scale-[1.01] hover:shadow-[0_0_40px_-10px_rgba(255,255,255,0.4)] active:scale-[0.99]'}
            `}
          >
            {isGenerating ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Processing...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="currentColor"><path d="M19.006 3.705a.75.75 0 01.512.921l-1.966 7.826 1.966 7.826a.75.75 0 01-1.456.366l-2.063-8.216-2.063 8.216a.75.75 0 01-1.455-.366l1.966-7.826-1.966-7.826a.75.75 0 011.456-.366l2.063 8.216 2.063-8.216a.75.75 0 01.921-.512zM6 6h12v12H6z" opacity="0" /><path d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                Generate New Beat
              </span>
            )}
          </button>

          {/* Play Loop Button */}
          <button
            onClick={togglePlayback}
            disabled={!isBeatReady}
            className={`
              flex-1 py-4 text-xl font-bold rounded-2xl transition-all duration-300 border
              ${!isBeatReady
                ? 'border-muted bg-card/30 text-muted-foreground cursor-not-allowed opacity-50'
                : isPlaying
                  ? 'border-red-500 bg-red-500/10 text-red-500 hover:bg-red-500/20'
                  : 'border-green-500 bg-green-500/10 text-green-500 hover:bg-green-500/20'}
            `}
          >
            {isPlaying ? (
              <span className="flex items-center justify-center gap-2">
                <svg width="24" height="24" fill="currentColor" viewBox="0 0 24 24"><rect x="6" y="4" width="4" height="16" /><rect x="14" y="4" width="4" height="16" /></svg>
                Stop
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <svg width="24" height="24" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                Play Loop
              </span>
            )}
          </button>

          {/* Download Button */}
          <button
            onClick={downloadBeat}
            disabled={!isBeatReady}
            className={`
              flex-1 py-4 text-xl font-bold rounded-2xl transition-all duration-300 border
              ${!isBeatReady
                ? 'border-muted bg-card/30 text-muted-foreground cursor-not-allowed opacity-50'
                : 'border-cyan-500 bg-cyan-500/10 text-cyan-500 hover:bg-cyan-500/20'}
            `}
          >
            <span className="flex items-center justify-center gap-2">
              <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" /></svg>
              Download
            </span>
          </button>
        </div>

      </section>
    </main>
  );
}
