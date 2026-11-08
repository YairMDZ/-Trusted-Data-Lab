"""
Módulo de Configuración Central - Observatorio de Datos
Maneja variables de entorno, rutas del proyecto y encabezados HTTP éticos
usando únicamente la biblioteca estándar de Python.
"""

import os
from pathlib import Path

# Rutas principales del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
BRONZE_DIR = BASE_DIR / "datos" / "bronce"
DOCS_DIR = BASE_DIR / "docs" / "E0"

# Asegurar existencia de la carpeta de bronce
BRONZE_DIR.mkdir(parents=True, exist_ok=True)


def load_env_file(filepath: Path = BASE_DIR / ".env") -> None:
    """
    Carga variables de un archivo .env local si existe, sin sobreescribir
    variables de entorno ya establecidas en el sistema u orquestador (GitHub Actions).
    Implementación nativa sin dependencias externas.
    """
    if not filepath.exists():
        return

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            # Ignorar líneas vacías o comentarios
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, val = stripped.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = val


# Cargar variables de .env al importar el módulo
load_env_file()

# Lectura estricta de tokens
INEGI_API_TOKEN = os.getenv("INEGI_API_TOKEN", "").strip()
BANXICO_API_TOKEN = os.getenv("BANXICO_API_TOKEN", "").strip()

# Encabezados éticos e identificables
USER_AGENT = "ObservatorioEscolarColima/1.0 (InvestigacionAcademica; contacto: observatorio.escolar@colima.edu.mx)"
REQUEST_TIMEOUT_SECONDS = 30
REQUEST_PAUSE_SECONDS = 1.5
