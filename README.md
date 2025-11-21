# sandbox_adk_persistent_maze

Лабиринт 5x5 с персистентным состоянием в Firestore. Два режима работы: консольный CLI и веб-интерфейс через ADK.

## Возможности
- Движение по сетке 5x5, стены: (1,1), (1,2), (3,3), (2,0), цель: (4,4) с монетой.
- Команды: `go n/s/e/w`, `look`/`where`, `history`, `whoami`, `quit`.
- Сарказм после 3 подряд BLOCKED/OOB, триумф при взятии монеты.
- Персистентность: позиция/инвентарь/статистика в Firestore (по username).
- Логи в stdout: `[TIMESTAMP] [CATEGORY] Message`.

## Требования
- Python 3.10+
- Доступ к Firestore (service account JSON).
- Для ADK/Gemini: `GOOGLE_API_KEY` (или Vertex AI project/location).

## Установка
1. Скопируйте `.env.template` в `.env` и заполните:
   - `GOOGLE_APPLICATION_CREDENTIALS` — путь к service-account JSON.
   - `FIRESTORE_PROJECT_ID` — ваш GCP проект.
   - `MAZE_COLLECTION_NAME` — коллекция для пользователей (по умолчанию `maze_users`).
   - `LOG_LEVEL` — опционально (`INFO` по умолчанию).
   - `GOOGLE_API_KEY` — для LLM (или `VERTEXAI_PROJECT`/`VERTEXAI_LOCATION`).
2. Установите зависимости: `pip install -r requirements.txt`.

## Запуск: CLI
```bash
python main.py
```
Дальше введите имя пользователя и команды (`go n`, `look`, `history`, `whoami`, `quit`).

## Запуск: ADK Web UI
```bash
adk web .
```
Затем в открывшемся UI выберите агент `maze_agent` и отправляйте команды (тот же протокол: `go n`, `look`, `history`, `whoami`).

## Тесты
```bash
pytest
```
Требуют корректных Firestore переменных окружения; используют реальный Firestore.

## Структура проекта
```
project_root/
├── .env.template
├── main.py                 # CLI: связывает конфиг, Firestore, сессию и движок
├── requirements.txt
├── src/
│   ├── config.py           # валидация окружения (pydantic-settings)
│   ├── engine.py           # логика карты и расчёт ходов
│   ├── memory.py           # работа с Firestore
│   └── session.py          # сессионное состояние, события, флеши
├── maze_agent/
│   ├── __init__.py
│   └── agent.py            # ADK агент (root_agent) использует те же хендлеры
└── tests/
    └── test_agent.py       # интеграция с Firestore + проверки движка
```

## Основной поток (CLI и агент)
1. Загрузка конфига -> настройки логов.
2. Инициализация Firestore (`PersistenceManager`) и загрузка состояния пользователя.
3. Создание `SessionManager` с позицией/инвентарём/статами.
4. Парсинг команд -> `engine.calculate_move` -> обновление сессии -> сохранение в Firestore -> ответ.
5. Дополнительно: флеш-сообщения, сарказм, триумф при цели, просмотр истории и статуса (`whoami`).
