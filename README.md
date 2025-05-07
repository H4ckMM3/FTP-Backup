# FTP Backup для Sublime Text

<p align="center">
  <img src="https://github.com/user-attachments/assets/46a0c933-3d0b-49cd-a07a-98563a5163d8" alt="FTP Backup Logo" width="200" />

</p>

<p align="center">
  <img src="https://img.shields.io/github/v/release/[ваш_юзернейм]/FTP-Backup?style=flat-square" alt="Version" />
  <img src="https://img.shields.io/github/license/[ваш_юзернейм]/FTP-Backup?style=flat-square" alt="License" />
  <img src="https://img.shields.io/packagecontrol/dt/FTP%20Backup?style=flat-square" alt="Downloads" />
</p>

## 📋 Описание

**FTP Backup** — мощный плагин для Sublime Text, предназначенный для автоматического создания резервных копий ваших файлов. Плагин отслеживает изменения в файлах, сохраняет версии "до" и "после" изменений, и позволяет легко возвращаться к предыдущим версиям.

Идеально подходит для разработчиков, работающих с проектами на удаленных серверах через FTP, SFTP или локально.

## ✨ Основные возможности

- **Автоматическое создание резервных копий** при сохранении файлов
- **Раздельное хранение версий "до" и "после"** изменений
- **Мини-панель** для быстрого доступа к функциям плагина (Alt+B)
- **Привязка к задачам** — организуйте бэкапы по задачам или тикетам
- **Создание ZIP-архивов** с резервными копиями
- **Поддержка разных проектов** — автоматическое определение сервера/сайта
- **Организация бэкапов по месяцам** для удобного хранения

## 🔧 Установка

### Через Package Control (рекомендуется)

1. Откройте **Command Palette** (Ctrl+Shift+P или Cmd+Shift+P на Mac)
2. Выберите `Package Control: Install Package`
3. Найдите и выберите `FTP Backup`

### Вручную

1. Скачайте или клонируйте этот репозиторий
2. Переименуйте папку в `FTP Backup`
3. Переместите папку в директорию пакетов Sublime Text:
   - **Windows**: `%APPDATA%\Sublime Text\Packages\`
   - **macOS**: `~/Library/Application Support/Sublime Text/Packages/`
   - **Linux**: `~/.config/sublime-text/Packages/`

## ⌨️ Клавиши

| Комбинация    | Действие                            |
|---------------|-------------------------------------|
| `Ctrl+Shift+R`| Сохранить файл с резервной копией   |
| `Alt+B`       | Показать мини-панель FTP Backup     |
| `Ctrl+Alt+B`  | Открыть полный интерфейс FTP Backup |

## 🖥️ Как использовать

### Первоначальная настройка

1. **Выберите папку для резервных копий**:
   - Меню `Preferences > Package Settings > FTP Backup > Browse Folder` или
   - Через интерфейс плагина: `Tools > FTP Backup > Browse Backup Folder`

2. **Начало работы**:
   - Используйте `Ctrl+Shift+R` вместо обычного `Ctrl+S` для сохранения ваших файлов
   - При первом сохранении вам будет предложено ввести имя проекта и номер задачи

### Мини-панель (Alt+B)

<p align="center">
  <img src="https://github.com/user-attachments/assets/5227d1f5-dcfe-490f-ba50-d558902f87b3" alt="Мини-панель FTP Backup" width="400" />


</p>

Мини-панель предоставляет быстрый доступ к основным функциям:
- Создание бэкапов "До" и "После"
- Создание ZIP-архива
- Выбор текущей задачи
- Информация о текущем файле и последнем бэкапе

### Полный интерфейс

<p align="center">
  <img src="https://github.com/user-attachments/assets/840a8b72-c381-4a03-b69f-bee50d677c39" alt="Интерфейс FTP Backup" width="600" />

</p>

Доступ к полному интерфейсу:
- Через меню `Tools > FTP Backup > Open Interface`
- Комбинацией клавиш `Ctrl+Alt+B`

## ⚙️ Настройки

Плагин можно настроить через файл `Preferences > Package Settings > FTP Backup > Settings` или через интерфейс плагина.

### Основные настройки:

```json
{
  // Путь к корневой папке для хранения бэкапов
  "backup_root": "C:\\Users\\username\\Desktop\\BackUp",

  // Создавать подпапки с месяцами и годами
  "create_month_folder": true
}
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
│       └── ...
└── another_site/
    └── ...

## 📋 Планы на будущее

Визуальное сравнение версий файлов
Интеграция с системами контроля версий
Расширенная статистика и отчеты
Поддержка Sublime Text 4

## 🐛 Известные проблемы

При использовании на macOS может потребоваться дополнительная настройка прав доступа
Несовместимость с некоторыми другими плагинами, перехватывающими сохранение файлов

## 🤝 Содействие разработке
Вклады приветствуются! Пожалуйста, не стесняйтесь отправлять Pull Request'ы или создавать Issue с предложениями и сообщениями об ошибках.
## 📄 Лицензия
Этот проект распространяется под лицензией MIT. См. файл LICENSE.md для дополнительной информации.
## 📬 Контакты

Создайте Issue в этом репозитории
E-mail: [ваш_email@example.com]
