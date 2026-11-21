"""
Módulo de Linaje y Trazabilidad End-to-End (Fase 5 - Entrega E2).
- Genera datos/linaje/manifiesto_bronce.{parquet,csv} con todos los archivos crudos de datos/bronce/
  (INEGI INPC, Banxico SIE, INEGI DENUE y Marco Geoestadístico), su SHA-256, tamaño y fecha de ingesta.
- Agrega columnas de linaje a TODAS las tablas de Capa Oro (E1 y E2) SIN modificar ningún valor existente:
  id_registro, fuente, archivos_origen_bronce, fecha_ingesta, n_registros_origen,
  fecha_min_origen, fecha_max_origen, hash_captura, run_id.
- Genera datos/linaje/tabla_linaje.{parquet,csv} registrando el linaje de Plata y Oro, incluyendo
  los identificadores exactos de los registros de origen para filas agregadas (tipo de cambio mensual,
  conteos por municipio, localidad y AGEB).
- Expone trazar(id_registro) y verificar_muestra_linaje() para auditar valores de Oro directamente
  contra los archivos crudos en datos/bronce/.
- Genera docs/E2/linaje.md con ejemplos reales de rastreo.
"""

import hashlib
import io
import json
import logging
import random
import re
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import geopandas as gpd
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.denue.extractor_denue import CATALOGO_SCIAN_ESTUDIO

logger = logging.getLogger("pipeline.linaje")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

COLUMNAS_LINAJE_ORO = [
    "id_registro",
    "fuente",
    "archivos_origen_bronce",
    "fecha_ingesta",
    "n_registros_origen",
    "fecha_min_origen",
    "fecha_max_origen",
    "hash_captura",
    "run_id",
]


def calcular_sha256_archivo(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def combinar_hashes(hashes: List[str]) -> str:
    unicos = sorted({str(h) for h in hashes if h})
    if len(unicos) == 1:
        return unicos[0]
    return hashlib.sha256("|".join(unicos).encode("utf-8")).hexdigest()


def _inferir_fecha_ingesta(ruta: Path) -> str:
    # 1. Intentar metadato compañero para DENUE / Marco Geoestadístico
    if ruta.suffix == ".zip" and "denue_colima_raw_" in ruta.name:
        meta_p = ruta.parent / ruta.name.replace("denue_colima_raw_", "denue_colima_metadata_").replace(".zip", ".json")
        if meta_p.exists():
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            if meta.get("fecha_ingesta_utc"):
                return str(meta["fecha_ingesta_utc"])
    if ruta.suffix == ".geojson" and "marco_geoestadistico_colima_municipios_" in ruta.name:
        meta_p = ruta.parent / ruta.name.replace("marco_geoestadistico_colima_municipios_", "marco_geoestadistico_colima_metadata_").replace(".geojson", ".json")
        if meta_p.exists():
            meta = json.loads(meta_p.read_text(encoding="utf-8"))
            if meta.get("fecha_ingesta_utc"):
                return str(meta["fecha_ingesta_utc"])
    # 2. Para JSON de INEGI / Banxico en raíz de datos/bronce/
    if ruta.suffix == ".json" and "metadata" not in ruta.name:
        try:
            data = json.loads(ruta.read_text(encoding="utf-8"))
            meta = data.get("metadata") or data.get("metadata_extraccion") or {}
            if meta.get("fecha_extraccion_utc"):
                return str(meta["fecha_extraccion_utc"])
        except Exception:
            pass
    # 3. Extraer de nombre YYYYMMDD_HHMMSS
    m = re.search(r"(\d{8})_(\d{6})", ruta.name)
    if m:
        d_str, h_str = m.groups()
        return f"{d_str[:4]}-{d_str[4:6]}-{d_str[6:8]}T{h_str[:2]}:{h_str[2:4]}:{h_str[4:6]}Z"
    return datetime.fromtimestamp(ruta.stat().st_mtime, tz=timezone.utc).isoformat()


def _clasificar_fuente_archivo(ruta: Path) -> str:
    nombre = ruta.name.lower()
    if "inegi_inpc" in nombre:
        return "INEGI (API BIE-BISE INPC)"
    if "banxico" in nombre:
        return "Banxico (API SIE)"
    if "denue" in nombre:
        return "INEGI (DENUE Colima)"
    if "marco_geoestadistico" in nombre:
        return "INEGI (Marco Geoestadístico GAIA)"
    return "Desconocida"


def construir_manifiesto_bronce(
    bronze_dir: Path = BASE_DIR / "datos" / "bronce",
    linaje_dir: Path = BASE_DIR / "datos" / "linaje",
) -> pd.DataFrame:
    """
    Escanea todos los archivos de datos crudos en datos/bronce/ (incluyendo subcarpetas
    denue/ y marco_geoestadistico/) y persiste datos/linaje/manifiesto_bronce.{parquet,csv}.
    """
    linaje_dir.mkdir(parents=True, exist_ok=True)
    filas = []

    patrones = [
        ("*.json", bronze_dir),
        ("denue_colima_raw_*.zip", bronze_dir / "denue"),
        ("marco_geoestadistico_colima_municipios_*.geojson", bronze_dir / "marco_geoestadistico"),
    ]
    for patron, carpeta in patrones:
        if not carpeta.exists():
            continue
        for ruta in sorted(carpeta.glob(patron)):
            if "metadata" in ruta.name.lower():
                continue
            rel = ruta.relative_to(BASE_DIR).as_posix()
            filas.append({
                "archivo": ruta.name,
                "ruta_relativa": rel,
                "sha256": calcular_sha256_archivo(ruta),
                "fecha_ingesta": _inferir_fecha_ingesta(ruta),
                "fuente": _clasificar_fuente_archivo(ruta),
                "tamano_bytes": ruta.stat().st_size,
            })

    df_manifiesto = pd.DataFrame(filas).sort_values(["fuente", "archivo"]).reset_index(drop=True)
    df_manifiesto.to_parquet(linaje_dir / "manifiesto_bronce.parquet", index=False)
    df_manifiesto.to_csv(linaje_dir / "manifiesto_bronce.csv", index=False, encoding="utf-8")
    logger.info("Manifiesto de Bronce guardado: %d archivos crudos registrados.", len(df_manifiesto))
    return df_manifiesto


def generar_run_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"run_{ts}_{uuid.uuid4().hex[:8]}"


def _limpiar_columnas_linaje_previas(df: pd.DataFrame) -> pd.DataFrame:
    cols_drop = [c for c in COLUMNAS_LINAJE_ORO if c in df.columns]
    return df.drop(columns=cols_drop) if cols_drop else df.copy()


def construir_linaje_completo(
    bronze_dir: Path = BASE_DIR / "datos" / "bronce",
    plata_dir: Path = BASE_DIR / "datos" / "plata",
    oro_dir: Path = BASE_DIR / "datos" / "oro",
    linaje_dir: Path = BASE_DIR / "datos" / "linaje",
    docs_linaje_path: Path = BASE_DIR / "docs" / "E2" / "linaje.md",
    run_id: Optional[str] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, str]:
    """
    1. Construye el manifiesto de Bronce.
    2. Registra el linaje de Plata (tabla_plata_long, tipo_cambio_mensual, denue_colima_plata).
    3. Agrega columnas de linaje a TODAS las tablas de Capa Oro (sin alterar valores existentes):
       - matriz_mensual_macro
       - comparativa_sectores
       - densidad_comercial_escolar_municipios
       - densidad_comercial_escolar_localidad
       - densidad_comercial_escolar_ageb
    4. Persiste datos/linaje/tabla_linaje.{parquet,csv}.
    """
    run_id = run_id or generar_run_id()
    linaje_dir.mkdir(parents=True, exist_ok=True)

    df_manifiesto = construir_manifiesto_bronce(bronze_dir=bronze_dir, linaje_dir=linaje_dir)
    mapa_hash = dict(zip(df_manifiesto["archivo"], df_manifiesto["sha256"]))
    mapa_ingesta = dict(zip(df_manifiesto["archivo"], df_manifiesto["fecha_ingesta"]))

    registros_linaje: List[Dict[str, Any]] = []

    # --------------------------------------------------------------------------
    # A. Lectura de tablas Plata (E1 + E2)
    # --------------------------------------------------------------------------
    df_plata_long = pd.read_parquet(plata_dir / "tabla_plata_long.parquet")
    df_plata_long["fecha"] = pd.to_datetime(df_plata_long["fecha"])
    df_tc_mensual = pd.read_parquet(plata_dir / "tipo_cambio_mensual.parquet")
    df_tc_mensual["fecha"] = pd.to_datetime(df_tc_mensual["fecha"])

    # Linaje de tabla_plata_long (1:1 con Bronce)
    for _, r in df_plata_long.iterrows():
        f_iso = r["fecha"].strftime("%Y-%m-%d")
        arch = str(r["archivo_origen"])
        id_reg = f"plata:tabla_plata_long:{r['cve_serie']}:{f_iso}"
        registros_linaje.append({
            "id_registro": id_reg,
            "capa": "plata",
            "tabla": "tabla_plata_long",
            "fuente": str(r["fuente"]),
            "archivos_origen_bronce": arch,
            "fecha_ingesta": mapa_ingesta.get(arch, str(r["fecha_captura_utc"])),
            "n_registros_origen": 1,
            "fecha_min_origen": f_iso,
            "fecha_max_origen": f_iso,
            "hash_captura": mapa_hash.get(arch, ""),
            "run_id": run_id,
            "ids_origen_json": json.dumps([f"{r['cve_serie']}@{f_iso}"], ensure_ascii=False),
        })

    # Mapa auxiliar de cotizaciones diarias SF43718 por mes para reconstruir agregados mensuales
    df_tc_diario = df_plata_long[df_plata_long["cve_serie"] == "SF43718"].copy()
    df_tc_diario["mes_ts"] = df_tc_diario["fecha"].dt.to_period("M").dt.to_timestamp()
    tc_por_mes: Dict[pd.Timestamp, pd.DataFrame] = {
        mes: grp.sort_values("fecha") for mes, grp in df_tc_diario.groupby("mes_ts")
    }

    # Linaje de tipo_cambio_mensual (agregado diario -> mensual)
    for _, r in df_tc_mensual.iterrows():
        mes_ts = r["fecha"]
        mes_iso = mes_ts.strftime("%Y-%m-%d")
        grp_d = tc_por_mes.get(mes_ts)
        if grp_d is not None and len(grp_d) > 0:
            archs = sorted(grp_d["archivo_origen"].unique().tolist())
            fechas_d = grp_d["fecha"].dt.strftime("%Y-%m-%d").tolist()
            ids_orig = [f"SF43718@{fd}" for fd in fechas_d]
            f_min, f_max = fechas_d[0], fechas_d[-1]
            n_orig = len(fechas_d)
        else:
            archs, ids_orig, f_min, f_max, n_orig = [], [], mes_iso, mes_iso, 0

        registros_linaje.append({
            "id_registro": f"plata:tipo_cambio_mensual:{mes_iso}",
            "capa": "plata",
            "tabla": "tipo_cambio_mensual",
            "fuente": "Banxico",
            "archivos_origen_bronce": ";".join(archs),
            "fecha_ingesta": max((mapa_ingesta.get(a, "") for a in archs), default=""),
            "n_registros_origen": n_orig,
            "fecha_min_origen": f_min,
            "fecha_max_origen": f_max,
            "hash_captura": combinar_hashes([mapa_hash.get(a, "") for a in archs]),
            "run_id": run_id,
            "ids_origen_json": json.dumps(ids_orig, ensure_ascii=False),
        })

    # --------------------------------------------------------------------------
    # B. Enriquecer con linaje las tablas Oro de E1 (SIN cambiar valores)
    # --------------------------------------------------------------------------
    # B1. matriz_mensual_macro
    series_mensuales = ["910392", "910394", "910395", "910397", "SP74625"]
    df_m_plata = df_plata_long[df_plata_long["cve_serie"].isin(series_mensuales)].copy()
    plata_por_mes: Dict[pd.Timestamp, pd.DataFrame] = {
        f: grp for f, grp in df_m_plata.groupby("fecha")
    }

    matriz_macro = _limpiar_columnas_linaje_previas(pd.read_parquet(oro_dir / "matriz_mensual_macro.parquet"))
    matriz_macro["fecha"] = pd.to_datetime(matriz_macro["fecha"])

    lin_macro_cols: List[Dict[str, Any]] = []
    for _, row in matriz_macro.iterrows():
        f_ts = row["fecha"]
        f_iso = f_ts.strftime("%Y-%m-%d")
        id_reg = f"oro:matriz_mensual_macro:{f_iso}"

        grp_m = plata_por_mes.get(f_ts, pd.DataFrame())
        grp_tc = tc_por_mes.get(f_ts, pd.DataFrame())

        archs = sorted(
            set(grp_m["archivo_origen"].tolist() if len(grp_m) else [])
            | set(grp_tc["archivo_origen"].tolist() if len(grp_tc) else [])
        )
        fuentes = sorted(
            set(grp_m["fuente"].tolist() if len(grp_m) else [])
            | ({"Banxico"} if len(grp_tc) else set())
        )
        ids_orig = [f"{r['cve_serie']}@{r['fecha'].strftime('%Y-%m-%d')}" for _, r in grp_m.iterrows()]
        fechas_orig = [f_iso] if len(grp_m) else []
        if len(grp_tc):
            fechas_tc = grp_tc["fecha"].dt.strftime("%Y-%m-%d").tolist()
            ids_orig.extend([f"SF43718@{fd}" for fd in fechas_tc])
            fechas_orig.extend(fechas_tc)

        meta_fila = {
            "id_registro": id_reg,
            "fuente": "+".join(fuentes),
            "archivos_origen_bronce": ";".join(archs),
            "fecha_ingesta": max((mapa_ingesta.get(a, "") for a in archs), default=""),
            "n_registros_origen": len(ids_orig),
            "fecha_min_origen": min(fechas_orig) if fechas_orig else f_iso,
            "fecha_max_origen": max(fechas_orig) if fechas_orig else f_iso,
            "hash_captura": combinar_hashes([mapa_hash.get(a, "") for a in archs]),
            "run_id": run_id,
        }
        lin_macro_cols.append(meta_fila)
        registros_linaje.append({
            **meta_fila,
            "capa": "oro",
            "tabla": "matriz_mensual_macro",
            "ids_origen_json": json.dumps(ids_orig, ensure_ascii=False),
        })

    matriz_macro = pd.concat([matriz_macro.reset_index(drop=True), pd.DataFrame(lin_macro_cols)], axis=1)
    matriz_macro.to_parquet(oro_dir / "matriz_mensual_macro.parquet", index=False)
    matriz_macro.to_csv(oro_dir / "matriz_mensual_macro.csv", index=False, encoding="utf-8")

    # B2. comparativa_sectores
    plata_idx = df_plata_long.set_index(["cve_serie", "fecha"])
    comp_sec = _limpiar_columnas_linaje_previas(pd.read_parquet(oro_dir / "comparativa_sectores.parquet"))
    comp_sec["fecha"] = pd.to_datetime(comp_sec["fecha"])

    lin_sec_cols: List[Dict[str, Any]] = []
    for _, row in comp_sec.iterrows():
        cve = str(row["cve_serie"])
        f_ts = row["fecha"]
        f_iso = f_ts.strftime("%Y-%m-%d")
        id_reg = f"oro:comparativa_sectores:{cve}:{f_iso}"

        origen = plata_idx.loc[(cve, f_ts)]
        arch = str(origen["archivo_origen"])
        fuente = str(origen["fuente"])
        meta_fila = {
            "id_registro": id_reg,
            "fuente": fuente,
            "archivos_origen_bronce": arch,
            "fecha_ingesta": mapa_ingesta.get(arch, str(origen["fecha_captura_utc"])),
            "n_registros_origen": 1,
            "fecha_min_origen": f_iso,
            "fecha_max_origen": f_iso,
            "hash_captura": mapa_hash.get(arch, ""),
            "run_id": run_id,
        }
        lin_sec_cols.append(meta_fila)
        registros_linaje.append({
            **meta_fila,
            "capa": "oro",
            "tabla": "comparativa_sectores",
            "ids_origen_json": json.dumps([f"{cve}@{f_iso}"], ensure_ascii=False),
        })

    comp_sec = pd.concat([comp_sec.reset_index(drop=True), pd.DataFrame(lin_sec_cols)], axis=1)
    comp_sec.to_parquet(oro_dir / "comparativa_sectores.parquet", index=False)
    comp_sec.to_csv(oro_dir / "comparativa_sectores.csv", index=False, encoding="utf-8")

    # --------------------------------------------------------------------------
    # C. Linaje Geoespacial (Plata DENUE + 3 Tablas Oro Geoespaciales)
    # --------------------------------------------------------------------------
    ruta_denue_plata = plata_dir / "denue_colima_plata.parquet"
    ruta_marco_plata = plata_dir / "marco_geoestadistico_colima_plata.parquet"
    if ruta_denue_plata.exists() and ruta_marco_plata.exists():
        gdf_denue = gpd.read_parquet(ruta_denue_plata)
        df_denue = pd.DataFrame(gdf_denue.drop(columns=["geometry"]))
        gdf_marco = gpd.read_parquet(ruta_marco_plata)
        arch_marco = str(gdf_marco["archivo_origen_marco"].iloc[0])

        # Linaje de Plata geoespacial (1:1 con DENUE Bronce)
        for _, r in df_denue.iterrows():
            arch = str(r["archivo_origen"])
            fa = str(r.get("fecha_alta", "")) or str(r["fecha_captura_utc"])[:10]
            registros_linaje.append({
                "id_registro": f"plata:denue_colima_plata:{r['id_establecimiento']}",
                "capa": "plata",
                "tabla": "denue_colima_plata",
                "fuente": "INEGI_DENUE",
                "archivos_origen_bronce": arch,
                "fecha_ingesta": mapa_ingesta.get(arch, str(r["fecha_captura_utc"])),
                "n_registros_origen": 1,
                "fecha_min_origen": fa,
                "fecha_max_origen": fa,
                "hash_captura": mapa_hash.get(arch, ""),
                "run_id": run_id,
                "ids_origen_json": json.dumps([str(r["id_establecimiento"])], ensure_ascii=False),
            })

        # Helper para tablas Oro geoespaciales agregadas
        def _enriquecer_oro_geo(
            nombre_tabla: str,
            clave_cols: List[str],
            incluir_marco: bool,
        ) -> None:
            ruta_p = oro_dir / f"{nombre_tabla}.parquet"
            if not ruta_p.exists():
                return
            df_oro = _limpiar_columnas_linaje_previas(pd.read_parquet(ruta_p))
            lin_rows: List[Dict[str, Any]] = []

            for _, row in df_oro.iterrows():
                mask = pd.Series(True, index=df_denue.index)
                partes_id = []
                for c in clave_cols:
                    val = str(row[c])
                    mask &= df_denue[c].astype(str) == val
                    partes_id.append(val)

                sub = df_denue[mask]
                id_reg = f"oro:{nombre_tabla}:" + ":".join(partes_id)
                archs = sorted(sub["archivo_origen"].unique().tolist())
                if incluir_marco and arch_marco not in archs:
                    archs.append(arch_marco)
                archs = sorted(archs)

                ids_est = sorted(sub["id_establecimiento"].astype(str).tolist())
                fechas_alta = sorted([f for f in sub["fecha_alta"].astype(str).tolist() if f and f != "nan"])
                f_min = fechas_alta[0] if fechas_alta else str(mapa_ingesta.get(arch_marco, ""))[:10]
                f_max = fechas_alta[-1] if fechas_alta else str(mapa_ingesta.get(arch_marco, ""))[:10]

                meta_fila = {
                    "id_registro": id_reg,
                    "fuente": "INEGI_DENUE+INEGI_MarcoGeo" if incluir_marco else "INEGI_DENUE",
                    "archivos_origen_bronce": ";".join(archs),
                    "fecha_ingesta": max((mapa_ingesta.get(a, "") for a in archs), default=""),
                    "n_registros_origen": len(ids_est) + (1 if incluir_marco else 0),
                    "fecha_min_origen": f_min,
                    "fecha_max_origen": f_max,
                    "hash_captura": combinar_hashes([mapa_hash.get(a, "") for a in archs]),
                    "run_id": run_id,
                }
                lin_rows.append(meta_fila)
                registros_linaje.append({
                    **meta_fila,
                    "capa": "oro",
                    "tabla": nombre_tabla,
                    "ids_origen_json": json.dumps(
                        {"denue_ids": ids_est, "marco_cvegeo": f"06{row['cve_mun']}"} if incluir_marco else {"denue_ids": ids_est},
                        ensure_ascii=False,
                    ),
                })

            df_enriq = pd.concat([df_oro.reset_index(drop=True), pd.DataFrame(lin_rows)], axis=1)
            df_enriq.to_parquet(ruta_p, index=False)
            df_enriq.to_csv(oro_dir / f"{nombre_tabla}.csv", index=False, encoding="utf-8")

        _enriquecer_oro_geo("densidad_comercial_escolar_municipios", ["cve_mun"], incluir_marco=True)
        _enriquecer_oro_geo("densidad_comercial_escolar_localidad", ["cve_mun", "cve_loc"], incluir_marco=False)
        _enriquecer_oro_geo("densidad_comercial_escolar_ageb", ["cve_mun", "cve_loc", "ageb"], incluir_marco=False)

    df_linaje = pd.DataFrame(registros_linaje)
    df_linaje.to_parquet(linaje_dir / "tabla_linaje.parquet", index=False)
    df_linaje.to_csv(linaje_dir / "tabla_linaje.csv", index=False, encoding="utf-8")

    logger.info(
        "Tabla de linaje generada (%s): %d registros totales (Plata=%d, Oro=%d).",
        run_id,
        len(df_linaje),
        int((df_linaje["capa"] == "plata").sum()),
        int((df_linaje["capa"] == "oro").sum()),
    )

    # Generar documentación con ejemplos reales de rastreo
    if docs_linaje_path is not None:
        generar_documentacion_linaje(
            docs_linaje_path=docs_linaje_path,
            linaje_dir=linaje_dir,
            bronze_dir=bronze_dir,
            oro_dir=oro_dir,
        )

    return df_manifiesto, df_linaje, run_id


def trazar(
    id_registro: str,
    linaje_dir: Path = BASE_DIR / "datos" / "linaje",
) -> Dict[str, Any]:
    """
    Rastrea un id_registro (de Capa Oro o Plata) hasta sus archivos crudos exactos
    en datos/bronce/, devolviendo metadatos de captura, SHA-256, fechas e IDs de origen.
    """
    df_lin = pd.read_parquet(linaje_dir / "tabla_linaje.parquet")
    df_man = pd.read_parquet(linaje_dir / "manifiesto_bronce.parquet")

    match = df_lin[df_lin["id_registro"] == id_registro]
    if match.empty:
        raise KeyError(f"No se encontró el id_registro '{id_registro}' en {linaje_dir / 'tabla_linaje.parquet'}")

    row = match.iloc[0]
    archivos_bronce = [a for a in str(row["archivos_origen_bronce"]).split(";") if a]
    man_sub = df_man[df_man["archivo"].isin(archivos_bronce)].to_dict(orient="records")

    ids_origen = json.loads(row["ids_origen_json"])
    return {
        "id_registro": row["id_registro"],
        "capa": row["capa"],
        "tabla": row["tabla"],
        "fuente": row["fuente"],
        "run_id": row["run_id"],
        "fecha_ingesta": row["fecha_ingesta"],
        "n_registros_origen": int(row["n_registros_origen"]),
        "fecha_min_origen": row["fecha_min_origen"],
        "fecha_max_origen": row["fecha_max_origen"],
        "hash_captura": row["hash_captura"],
        "archivos_bronce": man_sub,
        "ids_origen": ids_origen,
    }


def _cargar_indice_crudo_bronce(bronze_dir: Path) -> Dict[str, Any]:
    """Carga un índice en memoria de los valores crudos en Bronce para verificación independiente."""
    inegi_banxico: Dict[Tuple[str, str, str], float] = {}  # (archivo, cve_serie, fecha_iso) -> float
    for ruta in sorted(bronze_dir.glob("*.json")):
        data = json.loads(ruta.read_text(encoding="utf-8"))
        if "series" in data or "indicadores" in data:
            s_dict = data.get("series") or data.get("indicadores")
            for cve, payload in s_dict.items():
                raw = payload.get("data", payload)
                for s in raw.get("Series", []):
                    for obs in s.get("OBSERVATIONS", []):
                        tp = str(obs.get("TIME_PERIOD", "")).strip()
                        val = obs.get("OBS_VALUE")
                        parts = tp.split("/")
                        if len(parts) == 2 and val not in (None, "", "N/E"):
                            f_iso = f"{parts[0]}-{int(parts[1]):02d}-01"
                            inegi_banxico[(ruta.name, str(cve), f_iso)] = float(val)
        elif "respuesta_cruda" in data:
            for s in data.get("respuesta_cruda", {}).get("bmx", {}).get("series", []):
                sid = str(s.get("idSerie"))
                for item in s.get("datos", []):
                    f_raw = str(item.get("fecha", "")).strip()
                    v_raw = str(item.get("dato", "")).strip()
                    parts = f_raw.split("/")
                    if len(parts) == 3 and v_raw not in ("", "N/E", "None"):
                        d, m, y = parts
                        f_iso = f"{y}-{int(m):02d}-{int(d):02d}" if sid == "SF43718" else f"{y}-{int(m):02d}-01"
                        inegi_banxico[(ruta.name, sid, f_iso)] = float(v_raw)

    denue_crudo: Dict[str, Dict[str, Dict[str, str]]] = {}  # archivo -> {id -> {codigo_act, cve_mun, cve_loc, ageb}}
    denue_dir = bronze_dir / "denue"
    if denue_dir.exists():
        for zpath in sorted(denue_dir.glob("denue_colima_raw_*.zip")):
            with zipfile.ZipFile(zpath, "r") as zf:
                cand = [n for n in zf.namelist() if n.lower().endswith(".csv") and "conjunto_de_datos" in n.lower()]
                raw_bytes = zf.open(cand[0], "r").read()
                try:
                    txt = raw_bytes.decode("utf-8-sig")
                except UnicodeDecodeError:
                    txt = raw_bytes.decode("latin-1")
                df_z = pd.read_csv(io.StringIO(txt), dtype=str, low_memory=False)
                denue_crudo[zpath.name] = {
                    str(r["id"]).strip(): {
                        "codigo_act": str(r["codigo_act"]).strip(),
                        "cve_mun": str(r["cve_mun"]).strip().zfill(3),
                        "cve_loc": str(r["cve_loc"]).strip().zfill(4),
                        "ageb": str(r["ageb"]).strip(),
                    }
                    for _, r in df_z[["id", "codigo_act", "cve_mun", "cve_loc", "ageb"]].iterrows()
                }

    return {"macro": inegi_banxico, "denue": denue_crudo}


def verificar_muestra_linaje(
    n_por_tabla: int = 4,
    seed: int = 42,
    bronze_dir: Path = BASE_DIR / "datos" / "bronce",
    oro_dir: Path = BASE_DIR / "datos" / "oro",
    linaje_dir: Path = BASE_DIR / "datos" / "linaje",
) -> Dict[str, Any]:
    """
    Toma una muestra aleatoria estratificada de filas de TODAS las tablas de Capa Oro,
    rastrea cada fila con trazar(id_registro), lee directamente los archivos crudos en
    datos/bronce/, reconstruye el valor y confirma coincidencia exacta.
    """
    rng = random.Random(seed)
    indice_bronce = _cargar_indice_crudo_bronce(bronze_dir)
    resultados: List[Dict[str, Any]] = []

    # 1. Verificar muestra de matriz_mensual_macro
    df_macro = pd.read_parquet(oro_dir / "matriz_mensual_macro.parquet")
    idxs_macro = rng.sample(range(len(df_macro)), min(n_por_tabla, len(df_macro)))
    # Incluir al menos un mes con tipo de cambio disponible (posterior a 1991-11)
    idxs_con_tc = df_macro.index[df_macro["tc_disponible"] == True].tolist()
    if idxs_con_tc and not any(df_macro.loc[i, "tc_disponible"] for i in idxs_macro):
        idxs_macro[0] = idxs_con_tc[-2]

    for i in idxs_macro:
        row = df_macro.iloc[i]
        traza = trazar(row["id_registro"], linaje_dir=linaje_dir)
        archivos = [a["archivo"] for a in traza["archivos_bronce"]]
        f_iso = pd.Timestamp(row["fecha"]).strftime("%Y-%m-%d")

        # Reconstruir inpc_mercancias (910394) directamente desde JSON de INEGI en Bronce
        val_oro_merc = float(row["inpc_mercancias"])
        val_bronce_merc = None
        for a in archivos:
            if (a, "910394", f_iso) in indice_bronce["macro"]:
                val_bronce_merc = indice_bronce["macro"][(a, "910394", f_iso)]
                break
        ok_merc = val_bronce_merc is not None and abs(val_oro_merc - val_bronce_merc) < 1e-6

        # Si tiene tipo de cambio, reconstruir promedio mensual directamente desde días hábiles en JSON Banxico
        ok_tc = True
        detalle_tc = "sin_tc_historico"
        if bool(row["tc_disponible"]):
            ids_tc = [x for x in traza["ids_origen"] if x.startswith("SF43718@")]
            vals_d = []
            for item in ids_tc:
                fd = item.split("@")[1]
                for a in archivos:
                    if (a, "SF43718", fd) in indice_bronce["macro"]:
                        vals_d.append(indice_bronce["macro"][(a, "SF43718", fd)])
                        break
            prom_reconstruido = float(np.mean(vals_d)) if vals_d else np.nan
            ok_tc = len(vals_d) == len(ids_tc) and abs(float(row["tipo_cambio_fix_promedio"]) - prom_reconstruido) < 1e-6
            detalle_tc = f"TC promedio oro={row['tipo_cambio_fix_promedio']:.6f} vs bronce({len(vals_d)} días)={prom_reconstruido:.6f}"

        resultados.append({
            "tabla": "matriz_mensual_macro",
            "id_registro": row["id_registro"],
            "coincide": bool(ok_merc and ok_tc),
            "detalle": f"910394 oro={val_oro_merc} vs bronce={val_bronce_merc}; {detalle_tc}",
        })

    # 2. Verificar muestra de comparativa_sectores
    df_sec = pd.read_parquet(oro_dir / "comparativa_sectores.parquet")
    for i in rng.sample(range(len(df_sec)), min(n_por_tabla, len(df_sec))):
        row = df_sec.iloc[i]
        traza = trazar(row["id_registro"], linaje_dir=linaje_dir)
        arch = traza["archivos_bronce"][0]["archivo"]
        f_iso = pd.Timestamp(row["fecha"]).strftime("%Y-%m-%d")
        val_bronce = indice_bronce["macro"].get((arch, str(row["cve_serie"]), f_iso))
        ok = val_bronce is not None and abs(float(row["nivel_indice"]) - val_bronce) < 1e-6
        resultados.append({
            "tabla": "comparativa_sectores",
            "id_registro": row["id_registro"],
            "coincide": bool(ok),
            "detalle": f"{row['cve_serie']}@{f_iso} oro={row['nivel_indice']} vs bronce={val_bronce}",
        })

    # 3. Verificar muestra de tablas Oro Geoespaciales (municipios, localidad, ageb)
    for nombre_geo in [
        "densidad_comercial_escolar_municipios",
        "densidad_comercial_escolar_localidad",
        "densidad_comercial_escolar_ageb",
    ]:
        ruta_g = oro_dir / f"{nombre_geo}.parquet"
        if not ruta_g.exists():
            continue
        df_g = pd.read_parquet(ruta_g)
        for i in rng.sample(range(len(df_g)), min(n_por_tabla, len(df_g))):
            row = df_g.iloc[i]
            traza = trazar(row["id_registro"], linaje_dir=linaje_dir)
            ids_denue = traza["ids_origen"]["denue_ids"]
            zips = [a["archivo"] for a in traza["archivos_bronce"] if a["archivo"].endswith(".zip")]
            mapa_zip = indice_bronce["denue"].get(zips[0], {}) if zips else {}

            # Reconstruir conteos desde el ZIP crudo de Bronce
            c_esc = c_aba = c_dul = c_hel = 0
            for eid in ids_denue:
                rec = mapa_zip.get(eid)
                if not rec:
                    continue
                cat = CATALOGO_SCIAN_ESTUDIO.get(rec["codigo_act"], {}).get("categoria")
                if cat == "escuela_basica":
                    c_esc += 1
                elif cat == "abarrotes":
                    c_aba += 1
                elif cat == "dulces":
                    c_dul += 1
                elif cat == "helados_paletas":
                    c_hel += 1

            ok = (
                c_esc == int(row["n_escuelas_basicas"])
                and c_aba == int(row["n_abarrotes"])
                and c_dul == int(row["n_dulces"])
                and c_hel == int(row["n_helados_paletas"])
            )
            resultados.append({
                "tabla": nombre_geo,
                "id_registro": row["id_registro"],
                "coincide": bool(ok),
                "detalle": (
                    f"oro=(esc:{row['n_escuelas_basicas']}, aba:{row['n_abarrotes']}, dul:{row['n_dulces']}, hel:{row['n_helados_paletas']}) "
                    f"vs bronce=(esc:{c_esc}, aba:{c_aba}, dul:{c_dul}, hel:{c_hel})"
                ),
            })

    total = len(resultados)
    exitosos = sum(1 for r in resultados if r["coincide"])
    fallidos = total - exitosos
    return {
        "total_verificados": total,
        "exitosos": exitosos,
        "fallidos": fallidos,
        "tasa_exito_pct": round(100.0 * exitosos / total, 2) if total else 0.0,
        "detalle": resultados,
    }


def generar_documentacion_linaje(
    docs_linaje_path: Path = BASE_DIR / "docs" / "E2" / "linaje.md",
    linaje_dir: Path = BASE_DIR / "datos" / "linaje",
    bronze_dir: Path = BASE_DIR / "datos" / "bronce",
    oro_dir: Path = BASE_DIR / "datos" / "oro",
) -> None:
    """Genera docs/E2/linaje.md con arquitectura de trazabilidad y 3 ejemplos reales."""
    docs_linaje_path.parent.mkdir(parents=True, exist_ok=True)
    df_man = pd.read_parquet(linaje_dir / "manifiesto_bronce.parquet")
    df_lin = pd.read_parquet(linaje_dir / "tabla_linaje.parquet")
    verif = verificar_muestra_linaje(n_por_tabla=4, seed=42, bronze_dir=bronze_dir, oro_dir=oro_dir, linaje_dir=linaje_dir)

    # 3 ejemplos concretos reales
    ej1 = trazar("oro:matriz_mensual_macro:2026-09-01", linaje_dir=linaje_dir)
    ej2 = trazar("oro:comparativa_sectores:910394:2026-09-01", linaje_dir=linaje_dir)
    ej3 = trazar("oro:densidad_comercial_escolar_municipios:002", linaje_dir=linaje_dir)

    df_macro = pd.read_parquet(oro_dir / "matriz_mensual_macro.parquet")
    fila_ej1 = df_macro[df_macro["id_registro"] == ej1["id_registro"]].iloc[0]
    df_sec = pd.read_parquet(oro_dir / "comparativa_sectores.parquet")
    fila_ej2 = df_sec[df_sec["id_registro"] == ej2["id_registro"]].iloc[0]
    df_mun = pd.read_parquet(oro_dir / "densidad_comercial_escolar_municipios.parquet")
    fila_ej3 = df_mun[df_mun["id_registro"] == ej3["id_registro"]].iloc[0]

    filas_man = "\n".join(
        f"| `{r['archivo']}` | {r['fuente']} | `{r['fecha_ingesta']}` | {r['tamano_bytes']:,} B | `{r['sha256'][:16]}...` |"
        for _, r in df_man.iterrows()
    )

    resumen_tablas = (
        df_lin.groupby(["capa", "tabla"])["id_registro"]
        .count()
        .reset_index(name="n_registros")
    )
    filas_tablas = "\n".join(
        f"| `{r['capa']}` | `{r['tabla']}` | {r['n_registros']:,} |"
        for _, r in resumen_tablas.iterrows()
    )

    contenido = f"""# Arquitectura de Linaje y Trazabilidad de Datos (Entrega E2)

**Proyecto:** Observatorio de Datos — Comercio Minorista en Puestos Escolares (Colima, México)  
**Módulo de linaje:** `src/pipeline/linaje.py`  
**Artefactos generados:** `datos/linaje/manifiesto_bronce.parquet` y `datos/linaje/tabla_linaje.parquet`

---

## 1. Esquema de Columnas de Linaje en Capa Oro

Cada registro de las 5 tablas en `datos/oro/` (las 2 tablas macroeconómicas de E1 y las 3 tablas geoespaciales agregadas de E2) conserva intactos sus valores analíticos e incorpora 9 columnas estandarizadas de trazabilidad:

| Columna | Tipo | Descripción |
| :--- | :---: | :--- |
| `id_registro` | `STRING` | Identificador determinista único (ej. `oro:matriz_mensual_macro:2026-09-01`, `oro:densidad_comercial_escolar_municipios:002`). |
| `fuente` | `STRING` | Institución(es) pública(s) fuente(s) que alimentan la fila (`INEGI`, `Banxico`, `INEGI+Banxico`, `INEGI_DENUE+INEGI_MarcoGeo`). |
| `archivos_origen_bronce` | `STRING` | Nombre(s) exacto(s) de los archivo(s) crudo(s) en `datos/bronce/` separados por `;`. |
| `fecha_ingesta` | `STRING` | Timestamp ISO-8601 UTC más reciente de la ingesta cruda en Bronce. |
| `n_registros_origen` | `INT64` | Número exacto de observaciones crudas (o establecimientos + polígono) que integran la fila. |
| `fecha_min_origen` | `STRING` | Fecha más antigua de los registros de origen (en DENUE: `fecha_alta` mínima). |
| `fecha_max_origen` | `STRING` | Fecha más reciente de los registros de origen (en DENUE: `fecha_alta` máxima). |
| `hash_captura` | `STRING` | SHA-256 del archivo de Bronce o hash SHA-256 compuesto determinista si participan múltiples capturas. |
| `run_id` | `STRING` | Identificador único de la ejecución del pipeline (`run_YYYYMMDD_HHMMSS_<hex>`). |

Además, `datos/linaje/tabla_linaje.parquet` almacena la columna `ids_origen_json` con la lista completa de identificadores crudos (`cve_serie@fecha` para series diarias/mensuales y `denue_ids` + `marco_cvegeo` para agregados espaciales), permitiendo reconstruir matemáticamente cada promedio o conteo desde los datos crudos sin publicar puntos individuales en Oro.

---

## 2. Cobertura del Registro de Linaje (`datos/linaje/tabla_linaje.parquet`)

| Capa | Tabla | Registros Rastreados |
| :--- | :--- | :---: |
{filas_tablas}
| **Total** | **8 tablas (3 Plata + 5 Oro)** | **{len(df_lin):,}** |

---

## 3. Manifiesto de Archivos Crudos en Bronce (`datos/linaje/manifiesto_bronce.parquet`)

| Archivo Crudo | Fuente | Fecha de Ingesta (UTC) | Tamaño | SHA-256 (prefijo) |
| :--- | :--- | :---: | :---: | :---: |
{filas_man}

---

## 4. Tres Ejemplos Reales de Rastreo (`trazar(id_registro)`)

### Ejemplo 1 — Fila agregada multivariada en `matriz_mensual_macro` (E1)
* **Consulta:** `trazar("{ej1['id_registro']}")`
* **Valores en Capa Oro:** `inpc_mercancias = {fila_ej1['inpc_mercancias']}`, `tipo_cambio_fix_promedio = {fila_ej1['tipo_cambio_fix_promedio']:.6f}`
* **Fuente:** `{ej1['fuente']}` | **Run ID:** `{ej1['run_id']}`
* **Registros de origen (`n_registros_origen`):** **{ej1['n_registros_origen']}** (5 observaciones mensuales de INPC + {ej1['n_registros_origen'] - 5} cotizaciones diarias hábiles de `SF43718` en septiembre de 2026)
* **Rango de fechas de origen:** `{ej1['fecha_min_origen']}` a `{ej1['fecha_max_origen']}`
* **Archivos crudos en Bronce:**
  - `{ej1['archivos_bronce'][0]['ruta_relativa']}` (SHA-256: `{ej1['archivos_bronce'][0]['sha256'][:16]}...`, ingesta: `{ej1['archivos_bronce'][0]['fecha_ingesta']}`)
  - `{ej1['archivos_bronce'][1]['ruta_relativa']}` (SHA-256: `{ej1['archivos_bronce'][1]['sha256'][:16]}...`, ingesta: `{ej1['archivos_bronce'][1]['fecha_ingesta']}`)
* **Muestra de `ids_origen` guardados para reconstrucción:** `{ej1['ids_origen'][:8]}` ... ({len(ej1['ids_origen'])} en total)

### Ejemplo 2 — Fila sectorial en `comparativa_sectores` (E1)
* **Consulta:** `trazar("{ej2['id_registro']}")`
* **Valor en Capa Oro:** `sector = {fila_ej2['sector']}`, `nivel_indice = {fila_ej2['nivel_indice']}`, `var_mensual_pct = {fila_ej2['var_mensual_pct']:.4f}%`
* **Fuente:** `{ej2['fuente']}` | **Registros de origen:** `{ej2['n_registros_origen']}` (`{ej2['ids_origen']}`)
* **Archivo crudo en Bronce:** `{ej2['archivos_bronce'][0]['ruta_relativa']}`
* **Fecha de ingesta:** `{ej2['fecha_ingesta']}` | **SHA-256:** `{ej2['hash_captura']}`

### Ejemplo 3 — Fila agregada municipal geoespacial en `densidad_comercial_escolar_municipios` (E2)
* **Consulta:** `trazar("{ej3['id_registro']}")` (Municipio de **Colima**, clave `002`)
* **Valores en Capa Oro:** `n_escuelas_basicas = {int(fila_ej3['n_escuelas_basicas'])}`, `n_abarrotes = {int(fila_ej3['n_abarrotes'])}`, `n_dulces = {int(fila_ej3['n_dulces'])}`, `n_helados_paletas = {int(fila_ej3['n_helados_paletas'])}`, `comercios_por_escuela = {fila_ej3['comercios_por_escuela']}`, `area_km2_continental = {fila_ej3['area_km2_continental']}`
* **Fuente:** `{ej3['fuente']}`
* **Registros de origen (`n_registros_origen`):** **{ej3['n_registros_origen']}** ({len(ej3['ids_origen']['denue_ids'])} establecimientos DENUE + 1 polígono oficial `{ej3['ids_origen']['marco_cvegeo']}` del Marco Geoestadístico)
* **Rango `fecha_alta` DENUE:** `{ej3['fecha_min_origen']}` a `{ej3['fecha_max_origen']}`
* **Archivos crudos en Bronce:**
  - `{ej3['archivos_bronce'][0]['ruta_relativa']}` (SHA-256: `{ej3['archivos_bronce'][0]['sha256'][:16]}...`)
  - `{ej3['archivos_bronce'][1]['ruta_relativa']}` (SHA-256: `{ej3['archivos_bronce'][1]['sha256'][:16]}...`)
* **Muestra de `denue_ids` para reconstrucción:** `{ej3['ids_origen']['denue_ids'][:8]}` ... ({len(ej3['ids_origen']['denue_ids'])} IDs en total)

---

## 5. Resultado de la Auditoría Automatizada de Muestra Aleatoria

La función `verificar_muestra_linaje(n_por_tabla=4, seed=42)` muestreó **{verif['total_verificados']} filas aleatorias** a través de las 5 tablas de Capa Oro, abrió directamente los archivos crudos en `datos/bronce/` y reconstruyó sus valores desde cero:

* **Verificaciones exitosas:** **{verif['exitosos']} / {verif['total_verificados']} ({verif['tasa_exito_pct']}%)**
* **Discrepancias detectadas:** **{verif['fallidos']}**
"""
    docs_linaje_path.write_text(contenido, encoding="utf-8")
    logger.info("Documentación de linaje generada en: %s", docs_linaje_path)


if __name__ == "__main__":
    construir_linaje_completo()
    rep = verificar_muestra_linaje(n_por_tabla=4, seed=42)
    print("\n" + "=" * 74)
    print("VERIFICACIÓN DE LINAJE CONTRA ARCHIVOS CRUDOS EN BRONCE")
    print("=" * 74)
    print(f"Total verificados: {rep['total_verificados']} | Exitosos: {rep['exitosos']} | Fallidos: {rep['fallidos']} ({rep['tasa_exito_pct']}%)")
    for item in rep["detalle"]:
        estado = "OK" if item["coincide"] else "FALLO"
        print(f"  [{estado}] {item['id_registro']} -> {item['detalle']}")
    print("=" * 74 + "\n")
    sys.exit(0 if rep["fallidos"] == 0 else 1)
