import sublime
import sublime_plugin
import os
import json
import tempfile
import webbrowser
import socket
import threading
import http.server
import socketserver
import urllib.parse
import sys
import time
from datetime import datetime, timedelta
from functools import partial

# Глобальная переменная для хранения пути к временному HTML-файлу
TEMP_HTML_PATH = None
# Глобальная переменная для хранения порта сервера
SERVER_PORT = None
# Глобальная переменная для хранения экземпляра сервера
HTTP_SERVER = None

class BackupHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Обработчик HTTP-запросов для FTP Backup интерфейса"""
    
    def __init__(self, *args, directory=None, **kwargs):
        self.directory = directory
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Обработка GET-запросов"""
        parsed_path = urllib.parse.urlparse(self.path)
        
        # Корневой путь - показываем основной интерфейс
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Читаем HTML из файла
            with open(TEMP_HTML_PATH, 'rb') as f:
                self.wfile.write(f.read())
            return
            
        # API для выполнения команд
        elif parsed_path.path.startswith('/api/'):
            self.handle_api_request(parsed_path.path)
            return
            
        # Для всех остальных запросов - файлы из директории
        else:
            return super().do_GET()
    
    def do_POST(self):
        """Обработка POST-запросов для API"""
        parsed_path = urllib.parse.urlparse(self.path)
        
        if parsed_path.path.startswith('/api/'):
            # Получаем данные из тела запроса
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
                self.handle_api_post_request(parsed_path.path, data)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON data")
            return
        
        self.send_error(404, "Not found")
    
    def handle_api_post_request(self, path, data):
        """Обработка POST API-запросов"""
        # Разбираем путь запроса
        parts = path.split('/')[2:]  # Отбрасываем '/api/'
        
        if not parts:
            self.send_error(400, "Bad Request - Missing API endpoint")
            return
            
        command = parts[0]
        response = {"status": "error", "message": "Unknown command"}
        
        try:
            if command == "save_settings":
                # Сохраняем настройки
                if "backup_root" in data:
                    # Загружаем настройки
                    settings = sublime.load_settings('ftp_backup.sublime-settings')
                    settings.set('backup_root', data["backup_root"])
                    sublime.save_settings('ftp_backup.sublime-settings')
                    
                    # Если указан создавать месячные папки, сохраняем эту настройку
                    if "create_month_folder" in data:
                        settings.set('create_month_folder', data["create_month_folder"])
                        
                    # Если указан номер задачи по умолчанию, сохраняем его
                    if "default_task_number" in data and data["default_task_number"]:
                        # Устанавливаем новый номер задачи
                        try:
                            module_name = 'ftp_backup'
                            if module_name in sys.modules:
                                module = sys.modules[module_name]
                                module.CURRENT_TASK_NUMBER = data["default_task_number"]
                        except Exception as e:
                            print(f"Error setting task number: {str(e)}")
                    
                    response = {
                        "status": "success", 
                        "message": "Settings saved successfully"
                    }
                else:
                    response = {
                        "status": "error", 
                        "message": "Missing backup_root parameter"
                    }
            elif command == "restore_file_version":
                # Восстанавливаем версию файла
                if "version_path" in data and "file_path" in data:
                    version_path = data["version_path"]
                    file_path = data["file_path"]
                    
                    try:
                        # Проверяем существование файлов
                        if not os.path.exists(version_path):
                            response = {"status": "error", "message": "Version file not found"}
                        else:
                            # Сначала делаем резервную копию текущего файла
                            if os.path.exists(file_path):
                                # Создаем автоматический бэкап текущего файла перед восстановлением
                                sublime.active_window().run_command("ftp_backup_create_before", {"file_path": file_path})
                            
                            # Копируем содержимое выбранной версии в текущий файл
                            with open(version_path, 'r', encoding='utf-8', errors='replace') as source:
                                content = source.read()
                            
                            # Создаем директорию, если её нет
                            os.makedirs(os.path.dirname(file_path), exist_ok=True)
                            
                            with open(file_path, 'w', encoding='utf-8') as target:
                                target.write(content)
                            
                            response = {"status": "success", "message": "File version restored"}
                    except Exception as e:
                        response = {"status": "error", "message": str(e)}
                else:
                    response = {"status": "error", "message": "Missing version_path or file_path"}
        except Exception as e:
            response = {"status": "error", "message": str(e)}
        
        # Отправляем ответ
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def handle_api_request(self, path):
        """Обработка API-запросов"""
        # Разбираем путь запроса
        parts = path.split('/')[2:]  # Отбрасываем '/api/'
        
        if not parts:
            self.send_error(400, "Bad Request - Missing API endpoint")
            return
            
        command = parts[0]
        
        # Простой ответ для подтверждения запроса
        response = {"status": "success", "message": f"Command {command} executed"}
        
        # Выполняем соответствующую команду в Sublime Text
        try:
            if command == "save":
                # Запускаем команду сохранения с бэкапом
                sublime.active_window().run_command("ftp_backup_save")
            elif command == "before_backup":
                sublime.active_window().run_command("ftp_backup_create_before")
            elif command == "after_backup":
                sublime.active_window().run_command("ftp_backup_create_after")
            elif command == "create_zip":
                sublime.active_window().run_command("ftp_backup_create_zip")
            elif command == "open_folder":
                sublime.active_window().run_command("ftp_backup_open_folder_in_explorer")
            elif command == "open_settings":
                sublime.active_window().run_command("ftp_backup_open_settings")
            elif command == "change_task":
                # Получаем параметр task_number из запроса
                if len(parts) > 1:
                    task_number = parts[1]
                    # Устанавливаем новый номер задачи
                    module_name = 'ftp_backup'
                    if module_name in sys.modules:
                        module = sys.modules[module_name]
                        module.CURRENT_TASK_NUMBER = task_number
                        response["message"] = f"Task changed to: {task_number}"
                else:
                    response = {"status": "error", "message": "Missing task number"}
            elif command == "get_status":
                # Возвращаем текущий статус (задача и сервер)
                try:
                    from ftp_backup import CURRENT_TASK_NUMBER, CURRENT_SERVER
                    response = {
                        "status": "success",
                        "current_task": CURRENT_TASK_NUMBER,
                        "current_server": CURRENT_SERVER
                    }
                except ImportError:
                    response = {
                        "status": "error", 
                        "message": "Could not access ftp_backup module"
                    }
            elif command == "get_settings":
                # Возвращаем текущие настройки
                try:
                    settings = sublime.load_settings('ftp_backup.sublime-settings')
                    backup_root = settings.get('backup_root', os.path.join(os.path.expanduser("~"), "Desktop", "BackUp"))
                    create_month_folder = settings.get('create_month_folder', True)
                    
                    # Получаем текущий номер задачи
                    try:
                        from ftp_backup import CURRENT_TASK_NUMBER
                        default_task_number = CURRENT_TASK_NUMBER
                    except ImportError:
                        default_task_number = ""
                    
                    response = {
                        "status": "success",
                        "backup_root": backup_root,
                        "create_month_folder": create_month_folder,
                        "default_task_number": default_task_number
                    }
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
            elif command == "get_recent_backups":
                # Возвращаем последние сохраненные файлы
                try:
                    # Получаем путь к корневой папке бэкапов
                    settings = sublime.load_settings('ftp_backup.sublime-settings')
                    backup_root = settings.get('backup_root', os.path.join(os.path.expanduser("~"), "Desktop", "BackUp"))
                    
                    # Загружаем конфигурацию бэкапов
                    config_path = os.path.join(backup_root, 'backup_config.json')
                    recent_files = []
                    
                    if os.path.exists(config_path):
                        with open(config_path, 'r', encoding='utf-8') as f:
                            backup_config = json.load(f)
                            
                        # Преобразуем в список и сортируем по времени последнего бэкапа
                        files = []
                        for path, info in backup_config.items():
                            if 'last_backup_time' in info:
                                files.append({
                                    'path': path,
                                    'site': info.get('site', 'unknown'),
                                    'last_backup_time': info.get('last_backup_time', ''),
                                    'first_backup_time': info.get('first_backup_time', '')
                                })
                        
                        # Сортируем по времени последнего бэкапа (сначала новые)
                        files.sort(key=lambda x: x['last_backup_time'], reverse=True)
                        
                        # Берем последние 10 файлов
                        recent_files = files[:10]
                        
                    response = {
                        "status": "success",
                        "recent_files": recent_files
                    }
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
            elif command == "get_file_versions":
                # Получаем путь к файлу из параметров
                if len(parts) > 1:
                    file_path = urllib.parse.unquote(parts[1])
                    try:
                        # Получаем корневую папку бэкапов
                        settings = sublime.load_settings('ftp_backup.sublime-settings')
                        backup_root = settings.get('backup_root', os.path.join(os.path.expanduser("~"), "Desktop", "BackUp"))
                        
                        # Загружаем конфигурацию бэкапов
                        config_path = os.path.join(backup_root, 'backup_config.json')
                        versions = []
                        
                        if os.path.exists(config_path):
                            with open(config_path, 'r', encoding='utf-8') as f:
                                backup_config = json.load(f)
                            
                            # Получаем информацию о конкретном файле
                            if file_path in backup_config:
                                file_info = backup_config[file_path]
                                backup_dir = file_info.get('backup_dir', '')
                                
                                if backup_dir and os.path.exists(backup_dir):
                                    # Ищем все версии файла
                                    file_name = os.path.basename(file_path)
                                    for backup_file in os.listdir(backup_dir):
                                        if file_name in backup_file:
                                            # Определяем тип бэкапа (before/after)
                                            backup_type = 'Unknown'
                                            if '_before_' in backup_file:
                                                backup_type = 'Before'
                                            elif '_after_' in backup_file:
                                                backup_type = 'After'
                                            elif '_auto_' in backup_file:
                                                backup_type = 'Auto'
                                            
                                            # Получаем время из имени файла или из метаданных
                                            time_str = ''
                                            try:
                                                # Пытаемся извлечь дату из имени файла
                                                # Формат примерно такой: file_name_20230415_123045.php
                                                parts = backup_file.split('_')
                                                if len(parts) >= 2:
                                                    date_part = parts[-2]
                                                    time_part = parts[-1].split('.')[0]
                                                    if len(date_part) == 8 and len(time_part) == 6:
                                                        time_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                                            except:
                                                # Если не получилось извлечь дату из имени, используем дату модификации
                                                backup_path = os.path.join(backup_dir, backup_file)
                                                time_str = datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime('%Y-%m-%d %H:%M:%S')
                                            
                                            versions.append({
                                                'path': os.path.join(backup_dir, backup_file),
                                                'type': backup_type,
                                                'time': time_str
                                            })
                                    
                                    # Текущая версия файла (если существует)
                                    if os.path.exists(file_path):
                                        versions.append({
                                            'path': file_path,
                                            'type': 'Current',
                                            'time': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                                        })
                                    
                                    # Сортируем версии по времени (новые вверху)
                                    versions.sort(key=lambda x: x['time'], reverse=True)
                        
                        response = {
                            "status": "success",
                            "versions": versions
                        }
                    except Exception as e:
                        response = {"status": "error", "message": str(e)}
                else:
                    response = {"status": "error", "message": "Missing file path"}
            elif command == "get_file_content":
                # Получаем путь к файлу из параметров
                if len(parts) > 1:
                    file_path = urllib.parse.unquote(parts[1])
                    try:
                        if os.path.exists(file_path):
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                                file_content = f.read()
                            
                            response = {
                                "status": "success",
                                "content": file_content
                            }
                        else:
                            response = {"status": "error", "message": "File not found"}
                    except Exception as e:
                        response = {"status": "error", "message": str(e)}
                else:
                    response = {"status": "error", "message": "Missing file path"}
            elif command == "get_file_metadata":
                # Получаем путь к файлу из параметров
                if len(parts) > 1:
                    file_path = urllib.parse.unquote(parts[1])
                    try:
                        if os.path.exists(file_path):
                            # Получаем информацию о файле
                            file_size = os.path.getsize(file_path)
                            create_time = datetime.fromtimestamp(os.path.getctime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                            modified_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S')
                            
                            response = {
                                "status": "success",
                                "size": file_size,
                                "create_time": create_time,
                                "modified_time": modified_time
                            }
                        else:
                            response = {"status": "error", "message": "File not found"}
                    except Exception as e:
                        response = {"status": "error", "message": str(e)}
                else:
                    response = {"status": "error", "message": "Missing file path"}
            elif command == "open_file":
                # Получаем путь к файлу из параметров
                if len(parts) > 1:
                    file_path = urllib.parse.unquote(parts[1])
                    try:
                        if os.path.exists(file_path):
                            # Открываем файл в Sublime Text
                            window = sublime.active_window()
                            window.open_file(file_path)
                            response = {"status": "success", "message": "File opened"}
                        else:
                            response = {"status": "error", "message": "File not found"}
                    except Exception as e:
                        response = {"status": "error", "message": str(e)}
                else:
                    response = {"status": "error", "message": "Missing file path"}
            elif command == "export_file_history":
                # Получаем путь к файлу из параметров
                if len(parts) > 1:
                    file_path = urllib.parse.unquote(parts[1])
                    try:
                        # Получаем корневую папку бэкапов
                        settings = sublime.load_settings('ftp_backup.sublime-settings')
                        backup_root = settings.get('backup_root', os.path.join(os.path.expanduser("~"), "Desktop", "BackUp"))
                        
                        # Загружаем конфигурацию бэкапов
                        config_path = os.path.join(backup_root, 'backup_config.json')
                        report_data = []
                        
                        if os.path.exists(config_path):
                            with open(config_path, 'r', encoding='utf-8') as f:
                                backup_config = json.load(f)
                            
                            # Получаем информацию о конкретном файле
                            if file_path in backup_config:
                                file_info = backup_config[file_path]
                                backup_dir = file_info.get('backup_dir', '')
                                
                                # Добавляем основную информацию о файле
                                report_data.append(f"File History Report for: {file_path}")
                                report_data.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                                report_data.append(f"Server: {file_info.get('site', 'unknown')}")
                                report_data.append(f"First backup: {file_info.get('first_backup_time', 'unknown')}")
                                report_data.append(f"Last backup: {file_info.get('last_backup_time', 'unknown')}")
                                report_data.append("\n")
                                report_data.append("Backup Versions:")
                                report_data.append("-" * 60)
                                
                                if backup_dir and os.path.exists(backup_dir):
                                    # Ищем все версии файла
                                    file_name = os.path.basename(file_path)
                                    backup_files = []
                                    
                                    for backup_file in os.listdir(backup_dir):
                                        if file_name in backup_file:
                                            backup_type = 'Unknown'
                                            if '_before_' in backup_file:
                                                backup_type = 'Before'
                                            elif '_after_' in backup_file:
                                                backup_type = 'After'
                                            elif '_auto_' in backup_file:
                                                backup_type = 'Auto'
                                            
                                            # Получаем время из имени файла или из метаданных
                                            time_str = ''
                                            try:
                                                # Пытаемся извлечь дату из имени файла
                                                parts = backup_file.split('_')
                                                if len(parts) >= 2:
                                                    date_part = parts[-2]
                                                    time_part = parts[-1].split('.')[0]
                                                    if len(date_part) == 8 and len(time_part) == 6:
                                                        time_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
                                            except:
                                                # Если не получилось извлечь дату из имени, используем дату модификации
                                                backup_path = os.path.join(backup_dir, backup_file)
                                                time_str = datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime('%Y-%m-%d %H:%M:%S')
                                            
                                            backup_path = os.path.join(backup_dir, backup_file)
                                            file_size = os.path.getsize(backup_path)
                                            
                                            backup_files.append({
                                                'path': backup_path,
                                                'type': backup_type,
                                                'time': time_str,
                                                'size': file_size
                                            })
                                    
                                    # Сортируем версии по времени (новые вверху)
                                    backup_files.sort(key=lambda x: x['time'], reverse=True)
                                    
                                    # Добавляем текущую версию, если она существует
                                    if os.path.exists(file_path):
                                        backup_files.insert(0, {
                                            'path': file_path,
                                            'type': 'Current',
                                            'time': datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M:%S'),
                                            'size': os.path.getsize(file_path)
                                        })
                                    
                                    # Добавляем информацию о каждой версии
                                    for idx, version in enumerate(backup_files, 1):
                                        report_data.append(f"{idx}. {version['type']} Version")
                                        report_data.append(f"   Time: {version['time']}")
                                        report_data.append(f"   Size: {version['size']} bytes")
                                        report_data.append(f"   Path: {version['path']}")
                                        report_data.append("")
                                
                                # Создаем директорию для отчетов, если её нет
                                reports_dir = os.path.join(backup_root, 'reports')
                                os.makedirs(reports_dir, exist_ok=True)
                                
                                # Создаем отчет
                                report_filename = f"file_history_{os.path.basename(file_path)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                                report_path = os.path.join(reports_dir, report_filename)
                                
                                with open(report_path, 'w', encoding='utf-8') as f:
                                    f.write('\n'.join(report_data))
                                
                                response = {
                                    "status": "success",
                                    "message": "History report exported successfully",
                                    "export_path": report_path
                                }
                            else:
                                response = {"status": "error", "message": "File not found in backup config"}
                        else:
                            response = {"status": "error", "message": "Backup configuration not found"}
                    except Exception as e:
                        response = {"status": "error", "message": str(e)}
                else:
                    response = {"status": "error", "message": "Missing file path"}
            elif command == "get_backup_statistics":
                try:
                    # Получаем корневую папку бэкапов
                    settings = sublime.load_settings('ftp_backup.sublime-settings')
                    backup_root = settings.get('backup_root', os.path.join(os.path.expanduser("~"), "Desktop", "BackUp"))
                    
                    # Загружаем конфигурацию бэкапов
                    config_path = os.path.join(backup_root, 'backup_config.json')
                    
                    total_backups = 0
                    total_size = 0
                    unique_files = 0
                    most_backed_up_file = ""
                    most_backed_up_count = 0
                    file_backup_counts = {}
                    
                    # Статистика для тренда
                    current_week_backups = 0
                    previous_week_backups = 0
                    
                    if os.path.exists(config_path):
                        with open(config_path, 'r', encoding='utf-8') as f:
                            backup_config = json.load(f)
                        
                        # Текущая дата
                        now = datetime.now()
                        
                        # Начало текущей недели и предыдущей недели
                        current_week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
                        previous_week_start = current_week_start - timedelta(days=7)
                        
                        # Подсчитываем статистику
                        unique_files = len(backup_config)
                        
                        for file_path, file_info in backup_config.items():
                            # Подсчитываем бэкапы для каждого файла
                            backup_dir = file_info.get('backup_dir', '')
                            
                            if backup_dir and os.path.exists(backup_dir):
                                file_name = os.path.basename(file_path)
                                backup_count = 0
                                
                                for backup_file in os.listdir(backup_dir):
                                    if file_name in backup_file:
                                        backup_count += 1
                                        total_backups += 1
                                        
                                        # Получаем размер файла для общей статистики
                                        backup_path = os.path.join(backup_dir, backup_file)
                                        total_size += os.path.getsize(backup_path)
                                        
                                        # Проверяем, к какой неделе относится бэкап
                                        try:
                                            # Извлекаем дату из имени файла или из метаданных
                                            backup_time = None
                                            
                                            # Пытаемся извлечь дату из имени файла
                                            parts = backup_file.split('_')
                                            if len(parts) >= 2:
                                                date_part = parts[-2]
                                                time_part = parts[-1].split('.')[0]
                                                if len(date_part) == 8 and len(time_part) == 6:
                                                    backup_time = datetime.strptime(f"{date_part} {time_part}", "%Y%m%d %H%M%S")
                                            
                                            # Если не получилось извлечь дату из имени, используем дату модификации
                                            if backup_time is None:
                                                backup_time = datetime.fromtimestamp(os.path.getmtime(backup_path))
                                            
                                            # Проверяем, к какой неделе относится бэкап
                                            if backup_time >= current_week_start:
                                                current_week_backups += 1
                                            elif backup_time >= previous_week_start:
                                                previous_week_backups += 1
                                        except:
                                            pass  # Игнорируем ошибки при определении даты бэкапа
                                
                                # Сохраняем количество бэкапов для файла
                                file_backup_counts[file_path] = backup_count
                                
                                # Определяем файл с наибольшим количеством бэкапов
                                if backup_count > most_backed_up_count:
                                    most_backed_up_count = backup_count
                                    most_backed_up_file = file_path
                        
                        # Рассчитываем тренд (процентное изменение с прошлой недели)
                        weekly_trend = 0
                        if previous_week_backups > 0:
                            weekly_trend = round(((current_week_backups - previous_week_backups) / previous_week_backups) * 100)
                    
                    response = {
                        "status": "success",
                        "total_backups": total_backups,
                        "total_size": total_size,
                        "unique_files": unique_files,
                        "weekly_trend": weekly_trend,
                        "most_backed_up": most_backed_up_file
                    }
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
            else:
                response = {"status": "error", "message": f"Unknown command: {command}"}
        
        except Exception as e:
            response = {"status": "error", "message": str(e)}
        
        # Отправляем ответ
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

def find_free_port():
    """Находит свободный порт для запуска сервера"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def start_http_server(html_path):
    """Запускает HTTP-сервер для обслуживания HTML-интерфейса"""
    global SERVER_PORT, HTTP_SERVER, TEMP_HTML_PATH
    
    # Сохраняем путь к HTML-файлу
    TEMP_HTML_PATH = html_path
    
    # Находим свободный порт
    SERVER_PORT = find_free_port()
    
    # Получаем директорию, где находится HTML-файл
    directory = os.path.dirname(html_path)
    
    # Создаем обработчик с указанием директории
    handler = partial(BackupHTTPRequestHandler, directory=directory)
    
    # Запускаем сервер в отдельном потоке
    HTTP_SERVER = socketserver.TCPServer(("", SERVER_PORT), handler)
    
    server_thread = threading.Thread(target=HTTP_SERVER.serve_forever)
    server_thread.daemon = True
    server_thread.start()
    
    return SERVER_PORT

def stop_http_server():
    """Останавливает HTTP-сервер"""
    global HTTP_SERVER
    if HTTP_SERVER:
        HTTP_SERVER.shutdown()
        HTTP_SERVER = None

def prepare_html_with_api(html_content):
    """Модифицирует HTML-код для работы с API"""
    # Заменяем прямые вызовы на API-запросы
    api_script = """
    <script>
        // API для взаимодействия с Sublime Text
        const ftpBackupAPI = {
            call: async function(command, params = null) {
                let url = `/api/${command}`;
                if (params) {
                    url += `/${params}`;
                }
                const response = await fetch(url);
                return await response.json();
            },
            
            post: async function(command, data) {
                let url = `/api/${command}`;
                const response = await fetch(url, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                });
                return await response.json();
            },
            
            getStatus: async function() {
                return await this.call('get_status');
            },
            
            getSettings: async function() {
                return await this.call('get_settings');
            },
            
            getRecentBackups: async function() {
                return await this.call('get_recent_backups');
            },
            
            saveSettings: async function(settings) {
                return await this.post('save_settings', settings);
            },
            
            saveWithBackup: async function() {
                return await this.call('save');
            },
            
            createBeforeBackup: async function() {
                return await this.call('before_backup');
            },
            
            createAfterBackup: async function() {
                return await this.call('after_backup');
            },
            
            createZip: async function() {
                return await this.call('create_zip');
            },
            
            openFolder: async function() {
                return await this.call('open_folder');
            },
            
            openSettings: async function() {
                return await this.call('open_settings');
            },
            
            changeTask: async function(taskNumber) {
                return await this.call('change_task', taskNumber);
            }
        };

        // Функция для форматирования даты
        function formatDateTime(dateTimeStr) {
            if (!dateTimeStr) return '';
            
            const now = new Date();
            const date = new Date(dateTimeStr);
            
            // Проверяем, сегодня ли эта дата
            const isToday = date.toDateString() === now.toDateString();
            
            // Проверяем, вчера ли эта дата
            const yesterday = new Date(now);
            yesterday.setDate(now.getDate() - 1);
            const isYesterday = date.toDateString() === yesterday.toDateString();
            
            // Форматируем время
            const timeStr = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            
            if (isToday) {
                return `Today, ${timeStr}`;
            } else if (isYesterday) {
                return `Yesterday, ${timeStr}`;
            } else {
                // Для более старых дат показываем полную дату
                return date.toLocaleDateString() + ', ' + timeStr;
            }
        }
    </script>
    """
    
    # Находим закрывающий тег </head> и вставляем наш скрипт перед ним
    if '</head>' in html_content:
        html_content = html_content.replace('</head>', api_script + '</head>')
    else:
        # Если нет тега </head>, добавляем скрипт в начало
        html_content = api_script + html_content
    
    # Заменяем обработчики событий для кнопок
    button_handlers = """
    <script>
        // Обновляем список последних бэкапов
        async function updateRecentBackups() {
            try {
                const result = await ftpBackupAPI.getRecentBackups();
                if (result.status === 'success' && result.recent_files && result.recent_files.length > 0) {
                    const backupList = document.querySelector('.backup-list');
                    backupList.innerHTML = ''; // Очищаем список
                    
                    result.recent_files.forEach(file => {
                        const formattedTime = formatDateTime(file.last_backup_time);
                        
                        const backupItem = document.createElement('div');
                        backupItem.className = 'backup-item';
                        backupItem.innerHTML = `
                            <div class="backup-info">
                                <div class="backup-path">${file.path}</div>
                                <div class="backup-meta">
                                    <span><i class="fas fa-server"></i> ${file.site}</span>
                                    <span><i class="fas fa-clock"></i> ${formattedTime}</span>
                                </div>
                            </div>
                            <div class="backup-actions">
                                <button class="icon-btn" title="Compare" onclick="alert('Comparing backups is not implemented yet')">
                                    <i class="fas fa-exchange-alt"></i>
                                </button>
                                <button class="icon-btn" title="Open" onclick="alert('Opening file is not implemented yet')">
                                    <i class="fas fa-external-link-alt"></i>
                                </button>
                            </div>
                        `;
                        
                        backupList.appendChild(backupItem);
                    });
                } else {
                    console.error('No recent backups found or error:', result);
                    document.querySelector('.backup-list').innerHTML = '<div class="backup-item"><div class="backup-info">No recent backups found</div></div>';
                }
            } catch (error) {
                console.error('Error loading recent backups:', error);
                document.querySelector('.backup-list').innerHTML = '<div class="backup-item"><div class="backup-info">Error loading recent backups</div></div>';
            }
        }
        
        // После загрузки страницы
        document.addEventListener('DOMContentLoaded', async function() {
            // Загружаем текущий статус
            try {
                const statusData = await ftpBackupAPI.getStatus();
                if (statusData.status === 'success') {
                    if (statusData.current_task) {
                        document.querySelector('.task-badge').textContent = statusData.current_task;
                    }
                    if (statusData.current_server) {
                        document.querySelector('.server-badge').textContent = statusData.current_server;
                    }
                }
            } catch (error) {
                console.error('Error loading status:', error);
            }
            
            // Загружаем настройки
            try {
                const settingsData = await ftpBackupAPI.getSettings();
                if (settingsData.status === 'success') {
                    document.getElementById('backup-root').value = settingsData.backup_root;
                    document.getElementById('create-month-folder').checked = settingsData.create_month_folder;
                    document.getElementById('default-task-number').value = settingsData.default_task_number || '';
                }
            } catch (error) {
                console.error('Error loading settings:', error);
            }
            
            // Загружаем последние бэкапы
            updateRecentBackups();
            
            // Обработчики для кнопок
            document.getElementById('save-backup').addEventListener('click', async function() {
                try {
                    const result = await ftpBackupAPI.saveWithBackup();
                    if (result.status === 'success') {
                        alert('File saved with backup!');
                        // Обновляем список бэкапов после сохранения
                        setTimeout(updateRecentBackups, 500);
                    } else {
                        alert(`Error: ${result.message}`);
                    }
                } catch (error) {
                    console.error('Error saving with backup:', error);
                    alert('An error occurred while saving');
                }
            });
            
            document.getElementById('before-backup').addEventListener('click', async function() {
                try {
                    const result = await ftpBackupAPI.createBeforeBackup();
                    if (result.status === 'success') {
                        alert('Before backup created!');
                        // Обновляем список бэкапов
                        setTimeout(updateRecentBackups, 500);
                    } else {
                        alert(`Error: ${result.message}`);
                    }
                } catch (error) {
                    console.error('Error creating before backup:', error);
                    alert('An error occurred');
                }
            });
            
            document.getElementById('after-backup').addEventListener('click', async function() {
                try {
                    const result = await ftpBackupAPI.createAfterBackup();
                    if (result.status === 'success') {
                        alert('After backup created!');
                        // Обновляем список бэкапов
                        setTimeout(updateRecentBackups, 500);
                    } else {
                        alert(`Error: ${result.message}`);
                    }
                } catch (error) {
                    console.error('Error creating after backup:', error);
                    alert('An error occurred');
                }
            });
            
            document.getElementById('create-zip').addEventListener('click', async function() {
                try {
                    const result = await ftpBackupAPI.createZip();
                    alert(result.status === 'success' ? 'ZIP archive creation started!' : `Error: ${result.message}`);
                } catch (error) {
                    console.error('Error creating ZIP:', error);
                    alert('An error occurred');
                }
            });
            
            document.getElementById('open-folder').addEventListener('click', async function() {
                try {
                    await ftpBackupAPI.openFolder();
                    console.log('Opening backup folder...');
                } catch (error) {
                    console.error('Error opening folder:', error);
                }
            });
            
            document.getElementById('open-settings').addEventListener('click', function() {
                document.getElementById('settings-modal').style.display = 'flex';
            });
            
            // Сохранение настроек
            document.getElementById('save-settings').addEventListener('click', async function() {
                const backupRoot = document.getElementById('backup-root').value;
                const createMonthFolder = document.getElementById('create-month-folder').checked;
                const defaultTaskNumber = document.getElementById('default-task-number').value;
                
                if (!backupRoot) {
                    alert('Please enter a backup root path');
                    return;
                }
                
                try {
                    const result = await ftpBackupAPI.saveSettings({
                        backup_root: backupRoot,
                        create_month_folder: createMonthFolder,
                        default_task_number: defaultTaskNumber
                    });
                    
                    if (result.status === 'success') {
                        document.getElementById('settings-modal').style.display = 'none';
                        alert('Settings saved successfully!');
                        
                        // Если изменился номер задачи по умолчанию, обновляем отображение
                        if (defaultTaskNumber) {
                            document.querySelector('.task-badge').textContent = defaultTaskNumber;
                        }
                    } else {
                        alert(`Error: ${result.message}`);
                    }
                } catch (error) {
                    console.error('Error saving settings:', error);
                    alert('An error occurred while saving settings');
                }
            });
            
            // Обработчик смены задачи
            document.getElementById('save-task').addEventListener('click', async function() {
                const taskNumber = document.getElementById('task-number').value;
                if (taskNumber) {
                    try {
                        const result = await ftpBackupAPI.changeTask(taskNumber);
                        if (result.status === 'success') {
                            document.querySelector('.task-badge').textContent = taskNumber;
                            document.getElementById('task-modal').style.display = 'none';
                            alert('Task changed to: ' + taskNumber);
                        } else {
                            alert('Error: ' + result.message);
                        }
                    } catch (error) {
                        console.error('Error changing task:', error);
                        alert('An error occurred while changing task');
                    }
                } else {
                    alert('Please enter a task number');
                }
            });
            
            // Открытие модального окна задачи
            document.getElementById('change-task').addEventListener('click', function() {
                document.getElementById('task-modal').style.display = 'flex';
            });
            
            // Закрытие модальных окон
            document.querySelectorAll('.close-modal, #cancel-settings, #cancel-task').forEach(function(element) {
                element.addEventListener('click', function() {
                    document.getElementById('settings-modal').style.display = 'none';
                    document.getElementById('task-modal').style.display = 'none';
                });
            });
        });
    </script>
    """
    
    # Находим закрывающий тег </body> и вставляем наши обработчики перед ним
    if '</body>' in html_content:
        html_content = html_content.replace('</body>', button_handlers + '</body>')
    else:
        # Если нет тега </body>, добавляем обработчики в конец
        html_content = html_content + button_handlers
    
    return html_content

class FtpBackupInterfaceCommand(sublime_plugin.WindowCommand):
    def run(self):
        """
        Эта команда теперь запускает нативный интерфейс FTP Backup
        вместо открытия веб-интерфейса в браузере
        """
        try:
            # Вызываем новый нативный интерфейс
            self.window.run_command("ftp_backup_ui")
            sublime.status_message("FTP Backup: Открыт интерфейс")
            
        except Exception as e:
            sublime.error_message(f"FTP Backup: Ошибка при открытии интерфейса: {str(e)}")
            print(f"FTP Backup ERROR: {str(e)}")

class EventListener(sublime_plugin.EventListener):
    def on_exit(self):
        # Останавливаем HTTP-сервер при выходе из Sublime Text
        stop_http_server()