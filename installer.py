import argostranslate.package
import argostranslate.translate
import os

# Step 1: Update the available package index
print("🔄 Updating translation package index...")
argostranslate.package.update_package_index()

# Step 2: Get list of available translation packages
available_packages = argostranslate.package.get_available_packages()

# Step 3: Display all available translation pairs
print("\n🌐 Available translation models:")
for i, pkg in enumerate(available_packages, 1):
    print(f"{i}. {pkg.from_name} ({pkg.from_code}) → {pkg.to_name} ({pkg.to_code})")

# Step 4: Ask user which one to install
choice = int(input("\nEnter the number of the translation model you want to install: ")) - 1
if choice < 0 or choice >= len(available_packages):
    print("❌ Invalid selection. Exiting.")
    exit()

package_to_install = available_packages[choice]

# Step 5: Download and install the model
print(f"\n⬇️ Downloading model: {package_to_install.from_name} → {package_to_install.to_name}")
download_path = package_to_install.download()
argostranslate.package.install_from_path(download_path)

# Step 6: Display where the model was installed
install_dir = os.path.expanduser("~/.local/share/argos-translate/packages")

print(f"\n✅ {package_to_install.from_name} → {package_to_install.to_name} model installed successfully!")
print(f"📁 Installed to: {install_dir}")

# ==================================================
# STEP 7: Download Vosk Speech Recognition Model
# ==================================================

import urllib.request
import zipfile

print("\n🔊 Checking Vosk hindi speech recognition model...")

VOSK_MODEL_NAME = "vosk-model-small-hi-0.22"
VOSK_MODEL_ZIP = VOSK_MODEL_NAME + ".zip"
VOSK_MODEL_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL_ZIP}"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOSK_MODEL_DIR = os.path.join(BASE_DIR, VOSK_MODEL_NAME)

if os.path.isdir(VOSK_MODEL_DIR):
    print("✅ Vosk hindi model already installed")
else:
    print("⬇ Downloading Vosk hindi model...")
    zip_path = os.path.join(BASE_DIR, VOSK_MODEL_ZIP)

    urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path)

    print("📦 Extracting Vosk hindi model...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(BASE_DIR)

    os.remove(zip_path)
    print("✅ Vosk hindi model installed successfully")


