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

Подсказки для Timeweb лежат в `.agents/skills/`. Их читает любой агент. Можно попросить чат завести помощника и поднять сайт из этого репозитория. Перед платным шагом он называет цену и ждёт подтверждения.

Ключ доступа к аккаунту Timeweb хранится только на компьютере и в репозиторий не попадает.

1. **Помощник.** Быстрый DeepSeek, короткий ответ: Алиса не любит ждать. Платите за сами ответы, пакет токенов при создании не нужен. Ключ Timeweb показывает один раз в карточке. Сохраните его сразу.
2. **Сайт.** Отдельное приложение из этого репозитория. Оно принимает вопросы Алисы и отдаёт их помощнику. Адрес помощника задаётся при запуске. Ключ удобнее вписать потом в панели: чат не меняет настройки уже созданного приложения.
3. **Домен.** К приложению его привязывают в карточке в панели. Timeweb сам направляет домен на сайт и выпускает сертификат. В Диалогах адрес навыка: `https://<ваш-домен>/alice`. Пока домен только куплен и в интернете не открывается, этот адрес указывать рано.

Сменить помощника можно тем же чатом: новый адрес и новый ключ. Код тот же.

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

## Сайт на Timeweb Apps

Приложение собирается из Dockerfile в корне репозитория.

1. Apps → создать → backend.
2. Подключите репозиторий и ветку с этим Dockerfile.
3. Язык **Docker**. Команды сборки и запуска оставьте пустыми: процесс задаёт Dockerfile, порт берётся из `EXPOSE 8080`.
4. Сервис слушает `0.0.0.0:8080`. Снаружи Timeweb отдаёт его по HTTPS.
5. Проверка живости: `GET /health`, ответ `{"status":"ok"}`. Свою инструкцию `HEALTHCHECK` в Dockerfile не ставьте: она перебьёт проверку панели. В образе есть `curl`, без него проверка внутри контейнера не проходит.
6. Переменные: `TIMEWEB_API_KEY`, `TIMEWEB_BASE_URL`, по желанию `SYSTEM_PROMPT`, `TIMEWEB_MODEL`, `ALICE_REPLY_BUDGET_SECONDS`. Их можно задать при создании, позже их меняют в панели. Обратно из API значения не читаются.
7. Плата — тариф в месяц плюс отдельный публичный адрес. Удалить приложение через API нельзя: пока оно в панели, за него начисляют. Пауза не обещает, что начисления остановятся.
8. Свой домен указывается в карточке приложения. Сертификат выпускает Timeweb, свой поставить нельзя. Пока домен в интернете не открывается, навык можно временно направить на технический адрес: `https://<технический-домен>/alice`.

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
