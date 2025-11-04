import os
import queue
import sounddevice as sd
import vosk
import json
import argostranslate.translate

# --------------- Configuration ---------------
VOSK_MODEL_PATH = "models/vosk-model-small-en-us-0.15"  # English ASR model
SAMPLE_RATE = 16000
# ---------------------------------------------

# Step 1: Load Vosk offline speech recognition model
if not os.path.exists(VOSK_MODEL_PATH):
    raise FileNotFoundError(f"Vosk model not found at {VOSK_MODEL_PATH}\n"
                            f"Download one from https://alphacephei.com/vosk/models and unzip it into 'models/'")

model = vosk.Model(VOSK_MODEL_PATH)
recognizer = vosk.KaldiRecognizer(model, SAMPLE_RATE)

# Step 2: Load Argos Translate offline model (English → Hindi)
installed_languages = argostranslate.translate.get_installed_languages()
from_lang = next(filter(lambda l: l.code == "en", installed_languages))
to_lang = next(filter(lambda l: l.code == "hi", installed_languages))
translator = from_lang.get_translation(to_lang)

# Step 3: Setup real-time microphone stream
audio_q = queue.Queue()

def callback(indata, frames, time, status):
    if status:
        print(status)
    audio_q.put(bytes(indata))

print("🎙️ Speak something in English... (Ctrl+C to stop)\n")

with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16',
                       channels=1, callback=callback):
    while True:
        data = audio_q.get()
        if recognizer.AcceptWaveform(data):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
            if text.strip():
                print(f"🗣️ You said: {text}")
                translated = translator.translate(text)
                print(f"🌐 Translated (Hindi): {translated}\n")
