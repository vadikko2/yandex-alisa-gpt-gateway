# Шлюз Алисы к своему помощнику

Алиса открывает навык и задаёт ему вопрос. Этот сервис отвечает текстом вашего помощника из Timeweb Cloud.

Помощник в коде не зашит. Адрес и ключ лежат в настройках: другая модель ставится двумя строками и перезапуском, без правки программы.

| | |
|---|---|
| Сколько ждёт Алиса | **4,5 секунды** вместе с дорогой до сервера и обратно |
| Если не успели | «Думаю. Скажите „дальше“». Ответ дочитывается в фоне |
| Закончить | «хватит», «выход», «стоп», «пока», «до свидания» или кнопка «Закончить» |
| Длина ответа | не больше **1024** символов, лишнее обрезается |
| Память диалога | только в этом запущенном экземпляре, после деплоя пропадает |

Протокол навыка: [Яндекс Диалоги](https://yandex.ru/dev/dialogs/alice/doc/ru/).

## Настроить с агентом

В `.agents/skills/` лежат скилы Timeweb. Ими любой агент в Cursor, Codex и т.п. поднимает контур:

1. AI-агент в Timeweb Cloud (`$timeweb-ai`)
2. backend-приложение в Timeweb Apps из Dockerfile этого репозитория (`$timeweb-apps`)
3. привязку домена к Apps

Перед платным шагом агент показывает цену и ждёт подтверждения. Ключ доступа к аккаунту Timeweb хранится только локально и в репозиторий не коммитится.

Как это устроено по факту:

```text
Яндекс Диалоги  --POST /alice-->  FastAPI в Timeweb Apps  -->  AI-агент Timeweb
                                   (этот репозиторий)         (модель + промпт)
```

1. **AI-агент.** Через `$timeweb-ai` создаётся агент с быстрой моделью (у нас DeepSeek Flash): короткий ответ, без лишнего thinking, потому что Диалоги рвут навык через 4,5 секунды. Новый агент — pay-as-you-go, пакет токенов при создании не покупается. Access id идёт в `TIMEWEB_BASE_URL`. Ключ доступа API показывает один раз в карточке агента — его нужно сохранить и потом положить в `TIMEWEB_API_KEY` у Apps.
2. **Apps (API, не сайт).** Через `$timeweb-apps` поднимается отдельный backend из Dockerfile: язык Docker, пустые build/run, порт `8080`, health check `GET /health`. Это HTTP API шлюза: `POST /alice` принимает webhook Диалогов, `GET /health` — проверка живости. При создании задаются `TIMEWEB_BASE_URL`, `TIMEWEB_MODEL`, `SYSTEM_PROMPT`. Ключ агента (`TIMEWEB_API_KEY`) дописывается в переменные приложения после того, как его скопировали из карточки агента.
3. **Домен.** Купить домен нужно руками в [панели Timeweb](https://timeweb.cloud). Привязать купленный домен к Apps можно через скилы: платформа сама ставит A-запись на IP приложения и выпускает сертификат. В Яндекс Диалогах Webhook URL: `https://<ваш-домен>/alice`. Пока зона в реестре не опубликована, домен снаружи не откроется — до этого можно временно указать технический домен Apps.

Сменить AI-агента: новый access id и ключ в тех же двух переменных Apps, код шлюза не меняется.

### Промпт для агента: поднять весь контур в Timeweb

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
    TIMEWEB_MODEL, SYSTEM_PROMPT, ALICE_REPLY_BUDGET_SECONDS=3, HOST=0.0.0.0, PORT=8080.
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
     SYSTEM_PROMPT=<short Russian Alice gateway prompt from example.env>
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

## Запуск у себя

Нужны [uv](https://docs.astral.sh/uv/) и Python 3.13.

```bash
uv python pin 3.13
uv sync
cp example.env .env
```

В `.env` впишите помощника, как в следующем разделе, и запустите:

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

## Какого помощника звать

В [панели Timeweb](https://timeweb.cloud) создайте AI-агента и выберите модель. Характер задаётся промптом в панели и переживает обновление кода. Деньги списываются с баланса по мере запросов.

Из карточки агента, раздел API, нужны две вещи:

- **access id** из адреса API;
- **ключ доступа**. Его показывают один раз. Потеряли — выпустите новый там же. Это не ключ всего аккаунта и не ключ AI Gateway: `https://api.timeweb.ai/v1` это другой продукт.

```env
TIMEWEB_API_KEY=<ключ доступа агента>
TIMEWEB_BASE_URL=https://agent.timeweb.cloud/api/v1/cloud-ai/agents/<access-id>/v1
TIMEWEB_MODEL=deepseek-v4-flash
```

`TIMEWEB_BASE_URL` пишется без хвоста `/chat/completions`. Имя в `TIMEWEB_MODEL` агент Timeweb не читает: отвечает модель, выбранная в панели. Поле нужно, когда тот же шлюз смотрит в обычный адрес в стиле OpenAI и модель выбирают запросом.

`SYSTEM_PROMPT` шлюз добавляет к каждому вопросу: короткий разговорный ответ без разметки. Промпт агента в панели он не заменяет.

Температуру и лимит длины шлюз в запрос не кладёт. У части моделей GPT-5 такие поля ломают вызов, у остальных это настраивается в панели. Поэтому смена агента не требует правки кода.

Как устроен вызов: [OpenAI-совместимый API агентов](https://timeweb.cloud/docs/ai-agents/api-usage/openai-compatible-api).

Другой агент Timeweb ставится так: его access id в `TIMEWEB_BASE_URL`, его ключ в `TIMEWEB_API_KEY`, сохранить и перезапустить.

## Backend в Timeweb Apps

Это HTTP API шлюза, не фронтенд. Собирается из Dockerfile в корне репозитория. То же самое делает скил `$timeweb-apps`.

1. Apps → создать → backend.
2. Подключите репозиторий и ветку с этим Dockerfile.
3. Язык **Docker**. Команды сборки и запуска оставьте пустыми: процесс задаёт Dockerfile, порт берётся из `EXPOSE 8080`.
4. Сервис слушает `0.0.0.0:8080`. Снаружи Timeweb отдаёт его по HTTPS.
5. Проверка живости: `GET /health`, ответ `{"status":"ok"}`. Свою инструкцию `HEALTHCHECK` в Dockerfile не ставьте: она перебьёт проверку панели. В образе есть `curl`, без него проверка внутри контейнера не проходит.
6. Переменные: `TIMEWEB_API_KEY`, `TIMEWEB_BASE_URL`, по желанию `SYSTEM_PROMPT`, `TIMEWEB_MODEL`, `ALICE_REPLY_BUDGET_SECONDS`. Их можно задать при создании, позже их меняют в панели. Обратно из API значения не читаются.
7. Плата — тариф в месяц плюс отдельный публичный IP. Удалить приложение через API нельзя: пока оно в панели, за него начисляют. Пауза не обещает, что начисления остановятся.
8. Домен: купить в панели руками, привязать к Apps через скилы или в карточке приложения. Сертификат выпускает Timeweb, свой поставить нельзя. Пока зона не опубликована, временно используйте технический домен Apps: `https://<технический-домен>/alice`.

`ALICE_REPLY_BUDGET_SECONDS` лучше не опускать ниже 3. В лимит 4,5 секунды входит ещё дорога до Диалогов и обратно.

## Навык в Яндекс Диалогах

1. Откройте [консоль разработчика](https://dialogs.yandex.ru/developer) и создайте навык.
2. В настройках, блок Backend, вставьте Webhook URL: `https://<домен>/alice`.
3. Сохраните и проверьте на вкладке «Тестирование».

Формат обмена: [запрос](https://yandex.ru/dev/dialogs/alice/doc/ru/request), [ответ](https://yandex.ru/dev/dialogs/alice/doc/ru/response), [долгий ответ](https://yandex.ru/dev/dialogs/alice/doc/ru/wait-response). Если Алиса говорит, что навык не отвечает, помощник не уложился в 4,5 секунды. Скажите «дальше».

## Куда смотреть в коде

- `POST /alice` принимает сообщения Диалогов.
- `GET /health` нужен, чтобы платформа видела живое приложение.
- Вопрос обрабатывает команда `ReplyToUtterance` через `python-cqrs`.
- К помощнику ходит `TimewebLanguageModel`. Пока ключ и адрес пустые, вместо него отвечает заглушка.

## Другой провайдер вместо Timeweb

Навык Алисы при этом не меняется. Меняется только тот кусок, который ходит в языковую модель.

Если у провайдера обычный адрес в стиле OpenAI (`/v1/chat/completions`), отдельный код не нужен. В `TIMEWEB_BASE_URL` поставьте его адрес, в `TIMEWEB_MODEL` имя модели, в `TIMEWEB_API_KEY` его ключ. У агента Timeweb имя модели из запроса не читается. У прямого API OpenAI и похожих сервисов читается, поэтому модель выбирает `TIMEWEB_MODEL`.

Если API другое, в инфраструктуре заводят свой адаптер.

1. Порт уже есть: `LanguageModel` в `src/alice_gateway/service/ports/language_model.py`. Метод `complete` принимает список сообщений и возвращает текст.
2. Рядом с `TimewebLanguageModel` в `src/alice_gateway/infrastructure/adapters/language_model.py` добавьте класс и унаследуйте `LanguageModel`. В `complete` вызовите API и верните текст. Ошибку сети оберните в `LanguageModelError`.
3. Подключите класс в `build_language_model` в `src/alice_gateway/presentation/wiring/container.py`. Сейчас там выбор: есть ключ и адрес Timeweb — берётся `TimewebLanguageModel`, иначе заглушка.
4. Ключ и адрес читайте из `src/alice_gateway/shared/settings.py`, как `TIMEWEB_API_KEY` и `TIMEWEB_BASE_URL`. В репозиторий их не кладите.

Вебхук `/alice`, обработчик диалога и лимит 4,5 секунды трогать не надо: они говорят с портом, а не с Timeweb.

Промпт для модели:

```text
This repo is an Alice skill webhook. It calls a language model through the
LanguageModel port in src/alice_gateway/service/ports/language_model.py.
complete() takes a list of chat messages and returns assistant text.

The current adapter is TimewebLanguageModel in
src/alice_gateway/infrastructure/adapters/language_model.py.
build_language_model in src/alice_gateway/presentation/wiring/container.py
picks the adapter. Settings live in src/alice_gateway/shared/settings.py.

Add an adapter for the direct <provider, for example OpenAI> API.
Subclass LanguageModel, put the class next to TimewebLanguageModel,
wire it in build_language_model, and add environment variables for the API key,
base URL, and model name. Do not log the key.
Do not change the /alice webhook, the ReplyToUtterance handler, or the Alice
response shape. Cover the adapter with an HTTP mock test, the same way the
Timeweb adapter is already tested.
```
