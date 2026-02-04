import os
import zipfile
import urllib.request
import shutil
import ssl
import re


def download_and_extract(url, target_folder, log_callback=None):
    """
    Descarga un ZIP y lo descomprime en la carpeta destino.
    """
    try:
        # Configuración para evitar errores de certificados SSL en algunas redes
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        # 1. Definir ruta temporal para el zip
        filename = url.split('/')[-1]
        zip_path = os.path.join(target_folder, filename)

        if log_callback: log_callback(f"Descargando desde: {url}...")

        # --- CORRECCIÓN AQUÍ ---
        # El orden correcto es: (URL, RUTA_LOCAL)
        # Antes estaba al revés y por eso daba error "url type: c"
        with urllib.request.urlopen(url, context=ctx) as response, open(zip_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)

        if log_callback: log_callback("Descarga completada. Descomprimiendo...")

        # 3. Descomprimir
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(target_folder)

        # 4. Limpieza (Borrar el zip para ahorrar espacio)
        try:
            os.remove(zip_path)
        except:
            pass  # Si no se puede borrar, no es crítico

        if log_callback: log_callback("Descompresión finalizada.")
        return True, "Proceso completado"

    except Exception as e:
        return False, str(e)


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
  flush_interval = "1s"
  metric_batch_size = 1000
  metric_buffer_limit = 20000
  omit_hostname = true

# --- ENTRADA: MQTT (Mosquitto) ---
[[inputs.mqtt_consumer]]
  # Apuntamos al puerto 1884 que configuramos en Mosquitto
  servers = ["tcp://127.0.0.1:1884"]

  # Credenciales de Mosquitto (Variables del programa)
  username = "{mqtt_user}"
  password = "{mqtt_pass}"

  topics = ["shm/+/data"]
  name_override = "shm_data"

  data_format = "json"
  json_time_key = "ts"
  json_time_format = "unix_ms"
  json_timezone = "UTC"

  # Parseo del Topic para extraer el device_id
  [[inputs.mqtt_consumer.topic_parsing]]
    topic = "shm/+/data"
    tags  = "_/device_id/_"

# --- SALIDA: INFLUXDB V2 ---
[[outputs.influxdb_v2]]
  urls = ["{influx_url}"]
  token = "{influx_token}"
  bucket = "{bucket}"
  organization = "{org}"
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