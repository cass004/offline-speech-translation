# translator_full.py
# Requirements:
# pip install vosk pyttsx3 argostranslate gTTS playsound==1.2.2
# eSpeak NG installed (default path used below). Argos en->hi model must be installed.

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

# ---------------- CONFIG ----------------
VOSK_MODEL_PATH = r"D:/VIT Vellore/Project/Project 1/Offline Code Trial 2/vosk-model-small-en-us-0.15"
ESPEAK_PATH = r"C:\Program Files\eSpeak NG\espeak-ng.exe"
PREFERRED_INDEX = 24
FALLBACK_INDEX = 1

CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 2048
SILENCE_FRAME_LIMIT = 60
VAD_RMS_THRESHOLD = 600
VAD_FRAMES_TO_START = 2

# ---------------- INIT ----------------
if not os.path.exists(VOSK_MODEL_PATH):
    raise FileNotFoundError(f"Vosk model not found at: {VOSK_MODEL_PATH}")

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

# ---------------- AUDIO STREAM (FIXED ONLY HERE) ----------------
def open_stream():
    global stream, rec

    # 1️⃣ Preferred device (unchanged logic)
    try:
        pref_info = p.get_device_info_by_index(PREFERRED_INDEX)
        pref_rate = int(pref_info.get('defaultSampleRate', 16000))
        pref_rate = 16000 if pref_rate == 16000 else pref_rate

        stream = p.open(
            rate=pref_rate,
            channels=CHANNELS,
            format=FORMAT,
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
            input_device_index=PREFERRED_INDEX
        )
        rec = KaldiRecognizer(model, pref_rate)
        print("🎧 Using preferred device:", pref_info["name"])
        print("Audio stream opened with rate:", pref_rate)
        return rec, stream
    except Exception as e:
        print("⚠ Preferred device failed:", e)

    # 2️⃣ Fallback device (unchanged logic)
    try:
        def_info = p.get_device_info_by_index(FALLBACK_INDEX)
        def_rate = int(def_info.get('defaultSampleRate', 44100))

        stream = p.open(
            rate=def_rate,
            channels=CHANNELS,
            format=FORMAT,
            input=True,
            frames_per_buffer=FRAMES_PER_BUFFER,
            input_device_index=FALLBACK_INDEX
        )
        rec = KaldiRecognizer(model, def_rate)
        print("🎧 Using fallback device:", def_info["name"])
        print("Audio stream opened with rate:", def_rate)
        return rec, stream
    except Exception as e:
        print("⚠ Fallback device failed:", e)

    # 3️⃣ AUTO scan (added – FIX)
    print("🔍 Scanning for working microphone...")
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
            print(f"🎧 Auto-selected device [{i}]: {info['name']}")
            print("Audio stream opened with rate:", rate)
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
            if "hi" in str(v.languages).lower() or "hindi" in v.name.lower():
                engine.setProperty("voice", v.id)
                engine.say(text)
                engine.runAndWait()
                return True
    except Exception:
        pass
    return False

def tts_espeak_ng(text):
    if not os.path.isfile(ESPEAK_PATH):
        return False
    try:
        subprocess.run([ESPEAK_PATH, "-v", "hi", text], check=False)
        return True
    except Exception:
        return False

def tts_gtts_fallback(text):
    if not HAS_GTTS:
        return False
    tmp = tempfile.mktemp(".mp3")
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

        rms = audioop.rms(data, 2) if data else 0

        if rms >= VAD_RMS_THRESHOLD:
            voiced_frames += 1
            silent_frames = 0
            if not in_speech and voiced_frames >= VAD_FRAMES_TO_START:
                in_speech = True
                rec.Reset()
        else:
            voiced_frames = 0
            silent_frames += 1 if in_speech else 0

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
