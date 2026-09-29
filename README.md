# Шлюз Алисы к своему помощнику

Алиса открывает навык и задаёт ему вопрос. Этот сервис принимает webhook Диалогов и отвечает текстом вашей языковой модели.

Помощник в коде не зашит. Адрес и ключ лежат в настройках: другая модель ставится переменными окружения и перезапуском, без правки программы.

| | |
|---|---|
| Сколько ждёт Алиса | **4,5 секунды** вместе с дорогой до сервера и обратно |
| Если не успели | «Думаю. Скажите „дальше“». Ответ дочитывается в фоне |
| Закончить | «хватит», «выход», «стоп», «пока», «до свидания» или кнопка «Закончить» |
| Длина ответа | не больше **1024** символов, лишнее обрезается |
| Память диалога | только в этом запущенном экземпляре, после деплоя пропадает |

Протокол навыка: [Яндекс Диалоги](https://yandex.ru/dev/dialogs/alice/doc/ru/).

## Оглавление

1. [Как это устроено](#как-это-устроено)
2. [Промпты шлюза](#промпты-шлюза)
3. [Запуск у себя](#запуск-у-себя)
4. [Навык в Яндекс Диалогах](#навык-в-яндекс-диалогах)
5. [Куда смотреть в коде](#куда-смотреть-в-коде)
6. [Другой провайдер](#другой-провайдер)
7. [Деплой в Timeweb Cloud](#деплой-в-timeweb-cloud)
8. [Промпт для агента: поднять весь контур в Timeweb](#промпт-для-агента-поднять-весь-контур-в-timeweb)

## Как это устроено

```text
Яндекс Диалоги  --POST /alice-->  этот сервис (FastAPI)  -->  языковая модель
                  webhook навыка      ответ текстом          (OpenAI-совместимый API
                                                             или свой адаптер)
```

1. Диалоги шлют на `POST /alice` JSON запроса навыка.
2. Шлюз разбирает реплику, при необходимости держит короткий диалог в памяти процесса и вызывает модель.
3. Ответ укладывается в формат Диалогов. Если модель не успела за бюджет времени — «Думаю…», ответ дочитывается, пользователь говорит «дальше».
4. `GET /health` нужен хостингу: платформа видит, что процесс жив.

Характер помощника задаётся его system prompt (у провайдера) и промптом шлюза из файла (см. ниже). Температуру и лимит длины шлюз в запрос по умолчанию не кладёт — это настройки модели на стороне провайдера.

## Промпты шлюза

Тексты system prompt лежат в каталоге [`prompts/`](prompts/) в формате Markdown (`.md`). Их можно менять без правки Python-кода.

- По умолчанию используется [`prompts/alice_system.md`](prompts/alice_system.md).
- В окружении задаётся только путь: `SYSTEM_PROMPT_PATH=prompts/alice_system.md` (см. `example.env`).
- Относительный путь считается от рабочей директории процесса (в контейнере обычно корень приложения; каталог `prompts/` копируется в образ).
- После смены файла перезапустите процесс или пересоберите и выкатите образ, если промпт зашит в деплой.

Промпт самой модели у провайдера LLM — отдельный; файл из `prompts/` его не заменяет, а дополняет на каждый запрос.

## Запуск у себя

Нужны [uv](https://docs.astral.sh/uv/) и Python 3.13.

```bash
uv python pin 3.13
uv sync
cp example.env .env
```

В `.env` укажите ключ и адрес API помощника (см. `example.env`) и запустите:

```bash
uv run alice-gateway
```

Проверка:

```bash
curl -s http://127.0.0.1:8080/health
curl -s http://127.0.0.1:8080/alice \
  -H 'content-type: application/json' \
  -d '{"version":"1.0","session":{"session_id":"local","new":true,"message_id":0,"skill_id":"dev"},"request":{"type":"SimpleUtterance","command":"","original_utterance":""}}'
```

Пустые ключ и адрес не мешают запуску: сервис ответит, что помощник не настроен.

Тесты: `uv run pytest`.

`ALICE_REPLY_BUDGET_SECONDS` лучше не опускать ниже 3. В лимит 4,5 секунды входит ещё дорога до Диалогов и обратно.

## Навык в Яндекс Диалогах

1. Откройте [консоль разработчика](https://dialogs.yandex.ru/developer) и создайте навык.
2. В настройках, блок Backend, вставьте Webhook URL: `https://<ваш-публичный-хост>/alice`.
3. Сохраните и проверьте на вкладке «Тестирование».

Формат обмена: [запрос](https://yandex.ru/dev/dialogs/alice/doc/ru/request), [ответ](https://yandex.ru/dev/dialogs/alice/doc/ru/response), [долгий ответ](https://yandex.ru/dev/dialogs/alice/doc/ru/wait-response). Если Алиса говорит, что навык не отвечает, помощник не уложился в 4,5 секунды. Скажите «дальше».

## Куда смотреть в коде

- `POST /alice` — webhook Диалогов.
- `GET /health` — проверка живости.
- Вопрос обрабатывает команда `ReplyToUtterance` через `python-cqrs`.
- К модели ходит порт `LanguageModel`. Пока ключ и адрес пустые, отвечает заглушка.
- System prompt шлюза: файлы в `prompts/`, путь в `SYSTEM_PROMPT_PATH`.
- Корневой `Dockerfile` собирает контейнер на порту `8080` (нужен `curl` для health-проб на многих платформах). Свою инструкцию `HEALTHCHECK` в Dockerfile лучше не ставить, если хостинг сам дергает `/health`.

## Другой провайдер

Навык Алисы не меняется. Меняется только кусок, который ходит в языковую модель.

Если у провайдера обычный адрес в стиле OpenAI (`/v1/chat/completions`), отдельный код часто не нужен: в переменные кладут его ключ, корень API (без хвоста `/chat/completions`) и имя модели. Имя модели в запросе читают прямые API; у части «агентских» endpoint’ов модель уже выбрана в панели и поле в запросе игнорируется.

Если API другое, в инфраструктуре заводят свой адаптер.

1. Порт уже есть: `LanguageModel` в `src/alice_gateway/service/ports/language_model.py`. Метод `complete` принимает список сообщений и возвращает текст.
2. Рядом с текущим адаптером в `src/alice_gateway/infrastructure/adapters/language_model.py` добавьте класс и унаследуйте `LanguageModel`. В `complete` вызовите API и верните текст. Ошибку сети оберните в `LanguageModelError`.
3. Подключите класс в `build_language_model` в `src/alice_gateway/presentation/wiring/container.py`.
4. Ключ и адрес читайте из `src/alice_gateway/shared/settings.py`. В репозиторий их не кладите.

Вебхук `/alice`, обработчик диалога и лимит 4,5 секунды трогать не надо: они говорят с портом, а не с конкретным провайдером.

Промпт для модели (добавить адаптер):

```text
This repo is an Alice skill webhook. It calls a language model through the
LanguageModel port in src/alice_gateway/service/ports/language_model.py.
complete() takes a list of chat messages and returns assistant text.

There is already an OpenAI-compatible adapter in
src/alice_gateway/infrastructure/adapters/language_model.py.
build_language_model in src/alice_gateway/presentation/wiring/container.py
picks the adapter. Settings live in src/alice_gateway/shared/settings.py.
System prompt text is loaded from a Markdown file under prompts/
(path from SYSTEM_PROMPT_PATH).

Add an adapter for the direct <provider, for example OpenAI> API.
Subclass LanguageModel, put the class next to the existing adapter,
wire it in build_language_model, and add environment variables for the API key,
base URL, and model name. Do not log the key.
Do not change the /alice webhook, the ReplyToUtterance handler, or the Alice
response shape. Cover the adapter with an HTTP mock test, the same way the
existing adapter is already tested.
```

## Деплой в Timeweb Cloud

Дальше — конкретная схема на Timeweb: AI-агент как модель, backend в Timeweb Apps из Dockerfile этого репозитория, домен. В `.agents/skills/` лежат скилы (`$timeweb-ai`, `$timeweb-apps`, `$timeweb-domains`): ими агент в Cursor/Codex поднимает контур. Перед платным шагом он показывает цену и ждёт подтверждения. Ключ аккаунта Timeweb хранится только локально и в git не коммитится.

```text
Яндекс Диалоги  --POST /alice-->  FastAPI в Timeweb Apps  -->  AI-агент Timeweb
                                   (этот репозиторий)         (модель + промпт)
```

### AI-агент

В [панели Timeweb](https://timeweb.cloud) создайте AI-агента и выберите быструю модель (удобно для голоса, у нас DeepSeek Flash): короткий ответ, без лишнего thinking — Диалоги рвут навык через 4,5 секунды. Новый агент — pay-as-you-go. Характер задаётся промптом в панели.

Из карточки агента, раздел API:

- **access id** из адреса API;
- **ключ доступа**. Его показывают один раз. Это не ключ всего аккаунта и не ключ AI Gateway (`https://api.timeweb.ai/v1` — другой продукт).

```env
TIMEWEB_API_KEY=<ключ доступа агента>
TIMEWEB_BASE_URL=https://agent.timeweb.cloud/api/v1/cloud-ai/agents/<access-id>/v1
TIMEWEB_MODEL=deepseek-v4-flash
```

`TIMEWEB_BASE_URL` — без хвоста `/chat/completions`. Имя в `TIMEWEB_MODEL` агент Timeweb не читает: отвечает модель из панели. Поле нужно, когда тот же шлюз смотрит в обычный OpenAI-совместимый API.

Промпт шлюза — файл из `prompts/` (`SYSTEM_PROMPT_PATH`); промпт агента в панели он не заменяет. После правки `.md` нужна новая сборка Apps: каталог `prompts/` копируется в образ.

Смена агента: новый access id и ключ в тех же двух переменных, перезапуск. Документация: [OpenAI-совместимый API агентов](https://timeweb.cloud/docs/ai-agents/api-usage/openai-compatible-api).

### Backend в Timeweb Apps

Это HTTP API шлюза, не сайт. Собирается из Dockerfile. То же через скил `$timeweb-apps`.

1. Apps → создать → backend, репозиторий и ветка с этим Dockerfile.
2. Язык **Docker**, пустые build/run, порт из `EXPOSE 8080`.
3. Health check: `GET /health` → `{"status":"ok"}`. В образе есть `curl`.
4. Переменные: `TIMEWEB_API_KEY`, `TIMEWEB_BASE_URL`, по желанию `SYSTEM_PROMPT_PATH`, `TIMEWEB_MODEL`, `ALICE_REPLY_BUDGET_SECONDS`. Каталог `prompts/` входит в образ.
5. Плата — тариф в месяц плюс публичный IP. Удалить приложение через API нельзя.
6. Домен: купить в панели руками, привязать к Apps (скилы или карточка). Сертификат выпускает Timeweb. Пока зона не опубликована — технический домен Apps: `https://<технический-домен>/alice`.

### Навык

В Диалогах Webhook URL: `https://<ваш-домен>/alice` (или технический домен Apps, пока DNS не готов).

Готовый текст для копирования в агента — ниже.

## Промпт для агента: поднять весь контур в Timeweb

Ниже готовый текст **на английском** — его копируют в Cursor/Codex и т.п. Агент должен сначала прочитать скилы `$timeweb-ai`, `$timeweb-apps`, `$timeweb-domains`, следовать `AGENTS.md`, перед платным шагом назвать цену и ждать подтверждения, секреты в git не коммитить.

```text
Goal: deploy the Yandex Alice webhook gateway from this repository on Timeweb Cloud.

Architecture (do not change the code for this task):
  Yandex Dialogs --POST /alice--> FastAPI backend in Timeweb Apps (this repo, Dockerfile)
                                 --> Timeweb Cloud AI Agent (OpenAI-compatible API)

Repository facts:
  - Root Dockerfile, EXPOSE 8080, CMD runs `alice-gateway` (FastAPI + python-cqrs).
  - Endpoints: GET /health -> {"status":"ok"}; POST /alice -> Alice Dialogs JSON.
  - Image must include curl (Timeweb health probe uses it). Do not add Dockerfile HEALTHCHECK.
  - Env vars (see example.env): TIMEWEB_API_KEY, TIMEWEB_BASE_URL (agent root, NO /chat/completions),
    TIMEWEB_MODEL, SYSTEM_PROMPT_PATH=prompts/alice_system.md, ALICE_REPLY_BUDGET_SECONDS=3,
    HOST=0.0.0.0, PORT=8080. Dockerfile must COPY the prompts/ directory.
  - Gateway picks TimewebLanguageModel only when BOTH TIMEWEB_API_KEY and TIMEWEB_BASE_URL are set;
    otherwise users hear a stub message that the model is not configured.

Prerequisites:
  - Timeweb Cloud MCP token configured locally for the agent (not in git; see timeweb skill docs).
  - This git repository URL and branch the user wants to deploy (e.g. master).
  - For domain registration: user account in Timeweb panel; agent may use $timeweb-domains to check
    availability and explain DNS, but purchase is often panel-only.

Use Timeweb MCP via skills ($timeweb-ai, $timeweb-apps, $timeweb-domains, $timeweb-billing for costs). Steps:

1) Project
   - Put resources in the user's chosen Timeweb Cloud project (project_id from list_projects).

2) AI Agent ($timeweb-ai)
   - Create a private AI agent with a fast LLM suitable for voice (e.g. DeepSeek V4 Flash).
   - Pay-as-you-go agent (no token package at creation unless user explicitly asks).
   - Agent system prompt: short Russian voice assistant for Alice; no markdown; max ~4 sentences.
   - Model settings: moderate max_tokens (e.g. 512), enable_thinking false if the model supports it.
   - Save the agent access_id from the OpenAI-compatible URL:
     https://agent.timeweb.cloud/api/v1/cloud-ai/agents/<access-id>/v1
   - Tell the user: the agent API access key (JWT) is shown ONCE in the agent card (API section).
     It is NOT the access_id. User must copy it; you must not log or commit it.
   - Optionally verify the key with one chat/completions call before Apps deploy.

3) Timeweb Apps backend ($timeweb-apps)
   - Create a backend app from this Git repo: language docker, framework docker, empty build_cmd and run_cmd.
   - Use the latest commit SHA on the deploy branch (full 40 chars from list_vcs_commits).
   - Connect GitHub VCS provider if not already connected (add_vcs_provider with user token).
   - Pick an available backend preset; warn: monthly preset price plus public IP billed separately.
   - health_check path: /health
   - Set envs at create time (values for secrets: ask user or use panel after create):
     TIMEWEB_BASE_URL=https://agent.timeweb.cloud/api/v1/cloud-ai/agents/<access-id>/v1
     TIMEWEB_MODEL=deepseek-v4-flash (or matching model slug)
     SYSTEM_PROMPT_PATH=prompts/alice_system.md
     ALICE_REPLY_BUDGET_SECONDS=3
     HOST=0.0.0.0
     PORT=8080
   - After the user provides the agent API key, set TIMEWEB_API_KEY on the app (panel or API PATCH
     on the app with envs map including all existing vars). Redeploy/restart if needed.
   - Wait until deploy status is success and app status is active.
   - Smoke test: GET https://<technical-apps-domain>/health and POST /alice with a new session JSON.

4) Domain
   - Domain registration/purchase is MANUAL in Timeweb panel ($timeweb-domains docs only; do not
     assume MCP registers a TLD unless the skill exposes it).
   - Attach the user's domain to the Apps backend (PATCH app domains list: technical domain + custom
     fqdn). Platform creates A record to the app IP and issues Let's Encrypt.
   - Tell the user: until the TLD zone is published in DNS, the custom domain may not resolve;
     use the technical Apps domain for testing meanwhile.
   - Alice skill Webhook URL (user configures in Yandex Dialogs console, not Timeweb):
     https://<custom-domain>/alice  (or technical Apps domain until DNS is live)

5) Yandex Dialogs (outside Timeweb; user or agent guides, no MCP)
   - Create or open the Alice skill in Yandex Dialogs developer console.
   - Backend type: webhook; URL = https://<public-host>/alice (HTTPS required).
   - Publish/test the skill; utterances hit POST /alice with Alice session JSON.

6) Verification checklist (report each result)
   - /health returns 200 and {"status":"ok"}
   - POST /alice on new session returns welcome text
   - POST /alice with a question returns model text (not the stub) once TIMEWEB_API_KEY is set
   - If model is slow (> ALICE_REPLY_BUDGET_SECONDS), gateway returns "think / say dalshe" then
     answer on continue — expected for Alice 4.5s limit
   - Do not paste secrets in chat logs; remind user to rotate key if it was exposed

7) Swapping the LLM later
   - New Timeweb agent or OpenAI-compatible provider: change TIMEWEB_BASE_URL + TIMEWEB_API_KEY only,
     or add a new LanguageModel adapter per README "Another provider" section.
```
