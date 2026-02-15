# Hindi Speech → English → Simplified English
# DEBUG VERSION (Shows Why File May Not Be Created)

import os
import json
import subprocess
import audioop
import platform
import datetime

import pyaudio
from vosk import Model, KaldiRecognizer
from argostranslate import translate as argostranslate

# ================= NLP SIMPLIFIER =================

import nltk
from nltk.corpus import wordnet as wn
from nltk import pos_tag
from wordfreq import zipf_frequency
from difflib import get_close_matches

nltk.download("wordnet", quiet=True)
nltk.download("averaged_perceptron_tagger_eng", quiet=True)

AUX_VERBS = {
    "am","is","are","was","were",
    "be","been","being",
    "do","does","did",
    "have","has","had",
    "will","would","shall","should",
    "may","might","must","can","could"
}

STOP_WORDS = {
    "the","a","an","in","on","at","of","to","for","from",
    "and","or","but","if","then","this","that","these","those"
}

SIMPLE_MAP = {
    "lethargic":"lazy",
    "fatigued":"tired",
    "commence":"start",
    "terminate":"end",
    "utilize":"use",
    "assist":"help",
    "assistance":"help",
    "purchase":"buy",
    "reside":"live",
}

def get_wordnet_pos(tag):
    if tag.startswith("J"): return wn.ADJ
    if tag.startswith("V"): return wn.VERB
    if tag.startswith("R"): return wn.ADV
    return None

def simplify_text(text):
    tokens = text.split()
    tagged = pos_tag(tokens)
    output = []
    for token, tag in tagged:
        output.append(token)
    return " ".join(output)

# ================= PATH CONFIG =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print("BASE_DIR:", BASE_DIR)

if platform.system() == "Windows":
    PIPER_BIN = os.path.join(BASE_DIR, "piper_windows_amd64", "piper", "piper.exe")
    PIPER_MODEL = os.path.join(BASE_DIR, "piper_windows_amd64", "piper", "en_US-lessac-medium.onnx")
else:
    PIPER_BIN = os.path.join(BASE_DIR, "piper", "piper")
    PIPER_MODEL = os.path.join(BASE_DIR, "en_US-lessac-medium.onnx")
    PIPER_CONFIG = PIPER_MODEL + ".json"

BLUETOOTH_SINK = "bluez_sink.74_D7_13_FD_39_CD.handsfree_head_unit"

# ================= VOSK =================

def find_vosk_model():
    for name in os.listdir(BASE_DIR):
        if name.lower().startswith("vosk-model") and "-hi-" in name.lower():
            return os.path.join(BASE_DIR, name)
    return None

VOSK_MODEL_PATH = find_vosk_model()
if not VOSK_MODEL_PATH:
    raise FileNotFoundError("Hindi Vosk model not found.")

FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 2048

model = Model(VOSK_MODEL_PATH)
p = pyaudio.PyAudio()

langs = argostranslate.get_installed_languages()
hi = next(l for l in langs if l.code == "hi")
en = next(l for l in langs if l.code == "en")
translator = hi.get_translation(en)

def open_stream():
    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] < 1:
                continue
            rate = int(info["defaultSampleRate"])
            stream = p.open(rate=rate, channels=1, format=FORMAT,
                            input=True, frames_per_buffer=FRAMES_PER_BUFFER,
                            input_device_index=i)
            print(f"🎧 Using mic [{i}] {info['name']} @ {rate} Hz")
            return KaldiRecognizer(model, rate), stream
        except:
            continue
    raise SystemExit("No working microphone found")

rec, stream = open_stream()

# ================= PIPER TTS =================

def speak_text_en(text):
    if not text.strip():
        return

    output_dir = os.path.join(BASE_DIR, "audio_outputs")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"tts_{timestamp}.wav")

    print("Saving to:", output_file)

    try:
        result = subprocess.run(
            [PIPER_BIN, "-m", PIPER_MODEL, "-c", PIPER_CONFIG, "-f", output_file],
            input=text.encode("utf-8"),
            capture_output=True
        )

        print("Piper return code:", result.returncode)
        if result.stderr:
            print("Piper stderr:", result.stderr.decode())

        print("File exists after piper?", os.path.exists(output_file))

        if os.path.exists(output_file):
            subprocess.run(
                [
                    "paplay",
                    "--rate=16000",
                    "--device=" + BLUETOOTH_SINK,
                    output_file
                ]
            )
        else:
            print("❌ File was not created.")

    except Exception as e:
        print("TTS Error:", e)

# ================= MAIN =================

print("\n🎤 Speak Hindi (Ctrl+C to exit)\n")

try:
    while True:
        data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
        if rec.AcceptWaveform(data):
            spoken_hi = json.loads(rec.Result()).get("text", "")
            if not spoken_hi:
                continue

            print("🗣 Hindi:", spoken_hi)

            english = translator.translate(spoken_hi)
            print("🇬🇧 English:", english)

            speak_text_en(english)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    stream.close()
    p.terminate()
