import sublime
import sublime_plugin

# Подключение к основному модулю FTP Backup
try:
    from . import ftp_backup
except ImportError:
    import ftp_backup

class FtpBackupShowTaskInputCommand(sublime_plugin.WindowCommand):
    """Команда для вызова диалога ввода номера задачи"""
    
    def run(self):
        # Получаем текущий номер задачи
        try:
            current_task = ftp_backup.CURRENT_TASK_NUMBER or ""
        except:
            current_task = ""
            
        # Показываем диалог для ввода
        self.window.show_input_panel(
            "Введите номер/имя задачи:",
            current_task,
            self.on_task_entered,
            None,
            None
        )
    
    def on_task_entered(self, task_number):
        """Обработчик ввода номера задачи"""
        if task_number:
            try:
                # Устанавливаем новый номер задачи
                ftp_backup.CURRENT_TASK_NUMBER = task_number
                sublime.status_message(f"FTP Backup: Задача изменена на {task_number}")
            except Exception as e:
                sublime.status_message(f"FTP Backup: Ошибка при изменении задачи: {str(e)}")
        else:
            # Если ввод пустой, сбрасываем текущую задачу
            try:
                ftp_backup.CURRENT_TASK_NUMBER = None
                sublime.status_message("FTP Backup: Текущая задача сброшена")
            except:
                sublime.status_message("FTP Backup: Ошибка при сбросе задачи")