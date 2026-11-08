"""
Script de validación para la capa de datos/bronce/.
Utiliza exclusivamente la biblioteca estándar de Python (json, pathlib, sys).
Verifica integridad de archivos JSON, estructura de metadatos, atribución
y presencia de observaciones en las series extraídas de INEGI y Banxico.
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Tuple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("validar_bronce")

BASE_DIR = Path(__file__).resolve().parent.parent
BRONZE_DIR = BASE_DIR / "datos" / "bronce"


def validar_archivo_json(filepath: Path) -> Tuple[bool, str, Dict]:
    """
    Verifica que el archivo exista, no esté vacío y contenga JSON válido.
    """
    if not filepath.exists():
        return False, f"El archivo no existe: {filepath.name}", {}

    if filepath.stat().st_size == 0:
        return False, f"El archivo está vacío (0 bytes): {filepath.name}", {}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return True, "JSON válido", data
    except json.JSONDecodeError as e:
        return False, f"Error al parsear JSON en {filepath.name}: {e}", {}
    except Exception as e:
        return False, f"Error inesperado al leer {filepath.name}: {e}", {}


def validar_metadatos_base(data: Dict, nombre_archivo: str) -> List[str]:
    """
    Verifica que el objeto contenga los campos mínimos de auditoría y atribución.
    """
    errores = []
    meta = data.get("metadata") or data.get("metadata_extraccion")
    if not meta or not isinstance(meta, dict):
        errores.append(f"[{nombre_archivo}] Falta el bloque obligatorio de metadatos ('metadata' o 'metadata_extraccion')")
        return errores

    if "fuente" not in meta or not str(meta["fuente"]).strip():
        errores.append(f"[{nombre_archivo}] Campo de metadata ausente o vacío: 'fuente'")

    return errores


def validar_inegi(data: Dict) -> Tuple[bool, List[str], int]:
    """
    Valida la estructura específica esperada de los datos de INEGI.
    Soporta formato con clave 'series' o 'indicadores'.
    """
    errores = []
    total_observaciones = 0

    series_dict = data.get("series") or data.get("indicadores")
    if not series_dict or not isinstance(series_dict, dict):
        errores.append("[inegi] No contiene el diccionario de series ('series' o 'indicadores')")
        return False, errores, total_observaciones

    for ind_id, payload in series_dict.items():
        # Puede venir como {"data": {...}} o el payload directo devuelto por INEGI
        raw_inegi = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload

        if not raw_inegi or not isinstance(raw_inegi, dict):
            errores.append(f"[inegi] Indicador {ind_id} sin datos válidos")
            continue

        series_list = raw_inegi.get("Series", [])
        if not series_list:
            errores.append(f"[inegi] Indicador {ind_id} no contiene lista 'Series'")
            continue

        for serie in series_list:
            obs = serie.get("OBSERVATIONS", [])
            total_observaciones += len(obs)
            if len(obs) == 0:
                errores.append(f"[inegi] Serie en indicador {ind_id} tiene 0 observaciones")

    es_valido = len(errores) == 0
    return es_valido, errores, total_observaciones


def validar_banxico(data: Dict) -> Tuple[bool, List[str], int]:
    """
    Valida la estructura específica devuelta por la API SIE de Banxico.
    """
    errores = []
    total_observaciones = 0

    if "respuesta_cruda" not in data or data["respuesta_cruda"] is None:
        errores.append("[banxico_series_raw.json] Falta o es nula 'respuesta_cruda'")
        return False, errores, total_observaciones

    bmx = data["respuesta_cruda"].get("bmx", {})
    series = bmx.get("series", [])

    if not series:
        errores.append("[banxico_series_raw.json] 'bmx.series' no contiene series o está vacío")
        return False, errores, total_observaciones

    for s in series:
        datos = s.get("datos", [])
        total_observaciones += len(datos)
        if len(datos) == 0:
            errores.append(f"[banxico_series_raw.json] Serie {s.get('idSerie', 'desconocida')} sin datos")

    es_valido = len(errores) == 0
    return es_valido, errores, total_observaciones


def main() -> int:
    logger.info("Iniciando validación de la capa de datos/bronce/...")

    if not BRONZE_DIR.exists():
        logger.error("El directorio de datos/bronce no existe: %s", BRONZE_DIR)
        return 1

    patrones_esperados = [
        ("inegi_inpc_raw*.json", validar_inegi),
        ("banxico_series_raw*.json", validar_banxico),
    ]

    todos_los_errores: List[str] = []
    archivos_revisados = 0

    for patron, validador_especifico in patrones_esperados:
        archivos_encontrados = list(BRONZE_DIR.glob(patron))

        if not archivos_encontrados:
            logger.warning("No se encontraron archivos con el patrón: %s", patron)
            continue

        for ruta in archivos_encontrados:
            nombre_archivo = ruta.name
            archivos_revisados += 1
            logger.info("Validando integridad de: %s", nombre_archivo)

            valido_json, msg_json, data = validar_archivo_json(ruta)
            if not valido_json:
                todos_los_errores.append(msg_json)
                continue

            errores_meta = validar_metadatos_base(data, nombre_archivo)
            todos_los_errores.extend(errores_meta)

            valido_esp, errores_esp, total_obs = validador_especifico(data)
            todos_los_errores.extend(errores_esp)

            if valido_esp and not errores_meta:
                logger.info("-> %s APROBADO: Estructura íntegra (%d observaciones registradas).", nombre_archivo, total_obs)

    if archivos_revisados == 0:
        logger.warning("No se encontraron archivos JSON para validar en datos/bronce/. Ejecuta los extractores primero.")
        return 0

    print("\n" + "=" * 60)
    print("RESUMEN DE CALIDAD DE LA CAPA BRONCE")
    print("=" * 60)

    if todos_los_errores:
        logger.error("Se detectaron %d errores de calidad en la capa bronce:", len(todos_los_errores))
        for err in todos_los_errores:
            print(f"  [FALLO] {err}")
        return 1

    logger.info("Todos los archivos en datos/bronce/ pasaron satisfactoriamente la validación.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
