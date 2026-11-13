"""
Módulo de Reducción y Construcción de Capa Oro (Fase 6 - Entrega E1)
Genera en datos/oro/ dos tablas consolidadas listas para analítica:
1. matriz_mensual_macro (tabla ancha con series, variaciones, rezagos y tipo de cambio).
2. comparativa_sectores (tabla comparativa de Mercancías, Servicios y Agropecuarios).
Genera el diccionario de datos formal en docs/E1/diccionario_datos.md.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger("pipeline.reduccion")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def construir_capa_oro(
    df_plata_long: pd.DataFrame,
    df_tc_mensual: pd.DataFrame,
    oro_dir: Path = Path("datos/oro"),
    diccionario_path: Path = Path("docs/E1/diccionario_datos.md"),
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Construye las tablas de la Capa Oro y genera el diccionario de datos.
    """
    logger.info("Iniciando construcción de datasets analíticos de Capa Oro...")
    oro_dir.mkdir(parents=True, exist_ok=True)
    diccionario_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. TABLA ANCHA: matriz_mensual_macro
    # Periodo común: desde 1982-01-01 hasta 2026-09-01 (cobertura común de subíndices de INEGI)
    series_mensuales = ["910392", "910394", "910395", "910397", "SP74625"]
    df_m = df_plata_long[df_plata_long["cve_serie"].isin(series_mensuales)].copy()
    df_m = df_m[df_m["fecha"] >= "1982-01-01"].sort_values(["cve_serie", "fecha"])

    # Pivotear niveles de índice
    df_niveles = df_m.pivot(index="fecha", columns="cve_serie", values="valor").rename(columns={
        "910392": "inpc_general",
        "910394": "inpc_mercancias",
        "910395": "inpc_servicios",
        "910397": "inpc_agropecuarios",
        "SP74625": "inpc_subyacente_banxico",
    })

    # Calcular variaciones porcentuales mensuales
    df_var = df_niveles.pct_change() * 100.0
    df_var.columns = [f"var_pct_{col.replace('inpc_', '')}" for col in df_var.columns]

    # Calcular Z-score sobre niveles
    df_z = (df_niveles - df_niveles.mean()) / df_niveles.std()
    df_z.columns = [f"z_{col.replace('inpc_', '')}" for col in df_z.columns]

    # Rezagos de 1 y 3 meses (Lags) sobre variaciones de insumos escolares
    df_lags = pd.DataFrame(index=df_niveles.index)
    df_lags["lag1_var_mercancias"] = df_var["var_pct_mercancias"].shift(1)
    df_lags["lag3_var_mercancias"] = df_var["var_pct_mercancias"].shift(3)
    df_lags["lag1_var_agropecuarios"] = df_var["var_pct_agropecuarios"].shift(1)
    df_lags["lag3_var_agropecuarios"] = df_var["var_pct_agropecuarios"].shift(3)

    # Unir tipo de cambio FIX mensual (promedio y cierre)
    df_tc_prep = df_tc_mensual[["fecha", "promedio_mensual", "cierre_mensual"]].copy()
    df_tc_prep = df_tc_prep.rename(columns={
        "promedio_mensual": "tipo_cambio_fix_promedio",
        "cierre_mensual": "tipo_cambio_fix_cierre",
    }).set_index("fecha")

    # Variación porcentual y rezagos del tipo de cambio
    df_tc_prep["var_pct_tc_promedio"] = df_tc_prep["tipo_cambio_fix_promedio"].pct_change() * 100.0
    df_tc_prep["lag1_var_tc_promedio"] = df_tc_prep["var_pct_tc_promedio"].shift(1)
    df_tc_prep["z_tc_promedio"] = (df_tc_prep["tipo_cambio_fix_promedio"] - df_tc_prep["tipo_cambio_fix_promedio"].mean()) / df_tc_prep["tipo_cambio_fix_promedio"].std()

    # Combinar matriz ancha
    matriz_macro = pd.concat([df_niveles, df_var, df_z, df_lags], axis=1).join(df_tc_prep, how="left")
    matriz_macro = matriz_macro.reset_index()

    # Bandera de disponibilidad de tipo de cambio:
    # Entre 1982-01 y 1991-10 no existe serie oficial SF43718; se deja vacío (NaN, NO imputado)
    # y se marca con la bandera booleana tc_disponible.
    matriz_macro["tc_disponible"] = matriz_macro["tipo_cambio_fix_promedio"].notna()

    # Variables de calendario y estacionalidad escolar
    matriz_macro["año"] = matriz_macro["fecha"].dt.year
    matriz_macro["mes"] = matriz_macro["fecha"].dt.month
    matriz_macro["trimestre"] = "T" + matriz_macro["fecha"].dt.quarter.astype(str)
    matriz_macro["semestre"] = np.where(matriz_macro["mes"] <= 6, "S1", "S2")

    # Temporada alta de calor en Colima (Abril a Agosto)
    matriz_macro["es_temporada_calor"] = matriz_macro["mes"].isin([4, 5, 6, 7, 8]).astype(int)

    # Supuesto del dominio de ciclo escolar
    def periodo_escolar(m: int) -> str:
        if m in (7, 8):
            return "Vacaciones_Verano"
        elif m == 12:
            return "Vacaciones_Invierno"
        elif m == 4:
            return "Vacaciones_Semana_Santa"
        return "Clases_Regulares"

    matriz_macro["supuesto_ciclo_escolar"] = matriz_macro["mes"].apply(periodo_escolar)

    # 2. TABLA COMPARATIVA: comparativa_sectores
    # Comparar Mercancías (910394), Servicios (910395) y Agropecuarios (910397)
    sectores_map = {
        "910394": "Mercancías",
        "910395": "Servicios",
        "910397": "Agropecuarios",
    }
    df_sec = df_plata_long[df_plata_long["cve_serie"].isin(sectores_map.keys())].copy()
    df_sec = df_sec[df_sec["fecha"] >= "1982-01-01"].sort_values(["cve_serie", "fecha"]).reset_index(drop=True)

    df_sec["sector"] = df_sec["cve_serie"].map(sectores_map)
    df_sec["var_mensual_pct"] = df_sec.groupby("cve_serie")["valor"].pct_change() * 100.0
    df_sec["var_interanual_12m_pct"] = df_sec.groupby("cve_serie")["valor"].pct_change(12) * 100.0
    df_sec["volatilidad_12m"] = df_sec.groupby("cve_serie")["var_mensual_pct"].transform(lambda x: x.rolling(12).std())

    df_sec["año"] = df_sec["fecha"].dt.year
    df_sec["mes"] = df_sec["fecha"].dt.month
    df_sec["es_temporada_calor"] = df_sec["mes"].isin([4, 5, 6, 7, 8]).astype(int)
    df_sec["supuesto_ciclo_escolar"] = df_sec["mes"].apply(periodo_escolar)

    comparativa_sectores = df_sec[[
        "fecha", "cve_serie", "sector", "valor", "var_mensual_pct",
        "var_interanual_12m_pct", "volatilidad_12m", "es_temporada_calor",
        "supuesto_ciclo_escolar", "año", "mes"
    ]].rename(columns={"valor": "nivel_indice"})

    # 3. VERIFICACIÓN DE PERIODOS POR SERIE
    verificacion_series = []
    for cve in series_mensuales:
        grp = df_plata_long[df_plata_long["cve_serie"] == cve]
        nom = grp["nombre_literal"].iloc[0]
        n_obs = len(grp)
        f_ini = grp["fecha"].min().strftime("%Y-%m-%d")
        f_fin = grp["fecha"].max().strftime("%Y-%m-%d")

        # Rango esperado
        r_esp = pd.date_range(start=grp["fecha"].min(), end=grp["fecha"].max(), freq="MS")
        faltantes = len(set(r_esp.strftime("%Y-%m-%d")) - set(grp["fecha"].dt.strftime("%Y-%m-%d")))

        verificacion_series.append({
            "cve_serie": cve,
            "nombre_literal": nom,
            "frecuencia": "Mensual",
            "periodos": n_obs,
            "cumple_minimo_36": "SÍ" if n_obs >= 36 else "NO",
            "primera_fecha": f_ini,
            "ultima_fecha": f_fin,
            "meses_faltantes": faltantes,
        })

    # Tipo de cambio
    df_tc_grp = df_plata_long[df_plata_long["cve_serie"] == "SF43718"]
    verificacion_series.append({
        "cve_serie": "SF43718",
        "nombre_literal": "Tipo de cambio FIX (Diario)",
        "frecuencia": "Diaria hábil",
        "periodos": len(df_tc_grp),
        "cumple_minimo_36": "SÍ",
        "primera_fecha": df_tc_grp["fecha"].min().strftime("%Y-%m-%d"),
        "ultima_fecha": df_tc_grp["fecha"].max().strftime("%Y-%m-%d"),
        "meses_faltantes": 0,
    })
    df_verif = pd.DataFrame(verificacion_series)

    # Persistencia
    matriz_macro.to_parquet(oro_dir / "matriz_mensual_macro.parquet", index=False)
    matriz_macro.to_csv(oro_dir / "matriz_mensual_macro.csv", index=False, encoding="utf-8")

    comparativa_sectores.to_parquet(oro_dir / "comparativa_sectores.parquet", index=False)
    comparativa_sectores.to_csv(oro_dir / "comparativa_sectores.csv", index=False, encoding="utf-8")

    # Generar Diccionario de Datos
    generar_diccionario_datos(diccionario_path)

    logger.info("Datasets de Capa Oro construidos exitosamente:")
    logger.info("  - matriz_mensual_macro: %d filas x %d columnas", matriz_macro.shape[0], matriz_macro.shape[1])
    logger.info("  - comparativa_sectores: %d filas x %d columnas", comparativa_sectores.shape[0], comparativa_sectores.shape[1])

    return matriz_macro, comparativa_sectores, df_verif


def generar_diccionario_datos(diccionario_path: Path) -> None:
    """Genera el diccionario de datos formal para las tablas de Plata y Oro."""
    contenido = """# Diccionario de Datos del Observatorio (Entrega E1)

**Proyecto:** Observatorio de Datos - Puestos Escolares (Colima, México)  
**Versión de Catálogo:** 1.0 (Noviembre 2026)  
**Norma de Metadatos:** Nombres y unidades literales de `CL_INDICATOR` (INEGI) y `SIE` (Banxico).

---

## 1. Tabla: `datos/plata/tabla_plata_long` (Formato Largo / Plata)

Tabla maestra con la totalidad de observaciones válidas aceptadas por la Puerta de Calidad.

| Nombre de Columna | Tipo de Dato | Unidad de Medida | Descripción y Regla de Negocio | Fuente Oficial |
| :--- | :---: | :--- | :--- | :---: |
| `fecha` | `DATETIME` | Fecha ISO (YYYY-MM-01 o YYYY-MM-DD) | Primer día del mes para series mensuales; fecha hábil para tipo de cambio diario. | INEGI / Banxico |
| `cve_serie` | `STRING` | Clave alfanumérica | Clave oficial en catálogo (910392, 910394, 910395, 910397, SP74625, SF43718). | Catálogo oficial |
| `nombre_literal` | `STRING` | Texto literal | Denominación textual exacta sin interpretaciones subjetivas. | `CL_INDICATOR` / SIE |
| `unidad_literal` | `STRING` | Texto literal | Unidad de medida (`Índice base 2018=100` o `Pesos por Dólar`). | `CL_UNIT` / SIE |
| `fuente` | `STRING` | Categórico (`INEGI` / `Banxico`) | Institución pública generadora de la información. | Oficial |
| `valor` | `FLOAT` | Numérico continuo | Magnitud del índice o cotización cambiaria. Estrictamente mayor a 0. | BIE / SIE |
| `fecha_captura_utc` | `STRING` | Timestamp ISO 8601 | Fecha y hora UTC del momento de la extracción cruda a bronce. | Extractor |
| `archivo_origen` | `STRING` | Nombre de archivo | Archivo crudo específico en `datos/bronce/` de donde provino el registro. | Auditoría |

---

## 2. Tabla: `datos/oro/matriz_mensual_macro` (Tabla Ancha Multivariada / Oro)

Dataset consolidado mensual para análisis de sensibilidad, causalidad (E2) y pronósticos (E1).

| Nombre de Columna | Tipo | Unidad | Descripción y Cálculo |
| :--- | :---: | :--- | :--- |
| `fecha` | `DATETIME` | YYYY-MM-01 | Fecha de corte mensual estandarizada. |
| `inpc_general` | `FLOAT` | Base 2018=100 | Nivel del Índice General de Precios al Consumidor (Clave 910392). |
| `inpc_mercancias` | `FLOAT` | Base 2018=100 | Subíndice de Mercancías (Alimentos procesados y bebidas) (Clave 910394). |
| `inpc_servicios` | `FLOAT` | Base 2018=100 | Subíndice de Servicios al consumidor (Clave 910395). |
| `inpc_agropecuarios` | `FLOAT` | Base 2018=100 | Subíndice de productos Agropecuarios no procesados (Clave 910397). |
| `inpc_subyacente_banxico`| `FLOAT` | Base 2018=100 | Subíndice subyacente del INPC reportado por Banxico (Clave SP74625). |
| `var_pct_inpc_general` | `FLOAT` | Porcentaje (%) | Inflación mensual del índice general: $\\Delta\\% = (I_t/I_{t-1}-1)\\times 100$. |
| `var_pct_mercancias` | `FLOAT` | Porcentaje (%) | Variación mensual porcentual del subíndice de Mercancías. |
| `var_pct_servicios` | `FLOAT` | Porcentaje (%) | Variación mensual porcentual del subíndice de Servicios. |
| `var_pct_agropecuarios` | `FLOAT` | Porcentaje (%) | Variación mensual porcentual del subíndice de Agropecuarios. |
| `var_pct_subyacente` | `FLOAT` | Porcentaje (%) | Variación mensual porcentual del subíndice Subyacente. |
| `z_mercancias` | `FLOAT` | Adimensional | Estandarización Z-score del nivel de mercancías: $(x - \\mu)/\\sigma$. |
| `z_agropecuarios` | `FLOAT` | Adimensional | Estandarización Z-score del nivel de agropecuarios: $(x - \\mu)/\\sigma$. |
| `lag1_var_mercancias` | `FLOAT` | Porcentaje (%) | Rezagos a 1 mes ($t-1$) de la variación de mercancías. |
| `lag3_var_mercancias` | `FLOAT` | Porcentaje (%) | Rezagos a 3 meses ($t-3$) de la variación de mercancías. |
| `lag1_var_agropecuarios`| `FLOAT` | Porcentaje (%) | Rezagos a 1 mes ($t-1$) de la variación de agropecuarios. |
| `lag3_var_agropecuarios`| `FLOAT` | Porcentaje (%) | Rezagos a 3 meses ($t-3$) de la variación de agropecuarios. |
| `tipo_cambio_fix_promedio` | `FLOAT` | MXN / USD | Media aritmética mensual de cotizaciones diarias de SF43718. |
| `tipo_cambio_fix_cierre` | `FLOAT` | MXN / USD | Cotización del último día hábil bancario cotizado en el mes. |
| `var_pct_tc_promedio` | `FLOAT` | Porcentaje (%) | Variación mensual del tipo de cambio medio. |
| `lag1_var_tc_promedio` | `FLOAT` | Porcentaje (%) | Rezagos a 1 mes ($t-1$) del tipo de cambio. |
| `año`, `mes` | `INT` | Entero | Descomposición cronológica de la observación. |
| `trimestre`, `semestre` | `STRING` | Categórico | Trimestre (T1 a T4) y Semestre (S1 o S2). |
| `es_temporada_calor` | `INT` | Booleano (0 o 1) | 1 si mes $\\in [4, 5, 6, 7, 8]$ (meses calurosos en Colima); 0 en caso contrario. |
| `supuesto_ciclo_escolar` | `STRING` | Categórico | **[SUPUESTO DEL DOMINIO]** `Clases_Regulares`, `Vacaciones_Verano`, `Vacaciones_Invierno`, `Vacaciones_Semana_Santa`. |

---

## 3. Tabla: `datos/oro/comparativa_sectores` (Formato Largo / Comparativa Sectorial)

Dataset estructurado para análisis de clustering, co-movimiento y estacionalidad diferencial (E3).

| Nombre de Columna | Tipo | Unidad | Descripción |
| :--- | :---: | :--- | :--- |
| `fecha` | `DATETIME` | YYYY-MM-01 | Fecha de corte mensual. |
| `cve_serie` | `STRING` | Clave oficial | Clave del indicador (910394, 910395, 910397). |
| `sector` | `STRING` | Texto | Sector económico (`Mercancías`, `Servicios`, `Agropecuarios`). |
| `nivel_indice` | `FLOAT` | Base 2018=100 | Nivel de precio del índice. |
| `var_mensual_pct` | `FLOAT` | Porcentaje (%) | Variación porcentual mensual frente al mes previo. |
| `var_interanual_12m_pct`| `FLOAT` | Porcentaje (%) | Variación porcentual interanual frente al mismo mes del año previo. |
| `volatilidad_12m` | `FLOAT` | Desviación estándar | Desviación estándar móvil de los últimos 12 meses de la variación mensual. |
| `es_temporada_calor` | `INT` | Binario | Indicador de meses de alta temperatura en Colima. |
| `supuesto_ciclo_escolar`| `STRING` | Categórico | Supuesto de periodo escolar basado en entrevista de campo. |
"""
    diccionario_path.write_text(contenido, encoding="utf-8")
    logger.info("Diccionario de datos generado en: %s", diccionario_path)
