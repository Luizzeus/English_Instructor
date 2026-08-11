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
```

Subir a API:

```bash
uvicorn app.main:app --reload
```

Health check: `GET http://localhost:8000/api/health`

## Frontend (`frontend/`)

```bash
cd frontend
npm install
cp .env.example .env           # ajustar VITE_API_BASE_URL se necessário
npm run dev
```

Abre em `http://localhost:5173`. Com o backend rodando, a página mostra o status de conexão com `/api/health`.

## Variáveis de ambiente sensíveis

Nenhum `.env` é versionado (ver `.gitignore`) — apenas os `.env.example`. Chaves de Anthropic, Azure Speech e Clerk ficam só localmente ou em secrets do ambiente de deploy.

## Estado atual

Scaffold inicial: backend FastAPI com modelo de dados completo (SQLAlchemy + Alembic) e frontend Vite/React conectando ao health check. Ainda não implementados: integração real do Clerk, bot de conversação, camada de voz, métricas, recomendação de ferramentas. Backlog priorizado em `docs/architecture.md` (seção 5).
