import speech_recognition as sr
from deep_translator import GoogleTranslator
import subprocess
import pyaudio

# ------------------ PIPER CONFIG ------------------ #
PIPER_PATH = "./piper/piper"
MODEL_PATH = "./piper/en_US-lessac-medium.onnx"

# Initialize PyAudio
p = pyaudio.PyAudio()


# ------------------ SPEECH TO TEXT ------------------ #
def speech_to_text():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("🎙️ Speak in Hindi...")
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio, language="hi-IN")
        print(f"✅ You said (Hindi): {text}")
        return text
    except sr.UnknownValueError:
        print("❌ Could not understand audio")
        return None
    except sr.RequestError:
        print("❌ API error")
        return None


# ------------------ TRANSLATION ------------------ #
def translate_text(text):
    translated = GoogleTranslator(source="hi", target="en").translate(text)
    print(f"🌍 Translated (English): {translated}")
    return translated


# ------------------ PIPER + PYAUDIO (NO FILE) ------------------ #
def speak_text(text):
    process = subprocess.Popen(
        [PIPER_PATH, "--model", MODEL_PATH, "--output_raw"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )

    process.stdin.write(text.encode("utf-8"))
    process.stdin.close()

    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=22050,
        output=True
    )

    while True:
        data = process.stdout.read(1024)
        if not data:
            break
        stream.write(data)

    stream.stop_stream()
    stream.close()
    process.wait()


# ------------------ MAIN LOOP ------------------ #
print("🎯 Mode: Hindi → English")
print("Say 'stop' to exit.\n")

while True:
    spoken_text = speech_to_text()

    if spoken_text:
        if spoken_text.lower() in ["stop", "exit", "quit"]:
            print("🛑 Exiting...")
            break

        translated_text = translate_text(spoken_text)
        speak_text(translated_text)

    else:
        print("🔁 Try again...\n")


# Cleanup
p.terminate()
