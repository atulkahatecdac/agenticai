import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
import yfinance as yf
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_core._api.deprecation import LangChainDeprecationWarning, LangChainPendingDeprecationWarning

# langchain_core re-enables its own deprecation warnings on import, which runs
# AFTER our filters above and so overrides them - reapply now (same fix as
# 14_advanced/05_langchain/05_4_persistent_chatbot.py).
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Voice tool calling: user speaks a company name, GPT decides to CALL a
# real tool (live yfinance lookup - no hallucinated prices) to get the
# current price, then the answer is spoken back via TTS.
#
# Different concept from the other 15_real voice examples (personal_
# memory_assistant.py, language_tutor.py): those tested LangChain memory
# carrying context across turns. This one tests tool calling - the LLM
# recognizing "I don't know this, I need to call get_stock_price" rather
# than just answering from its own (possibly stale/wrong) training data.
#
# Two ways to run:
#   python voice_tool_calling_stock_price.py
#       Automated demo, no microphone needed. Two scripted turns ("What's
#       the current stock price of Apple?" / "What about Tesla?") are
#       synthesized into real audio via TTS first - standing in for a live
#       mic recording - so the full pipeline still runs audio in -> Whisper
#       -> tool-calling GPT -> TTS -> audio out, just without hardware.
#   python voice_tool_calling_stock_price.py mic
#       Real usage: records you talking through your actual microphone for
#       each turn instead of using the scripted lines.
# =====================================================================

openai_client = OpenAI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "voice_stock_price_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

RECORD_SECONDS = 6
SAMPLE_RATE = 16000  # matches Whisper's native sample rate


@tool
def get_stock_price(company_name_or_ticker: str) -> str:
    """Look up the CURRENT real-time stock price for a company. Input can be a
    company name (e.g. "Apple") or a ticker symbol (e.g. "AAPL") - either works.
    Returns the resolved ticker, company name, price, and currency."""
    matches = [q for q in yf.Search(company_name_or_ticker).quotes if q.get("quoteType") == "EQUITY"]
    if not matches:
        return f"Could not find a stock matching '{company_name_or_ticker}'."

    match = matches[0]
    symbol = match["symbol"]
    info = yf.Ticker(symbol).fast_info
    return (
        f"{match.get('shortname', symbol)} ({symbol}): "
        f"{info['lastPrice']:.2f} {info['currency']}"
    )


llm_with_tools = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools([get_stock_price])

SYSTEM_PROMPT = (
    "You are a voice assistant that reports stock prices. Always use the "
    "get_stock_price tool to look up a price - never answer from memory, since "
    "prices change constantly and you could be wrong. Once you have the tool "
    "result, answer in one short, natural spoken sentence (it will be read "
    "aloud) - no markdown, no ticker symbols in parentheses, just say the "
    "company name and the price naturally, e.g. 'Apple is currently trading "
    "at $311.00.'"
)


def answer_with_tool_calling(question: str) -> str:
    """Manual tool-calling loop: ask the model, run whatever tool(s) it asks
    for, then ask again with the tool result so it can phrase the final
    spoken answer."""
    messages = [SystemMessage(SYSTEM_PROMPT), HumanMessage(question)]
    ai_message = llm_with_tools.invoke(messages)
    messages.append(ai_message)

    if not ai_message.tool_calls:
        return ai_message.content

    for call in ai_message.tool_calls:
        print(f"  [tool call] get_stock_price({call['args']})")
        result = get_stock_price.invoke(call["args"])
        print(f"  [tool result] {result}")
        messages.append(ToolMessage(content=result, tool_call_id=call["id"]))

    final_message = llm_with_tools.invoke(messages)
    return final_message.content


def record_from_microphone(path: str, seconds: int = RECORD_SECONDS) -> None:
    """Real mic capture - only used in 'mic' mode, so sounddevice/soundfile are
    imported lazily here rather than at module load."""
    import sounddevice as sd
    import soundfile as sf

    print(f"Recording for {seconds}s... speak now.")
    audio = sd.rec(int(seconds * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    sf.write(path, audio, SAMPLE_RATE)
    print("Done recording.")


def synthesize_sample_user_turn(text: str, path: str) -> None:
    """Stand-in for a live mic recording: turns a scripted line into real audio via
    TTS, so the automated demo still exercises actual speech-to-text, not just text."""
    response = openai_client.audio.speech.create(model="gpt-4o-mini-tts", voice="alloy", input=text)
    response.write_to_file(path)


def transcribe(path: str) -> str:
    """Whisper: speech -> text."""
    with open(path, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text


def speak(text: str, path: str) -> None:
    """TTS: text -> speech, so the answer is an actual voice file, not just text."""
    response = openai_client.audio.speech.create(model="gpt-4o-mini-tts", voice="alloy", input=text)
    response.write_to_file(path)


def run_turn(turn_num: int, use_mic: bool, scripted_line: str = "") -> None:
    user_audio_path = os.path.join(AUDIO_DIR, f"turn{turn_num}_user.wav")

    if use_mic:
        record_from_microphone(user_audio_path)
    else:
        synthesize_sample_user_turn(scripted_line, user_audio_path)
        print(f'(simulated microphone input, synthesized via TTS): "{scripted_line}"')

    user_text = transcribe(user_audio_path)
    print(f"You said: {user_text}")

    reply = answer_with_tool_calling(user_text)
    print(f"Assistant: {reply}")

    reply_audio_path = os.path.join(AUDIO_DIR, f"turn{turn_num}_assistant.mp3")
    speak(reply, reply_audio_path)
    print(f"(assistant reply spoken to {reply_audio_path})\n")
    os.startfile(reply_audio_path)  # auto-play in the default media app (Windows only)


if __name__ == "__main__":
    use_mic = len(sys.argv) > 1 and sys.argv[1] == "mic"

    if use_mic:
        print("=== VOICE STOCK PRICE ASSISTANT (live microphone) ===")
        print("Two turns. Speak when prompted.\n")
        run_turn(1, use_mic=True)
        run_turn(2, use_mic=True)
    else:
        print("=== VOICE STOCK PRICE ASSISTANT (automated demo - no microphone needed) ===")
        print("Run with 'mic' as an argument to use your real microphone instead.\n")
        run_turn(1, use_mic=False, scripted_line="What's the current stock price of Apple?")
        run_turn(2, use_mic=False, scripted_line="What about Tesla?")
