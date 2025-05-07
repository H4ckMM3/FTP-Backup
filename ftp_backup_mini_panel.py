import sublime
import sublime_plugin
import os
import re
import json
from datetime import datetime

# Подключение к основному модулю FTP Backup
try:
    from . import ftp_backup
except ImportError:
    import ftp_backup

class FtpBackupMiniPanelCommand(sublime_plugin.TextCommand):
    """Команда для отображения мини-панели FTP Backup"""
    
    def run(self, edit):
        # Получаем информацию о текущем файле и задаче
        view = self.view
        file_path = view.file_name()
        
        if not file_path:
            sublime.status_message("FTP Backup: Нет открытого файла")
            return
            
        # Получаем текущую задачу и сервер
        try:
            current_task = ftp_backup.CURRENT_TASK_NUMBER or "не выбрана"
            current_server = ftp_backup.CURRENT_SERVER or "не определен"
        except:
            current_task = "не выбрана"
            current_server = "не определен"
            
        # Создаем HTML для мини-панели
        html_content = self.generate_panel_html(file_path, current_task, current_server)
        
        # Показываем мини-панель
        view.show_popup(
            html_content,
            max_width=400,
            max_height=300,
            on_navigate=self.on_navigate
        )
    
    def generate_panel_html(self, file_path, current_task, current_server):
        """Генерирует HTML для мини-панели"""
        file_name = os.path.basename(file_path)
        
        # Получаем статистику бэкапов для этого файла
        backup_stats = self.get_backup_stats(file_path)
        
        # Генерируем HTML с кнопкой для выбора задачи
        html = f"""
        <style>
            body {{
                margin: 0;
                padding: 10px;
                font-family: system-ui, sans-serif;
                font-size: 12px;
                background-color: var(--background);
                color: var(--foreground);
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
                border-bottom: 1px solid var(--foreground);
                padding-bottom: 8px;
            }}
            .title {{
                font-weight: bold;
                font-size: 14px;
            }}
            .file-info {{
                margin-bottom: 8px;
                padding: 5px;
                background-color: rgba(128, 128, 128, 0.1);
                border-radius: 3px;
            }}
            .task-info {{
                margin-bottom: 10px;
                position: relative;
            }}
            .task-badge {{
                display: inline-block;
                padding: 2px 5px;
                background-color: #3498db;
                color: white;
                border-radius: 3px;
                font-size: 11px;
            }}
            .server-badge {{
                display: inline-block;
                padding: 2px 5px;
                background-color: #2c3e50;
                color: white;
                border-radius: 3px;
                font-size: 11px;
                margin-left: 5px;
            }}
            .stats {{
                margin-bottom: 10px;
                font-size: 11px;
            }}
            .actions {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 5px;
            }}
            .btn {{
                padding: 5px;
                margin-bottom: 5px;
                text-align: center;
                background-color: rgba(52, 152, 219, 0.2);
                color: var(--foreground);
                text-decoration: none;
                border-radius: 3px;
                cursor: pointer;
            }}
            .btn:hover {{
                background-color: rgba(52, 152, 219, 0.4);
            }}
            .dropdown-btn {{
                display: inline-block;
                padding: 2px 5px;
                margin-left: 5px;
                background-color: rgba(52, 152, 219, 0.2);
                color: var(--foreground);
                text-decoration: none;
                border-radius: 3px;
                cursor: pointer;
                font-size: 11px;
            }}
            .dropdown-btn:hover {{
                background-color: rgba(52, 152, 219, 0.4);
            }}
        </style>
        
        <div class="header">
            <div class="title">FTP Backup</div>
            <a href="close" class="close-btn">✕</a>
        </div>
        
        <div class="file-info">
            Файл: <strong>{file_name}</strong>
        </div>
        
        <div class="task-info">
            Задача: <span class="task-badge">{current_task}</span>
            <span class="server-badge">{current_server}</span>
            <a href="choose_task" class="dropdown-btn">Выбрать</a>
        </div>
        
        <div class="stats">
            <div>Всего бэкапов: <strong>{backup_stats['total']}</strong></div>
            <div>Последний бэкап: <strong>{backup_stats['last_backup']}</strong></div>
        </div>
        
        <div class="actions">
            <a href="before" class="btn">Бэкап "До"</a>
            <a href="after" class="btn">Бэкап "После"</a>
            <a href="zip" class="btn">Создать ZIP</a>
            <a href="interface" class="btn">Интерфейс</a>
        </div>
        """
        
        return html
    
    def get_backup_stats(self, file_path):
        """Получает статистику бэкапов для файла"""
        try:
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            config_path = os.path.join(backup_root, 'backup_config.json')
            
            # Значения по умолчанию
            stats = {
                'total': 0,
                'last_backup': 'нет'
            }
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    import json
                    backup_config = json.load(f)
                
                # Пытаемся получить относительный путь к файлу, как это делает FTP Backup
                relative_path = self.extract_relative_path(file_path)
                
                if relative_path in backup_config:
                    file_info = backup_config[relative_path]
                    
                    # Получаем время последнего бэкапа
                    if 'last_backup_time' in file_info:
                        last_time = file_info['last_backup_time']
                        # Форматируем для более дружественного отображения
                        try:
                            dt = datetime.strptime(last_time, "%Y-%m-%d %H:%M:%S")
                            now = datetime.now()
                            
                            # Если сегодня
                            if dt.date() == now.date():
                                stats['last_backup'] = f"сегодня в {dt.strftime('%H:%M')}"
                            # Если вчера
                            elif (now.date() - dt.date()).days == 1:
                                stats['last_backup'] = f"вчера в {dt.strftime('%H:%M')}"
                            else:
                                stats['last_backup'] = dt.strftime('%d.%m.%Y %H:%M')
                        except:
                            stats['last_backup'] = last_time
                    
                    # Получаем количество бэкапов
                    # Здесь можно было бы посчитать фактические файлы бэкапов,
                    # но для простоты просто устанавливаем 1
                    stats['total'] = 1
                    
                    # Ищем папки с бэкапами
                    backup_dir = os.path.dirname(file_info.get('backup_dir', ''))
                    if backup_dir and os.path.exists(backup_dir):
                        file_name = os.path.basename(file_path)
                        count = 0
                        for root, dirs, files in os.walk(backup_dir):
                            for f in files:
                                if file_name in f:
                                    count += 1
                        if count > 0:
                            stats['total'] = count
            
            return stats
            
        except Exception as e:
            print(f"Ошибка получения статистики: {str(e)}")
            return {'total': 0, 'last_backup': 'ошибка'}
    
    def extract_relative_path(self, file_path):
        """Упрощенная версия метода извлечения относительного пути из FTP Backup"""
        try:
            normalized_path = file_path.replace('/', '\\')
            project_roots = [
                'var\\www\\',
                'www\\',
                'public_html\\',
                'local\\',
                'htdocs\\',
                'home\\'
            ]
            
            for root in project_roots:
                if root in normalized_path:
                    relative_path = normalized_path.split(root, 1)[1]
                    return relative_path.replace('\\', '/')
            
            # Попытка извлечь из временной папки
            temp_match = re.search(r'Temp\\[^\\]+\\(.+)', normalized_path)
            if temp_match:
                return temp_match.group(1).replace('\\', '/')
            
            # В крайнем случае возвращаем имя файла
            return os.path.basename(file_path)
        except:
            return os.path.basename(file_path)
    
    def get_project_tasks(self, file_path):
        """Получает список задач для текущего проекта (сервера)"""
        try:
            # Сначала определяем текущий проект/сервер
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            
            if not backup_root or not os.path.exists(backup_root):
                return []
            
            # Определяем имя сервера из файла или используем текущий
            try:
                # Создаем временный экземпляр FtpBackupManager для определения имени сервера
                backup_manager = ftp_backup.FtpBackupManager(backup_root)
                server_name = backup_manager.extract_site_name(file_path)
                
                # Если не удалось определить, используем текущий сервер
                if not server_name and hasattr(ftp_backup, 'CURRENT_SERVER'):
                    server_name = ftp_backup.CURRENT_SERVER
            except:
                # В случае ошибки, используем текущий сервер
                server_name = ftp_backup.CURRENT_SERVER if hasattr(ftp_backup, 'CURRENT_SERVER') else None
            
            if not server_name:
                return []
            
            # Ищем сопоставление для имени сервера
            server_folder = None
            mapping_path = os.path.join(backup_root, 'folder_mapping.json')
            
            if os.path.exists(mapping_path):
                try:
                    with open(mapping_path, 'r', encoding='utf-8') as f:
                        folder_mapping = json.load(f)
                    
                    if server_name in folder_mapping:
                        server_folder = folder_mapping[server_name]
                except:
                    pass
            
            if not server_folder:
                # Если не нашли в маппинге, пробуем найти по имени
                safe_server_name = re.sub(r'[^\w\-_.]', '_', server_name)
                server_path = os.path.join(backup_root, safe_server_name)
                
                if os.path.exists(server_path) and os.path.isdir(server_path):
                    server_folder = safe_server_name
            
            if not server_folder:
                return []
            
            # Теперь ищем задачи для этого сервера
            server_path = os.path.join(backup_root, server_folder)
            tasks = []
            
            # Просматриваем все подпапки в папке сервера
            for month_folder in os.listdir(server_path):
                month_path = os.path.join(server_path, month_folder)
                
                if not os.path.isdir(month_path):
                    continue
                
                # Ищем папки задач в папке месяца
                for item in os.listdir(month_path):
                    item_path = os.path.join(month_path, item)
                    
                    # Игнорируем служебные папки 'before' и 'after'
                    if item != 'before' and item != 'after' and os.path.isdir(item_path):
                        tasks.append(item)
            
            # Удаляем дубликаты и сортируем
            unique_tasks = sorted(list(set(tasks)))
            return unique_tasks
            
        except Exception as e:
            print(f"Ошибка при получении списка задач: {str(e)}")
            return []
    
    def show_task_selection(self, file_path):
        """Показывает меню выбора задачи через встроенные средства Sublime Text"""
        tasks = self.get_project_tasks(file_path)
        
        if not tasks:
            sublime.status_message("FTP Backup: Нет доступных задач для этого проекта")
            return
        
        # Добавляем возможность ввести новую задачу
        tasks.append("+ Создать новую задачу...")
        
        # Показываем панель быстрого выбора
        self.view.window().show_quick_panel(
            tasks,
            lambda idx: self.on_task_selected(idx, tasks, file_path),
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )
    
    def on_task_selected(self, idx, tasks, file_path):
        """Обработчик выбора задачи из выпадающего меню"""
        if idx == -1:
            # Отмена выбора
            return
        
        if idx == len(tasks) - 1:
            # Выбрана опция "Создать новую задачу"
            self.view.window().show_input_panel(
                "Введите название новой задачи:",
                "",
                self.on_task_entered,
                None,
                None
            )
        else:
            # Выбрана существующая задача
            task_number = tasks[idx]
            self.on_task_entered(task_number)
    
    def on_navigate(self, href):
        """Обрабатывает нажатия на кнопки мини-панели"""
        view = self.view
        window = view.window()
        file_path = view.file_name()
        
        if href == "close":
            view.hide_popup()
            
        elif href == "save":
            view.hide_popup()
            window.run_command("ftp_backup_save")
            
        elif href == "before":
            view.hide_popup()
            window.run_command("ftp_backup_create_before")
            
        elif href == "after":
            view.hide_popup()
            window.run_command("ftp_backup_create_after")
            
        elif href == "zip":
            view.hide_popup()
            window.run_command("ftp_backup_create_zip")
            
        elif href == "choose_task":
            view.hide_popup()
            # Показываем меню выбора задачи
            self.show_task_selection(file_path)
            
        elif href == "history":
            view.hide_popup()
            # Открываем интерфейс истории бэкапов
            # Поскольку специальной команды нет, используем общий интерфейс
            window.run_command("ftp_backup_interface")
            
        elif href == "interface":
            view.hide_popup()
            window.run_command("ftp_backup_interface")
            
        elif href == "settings":
            view.hide_popup()
            window.run_command("ftp_backup_open_settings")
    
    def on_task_entered(self, task_number):
        """Обработчик ввода новой задачи"""
        if not task_number:
            return
        
        try:
            # Устанавливаем новый номер задачи
            ftp_backup.CURRENT_TASK_NUMBER = task_number
            sublime.status_message(f"FTP Backup: Задача изменена на {task_number}")
        except Exception as e:
            sublime.status_message(f"FTP Backup: Ошибка при изменении задачи: {str(e)}")

# Команда для вызова мини-панели через комбинацию клавиш (Alt+B)
class FtpBackupShowMiniPanelCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if view:
            view.run_command("ftp_backup_mini_panel")