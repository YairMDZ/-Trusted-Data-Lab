"""
Módulo de Integración y Resolución de Conflictos (Fase 1 - Entrega E1)
Lee archivos crudos de datos/bronce/ (INEGI y Banxico), estandariza esquemas,
resuelve capturas repetidas (gana la más reciente), aísla duplicados y series
descartadas hacia cuarentena con motivo auditable, y genera la tabla larga en Plata.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger("pipeline.integracion")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Catálogo oficial literal extraído de docs/E0/series_seleccionadas.md
CATALOGO_OFICIAL: Dict[str, Dict[str, Any]] = {
    "910392": {
        "nombre_literal": "Índice general",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "frecuencia": "Mensual",
        "tema": "INPC General",
        "es_activa": True,
    },
    "910394": {
        "nombre_literal": "Mercancías",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "frecuencia": "Mensual",
        "tema": "Subyacente Mercancías",
        "es_activa": True,
    },
    "910395": {
        "nombre_literal": "Servicios",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "frecuencia": "Mensual",
        "tema": "Subyacente Servicios",
        "es_activa": True,
    },
    "910397": {
        "nombre_literal": "Agropecuarios",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "frecuencia": "Mensual",
        "tema": "No subyacente Agropecuarios",
        "es_activa": True,
    },
    "SP74625": {
        "nombre_literal": "Subíndice subyacente del INPC",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "Banxico",
        "frecuencia": "Mensual",
        "tema": "Inflación Subyacente",
        "es_activa": True,
    },
    "SF43718": {
        "nombre_literal": "Tipo de cambio FIX",
        "unidad_literal": "Pesos por Dólar",
        "fuente": "Banxico",
        "frecuencia": "Diaria",
        "tema": "Tipo de Cambio",
        "es_activa": True,
    },
    # Series legadas o duplicadas descartadas formalmente en E0:
    "SP1": {
        "nombre_literal": "Índice de Precios al Consumidor General (Banxico)",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "Banxico",
        "frecuencia": "Mensual",
        "tema": "Descartada por duplicidad con INEGI 910392",
        "es_activa": False,
    },
    "628194": {
        "nombre_literal": "INPC General (Canasta legada 2018)",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "frecuencia": "Mensual",
        "tema": "Descartada por congelada en 2024/07",
        "es_activa": False,
    },
    "628204": {
        "nombre_literal": "Subyacente Alimentos, Bebidas y Tabaco (Canasta legada)",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "frecuencia": "Mensual",
        "tema": "Descartada por congelada en 2024/07",
        "es_activa": False,
    },
    "628217": {
        "nombre_literal": "Refrescos envasados (Canasta legada)",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "frecuencia": "Mensual",
        "tema": "Descartada por congelada en 2024/07",
        "es_activa": False,
    },
    "628218": {
        "nombre_literal": "Azúcar (Canasta legada)",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "frecuencia": "Mensual",
        "tema": "Descartada por congelada en 2024/07",
        "es_activa": False,
    },
}

ACTIVE_SERIES = {k for k, v in CATALOGO_OFICIAL.items() if v["es_activa"]}


def extraer_timestamp_captura(filepath: Path, meta: Dict[str, Any]) -> str:
    """Extrae o infiere el timestamp UTC exacto de la captura cruda."""
    t = meta.get("fecha_extraccion_utc")
    if t:
        return str(t)
    # Extraer de nombre de archivo con formato AAAA-MM-DD o AAAAMMDD_HHMMSS
    match = re.search(r"(\d{8})_(\d{6})", filepath.name)
    if match:
        d_str, h_str = match.groups()
        return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}T{h_str[:2]}:{h_str[2:4]}:{h_str[4:6]}Z"
    # Si no tiene timestamp en nombre, usar st_mtime de creación inicial
    return datetime.fromtimestamp(filepath.stat().st_mtime).isoformat() + "Z"


def estandarizar_fecha(fecha_raw: str, fuente: str, cve_serie: str) -> str:
    """
    Estandariza fechas a formato ISO:
    - INEGI: 'YYYY/MM' -> 'YYYY-MM-01'
    - Banxico Mensual: 'DD/MM/YYYY' -> 'YYYY-MM-01'
    - Banxico Diario ('SF43718'): 'DD/MM/YYYY' -> 'YYYY-MM-DD'
    """
    if not fecha_raw:
        return ""
    fecha_limpia = str(fecha_raw).strip()
    if fuente == "INEGI":
        partes = fecha_limpia.split("/")
        if len(partes) == 2:
            return f"{partes[0]}-{int(partes[1]):02d}-01"
    else:  # Banxico
        partes = fecha_limpia.split("/")
        if len(partes) == 3:
            d, m, y = partes
            if cve_serie == "SF43718":
                return f"{y}-{int(m):02d}-{int(d):02d}"
            else:
                return f"{y}-{int(m):02d}-01"
    return fecha_limpia


def leer_archivos_bronce(bronze_dir: Path) -> List[Dict[str, Any]]:
    """Lee todos los archivos JSON de la capa datos/bronce/."""
    registros_crudos: List[Dict[str, Any]] = []

    archivos_json = sorted(bronze_dir.glob("*.json"))
    logger.info("Leyendo %d archivos crudos en %s...", len(archivos_json), bronze_dir)

    for ruta in archivos_json:
        try:
            with open(ruta, "r", encoding="utf-8") as fp:
                data = json.load(fp)
        except Exception as e:
            logger.error("Error al abrir JSON %s: %s", ruta.name, e)
            continue

        meta = data.get("metadata") or data.get("metadata_extraccion", {})
        ts_captura = extraer_timestamp_captura(ruta, meta)

        # Formato INEGI
        if "series" in data or "indicadores" in data:
            s_dict = data.get("series") or data.get("indicadores")
            for cve, payload in s_dict.items():
                raw = payload.get("data", payload)
                for s in raw.get("Series", []):
                    for obs in s.get("OBSERVATIONS", []):
                        registros_crudos.append({
                            "archivo_origen": ruta.name,
                            "fecha_captura_utc": ts_captura,
                            "fuente": "INEGI",
                            "cve_serie": str(cve),
                            "fecha_raw": obs.get("TIME_PERIOD"),
                            "valor_raw": obs.get("OBS_VALUE"),
                            "registro_original": json.dumps(obs, ensure_ascii=False),
                        })

        # Formato Banxico SIE
        elif "respuesta_cruda" in data:
            bmx = data.get("respuesta_cruda", {}).get("bmx", {})
            for s in bmx.get("series", []):
                sid = str(s.get("idSerie"))
                for item in s.get("datos", []):
                    registros_crudos.append({
                        "archivo_origen": ruta.name,
                        "fecha_captura_utc": ts_captura,
                        "fuente": "Banxico",
                        "cve_serie": sid,
                        "fecha_raw": item.get("fecha"),
                        "valor_raw": item.get("dato"),
                        "registro_original": json.dumps(item, ensure_ascii=False),
                    })

    logger.info("Total de registros crudos leídos: %d", len(registros_crudos))
    return registros_crudos


def integrar_datos_bronce(
    bronze_dir: Path = Path("datos/bronce"),
    plata_dir: Path = Path("datos/plata"),
    cuarentena_dir: Path = Path("datos/cuarentena"),
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Ejecuta la Fase 1 completa:
    1. Lee todos los JSON crudos.
    2. Identifica y envía series descartadas a cuarentena.
    3. Normaliza textos 'N/E' y los envía a cuarentena.
    4. Resuelve capturas repetidas (gana la más reciente por serie y fecha).
    5. Agrega SF43718 de diario a mensual (promedio mensual y cierre mensual).
    6. Guarda tabla integrada en datos/plata/ y registros rechazados en datos/cuarentena/.
    7. Valida conciliación de conteos.
    """
    plata_dir.mkdir(parents=True, exist_ok=True)
    cuarentena_dir.mkdir(parents=True, exist_ok=True)

    registros_crudos = leer_archivos_bronce(bronze_dir)
    total_entrada = len(registros_crudos)

    filas_cuarentena: List[Dict[str, Any]] = []
    filas_activas_candidatas: List[Dict[str, Any]] = []

    conteo_ne = 0
    ahora_utc = datetime.utcnow().isoformat() + "Z"

    for r in registros_crudos:
        cve = r["cve_serie"]
        # Caso 1: Series descartadas formalmente (628xxx, SP1, etc.)
        if cve not in ACTIVE_SERIES:
            motivo = (
                f"Serie '{cve}' descartada del análisis por desactualización/congelamiento o duplicidad "
                f"(ver docs/E0/series_seleccionadas.md)"
            )
            filas_cuarentena.append({
                "registro_original": r["registro_original"],
                "regla_violada": "serie_no_seleccionada",
                "motivo_texto": motivo,
                "fecha_hora_validacion": ahora_utc,
                "archivo_captura_origen": r["archivo_origen"],
                "fase_deteccion": "Fase 1: Integración",
                "cve_serie": cve,
                "fecha_raw": r["fecha_raw"],
            })
            continue

        # Caso 2: Manejo de textos no numéricos ('N/E', vacíos o nulos)
        v_str = str(r["valor_raw"]).strip() if r["valor_raw"] is not None else ""
        if v_str in ("N/E", "", "None", "null", "NaN"):
            conteo_ne += 1
            motivo = (
                f"Valor no numérico literal ('{v_str}') en serie {cve} para fecha {r['fecha_raw']}: "
                f"dato no existente o previo al inicio del cálculo oficial de la serie"
            )
            filas_cuarentena.append({
                "registro_original": r["registro_original"],
                "regla_violada": "valor_no_numerico_ne",
                "motivo_texto": motivo,
                "fecha_hora_validacion": ahora_utc,
                "archivo_captura_origen": r["archivo_origen"],
                "fase_deteccion": "Fase 1: Integración",
                "cve_serie": cve,
                "fecha_raw": r["fecha_raw"],
            })
            continue

        # Convertir a float
        try:
            val_num = float(v_str)
        except ValueError:
            conteo_ne += 1
            motivo = f"No se pudo convertir '{v_str}' a valor numérico float"
            filas_cuarentena.append({
                "registro_original": r["registro_original"],
                "regla_violada": "error_conversion_numerica",
                "motivo_texto": motivo,
                "fecha_hora_validacion": ahora_utc,
                "archivo_captura_origen": r["archivo_origen"],
                "fase_deteccion": "Fase 1: Integración",
                "cve_serie": cve,
                "fecha_raw": r["fecha_raw"],
            })
            continue

        fecha_std = estandarizar_fecha(r["fecha_raw"], r["fuente"], cve)
        info_cat = CATALOGO_OFICIAL.get(cve, {})

        filas_activas_candidatas.append({
            "fecha": fecha_std,
            "cve_serie": cve,
            "nombre_literal": info_cat.get("nombre_literal", cve),
            "unidad_literal": info_cat.get("unidad_literal", ""),
            "fuente": r["fuente"],
            "valor": val_num,
            "fecha_captura_utc": r["fecha_captura_utc"],
            "archivo_origen": r["archivo_origen"],
            "registro_original": r["registro_original"],
        })

    logger.info("Registros descartados por serie no activa o N/E: %d (N/E count: %d)", len(filas_cuarentena), conteo_ne)

    # Caso 3: Resolución de capturas repetidas (Deduplicación)
    # Regla: Gana la captura más reciente por serie y fecha
    filas_activas_candidatas.sort(
        key=lambda x: (x["cve_serie"], x["fecha"], x["fecha_captura_utc"]),
        reverse=True,
    )

    claves_vistas = set()
    filas_plata_long: List[Dict[str, Any]] = []

    for r in filas_activas_candidatas:
        clave_unica = (r["cve_serie"], r["fecha"])
        if clave_unica in claves_vistas:
            motivo = (
                f"Duplicado de captura anterior para serie {r['cve_serie']} en fecha {r['fecha']}; "
                f"descartado en favor de captura más reciente ({r['fecha_captura_utc']})"
            )
            filas_cuarentena.append({
                "registro_original": r["registro_original"],
                "regla_violada": "duplicado_captura_anterior",
                "motivo_texto": motivo,
                "fecha_hora_validacion": ahora_utc,
                "archivo_captura_origen": r["archivo_origen"],
                "fase_deteccion": "Fase 1: Integración",
                "cve_serie": r["cve_serie"],
                "fecha_raw": r["fecha"],
            })
        else:
            claves_vistas.add(clave_unica)
            filas_plata_long.append({
                "fecha": r["fecha"],
                "cve_serie": r["cve_serie"],
                "nombre_literal": r["nombre_literal"],
                "unidad_literal": r["unidad_literal"],
                "fuente": r["fuente"],
                "valor": r["valor"],
                "fecha_captura_utc": r["fecha_captura_utc"],
                "archivo_origen": r["archivo_origen"],
            })

    # DataFrames finales
    df_plata_long = pd.DataFrame(filas_plata_long)
    df_plata_long["fecha"] = pd.to_datetime(df_plata_long["fecha"])
    df_plata_long = df_plata_long.sort_values(by=["cve_serie", "fecha"]).reset_index(drop=True)

    df_cuarentena_f1 = pd.DataFrame(filas_cuarentena)

    # Validar conciliación matemática estricta
    total_plata = len(df_plata_long)
    total_cuarentena_f1 = len(df_cuarentena_f1)
    if total_entrada != (total_plata + total_cuarentena_f1):
        msg = (
            f"ERROR DE CONCILIACIÓN FASE 1: Total entrada ({total_entrada}) != "
            f"Plata ({total_plata}) + Cuarentena ({total_cuarentena_f1})"
        )
        logger.error(msg)
        raise ValueError(msg)

    logger.info(
        "CONCILIACIÓN FASE 1 EXITOSA: %d (Entrada) == %d (Plata) + %d (Cuarentena)",
        total_entrada,
        total_plata,
        total_cuarentena_f1,
    )

    # Agregación del tipo de cambio diario (SF43718) a mensual
    # Dos criterios formales:
    # 1. promedio_mensual: promedio aritmético de las cotizaciones diarias hábiles del mes.
    # 2. cierre_mensual: valor cotizado en el último día hábil bancario registrado del mes.
    df_tc_diario = df_plata_long[df_plata_long["cve_serie"] == "SF43718"].copy()
    df_tc_diario["mes_periodo"] = df_tc_diario["fecha"].dt.to_period("M").dt.to_timestamp()

    df_tc_mensual = (
        df_tc_diario.groupby("mes_periodo")
        .agg(
            promedio_mensual=("valor", "mean"),
            cierre_mensual=("valor", "last"),
            dias_cotizados=("valor", "count"),
            fecha_inicio_mes=("fecha", "min"),
            fecha_fin_mes=("fecha", "max"),
        )
        .reset_index()
        .rename(columns={"mes_periodo": "fecha"})
    )
    df_tc_mensual["cve_serie"] = "SF43718"
    df_tc_mensual["nombre_literal"] = "Tipo de cambio FIX (Agregado Mensual)"
    df_tc_mensual["unidad_literal"] = "Pesos por Dólar"
    df_tc_mensual["fuente"] = "Banxico"
    # Marca formal de mes incompleto (noviembre 2026 cuenta con cotizaciones sólo hasta el día 6)
    df_tc_mensual["es_mes_incompleto"] = df_tc_mensual["fecha"] == pd.Timestamp("2026-11-01")

    # Persistencia en datos/plata/ y datos/cuarentena/
    df_plata_long.to_parquet(plata_dir / "tabla_plata_long.parquet", index=False)
    df_plata_long.to_csv(plata_dir / "tabla_plata_long.csv", index=False, encoding="utf-8")

    df_tc_mensual.to_parquet(plata_dir / "tipo_cambio_mensual.parquet", index=False)
    df_tc_mensual.to_csv(plata_dir / "tipo_cambio_mensual.csv", index=False, encoding="utf-8")

    df_cuarentena_f1.to_parquet(cuarentena_dir / "cuarentena_integracion.parquet", index=False)
    df_cuarentena_f1.to_csv(cuarentena_dir / "cuarentena_integracion.csv", index=False, encoding="utf-8")

    # Resumen de inventario
    print("\n" + "=" * 70)
    print("INVENTARIO DE INTEGRACIÓN - FASE 1")
    print("=" * 70)
    print(f"Total registros brutos procesados: {total_entrada:,}")
    print(f"Total registros aceptados en Plata:  {total_plata:,}")
    print(f"Total registros en Cuarentena F1:   {total_cuarentena_f1:,}")
    print("-" * 70)
    print("Registros aceptados en Plata por Serie:")
    for cve, grp in df_plata_long.groupby("cve_serie"):
        nom = grp["nombre_literal"].iloc[0]
        min_f = grp["fecha"].min().strftime("%Y-%m-%d")
        max_f = grp["fecha"].max().strftime("%Y-%m-%d")
        print(f"  [{cve}] {nom:30}: {len(grp):6,} obs | {min_f} a {max_f}")
    print("-" * 70)
    print("Registros en Cuarentena por Regla:")
    for regla, grp in df_cuarentena_f1.groupby("regla_violada"):
        print(f"  {regla:32}: {len(grp):6,} registros")
    print("=" * 70 + "\n")

    return df_plata_long, df_cuarentena_f1, df_tc_mensual


if __name__ == "__main__":
    integrar_datos_bronce()
