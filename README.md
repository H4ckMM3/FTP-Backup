# FTP Backup для Sublime Text 🚀

<p align="center">
  <img src="https://github.com/user-attachments/assets/46a0c933-3d0b-49cd-a07a-98563a5163d8" alt="FTP Backup Logo" width="200" />
</p>

<p align="center">
  <a href="https://github.com/[ваш_юзернейм]/FTP-Backup/releases"><img src="https://img.shields.io/github/v/release/[ваш_юзернейм]/FTP-Backup?style=flat-square" alt="Version" /></a>
  <a href="https://github.com/[ваш_юзернейм]/FTP-Backup/blob/main/LICENSE.md"><img src="https://img.shields.io/github/license/[ваш_юзернейм]/FTP-Backup?style=flat-square" alt="License" /></a>
  <a href="https://packagecontrol.io/packages/FTP%20Backup"><img src="https://img.shields.io/packagecontrol/dt/FTP%20Backup?style=flat-square" alt="Downloads" /></a>
</p>

## 📖 Описание

**FTP Backup** — это плагин для **Sublime Text**, который автоматически создает резервные копии ваших файлов при их сохранении. Он сохраняет версии "до" и "после" изменений, упрощая откат к предыдущим версиям. Плагин идеально подходит для разработчиков, работающих с проектами через **FTP**, **SFTP** или локально.

> **Важно**: Не удаляйте файлы `folder_mapping.js`, `backup_config.js`, `site_name_mapping.js` — они необходимы для работы плагина.

## 🌟 Ключевые возможности

- 🔄 **Автоматические резервные копии** при каждом сохранении файла.
- 📂 **Хранение версий "до" и "после"** изменений.
- 🖼️ **Мини-панель** для быстрого доступа (нажмите `Alt+B`).
- 📌 **Привязка к задачам** для организации бэкапов по проектам или тикетам.
- 📦 **Создание ZIP-архивов** для удобного хранения.
- 🌐 **Поддержка разных проектов** с автоматическим определением сервера.
- 📅 **Организация по месяцам** для структурированного хранения.
- ✅ **Перезапись бэкапов** с подтверждением, без прав администратора.

## 🛠️ Установка

### 1️⃣ Через Package Control (рекомендуемый способ)

1. Откройте **Command Palette** (`Ctrl+Shift+P` или `Cmd+Shift+P` на Mac).
2. Выберите `Package Control: Add Repository`.
3. Вставьте URL: `https://github.com/H4ckMM3/FTP-Backup.git`.
4. Снова откройте **Command Palette** и выберите `Package Control: Install Package`.
5. Найдите и установите `FTP Backup`.

### 2️⃣ Вручную

1. Скачайте или клонируйте [репозиторий](https://github.com/H4ckMM3/FTP-Backup).
2. Скопируйте содержимое в папку `User`:
   - **Windows**: `%APPDATA%\Sublime Text\Packages\`
   - **macOS**: `~/Library/Application Support/Sublime Text/Packages/`
   - **Linux**: `~/.config/sublime-text/Packages/`

## 🎹 Горячие клавиши

| Клавиши          | Действие                              |
|------------------|---------------------------------------|
| `Ctrl+Shift+R`   | Сохранить с созданием бэкапа         |
| `Alt+B`          | Открыть мини-панель FTP Backup       |
| `Ctrl+Alt+B`     | Открыть полный интерфейс плагина      |

## 🚀 Быстрый старт

### 1. Настройка папки для бэкапов
- Перейдите в меню: `Preferences > Package Settings > FTP Backup > Browse Folder`.
- Или используйте: `Tools > FTP Backup > Browse Backup Folder`.
- Выберите папку, куда будут сохраняться резервные копии.

### 2. Сохранение файлов
- Используйте `Ctrl+Shift+R` вместо `Ctrl+S` для сохранения с бэкапом.
- При первом сохранении укажите **имя проекта** и **номер задачи**.

### 3. Мини-панель (`Alt+B`)

<p align="center">
  <img src="https://github.com/user-attachments/assets/5227d1f5-dcfe-490f-ba50-d558902f87b3" alt="Мини-панель FTP Backup" width="400" />
</p>

Мини-панель позволяет:
- Создавать бэкапы "до" и "после".
- Формировать ZIP-архивы.
- Переключать задачи.
- Просматривать информацию о файле и последнем бэкапе.

### 4. Полный интерфейс (`Ctrl+Alt+B`)

<p align="center">
  <img src="https://github.com/user-attachments/assets/840a8b72-c381-4a03-b69f-bee50d677c39" alt="Интерфейс FTP Backup" width="600" />
</p>

Доступ через:
- Меню: `Tools > FTP Backup > Open Interface`.
- Клавиши: `Ctrl+Alt+B`.

## ⚙️ Настройки

Настройте плагин через меню: `Preferences > Package Settings > FTP Backup > Settings`.

**Пример конфигурации:**

```json
{
  "backup_root": "C:\\Users\\username\\Desktop\\BackUp",
  "create_month_folder": true
}
```

**Структура папок бэкапов:**

```
BackUp/
├── site_name/
│   ├── January 2025/
│   │   ├── task_number/
│   │   │   ├── before/
│   │   │   │   └── relative_path_to_file
│   │   │   └── after/
│   │   │       └── relative_path_to_file
│   │   └── backup_site_name_date.zip
│   └── February 2025/
└── another_site/
```

## 🛠️ Технические требования

- **Совместимость**: Sublime Text 3 (3.0+), тестируется на Sublime Text 4.
- **ОС**: Windows 7+, macOS 10.12+, Linux (Ubuntu 18.04+, Debian 9+, CentOS 7+).
- **Минимально**:
  - 500 МБ свободного места.
  - Права на запись в папку бэкапов.
  - Python 3.3+ (встроен в Sublime Text 3).
- **Рекомендуется**: SSD, 1 ГБ свободного места.

### Ограничения
- Максимальный размер файла: 100 МБ.
- Не оптимизировано для бинарных файлов.
- Замедление интерфейса при >10,000 бэкапов.

## 🐞 Известные проблемы

- **macOS**: Может потребоваться настройка прав доступа.
- **Конфликты**: С плагинами, перехватывающими команды сохранения.
- **Кодировки**: Проблемы с UTF-16 и редкими кодировками.

## 📅 Планы развития

### Краткосрочные (1-2 месяца)
- Исправление ошибок с кодировками и правами доступа.
- Индикатор прогресса для ZIP-архивов.
- Настраиваемые горячие клавиши.

### Среднесрочные (3-6 месяцев)
- Оптимизация для больших файлов.
- Визуальный компаратор версий.
- Поиск и фильтрация бэкапов.

### Долгосрочные (6-12 месяцев)
- Интеграция с облачными хранилищами.
- Поддержка Git и других VCS.
- Дедупликация бэкапов.

## 🤝 Как помочь проекту

- ⭐ Поставьте звезду на [GitHub](https://github.com/H4ckMM3/FTP-Backup)!
- 🐛 Сообщайте об ошибках через [Issues](https://github.com/H4ckMM3/FTP-Backup/issues).
- 💡 Предлагайте идеи или отправляйте Pull Request.

## 📜 Лицензия

Распространяется под [MIT License](LICENSE.md).

## 📬 Обратная связь

Есть вопросы или предложения? Пишите в [Issues](https://github.com/H4ckMM3/FTP-Backup/issues)
