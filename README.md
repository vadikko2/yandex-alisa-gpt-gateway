# Yandex Alice GPT gateway

Вебхук навыка [Яндекс Диалогов](https://yandex.ru/dev/dialogs/alice/doc/ru/). Реплика пользователя уходит в OpenAI-совместимый API AI-агента Timeweb Cloud, ответ возвращается Алисе.

Агент не зашит в код. Его адрес и ключ — две переменные окружения, как в [ai-fitness-tgbot](https://github.com/vadikko2/ai-fitness-tgbot): чтобы поставить другую модель, меняете агента в панели и эти две переменные.

Диалоги отдают навыку **4,5 секунды** на весь круг (сеть туда, работа навыка, сеть обратно). Если модель не успела, шлюз сразу отвечает «Думаю. Скажите «дальше»» и дочитывает ответ в фоне этого же процесса. Следующая реплика «дальше» (или кнопка) отдаёт готовый текст. История диалога живёт в памяти одного контейнера Apps и пропадает после нового деплоя.

## Локально

Нужны [uv](https://docs.astral.sh/uv/) и Python 3.13.

```bash
uv python pin 3.13
uv sync
cp example.env .env
```

В `.env` укажите агента (см. ниже) и запустите:

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

Пустые `TIMEWEB_API_KEY` и `TIMEWEB_BASE_URL` оставляют заглушку: сервис поднимается, на вопрос отвечает, что модель не настроена.

Тесты: `uv run pytest`.

## Агент в Timeweb Cloud

1. Откройте [панель](https://timeweb.cloud) и проект, в котором должен жить агент.
2. AI-агенты → создать агента. Для этого репозитория в проекте [Yandex Alisa GPT](https://timeweb.cloud/my/projects/2979147) стоит **DeepSeek V4 Flash** (pay-as-you-go, токены списываются с баланса). Системный промпт агента задаётся в панели и переживает смену кода.
3. В карточке агента откройте API и скопируйте:
   - **access id** из OpenAI-совместимого URL;
   - **ключ доступа**. Его показывают один раз. Потеряли — выпустите новый в панели. Это не API-ключ аккаунта и не ключ AI Gateway.
4. Запишите в окружение приложения:

```env
TIMEWEB_API_KEY=<ключ доступа агента>
TIMEWEB_BASE_URL=https://agent.timeweb.cloud/api/v1/cloud-ai/agents/<access-id>/v1
TIMEWEB_MODEL=deepseek-v4-flash
```

`TIMEWEB_BASE_URL` — корень без `/chat/completions`. Поле `model` агент игнорирует: отвечает та модель, которая выбрана у агента. `TIMEWEB_MODEL` нужен только если тот же шлюз смотрит в обычный OpenAI-совместимый endpoint, где имя модели читают.

Промпт в `SYSTEM_PROMPT` шлюз добавляет к каждому запросу (короткий разговорный ответ без markdown). Промпт самого агента его не заменяет.

Документация вызова: [OpenAI-совместимый API агентов](https://timeweb.cloud/docs/ai-agents/api-usage/openai-compatible-api).

### Поменять агента

1. Создайте или выберите другого агента (другая модель, другой промпт, база знаний).
2. Подставьте его access id в `TIMEWEB_BASE_URL` и его ключ в `TIMEWEB_API_KEY`.
3. В Timeweb Apps сохраните переменные в панели и перезапустите приложение. Код и образ те же.

Температуру и лимит токенов шлюз не шлёт: у GPT-5 они ломают запрос, а у остальных агентов эти настройки живут в панели. Поэтому смена агента не требует правки репозитория.

## Приложение в Timeweb Apps

Отдельное приложение, сборка из Dockerfile в корне репозитория.

1. Apps → создать → backend.
2. Провайдер GitHub `vadikko2`, репозиторий `yandex-alisa-gpt-gateway`, ветка `master`.
3. Язык **Docker**. Команды сборки и запуска пустые: процесс задаёт `CMD` в Dockerfile, порт берётся из `EXPOSE 8080`.
4. Приложение слушает `0.0.0.0:8080`. Снаружи платформа отдаёт его по HTTPS.
5. Health check: `GET /health`, ответ `{"status":"ok"}`. В Dockerfile нет инструкции `HEALTHCHECK`, чтобы не перебить проверку панели.
6. Переменные: `TIMEWEB_API_KEY`, `TIMEWEB_BASE_URL`, при желании `SYSTEM_PROMPT`, `TIMEWEB_MODEL`, `ALICE_REPLY_BUDGET_SECONDS`. Их задают при создании или потом в панели. Значения в API маскируются.
7. Тариф backend — цена пресета в месяц плюс отдельный публичный IP. Приложение нельзя удалить через API: пока оно не удалено в панели, оно тарифицируется. Пауза не обещает остановку списаний.

Текущий выклад в проекте [Yandex Alisa GPT](https://timeweb.cloud/my/projects/2979147):

- Агент **Alice DeepSeek**, модель DeepSeek V4 Flash, pay-as-you-go (пакет токенов при создании не покупался). Access id: `ce9cf23b-3843-47d8-bcf4-7dcecfc00bb0`. Thinking выключен, `max_tokens` 512.
- Приложение **Yandex Alice Gateway** (id 261951), Docker, пресет backend 1 vCPU / 1 ГБ / ru-1 — 510 ₽ в месяц плюс публичный IP. Health check: `/health`.
- Webhook: `https://vadikko2-yandex-alisa-gpt-gateway-2b7f.twc1.net/alice`

`TIMEWEB_BASE_URL` в приложении уже указывает на этого агента. Ключ доступа агента API не отдаёт: его показывают в карточке агента, раздел API. Пока переменной `TIMEWEB_API_KEY` нет, шлюз отвечает заглушкой. Вставьте ключ в переменные приложения в панели и перезапустите.

## Навык Алисы

1. [Консоль разработчика Диалогов](https://dialogs.yandex.ru/developer) → создать навык.
2. Настройки → Backend → Webhook URL: `https://<домен-приложения>/alice`. Нужен HTTPS с полной цепочкой сертификата. У Apps это бесплатный сертификат платформы, свой ставить нельзя.
3. Сохранить и проверить на вкладке «Тестирование».
4. Формат запроса и ответа — [запрос](https://yandex.ru/dev/dialogs/alice/doc/ru/request) и [ответ](https://yandex.ru/dev/dialogs/alice/doc/ru/response). Текст ответа не длиннее 1024 символов, шлюз обрезает более длинный.
5. Если Алиса говорит, что навык не отвечает, модель не уложилась в [4,5 секунды](https://yandex.ru/dev/dialogs/alice/doc/ru/wait-response). Уменьшать `ALICE_REPLY_BUDGET_SECONDS` ниже 3 не стоит: в лимит входят ещё сеть до Диалогов и обратно. Пользователь говорит «дальше» или жмёт кнопку.

Фразы «хватит», «выход», «стоп», «пока», «до свидания» и кнопка «Закончить» завершают сессию.

## Что где лежит

- `POST /alice` — вебхук Диалогов.
- `GET /health` — проверка для Apps.
- Команда `ReplyToUtterance` идёт через `python-cqrs` (`RequestMediator`).
- Порт `LanguageModel` реализует `TimewebLanguageModel`. Пустые ключ и URL подменяют его заглушкой.
