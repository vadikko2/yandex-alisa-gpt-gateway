# Agent Channels, Features and APIs

Snapshot of the public docs (timeweb.cloud/docs/ai-agents/*), not live truth:
channel limits and model lineups change — verify in the panel or via
`get_cloud_service_catalog` before quoting them. **All channel setup,
pause and feature toggles are panel-only** — the MCP has no tools for them.
Know the consequences, advise correctly, link the panel.

## Channels

- **Site widget**: one script line in `<body>`. Domain allowlist semantics:
  empty list = works on any site; adding even ONE domain restricts the widget
  to listed domains only. Custom font is not shipped with the widget — a
  system fallback is used. Supports attachments if enabled on the agent.
- **External chat** (ai.timeweb.cloud): requires logging into a Timeweb Cloud
  account; visible to the owner only by default — access is granted via
  "Права и доступы". Keeps full agent config (prompt, KB, MCP tools).
- **Telegram**: token from BotFather; one agent can power several bots; works
  in DMs and groups. Access can be restricted to a list of logins (without @)
  — applies in both DMs and groups, strangers get a refusal.
- **MAX**: bots can be created only by organizations/sole proprietors with a
  verified org profile on the MAX partner platform, and the bot passes
  moderation — an individual asking for a MAX bot will hit this wall.
- **Jivo**: one agent = one Jivo bot = one communication channel. Requires a
  Provider ID issued by Jivo support via email (takes hours). The agent
  answers first; operators see the dialog in Jivo.

## Chat history

Saved for: widget, Telegram, playground. **Dialogs via API are NOT saved** —
if the user asks "где история", first ask which channel. CSV export is capped
at the last 2000 messages. Retention period is not documented.

## Web search

A toggle; the agent itself decides per query whether to search (Yandex-based).
Billed **per executed search request** (on top of normal tokens) — rate in the
docs/panel. Search can be restricted to a domain list. If the user complains
about search charges, remind: one user message can trigger several searches.

## Image generation

Toggle; Gemini image models (fast and detailed variants). The agent decides
when a message is an image request. Billed as tokens (prompt in, image out),
separately from text. Works in the external chat and the widget.

## Attachments in chats

Model-dependent — this matrix answers most "почему файл не прикрепляется":

| Model family | Accepts |
|---|---|
| ChatGPT | images (.jpg/.png/.gif/.webp), documents (.pdf/.docx/.xlsx), code files |
| Claude, Gemini | images only (.jpg/.png/.webp/.gif) |
| Grok | images (.jpg/.png/.webp) |
| DeepSeek, Yandex, Qwen | no attachments at all |

Limit: 5 MB per file, several files per message; channels: widget and
external chat. Token cost of attachments (per docs): image ≈
(width/512) × (height/512) × 700 tokens; Russian text ≈ characters/3.5;
English ≈ characters/4.

## Pause and delete (panel-only)

- **Pause does NOT save money**: billing continues as usual and the monthly
  charge date doesn't move; the widget disappears and the API returns 400.
  Never present pause as a cost-saving measure.
- **Delete is irreversible**, and linked knowledge bases survive — they keep
  billing until deleted separately (deleting a KB also removes its managed
  database).

## Three API paths (when the user asks "как дергать агента из кода")

| Path | History | Streaming | RAG/MCP tools |
|---|---|---|---|
| OpenAI-compatible (`.../v1/chat/completions`, URL on the agent dashboard) | client sends it in messages | yes | yes |
| Native (`POST .../agents/{id}/call`) | auto via `parent_message_id` | no | yes |
| AI Gateway (separate product, api.timeweb.ai) | client-side | yes | no — raw model |

OpenAI-compatible gotchas: the `model` parameter is ignored (the agent's model
is used); Embeddings/Images/Audio/Assistants endpoints are not supported; for
gpt-5-family use `max_completion_tokens` instead of `max_tokens`, and
`temperature` causes an error. The agent's API access key is shown **once** at
creation — if lost, a new one must be issued in the panel.
