"""
Extractor ético para la Capa Bronce Geoespacial (Entrega E2).
Fuentes oficiales del INEGI:
1. Directorio Estadístico Nacional de Unidades Económicas (DENUE) — Estado de Colima (06).
2. Marco Geoestadístico (Límites Municipales de Colima, clave 06) vía INEGI GAIA wscatgeo v2.

Reglas de seguridad y buenas prácticas:
- Lee el token desde la variable de entorno INEGI_DENUE_TOKEN (con fallback a INEGI_API_TOKEN).
- Enmascara el token en logs, metadatos y mensajes de error (nunca lo imprime ni persiste).
- Usa User-Agent identificable, pausas de cortesía entre peticiones y timeouts sin reintentos agresivos.
- Persiste respuestas crudas sin transformar en datos/bronce/denue/ y datos/bronce/marco_geoestadistico/
  junto con un archivo de metadatos con hash SHA-256 por cada captura.
"""

import csv
import hashlib
import io
import json
import logging
import os
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests

# ------------------------------------------------------------------------------
# 1. Rutas y configuración base
# ------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent
BRONZE_DENUE_DIR = BASE_DIR / "datos" / "bronce" / "denue"
BRONZE_MG_DIR = BASE_DIR / "datos" / "bronce" / "marco_geoestadistico"

USER_AGENT = "ObservatorioEscolarColima/2.0 (Contacto: investigacion-escolar@colima.edu.mx)"
PAUSA_SEGUNDOS = 2.0
TIMEOUT_API_SEGUNDOS = 15
TIMEOUT_DESCARGA_SEGUNDOS = 60

ENTIDAD_COLIMA = "06"
MUNICIPIOS_COLIMA: Dict[str, str] = {
    "001": "Armería",
    "002": "Colima",
    "003": "Comala",
    "004": "Coquimatlán",
    "005": "Cuauhtémoc",
    "006": "Ixtlahuacán",
    "007": "Manzanillo",
    "008": "Minatitlán",
    "009": "Tecomán",
    "010": "Villa de Álvarez",
}

# Catálogo oficial SCIAN 2018 / 2023 (claves y nombres literales verificados en INEGI)
CATALOGO_SCIAN_ESTUDIO: Dict[str, Dict[str, str]] = {
    # Escuelas de educación básica (6111xx)
    "611111": {"categoria": "escuela_basica", "nombre_literal": "Escuelas de educación preescolar del sector privado"},
    "611112": {"categoria": "escuela_basica", "nombre_literal": "Escuelas de educación preescolar del sector público"},
    "611121": {"categoria": "escuela_basica", "nombre_literal": "Escuelas de educación primaria del sector privado"},
    "611122": {"categoria": "escuela_basica", "nombre_literal": "Escuelas de educación primaria del sector público"},
    "611131": {"categoria": "escuela_basica", "nombre_literal": "Escuelas de educación secundaria general del sector privado"},
    "611132": {"categoria": "escuela_basica", "nombre_literal": "Escuelas de educación secundaria general del sector público"},
    "611141": {"categoria": "escuela_basica", "nombre_literal": "Escuelas de educación secundaria técnica del sector privado"},
    "611142": {"categoria": "escuela_basica", "nombre_literal": "Escuelas de educación secundaria técnica del sector público"},
    "611171": {"categoria": "escuela_basica", "nombre_literal": "Escuelas del sector privado que combinan diversos niveles de educación"},
    "611172": {"categoria": "escuela_basica", "nombre_literal": "Escuelas del sector público que combinan diversos niveles de educación"},
    "611181": {"categoria": "escuela_basica", "nombre_literal": "Escuelas del sector privado de educación para necesidades especiales"},
    "611182": {"categoria": "escuela_basica", "nombre_literal": "Escuelas del sector público de educación para necesidades especiales"},
    # Comercio al por menor relevante al entorno escolar
    "461110": {"categoria": "abarrotes", "nombre_literal": "Comercio al por menor en tiendas de abarrotes, ultramarinos y misceláneas"},
    "461160": {"categoria": "dulces", "nombre_literal": "Comercio al por menor de dulces y materias primas para repostería"},
    "461170": {"categoria": "helados_paletas", "nombre_literal": "Comercio al por menor de paletas de hielo y helados"},
}

URL_DENUE_MASIVA_COLIMA = "https://www.inegi.org.mx/contenidos/masiva/denue/denue_06_csv.zip"
URL_MARCO_GEO_COLIMA_V2 = "https://gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/06"
URL_MARCO_GEO_COLIMA_V1 = "https://gaia.inegi.org.mx/wscatgeo/geo/mgem/06"
LICENCIA_INEGI = "Términos de Libre Uso de la Información del INEGI (https://www.inegi.org.mx/inegi/terminos.html)"

# ------------------------------------------------------------------------------
# 2. Logging seguro
# ------------------------------------------------------------------------------
logger = logging.getLogger("denue.extractor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_handler)


# ------------------------------------------------------------------------------
# 3. Utilidades de entorno, enmascarado y hash SHA-256
# ------------------------------------------------------------------------------
def cargar_env_local(archivo_env: Path = BASE_DIR / ".env") -> None:
    """Carga variables locales desde .env sin sobrescribir las del entorno."""
    if not archivo_env.exists():
        return
    with open(archivo_env, "r", encoding="utf-8") as fp:
        for linea in fp:
            linea_limpia = linea.strip()
            if not linea_limpia or linea_limpia.startswith("#") or "=" not in linea_limpia:
                continue
            clave, valor = linea_limpia.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip("'").strip('"')
            if clave and clave not in os.environ:
                os.environ[clave] = valor


def obtener_token_denue() -> Tuple[str, str]:
    """
    Lee el token del entorno priorizando INEGI_DENUE_TOKEN y con fallback a INEGI_API_TOKEN.
    Devuelve (token, nombre_variable_usada). Nunca registra el valor del token.
    """
    cargar_env_local()
    tok_denue = os.getenv("INEGI_DENUE_TOKEN", "").strip()
    if tok_denue:
        return tok_denue, "INEGI_DENUE_TOKEN"
    tok_api = os.getenv("INEGI_API_TOKEN", "").strip()
    if tok_api:
        return tok_api, "INEGI_API_TOKEN"
    return "", "NINGUNA"


def enmascarar_token(texto: str, token: Optional[str]) -> str:
    """Reemplaza cualquier aparición literal del token por '***MASKED***'."""
    if not texto or not token:
        return str(texto)
    return str(texto).replace(token, "***MASKED***")


def calcular_sha256(filepath: Path) -> str:
    """Calcula el digest SHA-256 de un archivo por bloques."""
    h = hashlib.sha256()
    with open(filepath, "rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class IntegrityError(RuntimeError):
    """Excepción lanzada si un archivo ya registrado no coincide con su hash oficial (corrupción)."""


def verificar_archivos_registrados(bronze_denue_dir: Path = BRONZE_DENUE_DIR) -> None:
    """
    Verifica que todos los archivos ZIP del DENUE ya registrados localmente
    coincidan estrictamente con el hash registrado en sus respectivos metadatos JSON.
    Solo aborta si un archivo previamente registrado fue alterado o está corrupto.
    """
    if not bronze_denue_dir.exists():
        return

    for meta_file in sorted(bronze_denue_dir.glob("denue_colima_metadata_*.json")):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            archivo_zip = bronze_denue_dir / meta.get("archivo_datos", "")
            if archivo_zip.exists():
                hash_actual = calcular_sha256(archivo_zip)
                hash_registrado = meta.get("sha256")
                if hash_actual != hash_registrado:
                    raise IntegrityError(
                        f"CORRUPCIÓN DETECTADA: El archivo ya registrado '{archivo_zip.name}' "
                        f"posee un SHA-256 ({hash_actual}) que no coincide con su metadato oficial ({hash_registrado}). "
                        f"Se aborta para prevenir inconsistencias en el repositorio."
                    )
        except json.JSONDecodeError:
            continue


# ------------------------------------------------------------------------------
# 4. Sonda cortés a API REST DENUE v1 + descarga cruda oficial de Colima
# ------------------------------------------------------------------------------
def sondear_api_denue_v1(token: str) -> Dict[str, Any]:
    """
    Realiza una única petición ligera de verificación (sin reintentos agresivos)
    al método Cuantificar de la API v1 del DENUE para Colima (clase 461160).
    El token queda estrictamente enmascarado en todos los retornos y logs.
    """
    url_base = "https://www.inegi.org.mx/app/api/denue/v1/consulta/Cuantificar/461160/06/0/{TOKEN}"
    if not token:
        return {
            "url_consulta_enmascarada": url_base.format(TOKEN="***NO_CONFIGURADO***"),
            "estado": "omitida_sin_token",
            "http_status": None,
            "detalle": "Variable INEGI_DENUE_TOKEN no definida en el entorno.",
        }

    url_real = url_base.format(TOKEN=token)
    url_enmascarada = enmascarar_token(url_real, token)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    logger.info("Verificando disponibilidad de API REST DENUE v1: %s", url_enmascarada)
    try:
        resp = requests.get(url_real, headers=headers, timeout=TIMEOUT_API_SEGUNDOS)
        cuerpo_seguro = enmascarar_token(resp.text[:250], token)
        if resp.status_code == 200 and "No autorizado" not in cuerpo_seguro and "Error interno" not in cuerpo_seguro:
            logger.info("API REST DENUE v1 respondió HTTP 200 (sonda exitosa).")
            return {
                "url_consulta_enmascarada": url_enmascarada,
                "estado": "disponible",
                "http_status": resp.status_code,
                "detalle": "Sonda exitosa; se utiliza descarga masiva oficial estatal para evitar >140 peticiones paginadas.",
            }
        logger.warning(
            "API REST DENUE v1 devolvió estado no utilizable (HTTP %s): %s",
            resp.status_code,
            cuerpo_seguro,
        )
        return {
            "url_consulta_enmascarada": url_enmascarada,
            "estado": "no_autorizado_o_error_servicio",
            "http_status": resp.status_code,
            "detalle": cuerpo_seguro,
        }
    except requests.exceptions.RequestException as exc:
        err_seguro = enmascarar_token(str(exc), token)
        logger.warning("API REST DENUE v1 no respondió a tiempo (%s). Se usará descarga masiva oficial INEGI.", err_seguro)
        return {
            "url_consulta_enmascarada": url_enmascarada,
            "estado": "timeout_o_error_conexion",
            "http_status": None,
            "detalle": err_seguro,
        }


def extraer_denue_colima(
    timestamp_str: str,
    bronze_denue_dir: Path = BRONZE_DENUE_DIR,
) -> Tuple[Path, Path, Dict[str, Any]]:
    """
    Descarga el archivo oficial crudo del DENUE para el estado de Colima (06)
    en datos/bronce/denue/ y guarda su archivo de metadatos con SHA-256.
    
    Regla de integridad y versiones de INEGI:
    - Verifica primero que ningún archivo ZIP ya registrado localmente esté corrupto.
    - Si INEGI publica una nueva versión del paquete masivo (con hash distinto al previo),
      se registra como nueva captura válida en el manifiesto con su fecha de corte.
    - Únicamente se aborta la ejecución si un archivo previamente registrado no coincide con su hash.
    """
    bronze_denue_dir.mkdir(parents=True, exist_ok=True)

    # 1. Verificar integridad de archivos históricos ya registrados
    verificar_archivos_registrados(bronze_denue_dir)

    token, var_token = obtener_token_denue()
    sonda_api = sondear_api_denue_v1(token)
    logger.info("Pausa ética de %.1f segundos antes de descargar paquete oficial DENUE Colima...", PAUSA_SEGUNDOS)
    time.sleep(PAUSA_SEGUNDOS)

    headers = {"User-Agent": USER_AGENT}
    logger.info("Descargando conjunto oficial crudo DENUE Colima (06): %s", URL_DENUE_MASIVA_COLIMA)
    try:
        resp = requests.get(URL_DENUE_MASIVA_COLIMA, headers=headers, timeout=TIMEOUT_DESCARGA_SEGUNDOS)
        if resp.status_code != 200 or not resp.content.startswith(b"PK\x03\x04"):
            raise RuntimeError(
                f"Respuesta inesperada de INEGI DENUE masivo: HTTP {resp.status_code}, "
                f"Content-Type={resp.headers.get('Content-Type')}, bytes={len(resp.content)}"
            )
    except requests.exceptions.RequestException as exc:
        err_seguro = enmascarar_token(str(exc), token)
        logger.error("Fallo en descarga oficial DENUE Colima: %s", err_seguro)
        raise RuntimeError(f"Error de red al descargar DENUE Colima: {err_seguro}") from exc

    fecha_ingesta_utc = datetime.now(timezone.utc).isoformat()
    archivo_zip = bronze_denue_dir / f"denue_colima_raw_{timestamp_str}.zip"
    archivo_zip.write_bytes(resp.content)

    sha256_zip = calcular_sha256(archivo_zip)
    tamano_bytes = archivo_zip.stat().st_size

    # Inspección de integridad (solo lectura) para reporte de conteos y fecha de corte oficial
    conteos = resumir_zip_denue(archivo_zip)
    if conteos["total_registros_zip"] == 0:
        raise ValueError("El archivo ZIP descargado del DENUE contiene 0 registros.")

    # 2. Comprobar contra versiones previas registradas
    hashes_previos: Dict[str, str] = {}
    for meta_file in sorted(bronze_denue_dir.glob("denue_colima_metadata_*.json")):
        if meta_file.name == f"denue_colima_metadata_{timestamp_str}.json":
            continue
        try:
            m = json.loads(meta_file.read_text(encoding="utf-8"))
            if m.get("sha256"):
                hashes_previos[meta_file.name] = m.get("sha256")
        except Exception:
            pass

    es_nueva_version = bool(hashes_previos and sha256_zip not in hashes_previos.values())
    if es_nueva_version:
        logger.info(
            "NUEVA VERSIÓN DETECTADA en INEGI DENUE: el hash SHA-256 (%s...) "
            "difiere de la versión registrada anterior (%s...). "
            "Se registra como nueva captura válida en el manifiesto con fecha de corte %s.",
            sha256_zip[:16],
            list(hashes_previos.values())[-1][:16],
            conteos.get("fecha_corte", "N/A"),
        )
    elif hashes_previos:
        logger.info(
            "El archivo descargado coincide con la versión oficial registrada (SHA-256: %s...).",
            sha256_zip[:16],
        )

    metadatos = {
        "fuente": "INEGI — Directorio Estadístico Nacional de Unidades Económicas (DENUE)",
        "version_servicio": "DENUE Descarga Masiva Estatal CSV (complementaria a API REST v1)",
        "fecha_ingesta_utc": fecha_ingesta_utc,
        "fecha_corte_denue": conteos.get("fecha_corte", "2026/05"),
        "nueva_version_inegi": es_nueva_version,
        "archivo_datos": archivo_zip.name,
        "tamano_bytes": tamano_bytes,
        "sha256": sha256_zip,
        "url_descarga_efectiva": URL_DENUE_MASIVA_COLIMA,
        "variable_token_detectada": var_token,
        "sonda_api_rest_v1": sonda_api,
        "parametros": {
            "entidad": ENTIDAD_COLIMA,
            "entidad_nombre": "Colima",
            "municipios": MUNICIPIOS_COLIMA,
            "clases_scian_estudio": CATALOGO_SCIAN_ESTUDIO,
        },
        "user_agent": USER_AGENT,
        "licencia": LICENCIA_INEGI,
        "resumen_integridad": {
            "archivo_csv_interno": conteos["archivo_csv_interno"],
            "fecha_corte": conteos.get("fecha_corte", "2026/05"),
            "total_registros_crudos_entidad": conteos["total_registros_zip"],
            "total_registros_clases_estudio": conteos["total_estudio"],
            "conteo_por_categoria": conteos["por_categoria"],
            "conteo_por_municipio": conteos["por_municipio"],
        },
    }

    archivo_meta = bronze_denue_dir / f"denue_colima_metadata_{timestamp_str}.json"
    meta_texto = json.dumps(metadatos, ensure_ascii=False, indent=2)
    # Doble salvaguarda: verificar que el token nunca aparezca en metadatos
    if token and token in meta_texto:
        raise SecurityError("Fuga potencial de token detectada en metadatos.")
    archivo_meta.write_text(meta_texto, encoding="utf-8")

    # Actualizar manifiesto de bronce si el módulo de linaje está disponible
    try:
        from src.pipeline.linaje import construir_manifiesto_bronce
        construir_manifiesto_bronce()
    except Exception as exc:
        logger.debug("Actualización de manifiesto diferida al pipeline principal: %s", exc)

    logger.info("DENUE crudo guardado en: %s (%s bytes, SHA-256: %s...)", archivo_zip.name, f"{tamano_bytes:,}", sha256_zip[:16])
    logger.info("Metadatos DENUE guardados en: %s", archivo_meta.name)
    return archivo_zip, archivo_meta, conteos


class SecurityError(RuntimeError):
    """Excepción lanzada si se detecta exposición de credenciales."""


def resumir_zip_denue(archivo_zip: Path) -> Dict[str, Any]:
    """Lee el CSV interno del ZIP crudo para reportar conteos por municipio, categoría y fecha de corte."""
    por_categoria: Counter = Counter()
    por_municipio: Counter = Counter()
    total_zip = 0
    total_estudio = 0
    csv_interno = ""
    fecha_corte = "2026/05"

    with zipfile.ZipFile(archivo_zip, "r") as zf:
        # Detectar fecha de corte oficial en metadatos_denue.txt si está disponible
        meta_candidatos = [n for n in zf.namelist() if "metadatos_denue.txt" in n.lower()]
        if meta_candidatos:
            try:
                txt_meta = zf.read(meta_candidatos[0]).decode("latin-1")
                import re
                m_corte = re.search(r"DENUE.*?(\d{2}_\d{4}|\d{4}-\d{2})", txt_meta)
                if m_corte:
                    fecha_corte = m_corte.group(1).replace("_", "/")
            except Exception:
                pass

        candidatos = [n for n in zf.namelist() if n.lower().endswith(".csv") and "conjunto_de_datos" in n.lower()]
        if not candidatos:
            candidatos = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not candidatos:
            raise ValueError(f"No se encontró ningún archivo CSV dentro de {archivo_zip.name}")
        csv_interno = candidatos[0]

        with zf.open(csv_interno, "r") as raw_fp:
            # Los CSV del DENUE de INEGI suelen venir en latin-1 / utf-8-sig
            raw_bytes = raw_fp.read()
            try:
                texto = raw_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                texto = raw_bytes.decode("latin-1")

            reader = csv.DictReader(io.StringIO(texto))
            for row in reader:
                total_zip += 1
                cod = str(row.get("codigo_act", "")).strip()
                if cod in CATALOGO_SCIAN_ESTUDIO:
                    total_estudio += 1
                    cat = CATALOGO_SCIAN_ESTUDIO[cod]["categoria"]
                    por_categoria[cat] += 1
                    cve_mun = str(row.get("cve_mun", "")).strip().zfill(3)
                    nom_mun = MUNICIPIOS_COLIMA.get(cve_mun, str(row.get("municipio", cve_mun)).strip())
                    por_municipio[f"{cve_mun} - {nom_mun}"] += 1

    return {
        "archivo_csv_interno": csv_interno,
        "fecha_corte": fecha_corte,
        "total_registros_zip": total_zip,
        "total_estudio": total_estudio,
        "por_categoria": dict(sorted(por_categoria.items())),
        "por_municipio": dict(sorted(por_municipio.items())),
    }


# ------------------------------------------------------------------------------
# 5. Extracción de límites municipales del Marco Geoestadístico (INEGI GAIA)
# ------------------------------------------------------------------------------
def extraer_marco_geoestadistico_colima(
    timestamp_str: str,
    bronze_mg_dir: Path = BRONZE_MG_DIR,
) -> Tuple[Path, Path, Dict[str, Any]]:
    """
    Descarga los polígonos oficiales de los 10 municipios de Colima (06) desde
    el Servicio Web del Catálogo Único de Áreas Geoestadísticas del INEGI (GAIA)
    y persiste el GeoJSON crudo junto con sus metadatos y SHA-256.
    """
    bronze_mg_dir.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    logger.info("Descargando Marco Geoestadístico (municipios de Colima 06): %s", URL_MARCO_GEO_COLIMA_V2)
    url_usada = URL_MARCO_GEO_COLIMA_V2
    try:
        resp = requests.get(URL_MARCO_GEO_COLIMA_V2, headers=headers, timeout=TIMEOUT_DESCARGA_SEGUNDOS)
        if resp.status_code != 200:
            logger.warning("wscatgeo v2 devolvió HTTP %s; intentando fallback v1...", resp.status_code)
            time.sleep(PAUSA_SEGUNDOS)
            url_usada = URL_MARCO_GEO_COLIMA_V1
            resp = requests.get(URL_MARCO_GEO_COLIMA_V1, headers=headers, timeout=TIMEOUT_DESCARGA_SEGUNDOS)
        if resp.status_code != 200:
            raise RuntimeError(f"INEGI GAIA devolvió HTTP {resp.status_code}")
        payload = resp.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as exc:
        logger.error("Error al descargar Marco Geoestadístico de Colima: %s", exc)
        raise RuntimeError(f"Error al descargar Marco Geoestadístico: {exc}") from exc

    features = payload.get("features", [])
    if len(features) != 10:
        raise ValueError(f"Se esperaban exactamente 10 municipios para Colima (06), se recibieron {len(features)}.")

    fecha_ingesta_utc = datetime.now(timezone.utc).isoformat()
    archivo_geojson = bronze_mg_dir / f"marco_geoestadistico_colima_municipios_{timestamp_str}.geojson"
    archivo_geojson.write_bytes(resp.content)

    sha256_geo = calcular_sha256(archivo_geojson)
    tamano_bytes = archivo_geojson.stat().st_size

    metadatos_mg = {
        "fuente": "INEGI — Marco Geoestadístico (Servicio Web GAIA wscatgeo)",
        "version_servicio": "wscatgeo v2 (GeoJSON oficial)",
        "metadatos_origen_inegi": payload.get("metadatos", {}),
        "crs_origen_declarado": payload.get("metadatos", {}).get("CRS", "EPSG:6365 (ITRF2008 geográfico, equivalente operacional a WGS84 EPSG:4326)"),
        "fecha_ingesta_utc": fecha_ingesta_utc,
        "archivo_datos": archivo_geojson.name,
        "tamano_bytes": tamano_bytes,
        "sha256": sha256_geo,
        "url_consulta": url_usada,
        "parametros": {"entidad": ENTIDAD_COLIMA, "nivel": "municipal (mgem)"},
        "total_poligonos_municipales": len(features),
        "user_agent": USER_AGENT,
        "licencia": LICENCIA_INEGI,
    }

    archivo_meta = bronze_mg_dir / f"marco_geoestadistico_colima_metadata_{timestamp_str}.json"
    archivo_meta.write_text(json.dumps(metadatos_mg, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info(
        "Marco Geoestadístico guardado en: %s (%s bytes, %d municipios, SHA-256: %s...)",
        archivo_geojson.name,
        f"{tamano_bytes:,}",
        len(features),
        sha256_geo[:16],
    )
    return archivo_geojson, archivo_meta, metadatos_mg


def main() -> int:
    logger.info("======================================================================")
    logger.info("INICIANDO EXTRACCIÓN ÉTICA GEOESPACIAL A CAPA BRONCE (DENUE + MARCO)")
    logger.info("======================================================================")

    timestamp_actual = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    archivo_denue, meta_denue, conteos = extraer_denue_colima(timestamp_actual)

    logger.info("Pausa ética de %.1f segundos entre servicios de INEGI...", PAUSA_SEGUNDOS)
    time.sleep(PAUSA_SEGUNDOS)

    archivo_mg, meta_mg, info_mg = extraer_marco_geoestadistico_colima(timestamp_actual)

    print("\n" + "=" * 74)
    print("RESUMEN DE CAPTURA CRUDA EN BRONCE — FASE 2 (DENUE + MARCO GEOESTADÍSTICO)")
    print("=" * 74)
    print(f"Archivo DENUE crudo:  {archivo_denue.name} ({archivo_denue.stat().st_size / (1024*1024):.2f} MB)")
    print(f"Metadatos DENUE:      {meta_denue.name}")
    print(f"Archivo Marco Geo:    {archivo_mg.name} ({archivo_mg.stat().st_size / 1024:.1f} KB)")
    print(f"Metadatos Marco Geo:  {meta_mg.name}")
    print("-" * 74)
    print(f"Total registros crudos en DENUE Colima (todas las actividades): {conteos['total_registros_zip']:,}")
    print(f"Total registros en clases SCIAN de estudio:                     {conteos['total_estudio']:,}")
    print("-" * 74)
    print("Conteo por categoría de estudio:")
    for cat, cnt in conteos["por_categoria"].items():
        print(f"  - {cat:22}: {cnt:6,}")
    print("-" * 74)
    print("Conteo por municipio (clases SCIAN de estudio):")
    for mun, cnt in conteos["por_municipio"].items():
        print(f"  - {mun:26}: {cnt:6,}")
    print("=" * 74 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
