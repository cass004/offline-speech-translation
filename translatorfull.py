# ============================================================
# Hindi → English → Simplified AI Translator
# Wake Once → Continuous Listening
# Landscape 480x320
# Only Piper Fix + Bottom Spacing
# ============================================================

import os
import json
import subprocess
import tempfile
import platform
import threading
import tkinter as tk
import pyaudio
import nltk

from vosk import Model, KaldiRecognizer
from argostranslate import translate as argostranslate
from nltk.corpus import wordnet as wn
from nltk import pos_tag
from wordfreq import zipf_frequency
from difflib import get_close_matches

# ================= BASE PATH =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ================= AUTO MODEL DETECT =================

def find_model(lang_code):
    for name in os.listdir(BASE_DIR):
        lower = name.lower()
        if lower.startswith("vosk-model") and f"-{lang_code}-" in lower:
            return os.path.join(BASE_DIR, name)
    return None

EN_MODEL_PATH = find_model("en")
HI_MODEL_PATH = find_model("hi")

if not EN_MODEL_PATH:
    raise FileNotFoundError("English model not found.")
if not HI_MODEL_PATH:
    raise FileNotFoundError("Hindi model not found.")

# ================= TRANSLATOR =================

langs = argostranslate.get_installed_languages()
hi = next(l for l in langs if l.code == "hi")
en = next(l for l in langs if l.code == "en")
translator = hi.get_translation(en)

# ================= NLP SIMPLIFIER =================

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
    best = max(candidates, key=lambda w: zipf_frequency(w, "en"))
    return best if zipf_frequency(best, "en") > zipf_frequency(word, "en") else word

def simplify_text(text):
    tokens = text.split()
    tagged = pos_tag(tokens)
    output = []
    for token, tag in tagged:
        clean = token.strip(".,?!").lower()
        if clean in AUX_VERBS or clean in STOP_WORDS:
            output.append(token)
            continue
        if tag.startswith("N"):
            output.append(token)
            continue
        corrected = autocorrect(clean)
        wn_pos = get_wordnet_pos(tag)
        simple = get_simpler_word(corrected, wn_pos)
        output.append(token.replace(clean, simple) if simple != clean else token)
    return " ".join(output)

# ================= INTELLIGENT CORRECTION (UNCHANGED) =================

def intelligent_correction(hindi_text, english_text):
    eng = english_text.lower().strip()
    if "कैसे हो" in hindi_text or "कैसे हैं" in hindi_text:
        return "How are you?"
    if "क्या कर रहे" in hindi_text:
        return "What are you doing?"
    if eng.startswith("what are") and "doing" not in eng:
        return "What are you doing?"
    eng = eng.capitalize()
    if any(w in eng.lower() for w in ["how","what","why","when","where"]):
        if not eng.endswith("?"):
            eng += "?"
    return eng

# ================= PIPER FIX ONLY =================

if platform.system() == "Windows":
    PIPER_BIN = os.path.join(BASE_DIR,"piper_windows_amd64","piper","piper.exe")
    PIPER_MODEL = os.path.join(BASE_DIR,"piper_windows_amd64","piper","en_US-lessac-medium.onnx")
else:
    PIPER_BIN = os.path.join(BASE_DIR,"piper","piper")
    PIPER_MODEL = os.path.join(BASE_DIR,"piper","en_US-lessac-medium.onnx")
    PIPER_CONFIG = PIPER_MODEL + ".json"

def speak_text_en(text):
    if not text.strip():
        return

    tmp_wav = tempfile.mktemp(".wav")

    if platform.system() == "Windows":
        subprocess.run(
            [PIPER_BIN,"--model",PIPER_MODEL,"--output_file",tmp_wav],
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if os.path.exists(tmp_wav):
            import winsound
            winsound.PlaySound(tmp_wav, winsound.SND_FILENAME)
            os.remove(tmp_wav)
    else:
        subprocess.run(
            [PIPER_BIN,"-m",PIPER_MODEL,"-c",PIPER_CONFIG,"-f",tmp_wav],
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if os.path.exists(tmp_wav):
            subprocess.run(["aplay",tmp_wav])
            os.remove(tmp_wav)

# ================= ASSISTANT LOOP (UNCHANGED) =================

def assistant_loop(ui):

    wake_model = Model(EN_MODEL_PATH)
    hindi_model = Model(HI_MODEL_PATH)
    p = pyaudio.PyAudio()

    ui.show_waiting()

    wake_stream = p.open(format=pyaudio.paInt16,
                         channels=1,
                         rate=16000,
                         input=True,
                         frames_per_buffer=2048)

    wake_rec = KaldiRecognizer(wake_model,16000)

    while True:
        data = wake_stream.read(2048, exception_on_overflow=False)
        if wake_rec.AcceptWaveform(data):
            if "hello" in json.loads(wake_rec.Result()).get("text",""):
                break

    wake_stream.close()

    ui.set_listening_mode()
    ui.show_listening()

    hindi_stream = p.open(format=pyaudio.paInt16,
                          channels=1,
                          rate=16000,
                          input=True,
                          frames_per_buffer=2048)

    hindi_rec = KaldiRecognizer(hindi_model,16000)

    while True:
        data = hindi_stream.read(2048, exception_on_overflow=False)

        if hindi_rec.AcceptWaveform(data):
            spoken_hi = json.loads(hindi_rec.Result()).get("text","")
            if not spoken_hi:
                continue

            ui.show_hindi(spoken_hi)

            english_raw = translator.translate(spoken_hi)
            english = intelligent_correction(spoken_hi, english_raw)

            ui.last_hindi = spoken_hi
            ui.last_english = english

            ui.show_translation(english)
            speak_text_en(english)

# ================= GUI (ONLY SPACING ADDED) =================

class ModernTranslatorUI:

    def __init__(self, root):
        self.root = root
        self.root.title("AI Speech Translator")
        self.root.geometry("480x320")
        self.root.configure(bg="#000000")
        self.root.resizable(False, False)

        self.last_hindi = None
        self.last_english = None

        self.build_ui()

        threading.Thread(
            target=assistant_loop,
            args=(self,),
            daemon=True
        ).start()

    def build_ui(self):

        top_frame = tk.Frame(self.root, bg="#000000")
        top_frame.pack(fill="x", pady=5)

        self.light_canvas = tk.Canvas(
            top_frame,
            width=15,
            height=15,
            bg="#000000",
            highlightthickness=0
        )
        self.light_canvas.pack(side="left", padx=10)

        self.light = self.light_canvas.create_oval(
            2, 2, 13, 13,
            fill="gray"
        )

        self.container = tk.Frame(self.root, bg="#000000")
        self.container.pack(expand=True, pady=(0, 40))

        self.hindi_label = tk.Label(
            self.container,
            text="",
            font=("Segoe UI", 14),
            fg="#AAAAAA",
            bg="#000000",
            wraplength=460,
            justify="center"
        )
        self.hindi_label.pack(pady=3)

        self.english_label = tk.Label(
            self.container,
            text="",
            font=("Segoe UI", 26, "bold"),
            fg="white",
            bg="#000000",
            wraplength=460,
            justify="center"
        )
        self.english_label.pack(pady=3)

        tk.Button(
            self.root,
            text="✨ Simplify",
            font=("Segoe UI", 12, "bold"),
            bg="#222222",
            fg="white",
            relief="flat",
            command=self.simplify
        ).pack(pady=(0, 25))

    def show_waiting(self):
        self.hindi_label.config(text="")
        self.english_label.config(text="Waiting for wake word...")
        self.set_idle_mode()

    def show_listening(self):
        self.hindi_label.config(text="")
        self.english_label.config(text="Listening...")

    def show_hindi(self, text):
        self.hindi_label.config(text="")
        self.english_label.config(text=text)

    def show_translation(self, english_text):
        self.hindi_label.config(text=self.last_hindi)
        self.english_label.config(text=english_text)

    def simplify(self):
        if self.last_english:
            simplified = simplify_text(self.last_english)
            self.english_label.config(text=simplified)
            speak_text_en(simplified)

    def set_idle_mode(self):
        self.light_canvas.itemconfig(self.light, fill="gray")

    def set_listening_mode(self):
        self.light_canvas.itemconfig(self.light, fill="#00FF00")

# ================= START =================

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernTranslatorUI(root)
    root.mainloop()
