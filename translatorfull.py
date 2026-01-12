# translator_full_portable_fixed.py
# SAME LOGIC as your translator_full.py
# Only fixes: audio input error + hardcoded paths

import os
import json
import time
import subprocess
import audioop
import tempfile

import pyaudio
from vosk import Model, KaldiRecognizer
from argostranslate import translate as argotranslate

# Optional gTTS fallback
try:
    from gtts import gTTS
    from playsound import playsound
    HAS_GTTS = True
except Exception:
    HAS_GTTS = False

# ---------------- CONFIG (PORTABLE) ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔹 Auto-detect Vosk model folder
def find_vosk_model():
    for name in os.listdir(BASE_DIR):
        if name.lower().startswith("vosk-model"):
            path = os.path.join(BASE_DIR, name)
            if os.path.isdir(path):
                return path
    return None

VOSK_MODEL_PATH = find_vosk_model()
if not VOSK_MODEL_PATH:
    raise FileNotFoundError(
        "Vosk model not found.\n"
        "➡ Put vosk-model-* folder in the SAME directory as this script"
    )

# 🔹 eSpeak optional (won’t crash if missing)
ESPEAK_PATH = "espeak-ng"   # relies on PATH if installed

CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 2048
SILENCE_FRAME_LIMIT = 60
VAD_RMS_THRESHOLD = 600
VAD_FRAMES_TO_START = 2

# ---------------- INIT ----------------
model = Model(VOSK_MODEL_PATH)
p = pyaudio.PyAudio()
rec = None
stream = None

# ---------------- ARGOS TRANSLATE ----------------
langs = argotranslate.get_installed_languages()
en_lang = next((l for l in langs if l.code == "en"), None)
hi_lang = next((l for l in langs if l.code == "hi"), None)

if not (en_lang and hi_lang):
    raise SystemExit("Argos en/hi model not installed.")

translation_obj = en_lang.get_translation(hi_lang)

# ---------------- AUDIO STREAM (AUTO DEVICE) ----------------
def open_stream():
    global stream, rec

    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) < 1:
                continue

            rate = int(info.get("defaultSampleRate", 16000))
            if rate not in (8000, 16000, 44100, 48000):
                rate = 16000

            stream = p.open(
                rate=rate,
                channels=CHANNELS,
                format=FORMAT,
                input=True,
                frames_per_buffer=FRAMES_PER_BUFFER,
                input_device_index=i
            )

            rec = KaldiRecognizer(model, rate)
            print(f"🎧 Using mic [{i}] {info['name']} @ {rate} Hz")
            return rec, stream

        except Exception:
            continue

    raise SystemExit("❌ No working audio input device found")

rec, stream = open_stream()

# ---------------- TTS helpers (UNCHANGED) ----------------
def tts_pyttsx3_hi(text):
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        for v in voices:
            repr_v = (getattr(v, "id", "") + " " + getattr(v, "name", "") + " " +
                      str(getattr(v, "languages", ""))).lower()
            if "hi" in repr_v or "hindi" in repr_v or "hi-in" in repr_v:
                engine.setProperty("voice", v.id)
                engine.say(text)
                engine.runAndWait()
                return True
    except Exception:
        pass
    return False

def tts_espeak_ng(text):
    try:
        subprocess.run([ESPEAK_PATH, "-v", "hi", text], check=False)
        return True
    except Exception:
        return False

def tts_gtts_fallback(text):
    if not HAS_GTTS:
        return False
    tmp = tempfile.mktemp(suffix=".mp3")
    try:
        gTTS(text=text, lang='hi').save(tmp)
        playsound(tmp)
        return True
    except Exception:
        return False
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass

def speak_text_hi(text):
    if not text:
        return
    if tts_pyttsx3_hi(text):
        return
    if tts_espeak_ng(text):
        return
    if tts_gtts_fallback(text):
        return
    print("[TTS] No TTS available:", text)

# ---------------- VAD + Recognizer (UNCHANGED) ----------------
def recognize_speech():
    rec.Reset()
    print("🎙 Listening...")
    silent_frames = 0
    voiced_frames = 0
    in_speech = False

    while True:
        try:
            data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
        except Exception:
            time.sleep(0.05)
            continue

        if not data:
            silent_frames += 1
            if silent_frames > SILENCE_FRAME_LIMIT:
                rec.Reset()
                return ""
            continue

        rms = audioop.rms(data, 2)

        if rms >= VAD_RMS_THRESHOLD:
            voiced_frames += 1
            silent_frames = 0
            if not in_speech and voiced_frames >= VAD_FRAMES_TO_START:
                in_speech = True
                rec.Reset()
        else:
            if in_speech:
                silent_frames += 1
            else:
                silent_frames = 0
            voiced_frames = 0

        if rec.AcceptWaveform(data):
            res = json.loads(rec.Result())
            text = res.get("text", "").strip()
            if text:
                return text

        if in_speech and silent_frames > SILENCE_FRAME_LIMIT:
            rec.Reset()
            return ""

        time.sleep(0.005)

# ---------------- MAIN LOOP (UNCHANGED) ----------------
if __name__ == "__main__":
    print("Ready. Press Ctrl+C to quit.")
    try:
        while True:
            spoken = recognize_speech()
            if spoken:
                print("You said:", spoken)
                translated_hi = translation_obj.translate(spoken)
                print("Translated (hi):", translated_hi)
                speak_text_hi(translated_hi)
            else:
                time.sleep(0.2)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        try:
            stream.stop_stream()
            stream.close()
        except Exception:
            pass
        p.terminate()
