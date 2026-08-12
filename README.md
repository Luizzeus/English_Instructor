# Instrutor de Inglês com IA

Aplicativo de ensino de inglês focado em conversação, com bot de IA adaptado ao nível CEFR do aluno, métricas de evolução e simulações de cenários do cotidiano. Decisões de arquitetura, riscos e modelo de dados: [`docs/architecture.md`](docs/architecture.md).

Stack: FastAPI (backend) + React/TypeScript (frontend) + SQL Server + Claude (bot de conversação) + Azure AI Speech (STT/pronúncia/TTS) + Clerk (auth).

## Pré-requisitos

- Python 3.12+ (testado em 3.14)
- Node.js 20+
- SQL Server acessível (local ou remoto) + [ODBC Driver 18 for SQL Server](https://learn.microsoft.com/sql/connect/odbc/download-odbc-driver-for-sql-server) instalado
- Chaves de API: Anthropic, Azure Speech, Clerk (não obrigatórias para subir o scaffold — só para as features que as usam)

## Backend (`backend/`)

```bash
cd backend
python -m venv .venv
./.venv/Scripts/activate       # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
cp .env.example .env           # preencher DATABASE_URL e as chaves de API
```

Com `DATABASE_URL` apontando para uma instância SQL Server real:

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

Rodar os testes (não precisam de SQL Server nem de chave da Anthropic — usam SQLite in-memory e mockam a chamada ao LLM):

```bash
pip install -r requirements-dev.txt
pytest
```

## Frontend (`frontend/`)

```bash
cd frontend
npm install
cp .env.example .env           # ajustar VITE_API_BASE_URL se necessário
npm run dev
```

Abre em `http://localhost:5173`. Com o backend rodando, a página mostra o status de conexão com `/api/health`.

## Autenticação (Clerk)

1. Crie uma conta/app em [dashboard.clerk.com](https://dashboard.clerk.com).
2. No dashboard, copie:
   - **Publishable key** → `frontend/.env` como `VITE_CLERK_PUBLISHABLE_KEY`
   - **Secret key** → `backend/.env` como `CLERK_SECRET_KEY` (ainda não é usada pelo backend nesta fase — verificação de sessão é feita só via JWKS — mas fica registrada para as próximas integrações, ex. buscar dados de perfil via API do Clerk)
   - **Frontend API URL** (aparece em *API Keys* ou é `https://<seu-subdomínio>.clerk.accounts.dev`) → monte `CLERK_JWKS_URL` em `backend/.env` como `<frontend-api-url>/.well-known/jwks.json`
3. Sem essas chaves, o frontend mostra uma tela de "configuração pendente" em vez de quebrar, e o backend recusa qualquer request autenticada com 401 (não há fallback inseguro).

Fluxo implementado: o usuário clica em "Sign in" (modal do Clerk) → após autenticar, o frontend chama `POST /api/students/sync` com o token de sessão do Clerk → o backend valida o JWT contra o JWKS do Clerk (`app/core/security.py`) e cria/atualiza o `Student` correspondente pelo `clerk_user_id`. `GET /api/students/me` está protegido do mesmo jeito.

Se o app do Clerk estiver configurado para múltiplas origens além de `http://localhost:5173`, adicione-as em `CLERK_AUTHORIZED_PARTIES` (lista) no `.env` do backend — o backend rejeita tokens cujo `azp` não esteja nessa lista.

**Atenção ao testar o build do frontend:** sem `VITE_CLERK_PUBLISHABLE_KEY` definida, `main.tsx` renderiza uma tela de fallback e o Rollup elimina `App.tsx`/`Chat.tsx` do bundle inteiro por dead-code elimination — `npm run build` "passa" mesmo assim, mas não valida a UI de verdade. Para checar a build real, defina uma chave (mesmo que temporária) antes de buildar.

## Bot de conversação (protótipo em texto)

Um cenário completo está funcional de ponta a ponta: "Small talk profissional" (papo antes de uma reunião remota começar). Fluxo: `POST /api/sessions` (inicia sessão, bot manda a mensagem de abertura) → `POST /api/sessions/{id}/messages` (aluno responde, backend monta o histórico completo e chama Claude com um system prompt adaptado ao nível CEFR do aluno, aplicando correção implícita via recast) → `POST /api/sessions/{id}/end`. UI de chat em `frontend/src/Chat.tsx`, serviço de conversação em `backend/app/services/conversation.py`.

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
- **Erros gramaticais por 100 palavras**: Claude conta erros numa chamada estruturada dedicada (`app/services/metrics.py::grade_grammar_errors`), separada da correção implícita que o bot já faz durante a conversa.
- **Fluência (palavras/min)**: só para sessões de voz, calculada a partir da duração real do áudio gravado — `null` em sessões de texto.

O histórico fica em `GET /api/students/me/metrics` e aparece como uma tabela simples (`frontend/src/Metrics.tsx`, sem gráfico nesta primeira versão) logo abaixo do chat, atualizada automaticamente ao encerrar uma sessão. **Nenhum dos 3 indicadores é uma medida linguística validada** — são heurísticas propositalmente simples para a primeira versão; detalhes e limitações completas em `docs/architecture.md`. O campo `estimated_cefr_level` do snapshot ainda só repete o nível atual do aluno — a lógica real de promoção de nível é o próximo item do backlog.

## Variáveis de ambiente sensíveis

Nenhum `.env` é versionado (ver `.gitignore`) — apenas os `.env.example`. Chaves de Anthropic, Azure Speech e Clerk ficam só localmente ou em secrets do ambiente de deploy.

## Estado atual

Backend FastAPI com modelo de dados completo (SQLAlchemy + Alembic), auth Clerk integrada de ponta a ponta, protótipo funcional do bot de conversação em texto e voz (um cenário completo), e cálculo automático de 3 métricas de evolução por sessão com dashboard básico — tudo testado automaticamente (14 testes, Anthropic/Azure mockados). Ainda não implementados: promoção de nível CEFR, recomendação de ferramentas, repetição espaçada, gamificação. Backlog priorizado em `docs/architecture.md` (seção 5).
