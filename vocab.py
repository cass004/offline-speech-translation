# paraphraser.py
from transformers import pipeline

# Load a paraphrasing model (first time it downloads, then works offline)
paraphraser = pipeline("text2text-generation", model="Vamsi/T5_Paraphrase_Paws")

def simplify_sentence(sentence):
    """Generate a simpler paraphrase of a given sentence."""
    prompt = f"paraphrase: {sentence} </s>"
    result = paraphraser(prompt, max_length=60, num_return_sequences=1, do_sample=True)
    return result[0]['generated_text']

def main():
    sentence = input("Enter a sentence: ")
    print(f"You said: {sentence}")

    while True:
        user_feedback = input("\nDid you understand? (type 'yes' or 'no'): ").strip().lower()
        if user_feedback in ["no", "i didn't understand", "i dint understand", "not really"]:
            simpler = simplify_sentence(sentence)
            print(f"Simplified meaning: {simpler}")
            sentence = simpler  # Allow recursive simplification if needed
        elif user_feedback == "yes":
            print("Great! Glad you understood 😊")
            break
        else:
            print("Please answer with 'yes' or 'no'.")

if __name__ == "__main__":
    main()
