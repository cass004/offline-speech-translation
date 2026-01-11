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
ESPEAK_PATH = r"C:\Program Files\eSpeak NG\espeak-ng.exe"   # adjust if installed elsewhere
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

# Argos translate object
langs = argotranslate.get_installed_languages()
en_lang = next((l for l in langs if l.code == "en"), None)
hi_lang = next((l for l in langs if l.code == "hi"), None)
if not (en_lang and hi_lang):
    raise SystemExit("Argos en/hi model not installed. Install translate-en_hi.argosmodel first.")
translation_obj = en_lang.get_translation(hi_lang)

def open_stream():
    global stream, rec
    try:
        pref_info = p.get_device_info_by_index(PREFERRED_INDEX)
        pref_rate = int(pref_info.get('defaultSampleRate', 16000))
        pref_rate = 16000 if int(pref_rate) == 16000 else pref_rate
        stream = p.open(rate=pref_rate, channels=CHANNELS, format=FORMAT,
                        input=True, frames_per_buffer=FRAMES_PER_BUFFER,
                        input_device_index=PREFERRED_INDEX)
        recognizer_rate = pref_rate
    except Exception:
        def_info = p.get_device_info_by_index(FALLBACK_INDEX)
        def_rate = int(def_info.get('defaultSampleRate', 44100))
        stream = p.open(rate=def_rate, channels=CHANNELS, format=FORMAT,
                        input=True, frames_per_buffer=FRAMES_PER_BUFFER,
                        input_device_index=FALLBACK_INDEX)
        recognizer_rate = def_rate
    rec = KaldiRecognizer(model, recognizer_rate)
    print("Audio stream opened with rate:", recognizer_rate)
    return rec, stream

rec, stream = open_stream()

# ---------------- TTS helpers ----------------
def tts_pyttsx3_hi(text):
    # tries to use a Hindi SAPI voice if it ever exists
    try:
        import pyttsx3
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
        for v in voices:
            repr_v = (getattr(v, "id", "") + " " + getattr(v, "name", "") + " " + str(getattr(v, "languages", ""))).lower()
            if "hi" in repr_v or "hindi" in repr_v or "hi-in" in repr_v:
                engine.setProperty("voice", v.id)
                engine.say(text)
                engine.runAndWait()
                return True
    except Exception:
        pass
    return False

def tts_espeak_ng(text):
    # use eSpeak direct
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
    # prefer SAPI Hindi if available
    if tts_pyttsx3_hi(text):
        return
    # then eSpeak NG offline
    if tts_espeak_ng(text):
        return
    # then online fallback
    if tts_gtts_fallback(text):
        return
    # last resort: create WAV using eSpeak or TTS
    try:
        wav = os.path.join(tempfile.gettempdir(), "translator_hi.wav")
        if os.path.isfile(ESPEAK_PATH):
            subprocess.run([ESPEAK_PATH, "-v", "hi", "-w", wav, text], check=False)
            # play via windows default
            os.startfile(wav)
            return
    except Exception:
        pass
    print("[TTS] No TTS available. Translated text:", text)

# ---------------- VAD + Recognizer ----------------
def recognize_speech():
    rec.Reset()
    print("🎙 Listening...")
    silent_frames = 0
    voiced_frames = 0
    in_speech = False
    while True:
        try:
            data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
        except Exception as e:
            print("Stream read error:", e)
            time.sleep(0.05)
            continue
        if not data or len(data) == 0:
            silent_frames += 1
            if silent_frames > SILENCE_FRAME_LIMIT:
                rec.Reset()
                return ""
            continue
        try:
            rms = audioop.rms(data, 2)
        except Exception:
            rms = 0
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
        else:
            # partial = json.loads(rec.PartialResult()).get("partial","")
            pass
        if in_speech and silent_frames > SILENCE_FRAME_LIMIT:
            rec.Reset()
            return ""
        time.sleep(0.005)

# ---------------- MAIN LOOP ----------------
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

print{"start")
