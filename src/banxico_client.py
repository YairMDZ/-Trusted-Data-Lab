"""
Cliente ético para la API SIE de Banco de México (Banxico).
Extrae series macroeconómicas y de inflación relevantes para el análisis
de costos y demanda de insumos escolares en Colima.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import requests

from config import (
    BRONZE_DIR,
    BANXICO_API_TOKEN,
    REQUEST_PAUSE_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("banxico_client")

# Series oficiales del Sistema de Información Económica (SIE) de Banxico:
# SP1: Índice General Mensual INPC (Histórico de décadas)
# SP74625: Subíndice Subyacente del INPC mensual (Precios estables de mercancías)
# SF43718: Tipo de cambio FIX (pesos por dólar) - Relevante para compras al mayoreo
DEFAULT_SERIES = {
    "SP1": "INPC General Mensual (Banxico SIE)",
    "SP74625": "INPC Canasta Subyacente Mensual",
    "SF43718": "Tipo de Cambio para solventar obligaciones (FIX)",
}


def fetch_banxico_series(series_ids: List[str], token: str) -> Optional[Dict]:
    """
    Consulta una o varias series en la API SIE de Banxico mediante llamada HTTP GET.
    Autenticación por encabezado Bmx-Token para máxima seguridad.
    """
    series_query = ",".join(series_ids)
    url = f"https://www.banxico.org.mx/SieAPIRest/service/v1/series/{series_query}/datos"

    headers = {
        "Bmx-Token": token,
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    try:
        logger.info("Consultando serie(s) Banxico: %s...", series_query)
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)

        if response.status_code == 200:
            return response.json()
        elif response.status_code in (401, 403):
            logger.error("Error de autenticación con Banxico SIE (código %s). Verifica BANXICO_API_TOKEN.", response.status_code)
            return None
        else:
            logger.warning("Banxico respondió con código HTTP %s para series %s", response.status_code, series_query)
            return None
    except requests.exceptions.RequestException as e:
        logger.error("Error de conexión al consultar Banxico: %s", e)
        return None


def run_extraction(series_dict: Optional[Dict[str, str]] = None) -> Path:
    """
    Ejecuta la extracción de series de Banxico y almacena el resultado crudo
    en datos/bronce/banxico_series_raw.json.
    """
    if not BANXICO_API_TOKEN:
        logger.error(
            "Falta la variable de entorno BANXICO_API_TOKEN. "
            "Defínela en tu archivo .env o en los secretos de GitHub Actions."
        )
        sys.exit(1)

    series_map = series_dict or DEFAULT_SERIES
    series_keys = list(series_map.keys())

    payload = fetch_banxico_series(series_keys, BANXICO_API_TOKEN)

    results = {
        "metadata": {
            "fuente": "Banco de México - Sistema de Información Económica (SIE)",
            "fecha_extraccion": datetime.now(timezone.utc).isoformat(),
            "atribucion": "Fuente: Banco de México (Banxico), Sistema de Información Económica",
            "sector": "Comercio minorista de dulces, botanas y bebidas frías en puestos escolares",
            "series_solicitadas": series_map,
        },
        "respuesta_cruda": payload,
    }

    output_path = BRONZE_DIR / "banxico_series_raw.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("Extracción de Banxico completada con éxito. Archivo guardado en: %s", output_path)
    return output_path


if __name__ == "__main__":
    run_extraction()
