"""
Cliente ético para la API de Indicadores del INEGI (INPC mensual por genérico).
Extrae series de precios de insumos relevantes para puestos escolares de dulces,
botanas y bebidas frías en Colima.
"""

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional
import requests

from config import (
    BRONZE_DIR,
    INEGI_API_TOKEN,
    REQUEST_PAUSE_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("inegi_client")

# Series oficiales verificadas en la API BIE-BISE del INEGI (INPC mensual):
# 628194: INPC General Mensual (Nacional, base 2018 = 100)
# 628204: INPC Alimentos, bebidas y tabaco
# 628217: INPC Refrescos envasados
# 628218: INPC Azúcar
DEFAULT_INDICATORS = {
    "628194": "INPC General Mensual (Nacional, Base 2018)",
    "628204": "INPC Alimentos, Bebidas y Tabaco",
    "628217": "INPC Refrescos Envasados",
    "628218": "INPC Azucar",
}


def fetch_inegi_indicator(
    indicator_id: str,
    token: str,
    geographic_area: str = "00",
) -> Optional[Dict]:
    """
    Consulta un indicador del INEGI respetando pausas y cabeceras éticas.
    geographic_area: '00' para cobertura nacional.
    """
    # Endpoint oficial verificado en BIE-BISE versión 2.0
    url = f"https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{indicator_id}/es/{geographic_area}/false/BIE-BISE/2.0/{token}?type=json"

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    try:
        logger.info("Consultando indicador INEGI %s...", indicator_id)
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)

        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code in (401, 403):
            logger.error("Error de autenticación con INEGI (código %s). Verifica INEGI_API_TOKEN.", response.status_code)
            return None
        else:
            logger.warning(
                "INEGI respondió con código %s para indicador %s",
                response.status_code,
                indicator_id,
            )
            return None
    except requests.exceptions.RequestException as e:
        logger.error("Error de conexión al consultar INEGI %s: %s", indicator_id, e)
        return None


def run_extraction(indicators: Optional[Dict[str, str]] = None) -> Path:
    """
    Ejecuta el proceso de extracción para los indicadores seleccionados y guarda
    el resultado crudo en la capa de datos/bronce/inegi_inpc_raw.json.
    """
    if not INEGI_API_TOKEN:
        logger.error(
            "Falta la variable de entorno INEGI_API_TOKEN. "
            "Defínela en tu archivo .env o en los secretos de GitHub Actions."
        )
        sys.exit(1)

    indicators_to_fetch = indicators or DEFAULT_INDICATORS
    results = {
        "metadata": {
            "fuente": "INEGI - API de Indicadores (INPC)",
            "fecha_extraccion": datetime.now(timezone.utc).isoformat(),
            "atribucion": "Fuente: Instituto Nacional de Estadística y Geografía (INEGI)",
            "sector": "Comercio minorista de dulces, botanas y bebidas frías en puestos escolares",
            "region": "Colima, México / Nacional",
            "total_indicadores_solicitados": len(indicators_to_fetch),
        },
        "indicadores": {},
    }

    for idx, (ind_id, description) in enumerate(indicators_to_fetch.items()):
        payload = fetch_inegi_indicator(ind_id, INEGI_API_TOKEN)
        results["indicadores"][ind_id] = {
            "descripcion": description,
            "data": payload,
        }

        # Pausa ética entre peticiones consecutivas
        if idx < len(indicators_to_fetch) - 1:
            logger.info("Pausa ética de %s segundos...", REQUEST_PAUSE_SECONDS)
            time.sleep(REQUEST_PAUSE_SECONDS)

    output_path = BRONZE_DIR / "inegi_inpc_raw.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info("Extracción de INEGI completada con éxito. Archivo guardado en: %s", output_path)
    return output_path


if __name__ == "__main__":
    run_extraction()
