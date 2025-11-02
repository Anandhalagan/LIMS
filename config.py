import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_config.json')

DEFAULTS = {
    "use_glass": False,
    "theme": "Premium Light",
    "inactivity_timeout_minutes": 30
}


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cfg = DEFAULTS.copy()
                cfg.update(data)
                return cfg
    except Exception:
        pass
    return DEFAULTS.copy()


def save_config(cfg):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, indent=2)
        return True
    except Exception:
        return False
