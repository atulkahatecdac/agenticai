import tiktoken

MODEL = "gpt-4o-mini"
encoding = tiktoken.encoding_for_model(MODEL)


def show_tokens(text: str):
    tokens = encoding.encode(text)

    print(f"\nText: {text!r}")
    print(f"Number of tokens: {len(tokens)}\n")

    for token_id in tokens:
        piece = encoding.decode([token_id])
        print(f"  {token_id:>6}  ->  {piece!r}")


if __name__ == "__main__":
    text = input("Enter text to tokenize (press Enter for a default example): ").strip()
    if not text:
        text = (
            "Artificial Intelligence is transforming industries by "
            "automating repetitive tasks and assisting humans in decision-making."
        )

    show_tokens(text)
