import sublime
import sublime_plugin
import os
import json
import re
from datetime import datetime
import traceback

# Попытка импорта основного модуля FTP Backup
try:
    from . import ftp_backup
except ImportError:
    import ftp_backup

class FtpBackupUiCommand(sublime_plugin.WindowCommand):
    """Команда для отображения встроенного интерфейса FTP Backup в Sublime Text"""
    
    def run(self):
        """Вызов основного меню интерфейса"""
        options = [
            "📁 Выбрать корневую папку бэкапов",
            "📅 Настройка создания папок по месяцам",
            "📁 Открыть папку бэкапов",
            "🔍 Просмотр информации"
        ]
        
        self.window.show_quick_panel(
            options,
            self.on_option_selected,
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )
    
    def on_option_selected(self, index):
        """Обработчик выбора пункта меню"""
        if index == -1:
            return  # Отмена выбора
        
        if index == 0:  # Выбрать корневую папку бэкапов
            self.window.run_command("ftp_backup_browse_folder")
        
        elif index == 1:  # Настройка создания папок по месяцам
            self.toggle_month_folders()
        
        elif index == 2:  # Открыть папку бэкапов
            self.window.run_command("ftp_backup_open_folder_in_explorer")
        
        elif index == 3:  # Просмотр информации
            self.show_info()
    
    def toggle_month_folders(self):
        """Переключение настройки создания папок по месяцам"""
        settings = sublime.load_settings('ftp_backup.sublime-settings')
        current_value = settings.get('create_month_folder', True)
        
        # Создаем меню с текущим выбором
        options = [
            f"✅ Создавать папки по месяцам (текущее: {'Да' if current_value else 'Нет'})",
            f"❌ Не создавать папки по месяцам (текущее: {'Нет' if current_value else 'Да'})"
        ]
        
        self.window.show_quick_panel(
            options,
            lambda idx: self.on_month_folder_selected(idx, current_value),
            sublime.KEEP_OPEN_ON_FOCUS_LOST
        )
    
    def on_month_folder_selected(self, index, current_value):
        """Обработчик выбора настройки создания папок по месяцам"""
        if index == -1:
            return  # Отмена выбора
        
        new_value = True if index == 0 else False
        
        if new_value != current_value:
            # Если выбрано значение, отличное от текущего - сохраняем
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            settings.set('create_month_folder', new_value)
            sublime.save_settings('ftp_backup.sublime-settings')
            
            sublime.status_message(f"FTP Backup: {'Включено' if new_value else 'Отключено'} создание папок по месяцам")
    
    def show_info(self):
        """Показывает информацию о текущей задаче и сервере"""
        try:
            # Получаем информацию о текущей задаче и сервере
            task_number = getattr(ftp_backup, 'CURRENT_TASK_NUMBER', None) or "не выбрана"
            server_name = getattr(ftp_backup, 'CURRENT_SERVER', None) or "не определен"
            
            settings = sublime.load_settings('ftp_backup.sublime-settings')
            backup_root = settings.get('backup_root', "не задан")
            create_month_folder = settings.get('create_month_folder', True)
            
            # Создаем панель вывода с информацией
            panel = self.window.create_output_panel("ftp_backup_info")
            
            # Формируем текст для отображения
            info_text = f"""
╔══════════════════════════════════════════════
║ Информация FTP Backup
╠══════════════════════════════════════════════
║ Текущая задача: {task_number}
║ Текущий сервер: {server_name}
║ Корневая папка: {backup_root}
║ Создание папок по месяцам: {'Да' if create_month_folder else 'Нет'}
╚══════════════════════════════════════════════
"""
            
            # Выводим информацию в панель
            panel.run_command("append", {"characters": info_text, "scroll_to_end": True})
            self.window.run_command("show_panel", {"panel": "output.ftp_backup_info"})
            
        except Exception as e:
            sublime.error_message(f"Ошибка при отображении информации: {str(e)}")
            traceback.print_exc()


# Класс для отображения статусной строки с информацией о текущем состоянии FTP Backup
class FtpBackupStatusBar:
    """Отображает информацию в статусной строке Sublime Text"""
    
    def __init__(self):
        self.active = False
        self.update_timer = None
    
    def start(self):
        """Запускает отображение статуса"""
        self.active = True
        self.update_status()
    
    def stop(self):
        """Останавливает отображение статуса"""
        self.active = False
        for window in sublime.windows():
            for view in window.views():
                view.erase_status('ftp_backup')
    
    def update_status(self):
        """Обновляет статусную строку"""
        if not self.active:
            return
        
        try:
            # Получаем текущую задачу и сервер
            task = getattr(ftp_backup, 'CURRENT_TASK_NUMBER', None) or "не выбрана"
            server = getattr(ftp_backup, 'CURRENT_SERVER', None) or "не определен"
            
            # Отображаем статус для всех активных окон
            for window in sublime.windows():
                for view in window.views():
                    view.set_status('ftp_backup', f"FTP Backup: Задача: {task} | Сервер: {server}")
        except:
            pass
        
        # Планируем следующее обновление
        self.update_timer = sublime.set_timeout(self.update_status, 5000)  # каждые 5 секунд


# Глобальный экземпляр статусной строки
status_bar = FtpBackupStatusBar()


# Класс для запуска статусной строки при загрузке плагина
class FtpBackupStartupListener(sublime_plugin.EventListener):
    """Запускает отображение статусной строки при загрузке плагина"""
    
    def on_init(self, views):
        """Вызывается при инициализации плагина"""
        global status_bar
        status_bar.start()
        
    def on_exit(self):
        """Вызывается при выходе из Sublime Text"""
        global status_bar
        status_bar.stop()