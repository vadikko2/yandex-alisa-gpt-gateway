---
name: timeweb-ai
description: Manage Timeweb Cloud AI services — create and inspect AI agents
  (LLM assistants), pick a model with live token pricing, create knowledge bases
  (RAG), add documents by URL, link knowledge bases to agents, buy token packages
  when quota runs low, and read token-usage statistics. Use when the user says
  "создай агента", "подключи базу знаний", "кончились токены", "докупи токены",
  "сколько токенов сжёг агент", or asks about RAG on Timeweb Cloud. Do NOT use for
  the AI Gateway / ai-keys product or for changing an existing agent's model or
  system prompt (panel-only). Model lists and token prices must come from the live
  MCP catalog, never from pre-trained knowledge.
---

# Timeweb Cloud AI Agents & Knowledge Bases

## Concepts

An **AI Agent** is a hosted LLM assistant: model + system prompt + optional
Knowledge Bases (RAG) + tools/channels. A **Knowledge Base (KB)** is a document
store backed by a managed database; agents retrieve from it via RAG. One KB can
serve many agents and vice versa.

Billing differs: **new agents are pay-as-you-go** — tokens are debited from the
account balance hourly, no quota; only some **older agents use token packages**
with a quota (`total_tokens` / `used_tokens` / `remaining_tokens`). **KBs always
have a token quota** topped up with packages. Check `get_ai_agent` to see which
billing model a given agent is on: the token fields are present on BOTH (on
pay-as-you-go they are simply zero) — the reliable marker is
`token_package_id`: set = package model, null = pay-as-you-go.

## How to act

Through the Timeweb Cloud MCP (`timewebCloud`): `search_tools` →
`get_tool_definition` → `execute_tool`. `[WRITE]` needs the two-step
`confirm_token` flow (300 s TTL); `[BILLABLE]` charges immediately.

## Tool map

Agents (namespace `ai`):
- `list_ai_agents`, `get_ai_agent` — inventory and details (incl. token quota)
- `create_ai_agent` `[WRITE]` `[BILLABLE]` — new agent, per-resource billing
- `update_ai_agent_meta` `[WRITE]` — name/description ONLY
- `get_ai_agent_statistics` — token usage time series (bucketed by
  `interval_minutes`; always pass `start_time`/`end_time` — a bare call fails)
- `add_ai_agent_token_package` `[WRITE]` `[BILLABLE]` — top up agent tokens
- `link_knowledge_base_to_agent` `[WRITE]` — enable RAG for an agent

Knowledge bases (namespace `knowledgebase`):
- `list_knowledge_bases`, `list_knowledge_base_documents` (paginated, ≤100/page),
  `get_knowledge_base`, `get_knowledge_base_statistics` (token quota)
- `list_knowledge_base_token_packages` — price list of KB token packages
  (`base` / `additional` / `promo`), source of `token_package_id`; agent
  packages are NOT here (those live in the catalog)
- `create_knowledge_base` `[WRITE]` `[BILLABLE]`
- `create_knowledge_base_document_from_url` `[WRITE]` — add a document by URL
- `upload_knowledge_base_document` `[WRITE]` — create a document from INLINE
  TEXT (≤256k chars, filename with a text extension: .md/.txt/.csv/.json/
  .yaml/.html). For saving text produced in the dialog. **It cannot upload a
  user's file: MCP carries text, not files — PDF/DOCX/XLSX/images stay
  panel-only regardless of phrasing.** Indexing is async and consumes the KB
  token quota
- `reindex_knowledge_base_document`, `update_knowledge_base_document`,
  `update_knowledge_base_meta` `[WRITE]`
- `add_knowledge_base_token_package` `[WRITE]` `[BILLABLE]` — top up RAG tokens

Model and price catalogs:
- `list_ai_models` (namespace `ai`) — the foundation-model catalog (~100
  entries; narrow with `type`). Only `llm` and `hosted-llm` models can back an
  agent (`create_ai_agent(model_id)`); `image` works as an extra model.
  **NEVER offer an `embedding` model as an agent model — creation succeeds and
  the agent silently doesn't work**; `audio` is not wired into agents. In
  `parameter_values` an ABSENT key means unknown, not zero/false. Token
  packages are NOT returned here
- `get_cloud_service_catalog` (namespace `catalog`) — models with
  token-package pricing for agents. Together with `list_ai_models` and
  `list_knowledge_base_token_packages`, the only valid source of model lists
  and prices.

## Decision guide

| User intent | Do this |
|---|---|
| "Создай агента" | `list_ai_models` (llm/hosted-llm only) + `get_cloud_service_catalog` for prices → let the user pick model and confirm cost → `create_ai_agent` |
| "Подключи базу знаний / сделай RAG" | `list_knowledge_base_token_packages` for the package price → `create_knowledge_base` (confirm price) → `create_knowledge_base_document_from_url` per document → `link_knowledge_base_to_agent` |
| "Сохрани это в базу знаний" (text from the dialog) | `upload_knowledge_base_document` — write the FINISHED text into `content`; a description of the text is not the text |
| "Загрузи мой PDF/DOCX в базу" | Impossible via MCP — files don't reach the server; panel only. Public URL → `create_knowledge_base_document_from_url` |
| "Кончились токены / агент не отвечает" | `get_ai_agent` first. Package-billed agent (has a quota): if `remaining_tokens` is low, offer `add_ai_agent_token_package` with the price. Pay-as-you-go agent: no quota — check account balance (`get_account_finances`) and the agent's consumption limit (panel) instead |
| "Сколько токенов сжёг агент / когда пик" | `get_ai_agent_statistics` with a sensible `interval_minutes` for the period |
| "Переименуй агента" | `update_ai_agent_meta` |
| "Смени модель / промпт агента" | Not exposed via MCP — done in the panel (Playground), see below |
| "Подключи Telegram / виджет / Jivo / MAX" | Panel only; each channel has its own prerequisites and quirks — see references/channels-and-features.md before advising |
| "Поставь агента на паузу" | Panel only — and warn: pause does NOT stop billing |
| "Как дергать агента по API / из кода" | Three paths (OpenAI-compatible / native / AI Gateway) — comparison table in references/channels-and-features.md |

## Worked example: "агент перестал отвечать"

1. `execute_tool("get_ai_agent", {agent_id})` → status and billing model.
2. `execute_tool("get_ai_agent_statistics", {agent_id, ...})` with a small
   `interval_minutes` around the last activity → when consumption spiked.
3. Branch on what step 1 showed:
   - **Package-billed agent** (has a token quota) and `remaining_tokens` ≈ 0:
     «У агента закончились токены (осталось N из M). Могу докупить пакет на
     K токенов за P ₽ (цена из каталога) — докупать?» On yes →
     `add_ai_agent_token_package` twice: first call returns `confirm_token` +
     summary with the charge, second call executes it.
   - **Pay-as-you-go agent** (no quota): check `get_account_finances` — the
     account balance may be exhausted; or the agent hit its consumption limit,
     which is raised in the panel only. Report which one it is.

Deep dives: [references/tokens-and-billing.md](references/tokens-and-billing.md) —
what consumes tokens (system prompt + history + KB context), hourly debits,
consumption limits, reasoning-model costs;
[references/knowledge-bases.md](references/knowledge-bases.md) —
source formats and limits, indexing behavior, URL/SPA gotchas, triage table;
[references/channels-and-features.md](references/channels-and-features.md) —
channels (Telegram/MAX/Jivo/widget), chat history, web search, image
generation, attachments per model, pause/delete semantics, the three API paths.

## Not available through MCP — send to the panel

- **Changing an agent's model, system prompt, temperature, or token limits** —
  deliberately closed (an LLM editing a running LLM is high-risk). All of it IS
  doable in the panel's Playground — send the user there.
- **Channels (widget, Telegram, MAX, Jivo, external chat), web search, image
  generation, pause** — configured in the panel only.
- **Uploading document FILES to a KB** (PDF, DOCX, XLSX, images, archives) —
  MCP carries text, not files. Inline text works (`upload_knowledge_base_document`)
  and URLs work (`create_knowledge_base_document_from_url`); binary files go
  through the panel.
- **Deleting agents, KBs, or documents** — no delete operations exist. Deleting
  an agent in the panel does NOT delete its KBs — they keep billing separately.

Quote the `not_exposed` reason, link https://timeweb.cloud, stop. No workarounds —
in particular, do NOT delete-and-recreate an agent to "change" its model.

## Billing safety

Token packages and agent/KB creation charge the account **immediately**. Always:
fetch the current package/model price from the catalog, state it, get an explicit
yes, then execute with the confirm token. When topping up, first show
`remaining_tokens` so the user sees why.

## Troubleshooting

| Symptom | Cause | Action |
|---|---|---|
| Agent stopped answering mid-conversation | Quota exhausted (package agents) / balance or consumption limit (pay-as-you-go) | `get_ai_agent` → quota agents: offer a package; PAYG: check `get_account_finances`, limits are panel-only |
| KB linked but answers ignore documents | Documents still indexing or quota exhausted | Check document list/status and KB `remaining_tokens`; indexing takes time after adding |
| Usage chart contradicts the user's feeling | Statistics are bucketed | Re-query with a smaller `interval_minutes` before concluding anything |
| "Смени модель" fails | Operation not exposed | Panel, with the reason quoted |

## Anti-patterns (NEVER)

- NEVER pick a model or quote token prices from memory — `list_ai_models` and
  the catalogs only; the lineup changes often.
- NEVER back an agent with an `embedding` model — the backend accepts it and
  the agent silently doesn't work; agents take `llm`/`hosted-llm` only.
- NEVER buy a token package without showing the price and current remaining tokens.
- NEVER delete-and-recreate resources as a workaround for a closed operation.
- NEVER touch an agent's prompt/model settings even if the user insists it "should
  be possible" — explain it is panel-only by design.
