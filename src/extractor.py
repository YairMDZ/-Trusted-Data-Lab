"""
Extractor ético para el Observatorio de Datos (Puestos Escolares - Colima).
Descarga datos crudos sin transformar de las APIs oficiales de INEGI y Banxico.
Utiliza series activas oficiales con datos continuos hasta 2026 y 0 meses faltantes.
Almacena las respuestas en datos/bronce/ con timestamp en el nombre del archivo.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import requests

# ------------------------------------------------------------------------------
# 1. Rutas y configuración de carpetas
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
BRONZE_DIR = BASE_DIR / "datos" / "bronce"
LOGS_FILE = BASE_DIR / "extraccion.log"

BRONZE_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------
# 2. Configuración de Logging
# ------------------------------------------------------------------------------
logger = logging.getLogger("extractor_observatorio")
logger.setLevel(logging.INFO)

if not logger.handlers:
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(LOGS_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


# ------------------------------------------------------------------------------
# 3. Carga nativa de variables de entorno (.env)
# ------------------------------------------------------------------------------
def cargar_env_local(archivo_env: Path = BASE_DIR / ".env") -> None:
    if not archivo_env.exists():
        return

    with open(archivo_env, "r", encoding="utf-8") as f:
        for linea in f:
            linea_limpia = linea.strip()
            if not linea_limpia or linea_limpia.startswith("#"):
                continue
            if "=" in linea_limpia:
                clave, valor = linea_limpia.split("=", 1)
                clave = clave.strip()
                valor = valor.strip().strip("'").strip('"')
                if clave and clave not in os.environ:
                    os.environ[clave] = valor


cargar_env_local()

# Soporte para INEGI_API_TOKEN y BANXICO_API_TOKEN (con compatibilidad hacia INEGI_TOKEN / BANXICO_TOKEN)
INEGI_API_TOKEN = os.getenv("INEGI_API_TOKEN") or os.getenv("INEGI_TOKEN", "").strip()
BANXICO_API_TOKEN = os.getenv("BANXICO_API_TOKEN") or os.getenv("BANXICO_TOKEN", "").strip()

USER_AGENT = "ObservatorioEscolarColima/1.0 (Contacto: investigacion-escolar@colima.edu.mx)"
PAUSA_SEGUNDOS = 2.0
TIMEOUT_SEGUNDOS = 30


# ------------------------------------------------------------------------------
# 4. Series seleccionadas (Nombres oficiales literales de CL_INDICATOR)
# ------------------------------------------------------------------------------
# INEGI (INPC Base 2018, Actualización 2024 - Tema 189113, Fuente 3371):
SERIES_INEGI = {
    "910392": "Índice general",
    "910394": "Mercancías",
    "910395": "Servicios",
    "910397": "Agropecuarios",
}

# Banxico SIE:
# Se remueve SP1 para evitar duplicar el Índice General de INEGI (910392).
SERIES_BANXICO = {
    "SP74625": "Subíndice de la canasta subyacente (Precios de mercancías y servicios estables)",
    "SF43718": "Tipo de cambio FIX (Pesos por Dólar)",
}


# ------------------------------------------------------------------------------
# 5. Funciones de extracción
# ------------------------------------------------------------------------------
def verificar_tokens() -> None:
    errores = []
    if not INEGI_API_TOKEN:
        errores.append(
            "Falta el token de INEGI. Configura la variable de entorno 'INEGI_API_TOKEN' "
            "en tu archivo .env o en los secretos de GitHub."
        )
    if not BANXICO_API_TOKEN:
        errores.append(
            "Falta el token de Banxico. Configura la variable de entorno 'BANXICO_API_TOKEN' "
            "en tu archivo .env o en los secretos de GitHub."
        )

    if errores:
        for err in errores:
            logger.error(err)
        sys.exit(1)


def extraer_inegi(timestamp_str: str) -> Path:
    logger.info("Iniciando extracción de series activas INEGI (%d series)...", len(SERIES_INEGI))
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    respuestas_crudas: Dict[str, Any] = {
        "metadata_extraccion": {
            "fuente": "INEGI - API BIE-BISE v2.0 (Fuente 3371)",
            "fecha_extraccion_utc": datetime.now(timezone.utc).isoformat(),
            "user_agent": USER_AGENT,
            "series_solicitadas": SERIES_INEGI,
        },
        "series": {},
    }

    indicadores_lista = list(SERIES_INEGI.items())
    for idx, (ind_id, nombre_literal) in enumerate(indicadores_lista):
        url = f"https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{ind_id}/es/00/false/BIE-BISE/2.0/{INEGI_API_TOKEN}?type=json"

        try:
            logger.info("Consultando INEGI %s (%s)...", ind_id, nombre_literal)
            resp = requests.get(url, headers=headers, timeout=TIMEOUT_SEGUNDOS)

            if resp.status_code == 200:
                respuestas_crudas["series"][ind_id] = resp.json()
            elif resp.status_code in (401, 403):
                logger.error("Error de autenticación con INEGI (HTTP %s). Revisa INEGI_API_TOKEN.", resp.status_code)
                sys.exit(1)
            else:
                logger.warning("INEGI devolvió código HTTP %s para indicador %s", resp.status_code, ind_id)
                respuestas_crudas["series"][ind_id] = {"error_http": resp.status_code, "texto": resp.text}

        except requests.exceptions.RequestException as e:
            logger.error("Error de conexión al consultar INEGI %s: %s", ind_id, e)
            sys.exit(1)

        if idx < len(indicadores_lista) - 1:
            logger.info("Pausa ética de %.1f segundos...", PAUSA_SEGUNDOS)
            time.sleep(PAUSA_SEGUNDOS)

    archivo_destino = BRONZE_DIR / f"inegi_inpc_raw_{timestamp_str}.json"
    with open(archivo_destino, "w", encoding="utf-8") as f:
        json.dump(respuestas_crudas, f, ensure_ascii=False, indent=2)

    logger.info("Datos crudos de INEGI guardados en: %s", archivo_destino.name)
    return archivo_destino


def extraer_banxico(timestamp_str: str) -> Path:
    logger.info("Iniciando extracción de Banxico SIE (%d series en un lote)...", len(SERIES_BANXICO))
    series_query = ",".join(SERIES_BANXICO.keys())
    url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{series_query}/datos"

    headers = {
        "Bmx-Token": BANXICO_API_TOKEN,
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    try:
        logger.info("Consultando lote Banxico (%s)...", series_query)
        resp = requests.get(url, headers=headers, timeout=TIMEOUT_SEGUNDOS)

        if resp.status_code == 200:
            payload_crudo = resp.json()
        elif resp.status_code in (401, 403):
            logger.error("Error de autenticación con Banxico SIE (HTTP %s). Revisa BANXICO_API_TOKEN.", resp.status_code)
            sys.exit(1)
        else:
            logger.error("Banxico devolvió código HTTP %s", resp.status_code)
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        logger.error("Error de conexión al consultar Banxico: %s", e)
        sys.exit(1)

    contenido_final = {
        "metadata_extraccion": {
            "fuente": "Banco de México - API SIE",
            "fecha_extraccion_utc": datetime.now(timezone.utc).isoformat(),
            "user_agent": USER_AGENT,
            "series_solicitadas": SERIES_BANXICO,
        },
        "respuesta_cruda": payload_crudo,
    }

    archivo_destino = BRONZE_DIR / f"banxico_series_raw_{timestamp_str}.json"
    with open(archivo_destino, "w", encoding="utf-8") as f:
        json.dump(contenido_final, f, ensure_ascii=False, indent=2)

    logger.info("Datos crudos de Banxico guardados en: %s", archivo_destino.name)
    return archivo_destino


def main() -> None:
    logger.info("=================================================================")
    logger.info("INICIANDO EXTRACCIÓN CON SERIES REFINADAS A CAPA BRONCE")
    logger.info("=================================================================")

    verificar_tokens()

    timestamp_actual = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    ruta_inegi = extraer_inegi(timestamp_actual)

    logger.info("Pausa de transición entre APIs de %.1f segundos...", PAUSA_SEGUNDOS)
    time.sleep(PAUSA_SEGUNDOS)

    ruta_banxico = extraer_banxico(timestamp_actual)

    logger.info("=================================================================")
    logger.info("EXTRACCIÓN FINALIZADA CON ÉXITO")
    logger.info("Archivos generados en datos/bronce/:")
    logger.info("  - %s", ruta_inegi.name)
    logger.info("  - %s", ruta_banxico.name)
    logger.info("=================================================================")


if __name__ == "__main__":
    main()
