from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                               QTextEdit, QLineEdit, QFileDialog, QGroupBox, QFormLayout)
from gui.utils import WorkerThread
import core
import os


class InfluxWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuración InfluxDB 3 Portable")
        self.resize(600, 650)  # Hacemos la ventana más alta
        layout = QVBoxLayout(self)

        # --- SECCIÓN 1: Descarga ---
        group_download = QGroupBox("1. Descarga e Instalación")
        layout_download = QVBoxLayout()

        layout_download.addWidget(QLabel("Carpeta de destino:"))
        self.path_input = QLineEdit("C:\\InfluxDB3_Core")
        btn_browse = QPushButton("Seleccionar...")
        btn_browse.clicked.connect(self.select_folder)

        layout_download.addWidget(self.path_input)
        layout_download.addWidget(btn_browse)

        self.url_input = QLineEdit("https://dl.influxdata.com/influxdb/releases/influxdb3-core-3.8.0-windows_amd64.zip")
        layout_download.addWidget(QLabel("URL del ZIP:"))
        layout_download.addWidget(self.url_input)

        group_download.setLayout(layout_download)
        layout.addWidget(group_download)

        # --- SECCIÓN 2: Configuración (Tus parámetros) ---
        group_config = QGroupBox("2. Parámetros de Configuración (Script)")
        layout_config = QFormLayout()

        saved_node = core.get_setting("influx_node", "Asus_ROG")
        saved_data = core.get_setting("influx_data_dir", "databases/shmdatabase")

        self.input_node_id = QLineEdit(saved_node)
        self.input_node_id.setPlaceholderText("Ej: nodo-01")

        self.input_data_dir = QLineEdit(saved_data)
        self.input_data_dir.setPlaceholderText("Ruta relativa o absoluta de los datos")

        layout_config.addRow("Node ID (--node-id):", self.input_node_id)
        layout_config.addRow("Data Dir (--data-dir):", self.input_data_dir)

        group_config.setLayout(layout_config)
        layout.addWidget(group_config)

        # --- LOGS ---
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background: #0f0f0f; color: #00ff00; font-family: Consolas;")
        layout.addWidget(self.log_area)

        # --- BOTÓN ---
        self.btn_run = QPushButton("DESCARGAR Y GENERAR SCRIPTS .BAT")
        self.btn_run.setStyleSheet("background-color: #D0021B; color: white; font-weight: bold; padding: 15px;")
        self.btn_run.clicked.connect(self.start_process)
        layout.addWidget(self.btn_run)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if folder: self.path_input.setText(os.path.normpath(folder))

    def start_process(self):
        self.btn_run.setEnabled(False)
        target = self.path_input.text()
        url = self.url_input.text()
        node = self.input_node_id.text()
        data = self.input_data_dir.text()

        # --- GUARDAR EN JSON ---
        core.save_setting("influx_path", target)
        core.save_setting("influx_url", url)
        core.save_setting("influx_node", node)
        core.save_setting("influx_data_dir", data)

        def task(log_callback):
            log_callback("--- Paso 1: Descargando ---")
            success, msg = core.download_and_extract(url, target, log_callback)

            if success:
                log_callback("\n--- Paso 2: Creando Scripts Personalizados ---")
                ok, msg_conf = core.setup_influx3_scripts(target, node, data, log_callback)

                if ok:
                    log_callback("\n[¡PROCESO FINALIZADO CON ÉXITO!]")
                    log_callback(f"Ve a la carpeta: {target}")
                    log_callback("1. Ejecuta '1_INICIAR_SERVER.bat' (déjalo abierto)")
                    log_callback("2. Ejecuta '2_GENERAR_TOKEN.bat'")
                    log_callback("3. Busca el archivo 'credenciales_admin.txt' para ver tu token.")
                else:
                    log_callback(f"[ERROR Configuración]: {msg_conf}")
            else:
                log_callback(f"[ERROR Descarga]: {msg}")

        self.worker = WorkerThread(task)
        self.worker.log_signal.connect(self.log_area.append)
        self.worker.finished_signal.connect(lambda: self.btn_run.setEnabled(True))
        self.worker.start()