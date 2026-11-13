"""
Módulo de Transformación, Normalización y Reducción (Fase 4 - Entrega E1)
1. Normalización Min-Max y Z-score con persistencia de parámetros para reversibilidad.
2. Discretización de variaciones por cuantiles y por umbrales de dominio económico.
3. Jerarquías conceptuales temporales, temáticas y de ciclo escolar (marcada como supuesto de dominio).
4. Análisis de reducción: correlaciones, VIF entre factores y justificación de no muestreo.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Tuple
import numpy as np
import pandas as pd
from statsmodels.stats.outliers_influence import variance_inflation_factor

logger = logging.getLogger("pipeline.transformacion")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def transformar_y_normalizar(
    df_plata: pd.DataFrame,
    parametros_path: Path = Path("datos/plata/parametros_escalamiento.json"),
) -> Tuple[pd.DataFrame, Dict[str, Any], pd.DataFrame]:
    """
    Aplica normalización, discretización, jerarquías conceptuales y reducción.
    Guarda los parámetros de escalamiento en JSON para asegurar reversibilidad.
    """
    logger.info("Iniciando transformaciones, normalización y jerarquías conceptuales...")
    df = df_plata.copy().sort_values(["cve_serie", "fecha"]).reset_index(drop=True)

    parametros_escalamiento: Dict[str, Dict[str, float]] = {}

    # 1. Normalización Min-Max y Z-score por serie
    df["valor_minmax"] = np.nan
    df["valor_zscore"] = np.nan

    for cve, grp in df.groupby("cve_serie"):
        v = grp["valor"].values
        v_min = float(np.min(v))
        v_max = float(np.max(v))
        v_mean = float(np.mean(v))
        v_std = float(np.std(v, ddof=1)) if len(v) > 1 else 1.0

        rango = (v_max - v_min) if (v_max != v_min) else 1.0

        idx = grp.index
        df.loc[idx, "valor_minmax"] = (v - v_min) / rango
        df.loc[idx, "valor_zscore"] = (v - v_mean) / (v_std or 1.0)

        parametros_escalamiento[cve] = {
            "nombre": grp["nombre_literal"].iloc[0],
            "min": v_min,
            "max": v_max,
            "mean": v_mean,
            "std": v_std,
            "rango": rango,
        }

    # Guardar parámetros para garantizar reversibilidad matemática
    parametros_path.parent.mkdir(parents=True, exist_ok=True)
    with open(parametros_path, "w", encoding="utf-8") as fp:
        json.dump(parametros_escalamiento, fp, indent=2, ensure_ascii=False)
    logger.info("Parámetros de normalización guardados en: %s", parametros_path)

    # 2. Jerarquías conceptuales de tiempo
    df["año"] = df["fecha"].dt.year
    df["mes"] = df["fecha"].dt.month
    df["trimestre"] = "T" + df["fecha"].dt.quarter.astype(str)
    df["semestre"] = np.where(df["mes"] <= 6, "S1", "S2")

    nombres_meses = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }
    df["nombre_mes"] = df["mes"].map(nombres_meses)

    # 3. Jerarquía conceptual de Ciclo Escolar / Vacaciones
    # [SUPUESTO DEL DOMINIO: Basado en entrevista cualitativa de campo, no verificado con calendarios SEP históricos]
    def clasificar_ciclo_escolar(m: int) -> str:
        if m in (7, 8):
            return "Vacaciones_Verano"
        elif m == 12:
            return "Vacaciones_Invierno"
        elif m == 4:
            return "Vacaciones_Semana_Santa"
        else:
            return "Clases_Regulares"

    df["supuesto_ciclo_escolar"] = df["mes"].apply(clasificar_ciclo_escolar)

    # 4. Jerarquía conceptual de Series y Agregados Macroeconómicos
    mapa_agregado = {
        "910392": "General",
        "910394": "Subyacente",
        "910395": "Subyacente",
        "910397": "No_Subyacente",
        "SP74625": "Subyacente",
        "SF43718": "Divisas",
    }
    mapa_sector = {
        "910392": "Índice General",
        "910394": "Mercancías (Alimentos y Bebidas)",
        "910395": "Servicios",
        "910397": "Agropecuarios",
        "SP74625": "Canasta Subyacente",
        "SF43718": "Tipo de Cambio Dólar",
    }
    df["tipo_agregado"] = df["cve_serie"].map(mapa_agregado).fillna("Otros")
    df["clasificacion_sectorial"] = df["cve_serie"].map(mapa_sector).fillna("Otros")

    # 5. Discretización de variaciones porcentuales (para series con var_pct)
    if "var_pct" in df.columns:
        # Discretización por umbrales de dominio macroeconómico
        def clasificar_inflacion_dominio(v: float) -> str:
            if pd.isna(v):
                return "Sin_Dato"
            if v < 0.0:
                return "Deflación (<0%)"
            elif v <= 0.40:
                return "Moderada (0% a 0.4%)"
            elif v <= 1.00:
                return "Alta (0.4% a 1.0%)"
            else:
                return "Severa (>1.0%)"

        df["inflacion_nivel_dominio"] = df["var_pct"].apply(clasificar_inflacion_dominio)

        # Discretización por cuartiles (cuantiles 4-bins) sobre series mensuales
        df["inflacion_cuantil"] = "Sin_Dato"
        for cve, grp in df.groupby("cve_serie"):
            mask_valid = grp["var_pct"].notna()
            if mask_valid.sum() >= 4:
                etiquetas_q = ["Q1_Baja", "Q2_Media_Baja", "Q3_Media_Alta", "Q4_Alta"]
                try:
                    cuantiles = pd.qcut(grp.loc[mask_valid, "var_pct"], q=4, labels=etiquetas_q, duplicates="drop")
                    df.loc[grp.loc[mask_valid].index, "inflacion_cuantil"] = cuantiles.astype(str)
                except Exception:
                    pass

    # 6. Reducción y Selección de Variables: Correlación y VIF
    df_vif = calcular_vif_factores(df)

    return df, parametros_escalamiento, df_vif


def calcular_vif_factores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la correlación y el Factor de Inflación de la Varianza (VIF)
    entre los factores macroeconómicos mensuales en el periodo común (1982-2026).
    """
    logger.info("Calculando matriz de correlación y VIF para reducción de variables...")

    # Pivotear a formato ancho para variables mensuales comunes
    series_comunes = ["910392", "910394", "910395", "910397", "SP74625"]
    df_mensual = df[df["cve_serie"].isin(series_comunes)].copy()

    # Filtrar desde 1982 (inicio común de subíndices)
    df_mensual = df_mensual[df_mensual["fecha"] >= "1982-01-01"]

    pivot_var = df_mensual.pivot(index="fecha", columns="cve_serie", values="var_pct").dropna()

    pivot_var = pivot_var.rename(columns={
        "910392": "inpc_general",
        "910394": "mercancias",
        "910395": "servicios",
        "910397": "agropecuarios",
        "SP74625": "subyacente_banxico",
    })

    # Factores explicativos de inflación: mercancias, servicios, agropecuarios
    X = pivot_var[["mercancias", "servicios", "agropecuarios"]].copy()

    vif_data = []
    for i, col in enumerate(X.columns):
        vif_val = variance_inflation_factor(X.values, i)
        vif_data.append({
            "variable": col,
            "vif": float(vif_val),
            "diagnostico_multicolinealidad": "Baja (<5.0)" if vif_val < 5.0 else "Alta (>5.0)",
        })

    df_vif = pd.DataFrame(vif_data)
    return df_vif
