from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel,
                               QTextEdit, QLineEdit, QFileDialog, QGroupBox, QFormLayout, QMessageBox)
from gui.utils import WorkerThread
import core
import os


class InfluxWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Configuración InfluxDB 3 Portable")
        self.resize(600, 700)
        layout = QVBoxLayout(self)

        # --- SECCIÓN 1: Descarga ---
        group_download = QGroupBox("1. Descarga e Instalación")
        layout_download = QVBoxLayout()

        saved_path = core.get_setting("influx_path")
        if not saved_path:
            neighbor_path = core.get_setting("mosquitto_path") or core.get_setting("telegraf_path")
            if neighbor_path:
                parent_folder = os.path.dirname(neighbor_path)
                saved_path = os.path.join(parent_folder, "InfluxDB3_Core")
            else:
                saved_path = "C:\\InfluxDB3_Core"

        layout_download.addWidget(QLabel("Carpeta de destino:"))
        self.path_input = QLineEdit(saved_path)
        btn_browse = QPushButton("Seleccionar...")
        btn_browse.clicked.connect(self.select_folder)

        layout_download.addWidget(self.path_input)
        layout_download.addWidget(btn_browse)

        default_url = "https://dl.influxdata.com/influxdb/releases/influxdb3-core-3.8.0-windows_amd64.zip"
        saved_url = core.get_setting("influx_url", default_url)

        self.url_input = QLineEdit(saved_url)
        layout_download.addWidget(QLabel("URL del ZIP:"))
        layout_download.addWidget(self.url_input)

        group_download.setLayout(layout_download)
        layout.addWidget(group_download)

        # --- SECCIÓN 2: Configuración ---
        group_config = QGroupBox("2. Parámetros")
        layout_config = QFormLayout()

        saved_node = core.get_setting("influx_node", "Asus_ROG")
        saved_data = core.get_setting("influx_data_dir", "databases/shmdatabase")

        self.input_node_id = QLineEdit(saved_node)
        self.input_data_dir = QLineEdit(saved_data)

        layout_config.addRow("Node ID:", self.input_node_id)
        layout_config.addRow("Data Dir:", self.input_data_dir)

        group_config.setLayout(layout_config)
        layout.addWidget(group_config)

        # --- LOGS ---
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background: #0f0f0f; color: #00ff00; font-family: Consolas;")
        layout.addWidget(self.log_area)

        # --- BOTONES DE ACCIÓN ---
        # Botón 1: Descargar y Crear BATs
        self.btn_run = QPushButton("PASO 1: DESCARGAR Y GENERAR SCRIPTS .BAT")
        self.btn_run.setStyleSheet("background-color: #D0021B; color: white; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.start_process)
        layout.addWidget(self.btn_run)

        # Botón 2: Leer el Token (NUEVO)
        self.btn_read_token = QPushButton("PASO 2: LEER Y GUARDAR TOKEN (Post-Ejecución)")
        self.btn_read_token.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold; padding: 10px;")
        self.btn_read_token.setToolTip("Úsalo DESPUÉS de haber ejecutado '2_GENERAR_TOKEN.bat' en la carpeta")
        self.btn_read_token.clicked.connect(self.extract_token_process)
        layout.addWidget(self.btn_read_token)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Seleccionar Carpeta")
        if folder: self.path_input.setText(os.path.normpath(folder))

    def start_process(self):
        self.btn_run.setEnabled(False)
        target = self.path_input.text()
        url = self.url_input.text()
        node = self.input_node_id.text()
        data_path = self.input_data_dir.text()  # Ej: "databases/shmdatabase"

        # --- LÓGICA DE TRADUCCIÓN PARA TELEGRAF ---

        # 1. Extraer el nombre del Bucket desde la ruta
        # Si la ruta es "databases/shmdatabase", el bucket es "shmdatabase"
        bucket_name = os.path.basename(os.path.normpath(data_path))

        # 2. Definir una Organización por defecto (InfluxDB 3 suele usar 'docs' o vacía,
        # pero Telegraf necesita algo escrito).
        org_name = "docs"

        # --- GUARDAR EN EL CEREBRO COMPARTIDO (JSON) ---
        core.save_setting("influx_path", target)
        core.save_setting("influx_url", url)
        core.save_setting("influx_node", node)
        core.save_setting("influx_data_dir", data_path)

        # AQUÍ ESTÁ LA MAGIA: Guardamos las claves que Telegraf está buscando
        core.save_setting("influx_bucket", bucket_name)
        core.save_setting("influx_org", org_name)

        def task(log_callback):
            log_callback("--- Paso 1: Descargando ---")
            success, msg = core.download_and_extract(url, target, log_callback)

            if success:
                log_callback("\n--- Paso 2: Creando Scripts Personalizados ---")
                ok, msg_conf = core.setup_influx3_scripts(target, node, data_path, log_callback)

                if ok:
                    log_callback("\n[¡PROCESO FINALIZADO!]")
                    log_callback(f"Configuración guardada para Telegraf:")
                    log_callback(f" >> Bucket detectado: {bucket_name}")
                    log_callback(f" >> Org por defecto: {org_name}")
                    log_callback("------------------------------------------------")
                    log_callback(f"Ve a la carpeta: {target}")
                    log_callback("1. Ejecuta '1_INICIAR_SERVER.bat'")
                    log_callback("2. Ejecuta '2_GENERAR_TOKEN.bat'")
                    log_callback("3. Vuelve y presiona 'PASO 2: LEER TOKEN'")
                else:
                    log_callback(f"[ERROR Configuración]: {msg_conf}")
            else:
                log_callback(f"[ERROR Descarga]: {msg}")

        self.worker = WorkerThread(task)
        self.worker.log_signal.connect(self.log_area.append)
        self.worker.finished_signal.connect(lambda: self.btn_run.setEnabled(True))
        self.worker.start()

    # --- NUEVA FUNCIÓN PARA LEER EL TOKEN ---
    def extract_token_process(self):
        target = self.path_input.text()

        # Usamos una función lambda pequeña para el worker
        def task(log_callback):
            log_callback("\n--- Buscando token en credenciales_admin.txt ---")

            # Llamamos a la nueva función de core
            found, result = core.extract_token_from_file(target, log_callback)

            if found:
                token = result
                # GUARDAMOS EL TOKEN EN EL CEREBRO COMPARTIDO
                core.save_setting("influx_token", token)

                log_callback(f"\n[¡ÉXITO!]")
                log_callback(f"Token guardado en config.json.")
                log_callback("Ahora ve a la ventana de TELEGRAF, el token aparecerá automáticamente.")
            else:
                log_callback(f"[ERROR]: {result}")
                log_callback("Asegúrate de haber ejecutado el archivo .bat primero.")

        self.worker_token = WorkerThread(task)
        self.worker_token.log_signal.connect(self.log_area.append)
        self.worker_token.start()