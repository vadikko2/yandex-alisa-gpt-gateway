# Knowledge Bases: Sources, Indexing, Limits

Snapshot of the public docs (timeweb.cloud/docs/ai-agents/manage-knowledge-bases/*),
not live truth: supported formats and size limits change — if an upload fails
against what is written here, believe the error, not this file.

## What a KB accepts (public limits)

- **File formats**: .txt, .md, .csv, .htm/.html, .xml, .pdf, .doc/.docx,
  .xls/.xlsx. Text only — images and video inside documents are not indexed.
- **Size**: up to 50 MB per file; 1–100 files per upload batch.
- **Tables** (CSV/XLS): the first row must contain column names, otherwise
  retrieval quality degrades.
- **URL sources**: the page must be reachable without authorization and render
  its content without JavaScript (server-side HTML, not an SPA) — if `curl`
  can't fetch meaningful text, indexing can't either.

## Through MCP vs through the panel

Via MCP you can create a KB (`create_knowledge_base`), add **URL documents**
(`create_knowledge_base_document_from_url`), add **inline text documents**
(`upload_knowledge_base_document` — up to 256k characters, filename with a
text extension: .md/.txt/.csv/.json/.yaml/.html; write the finished text into
`content`), list documents, re-index and edit them, link the KB to an agent,
and buy token packages (prices — `list_knowledge_base_token_packages`).
**Binary file uploads are panel-only**: MCP carries text, not files, so a
user's PDF/DOCX/XLSX/image never reaches the server — send the user to the
panel and continue after they upload.

## Indexing behavior

- Indexing happens after a document is added and takes time (depends on size);
  the agent will not use a document until indexing completes. If "база знаний
  не работает" right after adding documents — check the document list first;
  it is usually still indexing.
- Indexing spends KB tokens (embeddings are generated per chunk). Big CSVs are
  the most expensive per MB. If quota runs out mid-indexing, top up
  (`add_knowledge_base_token_package`) — with the live package price.
- URL sources support re-indexing: a manual reindex button in the panel and
  scheduled auto-reindexing that re-fetches when the page's ETag changes.
  Recommend auto-reindex for docs/FAQ pages that change often.

## Linking to agents

One KB can serve several agents; one agent can use several KBs
(`link_knowledge_base_to_agent`). Every linked KB adds retrieved context to
each agent request — more linked KBs means more input tokens per request
(see tokens-and-billing.md in this directory).

## Quick triage: "агент не отвечает по базе"

| Check | Tool |
|---|---|
| KB actually linked to this agent? | `get_ai_agent` |
| Documents finished indexing? | `list_knowledge_base_documents` |
| KB token quota left? | `list_knowledge_bases` → remaining_tokens |
| Source was an SPA / behind auth? | ask the user for the URL, check it renders without JS |
