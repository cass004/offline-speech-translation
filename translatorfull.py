# ============================================================
# Hindi → English → Simplified AI Translator
# OFFLINE + ONLINE (FULL FINAL VERSION)
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
import socket
import speech_recognition as sr
from deep_translator import GoogleTranslator

from vosk import Model, KaldiRecognizer
from argostranslate import translate as argostranslate
from nltk.corpus import wordnet as wn
from nltk import pos_tag
from wordfreq import zipf_frequency
from difflib import get_close_matches

import time

# Latency tracking
t_start = 0
t_text = 0
t_audio = 0
# ================= MODE =================
MODE = "OFFLINE"

# ================= LANGUAGE MODE =================
LANG_PAIR = "HI_EN"
LANG_MODE = "HI_TO_EN"

# ================= NETWORK =================
def is_connected():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except:
        return False

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
ES_MODEL_PATH = find_model("es")

if not EN_MODEL_PATH:
    raise FileNotFoundError("English model not found.")
if not HI_MODEL_PATH:
    raise FileNotFoundError("Hindi model not found.")
if not ES_MODEL_PATH:
    raise FileNotFoundError("Spanish model not found.")

# ================= TRANSLATOR =================
langs = argostranslate.get_installed_languages()
hi = next(l for l in langs if l.code == "hi")
en = next(l for l in langs if l.code == "en")
es = next(l for l in langs if l.code == "es")

translator_hi_en = hi.get_translation(en)
translator_en_hi = en.get_translation(hi)
translator_es_en = es.get_translation(en)
translator_en_es = en.get_translation(es)

# ================= NLP SIMPLIFIER =================
nltk.download("wordnet", quiet=True)
nltk.download("averaged_perceptron_tagger_eng", quiet=True)

AUX_VERBS = {
    "am","is","are","was","were","be","been","being",
    "do","does","did","have","has","had",
    "will","would","shall","should","may","might","must","can","could"
}

STOP_WORDS = {
    "the","a","an","in","on","at","of","to","for","from",
    "and","or","but","if","then","this","that","these","those"
}

SIMPLE_MAP = {
    "lethargic":"lazy","fatigued":"tired","commence":"start",
    "terminate":"end","utilize":"use","assist":"help",
    "assistance":"help","purchase":"buy","reside":"live",
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

# ================= INTELLIGENT CORRECTION =================
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

# ================= PIPER =================
if platform.system() == "Windows":
    PIPER_BIN = os.path.join(BASE_DIR,"piper_windows_amd64","piper","piper.exe")
    PIPER_MODEL = os.path.join(BASE_DIR,"piper_windows_amd64","piper","en_US-lessac-medium.onnx")
else:
    PIPER_BIN = os.path.join(BASE_DIR,"piper","piper")
    PIPER_MODEL = os.path.join(BASE_DIR,"piper","en_US-lessac-medium.onnx")
    PIPER_CONFIG = PIPER_MODEL + ".json"

def speak_text_en(text, ui=None):
    if not text.strip():
        return

    import time

    tmp_wav = tempfile.mktemp(".wav")

    # ⏱ Generate audio (THIS TAKES TIME)
    gen_start = time.time()

    if platform.system() == "Windows":
        subprocess.run(
            [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", tmp_wav],
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    else:
        subprocess.run(
            [PIPER_BIN, "-m", PIPER_MODEL, "-c", PIPER_CONFIG, "-f", tmp_wav],
            input=text.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    gen_end = time.time()

    if os.path.exists(tmp_wav):

        play_start = time.time()   # 🎯 REAL AUDIO START

        if platform.system() == "Windows":
            import winsound
            winsound.PlaySound(tmp_wav, winsound.SND_FILENAME)
        else:
            subprocess.run(["aplay", tmp_wav])

        play_end = time.time()

        if ui:
            ui.update_audio_time(gen_end, play_start, play_end)

        os.remove(tmp_wav)

# ================= ONLINE PROCESS =================
def online_process(ui, recognizer, listening_mode):

    try:
        with sr.Microphone() as source:
            audio = recognizer.listen(source, phrase_time_limit=3)

        try:
            cmd = recognizer.recognize_google(audio, language="en-IN").lower()
        except:
            cmd = ""

        if not listening_mode and "hello" in cmd:
            ui.set_listening_mode()
            ui.show_listening()
            return True

        if listening_mode and any(c in cmd for c in ["stop", "pause", "exit", "quit"]):
            ui.set_idle_mode()
            ui.show_waiting()
            return False

        if not listening_mode:
            return listening_mode

        if LANG_MODE == "HI_TO_EN":
            text = recognizer.recognize_google(audio, language="hi-IN")
            ui.show_hindi(text)
            translated = GoogleTranslator(source="hi", target="en").translate(text)

        elif LANG_MODE == "EN_TO_HI":
            text = recognizer.recognize_google(audio, language="en-IN")
            ui.show_hindi(text)
            translated = GoogleTranslator(source="en", target="hi").translate(text)

        elif LANG_MODE == "ES_TO_EN":
            text = recognizer.recognize_google(audio, language="es-ES")
            ui.show_hindi(text)
            translated = GoogleTranslator(source="es", target="en").translate(text)

        elif LANG_MODE == "EN_TO_ES":
            text = recognizer.recognize_google(audio, language="en-IN")
            ui.show_hindi(text)
            translated = GoogleTranslator(source="en", target="es").translate(text)

        global t_start, t_text

        t_start = time.time()   # 🎯 START (speech captured)

        ui.last_hindi = text
        ui.last_english = translated

        ui.show_translation(translated)

        t_text = time.time()    # 📝 TEXT DISPLAYED

        ui.show_latency(t_start, t_text, None)

        speak_text_en(translated, ui)   # 🔊 audio handled inside

    except:
        pass

    return listening_mode

# ================= ASSISTANT LOOP =================
def assistant_loop(ui):

    hindi_model = Model(HI_MODEL_PATH)
    english_model = Model(EN_MODEL_PATH)
    spanish_model = Model(ES_MODEL_PATH)

    p = pyaudio.PyAudio()

    ui.show_waiting()

    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=16000,
                    input=True,
                    frames_per_buffer=2048)

    en_cmd_rec = KaldiRecognizer(english_model,16000)
    en_rec = KaldiRecognizer(english_model,16000)
    hi_rec = KaldiRecognizer(hindi_model,16000)
    es_rec = KaldiRecognizer(spanish_model,16000)

    recognizer_online = sr.Recognizer()
    listening_mode = False

    while True:

        if MODE == "ONLINE":
            if not is_connected():
                ui.show_no_network()
                continue

            listening_mode = online_process(ui, recognizer_online, listening_mode)
            continue

        data = stream.read(2048, exception_on_overflow=False)

        if en_cmd_rec.AcceptWaveform(data):
            cmd = json.loads(en_cmd_rec.Result()).get("text","").lower()

            if not listening_mode and "hello" in cmd:
                listening_mode = True
                en_cmd_rec.Reset()
                en_rec.Reset()
                hi_rec.Reset()
                ui.set_listening_mode()
                ui.show_listening()

            elif listening_mode and any(c in cmd for c in ["stop","pause"]):
                listening_mode = False
                en_cmd_rec.Reset()
                en_rec.Reset()
                hi_rec.Reset()
                ui.show_waiting()
                ui.set_idle_mode()

        if listening_mode:

            if LANG_MODE == "HI_TO_EN" and hi_rec.AcceptWaveform(data):

                spoken_text = json.loads(hi_rec.Result()).get("text","")
                if not spoken_text:
                    continue
                global t_start
                t_start = time.time()

                ui.show_hindi(spoken_text)

                english_raw = translator_hi_en.translate(spoken_text)
                english = intelligent_correction(spoken_text, english_raw)

                ui.last_hindi = spoken_text
                ui.last_english = english

                ui.show_translation(english)
                global t_text
                t_text = time.time()
                ui.show_latency(t_start, t_text, None)
                
               
                speak_text_en(english, ui)
                

            elif LANG_MODE == "EN_TO_HI" and en_rec.AcceptWaveform(data):

                spoken_text = json.loads(en_rec.Result()).get("text","")
                if not spoken_text:
                    continue

                ui.show_hindi(spoken_text)

                hindi_text = translator_en_hi.translate(spoken_text)

                ui.last_hindi = spoken_text
                ui.last_english = hindi_text

                ui.show_translation(hindi_text)
                speak_text_en(hindi_text)

            elif LANG_MODE == "ES_TO_EN" and es_rec.AcceptWaveform(data):

                spoken_text = json.loads(es_rec.Result()).get("text","")
                if not spoken_text:
                    continue

                ui.show_hindi(spoken_text)

                english = translator_es_en.translate(spoken_text)

                ui.last_hindi = spoken_text
                ui.last_english = english

                ui.show_translation(english)
                speak_text_en(english)

            elif LANG_MODE == "EN_TO_ES" and en_rec.AcceptWaveform(data):

                spoken_text = json.loads(en_rec.Result()).get("text","")
                if not spoken_text:
                    continue

                ui.show_hindi(spoken_text)

                spanish = translator_en_es.translate(spoken_text)

                ui.last_hindi = spoken_text
                ui.last_english = spanish

                ui.show_translation(spanish)
                speak_text_en(spanish)

# ================= GUI =================
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

        threading.Thread(target=assistant_loop,args=(self,),daemon=True).start()

    def build_ui(self):

        top_frame = tk.Frame(self.root, bg="#000000")
        top_frame.pack(fill="x", pady=5)

        self.light_canvas = tk.Canvas(top_frame,width=15,height=15,bg="#000000",highlightthickness=0)
        self.light_canvas.pack(side="left", padx=10)

        self.light = self.light_canvas.create_oval(2,2,13,13,fill="gray")

        self.container = tk.Frame(self.root, bg="#000000")
        self.container.pack(expand=True, pady=(0, 50))

        self.hindi_label = tk.Label(self.container,text="",font=("Segoe UI",14),
                                    fg="#AAAAAA",bg="#000000",
                                    wraplength=460,justify="center")
        self.hindi_label.pack(pady=3)

        self.english_label = tk.Label(self.container,text="",font=("Segoe UI",26,"bold"),
                                      fg="white",bg="#000000",
                                      wraplength=460,justify="center")
        self.english_label.pack(pady=3)

        btn_frame = tk.Frame(self.root, bg="#000000")
        btn_frame.pack(pady=(0,40))

        tk.Button(btn_frame,text="✨ Simplify",
                  font=("Segoe UI",12,"bold"),
                  bg="#222222",fg="white",
                  relief="flat",
                  command=self.simplify).pack(side="left", padx=10)

        tk.Button(btn_frame,text="🔄 Swap",
                  font=("Segoe UI",12,"bold"),
                  bg="#222222",fg="white",
                  relief="flat",
                  command=self.swap_languages).pack(side="left", padx=10)

        self.mode_btn = tk.Button(btn_frame,text="🌐 Online",
                                 font=("Segoe UI",12,"bold"),
                                 bg="#222222",fg="white",
                                 relief="flat",
                                 command=self.toggle_mode)
        self.mode_btn.pack(side="left", padx=10)

        tk.Button(btn_frame,text="🌍 Lang",
                  font=("Segoe UI",12,"bold"),
                  bg="#222222",fg="white",
                  relief="flat",
                  command=self.toggle_language_pair).pack(side="left", padx=10)

    def toggle_mode(self):
        global MODE
        MODE = "ONLINE" if MODE=="OFFLINE" else "OFFLINE"
        self.mode_btn.config(text="📴 Offline" if MODE=="ONLINE" else "🌐 Online")

    def swap_languages(self):
        global LANG_MODE, LANG_PAIR

        if LANG_PAIR == "HI_EN":
            if LANG_MODE == "HI_TO_EN":
                LANG_MODE = "EN_TO_HI"
                self.english_label.config(text="Mode: English → Hindi")
            else:
                LANG_MODE = "HI_TO_EN"
                self.english_label.config(text="Mode: Hindi → English")

        elif LANG_PAIR == "ES_EN":
            if LANG_MODE == "ES_TO_EN":
                LANG_MODE = "EN_TO_ES"
                self.english_label.config(text="Mode: English → Spanish")
            else:
                LANG_MODE = "ES_TO_EN"
                self.english_label.config(text="Mode: Spanish → English")

    def toggle_language_pair(self):
        global LANG_PAIR, LANG_MODE

        if LANG_PAIR == "HI_EN":
            LANG_PAIR = "ES_EN"
            LANG_MODE = "ES_TO_EN"
            self.english_label.config(text="Mode: Spanish → English")
        else:
            LANG_PAIR = "HI_EN"
            LANG_MODE = "HI_TO_EN"
            self.english_label.config(text="Mode: Hindi → English")

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

    def show_translation(self, text):
        self.hindi_label.config(text=self.last_hindi)
        self.english_label.config(text=text)

    def show_no_network(self):
        self.hindi_label.config(text="")
        self.english_label.config(text="❌ No Internet Connection")

    def simplify(self):
        if self.last_english:
            simplified = simplify_text(self.last_english)
            self.english_label.config(text=simplified)
            speak_text_en(simplified)

    def set_idle_mode(self):
        self.light_canvas.itemconfig(self.light, fill="gray")

    def set_listening_mode(self):
        self.light_canvas.itemconfig(self.light, fill="#00FF00")
    def show_latency(self, start, text_time, audio_time):
     if start and text_time:
        text_latency = round(text_time - start, 2)
     else:
        text_latency = 0

     if start and audio_time:
        audio_latency = round(audio_time - start, 2)
     else:
        audio_latency = "..."

     latency_info = f"\n⏱ Text: {text_latency}s | Audio: {audio_latency}s"

     base_text = self.last_english if self.last_english else ""
     self.english_label.config(text=base_text + latency_info)
    def update_audio_time(self, gen_end, play_start, play_end):
     global t_start, t_text

     text_latency = round(t_text - t_start, 2)
     audio_latency = round(play_start - t_start, 2)
     tts_delay = round(play_start - t_text, 2)
     playback_time = round(play_end - play_start, 2)

     latency_info = (
         f"\n⏱ Text: {text_latency}s"
         f" | Audio: {audio_latency}s"
         f"\n⚙️ TTS: {tts_delay}s | 🔊 Play: {playback_time}s"
     )

     base_text = self.last_english if self.last_english else ""
     self.english_label.config(text=base_text + latency_info)

# ================= START =================
if __name__ == "__main__":
    root = tk.Tk()
    app = ModernTranslatorUI(root)
    root.mainloop()
