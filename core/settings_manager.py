import json
import os

SETTINGS_FILE = "config.json"

def load_settings():
    """Carga la configuración desde el archivo JSON (si existe)."""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def get_setting(key, default_value=None):
    """Obtiene un valor guardado. Si no existe, devuelve el valor por defecto."""
    data = load_settings()
    return data.get(key, default_value)

def save_setting(key, value):
    """Guarda un valor en el archivo JSON."""
    data = load_settings()
    data[key] = value
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        print(f"Error guardando config: {e}")
        return False