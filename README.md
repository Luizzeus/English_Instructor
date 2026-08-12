# Instrutor de Inglês com IA

Aplicativo de ensino de inglês focado em conversação, com bot de IA adaptado ao nível CEFR do aluno, métricas de evolução e simulações de cenários do cotidiano. Decisões de arquitetura, riscos e modelo de dados: [`docs/architecture.md`](docs/architecture.md).

**Stack 100% open-source / custo zero** (pivô decidido em 2026-08-12, ver seção 1.1 do doc de arquitetura): FastAPI (backend) + React/TypeScript (frontend) + **PostgreSQL** (self-hosted) + **Ollama** (LLM local, open-weight) + **auth própria** (email/senha, `bcrypt` + JWT, sem provedor externo). Só a camada de voz ainda depende do Azure Speech (migração para faster-whisper + Piper pendente) — o `.env` ainda tem essas chaves antigas enquanto essa peça não migra.

## Pré-requisitos

- Python 3.12+ (testado em 3.14)
- Node.js 20+
- Docker (para rodar o PostgreSQL local)
- [Ollama](https://ollama.com) instalado e rodando localmente (LLM open-source, sem chave de API)
- Chave de API do Azure Speech (não obrigatória para subir o scaffold — só para o modo voz, que ainda depende dele até a migração terminar)

## Backend (`backend/`)

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate       # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
cp .env.example .env           # preencher DATABASE_URL e as chaves de API
```

Suba o PostgreSQL local via Docker (se ainda não tiver um rodando):

```bash
docker run -d --name english-instructor-pg \
  -e POSTGRES_PASSWORD=SUA_SENHA \
  -e POSTGRES_DB=english_instructor \
  -p 5432:5432 \
  postgres:17-alpine
```

Com `DATABASE_URL` apontando para essa instância:

```bash
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
python -m app.db.seed   # cria o cenário "Small talk profissional" (idempotente)
```

Subir a API:

```bash
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/api/health`

Rodar os testes (não precisam de Postgres nem de Ollama rodando — usam SQLite in-memory e mockam a chamada ao LLM):

```bash
pip install -r requirements-dev.txt
pytest
```

## LLM (Ollama, local)

1. Instale o [Ollama](https://ollama.com/download) — no Windows, `winget install Ollama.Ollama`.
2. Baixe o modelo usado por padrão: `ollama pull qwen2.5:7b-instruct` (~4.7GB, licença Apache 2.0).
3. O serviço do Ollama já sobe sozinho em `http://127.0.0.1:11434` depois de instalado (confirme com `curl http://127.0.0.1:11434/api/version`).

Configuração no `.env` do backend (valores padrão, normalmente não precisa mexer):

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
```

**Trade-off real, medido nesta máquina (sem GPU dedicada):** uma resposta curta leva **~20 segundos** rodando em CPU — bem mais lento que uma API paga, e a qualidade das correções/adaptação de nível é mais simples que a de um modelo maior. Aceito deliberadamente em troca de custo zero e não depender de nenhum provedor pago (ver `docs/architecture.md` seção 1.1). Se algum dia fizer sentido pagar por qualidade/velocidade, o código do provedor Anthropic continua disponível — troque `LLM_PROVIDER=anthropic` no `.env` e preencha `ANTHROPIC_API_KEY`, nada mais muda.

## Frontend (`frontend/`)

```bash
cd frontend
npm install
cp .env.example .env           # ajustar VITE_API_BASE_URL se necessário
npm run dev
```

Abre em `http://localhost:5173`. Com o backend rodando, a página mostra o status de conexão com `/api/health`.

## Autenticação (própria — email/senha)

Sem provedor externo. `Student` é a própria tabela de usuário (`email` + `hashed_password`). Configuração no `.env` do backend:

```bash
SECRET_KEY=...   # gere com: python -c "import secrets; print(secrets.token_urlsafe(48))"
ACCESS_TOKEN_EXPIRE_MINUTES=20160   # 14 dias
```

Sem `SECRET_KEY` configurada, os endpoints de auth falham explicitamente (`RuntimeError: SECRET_KEY is not configured`) — não há fallback inseguro.

Fluxo: `POST /api/auth/register` (email, senha, nome) ou `POST /api/auth/login` (email, senha) → backend retorna `{access_token, student}` → frontend guarda o token no `localStorage` (`frontend/src/lib/api.ts`) e manda `Authorization: Bearer <token>` em toda chamada autenticada. `GET /api/students/me` valida o token e devolve o perfil — usado ao recarregar a página para restaurar a sessão. Senhas são hasheadas com `bcrypt`, nunca guardadas em texto puro; tokens são JWT HS256 assinados com `SECRET_KEY`, sem estado no servidor (logout é só apagar o token no cliente).

Registro duplicado (mesmo email) é tratado como corrida real: duas tentativas concorrentes de registro com o mesmo email podem ambas passar pela checagem inicial e tentar inserir — o índice único do banco pega a perdedora, que recebe um 400 limpo em vez de um 500 (`backend/tests/test_auth.py::test_register_recovers_from_concurrent_duplicate_race` reproduz isso de verdade, não só no papel).

## Bot de conversação (protótipo em texto)

Um cenário completo está funcional de ponta a ponta: "Small talk profissional" (papo antes de uma reunião remota começar). Fluxo: `POST /api/sessions` (inicia sessão, bot manda a mensagem de abertura) → `POST /api/sessions/{id}/messages` (aluno responde, backend monta o histórico completo e chama o LLM configurado com um system prompt adaptado ao nível CEFR do aluno, aplicando correção implícita via recast) → `POST /api/sessions/{id}/end`. UI de chat em `frontend/src/Chat.tsx`, serviço de conversação em `backend/app/services/conversation.py`.

O provedor de LLM é abstraído em `backend/app/services/providers/` (`LLMProvider`, `AnthropicProvider`, `OllamaProvider`) e escolhido via `LLM_PROVIDER` no `.env` — troca de provedor não exige mudar `conversation.py` nem `metrics.py`.

## Camada de voz (Azure AI Speech)

Ao iniciar uma sessão com "Iniciar por voz", o botão 🎤 grava o microfone (Web Audio API, sem dependências externas), encoda como WAV 16 kHz/16-bit/mono no navegador (`frontend/src/lib/wavRecorder.ts`) e envia para `POST /api/sessions/{id}/voice-messages` (multipart). O backend (`backend/app/services/speech.py`):

1. Transcreve e avalia a pronúncia em modo *unscripted* (sem texto de referência — o aluno fala livremente, não repete um script), retornando scores de precisão, fluência, completude e pronúncia (0-100).
2. Gera a resposta do bot com o mesmo serviço de conversação do fluxo em texto.
3. Sintetiza a resposta em áudio (voz neural do Azure) e devolve como base64; o frontend toca automaticamente.

Configuração necessária: `AZURE_SPEECH_KEY` + `AZURE_SPEECH_REGION` no `.env` do backend (conta no [portal.azure.com](https://portal.azure.com), recurso "Speech"). Sem essas chaves, os endpoints de voz respondem com erro — não há fallback silencioso.

**Limitação conhecida:** não há credenciais reais do Azure Speech configuradas neste ambiente de desenvolvimento, então o fluxo foi validado com a integração mockada (`backend/tests/test_voice_flow.py`) — a qualidade real da transcrição/avaliação/síntese contra a API do Azure ainda não foi verificada manualmente.

## Métricas de evolução

Ao encerrar uma sessão (`POST /api/sessions/{id}/end`), o backend calcula automaticamente 3 indicadores a partir das mensagens do aluno naquela sessão e salva um `MetricSnapshot`:

- **Vocabulário ativo**: contagem de palavras-conteúdo únicas usadas (heurística por tokenização, sem lematização).
- **Erros gramaticais por 100 palavras**: o LLM configurado conta erros numa chamada estruturada dedicada (`app/services/metrics.py::grade_grammar_errors`), separada da correção implícita que o bot já faz durante a conversa.
- **Fluência (palavras/min)**: só para sessões de voz, calculada a partir da duração real do áudio gravado — `null` em sessões de texto.

O histórico fica em `GET /api/students/me/metrics` e aparece como uma tabela simples (`frontend/src/Metrics.tsx`, sem gráfico nesta primeira versão) logo abaixo do chat, atualizada automaticamente ao encerrar uma sessão. **Nenhum dos 3 indicadores é uma medida linguística validada** — são heurísticas propositalmente simples para a primeira versão; detalhes e limitações completas em `docs/architecture.md`. O campo `estimated_cefr_level` do snapshot ainda só repete o nível atual do aluno — a lógica real de promoção de nível é o próximo item do backlog.

## Variáveis de ambiente sensíveis

Nenhum `.env` é versionado (ver `.gitignore`) — apenas os `.env.example`. `SECRET_KEY`, chave da Azure Speech e (se usada) chave da Anthropic ficam só localmente ou em secrets do ambiente de deploy.

## Estado atual

Backend FastAPI com modelo de dados completo (SQLAlchemy + Alembic, agora em **PostgreSQL**), auth própria (email/senha, sem provedor externo), protótipo funcional do bot de conversação em texto e voz (um cenário completo, agora rodando em **Ollama local**), e cálculo automático de 3 métricas de evolução por sessão com dashboard básico — tudo testado automaticamente (23 testes) e validado de ponta a ponta no navegador (registro, login, persistência de sessão, conversa completa, métricas). **Migração para stack 100% open-source/custo zero** (iniciada 2026-08-12, ver `docs/architecture.md` seção 1.1): banco (Postgres) ✅, LLM (Ollama) ✅ e autenticação (email/senha própria) ✅ concluídos; só falta voz (Azure Speech → faster-whisper + Piper). Ainda não implementados: promoção de nível CEFR, recomendação de ferramentas, repetição espaçada, gamificação. Backlog priorizado em `docs/architecture.md` (seção 5).
