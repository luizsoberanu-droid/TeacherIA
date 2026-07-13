# -*- coding: utf-8 -*-
"""
============================================================
  PROF. ACE — Bot de Inglês no Telegram (VERSÃO 100% GRÁTIS)
------------------------------------------------------------
  Professor:    Google Gemini (camada gratuita)
  Transcrição:  Groq / Whisper (gratuito)
  Voz (/ouvir): edge-tts (vozes Microsoft, gratuito)
  Telegram:     gratuito
============================================================
"""

import os
import re
import json
import sqlite3
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
from pathlib import Path

import requests
import edge_tts
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ContextTypes, filters,
)

# ------------------------------------------------------------
# CONFIGURAÇÃO
# ------------------------------------------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AndrewNeural")

STUDENT_NAME = os.getenv("STUDENT_NAME", "Luiz Gustavo")

# Se preenchido, o bot só responde a este usuário (protege sua cota grátis
# quando o bot está hospedado na nuvem). Descubra seu ID mandando /start
# para o bot @userinfobot no Telegram.
AUTHORIZED_USER_ID = os.getenv("TELEGRAM_USER_ID", "").strip()
STUDENT_INTERESTS = os.getenv(
    "STUDENT_INTERESTS",
    "logistics and freight management, football tactics and World Cup analysis, "
    "building SaaS apps, Python and Power BI",
)

DB_PATH = Path(__file__).parent / "english_progress.db"
AUDIO_DIR = Path(__file__).parent / "audios"
AUDIO_DIR.mkdir(exist_ok=True)

MAX_HISTORY = 30
MAX_TG_LEN = 4000

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
log = logging.getLogger("prof_ace")

histories: dict[int, list] = {}

# ------------------------------------------------------------
# BANCO DE DADOS (SQLite)
# ------------------------------------------------------------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS student_profile (
                chat_id INTEGER PRIMARY KEY,
                name TEXT,
                cefr_level TEXT DEFAULT 'A0',
                interests TEXT,
                session_count INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS error_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                session INTEGER,
                type TEXT,
                item TEXT,
                correction TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                next_review TEXT,
                interval_days INTEGER DEFAULT 1,
                times_correct INTEGER DEFAULT 0
            );
            """
        )


def get_profile(chat_id: int) -> sqlite3.Row:
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM student_profile WHERE chat_id=?", (chat_id,)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO student_profile (chat_id, name, interests) VALUES (?,?,?)",
                (chat_id, STUDENT_NAME, STUDENT_INTERESTS),
            )
            row = conn.execute(
                "SELECT * FROM student_profile WHERE chat_id=?", (chat_id,)
            ).fetchone()
        return row


def bump_session(chat_id: int) -> int:
    with db() as conn:
        conn.execute(
            "UPDATE student_profile SET session_count = session_count + 1 WHERE chat_id=?",
            (chat_id,),
        )
        return conn.execute(
            "SELECT session_count FROM student_profile WHERE chat_id=?", (chat_id,)
        ).fetchone()[0]


def set_level(chat_id: int, level: str):
    with db() as conn:
        conn.execute(
            "UPDATE student_profile SET cefr_level=? WHERE chat_id=?",
            (level, chat_id),
        )


def due_items(chat_id: int, limit: int = 5) -> list[sqlite3.Row]:
    today = datetime.now().strftime("%Y-%m-%d")
    with db() as conn:
        return conn.execute(
            """SELECT * FROM error_log
               WHERE chat_id=? AND (next_review IS NULL OR next_review <= ?)
               ORDER BY next_review LIMIT ?""",
            (chat_id, today, limit),
        ).fetchall()


def recent_errors_summary(chat_id: int, limit: int = 10) -> str:
    with db() as conn:
        rows = conn.execute(
            """SELECT type, item, correction FROM error_log
               WHERE chat_id=? ORDER BY id DESC LIMIT ?""",
            (chat_id, limit),
        ).fetchall()
    if not rows:
        return "No recorded errors yet (first sessions)."
    return "; ".join(f"[{r['type']}] {r['item']} -> {r['correction']}" for r in rows)


def save_errors(chat_id: int, session: int, errors: list[dict]):
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    with db() as conn:
        for e in errors:
            conn.execute(
                """INSERT INTO error_log
                   (chat_id, session, type, item, correction, next_review, interval_days)
                   VALUES (?,?,?,?,?,?,?)""",
                (
                    chat_id,
                    session,
                    e.get("type", "grammar"),
                    e.get("item", ""),
                    e.get("correction", ""),
                    tomorrow,
                    int(e.get("srs_interval_days", 1)),
                ),
            )


# ------------------------------------------------------------
# SYSTEM PROMPT DO PROFESSOR
# ------------------------------------------------------------
def build_system_prompt(chat_id: int) -> str:
    p = get_profile(chat_id)
    due = due_items(chat_id)
    due_txt = (
        "; ".join(f"{r['item']} (correct: {r['correction']})" for r in due)
        if due
        else "none due today"
    )
    session_number = p["session_count"]

    placement = ""
    if session_number == 0:
        placement = """
# SESSION 0 - PLACEMENT
This is the very first session. Greet the student in Portuguese and
explain how the bot works in 3 short lines. Then run a friendly
placement: start with ONE very easy audio task ("me diga em ingles:
seu nome e sua idade"). If the student handles it, increase difficulty
(describe your weekend / give an opinion). If the student can barely
produce anything, STOP the placement immediately, reassure them warmly
in Portuguese that starting from zero is perfectly fine, set level A0,
and teach the first 3 survival phrases right away so they leave session
0 having SPOKEN English. Estimate the CEFR level honestly. In your
ERROR_LOG_JSON, include the field "estimated_level".
"""

    return f"""# ROLE
You are "Prof. Ace", an elite English teacher and pronunciation coach
specialized in Brazilian Portuguese speakers. You combine the rigor of a
phonetics analyst with the warmth of a great personal coach. Your single
mission: make the student speak real, natural, confident English as fast
as scientifically possible.

Your student: {p['name']}, native Brazilian Portuguese speaker.
Current level: {p['cefr_level']} (CEFR A0-C2). Session number: {session_number}.
Student interests (USE THEM in every conversation): {p['interests']}.
Known recurring errors from database: {recent_errors_summary(chat_id)}.
Spaced-repetition items due today: {due_txt}.
{placement}
# LANGUAGE POLICY (adaptive)
- A0 (absolute beginner, speaks almost nothing): 90% Portuguese. Teach
  survival English: greetings, numbers, "I am / I have / I want / I like",
  the 100 most frequent words. EVERY new word comes with pronunciation
  hint in Portuguese-friendly spelling (water = "UO-ter"). Tiny steps,
  lots of encouragement, maximum 3 new items per session.
- A1-A2: 60% Portuguese explanations, 40% English practice.
- B1: 30% Portuguese, 70% English. New grammar explained in Portuguese.
- B2+: 95% English. Portuguese only for subtle nuance contrasts.
- ALWAYS push slightly above the student's comfort zone (i+1), never far above.
- If the student writes/says something in Portuguese mid-conversation,
  gently respond and model how they could have said it in English.

# SESSION STRUCTURE
1. WARM-UP: one engaging question connected to the student's interests.
   Ask for an AUDIO reply, not text.
2. SHADOWING: give 3 target sentences loaded with the student's problem
   phonemes. For each: English sentence + IPA + Portuguese-friendly hint
   (e.g., think = "THink - lingua entre os dentes, NUNCA 'fink'").
   Tell the student they can hear each sentence with /ouvir + the sentence.
   Ask the student to send an audio repeating each one.
3. FREE CONVERSATION: 8-12 exchanges about the student's real life and
   interests. Apply the CORRECTION PROTOCOL.
4. SPACED REVIEW: quiz the student on the due items listed above.
5. FEEDBACK REPORT: end the session with the exact REPORT FORMAT.

# CORRECTION PROTOCOL
- Use RECASTS in conversation: reply naturally embedding the corrected
  form, without interrupting the flow.
- Do NOT correct every error. Prioritize: (1) errors that block
  communication, (2) recurring database errors, (3) fossilization risks.
- Praise SPECIFICALLY, never generically.
- For AUDIO messages you receive a TRANSCRIPTION. You cannot directly
  hear phoneme quality. Infer LIKELY pronunciation issues from the
  Brazilian error map and transcription artifacts (if the student said
  "sink" it may actually be "think"). Flag these as "provavel/likely",
  never as certainty.

# PRONUNCIATION TARGETS (Brazilian error map - hunt actively)
1. /TH/ think, this -> student says t/f/d
2. Final vowel epenthesis: good->"goodi", big->"bigui"
3. -ED endings: worked=/t/, played=/d/, wanted=/id/
4. /h/ vs /r/: hot, house, hungry vs angry
5. Short vs long vowels: ship/sheep, beach/bitch, full/fool
6. Word stress: deVELopment, COMFtable, hoTEL
7. /ae/ vs /eh/: bad/bed, man/men
8. Linking and reduction: wanna, whaddaya (recognition first)

# VOCABULARY PRIORITIES
- The 2,000 most frequent English words FIRST, through conversation.
- Teach CHUNKS: "I'd rather...", "It turns out...", "By the way...".
- Kill false friends on sight: actually, pretend, push, parents, college.
- Kill literal translations: "I have X years", "make a question", "win money".

# REPORT FORMAT (end of every session, when the student says goodbye or
asks for the report, or after ~12 conversation exchanges)
Session Report
Win of the day: [one thing they did right that they used to get wrong]
Top 3 to fix:
1. [error] -> [correction] -> [one-line why]
2. ...
3. ...
Added to review deck: [items going into spaced repetition]
Tomorrow's focus: [one specific target]

Then ALWAYS append, at the very end, this machine-readable block with
valid JSON (the backend parses and removes it):
[ERROR_LOG_JSON]
{{"errors": [{{"type": "pronunciation|grammar|vocab|false_friend", "item": "...", "correction": "...", "srs_interval_days": 1}}], "wins": ["..."], "estimated_level": "{p['cefr_level']}"}}
[/ERROR_LOG_JSON]

Also include the ERROR_LOG_JSON block (with any errors detected so far)
whenever you correct 2 or more errors in a single reply, even mid-session.

# PERSONALITY
- Energetic, direct, zero condescension. The student is a capable adult.
- Humor is welcome.
- Never let a session end without the student having SPOKEN (audio) at
  least 5 times.
- If the student is tired, offer a 5-minute micro-session.

# HARD RULES
- Never invent progress.
- Never lecture grammar for more than 4 lines. Teach through USE.
- Max ~120 words per conversational turn.
- One question at a time. End your turns with a question or a task.
- Plain text only: no markdown headers, no tables, no asterisks
  (Telegram plain chat)."""


# ------------------------------------------------------------
# GEMINI (professor) — API gratuita do Google
# ------------------------------------------------------------
JSON_RE = re.compile(r"\[ERROR_LOG_JSON\](.*?)\[/ERROR_LOG_JSON\]", re.S)
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)


def call_gemini(system_prompt: str, history: list) -> str:
    contents = [
        {
            "role": "user" if m["role"] == "user" else "model",
            "parts": [{"text": m["content"]}],
        }
        for m in history
    ]
    body = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1500, "temperature": 0.7},
    }
    r = requests.post(
        GEMINI_URL.format(model=GEMINI_MODEL, key=GEMINI_KEY),
        json=body,
        timeout=90,
    )
    if r.status_code == 429:
        return (
            "⏳ Atingimos o limite gratuito de mensagens por enquanto. "
            "Espera 1 minuto e manda de novo (ou volta amanhã se persistir)."
        )
    r.raise_for_status()
    data = r.json()
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def ask_professor(chat_id: int, user_text: str) -> str:
    history = histories.setdefault(chat_id, [])
    history.append({"role": "user", "content": user_text})
    history[:] = history[-MAX_HISTORY:]

    answer = call_gemini(build_system_prompt(chat_id), history)
    history.append({"role": "assistant", "content": answer})

    m = JSON_RE.search(answer)
    if m:
        try:
            data = json.loads(m.group(1).strip())
            profile = get_profile(chat_id)
            save_errors(chat_id, profile["session_count"], data.get("errors", []))
            lvl = data.get("estimated_level")
            if lvl and lvl != profile["cefr_level"]:
                set_level(chat_id, lvl)
            log.info("Salvos %d erros no banco.", len(data.get("errors", [])))
        except (json.JSONDecodeError, KeyError) as e:
            log.warning("Falha ao ler ERROR_LOG_JSON: %s", e)
        answer = JSON_RE.sub("", answer).strip()

    return answer


# ------------------------------------------------------------
# GROQ (transcrição Whisper) — gratuito
# ------------------------------------------------------------
def transcribe(ogg_path: Path) -> str:
    with open(ogg_path, "rb") as f:
        r = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            files={"file": ("audio.ogg", f, "audio/ogg")},
            data={"model": "whisper-large-v3", "language": "en"},
            timeout=90,
        )
    r.raise_for_status()
    return r.json()["text"].strip()


async def send_long(update: Update, text: str):
    for i in range(0, len(text), MAX_TG_LEN):
        await update.message.reply_text(text[i : i + MAX_TG_LEN])


# ------------------------------------------------------------
# SERVIDOR DE SAÚDE (necessário para hospedagem grátis no Render)
# Só liga se a variável PORT existir (no seu PC ela não existe,
# então localmente nada muda).
# ------------------------------------------------------------
class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write("✅ Prof. Ace está online!".encode("utf-8"))

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):  # silencia os logs de ping
        pass


def start_health_server():
    port = int(os.getenv("PORT", "0"))
    if port:
        server = HTTPServer(("0.0.0.0", port), _HealthHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        log.info("Servidor de saúde ativo na porta %d", port)


def is_authorized(update: Update) -> bool:
    """Se TELEGRAM_USER_ID estiver definido, só o dono usa o bot."""
    if not AUTHORIZED_USER_ID:
        return True
    return str(update.effective_user.id) == AUTHORIZED_USER_ID


def private(handler):
    """Decorator: bloqueia usuários não autorizados educadamente."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            await update.message.reply_text(
                "🔒 Este é um bot pessoal de estudos. "
                "O código é aberto — crie o seu em: "
                "github.com (procure por english-tutor-bot)"
            )
            return
        await handler(update, context)
    return wrapper


# ------------------------------------------------------------
# HANDLERS DO TELEGRAM
# ------------------------------------------------------------
@private
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    get_profile(chat_id)
    histories[chat_id] = []
    await update.message.reply_chat_action(ChatAction.TYPING)
    answer = ask_professor(
        chat_id,
        "SYSTEM NOTE: the student just opened the bot with /start. "
        "Greet them and begin (placement if session 0, otherwise the warm-up).",
    )
    bump_session(chat_id)
    await send_long(update, answer)


@private
async def cmd_nova(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    histories[chat_id] = []
    n = bump_session(chat_id)
    await update.message.reply_chat_action(ChatAction.TYPING)
    answer = ask_professor(
        chat_id,
        f"SYSTEM NOTE: the student started session {n} with /nova. "
        "Begin with the warm-up.",
    )
    await send_long(update, answer)


@private
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    p = get_profile(chat_id)
    with db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM error_log WHERE chat_id=?", (chat_id,)
        ).fetchone()[0]
    due = len(due_items(chat_id, limit=99))
    await update.message.reply_text(
        f"📊 Seu progresso\n"
        f"Nível estimado: {p['cefr_level']}\n"
        f"Sessões feitas: {p['session_count']}\n"
        f"Itens no banco de erros: {total}\n"
        f"Itens para revisar hoje: {due}\n\n"
        f"Comandos: /nova (nova sessão) • /ouvir <frase> (áudio da pronúncia)"
    )


@private
async def cmd_ouvir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera áudio (voz Microsoft, grátis) com a pronúncia correta."""
    text = " ".join(context.args) if context.args else ""
    if not text:
        await update.message.reply_text("Use assim: /ouvir I think this is good")
        return
    await update.message.reply_chat_action(ChatAction.RECORD_VOICE)
    mp3 = AUDIO_DIR / f"tts_{update.effective_chat.id}.mp3"
    communicate = edge_tts.Communicate(text, TTS_VOICE, rate="-15%")
    await communicate.save(str(mp3))
    with open(mp3, "rb") as f:
        await update.message.reply_voice(f, caption=f"🔊 {text}")


@private
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_chat_action(ChatAction.TYPING)
    answer = ask_professor(chat_id, update.message.text)
    await send_long(update, answer)


@private
async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_chat_action(ChatAction.TYPING)

    voice = update.message.voice or update.message.audio
    tg_file = await voice.get_file()
    ogg = AUDIO_DIR / f"in_{chat_id}.ogg"
    await tg_file.download_to_drive(ogg)

    try:
        text = transcribe(ogg)
    except Exception as e:
        log.error("Erro na transcrição: %s", e)
        await update.message.reply_text(
            "⚠️ Não consegui transcrever o áudio. Tenta de novo?"
        )
        return

    answer = ask_professor(
        chat_id,
        f"[AUDIO TRANSCRIPTION of the student's voice message]: {text}",
    )
    await send_long(update, f"📝 Eu ouvi: \"{text}\"\n\n{answer}")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    log.error("Erro no bot: %s", context.error)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------
def main():
    missing = [
        name
        for name, val in [
            ("TELEGRAM_TOKEN", TELEGRAM_TOKEN),
            ("GEMINI_API_KEY", GEMINI_KEY),
            ("GROQ_API_KEY", GROQ_KEY),
        ]
        if not val
    ]
    if missing:
        raise SystemExit(
            f"❌ Faltam variáveis no arquivo .env: {', '.join(missing)}\n"
            "Veja o GUIA_VERSAO_GRATIS.md"
        )

    init_db()
    start_health_server()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("nova", cmd_nova))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("ouvir", cmd_ouvir))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    print("✅ Prof. Ace (versão grátis) está no ar!")
    print("   Abra o Telegram e mande /start pro seu bot.")
    print("   (Para parar: Ctrl+C nesta janela)")
    app.run_polling()


if __name__ == "__main__":
    main()
