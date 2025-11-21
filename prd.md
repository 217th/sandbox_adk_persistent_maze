# Product Requirements Document (PRD): ADK Persistent Maze Agent (v4.0)

## 1\. Введение

Данный документ описывает архитектуру и требования к реализации диалогового агента "Persistent Maze" (Персистентный Лабиринт) на базе Google Agent Development Kit (ADK).

**Ключевая особенность:** Гибридная модель памяти.

1.  **Hot Storage (Session):** Хранит кратковременные реакции (Flash), историю текущего диалога (Events) и текущее состояние для быстрого доступа.
2.  **Cold Storage (Firestore):** Хранит долгосрочный прогресс пользователя (координаты, инвентарь) между перезапусками приложения.

## 2\. Сценарий Использования (User Experience)

### 2.1 Игровой Мир

  * **Размер:** Сетка 5x5 (x: 0..4, y: 0..4).
  * **Точка старта:** (0, 0).
  * **Цель:** Клетка (4, 4), содержащая "Золотую Монету".
  * **Стены (Непроходимые зоны):**
      * (1, 1), (1, 2) — вертикальная преграда.
      * (3, 3) — одиночный блок.
      * (2, 0) — стена у нижней границы.

### 2.2 Интерфейс Команд (CLI)

Агент должен распознавать следующие текстовые команды (Case-insensitive):

1.  **Команды движения:** `go north`, `go south`, `go east`, `go west` (или `n`, `s`, `e`, `w`).
2.  **Команды осмотра:** `look` / `where` (описание клетки, стены, инвентарь).
3.  **Команды отладки:**
      * `history`: показать сырой лог событий текущей сессии (из RAM).
      * `whoami`: показать имя пользователя и статус синхронизации с облаком.

### 2.3 Поведенческие Паттерны

  * **Стандартный тон:** Нейтральный.
  * **Успех:** Торжественный (при взятии монеты).
  * **Упрямство:** Если пользователь 3 раза подряд получает статус `BLOCKED` или `OOB` (Out of Bounds), агент отвечает с сарказмом.

## 3\. Модель Данных

### 3.1 Persistent Memory (Google Cloud Firestore)

  * **Коллекция:** Конфигурируемое имя (например, `maze_users`).
  * **Document ID:** `username` (String).
  * **Schema:**
    ```json
    {
      "last_updated": "Timestamp",
      "position": { "x": 2, "y": 3 },
      "inventory": ["gold_coin"], // Если взята
      "stats": { "total_steps": 15 }
    }
    ```

### 3.2 Session Storage (ADK Session Object)

Живет только в рамках процесса диалога.

  * **State:** Копия данных из Firestore + текущие изменения.
  * **Events (`_event_log`):** Список словарей `{"timestamp": "...", "action": "MOVE", "result": "BLOCKED"}`.
  * **Flash (`_flash_buffer`):** Очередь одноразовых сообщений (уведомления об ошибках или событиях), которая очищается после прочтения.

## 4\. Структура Проекта (Project Structure) [CRITICAL]

Кодирующий агент должен придерживаться следующей файловой структуры. Любые отклонения от этой структуры допустимы **только** при наличии явного текстового обоснования в комментариях к коду или в ответе.

```text
project_root/
├── .env                # Локальные секреты (в .gitignore)
├── .env.template       # Шаблон переменных окружения
├── main.py             # Точка входа приложения
├── requirements.txt    # Зависимости (включая pydantic-settings)
├── src/
│   ├── __init__.py
│   ├── config.py       # Валидация конфигурации (Pydantic)
│   ├── engine.py       # MazeEngine (Логика игры, без I/O)
│   ├── memory.py       # PersistenceManager (Firestore Client)
│   └── session.py      # SessionManager (Flash/Events Logic)
└── tests/
    ├── __init__.py
    └── test_agent.py   # Интеграционные тесты
```

## 5\. Конфигурация и Валидация (Configuration)

Использовать библиотеку `pydantic-settings` для строгой типизации конфигурации.
Валидация должна происходить при старте приложения (`main.py`). Если конфигурация невалидна, приложение должно немедленно завершаться с ошибкой.

**Обязательные поля (`src/config.py`):**

1.  `GOOGLE_APPLICATION_CREDENTIALS`: Путь к JSON-ключу (FilePath).
2.  `FIRESTORE_PROJECT_ID`: ID проекта Google Cloud (String).
3.  `MAZE_COLLECTION_NAME`: Имя коллекции Firestore (String).
4.  `LOG_LEVEL`: Уровень логирования (Optional, default="INFO").

## 6\. Функциональные Компоненты

### 6.1 Модуль `src/memory.py`

  * Инициализирует клиент Firestore, используя `config.py`.
  * **Load:** `get_user(username)` -\> возвращает dict. Если нет — создает дефолтный (0,0).
  * **Save:** `update_user(username, data)` -\> пишет `position` и `inventory`.

### 6.2 Модуль `src/session.py`

  * Управляет объектом сессии ADK.
  * Реализует логику **Flash**: методы `add_flash(msg)` и `consume_flash()`.
  * Реализует логику **Events**: запись событий и проверка "упрямства" (анализ последних 3-х записей).

### 6.3 Модуль `src/engine.py`

  * Содержит константы карты (размер 5x5, координаты стен, координата монеты).
  * Метод `calculate_move(current_pos, direction)` -\> возвращает новую позицию и статус (SUCCESS/BLOCKED).

## 7\. Логика Обработки Хода

1.  **Start:** Ввод имени -\> `memory.load` -\> запись данных в `session.state`.
2.  **Move:** Ввод команды -\> `engine.calculate` -\> `session.state` update.
      * Если успех: запись в `session.events` (SUCCESS) -\> `memory.save` (Firestore).
      * Если стена: запись в `session.events` (BLOCKED) -\> `session.flash.add("Стена!")`.
3.  **Response:**
      * Формирование текста на основе новой позиции.
      * Проверка `session.check_stubbornness()` -\> добавление сарказма.
      * Вызов `session.consume_flash()` -\> добавление уведомлений.

## 8\. Логирование и Технические Требования

  * **Язык:** Python 3.10+
  * **Логи:** Вывод в `stdout`. Формат: `[TIMESTAMP] [CATEGORY] Message`. Категории: `[CONFIG]`, `[CLOUD]`, `[GAME]`, `[SESSION]`.
  * **Тестирование:** Реализовать тесты в `tests/test_agent.py`, которые проверяют полный цикл (Save/Load) с использованием **реального** подключения к Firestore (на основе предоставленных ключей).
