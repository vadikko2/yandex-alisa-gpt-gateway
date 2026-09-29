# Tokens and AI Billing

Semantics only, and a snapshot of the public docs rather than live truth: every
price comes from `get_cloud_service_catalog` (AI models with token packages) or
the panel, never from this file. If a tool response contradicts what is written
here, the tool wins.

## What a token is

Models split text into tokens: a word fragment, a short word, or a punctuation
mark. Rough guide: **1 000 tokens ≈ 750 words** in Russian or English. Both
directions are counted: input tokens (the request) and output tokens (the
answer), priced separately per model.

## What actually consumes tokens per request

Users usually underestimate input. Every agent request includes:

- the **system prompt** of the agent — every single time;
- the **conversation history** — grows with every turn;
- **knowledge-base context** — retrieved chunks are injected into the request
  when a KB is linked;
- the user message itself, and then the model's answer as output tokens.

So a long system prompt + long dialog + linked KB can make a one-line question
cost thousands of input tokens. This is the standard explanation for "почему
агент столько ест" — check `get_ai_agent_statistics` before theorizing.

## How agents are billed

New agents are **pay-as-you-go**: a small fixed monthly fee per agent, plus
tokens debited from the account balance **once per hour** at per-model rates.
(Package-based billing exists only on some old agents.) A **consumption limit**
can be set per agent — at creation or later in the panel ("Управление" →
"Установить лимиты") — to cap spending; recommend it when the user worries
about costs.

## How knowledge bases are billed

Two components: a monthly token subscription (first charge immediately at
creation) and an hourly-billed managed OpenSearch database backing the KB.
KB tokens are spent on **indexing documents** (embedding generation) and on
**search at query time**. Consumption per megabyte differs a lot by format:
CSV is roughly twice as expensive as plain text; HTML is much cheaper per MB.
Extra token packages (`add_knowledge_base_token_package`,
`add_ai_agent_token_package`) are valid until the end of the current paid
period — they do not roll over; say this before selling one. Agent packages
apply only to package-billed (older) agents and come in multiples of 250k
tokens.

## Package-billed agents: plan changes (panel-only)

The plan can only be **increased**, never downgraded; the change applies
instantly and **unused tokens of the old plan burn** — they do not migrate.
So when a package agent is short on tokens near the end of the month, buying
an extra package is usually smarter than upgrading the plan; say this
trade-off out loud.

## Reasoning models eat more

Models marked as reasoning ("режим размышлений") cannot have thinking turned
off, and it increases BOTH input and output token consumption on every
iteration. If a user complains a reasoning model burns tokens faster than the
previous one — that's expected behavior, not a bug; suggest a non-reasoning
model (model change is panel-only).

## Diagnosing "агент замолчал" / cost complaints

1. `get_ai_agent` → status and billing model. Token fields are present on both
   models (zero on pay-as-you-go) — check `token_package_id`: set = package
   model, null = pay-as-you-go.
2. `get_ai_agent_statistics` → when the spike happened; use a small
   `interval_minutes` around it and always pass `start_time`/`end_time` —
   a bare call fails.
3. Branch by billing model:
   - **Package-billed** (quota): if `remaining_tokens` ≈ 0, offer a token
     package with the live price.
   - **Pay-as-you-go** (no quota): check `get_account_finances` — the account
     balance may be exhausted; otherwise the agent likely hit its consumption
     limit. Both raising the limit and setting it are panel-only — report,
     don't attempt.
4. Structural fixes for high burn: shorter system prompt, fewer/leaner KB
   documents — but changing model or prompt is panel-only, so recommend,
   don't execute.
