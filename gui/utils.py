from PySide6.QtCore import QThread, Signal

class WorkerThread(QThread):
    """Hilo genérico para ejecutar tareas en segundo plano"""
    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, task_function, **kwargs):
        super().__init__()
        self.task_function = task_function
        self.kwargs = kwargs

    def run(self):
        # Inyectamos el callback de log
        self.kwargs['log_callback'] = self.log_signal.emit
        self.task_function(**self.kwargs)
        self.finished_signal.emit()