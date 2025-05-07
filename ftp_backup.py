import os
import shutil
import json
import zipfile
from datetime import datetime
import socket
import re
import traceback
import logging
import sublime
import sublime_plugin
import urllib.parse
import time

# Глобальные переменные для хранения текущего номера задачи и текущего сервера
CURRENT_TASK_NUMBER = None
CURRENT_SERVER = None

class FtpBackupLogger:
    def __init__(self, backup_root):
        """Настройка логирования"""
        log_dir = os.path.join(backup_root, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, 'ftp_backup.log')
        logging.basicConfig(
            filename=log_file, 
            level=logging.DEBUG, 
            format='%(asctime)s - %(levelname)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger('FtpBackup')

    def debug(self, message):
        """Отладочное сообщение"""
        print(f"[FTP Backup Debug] {message}")
        self.logger.debug(message)

    def error(self, message):
        """Сообщение об ошибке"""
        print(f"[FTP Backup ERROR] {message}")
        self.logger.error(message)
        self.logger.error(traceback.format_exc())

class FtpBackupManager:
    def __init__(self, backup_root=None):
        # Если не указан backup_root, пытаемся загрузить из настроек
        if backup_root is None:
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            if not backup_root:
                # Если настройки пусты, используем значение по умолчанию
                backup_root = os.path.join(os.path.expanduser("~"), "Desktop", "BackUp")
                
        self.backup_root = backup_root
        self.server_backup_map = {}
        self.config_path = os.path.join(backup_root, 'backup_config.json')
        
        # Путь к файлу сопоставления папок сайтов
        self.folder_mapping_path = os.path.join(backup_root, 'folder_mapping.json')
        
        self.logger = FtpBackupLogger(backup_root)
        self.project_roots = [
            'var\\www\\',
            'www\\',
            'public_html\\',
            'local\\',
            'htdocs\\',
            'home\\'
        ]
        
        os.makedirs(backup_root, exist_ok=True)
        self._load_config()
        self._load_folder_mapping()
        
        self.logger.debug(f"Инициализация FtpBackupManager. Корневая папка: {backup_root}")

    def _load_config(self):
        """Загрузка конфигурации бэкапов с расширенной отладкой"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.server_backup_map = json.load(f)
                self.logger.debug(f"Конфигурация загружена: {len(self.server_backup_map)} записей")
            else:
                self.logger.debug("Файл конфигурации не найден. Будет создан новый.")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки конфигурации: {e}")

    def _load_folder_mapping(self):
        """Загрузка сопоставления имен папок с их оригинальными именами сайтов"""
        try:
            if os.path.exists(self.folder_mapping_path):
                with open(self.folder_mapping_path, 'r', encoding='utf-8') as f:
                    self.folder_mapping = json.load(f)
                self.logger.debug(f"Сопоставление папок загружено: {len(self.folder_mapping)} записей")
            else:
                self.folder_mapping = {}
                self.logger.debug("Файл сопоставления папок не найден. Будет создан новый.")
        except Exception as e:
            self.logger.error(f"Ошибка загрузки сопоставления папок: {e}")
            self.folder_mapping = {}
    
    def _save_folder_mapping(self):
        """Сохранение сопоставления папок"""
        try:
            with open(self.folder_mapping_path, 'w', encoding='utf-8') as f:
                json.dump(self.folder_mapping, f, indent=4, ensure_ascii=False)
            self.logger.debug(f"Сопоставление папок сохранено: {len(self.folder_mapping)} записей")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения сопоставления папок: {e}")

    def _detect_renamed_folders(self):
        """
        Обнаруживает переименованные папки и обновляет сопоставление
        со строгой проверкой соответствия имен
        """
        try:
            # Получаем список существующих папок
            existing_folders = []
            for name in os.listdir(self.backup_root):
                path = os.path.join(self.backup_root, name)
                if os.path.isdir(path) and name not in ["logs"]:
                    existing_folders.append(name)
            
            # Проверяем каждое сопоставление
            for site_name, folder_name in list(self.folder_mapping.items()):
                if folder_name not in existing_folders:
                    self.logger.debug(f"Папка {folder_name} для сайта {site_name} не найдена, ищем переименованную")
                    
                    # Создаем безопасное имя сайта для сравнения
                    safe_site_name = re.sub(r'[^\w\-_.]', '_', site_name)
                    
                    # Проверяем все существующие папки для поиска переименованной
                    for existing_folder in existing_folders:
                        # Пропускаем папки, которые уже назначены другим сайтам
                        if existing_folder in self.folder_mapping.values():
                            continue
                        
                        # Строгая проверка соответствия имени
                        # Сравнение должно учитывать суффиксы, чтобы не путать похожие, но разные сайты
                        # Например, kulakov-wp-loc-3.dev-z.ru и kualkov-bitrix-loc-3.dev-z.ru
                        similarity = self._calculate_name_similarity(folder_name, existing_folder)
                        
                        # Считаем папки идентичными только при очень высоком сходстве
                        if similarity > 0.9:  # Требуем очень высокую степень сходства
                            # Проверяем характерные особенности папки сайта
                            folder_path = os.path.join(self.backup_root, existing_folder)
                            
                            # Ищем месячные подпапки как признак папки бэкапов сайта
                            month_pattern = re.compile(r'^(January|February|March|April|May|June|July|August|September|October|November|December) \d{4}$')
                            has_month_folders = False
                            try:
                                for item in os.listdir(folder_path):
                                    if os.path.isdir(os.path.join(folder_path, item)) and month_pattern.match(item):
                                        has_month_folders = True
                                        break
                            except:
                                continue
                            
                            if has_month_folders:
                                # Обнаружена переименованная папка
                                self.logger.debug(f"Обнаружена переименованная папка: {folder_name} -> {existing_folder} для сайта {site_name}")
                                
                                # Обновляем сопоставление
                                self.folder_mapping[site_name] = existing_folder
                                self._save_folder_mapping()
                                break
        
        except Exception as e:
            self.logger.error(f"Ошибка при обнаружении переименованных папок: {e}")

    def _calculate_name_similarity(self, name1, name2):
        """
        Вычисляет степень сходства между двумя именами папок
        Возвращает значение от 0.0 (полностью разные) до 1.0 (идентичные)
        """
        # Нормализуем имена - приводим к нижнему регистру и заменяем подчеркивания и тире на точки
        name1 = name1.lower().replace('_', '.').replace('-', '.')
        name2 = name2.lower().replace('_', '.').replace('-', '.')
        
        # Если имена идентичны после нормализации, возвращаем 1.0
        if name1 == name2:
            return 1.0
        
        # Разбиваем имена на части по точкам для более точного сравнения
        parts1 = name1.split('.')
        parts2 = name2.split('.')
        
        # Если разное количество частей - сайты, скорее всего, разные
        if len(parts1) != len(parts2):
            return 0.5
        
        # Считаем совпадающие части
        matching_parts = sum(1 for p1, p2 in zip(parts1, parts2) if p1 == p2)
        similarity = matching_parts / max(len(parts1), len(parts2))
        
        return similarity


    def _extract_relative_path(self, file_path):
        """
        Извлечение относительного пути файла с максимальной отладкой
        """
        self.logger.debug(f"Извлечение пути для: {file_path}")
        normalized_path = file_path.replace('/', '\\')
        for root in self.project_roots:
            if root in normalized_path:
                relative_path = normalized_path.split(root, 1)[1]
                result = relative_path.replace('\\', '/')
                self.logger.debug(f"Извлечен путь через корневую папку {root}: {result}")
                return result
        try:
            temp_match = re.search(r'Temp\\[^\\]+\\(.+)', normalized_path)
            if temp_match:
                result = temp_match.group(1).replace('\\', '/')
                self.logger.debug(f"Извлечен путь из временной папки: {result}")
                return result
        except Exception as e:
            self.logger.error(f"Ошибка извлечения из временной папки: {e}")
        
        result = os.path.basename(file_path)
        self.logger.debug(f"Использовано имя файла: {result}")
        return result

    def extract_site_name(self, file_path, prompt_if_failed=True):
        """
        Извлечение имени сайта из пути к файлу.
        Теперь всегда запрашивает имя проекта у пользователя.
        """
        try:
            # Проверяем, есть ли уже сохраненное имя сайта для этого пути
            saved_site = self._check_site_name_mapping(file_path)
            if saved_site:
                self.logger.debug(f"Используется сохраненное имя проекта: {saved_site}")
                return saved_site
            
            # Пытаемся извлечь имя сайта из пути для предложения пользователю
            suggested_name = None
            normalized_path = file_path.replace('/', '\\')
            patterns = [
                r'(?:var\\www\\|www\\|public_html\\|local\\|htdocs\\|home\\)([^\\]+)',
                r'ftp://([^/]+)',
                r'\\([^\\]+)\\(?:www|public_html|httpdocs)\\',
            ]

            # Пытаемся извлечь имя сайта из пути
            for pattern in patterns:
                match = re.search(pattern, normalized_path)
                if match:
                    suggested_name = match.group(1)
                    self.logger.debug(f"Предполагаемое имя проекта: {suggested_name} из пути {file_path}")
                    break

            if not suggested_name:
                parts = normalized_path.split('\\')
                for i, part in enumerate(parts):
                    if part.lower() in ['www', 'public_html', 'httpdocs', 'htdocs'] and i > 0:
                        suggested_name = parts[i-1]
                        self.logger.debug(f"Предполагаемое имя проекта из структуры пути: {suggested_name}")
                        break

                if not suggested_name:
                    for part in parts:
                        if '.' in part and not part.endswith(('.php', '.html', '.js', '.css')):
                            suggested_name = part
                            self.logger.debug(f"Предполагаемое имя проекта с точкой как домен: {suggested_name}")
                            break

            # Запоминаем текущее окно для корректного вызова команды
            window = sublime.active_window()

            # Создаем переменную, в которую сохраним результат ввода
            global SITE_NAME_INPUT
            SITE_NAME_INPUT = None

            # Показываем диалог для ввода имени проекта с предложенным именем, если оно есть
            prompt_text = "Введите название проекта:"
            default_value = suggested_name if suggested_name else ""
            
            window.show_input_panel(
                prompt_text,
                default_value,
                self._on_site_name_entered,
                None,
                None
            )

            # Ожидаем ввод
            max_wait = 30  # максимальное время ожидания в секундах
            wait_interval = 0.1
            waited = 0

            while SITE_NAME_INPUT is None and waited < max_wait:
                time.sleep(wait_interval)
                waited += wait_interval

            if SITE_NAME_INPUT:
                # Сохраняем имя проекта для дальнейшего использования
                self._save_site_name_mapping(file_path, SITE_NAME_INPUT)
                return SITE_NAME_INPUT

            # Если пользователь не ввел имя, используем имя хоста
            hostname = socket.gethostname()
            self.logger.debug(f"Пользователь не ввел имя проекта, используется имя хоста: {hostname}")
            return hostname

        except Exception as e:
            self.logger.error(f"Ошибка при вводе имени проекта: {e}")
            return "unknown_site"

    def _on_site_name_entered(self, site_name):
        """Обработчик ввода имени сайта"""
        global SITE_NAME_INPUT
        if site_name:
            SITE_NAME_INPUT = site_name
            self.logger.debug(f"Пользователь указал имя сайта: {site_name}")
        else:
            SITE_NAME_INPUT = "unknown_site"
            self.logger.debug("Пользователь не указал имя сайта, используется значение по умолчанию")

    def _save_site_name_mapping(self, file_path, site_name):
        """Сохраняет соответствие между путем к файлу и именем сайта"""
        try:
            # Загружаем существующие маппинги
            mapping_path = os.path.join(self.backup_root, 'site_name_mapping.json')

            if os.path.exists(mapping_path):
                with open(mapping_path, 'r', encoding='utf-8') as f:
                    mappings = json.load(f)
            else:
                mappings = {}

            # Определяем корневой путь проекта
            project_root = self._extract_project_root(file_path)

            if project_root:
                # Сохраняем соответствие между корневым путем проекта и именем сайта
                mappings[project_root] = site_name

                with open(mapping_path, 'w', encoding='utf-8') as f:
                    json.dump(mappings, f, indent=4, ensure_ascii=False)

                self.logger.debug(f"Сохранено соответствие: {project_root} -> {site_name}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения соответствия имени сайта: {e}")

    def _extract_project_root(self, file_path):
        """Извлекает корневой путь проекта из пути к файлу"""
        try:
            normalized_path = file_path.replace('/', '\\')

            # Пытаемся найти корневую папку проекта
            for root in self.project_roots:
                if root in normalized_path:
                    parts = normalized_path.split(root)
                    if len(parts) > 1:
                        return parts[0] + root

            return None
        except Exception as e:
            self.logger.error(f"Ошибка извлечения корневого пути проекта: {e}")
            return None

    def _check_site_name_mapping(self, file_path):
        """Проверяет, есть ли уже сохраненное имя сайта для данного пути"""
        try:
            mapping_path = os.path.join(self.backup_root, 'site_name_mapping.json')

            if not os.path.exists(mapping_path):
                return None

            with open(mapping_path, 'r', encoding='utf-8') as f:
                mappings = json.load(f)

            # Ищем соответствие для пути к файлу
            project_root = self._extract_project_root(file_path)

            if project_root and project_root in mappings:
                site_name = mappings[project_root]
                self.logger.debug(f"Найдено сохраненное имя сайта: {site_name} для пути {project_root}")
                return site_name

            return None
        except Exception as e:
            self.logger.error(f"Ошибка проверки соответствия имени сайта: {e}")
            return None

    def backup_file(self, file_path, server_name=None, mode=None, task_number=None):
        """
        Создание бэкапа с указанием имени проекта и номера задачи
        mode: None (автоматический), 'before', 'after'
        task_number: Номер задачи (опционально)
        server_name: Имя проекта (опционально)
        """
        try:
            excluded_files = [
                'default.sublime-commands', 
                '.sublime-commands', 
                '.DS_Store',  
                'Thumbs.db'  
            ]
            
            if (os.path.basename(file_path) in excluded_files or 
                any(ext in file_path for ext in excluded_files)):
                self.logger.debug(f"Файл {file_path} исключен из бэкапа")
                return None, None, None

            if not os.path.exists(file_path):
                self.logger.error(f"Файл не существует: {file_path}")
                return None, None, None
            
            # Обнаруживаем переименованные папки и обновляем сопоставление
            self._detect_renamed_folders()
            
            # Получаем имя проекта из параметра или из сохраненного соответствия
            site_name = server_name
            if not site_name:
                saved_site = self._check_site_name_mapping(file_path)
                if saved_site:
                    site_name = saved_site
                else:
                    # Если нет ни параметра, ни сохраненного соответствия, используем имя хоста
                    site_name = socket.gethostname()
            
            # Создаем ключ папки сайта из имени сайта
            default_key = re.sub(r'[^\w\-_.]', '_', site_name)
            
            # Проверяем, есть ли сопоставление с папкой
            server_key = default_key
            if site_name in self.folder_mapping:
                server_key = self.folder_mapping[site_name]
                self.logger.debug(f"Используется сопоставленная папка {server_key} для проекта {site_name}")
            else:
                # Проверяем, нет ли уже папки с таким именем
                if os.path.exists(os.path.join(self.backup_root, default_key)):
                    # Используем существующую папку
                    server_key = default_key
                else:
                    # Создаем новую папку и проверяем, что имя уникально
                    index = 1
                    while os.path.exists(os.path.join(self.backup_root, server_key)):
                        server_key = f"{default_key}_{index}"
                        index += 1
                
                # Добавляем новое сопоставление
                self.folder_mapping[site_name] = server_key
                self._save_folder_mapping()
                self.logger.debug(f"Создано новое сопоставление проект {site_name} -> папка {server_key}")
            
            self.logger.debug(f"Проект: {site_name}, Ключ проекта: {server_key}")

      
       
            current_month_year = datetime.now().strftime("%B %Y")
            server_folder = os.path.join(self.backup_root, server_key)
            if not os.path.exists(server_folder):
                os.makedirs(server_folder, exist_ok=True)
                self.logger.debug(f"Создана новая папка для сайта: {server_key}")
            else:
                self.logger.debug(f"Используется существующая папка для сайта: {server_key}")
            
            # Проверяем настройки создания месячных папок
            create_month_folder = True
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            if settings.has('create_month_folder'):
                create_month_folder = settings.get('create_month_folder')
            
            if create_month_folder:
                month_year_folder = os.path.join(server_folder, current_month_year)
                if not os.path.exists(month_year_folder):
                    os.makedirs(month_year_folder, exist_ok=True)
                    self.logger.debug(f"Создана новая папка для месяца: {current_month_year}")
                else:
                    self.logger.debug(f"Используется существующая папка для месяца: {current_month_year}")
            else:
                # Если не используем месячные папки, используем корневую папку сайта
                month_year_folder = server_folder
                self.logger.debug("Создание месячных папок отключено, используется корневая папка сайта")
            
            # Добавляем папку с номером задачи, если указан
            if task_number:
               task_folder = os.path.join(month_year_folder, task_number)
               self.logger.debug(f"Используется папка задачи: {task_number}")
            else:
                task_folder = month_year_folder
                self.logger.debug("Используется папка без номера задачи")
            
            if not os.path.exists(task_folder):
                os.makedirs(task_folder, exist_ok=True)
            
            before_path = os.path.join(task_folder, 'before')
            after_path = os.path.join(task_folder, 'after')

            os.makedirs(before_path, exist_ok=True)
            os.makedirs(after_path, exist_ok=True)
            
            relative_path = self._extract_relative_path(file_path)
            
            self.logger.debug(f"Относительный путь: {relative_path}")

            if mode == 'before':
                backup_path = os.path.join(before_path, relative_path)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                shutil.copy2(file_path, backup_path)
                self.logger.debug(f"Создан принудительный 'before' бэкап в {backup_path}")
                
                if relative_path not in self.server_backup_map:
                    self.server_backup_map[relative_path] = {
                        'first_backup_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'site': site_name,
                        'backup_dir': os.path.dirname(backup_path)
                    }
            
            elif mode == 'after':
                backup_path = os.path.join(after_path, relative_path)
                os.makedirs(os.path.dirname(backup_path), exist_ok=True)
                
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                
                shutil.copy2(file_path, backup_path)
                self.logger.debug(f"Создан принудительный 'after' бэкап в {backup_path}")
                
                # Обновляем информацию о директории бэкапа в мапе
                if relative_path in self.server_backup_map:
                    self.server_backup_map[relative_path]['backup_dir'] = os.path.dirname(backup_path)
            
            else:
                first_backup_path = os.path.join(before_path, relative_path)
                after_backup_path = os.path.join(after_path, relative_path)
                
                os.makedirs(os.path.dirname(first_backup_path), exist_ok=True)
                os.makedirs(os.path.dirname(after_backup_path), exist_ok=True)

                if relative_path not in self.server_backup_map:
                    shutil.copy2(file_path, first_backup_path)
                    
                    self.server_backup_map[relative_path] = {
                        'first_backup_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'site': site_name,
                        'backup_dir': os.path.dirname(first_backup_path)
                    }

                if os.path.exists(after_backup_path):
                    os.remove(after_backup_path)
                
                shutil.copy2(file_path, after_backup_path)
                
                # Обновляем информацию о директории бэкапа в мапе
                if relative_path in self.server_backup_map:
                    self.server_backup_map[relative_path]['backup_dir'] = os.path.dirname(after_backup_path)

            if relative_path in self.server_backup_map:
                self.server_backup_map[relative_path]['last_backup_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.server_backup_map[relative_path]['site'] = site_name
            
            self._save_config()
            
            # Возвращаем имя сайта для проверки смены сервера
            return before_path, after_path, site_name

        except Exception as e:
            self.logger.error(f"Критическая ошибка бэкапа: {e}")
            sublime.status_message(f"FTP Backup ERROR: {e}")
            return None, None, None

    def _save_config(self):
        """Сохранение конфигурации с расширенной отладкой"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.server_backup_map, f, indent=4, ensure_ascii=False)
            self.logger.debug(f"Конфигурация сохранена: {len(self.server_backup_map)} записей")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения конфигурации: {e}")

    def create_backup_zip(self, folder_path, folder_type=None):
        """
        Создание ZIP-архива указанной папки бэкапа
        folder_path: путь к папке с бэкапами
        folder_type: 'before', 'after' или None (полная папка)
        """
        try:
            if not os.path.exists(folder_path):
                self.logger.error(f"Папка для архивации не существует: {folder_path}")
                return None
            
            # Приводим путь к стандартному виду
            folder_path = os.path.normpath(folder_path)
            
            # Извлекаем имя сайта безопасным способом
            folder_parts = folder_path.split(os.sep)
            # Удаляем пустые элементы
            folder_parts = [part for part in folder_parts if part]
            
            # Находим имя сайта - ищем часть после корневой папки бэкапов
            site_name = "backup"  # значение по умолчанию
            
            # Ищем в пути индекс корневой директории бэкапов
            backup_root_parts = os.path.normpath(self.backup_root).split(os.sep)
            backup_root_parts = [part for part in backup_root_parts if part]
            
            # Находим индекс корневого каталога BackUp в пути
            root_index = -1
            for i, part in enumerate(folder_parts):
                if i < len(folder_parts) - 1 and part == backup_root_parts[-1]:
                    root_index = i
                    break
            
            # Если нашли корневой каталог, то следующий элемент должен быть именем сайта
            if root_index >= 0 and root_index + 1 < len(folder_parts):
                site_name = folder_parts[root_index + 1]
                self.logger.debug(f"Извлечено имя сайта из пути: {site_name}")
                
                # Проверяем, есть ли сопоставление с реальным именем сайта в folder_mapping
                for real_site_name, folder_key in self.folder_mapping.items():
                    if folder_key == site_name:
                        site_name = real_site_name
                        self.logger.debug(f"Найдено соответствие с реальным именем сайта: {site_name}")
                        break
            
            # Формируем дату и время для имени файла
            date_str = datetime.now().strftime("%d.%m.%Y.%H.%M")
            
            # Формируем имя ZIP архива
            if folder_type:
                zip_name = f"backup_{site_name}_{folder_type}_{date_str}.zip"
            else:
                zip_name = f"backup_{site_name}_{date_str}.zip"
            
            # Определяем папку задачи (task_xxx) или использовать исходную директорию
            zip_dir = folder_path
            
            # Проверяем, может ли текущая папка быть 'before' или 'after' внутри задачи
            current_folder = os.path.basename(folder_path)
            if current_folder in ['before', 'after']:
                # Поднимаемся на уровень выше - к папке задачи
                zip_dir = os.path.dirname(folder_path)
                self.logger.debug(f"Обнаружена папка {current_folder}, поднимаемся к папке задачи: {zip_dir}")
            
            # Ищем, содержит ли путь папку задачи
            task_folder = None
            for i, part in enumerate(folder_parts):
                if part.startswith('task_') or re.match(r'task_[\w-]+', part):
                    # Определяем полный путь до папки задачи
                    task_index = i
                    
                    # Собираем путь до папки задачи включительно
                    if ':' in folder_path:  # Windows путь
                        drive = folder_path.split(':')[0] + ':'
                        path_parts = folder_parts[:task_index+1]
                        task_folder = os.path.join(drive, os.sep, *path_parts)
                    else:  # Unix путь
                        path_parts = folder_parts[:task_index+1]
                        task_folder = os.path.join(os.sep, *path_parts)
                    
                    self.logger.debug(f"Найдена папка задачи: {task_folder}")
                    break
            
            # Если нашли папку задачи, используем её
            if task_folder:
                zip_dir = task_folder
                self.logger.debug(f"Установлена папка задачи для ZIP: {zip_dir}")
            
            # Формируем полный путь к ZIP
            zip_path = os.path.join(zip_dir, zip_name)
            
            # Убеждаемся, что директория существует
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)
            
            self.logger.debug(f"Создание архива в папке задачи: {zip_path}")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
                        self.logger.debug(f"Добавлен файл {arcname}")
            
            self.logger.debug(f"Архив успешно создан: {zip_path}")
            
            return zip_path
            
        except Exception as e:
            self.logger.error(f"Ошибка создания архива: {e}")
            return None

class SaveCommand(sublime_plugin.TextCommand):
    """Перекрытие стандартной команды save"""
    def run(self, edit, **kwargs):
        sublime.status_message("⛔ Используйте Ctrl+Shift+R для сохранения с бэкапом")
        
class SaveAsCommand(sublime_plugin.TextCommand):
    """Перекрытие стандартной команды save_as"""
    def run(self, edit, **kwargs):
        sublime.status_message("⛔ Используйте Ctrl+Shift+R для сохранения с бэкапом")

class PromptSaveAsCommand(sublime_plugin.TextCommand):
    """Перекрытие стандартной команды prompt_save_as"""
    def run(self, edit, **kwargs):
        sublime.status_message("⛔ Используйте Ctrl+Shift+R для сохранения с бэкапом")

class FtpBackupSaveCommand(sublime_plugin.TextCommand):
    """Команда для сохранения с бэкапом по Ctrl+Shift+R"""
    def run(self, edit):
        file_path = self.view.file_name()
        
        if not file_path:
            sublime.status_message("Сначала сохраните файл с указанием имени")
            self.view.window().run_command("save_as")
            return
        
        # Загружаем настройки
        settings = sublime.load_settings('ftp_backup.sublime-settings')
        backup_root = settings.get('backup_root')
        if not backup_root:
            # Если нет настроек, показываем диалог для выбора папки
            self.view.window().run_command("ftp_backup_browse_folder")
            return
            
        self.backup_manager = FtpBackupManager(backup_root)
        self.file_path = file_path
        
        # Проверяем, есть ли уже сохраненное имя проекта
        saved_site = self.backup_manager._check_site_name_mapping(file_path)
        if saved_site:
            self.backup_manager.logger.debug(f"Используется сохраненное имя проекта: {saved_site}")
            self.on_project_name_entered(saved_site)
        else:
            # Пытаемся найти предполагаемое имя проекта
            suggested_name = self.get_suggested_project_name(file_path)
            
            # Запрашиваем у пользователя имя проекта
            self.view.window().show_input_panel(
                "Введите название проекта:", 
                suggested_name if suggested_name else "", 
                self.on_project_name_entered, 
                None, 
                None
            )
    
    def get_suggested_project_name(self, file_path):
        """Пытается определить имя проекта из пути к файлу"""
        try:
            normalized_path = file_path.replace('/', '\\')
            patterns = [
                r'(?:var\\www\\|www\\|public_html\\|local\\|htdocs\\|home\\)([^\\]+)',
                r'ftp://([^/]+)',
                r'\\([^\\]+)\\(?:www|public_html|httpdocs)\\',
            ]

            for pattern in patterns:
                match = re.search(pattern, normalized_path)
                if match:
                    return match.group(1)

            parts = normalized_path.split('\\')
            for i, part in enumerate(parts):
                if part.lower() in ['www', 'public_html', 'httpdocs', 'htdocs'] and i > 0:
                    return parts[i-1]

            for part in parts:
                if '.' in part and not part.endswith(('.php', '.html', '.js', '.css')):
                    return part
                    
            return None
        except Exception as e:
            print(f"Ошибка при определении имени проекта: {e}")
            return None
    
    def on_project_name_entered(self, project_name):
        """Обработчик ввода имени проекта"""
        global CURRENT_SERVER
        
        if not project_name:
            project_name = socket.gethostname()
            print(f"Пользователь не ввел имя проекта, используется имя хоста: {project_name}")
        
        # Сохраняем имя проекта
        self.backup_manager._save_site_name_mapping(self.file_path, project_name)
        CURRENT_SERVER = project_name
        
        # Теперь запрашиваем номер задачи
        global CURRENT_TASK_NUMBER
        if CURRENT_TASK_NUMBER:
            self.on_task_number_entered(CURRENT_TASK_NUMBER)
        else:
            self.view.window().show_input_panel(
                "Введите название папки задачи:", 
                "", 
                self.on_task_number_entered, 
                None, 
                None
            )
    
    def on_task_number_entered(self, task_number):
        """Обработчик ввода номера задачи"""
        # Обработка пустого ввода
        task_number = task_number.strip() if task_number else None
        
        # Сохраняем номер задачи глобально
        global CURRENT_TASK_NUMBER
        CURRENT_TASK_NUMBER = task_number
        
        try:
            global CURRENT_SERVER
            
            # Создаем бэкап "до"
            before_path, _, _ = self.backup_manager.backup_file(
                self.file_path, 
                server_name=CURRENT_SERVER,
                mode='before', 
                task_number=task_number
            )
            
            # Сохраняем содержимое файла
            content = self.view.substr(sublime.Region(0, self.view.size()))
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Создаем бэкап "после"
            self.backup_manager.backup_file(
                self.file_path, 
                server_name=CURRENT_SERVER,
                mode='after', 
                task_number=task_number
            )
            
            # Обновляем статусы в редакторе
            self.view.set_scratch(True)
            self.view.set_scratch(False)
            
            task_info = f" (задача #{task_number})" if task_number else ""
            sublime.status_message(f"✅ Файл успешно сохранен с бэкапом{task_info}: {os.path.basename(self.file_path)}")
        
        except Exception as e:
            sublime.error_message(f"❌ Ошибка сохранения с бэкапом: {str(e)}")
    
    def get_suggested_project_name(self, file_path):
        """Пытается определить имя проекта из пути к файлу"""
        try:
            normalized_path = file_path.replace('/', '\\')
            patterns = [
                r'(?:var\\www\\|www\\|public_html\\|local\\|htdocs\\|home\\)([^\\]+)',
                r'ftp://([^/]+)',
                r'\\([^\\]+)\\(?:www|public_html|httpdocs)\\',
            ]

            for pattern in patterns:
                match = re.search(pattern, normalized_path)
                if match:
                    return match.group(1)

            parts = normalized_path.split('\\')
            for i, part in enumerate(parts):
                if part.lower() in ['www', 'public_html', 'httpdocs', 'htdocs'] and i > 0:
                    return parts[i-1]

            for part in parts:
                if '.' in part and not part.endswith(('.php', '.html', '.js', '.css')):
                    return part
                    
            return None
        except Exception as e:
            self.backup_manager.logger.error(f"Ошибка при определении имени проекта: {e}")
            return None
    
    def on_project_name_entered(self, project_name):
        """Обработчик ввода имени проекта"""
        global CURRENT_SERVER
        
        if not project_name:
            project_name = socket.gethostname()
            self.backup_manager.logger.debug(f"Пользователь не ввел имя проекта, используется имя хоста: {project_name}")
        
        # Сохраняем имя проекта
        self.backup_manager._save_site_name_mapping(self.file_path, project_name)
        CURRENT_SERVER = project_name
        
        # Теперь запрашиваем номер задачи
        global CURRENT_TASK_NUMBER
        if CURRENT_TASK_NUMBER:
            self.on_task_number_entered(CURRENT_TASK_NUMBER)
        else:
            self.view.window().show_input_panel(
                "Введите название папки задачи:", 
                "", 
                self.on_task_number_entered, 
                None, 
                None
            )
    
    def on_task_number_entered(self, task_number):
        """Обработчик ввода номера задачи"""
        # Обработка пустого ввода
        task_number = task_number.strip() if task_number else None
        
        # Сохраняем номер задачи глобально
        global CURRENT_TASK_NUMBER
        CURRENT_TASK_NUMBER = task_number
        
        try:
            global CURRENT_SERVER
            
            # Создаем бэкап "до"
            before_path, _, _ = self.backup_manager.backup_file(
                self.file_path, 
                server_name=CURRENT_SERVER,
                mode='before', 
                task_number=task_number
            )
            
            # Сохраняем содержимое файла
            content = self.view.substr(sublime.Region(0, self.view.size()))
            with open(self.file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Создаем бэкап "после"
            self.backup_manager.backup_file(
                self.file_path, 
                server_name=CURRENT_SERVER,
                mode='after', 
                task_number=task_number
            )
            
            # Обновляем статусы в редакторе
            self.view.set_scratch(True)
            self.view.set_scratch(False)
            
            task_info = f" (задача #{task_number})" if task_number else ""
            sublime.status_message(f"✅ Файл успешно сохранен с бэкапом{task_info}: {os.path.basename(self.file_path)}")
        
        except Exception as e:
            sublime.error_message(f"❌ Ошибка сохранения с бэкапом: {str(e)}")
    
    def save_with_backup(self, file_path, task_number):
        try:
            # Обработка пустого ввода
            task_number = task_number.strip() if task_number else None
            
            # Сохраняем номер задачи глобально
            global CURRENT_TASK_NUMBER
            CURRENT_TASK_NUMBER = task_number
            
            # Загружаем путь к директории бэкапов из настроек
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            backup_manager = FtpBackupManager(backup_root)
        
            before_path, after_path, _ = backup_manager.backup_file(file_path, mode='before', task_number=task_number)
            content = self.view.substr(sublime.Region(0, self.view.size()))
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            backup_manager.backup_file(file_path, mode='after', task_number=task_number)
            self.view.set_scratch(True)
            self.view.set_scratch(False)
            
            task_info = f" (задача #{task_number})" if task_number else ""
            sublime.status_message(f"✅ Файл успешно сохранен с бэкапом{task_info}: {os.path.basename(file_path)}")
        
        except Exception as e:
            sublime.error_message(f"❌ Ошибка сохранения с бэкапом: {str(e)}")

class BlockStandardSaveListener(sublime_plugin.EventListener):
    def on_text_command(self, view, command_name, args):
        """Перехват стандартных команд сохранения"""
        blocked_commands = ["save", "save_all", "prompt_save_as", "save_as", "save_all_with_new_window"]
        
        if command_name in blocked_commands:
            sublime.status_message("⛔ Используйте Ctrl+Shift+R для сохранения с бэкапом")
            return ("noop", None) 
        
        return None

    def on_pre_save(self, view):
        """Заблокировать любые прямые сохранения"""
        pass

    def on_post_save(self, view):
        """Заблокировать любые постобработки сохранения"""
        pass

    def on_query_context(self, view, key, operator, operand, match_all):
        """Перехватываем контекстные запросы для блокировки сохранения"""
        if key == "save_available":
            return False

class FtpBackupCreateBeforeCommand(sublime_plugin.TextCommand):
    def run(self, edit, file_path=None):
        """Создание принудительного 'before' бэкапа"""
        if file_path is None:
            file_path = self.view.file_name()
        
        if not file_path:
            sublime.status_message("FTP Backup: Нет открытого файла")
            return
        
        # Загружаем настройки
        settings = sublime.load_settings('ftp_backup.sublime-settings')
        backup_root = settings.get('backup_root')
        if not backup_root:
            sublime.status_message("FTP Backup: Не указана папка для бэкапов")
            self.view.window().run_command("ftp_backup_browse_folder")
            return
            
        self.backup_manager = FtpBackupManager(backup_root)
        self.file_path = file_path
        
        # Проверяем, есть ли уже сохраненное имя проекта
        saved_site = self.backup_manager._check_site_name_mapping(file_path)
        if saved_site:
            self.backup_manager.logger.debug(f"Используется сохраненное имя проекта: {saved_site}")
            self.on_project_name_entered(saved_site)
        else:
            # Пытаемся найти предполагаемое имя проекта
            suggested_name = self.get_suggested_project_name(file_path)
            
            # Запрашиваем у пользователя имя проекта
            self.view.window().show_input_panel(
                "Введите название проекта:", 
                suggested_name if suggested_name else "", 
                self.on_project_name_entered, 
                None, 
                None
            )
    
    def get_suggested_project_name(self, file_path):
        """Пытается определить имя проекта из пути к файлу"""
        try:
            normalized_path = file_path.replace('/', '\\')
            patterns = [
                r'(?:var\\www\\|www\\|public_html\\|local\\|htdocs\\|home\\)([^\\]+)',
                r'ftp://([^/]+)',
                r'\\([^\\]+)\\(?:www|public_html|httpdocs)\\',
            ]

            for pattern in patterns:
                match = re.search(pattern, normalized_path)
                if match:
                    return match.group(1)

            parts = normalized_path.split('\\')
            for i, part in enumerate(parts):
                if part.lower() in ['www', 'public_html', 'httpdocs', 'htdocs'] and i > 0:
                    return parts[i-1]

            for part in parts:
                if '.' in part and not part.endswith(('.php', '.html', '.js', '.css')):
                    return part
                    
            return None
        except Exception as e:
            print(f"Ошибка при определении имени проекта: {e}")
            return None
    
    def on_project_name_entered(self, project_name):
        """Обработчик ввода имени проекта"""
        global CURRENT_SERVER
        
        if not project_name:
            project_name = socket.gethostname()
            print(f"Пользователь не ввел имя проекта, используется имя хоста: {project_name}")
        
        # Сохраняем имя проекта
        self.backup_manager._save_site_name_mapping(self.file_path, project_name)
        CURRENT_SERVER = project_name
        
        # Теперь запрашиваем номер задачи
        global CURRENT_TASK_NUMBER
        if CURRENT_TASK_NUMBER:
            self.on_task_number_entered(CURRENT_TASK_NUMBER)
        else:
            self.view.window().show_input_panel(
                "Введите название папки задачи:", 
                "", 
                self.on_task_number_entered, 
                None, 
                None
            )
    
    def on_task_number_entered(self, task_number):
        """Обработчик ввода номера задачи"""
        # Обработка пустого ввода
        task_number = task_number.strip() if task_number else None
        
        # Сохраняем номер задачи глобально
        global CURRENT_TASK_NUMBER
        CURRENT_TASK_NUMBER = task_number
        
        try:
            global CURRENT_SERVER
            
            # Создаем бэкап "до"
            before_path, _, _ = self.backup_manager.backup_file(
                self.file_path, 
                server_name=CURRENT_SERVER,
                mode='before', 
                task_number=task_number
            )
            
            task_info = f" (задача #{task_number})" if task_number else ""
            sublime.status_message(f"FTP Backup: Создан 'before' бэкап{task_info} для {os.path.basename(self.file_path)}")
        
        except Exception as e:
            sublime.error_message(f"Ошибка создания 'before' бэкапа: {str(e)}")
    
    def create_before_backup(self, file_path, task_number):
        try:
            # Обработка пустого ввода
            task_number = task_number.strip() if task_number else None
            
            # Сохраняем номер задачи глобально
            global CURRENT_TASK_NUMBER
            CURRENT_TASK_NUMBER = task_number
            
            # Загружаем путь к директории бэкапов из настроек
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            backup_manager = FtpBackupManager(backup_root)
            
            before_path, _, _ = backup_manager.backup_file(file_path, mode='before', task_number=task_number)
            
            task_info = f" (задача #{task_number})" if task_number else ""
            sublime.status_message(f"FTP Backup: Создан 'before' бэкап{task_info} для {os.path.basename(file_path)}")
        
        except Exception as e:
            sublime.error_message(f"Ошибка создания 'before' бэкапа: {str(e)}")

class FtpBackupCreateAfterCommand(sublime_plugin.TextCommand):
    def run(self, edit, file_path=None):
        """Создание принудительного 'after' бэкапа"""
        if file_path is None:
            file_path = self.view.file_name()
        
        if not file_path:
            sublime.status_message("FTP Backup: Нет открытого файла")
            return
        
        # Загружаем настройки
        settings = sublime.load_settings('ftp_backup.sublime-settings')
        backup_root = settings.get('backup_root')
        if not backup_root:
            sublime.status_message("FTP Backup: Не указана папка для бэкапов")
            self.view.window().run_command("ftp_backup_browse_folder")
            return
            
        self.backup_manager = FtpBackupManager(backup_root)
        self.file_path = file_path
        
        # Проверяем, есть ли уже сохраненное имя проекта
        saved_site = self.backup_manager._check_site_name_mapping(file_path)
        if saved_site:
            self.backup_manager.logger.debug(f"Используется сохраненное имя проекта: {saved_site}")
            self.on_project_name_entered(saved_site)
        else:
            # Пытаемся найти предполагаемое имя проекта
            suggested_name = self.get_suggested_project_name(file_path)
            
            # Запрашиваем у пользователя имя проекта
            self.view.window().show_input_panel(
                "Введите название проекта:", 
                suggested_name if suggested_name else "", 
                self.on_project_name_entered, 
                None, 
                None
            )
    
    def get_suggested_project_name(self, file_path):
        """Пытается определить имя проекта из пути к файлу"""
        try:
            normalized_path = file_path.replace('/', '\\')
            patterns = [
                r'(?:var\\www\\|www\\|public_html\\|local\\|htdocs\\|home\\)([^\\]+)',
                r'ftp://([^/]+)',
                r'\\([^\\]+)\\(?:www|public_html|httpdocs)\\',
            ]

            for pattern in patterns:
                match = re.search(pattern, normalized_path)
                if match:
                    return match.group(1)

            parts = normalized_path.split('\\')
            for i, part in enumerate(parts):
                if part.lower() in ['www', 'public_html', 'httpdocs', 'htdocs'] and i > 0:
                    return parts[i-1]

            for part in parts:
                if '.' in part and not part.endswith(('.php', '.html', '.js', '.css')):
                    return part
                    
            return None
        except Exception as e:
            print(f"Ошибка при определении имени проекта: {e}")
            return None
    
    def on_project_name_entered(self, project_name):
        """Обработчик ввода имени проекта"""
        global CURRENT_SERVER
        
        if not project_name:
            project_name = socket.gethostname()
            print(f"Пользователь не ввел имя проекта, используется имя хоста: {project_name}")
        
        # Сохраняем имя проекта
        self.backup_manager._save_site_name_mapping(self.file_path, project_name)
        CURRENT_SERVER = project_name
        
        # Теперь запрашиваем номер задачи
        global CURRENT_TASK_NUMBER
        if CURRENT_TASK_NUMBER:
            self.on_task_number_entered(CURRENT_TASK_NUMBER)
        else:
            self.view.window().show_input_panel(
                "Введите название папки задачи:", 
                "", 
                self.on_task_number_entered, 
                None, 
                None
            )
    
    def on_task_number_entered(self, task_number):
        """Обработчик ввода номера задачи"""
        # Обработка пустого ввода
        task_number = task_number.strip() if task_number else None
        
        # Сохраняем номер задачи глобально
        global CURRENT_TASK_NUMBER
        CURRENT_TASK_NUMBER = task_number
        
        try:
            global CURRENT_SERVER
            
            # Создаем бэкап "после"
            _, after_path, _ = self.backup_manager.backup_file(
                self.file_path, 
                server_name=CURRENT_SERVER,
                mode='after', 
                task_number=task_number
            )
            
            task_info = f" (задача #{task_number})" if task_number else ""
            sublime.status_message(f"FTP Backup: Создан 'after' бэкап{task_info} для {os.path.basename(self.file_path)}")
        
        except Exception as e:
            sublime.error_message(f"Ошибка создания 'after' бэкапа: {str(e)}")
    
    def create_after_backup(self, file_path, task_number):
        try:
            # Обработка пустого ввода
            task_number = task_number.strip() if task_number else None
            
            # Сохраняем номер задачи глобально
            global CURRENT_TASK_NUMBER
            CURRENT_TASK_NUMBER = task_number
            
            # Загружаем путь к директории бэкапов из настроек
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            backup_manager = FtpBackupManager(backup_root)
            
            _, after_path, _ = backup_manager.backup_file(file_path, mode='after', task_number=task_number)
            
            task_info = f" (задача #{task_number})" if task_number else ""
            sublime.status_message(f"FTP Backup: Создан 'after' бэкап{task_info} для {os.path.basename(file_path)}")
        
        except Exception as e:
            sublime.error_message(f"Ошибка создания 'after' бэкапа: {str(e)}")

class FtpBackupCreateZipCommand(sublime_plugin.WindowCommand):
    def run(self):
        """Создание ZIP-архива с выбором папки"""
        # Загружаем путь к директории бэкапов из настроек
        settings = sublime.load_settings('ftp_backup.sublime-settings')
        backup_root = settings.get('backup_root')
        
        try:
            # Получаем список сайтов (папок первого уровня)
            sites = [d for d in os.listdir(backup_root) 
                    if os.path.isdir(os.path.join(backup_root, d)) and not d == 'logs']
            
            if not sites:
                sublime.status_message("FTP Backup: Нет доступных папок для архивации")
                return
            
            # Показываем выбор сайта
            self.backup_root = backup_root
            self.sites = sites
            self.window.show_quick_panel(sites, self.on_site_selected)
            
        except Exception as e:
            sublime.error_message(f"Ошибка при создании ZIP-архива: {str(e)}")
    
    def on_site_selected(self, index):
        if index == -1:
            return
        
        site = self.sites[index]
        site_path = os.path.join(self.backup_root, site)
        
        # Получаем список месяцев
        months = [d for d in os.listdir(site_path) 
                if os.path.isdir(os.path.join(site_path, d))]
        
        if not months:
            sublime.status_message(f"FTP Backup: В папке {site} нет доступных месяцев")
            return
        
        self.site = site
        self.months = months
        self.site_path = site_path
        self.window.show_quick_panel(months, self.on_month_selected)
    
    def on_month_selected(self, index):
        if index == -1:
            return
        
        month = self.months[index]
        month_path = os.path.join(self.site_path, month)
        
        # Проверяем наличие папок задач
        items = [d for d in os.listdir(month_path) 
                if os.path.isdir(os.path.join(month_path, d))]
        
       # Разделяем на задачи и папки before/after на корневом уровне
        root_folders = [d for d in items if d in ['before', 'after']]
        tasks = [d for d in items if d not in ['before', 'after']]  # Все остальные папки считаем задачами
        
        all_options = []
        
        # Если есть корневые папки before/after, добавляем опцию всей папки месяца
        if root_folders:
            all_options.append(f"[Весь месяц] {month}")
            if 'before' in root_folders:
                all_options.append(f"[Before] {month}")
            if 'after' in root_folders:
                all_options.append(f"[After] {month}")
        
        # Добавляем папки задач
        for task in tasks:
            task_path = os.path.join(month_path, task)
            task_items = os.listdir(task_path)
            
            all_options.append(f"[Задача] {task}")
            
            if 'before' in task_items:
                all_options.append(f"[Before] {task}")
            if 'after' in task_items:
                all_options.append(f"[After] {task}")
        
        if not all_options:
            sublime.status_message(f"FTP Backup: В папке {month} нет доступных папок для архивации")
            return
        
        self.month = month
        self.month_path = month_path
        self.all_options = all_options
        self.tasks = tasks
        self.root_folders = root_folders
        
        self.window.show_quick_panel(all_options, self.on_folder_selected)
    
    def on_folder_selected(self, index):
        if index == -1:
            return
        
        selected = self.all_options[index]
        
        # Загружаем путь к директории бэкапов из настроек
        settings = sublime.load_settings('ftp_backup.sublime-settings')
        backup_root = settings.get('backup_root')
        backup_manager = FtpBackupManager(backup_root)
        
        try:
            zip_path = None
            
            # Парсим выбранную опцию
            if selected.startswith('[Весь месяц]'):
                # Архивируем всю папку месяца
                zip_path = self.create_zip_archive(backup_manager, self.month_path)
                
            elif selected.startswith('[Before]') or selected.startswith('[After]'):
                folder_type = 'before' if selected.startswith('[Before]') else 'after'
                
                if selected.split('] ')[1] == self.month:
                    # Архивируем корневую папку before/after
                    folder_path = os.path.join(self.month_path, folder_type)
                else:
                    # Архивируем папку before/after задачи
                    task_name = selected.split('] ')[1]
                    folder_path = os.path.join(self.month_path, task_name, folder_type)
                
                zip_path = self.create_zip_archive(backup_manager, folder_path, folder_type)
                
            elif selected.startswith('[Задача]'):
                # Архивируем всю папку задачи
                task_name = selected.split('] ')[1]
                folder_path = os.path.join(self.month_path, task_name)
                zip_path = self.create_zip_archive(backup_manager, folder_path)
            
            # После создания архива, уведомляем пользователя
            if zip_path:
                sublime.status_message(f"FTP Backup: Архив успешно создан по пути: {zip_path}")
            else:
                sublime.status_message("FTP Backup: Ошибка при создании архива")
        
        except Exception as e:
            sublime.error_message(f"Ошибка при создании архива: {str(e)}")
    
    def create_zip_archive(self, backup_manager, folder_path, folder_type=None):
        """
        Создание ZIP-архива для указанной папки с сохранением в папке задачи
        """
        try:
            if not os.path.exists(folder_path):
                sublime.status_message(f"FTP Backup: Папка для архивации не существует: {folder_path}")
                return None
            
            # Приводим путь к стандартному виду
            folder_path = os.path.normpath(folder_path)
            
            # Извлекаем имя сайта безопасным способом
            folder_parts = folder_path.split(os.sep)
            # Удаляем пустые элементы
            folder_parts = [part for part in folder_parts if part]
            
            # Находим имя сайта - ищем имя папки после корневой папки BackUp
            site_name = "backup"  # значение по умолчанию
            
            # Ищем в пути индекс корневой директории бэкапов
            backup_root_parts = os.path.normpath(self.backup_root).split(os.sep)
            backup_root_parts = [part for part in backup_root_parts if part]
            
            # Находим индекс корневого каталога BackUp в пути
            root_index = -1
            for i, part in enumerate(folder_parts):
                if i < len(folder_parts) - 1 and part == backup_root_parts[-1]:
                    root_index = i
                    break
            
            # Если нашли корневой каталог, то следующий элемент должен быть именем сайта
            if root_index >= 0 and root_index + 1 < len(folder_parts):
                site_name = folder_parts[root_index + 1]
                backup_manager.logger.debug(f"Извлечено имя сайта из пути: {site_name}")
                
                # Проверяем, есть ли сопоставление с реальным именем сайта в folder_mapping
                for real_site_name, folder_key in backup_manager.folder_mapping.items():
                    if folder_key == site_name:
                        site_name = real_site_name
                        backup_manager.logger.debug(f"Найдено соответствие с реальным именем сайта: {site_name}")
                        break
            
            # Формируем безопасное имя архива без недопустимых символов
            date_str = datetime.now().strftime("%d.%m.%Y.%H.%M")
            
            # Определяем имя архива с учетом типа папки
            if folder_type:
                zip_name = f"backup_{site_name}_{folder_type}_{date_str}.zip"
            else:
                zip_name = f"backup_{site_name}_{date_str}.zip"
            
            # Определяем папку задачи (task_xxx) или использовать исходную директорию
            zip_dir = folder_path
            
            # Проверяем, может ли текущая папка быть 'before' или 'after' внутри задачи
            current_folder = os.path.basename(folder_path)
            if current_folder in ['before', 'after']:
                # Поднимаемся на уровень выше - к папке задачи
                zip_dir = os.path.dirname(folder_path)
                backup_manager.logger.debug(f"Обнаружена папка {current_folder}, поднимаемся к папке задачи: {zip_dir}")
            
            # Ищем, содержит ли путь папку задачи
            task_folder = None
            for i, part in enumerate(folder_parts):
                if part.startswith('task_') or re.match(r'task_[\w-]+', part):
                    # Определяем полный путь до папки задачи
                    task_index = i
                    
                    # Собираем путь до папки задачи включительно
                    if ':' in folder_path:  # Windows путь
                        drive = folder_path.split(':')[0] + ':'
                        path_parts = folder_parts[:task_index+1]
                        task_folder = os.path.join(drive, os.sep, *path_parts)
                    else:  # Unix путь
                        path_parts = folder_parts[:task_index+1]
                        task_folder = os.path.join(os.sep, *path_parts)
                    
                    backup_manager.logger.debug(f"Найдена папка задачи: {task_folder}")
                    break
            
            # Если нашли папку задачи, используем её
            if task_folder:
                zip_dir = task_folder
                backup_manager.logger.debug(f"Установлена папка задачи для ZIP: {zip_dir}")
            
            # Формируем полный путь к ZIP
            zip_path = os.path.join(zip_dir, zip_name)
            
            # Убеждаемся, что директория существует
            os.makedirs(os.path.dirname(zip_path), exist_ok=True)
            
            backup_manager.logger.debug(f"Создание архива в папке задачи: {zip_path}")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
                        backup_manager.logger.debug(f"Добавлен файл {arcname}")
            
            backup_manager.logger.debug(f"Архив успешно создан: {zip_path}")
            
            # Сбрасываем текущий номер задачи после создания архива
            global CURRENT_TASK_NUMBER, CURRENT_SERVER
            CURRENT_TASK_NUMBER = None
            CURRENT_SERVER = None
            backup_manager.logger.debug("Номер текущей задачи и сервер сброшены после создания архива")
            
            return zip_path
            
        except Exception as e:
            backup_manager.logger.error(f"Ошибка создания архива: {e}")
            return None
