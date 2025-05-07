import sublime
import os
import re
from datetime import datetime
import sublime
import os
import re
import json  # Добавляем импорт json
from datetime import datetime



# Подключение к основному модулю FTP Backup
try:
    # Попытка относительного импорта
    from . import ftp_backup
except (ImportError, ValueError):
    try:
        # Попытка абсолютного импорта
        import ftp_backup
    except ImportError:
        # Последняя попытка импорта
        try:
            import sys
            import os
            user_package_path = os.path.join(sublime.packages_path(), 'User')
            sys.path.insert(0, user_package_path)
            import ftp_backup
            sys.path.pop(0)
        except ImportError:
            ftp_backup = None

class TaskSelectorHelper:
    """
    Вспомогательный класс для выбора задач
    Используется различными командами FTP Backup
    Фильтрует задачи по текущему проекту/сайту
    """
    
    def __init__(self, window, callback, file_path=None):
        """
        Инициализация хелпера
        window - окно Sublime Text
        callback - функция, которая будет вызвана после выбора задачи
                  с параметром task_number
        file_path - путь к текущему файлу (для определения проекта/сайта)
        """
        self.window = window
        self.callback = callback
        self.file_path = file_path
        
        # Определяем текущий сайт
        if file_path:
            # Получаем текущий сервер
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            if backup_root:
                backup_manager = ftp_backup.FtpBackupManager(backup_root)
                self.current_site = backup_manager.extract_site_name(file_path)
            else:
                self.current_site = None
        else:
            self.current_site = None
    
    def show_task_selector(self):
        """Показывает выпадающий список для выбора задачи"""
        # Получаем список всех задач для текущего проекта
        tasks = self.get_project_tasks()
        
        if tasks:
            # Используем show_quick_panel с параметрами для лучшего отображения
            self.window.show_quick_panel(
                # Для каждой задачи отправляем полное описание
                items=[task[1] for task in tasks],
                on_select=lambda index: self.on_task_selected(index, tasks),
                flags=sublime.MONOSPACE_FONT,  # Используем моноширинный шрифт для лучшего выравнивания
                placeholder="Выберите задачу для проекта или создайте новую..."
            )
        else:
            # Если задачи не найдены, показываем стандартный диалог
            self.window.show_input_panel(
                f"Введите номер/имя задачи для проекта {self.current_site or ''}:",
                "",
                self.on_task_entered,
                None,
                None
            )
    
    def get_project_tasks(self):
        """
        Получает список задач, относящихся к текущему проекту/сайту
        Возвращает список с именами задач и дополнительной информацией
        """
        try:
            # Если нет текущего сайта, вернем все задачи
            if not self.current_site:
                return self.get_all_tasks()
            
            # Получаем корневую папку бэкапов из настроек
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            
            if not backup_root or not os.path.exists(backup_root):
                return []
            
            # Ищем папку сайта
            site_folder = self._find_site_folder(backup_root, self.current_site)
            if not site_folder:
                # Если папка сайта не найдена, пробуем найти по части имени
                for folder in os.listdir(backup_root):
                    folder_path = os.path.join(backup_root, folder)
                    if os.path.isdir(folder_path) and folder != "logs":
                        # Проверяем, содержит ли имя папки часть имени сайта
                        if self.current_site.lower() in folder.lower() or folder.lower() in self.current_site.lower():
                            site_folder = folder
                            break
            
            # Если сайт все еще не найден, вернем все задачи
            if not site_folder:
                return self.get_all_tasks()
            
            # Словарь для хранения информации о задачах
            # Ключ - имя задачи, значение - словарь с информацией
            tasks_info = {}
            
            # Путь к папке сайта
            site_path = os.path.join(backup_root, site_folder)
            
            # Проверяем подпапки сайта (месяцы или задачи)
            for month_folder in os.listdir(site_path):
                month_path = os.path.join(site_path, month_folder)
                
                if not os.path.isdir(month_path):
                    continue
                
                # Ищем задачи в папке месяца
                for item in os.listdir(month_path):
                    item_path = os.path.join(month_path, item)
                    
                    # Проверяем является ли папка задачей
                    # Задача обычно имеет имя, начинающееся с task_ или это папка, не являющаяся before/after
                    if os.path.isdir(item_path) and item not in ['before', 'after', 'logs']:
                        # Если задача еще не в словаре, добавляем её
                        if item not in tasks_info:
                            tasks_info[item] = {
                                'name': item,
                                'sites': set([site_folder]),  # Сайты, где используется задача
                                'file_count': 0,  # Общее количество файлов
                                'mod_time': 0,    # Время последней модификации
                                'paths': []       # Пути к папкам задачи
                            }
                        
                        # Добавляем путь к папке задачи
                        tasks_info[item]['paths'].append(item_path)
                        
                        # Подсчитываем файлы и проверяем время модификации
                        for root, dirs, files in os.walk(item_path):
                            tasks_info[item]['file_count'] += len(files)
                            
                            # Проверяем время модификации каждого файла
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    mtime = os.path.getmtime(file_path)
                                    if mtime > tasks_info[item]['mod_time']:
                                        tasks_info[item]['mod_time'] = mtime
                                except:
                                    pass
            
            # Преобразуем информацию о задачах в список для отображения
            display_tasks = []
            
            # Добавляем текущую задачу в начало списка, если она существует и в этом проекте
            try:
                current_task = ftp_backup.CURRENT_TASK_NUMBER
                if current_task and current_task in tasks_info:
                    info = tasks_info[current_task]
                    
                    # Форматируем время последней модификации
                    if info['mod_time'] > 0:
                        mod_time_str = datetime.fromtimestamp(info['mod_time']).strftime('%d.%m.%Y %H:%M')
                    else:
                        mod_time_str = "неизвестно"
                    
                    # Формируем строку для отображения
                    sites_str = ", ".join(sorted(info['sites']))
                    if len(sites_str) > 20:
                        sites_str = sites_str[:17] + "..."
                    
                    # Добавляем задачу с дополнительной информацией
                    display_task = f"★ {current_task} [{info['file_count']} файлов, {mod_time_str}]"
                    
                    # Добавляем в начало списка
                    display_tasks.append([current_task, display_task])
                    # Удаляем из словаря, чтобы не дублировать
                    del tasks_info[current_task]
            except:
                pass
            
            # Добавляем остальные задачи
            for task_name, info in sorted(tasks_info.items()):
                # Форматируем время последней модификации
                if info['mod_time'] > 0:
                    mod_time_str = datetime.fromtimestamp(info['mod_time']).strftime('%d.%m.%Y %H:%M')
                else:
                    mod_time_str = "неизвестно"
                
                # Формируем строку для отображения
                sites_str = ", ".join(sorted(info['sites']))
                if len(sites_str) > 20:
                    sites_str = sites_str[:17] + "..."
                
                # Добавляем задачу с дополнительной информацией
                display_task = f"{task_name} [{info['file_count']} файлов, {mod_time_str}]"
                
                # Сохраняем оригинальное имя задачи в первом элементе списка,
                # чтобы использовать его при выборе
                display_tasks.append([task_name, display_task])
            
            # Всегда добавляем опцию "Создать новую задачу" в начало списка
            display_tasks.insert(0, ["__new__", f"✚ Создать новую задачу для {site_folder}..."])
            
            return display_tasks
            
        except Exception as e:
            print(f"Ошибка при получении списка задач проекта: {str(e)}")
            return []
    
    def _find_site_folder(self, backup_root, site_name):
        """
        Поиск папки сайта в корневой директории бэкапов
        Учитывает возможное сопоставление имен сайтов с папками
        """
        try:
            # Проверяем наличие сопоставления папок
            folder_mapping_path = os.path.join(backup_root, 'folder_mapping.json')
            if os.path.exists(folder_mapping_path):
                with open(folder_mapping_path, 'r', encoding='utf-8') as f:
                    folder_mapping = json.load(f)
                
                # Проверяем, есть ли сайт в сопоставлении
                if site_name in folder_mapping:
                    return folder_mapping[site_name]
            
            # Если сопоставление не найдено, пробуем найти по имени
            safe_site_name = re.sub(r'[^\w\-_.]', '_', site_name)
            if os.path.exists(os.path.join(backup_root, safe_site_name)):
                return safe_site_name
            
            # Пробуем найти по части имени
            for folder in os.listdir(backup_root):
                folder_path = os.path.join(backup_root, folder)
                if os.path.isdir(folder_path) and folder != "logs":
                    # Проверяем, является ли эта папка точным совпадением
                    if folder.lower() == site_name.lower():
                        return folder
            
            # Ничего не найдено
            return None
            
        except Exception as e:
            print(f"Ошибка при поиске папки сайта: {str(e)}")
            return None
    
    def get_all_tasks(self):
        """
        Получает список всех доступных задач из папки бэкапов
        Возвращает список строк с именами задач и дополнительной информацией
        """
        try:
            # Получаем корневую папку бэкапов из настроек
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root')
            
            if not backup_root or not os.path.exists(backup_root):
                return []
            
            # Словарь для хранения информации о задачах
            # Ключ - имя задачи, значение - словарь с информацией
            tasks_info = {}
            
            # Ищем задачи во всех подпапках
            for site_folder in os.listdir(backup_root):
                site_path = os.path.join(backup_root, site_folder)
                
                # Игнорируем папку логов и файлы
                if not os.path.isdir(site_path) or site_folder == 'logs':
                    continue
                
                # Проверяем подпапки сайта (месяцы или задачи)
                for month_folder in os.listdir(site_path):
                    month_path = os.path.join(site_path, month_folder)
                    
                    if not os.path.isdir(month_path):
                        continue
                    
                    # Ищем задачи в папке месяца
                    for item in os.listdir(month_path):
                        item_path = os.path.join(month_path, item)
                        
                        # Проверяем является ли папка задачей
                        # Задача обычно имеет имя, начинающееся с task_ или это папка, не являющаяся before/after
                        if os.path.isdir(item_path) and item not in ['before', 'after', 'logs']:
                            # Если задача еще не в словаре, добавляем её
                            if item not in tasks_info:
                                tasks_info[item] = {
                                    'name': item,
                                    'sites': set(),  # Сайты, где используется задача
                                    'file_count': 0,  # Общее количество файлов
                                    'mod_time': 0,    # Время последней модификации
                                    'paths': []       # Пути к папкам задачи
                                }
                            
                            # Добавляем информацию о сайте
                            tasks_info[item]['sites'].add(site_folder)
                            
                            # Добавляем путь к папке задачи
                            tasks_info[item]['paths'].append(item_path)
                            
                            # Подсчитываем файлы и проверяем время модификации
                            for root, dirs, files in os.walk(item_path):
                                tasks_info[item]['file_count'] += len(files)
                                
                                # Проверяем время модификации каждого файла
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    try:
                                        mtime = os.path.getmtime(file_path)
                                        if mtime > tasks_info[item]['mod_time']:
                                            tasks_info[item]['mod_time'] = mtime
                                    except:
                                        pass
            
            # Преобразуем информацию о задачах в список для отображения
            display_tasks = []
            
            # Добавляем текущую задачу в начало списка, если она существует
            try:
                current_task = ftp_backup.CURRENT_TASK_NUMBER
                if current_task and current_task in tasks_info:
                    info = tasks_info[current_task]
                    
                    # Форматируем время последней модификации
                    if info['mod_time'] > 0:
                        mod_time_str = datetime.fromtimestamp(info['mod_time']).strftime('%d.%m.%Y %H:%M')
                    else:
                        mod_time_str = "неизвестно"
                    
                    # Формируем строку для отображения
                    sites_str = ", ".join(sorted(info['sites']))
                    if len(sites_str) > 20:
                        sites_str = sites_str[:17] + "..."
                    
                    # Добавляем задачу с дополнительной информацией
                    display_task = f"★ {current_task} [{info['file_count']} файлов, {mod_time_str}]"
                    
                    # Добавляем в начало списка
                    display_tasks.append([current_task, display_task])
                    # Удаляем из словаря, чтобы не дублировать
                    del tasks_info[current_task]
            except:
                pass
            
            # Добавляем остальные задачи
            for task_name, info in sorted(tasks_info.items()):
                # Форматируем время последней модификации
                if info['mod_time'] > 0:
                    mod_time_str = datetime.fromtimestamp(info['mod_time']).strftime('%d.%m.%Y %H:%M')
                else:
                    mod_time_str = "неизвестно"
                
                # Формируем строку для отображения
                sites_str = ", ".join(sorted(info['sites']))
                if len(sites_str) > 20:
                    sites_str = sites_str[:17] + "..."
                
                # Добавляем задачу с дополнительной информацией
                display_task = f"{task_name} [{info['file_count']} файлов, {mod_time_str}]"
                
                # Сохраняем оригинальное имя задачи в первом элементе списка,
                # чтобы использовать его при выборе
                display_tasks.append([task_name, display_task])
            
            # Всегда добавляем опцию "Создать новую задачу" в начало списка
            display_tasks.insert(0, ["__new__", "✚ Создать новую задачу..."])
            
            return display_tasks
            
        except Exception as e:
            print(f"Ошибка при получении списка задач: {str(e)}")
            return []
    
    def on_task_selected(self, index, tasks):
        """Обработчик выбора задачи из списка"""
        if index == -1:  # Пользователь отменил выбор
            return
        
        # Проверка, выбрал ли пользователь "Создать новую задачу"
        if index == 0 and tasks and tasks[0][0] == "__new__":
            self.window.show_input_panel(
                f"Введите название новой задачи для проекта {self.current_site or ''}:",
                "",
                self.on_new_task_entered,
                None,
                None
            )
            return
        
        # Получаем настоящее имя задачи из первого элемента списка
        selected_task = tasks[index][0]
        
        try:
            # Устанавливаем новый номер задачи
            ftp_backup.CURRENT_TASK_NUMBER = selected_task
            sublime.status_message(f"FTP Backup: Задача изменена на {selected_task}")
            
            # Вызываем callback с выбранной задачей
            if self.callback:
                self.callback(selected_task)
        except Exception as e:
            sublime.status_message(f"FTP Backup: Ошибка при изменении задачи: {str(e)}")
    
    def on_new_task_entered(self, task_name):
        """Обработчик ввода имени новой задачи"""
        if not task_name:
            return
            
        # Проверяем, нет ли уже такой задачи
        existing_tasks = [t[0] for t in self.get_project_tasks()]
        if task_name in existing_tasks:
            if sublime.ok_cancel_dialog(
                f"Задача '{task_name}' уже существует.\nВыбрать эту задачу?",
                "Выбрать"
            ):
                try:
                    ftp_backup.CURRENT_TASK_NUMBER = task_name
                    sublime.status_message(f"FTP Backup: Задача изменена на {task_name}")
                    
                    # Вызываем callback с выбранной задачей
                    if self.callback:
                        self.callback(task_name)
                except Exception as e:
                    sublime.status_message(f"FTP Backup: Ошибка при изменении задачи: {str(e)}")
            return
            
        # Создаем новую задачу (просто устанавливаем имя в глобальную переменную)
        try:
            ftp_backup.CURRENT_TASK_NUMBER = task_name
            sublime.status_message(f"FTP Backup: Создана новая задача {task_name}")
            
            # Вызываем callback с выбранной задачей
            if self.callback:
                self.callback(task_name)
            
            # Подсказка пользователю о создании бэкапа
            sublime.set_timeout(lambda: sublime.status_message(
                "Для создания папки задачи сделайте бэкап файла: Ctrl+Shift+R"
            ), 2000)
        except Exception as e:
            sublime.status_message(f"FTP Backup: Ошибка при создании задачи: {str(e)}")
    
    def on_task_entered(self, task_number):
        """Обработчик ручного ввода номера задачи"""
        if task_number:
            try:
                # Устанавливаем новый номер задачи
                ftp_backup.CURRENT_TASK_NUMBER = task_number
                sublime.status_message(f"FTP Backup: Задача изменена на {task_number}")
                
                # Вызываем callback с выбранной задачей
                if self.callback:
                    self.callback(task_number)
            except Exception as e:
                sublime.status_message(f"FTP Backup: Ошибка при изменении задачи: {str(e)}")
        else:
            # Если ввод пустой, сбрасываем текущую задачу
            try:
                ftp_backup.CURRENT_TASK_NUMBER = None
                sublime.status_message("FTP Backup: Текущая задача сброшена")
                
                # Вызываем callback с пустым значением
                if self.callback:
                    self.callback(None)
            except:
                sublime.status_message("FTP Backup: Ошибка при сбросе задачи")