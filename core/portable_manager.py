import os
import zipfile
import urllib.request
import shutil
import ssl
import re

def download_and_extract(url, target_folder, log_callback=None):
    try:
        # Setup SSL context to avoid certificate errors on certain networks
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        # 1. Define temporary path for the zip file
        file_name = url.split('/')[-1]
        zip_file_path = os.path.join(target_folder, file_name)

        if log_callback:
            log_callback(f"Descargando desde: {url}...")

        # --- FIX: Create a request object with a standard User-Agent ---
        request_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        http_request = urllib.request.Request(url, headers=request_headers)

        # Pass the http_request object instead of the raw string url
        with urllib.request.urlopen(http_request, context=ssl_context) as http_response, open(zip_file_path, 'wb') as output_file:
            shutil.copyfileobj(http_response, output_file)

        if log_callback:
            log_callback("Descarga completada. Descomprimiendo...")

        # 3. Extract the downloaded zip file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_reference:
            zip_reference.extractall(target_folder)

        # 4. Cleanup (remove the zip file to save space)
        try:
            os.remove(zip_file_path)
        except:
            pass  # If it cannot be deleted, it is not critical

        if log_callback:
            log_callback("Descompresión finalizada.")
        return True, "Proceso completado"

    except Exception as error_msg:
        return False, str(error_msg)


def create_launcher_bat(target_folder, exe_name, log_callback=None):
    """
    Busca el .exe (incluso si está dentro de subcarpetas) y crea un .bat en la raíz.
    """
    exe_path = None

    # Buscar el ejecutable recursivamente
    for root, dirs, files in os.walk(target_folder):
        if exe_name in files:
            exe_path = os.path.join(root, exe_name)
            break

    if not exe_path:
        return False, f"No se encontró {exe_name} en la carpeta."

    # Crear el contenido del .bat
    bat_content = f"""@echo off
echo Iniciando InfluxDB Portable...
echo Para salir presiona Ctrl+C
echo ------------------------------
"{exe_path}"
pause
"""
    bat_path = os.path.join(target_folder, "INICIAR_INFLUX.bat")

    try:
        with open(bat_path, "w") as f:
            f.write(bat_content)
        if log_callback: log_callback(f"Creado lanzador en: {bat_path}")
        return True, bat_path
    except Exception as e:
        return False, str(e)


def setup_influx3_scripts(target_folder, node_id, data_dir, log_callback=None):
    """
    Crea los scripts .bat específicos para InfluxDB 3 Core con los parámetros del usuario.
    """
    exe_name = "influxdb3.exe"  # Buscamos este nombre primero
    exe_path = None

    # 1. Buscar el ejecutable (puede llamarse influxd.exe o influxdb3.exe)
    for root, dirs, files in os.walk(target_folder):
        if "influxdb3.exe" in files:
            exe_path = os.path.join(root, "influxdb3.exe")
            break
        elif "influxd.exe" in files:  # Por si acaso descargan una versión con el nombre antiguo
            exe_path = os.path.join(root, "influxd.exe")
            break

    if not exe_path:
        return False, "No se encontró influxdb3.exe ni influxd.exe"

    # 2. Crear script del SERVIDOR
    # Usamos comillas en las rutas por si hay espacios
    server_bat = os.path.join(target_folder, "1_INICIAR_SERVER.bat")
    server_content = f"""@echo off
title InfluxDB 3 Server - Node: {node_id}
echo Iniciando servidor...
echo Data Dir: {data_dir}
echo ------------------------------------------
"{exe_path}" serve --node-id {node_id} --object-store file --data-dir "{data_dir}"
pause
"""

    # 3. Crear script del TOKEN (Guarda en credentials.txt)
    token_bat = os.path.join(target_folder, "2_GENERAR_TOKEN.bat")
    credentials_file = os.path.join(target_folder, "credenciales_admin.txt")

    # El comando >> agrega el resultado al final del archivo txt
    token_content = f"""@echo off
echo Generando Token de Admin...
echo ------------------------------------------
echo Fecha: %date% %time% >> "{credentials_file}"
echo Node ID: {node_id} >> "{credentials_file}"

echo Ejecutando comando...
"{exe_path}" create token --admin >> "{credentials_file}"

echo.
echo [EXITO] La informacion se ha guardado en: 
echo {credentials_file}
echo.
pause
"""

    try:
        with open(server_bat, "w") as f:
            f.write(server_content)
        with open(token_bat, "w") as f:
            f.write(token_content)

        if log_callback:
            log_callback(f"Script Server creado: {server_bat}")
            log_callback(f"Script Token creado: {token_bat}")

        return True, "Scripts configurados"
    except Exception as e:
        return False, str(e)


def setup_telegraf_portable(target_folder, influx_url, influx_token, org, bucket, mqtt_user, mqtt_pass,
                            log_callback=None):
    """
    Configura Telegraf Portable con el esquema específico MQTT -> InfluxDB v2
    """
    exe_name = "telegraf.exe"
    exe_path = None
    base_dir = None

    # 1. Buscar el ejecutable
    for root, dirs, files in os.walk(target_folder):
        if exe_name in files:
            exe_path = os.path.join(root, exe_name)
            base_dir = root
            break

    if not exe_path:
        return False, "No se encontró telegraf.exe"

    # 2. Crear telegraf.conf con TU ESQUEMA
    conf_path = os.path.join(base_dir, "telegraf.conf")

    # Inyectamos las variables en tu plantilla
    config_content = f"""
# --- CONFIGURACIÓN GENERADA AUTOMÁTICAMENTE ---

[agent]
  # Ajustamos los intervalos para cumplir con "Batch writes" (Lotes)
  interval = "10s"
  round_interval = true
  metric_batch_size = 10000    # InfluxDB prefiere lotes grandes (hasta 10,000 líneas)
  metric_buffer_limit = 3600000
  collection_jitter = "0s"
  flush_interval = "10s"       # Enviamos cada 10s en lugar de 1s para no saturar la red HTTP
  flush_jitter = "0.1s"
  omit_hostname = true         # Esto cumple con no enviar basura extra (tagexclude)
  precision = "1ns"            # Clave: El ESP32 envía nanosegundos al añadir "000000"

# --- ENTRADA: MQTT (Mosquitto) ---
[[inputs.mqtt_consumer]]
  # Apuntamos al puerto 1884 que configuramos en Mosquitto
  servers = ["tcp://127.0.0.1:1884"]

  # Credenciales de Mosquitto (Variables del programa)
  username = "{mqtt_user}"
  password = "{mqtt_pass}"

  # Escuchamos tanto los datos de los sensores como las estadísticas
  topics = [
    "shm/+/data",
    "shm/+/stats"
  ]

  data_format = "influx"
  
# --- PROCESAMIENTO OPCIONAL (Recomendado por la doc) ---
# Elimina puntos duplicados exactos en caso de retransmisiones MQTT
#[[processors.dedup]]
    #dedup_interval = "10s"

# --- SALIDA: INFLUXDB V2 ---
[[outputs.influxdb_v2]]
  urls = ["{influx_url}"]
  token = "{influx_token}"
  bucket = "{bucket}"
  organization = "{org}"
  
  # OPTIMIZACIÓN CRÍTICA: Comprime el payload masivo de arrays hasta un 80%
  content_encoding = "gzip"
"""
    try:
        with open(conf_path, "w") as f:
            f.write(config_content)
        if log_callback: log_callback(f"Configuración MQTT->Influx guardada en: {conf_path}")
    except Exception as e:
        return False, f"Error escribiendo conf: {e}"

    # 3. Crear el BAT de arranque
    bat_path = os.path.join(target_folder, "4. INICIAR_TELEGRAF.bat")

    bat_content = f"""@echo off
title Telegraf Gateway (MQTT -> InfluxDB)
echo ---------------------------------------------------
echo INICIANDO TELEGRAF
echo Conf: "{conf_path}"
echo ---------------------------------------------------
echo.
"{exe_path}" --config "{conf_path}"
if %errorlevel% neq 0 pause
"""
    try:
        with open(bat_path, "w") as f:
            f.write(bat_content)
        return True, bat_path
    except Exception as e:
        return False, f"Error escribiendo bat: {e}"


def extract_token_from_file(target_folder, log_callback=None):
    """
    Lee el archivo credenciales_admin.txt, ignora los colores ANSI
    y extrae el token que empieza por 'apiv3_'.
    """
    file_path = os.path.join(target_folder, "credenciales_admin.txt")

    if not os.path.exists(file_path):
        return None, "No se encontró el archivo 'credenciales_admin.txt'. Ejecuta el BAT primero."

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Explicación del REGEX:
        # apiv3_      -> Busca textualmente esto
        # [a-zA-Z0-9\-_]+ -> Seguido de cualquier letra, número, guion o guion bajo
        match = re.search(r'(apiv3_[a-zA-Z0-9\-_]+)', content)

        if match:
            token = match.group(1)
            if log_callback: log_callback(f"Token detectado: {token[:10]}... (oculto)")
            return True, token
        else:
            return False, "No se encontró ningún patrón 'apiv3_' en el archivo."

    except Exception as e:
        return False, str(e)