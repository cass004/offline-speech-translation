import argostranslate.translate

# Reload system translations (now includes installed models)
installed_languages = argostranslate.translate.get_installed_languages()

# Find English → Hindi translator
from_lang = next(filter(lambda l: l.code == "en", installed_languages))
to_lang = next(filter(lambda l: l.code == "hi", installed_languages))

translator = from_lang.get_translation(to_lang)

# Translate some text
text = "hello, how are you?"
translated_text = translator.translate(text)

print("Original:", text)
print("Translated:", translated_text)

