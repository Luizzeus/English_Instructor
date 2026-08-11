# Arquitetura — Instrutor de Inglês com IA (Foco em Conversação)

Status: decisões estruturais validadas em 2026-08-11. Este documento é vivo — atualizar a cada decisão nova, não só ao final.

## 1. Decisões estruturais (seção 5 do briefing)

| # | Decisão | Escolha | Justificativa |
|---|---|---|---|
| 1 | Plataforma-alvo | Web app (PWA) | Deploy único, instalável no celular via browser, sem fricção de app store. Sessões curtas (5-20min) cabem bem no browser mobile. Mobile nativo fica para fase 2 se houver tração. |
| 2 | Backend | Python + FastAPI | Ecossistema de IA/NLP mais maduro (SDK Anthropic, spaCy para complexidade sintática, integração com STT/TTS) do que .NET/Java para este domínio. |
| 2 | Frontend | React + TypeScript | Padrão de mercado para chat/dashboard interativo; ecossistema maduro de componentes de áudio/streaming. |
| 3 | LLM de conversação | Claude (Sonnet) via API Anthropic | Bom custo/benefício; segue system prompts complexos (persona, nível CEFR, correção implícita via recast) de forma confiável. |
| 3 | STT + avaliação de pronúncia/fluência | Azure AI Speech | API dedicada de *Pronunciation Assessment* (precisão, fluência, completude) — cobre diretamente as métricas da seção 3.2 sem precisar construir essa lógica do zero. |
| 3 | TTS | Azure Neural TTS | Mesmo serviço da Azure Speech, vozes naturais, custo previsível e integração única. |
| 4 | Armazenamento primário | SQL Server | Modelo relacional claro (aluno, sessão, métrica, cenário, exercício, recomendação); facilita queries agregadas/históricas para a lógica auditável de promoção de nível CEFR. |
| 4 | Transcrições de conversa | Coluna JSON no SQL Server | Evita persistência poliglota prematura no MVP. Migração para MongoDB só se volume/flexibilidade justificarem depois. |
| 5 | Autenticação | Clerk (provedor gerenciado) | Multiusuário exige auth robusto (MFA, login social, proteção contra brute-force). Clerk tem SDK React de primeira classe e verificação de JWT simples no FastAPI. Free tier cobre o MVP. |
| 6 | Modelo de custo | Free tier com limite rígido, sem cobrança ainda | Sem gateway de pagamento no MVP. Foco em validar o produto; monetização entra depois de validação. |

## 2. Riscos técnicos identificados (sinalizar cedo, não só no final)

- **Custo de IA em escala**: bot de conversação (Claude) + STT/TTS (Azure) por sessão. Precisa de tracking de tokens/segundos por usuário desde o dia 1, com hard cap diário — não é opcional dado o modelo "free tier sem cobrança".
- **Latência de voz**: pipeline completo é STT → LLM → TTS. Cada etapa soma latência; meta realista para turno de voz é ~3-5s (mais alta que texto puro, que mira 2-3s). Precisa ser comunicado como expectativa desde o protótipo, com streaming de áudio para mitigar percepção de espera.
- **Qualidade da correção gramatical automática**: recast implícito via LLM pode ser inconsistente; validar com casos de teste reais antes de confiar no "resumo de erros recorrentes" como métrica.
- **Lógica de promoção de nível CEFR precisa ser auditável**: não pode ser um score de IA opaco — implementar como regras explícitas sobre as métricas objetivas (vocabulário ativo, taxa de erro, complexidade sintática, fluência), com o LLM apenas alimentando esses indicadores, não decidindo a promoção diretamente.

## 3. Componentes (visão de alto nível)

```
[React PWA] --(HTTPS/WSS)--> [FastAPI backend]
                                   |-- Clerk (auth, JWT verification)
                                   |-- Anthropic API (Claude - bot de conversação)
                                   |-- Azure AI Speech (STT + Pronunciation Assessment + TTS)
                                   |-- SQL Server (dados relacionais + transcrições JSON)
                                   |-- Serviço de métricas (calcula CEFR, vocabulário, complexidade)
                                   |-- Serviço de recomendação (ferramentas complementares)
```

Fluxo de voz: cliente grava áudio → upload para backend → Azure STT + Pronunciation Assessment → texto + scores → Claude gera resposta → Azure TTS → áudio retorna ao cliente (streaming quando possível).

## 4. Modelo de dados (rascunho — entidades principais)

- **Student**: id, clerk_user_id, nome, nível CEFR atual, data de criação, preferências (tom do bot, duração padrão de sessão).
- **Session**: id, student_id, cenário_id, início, fim, modalidade (texto/voz), status.
- **Message**: id, session_id, autor (aluno/bot), texto, áudio_url (se houver), timestamp, correções implícitas aplicadas (recast).
- **MetricSnapshot**: id, student_id, session_id, data, vocabulário_ativo_count, taxa_erro_por_100_palavras, palavras_por_minuto, complexidade_sintática_média, nível_cefr_estimado.
- **CefrPromotionLog**: id, student_id, data, nível_anterior, nível_novo, métricas_usadas (JSON), regra_aplicada — auditável, não caixa-preta.
- **Scenario**: id, nome, descrição, persona_do_bot, contexto (JSON com system prompt base), nível_cefr_alvo, tags (ex.: "trabalho remoto", "entrevista").
- **ExerciseAttempt**: id, session_id, tipo (completar frase, escolha, reformulação, shadowing), item_vocabulário/estrutura_alvo, acerto (bool), timestamp — alimenta repetição espaçada.
- **SpacedRepetitionCard**: id, student_id, item (palavra/estrutura), próxima_revisão, intervalo_atual, histórico_de_acertos.
- **ToolRecommendation**: id, student_id, ferramenta, motivo (referência à lacuna específica identificada), tem_alternativa_gratuita (bool), data.

## 5. Próximos passos propostos (backlog priorizado, fase 1)

1. Scaffold do repo: estrutura de pastas (backend FastAPI, frontend React), git init, configuração de ambiente.
2. Modelo de dados: schema SQL Server (migrations) para as entidades acima.
3. Integração Clerk (auth) end-to-end (frontend + verificação de JWT no backend).
4. Protótipo do bot de conversação (texto apenas primeiro, um cenário completo: ex. "small talk profissional") — valida o núcleo antes de acrescentar voz.
5. Camada de voz: Azure STT (Pronunciation Assessment) + TTS integrados ao mesmo fluxo de conversação.
6. Serviço de métricas: cálculo dos 3 indicadores mais simples primeiro (vocabulário ativo, taxa de erro, fluência) + dashboard básico.
7. Lógica de promoção de nível CEFR (regras explícitas e auditáveis).
8. Módulo de recomendação de ferramentas (contextual, justificado).
9. Repetição espaçada + exercícios variados dentro do diálogo.
10. Gamificação leve (streak, metas semanais).

Dependências: 2 bloqueia 3-9 (tudo depende do schema). 3 bloqueia qualquer feature multiusuário real. 4 deve ficar estável antes de 5 (adicionar voz em cima de um bot de texto que já funciona, não em paralelo).
