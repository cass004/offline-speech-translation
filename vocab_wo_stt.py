import nltk
from nltk.corpus import wordnet as wn
from wordfreq import zipf_frequency

# Download once (safe if already downloaded)
nltk.download("wordnet", quiet=True)


# -------------------------
# FIND SIMPLER SYNONYMS
# -------------------------
def get_simpler_word(word):
    synsets = wn.synsets(word)

    if not synsets:
        return word

    synonyms = set()

    for syn in synsets:
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace("_", " "))

    if not synonyms:
        return word

    # Choose the most common (simplest) word
    simplest = max(
        synonyms,
        key=lambda w: zipf_frequency(w.lower(), "en")
    )

    # Only replace if actually simpler
    if zipf_frequency(simplest.lower(), "en") > zipf_frequency(word.lower(), "en"):
        return simplest

    return word


# -------------------------
# TEXT SIMPLIFIER
# -------------------------
def simplify_text(text):
    words = text.split()
    output = []

    for token in words:
        clean = token.strip(".,?!")

        # Attempt to simplify every word
        simple = get_simpler_word(clean.lower())

        if simple != clean.lower():
            # Preserve punctuation
            new_word = token.replace(clean, simple)
            output.append(new_word)
        else:
            output.append(token)

    return " ".join(output)


# -------------------------
# INTERACTIVE LOOP
# -------------------------
print("\n--- ✅ AUTO VOCAB SIMPLIFIER (OFFLINE) ---")

current = input("\nEnter text:\n> ")

while True:
    cmd = input("\nType 'simplify' or 'understood':\n> ").lower()

    if cmd == "simplify":
        current = simplify_text(current)
        print("\n--- SIMPLIFIED ---")
        print(current)

    elif cmd == "understood":
        print("\n✅ Done.")
        break

    else:
        print("\n❌ Unknown command. Type 'simplify' or 'understood'")
