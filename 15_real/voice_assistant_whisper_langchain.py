import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os
import sys
from dotenv import load_dotenv
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core._api.deprecation import LangChainDeprecationWarning, LangChainPendingDeprecationWarning

# langchain_core re-enables its own deprecation warnings on import, which runs
# AFTER our filters above and so overrides them - reapply now (same fix as
# 14_advanced/05_langchain/05_4_persistent_chatbot.py).
warnings.filterwarnings("ignore", category=LangChainDeprecationWarning)
warnings.filterwarnings("ignore", category=LangChainPendingDeprecationWarning)

load_dotenv(override=True)
sys.stdout.reconfigure(encoding="utf-8")

# =====================================================================
# Voice-based assistant: Whisper (speech -> text) + LangChain (multi-turn
# memory) + GPT (the actual reasoning/response) - plus TTS (text -> speech)
# to close the loop, since a "voice assistant" that only replies in text
# isn't really one.
#
# Two ways to run:
#   python voice_assistant_whisper_langchain.py
#       Automated demo, no microphone needed. Two scripted user turns are
#       synthesized into real audio via TTS first - standing in for a live
#       mic recording - so the full pipeline (audio in -> Whisper -> LangChain
#       + GPT -> TTS -> audio out) is exercised end-to-end either way.
#   python voice_assistant_whisper_langchain.py mic
#       Real usage: records you talking through your actual microphone for
#       each turn instead of using the scripted lines.
#
# The second turn in both modes deliberately asks the assistant to recall
# something from the first turn, to prove the LangChain memory (not just
# a single stateless Whisper->GPT call) is what's carrying context across
# turns.
# =====================================================================

openai_client = OpenAI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "voice_assistant_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

RECORD_SECONDS = 6
SAMPLE_RATE = 16000  # matches Whisper's native sample rate

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful voice assistant. Keep answers short and conversational - "
               "they will be read aloud, so avoid bullet points, markdown, or long lists."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | llm

# In-memory history per session_id, cleared when the process exits. A real,
# persistent voice assistant would swap this for SQLChatMessageHistory - same
# pattern as 14_advanced/05_langchain/05_4_persistent_chatbot.py.
_histories: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    return _histories.setdefault(session_id, InMemoryChatMessageHistory())


assistant_chain = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history",
)


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
    """TTS: text -> speech, so the assistant's reply is an actual voice file, not just text."""
    response = openai_client.audio.speech.create(model="gpt-4o-mini-tts", voice="alloy", input=text)
    response.write_to_file(path)


def run_turn(session_id: str, turn_num: int, use_mic: bool, scripted_line: str = "") -> None:
    user_audio_path = os.path.join(AUDIO_DIR, f"{session_id}_turn{turn_num}_user.wav")

    if use_mic:
        record_from_microphone(user_audio_path)
    else:
        synthesize_sample_user_turn(scripted_line, user_audio_path)
        print(f'(simulated microphone input, synthesized via TTS): "{scripted_line}"')

    user_text = transcribe(user_audio_path)
    print(f"You said: {user_text}")

    reply = assistant_chain.invoke(
        {"input": user_text}, config={"configurable": {"session_id": session_id}}
    ).content
    print(f"Assistant: {reply}")

    reply_audio_path = os.path.join(AUDIO_DIR, f"{session_id}_turn{turn_num}_assistant.mp3")
    speak(reply, reply_audio_path)
    print(f"(assistant reply spoken to {reply_audio_path})\n")
    os.startfile(reply_audio_path)  # auto-play in the default media app (Windows only)


if __name__ == "__main__":
    use_mic = len(sys.argv) > 1 and sys.argv[1] == "mic"
    session_id = "demo_user"

    if use_mic:
        print("=== VOICE ASSISTANT (live microphone) ===")
        print("Two turns. Speak when prompted.\n")
        run_turn(session_id, 1, use_mic=True)
        run_turn(session_id, 2, use_mic=True)
    else:
        print("=== VOICE ASSISTANT (automated demo - no microphone needed) ===")
        print("Run with 'mic' as an argument to use your real microphone instead.\n")
        run_turn(
            session_id, 1, use_mic=False,
            scripted_line="Hi, I'm Alex. I'm planning a trip to Japan in October, and "
                          "I've got a shellfish allergy.",
        )
        run_turn(
            session_id, 2, use_mic=False,
            scripted_line="What kind of food should I be careful about, and remind me - "
                          "when did I say I'm traveling?",
        )
