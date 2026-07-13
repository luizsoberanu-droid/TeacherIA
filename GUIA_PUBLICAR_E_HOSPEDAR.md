# 🌐 GUIA — Publicar no GitHub + Hospedar 24h de graça

Duas missões neste guia:
- **Parte A:** publicar o projeto no GitHub (portfólio + necessário pra hospedar)
- **Parte B:** hospedar no Render (bot no ar 24h, sem PC ligado, grátis)

Tempo total: ~40 minutos. Tudo sem cartão de crédito.

---

# 🔴 ANTES DE TUDO — Regra de ouro da segurança

O arquivo **`.env` NUNCA vai para o GitHub.** Ele tem suas chaves — quem
tiver as chaves usa suas cotas e controla seu bot. O arquivo `.gitignore`
que vamos criar protege contra isso, mas fique atento na hora do upload:

✅ Sobe: `bot_gratis.py`, `requirements.txt`, `README.md`, `.gitignore`, `env_exemplo_gratis.txt`
❌ NÃO sobe: `.env`, `english_progress.db`, pasta `audios/`, pasta `venv/`

Se um dia subir o `.env` sem querer: apague o repositório E gere chaves
novas nos 3 sites (as antigas ficam comprometidas pra sempre no histórico).

---

# PARTE A — Publicar no GitHub

## A1 — Criar a conta (5 min)

1. Acesse **https://github.com** → **Sign up**
2. Use seu e-mail pessoal, crie usuário e senha
3. Confirme o código que chega no e-mail

## A2 — Criar o repositório (3 min)

1. Logado, clique no **+** no canto superior direito → **New repository**
2. Preencha:
   - **Repository name:** `english-tutor-bot`
   - **Description:** `Professor de inglês com IA no Telegram — áudio, correção de pronúncia e repetição espaçada`
   - Marque **Public** (é o que vale como portfólio)
   - ✅ Marque **"Add a README file"** (vamos substituir depois)
3. Clique em **Create repository**

## A3 — Subir os arquivos (5 min)

1. No repositório, clique em **Add file → Upload files**
2. Arraste para a página estes 4 arquivos (da sua pasta `english_bot`):
   - `bot_gratis.py`
   - `requirements.txt` *(o novo que te entreguei — sem "_gratis" no nome)*
   - `env_exemplo_gratis.txt`
   - `README.md` *(o novo que te entreguei — substitui o criado no A2)*
3. Confira DUAS vezes que o `.env` NÃO está na lista!
4. Embaixo, em "Commit changes", clique no botão verde **Commit changes**

## A4 — Criar o .gitignore (3 min)

O jeito mais fácil (sem brigar com o Windows por causa do ponto no nome):

1. No repositório, **Add file → Create new file**
2. No campo do nome, digite exatamente: `.gitignore`
3. Abra o arquivo `gitignore.txt` que te entreguei, copie TODO o conteúdo
   e cole no campo grande
4. **Commit changes**

✅ **Pronto! Projeto publicado.** Seu portfólio está em:
`https://github.com/SEU_USUARIO/english-tutor-bot`

---

# PARTE B — Hospedar 24h no Render (grátis)

Como funciona o esquema gratuito: o Render roda seu bot de graça, mas
"dorme" serviços parados. Por isso o bot agora tem um mini "portãozinho
web" (health-check), e um vigia gratuito (UptimeRobot) fica batendo nele
a cada 5 minutos pra manter acordado. Resultado: bot no ar 24h, custo zero.

## B1 — Criar conta no Render (2 min)

1. Acesse **https://render.com** → **Get Started**
2. Escolha **"Sign in with GitHub"** (isso já conecta as duas contas)
3. Autorize o Render a acessar seus repositórios

## B2 — Criar o serviço (5 min)

1. No painel do Render: **New +** → **Web Service**
2. Encontre `english-tutor-bot` na lista e clique em **Connect**
3. Preencha:
   - **Name:** `english-tutor-bot`
   - **Region:** qualquer (Ohio/Oregon ok)
   - **Branch:** `main`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot_gratis.py`
   - **Instance Type:** **Free** ← importante!

## B3 — Colocar as chaves (as variáveis de ambiente) (3 min)

Na nuvem não existe arquivo `.env` — as chaves vão no painel:

1. Ainda na tela de criação (ou depois em **Environment**), clique em
   **Add Environment Variable** e crie uma por uma:

   | Key | Value |
   |---|---|
   | `TELEGRAM_TOKEN` | seu token do BotFather |
   | `GEMINI_API_KEY` | sua chave do Google AI Studio |
   | `GROQ_API_KEY` | sua chave do Groq |
   | `TELEGRAM_USER_ID` | seu ID do Telegram (veja abaixo) |

   💡 **Seu ID do Telegram:** procure o bot **@userinfobot** no Telegram,
   mande `/start`, ele responde com seu `Id` (um número tipo `123456789`).
   Com essa variável preenchida, **só você** consegue usar o bot — como o
   código agora é público no GitHub, isso impede estranhos de gastarem
   sua cota gratuita.

2. Clique em **Deploy Web Service** e aguarde uns 3–5 minutos.
   Quando aparecer **"Live"** em verde → está no ar! 🎉

3. **Teste:** copie a URL do serviço (algo como
   `https://english-tutor-bot.onrender.com`) e abra no navegador.
   Deve aparecer: `✅ Prof. Ace está online!`

4. **Teste no Telegram:** mande `/status` pro bot. Respondeu? Perfeito.
   ⚠️ Se o bot ainda estiver rodando no seu PC, FECHE lá (Ctrl+C) —
   duas cópias do mesmo bot ao mesmo tempo dão conflito.

## B4 — O vigia que mantém o bot acordado (5 min)

1. Acesse **https://uptimerobot.com** → crie conta grátis
2. **+ Add New Monitor**:
   - **Monitor Type:** HTTP(s)
   - **Friendly Name:** `Prof Ace`
   - **URL:** a URL do Render (a mesma do teste no navegador)
   - **Monitoring Interval:** 5 minutes
3. **Create Monitor**

Pronto: o UptimeRobot visita seu bot a cada 5 min e ele nunca dorme.
Bônus: se o bot cair, você recebe e-mail avisando.

---

# ⚠️ Limitações honestas do plano grátis (leia!)

1. **O progresso zera quando o Render reinicia o serviço** (a cada novo
   deploy e ocasionalmente por manutenção). O banco `english_progress.db`
   vive no disco temporário. Seu nível e erros salvos se perdem — as
   aulas continuam funcionando normalmente. Solução definitiva (Fase 2):
   migrar pra um banco em nuvem gratuito (Turso ou Supabase) — me pede
   quando incomodar.
2. **750 horas grátis/mês no Render** = dá exatamente pra 1 serviço
   ligado 24/7 (um mês tem ~744h). Então: só este bot na conta gratuita.
3. **Primeiro deploy do mês pode demorar** alguns minutos. Normal.

---

# 🔧 Problemas comuns

**Deploy falhou com erro vermelho** → clique em "Logs" no Render e veja a
última linha. Erro comum: esqueceu de subir o `requirements.txt` no GitHub.

**Bot "Live" mas não responde no Telegram** → 1) confira as 3 chaves em
Environment (sem espaços extras); 2) veja se não tem outra cópia do bot
rodando no seu PC; 3) olhe os Logs.

**"❌ Faltam variáveis"** nos logs → alguma Environment Variable com o
nome escrito errado. Tem que ser EXATAMENTE `TELEGRAM_TOKEN`,
`GEMINI_API_KEY`, `GROQ_API_KEY`.

**Bot responde "🔒 Este é um bot pessoal"** para VOCÊ → seu
`TELEGRAM_USER_ID` está errado. Confirme com o @userinfobot e corrija no
painel do Render (ele reinicia sozinho ao salvar).

**Atualizei o código, e agora?** → suba o arquivo novo no GitHub (Upload
files → substitui) e o Render redeploya automaticamente.

Bons estudos e parabéns pelo primeiro projeto publicado! 🚀
