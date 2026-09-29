# Project instructions

Один набор скилов для любого агента: Cursor, Codex и остальные. Тексты правил остаются в `.cursor/rules/*.mdc`. Свой MCP и хуки репозиторий не везёт.

Если указания расходятся, этот файл и `.mdc` важнее скила.

## Где что лежит

| Что | Путь | Заметка |
|-----|------|---------|
| Скилы | `.agents/skills/{name}/SKILL.md` | Общие. У каждого есть `agents/openai.yaml`. |
| Правила | `.cursor/rules/*.mdc` | Полный текст. Cursor подставляет сам. Остальные агенты **читают** файлы из списка ниже. |
| Graphify | `.cursor/rules/graphify.mdc` и `.agents/skills/graphify/` | Команда берётся из имени скила `graphify`. |

Не заводите второе дерево скилов в `.cursor/skills/`. Не создавайте `.agents/rules/` и `.agents/commands/`.

## Всегда прочитать

Перед разбором репозитория, планом или правками прочитайте целиком:

- `.cursor/rules/graphify.mdc`

Если есть `graphify-out/graph.json`, следуйте правилам graphify из этого файла.

## Cursor

- Правила подставляются из `.cursor/rules/*.mdc`. Не копируйте их в `.agents/rules/`.
- Скилы только в `.agents/skills/`. Не дублируйте их в каталог скилов Cursor.

## Другие агенты

- Этот `AGENTS.md` читается сам.
- Скилы Timeweb и graphify берутся из `.agents/skills/`.
- Файлы `.mdc` сами не подставляются. Прочитайте список «Всегда прочитать».

## Скилы

| Скил | Когда |
|------|--------|
| `$timeweb-ai` | Агенты, модели, токены, базы знаний |
| `$timeweb-apps` | Приложения Apps и реестр образов |
| `$timeweb-domains` | Домены, DNS, почта. Не домены самого Apps |
| `$timeweb-account` | Аккаунт и доступ |
| `$timeweb-billing` | Баланс и платежи |
| `$timeweb-servers` | Облачные серверы |
| `$timeweb-network` | Сети, IP, VPC |
| `$timeweb-databases` | Базы данных |
| `$timeweb-s3` | Хранилище S3 |
| `$timeweb-kubernetes` | Kubernetes |
| `$graphify` | Граф кода в `graphify-out/` |

Когда скил вызван, прочитайте его `SKILL.md` целиком и следуйте ему. Дополнительные файлы лежат рядом, в `references/`.
