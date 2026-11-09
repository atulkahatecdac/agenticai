import os
import sys
import tiktoken

sys.stdout.reconfigure(encoding="utf-8")  # Devanagari characters fall outside Windows' cp1252 console codepage

MODEL = "gpt-4o-mini"
encoding = tiktoken.encoding_for_model(MODEL)

TEXT_PATH = os.path.join(os.path.dirname(__file__), "chatgpt.txt")  # Hindi (Devanagari) text


def show_tokens(text: str):
    
    # convert text to tokens
    tokens = encoding.encode(text)

    print(f"\nText length: {len(text)} characters")
    print(f"Number of tokens: {len(tokens)}\n")

    for token_id in tokens:
        # convert token back to text
        piece = encoding.decode([token_id])
        print(f"  {token_id:>6}  ->  {piece!r}")


if __name__ == "__main__":
    with open(TEXT_PATH, encoding="utf-8") as f:
        text = f.read()

    show_tokens(text)
