"""
Módulo de Capa Plata Geoespacial y Puerta de Calidad (Fase 3 - Entrega E2).
- Lee capturas crudas de datos/bronce/denue/ y datos/bronce/marco_geoestadistico/.
- Aplica minimización estricta de datos personales (descarta razón social, nombre comercial,
  teléfonos, correos, sitios web y direcciones exactas).
- Valida con Pandera (lazy=True) y contención espacial contra el Marco Geoestadístico de Colima.
- Segrega descartes por diseño y registros inválidos a datos/cuarentena/cuarentena_denue.{parquet,csv}.
- Verifica conciliación estricta: entrada = Plata + Cuarentena (lanza ValueError si no cuadra).
- Define CRS explícitos: EPSG:4326 (almacenamiento) y EPSG:6372 (cálculos métricos para México).
"""

import io
import json
import logging
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import geopandas as gpd
import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors
from shapely.geometry import box

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.denue.extractor_denue import (
    CATALOGO_SCIAN_ESTUDIO,
    ENTIDAD_COLIMA,
    MUNICIPIOS_COLIMA,
)

logger = logging.getLogger("denue.plata_geo")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# CRS oficiales del proyecto
CRS_ALMACENAMIENTO = "EPSG:4326"  # WGS 84 (latitud/longitud) — estándar GeoJSON / GeoParquet
CRS_PROYECTADO_MX = "EPSG:6372"   # Mexico ITRF2008 / Lambert Conformal Conic (CRS oficial INEGI en metros)

# Límites geográficos de Colima (incluyendo Archipiélago de Revillagigedo para bounding box estatal)
COLIMA_LAT_MIN, COLIMA_LAT_MAX = 18.30, 19.60
COLIMA_LON_MIN, COLIMA_LON_MAX = -114.80, -103.40
# Caja continental de Colima (para separar área continental y visualizaciones sin distorsión oceánica)
COLIMA_CONTINENTAL_BOX = box(-104.75, 18.60, -103.40, 19.55)

# Minimización de datos personales: catálogo explícito de campos descartados vs conservados
CAMPOS_PERSONALES_Y_NO_ANALITICOS_DESCARTADOS: Dict[str, str] = {
    "nom_estab": "Nombre comercial del establecimiento; en microempresas suele corresponder al nombre personal del propietario.",
    "raz_social": "Razón social o nombre de persona física con actividad empresarial (dato identificativo).",
    "telefono": "Número telefónico de contacto (dato personal / de contacto no requerido para el estudio).",
    "correoelec": "Correo electrónico del establecimiento o propietario (dato personal identificable).",
    "www": "Sitio web o perfil de red social comercial (no requerido para agregación territorial).",
    "clee": "Clave Estadística de Establecimiento (código redundante al conservar id_establecimiento).",
    "tipo_vial": "Tipo de vialidad de domicilio exacto (descartado por minimización espacial).",
    "nom_vial": "Nombre de calle/vialidad de domicilio exacto (descartado por minimización espacial).",
    "tipo_v_e_1": "Entrecalle 1 (domicilio detallado innecesario).",
    "nom_v_e_1": "Nombre de entrecalle 1 (domicilio detallado innecesario).",
    "tipo_v_e_2": "Entrecalle 2 (domicilio detallado innecesario).",
    "nom_v_e_2": "Nombre de entrecalle 2 (domicilio detallado innecesario).",
    "tipo_v_e_3": "Entrecalle 3 (domicilio detallado innecesario).",
    "nom_v_e_3": "Nombre de entrecalle 3 (domicilio detallado innecesario).",
    "numero_ext": "Número exterior del domicilio exacto (descartado por minimización).",
    "letra_ext": "Letra exterior del domicilio exacto (descartado por minimización).",
    "edificio": "Nombre de edificio (descartado por minimización).",
    "edificio_e": "Piso o nivel de edificio (descartado por minimización).",
    "numero_int": "Número interior del domicilio (descartado por minimización).",
    "letra_int": "Letra interior del domicilio (descartado por minimización).",
    "tipo_asent": "Tipo de asentamiento humano (descartado por minimización).",
    "nomb_asent": "Nombre de colonia o asentamiento (descartado por minimización).",
    "tipoCenCom": "Tipo de centro comercial (descartado por minimización).",
    "nom_CenCom": "Nombre de centro comercial (descartado por minimización).",
    "num_local": "Número de local comercial (descartado por minimización).",
    "cod_postal": "Código postal (no requerido al contar con clave municipal, localidad y AGEB).",
    "manzana": "Clave de manzana censal (descartada para reducir reidentificación microespacial).",
    "tipoUniEco": "Tipo de unidad económica (fijo/semifijo; informativo secundario).",
    "entidad": "Nombre de entidad redundante con cve_ent='06'.",
}

CATEGORIAS_VALIDAS = sorted({v["categoria"] for v in CATALOGO_SCIAN_ESTUDIO.values()})
CODIGOS_SCIAN_VALIDOS = sorted(CATALOGO_SCIAN_ESTUDIO.keys())
MUNICIPIOS_VALIDOS = sorted(MUNICIPIOS_COLIMA.keys())

# Esquema Pandera estricto para Capa Plata Geoespacial (evaluación lazy)
esquema_denue_plata = pa.DataFrameSchema(
    columns={
        "id_establecimiento": pa.Column(
            pa.String,
            checks=[pa.Check.str_length(min_value=1, error="Identificador de establecimiento vacío")],
            nullable=False,
            unique=True,
            description="Identificador único oficial del establecimiento en DENUE",
        ),
        "codigo_act": pa.Column(
            pa.String,
            checks=[pa.Check.isin(CODIGOS_SCIAN_VALIDOS, error="Código SCIAN inexistente en el catálogo oficial del estudio")],
            nullable=False,
            description="Código de clase de actividad económica SCIAN (6 dígitos)",
        ),
        "nombre_act": pa.Column(
            pa.String,
            checks=[pa.Check.str_length(min_value=1, error="Nombre de actividad económica vacío")],
            nullable=False,
            description="Nombre literal oficial de la clase SCIAN",
        ),
        "categoria": pa.Column(
            pa.String,
            checks=[pa.Check.isin(CATEGORIAS_VALIDAS, error="Categoría analítica no reconocida")],
            nullable=False,
            description="Categoría analítica del observatorio (escuela_basica, abarrotes, dulces, helados_paletas)",
        ),
        "estrato_personal": pa.Column(
            pa.String,
            nullable=True,
            description="Estrato oficial de personal ocupado reportado por DENUE",
        ),
        "cve_ent": pa.Column(
            pa.String,
            checks=[pa.Check.equal_to(ENTIDAD_COLIMA, error="Entidad federativa distinta a Colima (06)")],
            nullable=False,
            description="Clave oficial de entidad federativa (06)",
        ),
        "cve_mun": pa.Column(
            pa.String,
            checks=[pa.Check.isin(MUNICIPIOS_VALIDOS, error="Clave de municipio no válida para Colima (001-010)")],
            nullable=False,
            description="Clave oficial de municipio INEGI (001 a 010)",
        ),
        "municipio": pa.Column(
            pa.String,
            checks=[pa.Check.str_length(min_value=1, error="Nombre de municipio vacío")],
            nullable=False,
            description="Nombre oficial del municipio",
        ),
        "latitud": pa.Column(
            pa.Float,
            checks=[
                pa.Check.in_range(
                    COLIMA_LAT_MIN,
                    COLIMA_LAT_MAX,
                    error=f"Latitud fuera de límites del estado de Colima [{COLIMA_LAT_MIN}, {COLIMA_LAT_MAX}]",
                )
            ],
            nullable=False,
            description="Latitud geográfica WGS84 en grados decimales",
        ),
        "longitud": pa.Column(
            pa.Float,
            checks=[
                pa.Check.in_range(
                    COLIMA_LON_MIN,
                    COLIMA_LON_MAX,
                    error=f"Longitud fuera de límites del estado de Colima [{COLIMA_LON_MIN}, {COLIMA_LON_MAX}]",
                )
            ],
            nullable=False,
            description="Longitud geográfica WGS84 en grados decimales",
        ),
        "fecha_captura_utc": pa.Column(
            pa.String,
            nullable=False,
            description="Marca temporal UTC de ingesta en Bronce",
        ),
        "archivo_origen": pa.Column(
            pa.String,
            nullable=False,
            description="Archivo crudo de origen en datos/bronce/denue/",
        ),
    },
    strict=False,
    ordered=False,
)


class PuertaCalidadGeo:
    """Puerta de Calidad Geoespacial basada en Pandera (lazy=True) + contención espacial."""

    def __init__(self, cuarentena_dir: Path = Path("datos/cuarentena")):
        self.cuarentena_dir = cuarentena_dir
        self.cuarentena_dir.mkdir(parents=True, exist_ok=True)

    def validar_y_segregar(
        self,
        df: pd.DataFrame,
        gdf_marco: Optional[gpd.GeoDataFrame] = None,
    ) -> Tuple[gpd.GeoDataFrame, pd.DataFrame]:
        """
        Valida un DataFrame de registros minimizados con Pandera (lazy=True)
        y, si se proporciona el Marco Geoestadístico, verifica contención espacial
        dentro de los polígonos estatales de Colima.
        Devuelve (gdf_validos_epsg4326, df_cuarentena_calidad).
        """
        ahora_utc = datetime.now(timezone.utc).isoformat()
        filas_cuarentena: List[Dict[str, Any]] = []

        df_work = df.copy().reset_index(drop=True)
        # Coerción segura de latitud/longitud a float (nulos o texto inválido quedan como NaN y Pandera los rechaza)
        df_work["latitud"] = pd.to_numeric(df_work.get("latitud"), errors="coerce")
        df_work["longitud"] = pd.to_numeric(df_work.get("longitud"), errors="coerce")

        indices_fallidos: set = set()
        motivos_por_idx: Dict[int, List[str]] = {}

        try:
            esquema_denue_plata.validate(df_work, lazy=True)
            logger.info("Puerta de Calidad Pandera Geo superada: 100%% de los registros (%d) conformes.", len(df_work))
        except SchemaErrors as err:
            logger.warning("Puerta de Calidad Pandera Geo detectó anomalías (lazy=True). Segregando a cuarentena...")
            fc = err.failure_cases
            for _, row in fc.iterrows():
                idx_val = row["index"]
                if pd.isna(idx_val):
                    continue
                i = int(idx_val)
                indices_fallidos.add(i)
                col = row["column"]
                chk = row["check"]
                val = row["failure_case"]
                motivos_por_idx.setdefault(i, []).append(
                    f"Fallo en columna '{col}' (regla: {chk}, valor_recibido: {val})"
                )

            # Manejo explícito de duplicados en id_establecimiento si Pandera reportó index=None en unicidad
            dups_mask = df_work["id_establecimiento"].duplicated(keep=False)
            for i in df_work.index[dups_mask]:
                if i not in indices_fallidos:
                    indices_fallidos.add(int(i))
                motivo_dup = f"Identificador duplicado en 'id_establecimiento': {df_work.loc[i, 'id_establecimiento']}"
                if motivo_dup not in motivos_por_idx.get(int(i), []):
                    motivos_por_idx.setdefault(int(i), []).append(motivo_dup)

        mask_rechazo_pandera = df_work.index.isin(indices_fallidos)
        df_validos_tab = df_work[~mask_rechazo_pandera].copy().reset_index(drop=True)
        df_rechazados_pandera = df_work[mask_rechazo_pandera].copy()

        for idx_orig, row_inv in df_rechazados_pandera.iterrows():
            motivos = "; ".join(motivos_por_idx.get(int(idx_orig), ["Violación de esquema Pandera Geo"]))
            filas_cuarentena.append({
                "id_establecimiento": str(row_inv.get("id_establecimiento", "")),
                "codigo_act": str(row_inv.get("codigo_act", "")),
                "cve_mun": str(row_inv.get("cve_mun", "")),
                "latitud": row_inv.get("latitud"),
                "longitud": row_inv.get("longitud"),
                "regla_violada": "pandera_geo_schema_check",
                "motivo_texto": motivos,
                "fecha_hora_validacion": ahora_utc,
                "archivo_captura_origen": str(row_inv.get("archivo_origen", "desconocido")),
                "fase_deteccion": "Fase 3: Puerta de Calidad Geoespacial (Pandera)",
            })

        # Conversión a GeoDataFrame en CRS EPSG:4326
        gdf_validos = gpd.GeoDataFrame(
            df_validos_tab,
            geometry=gpd.points_from_xy(df_validos_tab["longitud"], df_validos_tab["latitud"]),
            crs=CRS_ALMACENAMIENTO,
        )

        # Validación espacial exacta contra los polígonos oficiales del Marco Geoestadístico
        if gdf_marco is not None and len(gdf_validos) > 0:
            marco_4326 = gdf_marco.to_crs(CRS_ALMACENAMIENTO)
            union_estatal = marco_4326.geometry.union_all()
            dentro = gdf_validos.geometry.within(union_estatal)
            fuera_mask = ~dentro
            if fuera_mask.any():
                logger.warning(
                    "Se detectaron %d puntos fuera de los polígonos oficiales de Colima. Segregando a cuarentena...",
                    int(fuera_mask.sum()),
                )
                for _, row_f in gdf_validos[fuera_mask].iterrows():
                    filas_cuarentena.append({
                        "id_establecimiento": str(row_f["id_establecimiento"]),
                        "codigo_act": str(row_f["codigo_act"]),
                        "cve_mun": str(row_f["cve_mun"]),
                        "latitud": float(row_f["latitud"]),
                        "longitud": float(row_f["longitud"]),
                        "regla_violada": "coordenada_fuera_limites_colima",
                        "motivo_texto": (
                            f"Coordenada ({row_f['latitud']}, {row_f['longitud']}) fuera de los polígonos "
                            f"oficiales del Marco Geoestadístico de Colima."
                        ),
                        "fecha_hora_validacion": ahora_utc,
                        "archivo_captura_origen": str(row_f["archivo_origen"]),
                        "fase_deteccion": "Fase 3: Validación Espacial Marco Geoestadístico",
                    })
                gdf_validos = gdf_validos[dentro].copy().reset_index(drop=True)

        df_cuarentena = pd.DataFrame(
            filas_cuarentena,
            columns=[
                "id_establecimiento",
                "codigo_act",
                "cve_mun",
                "latitud",
                "longitud",
                "regla_violada",
                "motivo_texto",
                "fecha_hora_validacion",
                "archivo_captura_origen",
                "fase_deteccion",
            ],
        )
        return gdf_validos, df_cuarentena

    def conciliar(
        self,
        total_entrada: int,
        gdf_plata: gpd.GeoDataFrame,
        df_cuarentena_total: pd.DataFrame,
    ) -> bool:
        """Verifica conciliación estricta: entrada = Plata + Cuarentena."""
        n_plata = len(gdf_plata)
        n_cuar = len(df_cuarentena_total)
        if total_entrada != (n_plata + n_cuar):
            msg = (
                f"FALLA CRÍTICA DE CONCILIACIÓN GEOESPACIAL: Entrada ({total_entrada}) != "
                f"Plata ({n_plata}) + Cuarentena ({n_cuar}). "
                f"Diferencia: {total_entrada - (n_plata + n_cuar)}."
            )
            logger.error(msg)
            raise ValueError(msg)
        logger.info(
            "CONCILIACIÓN GEOESPACIAL VERIFICADA: %d (Entrada) == %d (Plata) + %d (Cuarentena).",
            total_entrada,
            n_plata,
            n_cuar,
        )
        return True


def cargar_marco_geoestadistico(
    bronze_mg_dir: Path = BASE_DIR / "datos" / "bronce" / "marco_geoestadistico",
    plata_dir: Path = BASE_DIR / "datos" / "plata",
) -> Tuple[gpd.GeoDataFrame, Path]:
    """
    Carga el archivo GeoJSON más reciente del Marco Geoestadístico en Bronce,
    normaliza su CRS a EPSG:4326 y calcula áreas oficiales en km² usando EPSG:6372.
    """
    archivos = sorted(bronze_mg_dir.glob("marco_geoestadistico_colima_municipios_*.geojson"))
    if not archivos:
        raise FileNotFoundError(f"No se encontró archivo GeoJSON del Marco Geoestadístico en {bronze_mg_dir}")

    ruta_mg = archivos[-1]
    gdf = gpd.read_file(ruta_mg)
    if gdf.crs is None:
        gdf = gdf.set_crs(CRS_ALMACENAMIENTO)
    else:
        gdf = gdf.to_crs(CRS_ALMACENAMIENTO)

    # Normalizar nombres de columnas entre wscatgeo v1 y v2
    rename_map = {}
    if "cve_agem" in gdf.columns and "cve_mun" not in gdf.columns:
        rename_map["cve_agem"] = "cve_mun"
    if "cve_agee" in gdf.columns and "cve_ent" not in gdf.columns:
        rename_map["cve_agee"] = "cve_ent"
    if "nom_agem" in gdf.columns and "nomgeo" not in gdf.columns:
        rename_map["nom_agem"] = "nomgeo"
    if "pob" in gdf.columns and "pob_total" not in gdf.columns:
        rename_map["pob"] = "pob_total"
    if rename_map:
        gdf = gdf.rename(columns=rename_map)

    gdf["cve_mun"] = gdf["cve_mun"].astype(str).str.strip().str.zfill(3)
    gdf["cve_ent"] = gdf["cve_ent"].astype(str).str.strip().str.zfill(2)
    gdf["pob_total"] = pd.to_numeric(gdf.get("pob_total"), errors="coerce").astype("Int64")

    # Cálculo exacto de área en km² en proyección métrica oficial de México (EPSG:6372)
    gdf_6372 = gdf.to_crs(CRS_PROYECTADO_MX)
    gdf["area_km2_oficial"] = (gdf_6372.geometry.area / 1_000_000.0).round(4)

    # Área continental (recortando Archipiélago de Revillagigedo para densidades territoriales continentales)
    gdf_cont = gdf.copy()
    gdf_cont["geometry"] = gdf_cont.geometry.intersection(COLIMA_CONTINENTAL_BOX)
    gdf_cont_6372 = gdf_cont.to_crs(CRS_PROYECTADO_MX)
    gdf["area_km2_continental"] = (gdf_cont_6372.geometry.area / 1_000_000.0).round(4)

    gdf["archivo_origen_marco"] = ruta_mg.name
    gdf = gdf.sort_values("cve_mun").reset_index(drop=True)

    plata_dir.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(plata_dir / "marco_geoestadistico_colima_plata.parquet", index=False)
    logger.info("Marco Geoestadístico en Plata guardado (%d municipios, CRS=%s).", len(gdf), gdf.crs)
    return gdf, ruta_mg


def leer_capturas_denue_bronce(
    bronze_denue_dir: Path = BASE_DIR / "datos" / "bronce" / "denue",
) -> Tuple[List[Dict[str, Any]], List[Path]]:
    """
    Lee todos los archivos ZIP crudos de DENUE en datos/bronce/denue/ junto con
    sus metadatos de fecha de ingesta UTC.
    """
    zips = sorted(bronze_denue_dir.glob("denue_colima_raw_*.zip"))
    if not zips:
        raise FileNotFoundError(f"No se encontraron archivos ZIP crudos del DENUE en {bronze_denue_dir}")

    registros: List[Dict[str, Any]] = []
    for zpath in zips:
        # Buscar archivo de metadatos compañero
        ts_suffix = zpath.stem.replace("denue_colima_raw_", "")
        meta_path = bronze_denue_dir / f"denue_colima_metadata_{ts_suffix}.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            fecha_ingesta = str(meta.get("fecha_ingesta_utc", ""))
        else:
            fecha_ingesta = datetime.fromtimestamp(zpath.stat().st_mtime, tz=timezone.utc).isoformat()

        with zipfile.ZipFile(zpath, "r") as zf:
            candidatos = [n for n in zf.namelist() if n.lower().endswith(".csv") and "conjunto_de_datos" in n.lower()]
            if not candidatos:
                candidatos = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            csv_interno = candidatos[0]
            raw_bytes = zf.open(csv_interno, "r").read()
            try:
                texto = raw_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                texto = raw_bytes.decode("latin-1")

        df_raw = pd.read_csv(io.StringIO(texto), dtype=str, low_memory=False)
        df_raw["__archivo_origen"] = zpath.name
        df_raw["__fecha_captura_utc"] = fecha_ingesta
        registros.extend(df_raw.to_dict(orient="records"))
        logger.info("Leídos %d registros crudos desde %s (ingesta %s).", len(df_raw), zpath.name, fecha_ingesta)

    return registros, zips


def construir_plata_geoespacial(
    bronze_denue_dir: Path = BASE_DIR / "datos" / "bronce" / "denue",
    bronze_mg_dir: Path = BASE_DIR / "datos" / "bronce" / "marco_geoestadistico",
    plata_dir: Path = BASE_DIR / "datos" / "plata",
    cuarentena_dir: Path = BASE_DIR / "datos" / "cuarentena",
) -> Tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Ejecuta la Fase 3 completa:
    1. Carga Marco Geoestadístico (CRS EPSG:4326 + áreas EPSG:6372).
    2. Lee todos los registros crudos de DENUE en Bronce.
    3. Segrega actividades fuera del catálogo SCIAN de estudio a cuarentena (descarte por diseño).
    4. Resuelve capturas históricas repetidas (gana la captura más reciente por id_establecimiento).
    5. Aplica minimización estricta de datos personales.
    6. Ejecuta Puerta de Calidad Pandera (lazy=True) + contención espacial.
    7. Concilia entrada == Plata + Cuarentena (falla si no cuadra).
    8. Guarda GeoParquet, GeoJSON y cuarentena.
    """
    plata_dir.mkdir(parents=True, exist_ok=True)
    cuarentena_dir.mkdir(parents=True, exist_ok=True)

    gdf_marco, ruta_mg = cargar_marco_geoestadistico(bronze_mg_dir=bronze_mg_dir, plata_dir=plata_dir)
    registros_crudos, zips_bronce = leer_capturas_denue_bronce(bronze_denue_dir=bronze_denue_dir)
    total_entrada = len(registros_crudos)

    ahora_utc = datetime.now(timezone.utc).isoformat()
    cuarentena_diseno: List[Dict[str, Any]] = []
    candidatos_estudio: List[Dict[str, Any]] = []

    for r in registros_crudos:
        cod = str(r.get("codigo_act", "")).strip()
        id_est = str(r.get("id", "")).strip()
        cve_mun = str(r.get("cve_mun", "")).strip().zfill(3)
        lat_raw = r.get("latitud")
        lon_raw = r.get("longitud")
        arch = str(r.get("__archivo_origen", ""))
        ts_cap = str(r.get("__fecha_captura_utc", ""))

        # Descarte por diseño 1: actividad económica fuera del catálogo de estudio
        if cod not in CATALOGO_SCIAN_ESTUDIO:
            cuarentena_diseno.append({
                "id_establecimiento": id_est,
                "codigo_act": cod,
                "cve_mun": cve_mun,
                "latitud": pd.to_numeric(lat_raw, errors="coerce"),
                "longitud": pd.to_numeric(lon_raw, errors="coerce"),
                "regla_violada": "scian_fuera_de_alcance",
                "motivo_texto": (
                    f"Descarte por diseño: código SCIAN '{cod}' fuera de las 15 clases oficiales "
                    f"del estudio (escuelas básicas 6111xx, abarrotes 461110, dulces 461160, helados/paletas 461170)."
                ),
                "fecha_hora_validacion": ahora_utc,
                "archivo_captura_origen": arch,
                "fase_deteccion": "Fase 3: Filtro de Alcance SCIAN (Diseño)",
            })
            continue

        info_scian = CATALOGO_SCIAN_ESTUDIO[cod]
        # Minimización estricta: solo conservar columnas analíticas/geográficas permitidas
        candidatos_estudio.append({
            "id_establecimiento": id_est,
            "codigo_act": cod,
            "nombre_act": info_scian["nombre_literal"],
            "categoria": info_scian["categoria"],
            "estrato_personal": str(r.get("per_ocu", "")).strip() or None,
            "cve_ent": str(r.get("cve_ent", ENTIDAD_COLIMA)).strip().zfill(2),
            "cve_mun": cve_mun,
            "municipio": MUNICIPIOS_COLIMA.get(cve_mun, str(r.get("municipio", "")).strip()),
            "cve_loc": str(r.get("cve_loc", "")).strip().zfill(4),
            "localidad": str(r.get("localidad", "")).strip(),
            "ageb": str(r.get("ageb", "")).strip(),
            "latitud": lat_raw,
            "longitud": lon_raw,
            "fecha_alta": str(r.get("fecha_alta", "")).strip(),
            "fecha_captura_utc": ts_cap,
            "archivo_origen": arch,
        })

    # Descarte por diseño 2: deduplicación entre capturas históricas (gana la más reciente)
    candidatos_estudio.sort(
        key=lambda x: (x["id_establecimiento"], x["fecha_captura_utc"]),
        reverse=True,
    )
    vistos = set()
    candidatos_unicos: List[Dict[str, Any]] = []
    for rec in candidatos_estudio:
        eid = rec["id_establecimiento"]
        if eid in vistos:
            cuarentena_diseno.append({
                "id_establecimiento": eid,
                "codigo_act": rec["codigo_act"],
                "cve_mun": rec["cve_mun"],
                "latitud": pd.to_numeric(rec["latitud"], errors="coerce"),
                "longitud": pd.to_numeric(rec["longitud"], errors="coerce"),
                "regla_violada": "duplicado_captura_anterior",
                "motivo_texto": f"Duplicado de captura histórica anterior para establecimiento {eid}; prevalece captura más reciente.",
                "fecha_hora_validacion": ahora_utc,
                "archivo_captura_origen": rec["archivo_origen"],
                "fase_deteccion": "Fase 3: Resolución de Capturas DENUE",
            })
        else:
            vistos.add(eid)
            candidatos_unicos.append(rec)

    df_candidatos = pd.DataFrame(candidatos_unicos)

    # Verificar que ningún campo personal prohibido sobrevivió
    cols_prohibidas_presentes = set(df_candidatos.columns) & set(CAMPOS_PERSONALES_Y_NO_ANALITICOS_DESCARTADOS.keys())
    if cols_prohibidas_presentes:
        raise RuntimeError(f"Violación de minimización de datos personales: {cols_prohibidas_presentes}")

    # Puerta de Calidad Pandera (lazy) + contención espacial Marco Geoestadístico
    puerta_geo = PuertaCalidadGeo(cuarentena_dir=cuarentena_dir)
    gdf_plata, df_cuarentena_calidad = puerta_geo.validar_y_segregar(df_candidatos, gdf_marco=gdf_marco)

    df_cuarentena_diseno = pd.DataFrame(
        cuarentena_diseno,
        columns=[
            "id_establecimiento",
            "codigo_act",
            "cve_mun",
            "latitud",
            "longitud",
            "regla_violada",
            "motivo_texto",
            "fecha_hora_validacion",
            "archivo_captura_origen",
            "fase_deteccion",
        ],
    )
    df_cuarentena_denue = pd.concat([df_cuarentena_diseno, df_cuarentena_calidad], ignore_index=True)

    # Conciliación estricta obligatoria
    puerta_geo.conciliar(total_entrada, gdf_plata, df_cuarentena_denue)

    # Orden estable
    gdf_plata = gdf_plata.sort_values(["cve_mun", "categoria", "id_establecimiento"]).reset_index(drop=True)

    # Persistencia en datos/plata/ (GeoParquet + GeoJSON en EPSG:4326) y datos/cuarentena/
    ruta_plata_parquet = plata_dir / "denue_colima_plata.parquet"
    ruta_plata_geojson = plata_dir / "denue_colima_plata.geojson"
    gdf_plata.to_parquet(ruta_plata_parquet, index=False)
    gdf_plata.to_file(ruta_plata_geojson, driver="GeoJSON")

    df_cuarentena_denue.to_parquet(cuarentena_dir / "cuarentena_denue.parquet", index=False)
    df_cuarentena_denue.to_csv(cuarentena_dir / "cuarentena_denue.csv", index=False, encoding="utf-8")

    resumen = {
        "total_entrada": total_entrada,
        "total_plata": len(gdf_plata),
        "total_cuarentena": len(df_cuarentena_denue),
        "cuarentena_por_regla": df_cuarentena_denue["regla_violada"].value_counts().to_dict(),
        "violaciones_calidad_reales": len(df_cuarentena_calidad),
        "crs_almacenamiento": str(gdf_plata.crs),
        "crs_proyectado_calculo": CRS_PROYECTADO_MX,
        "campos_conservados": list(gdf_plata.columns),
        "n_campos_descartados": len(CAMPOS_PERSONALES_Y_NO_ANALITICOS_DESCARTADOS),
        "archivo_marco": ruta_mg.name,
        "archivos_denue": [z.name for z in zips_bronce],
    }

    logger.info(
        "Capa Plata Geoespacial generada: %d puntos válidos (%s), %d en cuarentena (%d por calidad real).",
        resumen["total_plata"],
        resumen["crs_almacenamiento"],
        resumen["total_cuarentena"],
        resumen["violaciones_calidad_reales"],
    )
    return gdf_plata, gdf_marco, df_cuarentena_denue, resumen


if __name__ == "__main__":
    construir_plata_geoespacial()
