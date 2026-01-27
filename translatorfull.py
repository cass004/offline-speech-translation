# Hindi Speech → English (audio) → Simplified English (audio)
# FINAL SEMANTIC-SAFE VERSION

import os
import json
import subprocess
import audioop
import tempfile

import pyaudio
from vosk import Model, KaldiRecognizer
from argostranslate import translate as argostranslate

# ---------------- OPTIONAL TTS ----------------
try:
    from gtts import gTTS
    from playsound import playsound
    HAS_GTTS = True
except Exception:
    HAS_GTTS = False

# ================= NLP SIMPLIFIER =================
import nltk
from nltk.corpus import wordnet as wn
from nltk import pos_tag
from wordfreq import zipf_frequency
from difflib import get_close_matches

nltk.download("wordnet", quiet=True)
nltk.download("averaged_perceptron_tagger_eng", quiet=True)

# ---- FUNCTION WORDS (NEVER MODIFY) ----
AUX_VERBS = {
    "am", "is", "are", "was", "were",
    "be", "been", "being",
    "do", "does", "did",
    "have", "has", "had",
    "will", "would", "shall", "should",
    "may", "might", "must", "can", "could"
}

STOP_WORDS = {
    "the", "a", "an",
    "in", "on", "at", "of", "to", "for", "from",
    "and", "or", "but", "if", "then",
    "this", "that", "these", "those"
}

# ---- MANUAL SAFE SIMPLIFICATIONS ----
SIMPLE_MAP = {
    "lethargic": "lazy",
    "fatigued": "tired",
    "commence": "start",
    "terminate": "end",
    "utilize": "use",
    "assist": "help",
    "assistance": "help",
    "purchase": "buy",
    "reside": "live",
}

def get_wordnet_pos(tag):
    if tag.startswith("J"):
        return wn.ADJ
    if tag.startswith("V"):
        return wn.VERB
    if tag.startswith("R"):
        return wn.ADV
    return None

# ✅ AUTOCORRECT ONLY UNKNOWN WORDS
def autocorrect(word):
    if wn.synsets(word):
        return word
    matches = get_close_matches(word, wn.words(), n=1, cutoff=0.85)
    return matches[0] if matches else word

def get_simpler_word(word, pos=None):
    if word in SIMPLE_MAP:
        return SIMPLE_MAP[word]

    if not pos:
        return word

    synsets = wn.synsets(word, pos=pos)
    if not synsets:
        return word

    candidates = set()
    for syn in synsets:
        for lemma in syn.lemmas():
            candidates.add(lemma.name().replace("_", " "))

    if not candidates:
        return word

    best = max(candidates, key=lambda w: zipf_frequency(w, "en"))
    return best if zipf_frequency(best, "en") > zipf_frequency(word, "en") else word

# ✅ FINAL SAFE SIMPLIFIER
def simplify_text(text):
    tokens = text.split()
    tagged = pos_tag(tokens)
    output = []

    for token, tag in tagged:
        clean = token.strip(".,?!").lower()

        # 🚫 NEVER TOUCH FUNCTION WORDS
        if clean in AUX_VERBS or clean in STOP_WORDS:
            output.append(token)
            continue

        # 🚫 NEVER SIMPLIFY NOUNS (critical rule)
        if tag.startswith("N"):
            output.append(token)
            continue

        corrected = autocorrect(clean)
        wn_pos = get_wordnet_pos(tag)
        simple = get_simpler_word(corrected, wn_pos)

        output.append(token.replace(clean, simple) if simple != clean else token)

    return " ".join(output)

# ================= AUDIO CONFIG =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_vosk_model():
    for name in os.listdir(BASE_DIR):
        if name.lower().startswith("vosk-model"):
            path = os.path.join(BASE_DIR, name)
            if os.path.isdir(path):
                return path
    return None

VOSK_MODEL_PATH = find_vosk_model()
if not VOSK_MODEL_PATH:
    raise FileNotFoundError("Put vosk-model-small-hi-* beside this script")

ESPEAK_PATH = "espeak-ng"

FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 2048
SILENCE_FRAME_LIMIT = 60
VAD_RMS_THRESHOLD = 600
VAD_FRAMES_TO_START = 2

model = Model(VOSK_MODEL_PATH)
p = pyaudio.PyAudio()

# ================= ARGOS (HI → EN) =================
langs = argostranslate.get_installed_languages()
hi = next(l for l in langs if l.code == "hi")
en = next(l for l in langs if l.code == "en")
translator = hi.get_translation(en)

# ================= AUDIO STREAM =================
def open_stream():
    for i in range(p.get_device_count()):
        try:
            info = p.get_device_info_by_index(i)
            if info["maxInputChannels"] < 1:
                continue
            rate = int(info["defaultSampleRate"])
            stream = p.open(
                rate=rate,
                channels=1,
                format=FORMAT,
                input=True,
                frames_per_buffer=FRAMES_PER_BUFFER,
                input_device_index=i
            )
            print(f"🎧 Using mic [{i}] {info['name']} @ {rate} Hz")
            return KaldiRecognizer(model, rate), stream
        except Exception:
            continue
    raise SystemExit("No working microphone found")

rec, stream = open_stream()

# ================= TTS =================
def speak_text_en(text):
    if not text.strip():
        return

    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        return
    except Exception:
        pass

    try:
        subprocess.run(
            [ESPEAK_PATH, "-v", "en", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return
    except Exception:
        pass

    if HAS_GTTS:
        try:
            tmp = tempfile.mktemp(".mp3")
            gTTS(text=text, lang="en").save(tmp)
            playsound(tmp)
            os.remove(tmp)
        except Exception:
            pass

# ================= SPEECH RECOGNITION =================
def recognize_speech():
    rec.Reset()
    silent = voiced = 0
    in_speech = False

    while True:
        data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
        rms = audioop.rms(data, 2)

        if rms >= VAD_RMS_THRESHOLD:
            voiced += 1
            silent = 0
            if not in_speech and voiced >= VAD_FRAMES_TO_START:
                in_speech = True
                rec.Reset()
        else:
            silent += 1
            voiced = 0

        if rec.AcceptWaveform(data):
            text = json.loads(rec.Result()).get("text", "")
            if text:
                return text

        if in_speech and silent > SILENCE_FRAME_LIMIT:
            return ""

# ================= MAIN =================
print("\n🎤 Speak Hindi (Ctrl+C to exit)\n")

try:
    while True:
        spoken_hi = recognize_speech()
        if not spoken_hi:
            continue

        print("🗣 Hindi:", spoken_hi)

        english = translator.translate(spoken_hi)
        print("🇬🇧 English:", english)
        speak_text_en(english)

        if input("Simplify English sentence? (y/n): ").strip().lower() == "y":
            simplified = simplify_text(english)
            print("✨ Simplified English:", simplified)
            speak_text_en(simplified)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    stream.close()
    p.terminate()
