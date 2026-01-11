# translator_portable.py
# Fully portable Offline English → Hindi Speech Translator
#
# Requirements:
# pip install vosk pyaudio pyttsx3 argostranslate gTTS playsound==1.2.2
# Argos translate-en_hi.argosmodel installed
# (Optional) eSpeak NG installed

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

# ---------------- PORTABLE SETUP ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_vosk_model():
    for name in os.listdir(BASE_DIR):
        if name.lower().startswith("vosk-model") and os.path.isdir(os.path.join(BASE_DIR, name)):
            return os.path.join(BASE_DIR, name)
    return None

VOSK_MODEL_PATH = find_vosk_model()

if not VOSK_MODEL_PATH:
    raise SystemExit(
        "\n❌ No Vosk model found.\n"
        "➡ Download an English Vosk model\n"
        "➡ Extract it into the SAME folder as this script\n"
        "➡ Folder name must start with 'vosk-model'\n"
    )

print("✅ Using Vosk model:", os.path.basename(VOSK_MODEL_PATH))

# ---------------- AUDIO CONFIG ----------------
PREFERRED_INDEX = 24
FALLBACK_INDEX = 1

CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 2048
SILENCE_FRAME_LIMIT = 60
VAD_RMS_THRESHOLD = 600
VAD_FRAMES_TO_START = 2

# ---------------- INIT ----------------
model = Model(VOSK_MODEL_PATH)
p = pyaudio.PyAudio()

# ---------------- ARGOS TRANSLATE ----------------
langs = argotranslate.get_installed_languages()
en_lang = next((l for l in langs if l.code == "en"), None)
hi_lang = next((l for l in langs if l.code == "hi"), None)

if not (en_lang and hi_lang):
    raise SystemExit("❌ Argos en→hi model not installed")

translation_obj = en_lang.get_translation(hi_lang)

# ---------------- AUDIO STREAM ----------------
def open_stream():
    try:
        info = p.get_device_info_by_index(PREFERRED_INDEX)
        rate = int(info.get("defaultSampleRate", 16000))
        rate = 16000 if rate != 16000 else rate
        stream = p.open(rate=rate, channels=CHANNELS, format=FORMAT,
                        input=True, frames_per_buffer=FRAMES_PER_BUFFER,
                        input_device_index=PREFERRED_INDEX)
    except Exception:
        info = p.get_device_info_by_index(FALLBACK_INDEX)
        rate = int(info.get("defaultSampleRate", 44100))
        stream = p.open(rate=rate, channels=CHANNELS, format=FORMAT,
                        input=True, frames_per_buffer=FRAMES_PER_BUFFER,
                        input_device_index=FALLBACK_INDEX)

    print("🎧 Audio stream opened at", rate, "Hz")
    return KaldiRecognizer(model, rate), stream

rec, stream = open_stream()

# ---------------- TTS ----------------
def speak_text_hi(text):
    if not text:
        return

    # Try pyttsx3
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return
    except Exception:
        pass

    # Try eSpeak (if available in PATH)
    try:
        subprocess.run(["espeak-ng", "-v", "hi", text], check=False)
        return
    except Exception:
        pass

    # gTTS fallback
    if HAS_GTTS:
        tmp = tempfile.mktemp(".mp3")
        try:
            gTTS(text=text, lang="hi").save(tmp)
            playsound(tmp)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

# ---------------- SPEECH RECOGNITION ----------------
def recognize_speech():
    rec.Reset()
    silent = voiced = 0
    in_speech = False

    print("🎙 Listening...")

    while True:
        data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
        rms = audioop.rms(data, 2)

        if rms >= VAD_RMS_THRESHOLD:
            voiced += 1
            silent = 0
            if voiced >= VAD_FRAMES_TO_START:
                in_speech = True
        else:
            silent += 1
            voiced = 0

        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            return result.get("text", "").strip()

        if in_speech and silent > SILENCE_FRAME_LIMIT:
            return ""

# ---------------- MAIN LOOP ----------------
if __name__ == "__main__":
    print("\n✅ Ready — Speak English (Ctrl+C to exit)\n")

    try:
        while True:
            spoken = recognize_speech()

            if spoken:
                print("🗣 You said:", spoken)

                translated = translation_obj.translate(spoken)
                print("🇮🇳 Hindi:", translated)

                speak_text_hi(translated)

            time.sleep(0.2)

    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
