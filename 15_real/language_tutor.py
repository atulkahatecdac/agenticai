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
# Language Tutor: Whisper (speech -> text) + LangChain memory + GPT
# (the tutor) + TTS (text -> speech). Same four building blocks as
# 15_real/personal_memory_assistant.py, but a harder test of memory:
# turn 1 asks for a numbered list, turn 2 says "repeat the second one" -
# to answer correctly the assistant has to recall its OWN earlier reply
# (not just a fact the user stated) and resolve "the second one" against
# it. A stateless Whisper->GPT call would have no lesson to refer back to
# and could only guess.
#
# Two ways to run:
#   python language_tutor.py
#       Automated demo, no microphone needed. Both turns are synthesized
#       into real audio via TTS first - standing in for a live mic
#       recording - so the full pipeline still runs audio in -> Whisper ->
#       LangChain + GPT -> TTS -> audio out, just without needing hardware.
#   python language_tutor.py mic
#       Real usage: records you talking through your actual microphone for
#       each turn instead of using the scripted lines.
# =====================================================================

openai_client = OpenAI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "language_tutor_audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

RECORD_SECONDS = 6
SAMPLE_RATE = 16000  # matches Whisper's native sample rate

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a friendly language tutor speaking with a student. Keep answers "
               "short and conversational - they will be read aloud, so avoid markdown; when "
               "teaching a numbered list of phrases, say them as 'first ... second ... third "
               "...' instead of using digits or bullet points. When asked to repeat or explain "
               "something from earlier in the lesson, refer back to exactly what you taught - "
               "don't invent a different phrase."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}"),
])

chain = prompt | llm

# In-memory history per session_id, cleared when the process exits. A real,
# persistent tutor would swap this for SQLChatMessageHistory - same pattern
# as 14_advanced/05_langchain/05_4_persistent_chatbot.py and
# 15_real/langchain_long_term_memory_rag.py.
_histories: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> InMemoryChatMessageHistory:
    return _histories.setdefault(session_id, InMemoryChatMessageHistory())


tutor_chain = RunnableWithMessageHistory(
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
    """TTS: text -> speech, so the tutor's reply is an actual voice file, not just text."""
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

    reply = tutor_chain.invoke(
        {"input": user_text}, config={"configurable": {"session_id": session_id}}
    ).content
    print(f"Tutor: {reply}")

    reply_audio_path = os.path.join(AUDIO_DIR, f"{session_id}_turn{turn_num}_tutor.mp3")
    speak(reply, reply_audio_path)
    print(f"(tutor reply spoken to {reply_audio_path})\n")
    os.startfile(reply_audio_path)  # auto-play in the default media app (Windows only)


if __name__ == "__main__":
    use_mic = len(sys.argv) > 1 and sys.argv[1] == "mic"
    session_id = "demo_student"

    if use_mic:
        print("=== LANGUAGE TUTOR (live microphone) ===")
        print("Two turns. Speak when prompted.\n")
        run_turn(session_id, 1, use_mic=True)
        run_turn(session_id, 2, use_mic=True)
    else:
        print("=== LANGUAGE TUTOR (automated demo - no microphone needed) ===")
        print("Run with 'mic' as an argument to use your real microphone instead.\n")
        run_turn(
            session_id, 1, use_mic=False,
            scripted_line="Teach me three Japanese greetings.",
        )
        run_turn(
            session_id, 2, use_mic=False,
            scripted_line="Repeat the second one.",
        )
