# Руководство разработчика для FTP Backup Plugin

## 📋 Содержание

1. [Обзор архитектуры](#обзор-архитектуры)
2. [Структура проекта](#структура-проекта)
3. [Основные компоненты](#основные-компоненты)
4. [API и интерфейсы](#api-и-интерфейсы)
5. [Система логирования](#система-логирования)
6. [Управление конфигурацией](#управление-конфигурацией)
7. [Обработка файлов](#обработка-файлов)
8. [Пользовательский интерфейс](#пользовательский-интерфейс)
9. [Расширение функциональности](#расширение-функциональности)
10. [Отладка и тестирование](#отладка-и-тестирование)
11. [Советы по производительности](#советы-по-производительности)
12. [Известные ограничения](#известные-ограничения)

---

## 🏗️ Обзор архитектуры

FTP Backup Plugin построен на модульной архитектуре с четким разделением ответственности:

```
┌─────────────────────────────────────────────────────────────┐
│                    Sublime Text API                        │
├─────────────────────────────────────────────────────────────┤
│  Commands Layer (Команды Sublime Text)                     │
│  ├── FtpBackupSaveCommand                                  │
│  ├── FtpBackupCreateBeforeCommand                          │
│  ├── FtpBackupCreateAfterCommand                           │
│  └── FtpBackupCreateZipCommand                             │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer (Бизнес-логика)                      │
│  ├── FtpBackupManager                                      │
│  ├── FtpBackupLogger                                       │
│  └── Event Listeners                                       │
├─────────────────────────────────────────────────────────────┤
│  UI Layer (Пользовательский интерфейс)                     │
│  ├── Mini Panel                                            │
│  ├── Full Interface                                        │
│  ├── Task Selector                                         │
│  └── Settings Panel                                        │
├─────────────────────────────────────────────────────────────┤
│  Data Layer (Слой данных)                                  │
│  ├── Configuration Files                                   │
│  ├── File System Operations                                │
│  └── Backup Storage                                        │
└─────────────────────────────────────────────────────────────┘
```

### Принципы проектирования:

1. **Разделение ответственности** - каждый модуль отвечает за свою область
2. **Инверсия зависимостей** - высокоуровневые модули не зависят от низкоуровневых
3. **Единая точка входа** - все операции проходят через FtpBackupManager
4. **Конфигурируемость** - настройки вынесены в отдельные файлы
5. **Логирование** - все операции логируются для отладки

---

## 📁 Структура проекта

```
FTP-Backup-main/
├── ftp_backup.py                    # Основной модуль с бизнес-логикой
├── ftp_backup_interface.py          # HTTP API и веб-интерфейс
├── ftp_backup_ui.py                 # Нативный UI интерфейс
├── ftp_backup_mini_panel.py         # Мини-панель (Alt+B)
├── ftp_backup_task_selector.py      # Селектор задач
├── ftp_backup_task_command.py       # Команды для работы с задачами
├── ftp_backup_settings.py           # Панель настроек
├── ftp_backup.sublime-settings      # Конфигурация по умолчанию
├── Default.sublime-commands         # Регистрация команд
├── Default (Windows).sublime-keymap # Горячие клавиши
├── Main.sublime-menu                # Меню плагина
├── fontawesome.js                   # Иконки для интерфейса
├── messages/                        # Сообщения для пользователей
│   ├── 1.0.0.txt
│   └── install.txt
├── README.md                        # Документация для пользователей
├── LICENSE.md                       # Лицензия
└── DEVELOPER_GUIDE.md              # Это руководство
```

### Ключевые файлы:

- **`ftp_backup.py`** - сердце плагина, содержит всю основную логику
- **`ftp_backup_interface.py`** - HTTP API для веб-интерфейса
- **`ftp_backup_ui.py`** - нативный интерфейс Sublime Text
- **`ftp_backup_mini_panel.py`** - компактная панель управления

---

## 🔧 Основные компоненты

### 1. FtpBackupManager

Центральный класс, управляющий всеми операциями бэкапа:

```python
class FtpBackupManager:
    def __init__(self, backup_root=None):
        self.backup_root = backup_root
        self.server_backup_map = {}
        self.config_path = os.path.join(backup_root, 'backup_config.json')
        self.folder_mapping_path = os.path.join(backup_root, 'folder_mapping.json')
        self.logger = FtpBackupLogger(backup_root)

    def backup_file(self, file_path, server_name=None, mode=None, task_number=None):
        # Основной метод создания бэкапа
        pass

    def create_backup_zip(self, folder_path, folder_type=None):
        # Создание ZIP-архива
        pass
```

**Ключевые методы:**

- `backup_file()` - создание бэкапа файла
- `create_backup_zip()` - архивирование папок
- `extract_site_name()` - извлечение имени сайта из пути
- `_extract_relative_path()` - получение относительного пути

### 2. FtpBackupLogger

Система логирования для отладки:

```python
class FtpBackupLogger:
    def __init__(self, backup_root):
        log_dir = os.path.join(backup_root, 'logs')
        log_file = os.path.join(log_dir, 'ftp_backup.log')
        # Настройка логирования

    def debug(self, message):
        # Отладочные сообщения

    def error(self, message):
        # Сообщения об ошибках
```

### 3. Команды Sublime Text

```python
class FtpBackupSaveCommand(sublime_plugin.TextCommand):
    """Сохранение с бэкапом (Ctrl+Shift+R)"""

class FtpBackupCreateBeforeCommand(sublime_plugin.TextCommand):
    """Создание 'before' бэкапа"""

class FtpBackupCreateAfterCommand(sublime_plugin.TextCommand):
    """Создание 'after' бэкапа"""

class FtpBackupCreateZipCommand(sublime_plugin.WindowCommand):
    """Создание ZIP-архива"""
```

---

## 🔌 API и интерфейсы

### HTTP API (ftp_backup_interface.py)

Плагин предоставляет REST API для веб-интерфейса:

```python
# GET endpoints
/api/get_status              # Текущий статус (задача, сервер)
/api/get_settings            # Настройки плагина
/api/get_recent_backups      # Последние бэкапы
/api/get_file_versions       # Версии файла
/api/get_file_content        # Содержимое файла
/api/get_file_metadata       # Метаданные файла
/api/get_backup_statistics   # Статистика бэкапов

# POST endpoints
/api/save_settings           # Сохранение настроек
/api/restore_file_version    # Восстановление версии файла

# Action endpoints
/api/save                    # Сохранение с бэкапом
/api/before_backup           # Создание 'before' бэкапа
/api/after_backup            # Создание 'after' бэкапа
/api/create_zip              # Создание ZIP-архива
/api/change_task             # Смена задачи
```

### Пример использования API:

```javascript
// Получение статуса
const status = await ftpBackupAPI.getStatus();

// Сохранение с бэкапом
const result = await ftpBackupAPI.saveWithBackup();

// Смена задачи
await ftpBackupAPI.changeTask("task_123");
```

### Внутренние интерфейсы

```python
# Глобальные переменные для состояния
CURRENT_TASK_NUMBER = None  # Текущий номер задачи
CURRENT_SERVER = None       # Текущий сервер/проект

# Методы FtpBackupManager
manager = FtpBackupManager(backup_root)
before_path, after_path, site_name = manager.backup_file(
    file_path,
    server_name="my_project",
    mode="before",
    task_number="task_123"
)
```

---

## 📝 Система логирования

### Конфигурация логирования

```python
class FtpBackupLogger:
    def __init__(self, backup_root):
        log_dir = os.path.join(backup_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'ftp_backup.log')

        logging.basicConfig(
            filename=log_file,
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
```

### Уровни логирования

- **DEBUG** - детальная отладочная информация
- **INFO** - общая информация о работе
- **WARNING** - предупреждения
- **ERROR** - ошибки с полным стектрейсом

### Примеры логов

```
2025-01-15 14:30:25 - DEBUG: Инициализация FtpBackupManager. Корневая папка: C:\BackUp
2025-01-15 14:30:26 - DEBUG: Конфигурация загружена: 15 записей
2025-01-15 14:30:27 - DEBUG: Извлечен путь через корневую папку www: index.php
2025-01-15 14:30:28 - DEBUG: Создан/перезаписан бэкап в C:\BackUp\site\before\index.php
2025-01-15 14:30:29 - ERROR: Ошибка сохранения конфигурации: Permission denied
```

### Отладка проблем

1. **Проверьте лог-файл**: `{backup_root}/logs/ftp_backup.log`
2. **Включите отладку**: логи уже настроены на DEBUG уровень
3. **Анализируйте ошибки**: все исключения логируются с полным стектрейсом

---

## ⚙️ Управление конфигурацией

### Файлы конфигурации

```python
# Основные файлы конфигурации
backup_config.json      # Информация о бэкапах файлов
folder_mapping.json     # Сопоставление имен сайтов с папками
site_name_mapping.json  # Соответствие путей проектов и имен сайтов
```

### Структура backup_config.json

```json
{
  "relative/path/to/file.php": {
    "first_backup_time": "2025-01-15 14:30:25",
    "last_backup_time": "2025-01-15 15:45:12",
    "site": "my_project",
    "backup_dir": "C:\\BackUp\\my_project\\January 2025\\task_123"
  }
}
```

### Структура folder_mapping.json

```json
{
  "my_project": "my_project_folder",
  "another_site": "another_site_folder"
}
```

### Структура site_name_mapping.json

```json
{
  "C:\\var\\www\\my_project": "my_project",
  "C:\\var\\www\\another_site": "another_site"
}
```

### Методы работы с конфигурацией

```python
def _load_config(self):
    """Загрузка конфигурации бэкапов"""
    if os.path.exists(self.config_path):
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.server_backup_map = json.load(f)

def _save_config(self):
    """Сохранение конфигурации"""
    with open(self.config_path, 'w', encoding='utf-8') as f:
        json.dump(self.server_backup_map, f, indent=4, ensure_ascii=False)
```

---

## 📁 Обработка файлов

### Определение имени сайта

```python
def extract_site_name(self, file_path, prompt_if_failed=True):
    """Извлечение имени сайта из пути к файлу"""

    # Паттерны для поиска имени сайта
    patterns = [
        r'(?:var\\www\\|www\\|public_html\\|local\\|htdocs\\|home\\)([^\\]+)',
        r'ftp://([^/]+)',
        r'\\([^\\]+)\\(?:www|public_html|httpdocs)\\',
    ]

    # Поиск по паттернам
    for pattern in patterns:
        match = re.search(pattern, normalized_path)
        if match:
            return match.group(1)

    # Запрос у пользователя
    if prompt_if_failed:
        return self._prompt_site_name()
```

### Извлечение относительного пути

```python
def _extract_relative_path(self, file_path):
    """Извлечение относительного пути файла"""

    project_roots = [
        'var\\www\\',
        'www\\',
        'public_html\\',
        'local\\',
        'htdocs\\',
        'home\\'
    ]

    normalized_path = file_path.replace('/', '\\')
    for root in project_roots:
        if root in normalized_path:
            relative_path = normalized_path.split(root, 1)[1]
            return relative_path.replace('\\', '/')

    return os.path.basename(file_path)
```

### Структура папок бэкапа

```
BackUp/
├── site_name/                    # Имя сайта/проекта
│   ├── January 2025/            # Месяц и год
│   │   ├── task_123/            # Номер задачи
│   │   │   ├── before/          # Версия "до" изменений
│   │   │   │   └── index.php
│   │   │   └── after/           # Версия "после" изменений
│   │   │       └── index.php
│   │   └── backup_site_15.01.2025.14.30.zip
│   └── February 2025/
└── another_site/
```

### Режимы бэкапа

```python
# Режимы для метода backup_file()
mode = None      # Автоматический (создает и before, и after)
mode = 'before'  # Только версия "до"
mode = 'after'   # Только версия "после"
```

---

## 🎨 Пользовательский интерфейс

### Мини-панель (Alt+B)

```python
class FtpBackupMiniPanelCommand(sublime_plugin.WindowCommand):
    def run(self):
        # Создание компактной панели управления
        items = [
            ["💾 Save with Backup", "save_with_backup"],
            ["📁 Create Before Backup", "create_before_backup"],
            ["📁 Create After Backup", "create_after_backup"],
            ["📦 Create ZIP Archive", "create_zip_archive"],
            ["🔄 Change Task", "change_task"],
            ["⚙️ Settings", "open_settings"]
        ]

        self.window.show_quick_panel(items, self.on_selected)
```

### Полный интерфейс (Ctrl+Alt+B)

```python
class FtpBackupInterfaceCommand(sublime_plugin.WindowCommand):
    def run(self):
        # Запуск нативного интерфейса
        self.window.run_command("ftp_backup_ui")
```

### Селектор задач

```python
class FtpBackupTaskSelectorCommand(sublime_plugin.WindowCommand):
    def run(self):
        # Интерфейс для выбора и управления задачами
        # Показывает список существующих задач
        # Позволяет создавать новые задачи
        # Управляет переключением между задачами
```

### Панель настроек

```python
class FtpBackupSettingsCommand(sublime_plugin.WindowCommand):
    def run(self):
        # Интерфейс для настройки плагина
        # Путь к папке бэкапов
        # Создание месячных папок
        # Номер задачи по умолчанию
```

---

## 🔧 Расширение функциональности

### Добавление новой команды

1. **Создайте новый класс команды:**

```python
class FtpBackupCustomCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_path = self.view.file_name()
        if not file_path:
            sublime.status_message("No file open")
            return

        # Ваша логика здесь
        self.perform_custom_operation(file_path)

    def perform_custom_operation(self, file_path):
        # Реализация вашей функциональности
        pass
```

2. **Зарегистрируйте команду в Default.sublime-commands:**

```json
{
  "caption": "FTP Backup: Custom Operation",
  "command": "ftp_backup_custom"
}
```

3. **Добавьте горячие клавиши в Default.sublime-keymap:**

```json
{
  "keys": ["ctrl+shift+c"],
  "command": "ftp_backup_custom"
}
```

### Расширение FtpBackupManager

```python
class ExtendedFtpBackupManager(FtpBackupManager):
    def __init__(self, backup_root=None):
        super().__init__(backup_root)
        # Дополнительная инициализация

    def custom_backup_method(self, file_path):
        """Ваш кастомный метод бэкапа"""
        # Логика вашего метода
        pass

    def validate_file(self, file_path):
        """Валидация файла перед бэкапом"""
        # Проверки файла
        return True
```

### Добавление новых типов бэкапа

```python
def backup_file(self, file_path, server_name=None, mode=None, task_number=None):
    # Существующий код...

    if mode == 'custom':
        # Ваша логика для кастомного режима
        custom_backup_path = os.path.join(task_folder, 'custom')
        os.makedirs(custom_backup_path, exist_ok=True)
        # Дополнительная обработка...
```

### Интеграция с внешними системами

```python
class ExternalSystemIntegration:
    def __init__(self):
        self.api_key = "your_api_key"
        self.api_url = "https://api.example.com"

    def sync_with_external_system(self, backup_info):
        """Синхронизация с внешней системой"""
        # Отправка данных о бэкапе
        pass

    def get_external_backups(self, site_name):
        """Получение бэкапов из внешней системы"""
        # Получение данных
        pass
```

---

## 🐛 Отладка и тестирование

### Отладка в Sublime Text

1. **Включите отладку:**

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Используйте console.log:**

   ```python
   print(f"Debug: {variable}")
   sublime.status_message(f"Debug: {variable}")
   ```

3. **Проверьте лог-файлы:**
   - `{backup_root}/logs/ftp_backup.log`

### Тестирование команд

```python
# Тестирование в консоли Sublime Text
# Откройте консоль: View > Show Console

# Выполнение команды
sublime.active_window().run_command("ftp_backup_save")

# Проверка настроек
settings = sublime.load_settings('ftp_backup.sublime-settings')
print(settings.get('backup_root'))
```

### Тестирование API

```python
# Тестирование HTTP API
import requests

# Получение статуса
response = requests.get('http://localhost:8080/api/get_status')
print(response.json())

# Создание бэкапа
response = requests.post('http://localhost:8080/api/save')
print(response.json())
```

### Создание тестовых данных

```python
def create_test_backup():
    """Создание тестового бэкапа для отладки"""
    test_file = "C:\\var\\www\\test_site\\index.php"
    test_content = "<?php echo 'Hello World'; ?>"

    # Создаем тестовый файл
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, 'w') as f:
        f.write(test_content)

    # Создаем бэкап
    manager = FtpBackupManager("C:\\TestBackup")
    manager.backup_file(test_file, "test_site", "before", "test_task")
```

### Отладка проблем с правами доступа

```python
def check_permissions(path):
    """Проверка прав доступа к папке"""
    try:
        # Проверяем права на чтение
        os.listdir(path)

        # Проверяем права на запись
        test_file = os.path.join(path, 'test_write.tmp')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)

        return True
    except Exception as e:
        print(f"Permission error: {e}")
        return False
```

---

## ⚡ Советы по производительности

### Оптимизация работы с файлами

```python
# Используйте буферизованное копирование для больших файлов
def copy_large_file(src, dst, buffer_size=8192):
    """Копирование больших файлов с буферизацией"""
    with open(src, 'rb') as fsrc:
        with open(dst, 'wb') as fdst:
            while True:
                buf = fsrc.read(buffer_size)
                if not buf:
                    break
                fdst.write(buf)
```

### Кэширование данных

```python
class CachedBackupManager(FtpBackupManager):
    def __init__(self, backup_root=None):
        super().__init__(backup_root)
        self._config_cache = None
        self._cache_timestamp = 0

    def _load_config(self):
        """Кэшированная загрузка конфигурации"""
        current_time = time.time()

        # Проверяем, нужно ли обновить кэш
        if (self._config_cache is None or
            current_time - self._cache_timestamp > 30):  # 30 секунд

            super()._load_config()
            self._config_cache = self.server_backup_map.copy()
            self._cache_timestamp = current_time
        else:
            self.server_backup_map = self._config_cache.copy()
```

### Асинхронные операции

```python
import threading

def async_backup(self, file_path, server_name=None, mode=None, task_number=None):
    """Асинхронное создание бэкапа"""
    def backup_worker():
        try:
            self.backup_file(file_path, server_name, mode, task_number)
            sublime.status_message("Backup completed successfully")
        except Exception as e:
            sublime.error_message(f"Backup failed: {str(e)}")

    # Запускаем в отдельном потоке
    thread = threading.Thread(target=backup_worker)
    thread.daemon = True
    thread.start()
```

### Оптимизация поиска файлов

```python
def find_backup_files_optimized(self, site_name, pattern=None):
    """Оптимизированный поиск файлов бэкапа"""
    site_path = os.path.join(self.backup_root, site_name)

    if not os.path.exists(site_path):
        return []

    # Используем os.walk с фильтрацией
    backup_files = []
    for root, dirs, files in os.walk(site_path):
        # Пропускаем папки логов
        dirs[:] = [d for d in dirs if d != 'logs']

        for file in files:
            if pattern is None or pattern in file:
                backup_files.append(os.path.join(root, file))

    return backup_files
```

---

## ⚠️ Известные ограничения

### Ограничения файловой системы

1. **Максимальный размер файла**: 100 МБ (рекомендуется)
2. **Количество файлов**: до 10,000 бэкапов без заметного замедления
3. **Пути**: максимальная длина пути зависит от ОС

### Ограничения Sublime Text API

```python
# Ограничения API Sublime Text
# - Команды должны выполняться в главном потоке
# - Нет прямого доступа к файловой системе из команд
# - Ограниченный доступ к настройкам системы
```

### Ограничения кодировок

```python
def safe_file_operation(file_path, operation):
    """Безопасная работа с файлами разных кодировок"""
    encodings = ['utf-8', 'cp1251', 'iso-8859-1', 'utf-16']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            return operation(content)
        except UnicodeDecodeError:
            continue

    # Если не удалось прочитать, используем бинарный режим
    with open(file_path, 'rb') as f:
        return operation(f.read().decode('utf-8', errors='replace'))
```

### Ограничения производительности

1. **Большие файлы**: могут замедлить интерфейс
2. **Много бэкапов**: загрузка списка может быть медленной
3. **Сетевые пути**: могут быть медленными

### Рекомендации по обходу ограничений

```python
# Для больших файлов
def backup_large_file(self, file_path, max_size=50*1024*1024):  # 50MB
    """Специальная обработка больших файлов"""
    if os.path.getsize(file_path) > max_size:
        # Используем сжатие или разделение
        return self.backup_compressed_file(file_path)
    else:
        return self.backup_file(file_path)

# Для множественных бэкапов
def get_backups_paginated(self, page=0, page_size=100):
    """Постраничная загрузка бэкапов"""
    all_backups = self.get_all_backups()
    start = page * page_size
    end = start + page_size
    return all_backups[start:end]
```

---

## 📚 Дополнительные ресурсы

### Полезные ссылки

- [Sublime Text API Documentation](https://www.sublimetext.com/docs/api_reference.html)
- [Python File Operations](https://docs.python.org/3/library/os.html)
- [JSON Handling in Python](https://docs.python.org/3/library/json.html)
- [Regular Expressions](https://docs.python.org/3/library/re.html)

### Примеры использования

```python
# Полный пример создания кастомной команды
class FtpBackupCustomBackupCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_path = self.view.file_name()
        if not file_path:
            sublime.status_message("No file open")
            return

        # Загружаем настройки
        settings = sublime.load_settings('ftp_backup.sublime-settings')
        backup_root = settings.get('backup_root')

        if not backup_root:
            sublime.status_message("Backup root not configured")
            return

        # Создаем менеджер
        manager = FtpBackupManager(backup_root)

        # Выполняем кастомную операцию
        try:
            result = manager.custom_backup_operation(file_path)
            sublime.status_message(f"Custom backup completed: {result}")
        except Exception as e:
            sublime.error_message(f"Custom backup failed: {str(e)}")
```

### Контакты для разработчиков

- **Issues**: [GitHub Issues](https://github.com/H4ckMM3/FTP-Backup/issues)
- **Discussions**: [GitHub Discussions](https://github.com/H4ckMM3/FTP-Backup/discussions)
- **Wiki**: [GitHub Wiki](https://github.com/H4ckMM3/FTP-Backup/wiki)

---

## 📄 Лицензия

Этот код распространяется под лицензией MIT. См. файл `LICENSE.md` для подробностей.

---

_Последнее обновление: Январь 2025_
