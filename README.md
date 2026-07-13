# 🎓 Prof. Ace — English Tutor Bot for Telegram

Bot de Telegram que funciona como **professor particular de inglês com IA**,
especializado em falantes de português brasileiro. Correção de fala,
pronúncia e vocabulário por mensagens de **áudio e texto** — com memória
de erros e revisão espaçada. **100% construído com serviços gratuitos.**

## ✨ Funcionalidades

- 🎙️ **Aulas por áudio**: o aluno fala inglês por mensagem de voz; o bot
  transcreve (Whisper via Groq), analisa e corrige
- 🧠 **Professor adaptativo** (Google Gemini): nivelamento CEFR automático
  na primeira sessão (de iniciante absoluto A0 até C2) e aulas que se
  ajustam ao nível do aluno
- 🔁 **Repetição espaçada (SRS)**: cada erro vai para um banco SQLite e
  volta em intervalos crescentes (1 → 2 → 4 → 8 → 16 → 32 dias)
- 🗣️ **Correção por recast**: erros são corrigidos naturalmente dentro da
  conversa, sem interromper o fluxo — método com base em pesquisa de
  aquisição de segunda língua
- 🎯 **Caça aos erros de brasileiro**: TH, vogal extra no fim ("goodi"),
  terminações -ED, ship/sheep, false friends, traduções literais
- 🔊 `/ouvir <frase>`: áudio com a pronúncia correta (vozes neurais
  Microsoft via edge-tts, em velocidade reduzida para iniciantes)
- 📊 `/status`: nível atual, sessões feitas e itens a revisar

## 🏗️ Arquitetura

```
Telegram (áudio/texto)
   └─> python-telegram-bot (polling)
         ├─> Groq API ──> Whisper large-v3 (transcrição do áudio)
         ├─> Google Gemini (professor: prompt pedagógico + histórico)
         │      └─> bloco [ERROR_LOG_JSON] parseado a cada resposta
         ├─> SQLite (perfil do aluno + banco de erros + agenda SRS)
         └─> edge-tts (áudios de pronúncia)
```

O "cérebro pedagógico" é um system prompt estruturado que define papel,
política de idioma por nível, estrutura de sessão (warm-up → shadowing →
conversa livre → revisão → relatório), protocolo de correção e um formato
de saída legível por máquina — o backend extrai o JSON de erros de cada
resposta e alimenta o sistema de repetição espaçada.

## 🚀 Rodando localmente

1. Clone o repositório e entre na pasta
2. Crie o arquivo `.env` (use `env_exemplo_gratis.txt` como modelo):
   ```
   TELEGRAM_TOKEN=...     # @BotFather no Telegram
   GEMINI_API_KEY=...     # https://aistudio.google.com (grátis)
   GROQ_API_KEY=...       # https://console.groq.com (grátis)
   TELEGRAM_USER_ID=...   # opcional: restringe o bot só a você
   ```
3. Instale e rode:
   ```
   python -m venv venv
   venv\Scripts\activate        # Windows  (Linux/Mac: source venv/bin/activate)
   pip install -r requirements.txt
   python bot_gratis.py
   ```
4. No Telegram, mande `/start` para o seu bot. A primeira sessão é o
   teste de nivelamento — responda por áudio!

## ☁️ Hospedagem gratuita (24h no ar)

O bot inclui um mini servidor HTTP de health-check (ativado pela variável
`PORT`), o que permite hospedá-lo no plano gratuito do
[Render](https://render.com) como Web Service, mantido acordado por um
monitor gratuito do [UptimeRobot](https://uptimerobot.com).

- Build command: `pip install -r requirements.txt`
- Start command: `python bot_gratis.py`
- Variáveis de ambiente: as mesmas do `.env` (configuradas no painel)

> ⚠️ No plano gratuito do Render o disco é efêmero: o banco de progresso
> (`english_progress.db`) é zerado a cada redeploy. Roadmap: migrar o
> SQLite para um banco em nuvem gratuito (Turso/Supabase).

## 🧰 Stack

`Python` · `python-telegram-bot` · `Google Gemini API` · `Groq (Whisper)` ·
`edge-tts` · `SQLite` · `Render`

## 📄 Licença

MIT — use, estude e adapte à vontade.
