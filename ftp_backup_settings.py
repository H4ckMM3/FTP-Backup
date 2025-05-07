import os
import sublime
import sublime_plugin
import json

class FtpBackupSettings:
    def __init__(self):
        self.settings_file = 'ftp_backup.sublime-settings'
        self._load_settings()

    def _load_settings(self):
        """Загрузка настроек с установкой значений по умолчанию и расширенной диагностикой"""
        try:
            # Проверяем, существует ли файл настроек
            settings_path = os.path.join(sublime.packages_path(), "User", self.settings_file)
            
            if not os.path.exists(settings_path):
                # Создаем файл настроек по умолчанию
                default_path = os.path.join(os.path.expanduser("~"), "Desktop", "BackUp")
                default_settings = {"backup_root": default_path}
                
                os.makedirs(os.path.dirname(settings_path), exist_ok=True)
                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(default_settings, f, indent=4, ensure_ascii=False)
                    
                print(f"FTP Backup: создан новый файл настроек: {settings_path}")
            
            # Загружаем настройки
            self.settings = sublime.load_settings(self.settings_file)
            
            # Проверяем наличие необходимых настроек
            if not self.settings.has('backup_root'):
                default_path = os.path.join(os.path.expanduser("~"), "Desktop", "BackUp")
                self.settings.set('backup_root', default_path)
                sublime.save_settings(self.settings_file)
                print(f"FTP Backup: установлен путь по умолчанию: {default_path}")
                
        except Exception as e:
            print(f"FTP Backup ERROR при загрузке настроек: {str(e)}")
            # Создаем объект настроек в памяти, если не удалось загрузить из файла
            from types import SimpleNamespace
            self.settings = SimpleNamespace()
            self.settings.get = lambda key, default=None: os.path.join(os.path.expanduser("~"), "Desktop", "BackUp") if key == "backup_root" else default
            self.settings.set = lambda key, value: None
            print(f"FTP Backup: используются аварийные настройки")
    
    def get_backup_root(self):
        """Получение корневой папки для бэкапов с проверкой на ошибки"""
        try:
            path = self.settings.get('backup_root')
            if not path:
                path = os.path.join(os.path.expanduser("~"), "Desktop", "BackUp")
                print(f"FTP Backup: путь был пустым, используется путь по умолчанию: {path}")
            return path
        except Exception as e:
            print(f"FTP Backup ERROR при получении пути: {str(e)}")
            default_path = os.path.join(os.path.expanduser("~"), "Desktop", "BackUp")
            print(f"FTP Backup: при ошибке используется путь по умолчанию: {default_path}")
            return default_path
    
    def set_backup_root(self, path):
        """Установка корневой папки для бэкапов с обработкой ошибок"""
        try:
            # Проверяем и при необходимости создаем папку
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                print(f"FTP Backup: создана папка для бэкапов: {path}")
            
            # Сохраняем настройку
            self.settings.set('backup_root', path)
            sublime.save_settings(self.settings_file)
            print(f"FTP Backup: сохранен новый путь: {path}")
        except Exception as e:
            print(f"FTP Backup ERROR при сохранении пути: {str(e)}")
            sublime.error_message(f"Не удалось сохранить путь: {str(e)}")

class FtpBackupOpenSettingsCommand(sublime_plugin.WindowCommand):
    def run(self):
        """Открытие окна настроек с проверкой существования файла"""
        # Проверяем, существует ли файл настроек
        settings_path = os.path.join(sublime.packages_path(), "User", "ftp_backup.sublime-settings")
        
        if not os.path.exists(settings_path):
            # Создаем файл настроек с значениями по умолчанию, если он не существует
            default_settings = {
                "backup_root": os.path.join(os.path.expanduser("~"), "Desktop", "BackUp")
            }
            
            try:
                os.makedirs(os.path.dirname(settings_path), exist_ok=True)
                with open(settings_path, 'w', encoding='utf-8') as f:
                    json.dump(default_settings, f, indent=4, ensure_ascii=False)
                sublime.status_message("FTP Backup: Создан файл настроек")
            except Exception as e:
                sublime.error_message(f"Ошибка при создании файла настроек: {str(e)}")
                return
        
        # Открываем файл настроек
        self.window.run_command('open_file', {
            'file': settings_path
        })

class FtpBackupBrowseFolderCommand(sublime_plugin.WindowCommand):
    def run(self):
        """Диалог ввода пути к папке для бэкапов"""
        # Получаем текущую папку для бэкапов
        settings = FtpBackupSettings()
        current_folder = settings.get_backup_root()
        
        # Показываем диалог ввода пути
        self.window.show_input_panel(
            "Введите путь к папке для бэкапов:", 
            current_folder, 
            self.on_folder_entered, 
            None, 
            None
        )
    
    def on_folder_entered(self, folder_path):
        """Обработка введенного пути"""
        # Проверяем, существует ли папка
        if not os.path.exists(folder_path):
            try:
                # Пытаемся создать папку, если её нет
                os.makedirs(folder_path, exist_ok=True)
                sublime.status_message(f"FTP Backup: Создана новая папка для бэкапов: {folder_path}")
            except Exception as e:
                sublime.error_message(f"Ошибка при создании папки: {str(e)}")
                return
        
        try:
            # Сохраняем настройку
            settings = FtpBackupSettings()
            settings.set_backup_root(folder_path)
            sublime.status_message(f"FTP Backup: Установлена папка для бэкапов: {folder_path}")
        except Exception as e:
            sublime.error_message(f"Ошибка при сохранении настройки: {str(e)}")

# Команда для отображения текущего пути бэкапов
class FtpBackupShowCurrentPathCommand(sublime_plugin.WindowCommand):
    def run(self):
        """Показывает текущий путь для бэкапов в строке статуса и панели вывода"""
        settings = FtpBackupSettings()
        current_path = settings.get_backup_root()
        
        # Показываем в строке статуса
        sublime.status_message(f"FTP Backup: текущая папка: {current_path}")
        
        # Создаем и показываем панель вывода с информацией
        panel = self.window.create_output_panel("ftp_backup_path")
        panel.run_command("append", {"characters": f"Текущая папка для бэкапов:\n{current_path}\n\n", "scroll_to_end": True})
        self.window.run_command("show_panel", {"panel": "output.ftp_backup_path"})
        
        # Дополнительно, если путь существует - показываем это
        if os.path.exists(current_path):
            panel.run_command("append", {"characters": "✅ Папка существует\n", "scroll_to_end": True})
            panel.run_command("append", {"characters": "\nДля открытия этой папки в проводнике используйте команду:\n", "scroll_to_end": True})
            panel.run_command("append", {"characters": "FTP Backup: Open Backup Folder\n", "scroll_to_end": True})
        else:
            panel.run_command("append", {"characters": "❌ Папка не существует! Нужно создать или выбрать другую.\n", "scroll_to_end": True})
            
class FtpBackupOpenFolderInExplorerCommand(sublime_plugin.WindowCommand):
    def run(self):
        """Открывает папку с бэкапами в проводнике"""
        try:
            settings = FtpBackupSettings()
            backup_path = settings.get_backup_root()
            
            if not os.path.exists(backup_path):
                os.makedirs(backup_path, exist_ok=True)
                sublime.status_message(f"FTP Backup: Создана папка {backup_path}")
                
            # Определяем команду в зависимости от ОС
            import subprocess
            import platform
            
            system = platform.system()
            if system == 'Windows':
                # Windows
                os.startfile(backup_path)
            elif system == 'Darwin':
                # macOS
                subprocess.Popen(['open', backup_path])
            else:
                # Linux
                subprocess.Popen(['xdg-open', backup_path])
                
            sublime.status_message(f"FTP Backup: Открыта папка бэкапов в проводнике")
        except Exception as e:
            sublime.error_message(f"Ошибка при открытии папки: {str(e)}")