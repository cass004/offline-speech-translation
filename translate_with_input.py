import argostranslate.translate

# Load installed languages
installed_languages = argostranslate.translate.get_installed_languages()

# Select English → Hindi
from_lang = next(filter(lambda l: l.code == "en", installed_languages))
to_lang = next(filter(lambda l: l.code == "hi", installed_languages))
translator = from_lang.get_translation(to_lang)

# Take input from user
text = input("Enter a sentence to translate (English → Hindi): ")

# Translate
translated_text = translator.translate(text)

print("\nOriginal:", text)
print("Translated:", translated_text)
