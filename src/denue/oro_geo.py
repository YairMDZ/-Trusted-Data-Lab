"""
Módulo de Capa Oro Geoespacial y Visualización Cartográfica (Fase 4 - Entrega E2).
- Agrega los registros válidos de Capa Plata (EPSG:4326) a nivel municipal, de localidad y de AGEB.
- NO publica puntos ni coordenadas individuales en datos/oro/.
- Calcula densidad comercial por escuela, densidad por km² (proyección EPSG:6372) y tasas por 10,000 hab.
- Produce mapas cartográficos en docs/E2/figuras/ usando exclusivamente los polígonos oficiales del
  Marco Geoestadístico del INEGI como base (sin descarga masiva de teselas externas).
- Genera docs/E2/diccionario_geoespacial.md.
"""

import logging
import sys
from pathlib import Path
from typing import Dict, Tuple
import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.denue.plata_geo import (
    CAMPOS_PERSONALES_Y_NO_ANALITICOS_DESCARTADOS,
    COLIMA_CONTINENTAL_BOX,
    CRS_ALMACENAMIENTO,
    CRS_PROYECTADO_MX,
)

logger = logging.getLogger("denue.oro_geo")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def construir_oro_geoespacial(
    gdf_plata: gpd.GeoDataFrame,
    gdf_marco: gpd.GeoDataFrame,
    oro_dir: Path = BASE_DIR / "datos" / "oro",
    figuras_dir: Path = BASE_DIR / "docs" / "E2" / "figuras",
    diccionario_path: Path = BASE_DIR / "docs" / "E2" / "diccionario_geoespacial.md",
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Construye las tablas agregadas geoespaciales en datos/oro/,
    genera los mapas cartográficos en docs/E2/figuras/ y redacta
    docs/E2/diccionario_geoespacial.md.
    """
    oro_dir.mkdir(parents=True, exist_ok=True)
    figuras_dir.mkdir(parents=True, exist_ok=True)
    diccionario_path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(gdf_plata.drop(columns=["geometry"]))

    # Fecha de captura para pie de mapas
    fecha_captura_str = str(df["fecha_captura_utc"].max())[:10] if len(df) > 0 else "N/D"

    # --------------------------------------------------------------------------
    # 1. Tabla Oro Municipal (10 municipios de Colima)
    # --------------------------------------------------------------------------
    piv_mun = (
        df.pivot_table(
            index="cve_mun",
            columns="categoria",
            values="id_establecimiento",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for col_cat in ["escuela_basica", "abarrotes", "dulces", "helados_paletas"]:
        if col_cat not in piv_mun.columns:
            piv_mun[col_cat] = 0

    piv_mun = piv_mun.rename(columns={
        "escuela_basica": "n_escuelas_basicas",
        "abarrotes": "n_abarrotes",
        "dulces": "n_dulces",
        "helados_paletas": "n_helados_paletas",
    })

    marco_base = pd.DataFrame(
        gdf_marco[["cve_ent", "cve_mun", "nomgeo", "pob_total", "area_km2_oficial", "area_km2_continental"]]
    ).rename(columns={"nomgeo": "municipio", "pob_total": "pob_total_censo2020"})

    df_oro_mun = marco_base.merge(piv_mun, on="cve_mun", how="left")
    for c in ["n_escuelas_basicas", "n_abarrotes", "n_dulces", "n_helados_paletas"]:
        df_oro_mun[c] = df_oro_mun[c].fillna(0).astype(int)

    df_oro_mun["n_comercios_total"] = (
        df_oro_mun["n_abarrotes"] + df_oro_mun["n_dulces"] + df_oro_mun["n_helados_paletas"]
    )
    df_oro_mun["n_unidades_estudio"] = df_oro_mun["n_escuelas_basicas"] + df_oro_mun["n_comercios_total"]
    df_oro_mun["comercios_por_escuela"] = np.where(
        df_oro_mun["n_escuelas_basicas"] > 0,
        (df_oro_mun["n_comercios_total"] / df_oro_mun["n_escuelas_basicas"]).round(4),
        np.nan,
    )
    df_oro_mun["dulces_helados_por_escuela"] = np.where(
        df_oro_mun["n_escuelas_basicas"] > 0,
        ((df_oro_mun["n_dulces"] + df_oro_mun["n_helados_paletas"]) / df_oro_mun["n_escuelas_basicas"]).round(4),
        np.nan,
    )
    df_oro_mun["escuelas_por_km2_continental"] = (
        df_oro_mun["n_escuelas_basicas"] / df_oro_mun["area_km2_continental"]
    ).round(4)
    df_oro_mun["comercios_por_km2_continental"] = (
        df_oro_mun["n_comercios_total"] / df_oro_mun["area_km2_continental"]
    ).round(4)
    df_oro_mun["escuelas_por_km2_oficial"] = (
        df_oro_mun["n_escuelas_basicas"] / df_oro_mun["area_km2_oficial"]
    ).round(4)
    df_oro_mun["comercios_por_km2_oficial"] = (
        df_oro_mun["n_comercios_total"] / df_oro_mun["area_km2_oficial"]
    ).round(4)
    df_oro_mun["escuelas_por_10k_hab"] = (
        df_oro_mun["n_escuelas_basicas"] / (df_oro_mun["pob_total_censo2020"].astype(float) / 10_000.0)
    ).round(4)
    df_oro_mun["comercios_por_10k_hab"] = (
        df_oro_mun["n_comercios_total"] / (df_oro_mun["pob_total_censo2020"].astype(float) / 10_000.0)
    ).round(4)

    df_oro_mun = df_oro_mun.sort_values("cve_mun").reset_index(drop=True)

    # --------------------------------------------------------------------------
    # 2. Tabla Oro por AGEB (sin puntos individuales)
    # --------------------------------------------------------------------------
    piv_ageb = (
        df.pivot_table(
            index=["cve_ent", "cve_mun", "municipio", "cve_loc", "localidad", "ageb"],
            columns="categoria",
            values="id_establecimiento",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for col_cat in ["escuela_basica", "abarrotes", "dulces", "helados_paletas"]:
        if col_cat not in piv_ageb.columns:
            piv_ageb[col_cat] = 0
    piv_ageb = piv_ageb.rename(columns={
        "escuela_basica": "n_escuelas_basicas",
        "abarrotes": "n_abarrotes",
        "dulces": "n_dulces",
        "helados_paletas": "n_helados_paletas",
    })
    piv_ageb["n_comercios_total"] = (
        piv_ageb["n_abarrotes"] + piv_ageb["n_dulces"] + piv_ageb["n_helados_paletas"]
    )
    piv_ageb["n_unidades_estudio"] = piv_ageb["n_escuelas_basicas"] + piv_ageb["n_comercios_total"]
    piv_ageb["comercios_por_escuela"] = np.where(
        piv_ageb["n_escuelas_basicas"] > 0,
        (piv_ageb["n_comercios_total"] / piv_ageb["n_escuelas_basicas"]).round(4),
        np.nan,
    )
    df_oro_ageb = piv_ageb.sort_values(["cve_mun", "cve_loc", "ageb"]).reset_index(drop=True)

    # --------------------------------------------------------------------------
    # 3. Tabla Oro por Localidad (sin puntos individuales)
    # --------------------------------------------------------------------------
    piv_loc = (
        df.pivot_table(
            index=["cve_ent", "cve_mun", "municipio", "cve_loc", "localidad"],
            columns="categoria",
            values="id_establecimiento",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    for col_cat in ["escuela_basica", "abarrotes", "dulces", "helados_paletas"]:
        if col_cat not in piv_loc.columns:
            piv_loc[col_cat] = 0
    piv_loc = piv_loc.rename(columns={
        "escuela_basica": "n_escuelas_basicas",
        "abarrotes": "n_abarrotes",
        "dulces": "n_dulces",
        "helados_paletas": "n_helados_paletas",
    })
    piv_loc["n_comercios_total"] = (
        piv_loc["n_abarrotes"] + piv_loc["n_dulces"] + piv_loc["n_helados_paletas"]
    )
    piv_loc["n_unidades_estudio"] = piv_loc["n_escuelas_basicas"] + piv_loc["n_comercios_total"]
    piv_loc["comercios_por_escuela"] = np.where(
        piv_loc["n_escuelas_basicas"] > 0,
        (piv_loc["n_comercios_total"] / piv_loc["n_escuelas_basicas"]).round(4),
        np.nan,
    )
    df_oro_loc = piv_loc.sort_values(["cve_mun", "cve_loc"]).reset_index(drop=True)

    # Persistencia en datos/oro/ (solo tablas agregadas; cero puntos individuales)
    df_oro_mun.to_parquet(oro_dir / "densidad_comercial_escolar_municipios.parquet", index=False)
    df_oro_mun.to_csv(oro_dir / "densidad_comercial_escolar_municipios.csv", index=False, encoding="utf-8")

    df_oro_ageb.to_parquet(oro_dir / "densidad_comercial_escolar_ageb.parquet", index=False)
    df_oro_ageb.to_csv(oro_dir / "densidad_comercial_escolar_ageb.csv", index=False, encoding="utf-8")

    df_oro_loc.to_parquet(oro_dir / "densidad_comercial_escolar_localidad.parquet", index=False)
    df_oro_loc.to_csv(oro_dir / "densidad_comercial_escolar_localidad.csv", index=False, encoding="utf-8")

    # --------------------------------------------------------------------------
    # 4. Visualizaciones Cartográficas (usando Marco Geoestadístico oficial)
    # --------------------------------------------------------------------------
    _generar_mapa_coropleta(gdf_marco, df_oro_mun, figuras_dir / "coropleta_comercios_por_escuela_municipios.png", fecha_captura_str)
    _generar_mapa_puntos_colima(gdf_marco, gdf_plata, figuras_dir / "mapa_puntos_escuelas_dulces_colima.png", fecha_captura_str)

    # --------------------------------------------------------------------------
    # 5. Diccionario de Datos Geoespacial
    # --------------------------------------------------------------------------
    _generar_diccionario_geoespacial(diccionario_path, df_oro_mun, df_oro_ageb, df_oro_loc)

    logger.info(
        "Capa Oro Geoespacial construida: %d municipios, %d localidades, %d AGEBs.",
        len(df_oro_mun),
        len(df_oro_loc),
        len(df_oro_ageb),
    )
    return df_oro_mun, df_oro_ageb, df_oro_loc


def _generar_mapa_coropleta(
    gdf_marco: gpd.GeoDataFrame,
    df_oro_mun: pd.DataFrame,
    output_path: Path,
    fecha_captura: str,
) -> None:
    """Genera el mapa coroplético municipal de comercios por escuela en Colima continental."""
    gdf_plot = gdf_marco.to_crs(CRS_ALMACENAMIENTO).copy()
    # Recortar gráficamente a Colima continental (sin Archipiélago de Revillagigedo)
    gdf_plot["geometry"] = gdf_plot.geometry.intersection(COLIMA_CONTINENTAL_BOX)
    gdf_plot = gdf_plot.merge(
        df_oro_mun[["cve_mun", "municipio", "comercios_por_escuela", "n_escuelas_basicas", "n_comercios_total"]],
        on="cve_mun",
        how="left",
    )

    fig, ax = plt.subplots(figsize=(11, 8.5), dpi=180)
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#EAF3FA")

    gdf_plot.plot(
        column="comercios_por_escuela",
        cmap="YlOrRd",
        linewidth=1.1,
        edgecolor="#2C3E50",
        legend=True,
        legend_kwds={
            "label": "Comercios minoristas de estudio por escuela básica",
            "orientation": "vertical",
            "shrink": 0.72,
            "pad": 0.02,
        },
        ax=ax,
    )

    # Etiquetas municipales usando representative_point() para garantizar que caigan dentro del polígono
    offsets = {
        "008": (-0.07, 0.04),   # Minatitlán (evitar cruce con Villa de Álvarez)
        "010": (0.06, -0.03),   # Villa de Álvarez
        "002": (0.04, -0.02),   # Colima
        "004": (-0.02, -0.02),  # Coquimatlán
        "003": (0.02, 0.02),    # Comala
        "005": (0.02, 0.01),    # Cuauhtémoc
        "001": (-0.01, -0.01),  # Armería
    }
    for _, row in gdf_plot.iterrows():
        pt = row.geometry.representative_point()
        dx, dy = offsets.get(row["cve_mun"], (0.0, 0.0))
        etiqueta = f"{row['municipio']}\n{row['comercios_por_escuela']:.2f} com/esc\n({row['n_escuelas_basicas']} esc.)"
        ax.annotate(
            text=etiqueta,
            xy=(pt.x + dx, pt.y + dy),
            ha="center",
            va="center",
            fontsize=7.3,
            fontweight="bold",
            color="#1B2631",
            bbox=dict(boxstyle="round,pad=0.22", facecolor="white", edgecolor="#AAB7B8", alpha=0.84),
        )

    ax.set_xlim(-104.74, -103.44)
    ax.set_ylim(18.64, 19.55)
    ax.set_xlabel("Longitud Oeste (° WGS84 / EPSG:4326)", fontsize=9.5)
    ax.set_ylabel("Latitud Norte (° WGS84 / EPSG:4326)", fontsize=9.5)
    ax.grid(True, linestyle="--", alpha=0.35, color="#7F8C8D")

    # Flecha de norte
    ax.annotate(
        "N",
        xy=(0.95, 0.94),
        xytext=(0.95, 0.85),
        xycoords="axes fraction",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        arrowprops=dict(arrowstyle="-|>", lw=1.8, color="#1B2631"),
    )

    ax.set_title(
        "Relación de Comercios Minoristas por Escuela de Educación Básica — Estado de Colima",
        fontsize=12.5,
        fontweight="bold",
        pad=14,
        color="#17202A",
    )
    fig.text(
        0.5,
        0.012,
        (
            f"Fuente: INEGI — DENUE (Colima, clases SCIAN 6111xx, 461110, 461160, 461170) y Marco Geoestadístico (dic. 2025). "
            f"Fecha de captura: {fecha_captura}.\n"
            "Nota cartográfica: Vista continental de Colima (el Archipiélago de Revillagigedo se omite gráficamente para preservar escala municipal). "
            "Licencia: Términos de Libre Uso INEGI."
        ),
        ha="center",
        fontsize=7.6,
        color="#4D5656",
    )

    plt.tight_layout(rect=[0, 0.045, 1, 0.98])
    plt.savefig(output_path, dpi=180)
    plt.close(fig)
    logger.info("Mapa coroplético guardado en: %s", output_path)


def _generar_mapa_puntos_colima(
    gdf_marco: gpd.GeoDataFrame,
    gdf_plata: gpd.GeoDataFrame,
    output_path: Path,
    fecha_captura: str,
) -> None:
    """Genera mapa de puntos (escuelas, dulcerías y paleterías/heladerías) en el municipio de Colima."""
    colima_poly = gdf_marco[gdf_marco["cve_mun"] == "002"].to_crs(CRS_ALMACENAMIENTO)
    pts_colima = gdf_plata[gdf_plata["cve_mun"] == "002"].to_crs(CRS_ALMACENAMIENTO)

    esc = pts_colima[pts_colima["categoria"] == "escuela_basica"]
    dul = pts_colima[pts_colima["categoria"] == "dulces"]
    hel = pts_colima[pts_colima["categoria"] == "helados_paletas"]

    # Zona urbana aproximada de la Ciudad de Colima (cuantiles 5%-95% de puntos o caja fija de la cabecera)
    urb_xmin, urb_xmax = -103.78, -103.68
    urb_ymin, urb_ymax = 19.20, 19.285

    fig, (ax_mun, ax_urb) = plt.subplots(1, 2, figsize=(13.5, 6.8), dpi=180)
    fig.patch.set_facecolor("#FAFAFA")

    # Panel 1: Municipio completo de Colima
    ax_mun.set_facecolor("#F4F6F7")
    colima_poly.plot(ax=ax_mun, facecolor="#FDFEFE", edgecolor="#2C3E50", linewidth=1.3)
    esc.plot(ax=ax_mun, color="#1F618D", markersize=22, marker="^", alpha=0.82, label=f"Escuelas básicas 6111xx (n={len(esc)})", zorder=3)
    dul.plot(ax=ax_mun, color="#C0392B", markersize=34, marker="o", alpha=0.90, edgecolor="white", linewidth=0.4, label=f"Dulcerías 461160 (n={len(dul)})", zorder=4)
    hel.plot(ax=ax_mun, color="#16A085", markersize=34, marker="s", alpha=0.90, edgecolor="white", linewidth=0.4, label=f"Paletas y helados 461170 (n={len(hel)})", zorder=4)

    # Recuadro de la zona urbana ampliada
    rect = mpatches.Rectangle(
        (urb_xmin, urb_ymin),
        urb_xmax - urb_xmin,
        urb_ymax - urb_ymin,
        linewidth=1.5,
        edgecolor="#D35400",
        facecolor="none",
        linestyle="--",
        zorder=5,
    )
    ax_mun.add_patch(rect)
    ax_mun.set_title("A) Municipio de Colima (límite oficial completo)", fontsize=10.5, fontweight="bold")
    ax_mun.set_xlabel("Longitud Oeste (° WGS84)", fontsize=8.8)
    ax_mun.set_ylabel("Latitud Norte (° WGS84)", fontsize=8.8)
    ax_mun.grid(True, linestyle=":", alpha=0.45)

    # Panel 2: Acercamiento a la zona urbana de Colima capital
    ax_urb.set_facecolor("#F4F6F7")
    colima_poly.plot(ax=ax_urb, facecolor="#FDFEFE", edgecolor="#2C3E50", linewidth=1.3)
    esc.plot(ax=ax_urb, color="#1F618D", markersize=38, marker="^", alpha=0.82, label=f"Escuelas básicas 6111xx (n={len(esc)})", zorder=3)
    dul.plot(ax=ax_urb, color="#C0392B", markersize=54, marker="o", alpha=0.92, edgecolor="white", linewidth=0.5, label=f"Dulcerías 461160 (n={len(dul)})", zorder=4)
    hel.plot(ax=ax_urb, color="#16A085", markersize=54, marker="s", alpha=0.92, edgecolor="white", linewidth=0.5, label=f"Paletas y helados 461170 (n={len(hel)})", zorder=4)

    ax_urb.set_xlim(urb_xmin, urb_xmax)
    ax_urb.set_ylim(urb_ymin, urb_ymax)
    ax_urb.set_title("B) Acercamiento — Zona Urbana de Colima Capital", fontsize=10.5, fontweight="bold")
    ax_urb.set_xlabel("Longitud Oeste (° WGS84)", fontsize=8.8)
    ax_urb.set_ylabel("Latitud Norte (° WGS84)", fontsize=8.8)
    ax_urb.grid(True, linestyle=":", alpha=0.45)
    ax_urb.legend(loc="lower right", frameon=True, facecolor="white", framealpha=0.92, fontsize=8.5)

    fig.suptitle(
        "Distribución Espacial de Escuelas Básicas, Dulcerías y Paleterías en el Municipio de Colima",
        fontsize=13,
        fontweight="bold",
        y=0.97,
        color="#17202A",
    )
    fig.text(
        0.5,
        0.012,
        (
            f"Fuente: INEGI — DENUE (Colima, clave municipal 06002) y Marco Geoestadístico (dic. 2025). "
            f"Fecha de captura: {fecha_captura}. Base cartográfica exclusiva del Marco Geoestadístico (sin teselas externas).\n"
            "Privacidad: Los puntos representan exclusivamente ubicación censal anonimizada sin nombres comerciales, razones sociales ni datos de contacto."
        ),
        ha="center",
        fontsize=7.6,
        color="#4D5656",
    )

    plt.tight_layout(rect=[0, 0.055, 1, 0.93])
    plt.savefig(output_path, dpi=180)
    plt.close(fig)
    logger.info("Mapa de puntos de Colima guardado en: %s", output_path)


def _generar_diccionario_geoespacial(
    diccionario_path: Path,
    df_oro_mun: pd.DataFrame,
    df_oro_ageb: pd.DataFrame,
    df_oro_loc: pd.DataFrame,
) -> None:
    """Genera docs/E2/diccionario_geoespacial.md con todas las tablas, CRS y minimización."""
    lineas_descartados = "\n".join(
        f"| `{col}` | {motivo} |"
        for col, motivo in CAMPOS_PERSONALES_Y_NO_ANALITICOS_DESCARTADOS.items()
    )

    contenido = f"""# Diccionario de Datos Geoespaciales (Entrega E2)

**Proyecto:** Observatorio de Datos — Comercio Minorista en Puestos Escolares (Colima, México)  
**Fuentes Oficiales:** INEGI DENUE (Colima, entidad `06`) e INEGI Marco Geoestadístico (dic. 2025, servicio GAIA `wscatgeo v2`)  
**Licencia:** Términos de Libre Uso de la Información del INEGI (`https://www.inegi.org.mx/inegi/terminos.html`)

---

## 1. Sistemas de Referencia de Coordenadas (CRS) y Justificación Técnica

| Uso | Código EPSG | Nombre Oficial | Justificación Técnica |
| :--- | :---: | :--- | :--- |
| **Almacenamiento e intercambio** | `{CRS_ALMACENAMIENTO}` | WGS 84 (Geográfico 2D, grados decimales) | Estándar internacional RFC 7946 para GeoJSON y GeoParquet; coincide con las coordenadas latitud/longitud del DENUE y es equivalente operacionalmente a `EPSG:6365` (ITRF2008 geográfico) reportado por el servicio GAIA del INEGI. |
| **Cálculo de áreas y distancias** | `{CRS_PROYECTADO_MX}` | Mexico ITRF2008 / Lambert Conformal Conic (CCL) | Proyección oficial del INEGI para el Marco Geoestadístico Nacional en metros. Evita la distorsión angular de calcular áreas o distancias en grados decimales y garantiza exactitud métrica ($\text{{km}}^2$) en el estado de Colima. |

> **Nota sobre superficie oficial vs. superficie continental:**  
> En el Marco Geoestadístico oficial del INEGI, los municipios de Manzanillo (`007`) y Tecomán (`009`) incluyen territorio insular del **Archipiélago de Revillagigedo** en el Océano Pacífico (hasta $-114.76^\\circ$ O). Por ello, la tabla Oro municipal reporta tanto `area_km2_oficial` (polígono completo del INEGI) como `area_km2_continental` (porción continental de Colima donde operan el 100% de las escuelas y comercios estudiados).

---

## 2. Tabla de Capa Plata: `datos/plata/denue_colima_plata.parquet` (y `.geojson`)

Contiene los establecimientos válidos de las 15 clases SCIAN de estudio tras la Puerta de Calidad Pandera y minimización estricta de datos personales. **CRS:** `EPSG:4326`.

| Columna | Tipo | Unidad / Dominio | Descripción |
| :--- | :---: | :--- | :--- |
| `id_establecimiento` | `STRING` | Identificador único | Clave numérica única del establecimiento en el DENUE (`id`). |
| `codigo_act` | `STRING` | Clave SCIAN (6 dígitos) | Código literal del catálogo oficial SCIAN (`6111xx`, `461110`, `461160`, `461170`). |
| `nombre_act` | `STRING` | Texto literal oficial | Nombre literal de la actividad económica según el catálogo SCIAN del INEGI. |
| `categoria` | `STRING` | Categórico (4 valores) | Agrupación analítica: `escuela_basica`, `abarrotes`, `dulces`, `helados_paletas`. |
| `estrato_personal` | `STRING` | Categórico censal | Estrato de personal ocupado reportado por DENUE (`0 a 5 personas`, etc.). |
| `cve_ent` | `STRING` | `"06"` | Clave oficial de la entidad federativa Colima. |
| `cve_mun` | `STRING` | `"001"` a `"010"` | Clave oficial del municipio según el Marco Geoestadístico. |
| `municipio` | `STRING` | Texto oficial | Nombre oficial del municipio de Colima. |
| `cve_loc` | `STRING` | Clave de 4 dígitos | Clave oficial de localidad geoestadística. |
| `localidad` | `STRING` | Texto oficial | Nombre oficial de la localidad. |
| `ageb` | `STRING` | Clave alfanumérica | Clave del Área Geoestadística Básica (AGEB) reportada en DENUE. |
| `latitud` | `FLOAT64` | Grados decimales (°N) | Latitud geográfica validada dentro de los polígonos oficiales de Colima. |
| `longitud` | `FLOAT64` | Grados decimales (°O) | Longitud geográfica validada dentro de los polígonos oficiales de Colima. |
| `fecha_alta` | `STRING` | `YYYY-MM` | Mes y año de incorporación del establecimiento en el directorio DENUE. |
| `fecha_captura_utc` | `STRING` | ISO 8601 UTC | Fecha y hora de descarga del archivo crudo en `datos/bronce/denue/`. |
| `archivo_origen` | `STRING` | Nombre de archivo | Archivo ZIP crudo de origen en Bronce. |
| `geometry` | `POINT` | `EPSG:4326` | Geometría puntual derivada de `(longitud, latitud)`. |

---

## 3. Tablas Agregadas de Capa Oro (`datos/oro/`) — Sin Puntos Individuales

Por principio de privacidad y diseño de capa analítica, **ninguna tabla de `datos/oro/` contiene puntos ni coordenadas individuales**. Todas las tablas incorporan adicionalmente columnas de linaje y trazabilidad generadas en la Fase 5 (`id_registro`, `fuente`, `archivos_origen_bronce`, `fecha_ingesta`, `n_registros_origen`, `fecha_min_origen`, `fecha_max_origen`, `hash_captura`, `run_id`).

### A. `datos/oro/densidad_comercial_escolar_municipios.parquet` ({len(df_oro_mun)} filas)

| Columna | Tipo | Unidad | Descripción y Fórmula |
| :--- | :---: | :--- | :--- |
| `cve_ent`, `cve_mun`, `municipio` | `STRING` | Catálogo INEGI | Identificadores oficiales del municipio en Colima (`06001`–`06010`). |
| `pob_total_censo2020` | `INT64` | Habitantes | Población total oficial del municipio (INEGI, Censo de Población y Vivienda 2020). |
| `area_km2_oficial` | `FLOAT64` | $\\text{{km}}^2$ | Superficie total del polígono oficial INEGI calculada en `EPSG:6372`. |
| `area_km2_continental` | `FLOAT64` | $\\text{{km}}^2$ | Superficie continental del municipio en `EPSG:6372` (excluye Archipiélago de Revillagigedo). |
| `n_escuelas_basicas` | `INT64` | Establecimientos | Conteo de escuelas de educación básica (`6111xx`). |
| `n_abarrotes` | `INT64` | Establecimientos | Conteo de tiendas de abarrotes, ultramarinos y misceláneas (`461110`). |
| `n_dulces` | `INT64` | Establecimientos | Conteo de comercio al por menor de dulces y materias primas para repostería (`461160`). |
| `n_helados_paletas` | `INT64` | Establecimientos | Conteo de comercio al por menor de paletas de hielo y helados (`461170`). |
| `n_comercios_total` | `INT64` | Establecimientos | Suma de `n_abarrotes + n_dulces + n_helados_paletas`. |
| `n_unidades_estudio` | `INT64` | Establecimientos | Total de unidades económicas del estudio en el municipio (`n_escuelas_basicas + n_comercios_total`). |
| `comercios_por_escuela` | `FLOAT64` | Ratio | `n_comercios_total / n_escuelas_basicas`. |
| `dulces_helados_por_escuela` | `FLOAT64` | Ratio | `(n_dulces + n_helados_paletas) / n_escuelas_basicas`. |
| `escuelas_por_km2_continental` | `FLOAT64` | $\\text{{escuelas}}/\\text{{km}}^2$ | `n_escuelas_basicas / area_km2_continental`. |
| `comercios_por_km2_continental` | `FLOAT64` | $\\text{{comercios}}/\\text{{km}}^2$ | `n_comercios_total / area_km2_continental`. |
| `escuelas_por_km2_oficial` | `FLOAT64` | $\\text{{escuelas}}/\\text{{km}}^2$ | `n_escuelas_basicas / area_km2_oficial`. |
| `comercios_por_km2_oficial` | `FLOAT64` | $\\text{{comercios}}/\\text{{km}}^2$ | `n_comercios_total / area_km2_oficial`. |
| `escuelas_por_10k_hab` | `FLOAT64` | Tasa / 10k hab. | `n_escuelas_basicas / (pob_total_censo2020 / 10,000)`. |
| `comercios_por_10k_hab` | `FLOAT64` | Tasa / 10k hab. | `n_comercios_total / (pob_total_censo2020 / 10,000)`. |

### B. `datos/oro/densidad_comercial_escolar_ageb.parquet` ({len(df_oro_ageb)} filas) y `densidad_comercial_escolar_localidad.parquet` ({len(df_oro_loc)} filas)

Desagregaciones territoriales por clave de AGEB (`cve_mun`, `cve_loc`, `ageb`) y por localidad (`cve_mun`, `cve_loc`, `localidad`) con los mismos conteos (`n_escuelas_basicas`, `n_abarrotes`, `n_dulces`, `n_helados_paletas`, `n_comercios_total`, `n_unidades_estudio`) y razón `comercios_por_escuela` (`NaN` cuando `n_escuelas_basicas == 0`, sin imputación artificial).

---

## 4. Registro de Minimización de Datos Personales (Campos Descartados en Capa Plata)

De los **42 campos originales** presentes en el archivo crudo del DENUE en Bronce, se descartaron **{len(CAMPOS_PERSONALES_Y_NO_ANALITICOS_DESCARTADOS)} campos** con información personal, de contacto o domicilio exacto antes de construir la Capa Plata:

| Campo Descartado | Justificación de Minimización |
| :--- | :--- |
{lineas_descartados}
"""
    diccionario_path.write_text(contenido, encoding="utf-8")
    logger.info("Diccionario geoespacial guardado en: %s", diccionario_path)


if __name__ == "__main__":
    gdf_p = gpd.read_parquet(BASE_DIR / "datos" / "plata" / "denue_colima_plata.parquet")
    gdf_m = gpd.read_parquet(BASE_DIR / "datos" / "plata" / "marco_geoestadistico_colima_plata.parquet")
    df_mun, df_ageb, df_loc = construir_oro_geoespacial(gdf_p, gdf_m)
    print("\nTABLA ORO MUNICIPAL:")
    print(
        df_mun[
            [
                "cve_mun",
                "municipio",
                "n_escuelas_basicas",
                "n_abarrotes",
                "n_dulces",
                "n_helados_paletas",
                "n_comercios_total",
                "comercios_por_escuela",
                "area_km2_continental",
                "comercios_por_km2_continental",
            ]
        ].to_string(index=False)
    )
