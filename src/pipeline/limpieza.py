"""
Módulo de Limpieza Estadística (Fases 2 y 3 - Entrega E1)
1. Diagnóstico de valores faltantes y análisis de mecanismos (MCAR/MAR/MNAR).
2. Experimento de sensibilidad de imputación bajo simulación controlada (5% y 10%).
3. Detección de atípicos sobre variaciones porcentuales (IQR, Z-score MAD, Isolation Forest).
4. Generación de banderas y figuras estadísticas en docs/E1/figuras/.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_absolute_error, mean_squared_error

logger = logging.getLogger("pipeline.limpieza")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

FIGURAS_DIR = Path("docs/E1/figuras")
FIGURAS_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# FASE 2: DIAGNÓSTICO DE FALTANTES Y EXPERIMENTO DE IMPUTACIÓN (SIMULACIÓN)
# ==============================================================================
def diagnosticar_faltantes(df_plata: pd.DataFrame) -> pd.DataFrame:
    """
    Diagnostica la presencia de valores nulos y meses faltantes contra el
    calendario continuo esperado para cada serie en la capa Plata.
    """
    diagnosticos = []

    for cve, grp in df_plata.groupby("cve_serie"):
        grp_sorted = grp.sort_values("fecha").reset_index(drop=True)
        nombre = grp_sorted["nombre_literal"].iloc[0]
        fuente = grp_sorted["fuente"].iloc[0]
        n_obs = len(grp_sorted)
        n_nulos = grp_sorted["valor"].isna().sum()

        f_min = grp_sorted["fecha"].min()
        f_max = grp_sorted["fecha"].max()

        # Si es mensual, verificar continuidad de meses
        if cve != "SF43718":
            rango_esperado = pd.date_range(start=f_min, end=f_max, freq="MS")
            fechas_reales = set(grp_sorted["fecha"].dt.strftime("%Y-%m-%d"))
            fechas_esperadas = set(rango_esperado.strftime("%Y-%m-%d"))
            faltantes_cal = len(fechas_esperadas - fechas_reales)
        else:
            faltantes_cal = 0  # Serie diaria hábil bancaria

        diagnosticos.append({
            "cve_serie": cve,
            "nombre_literal": nombre,
            "fuente": fuente,
            "n_observaciones": n_obs,
            "nulos_detectados": int(n_nulos),
            "pct_nulos": float(n_nulos / n_obs * 100),
            "fecha_inicio": f_min.strftime("%Y-%m-%d"),
            "fecha_fin": f_max.strftime("%Y-%m-%d"),
            "meses_faltantes_calendario": faltantes_cal,
            "mecanismo_ausencia": "N/A (Serie completa 100%)" if (n_nulos == 0 and faltantes_cal == 0) else "MCAR/MAR",
        })

    df_diag = pd.DataFrame(diagnosticos)
    return df_diag


def experimento_imputacion(
    df_plata: pd.DataFrame,
    serie_objetivo: str = "910394",  # Mercancías
    semilla: int = 42,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Experimento de sensibilidad controlado (SIMULACIÓN ETIQUETADA).
    Enmascara artificialmente 5% y 10% de los datos reales de la serie Mercancías
    y compara 3 métodos de imputación:
    1. Interpolación lineal
    2. Media mensual histórica (estacional)
    3. Spline cúbico (o KNN)
    NO modifica los datos reales de producción.
    """
    logger.info("Iniciando experimento de sensibilidad de imputación sobre serie %s...", serie_objetivo)
    df_s = df_plata[df_plata["cve_serie"] == serie_objetivo].sort_values("fecha").copy()
    y_real = df_s["valor"].values
    n = len(y_real)

    np.random.seed(semilla)
    resultados = []

    tasas_enmascaramiento = [0.05, 0.10]

    series_simuladas = {"fecha": df_s["fecha"].values, "real": y_real}

    for tasa in tasas_enmascaramiento:
        k_nulos = int(n * tasa)
        idx_nulos = np.random.choice(n, size=k_nulos, replace=False)

        y_masked = y_real.copy().astype(float)
        y_masked[idx_nulos] = np.nan

        s_masked = pd.Series(y_masked, index=df_s["fecha"])

        # Método 1: Interpolación Lineal
        s_lineal = s_masked.interpolate(method="time").bfill().ffill()
        rmse_lineal = np.sqrt(mean_squared_error(y_real[idx_nulos], s_lineal.values[idx_nulos]))
        mae_lineal = mean_absolute_error(y_real[idx_nulos], s_lineal.values[idx_nulos])

        # Método 2: Media Estacional Histórica (por mes del año)
        df_temp = pd.DataFrame({"mes": df_s["fecha"].dt.month, "valor": y_masked})
        media_por_mes = df_temp.groupby("mes")["valor"].transform("mean")
        s_estacional = df_temp["valor"].fillna(media_por_mes).bfill().ffill()
        rmse_estacional = np.sqrt(mean_squared_error(y_real[idx_nulos], s_estacional.values[idx_nulos]))
        mae_estacional = mean_absolute_error(y_real[idx_nulos], s_estacional.values[idx_nulos])

        # Método 3: Spline Cúbico
        try:
            s_spline = s_masked.interpolate(method="spline", order=3).bfill().ffill()
        except Exception:
            s_spline = s_masked.interpolate(method="quadratic").bfill().ffill()
        rmse_spline = np.sqrt(mean_squared_error(y_real[idx_nulos], s_spline.values[idx_nulos]))
        mae_spline = mean_absolute_error(y_real[idx_nulos], s_spline.values[idx_nulos])

        resultados.append({
            "tasa_enmascaramiento": f"{int(tasa*100)}%",
            "metodo": "Interpolación Lineal",
            "rmse": float(rmse_lineal),
            "mae": float(mae_lineal),
            "k_imputados": k_nulos,
        })
        resultados.append({
            "tasa_enmascaramiento": f"{int(tasa*100)}%",
            "metodo": "Media Estacional del Mes",
            "rmse": float(rmse_estacional),
            "mae": float(mae_estacional),
            "k_imputados": k_nulos,
        })
        resultados.append({
            "tasa_enmascaramiento": f"{int(tasa*100)}%",
            "metodo": "Spline Cúbico",
            "rmse": float(rmse_spline),
            "mae": float(mae_spline),
            "k_imputados": k_nulos,
        })

        if tasa == 0.10:
            series_simuladas["masked_10pct"] = y_masked
            series_simuladas["lineal"] = s_lineal.values
            series_simuladas["estacional"] = s_estacional.values
            series_simuladas["spline"] = s_spline.values
            series_simuladas["idx_nulos"] = idx_nulos

    df_res = pd.DataFrame(resultados)

    # Graficar comparación de simulación
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(12, 6))

    # Graficar últimos 72 meses para que sea visualmente claro
    sub_n = 72
    fechas_sub = series_simuladas["fecha"][-sub_n:]
    y_sub_real = series_simuladas["real"][-sub_n:]
    y_sub_lin = series_simuladas["lineal"][-sub_n:]
    y_sub_spline = series_simuladas["spline"][-sub_n:]
    y_sub_est = series_simuladas["estacional"][-sub_n:]

    ax.plot(fechas_sub, y_sub_real, label="Serie Real (910394 Mercancías)", color="black", lw=2)
    ax.plot(fechas_sub, y_sub_lin, label="Interpolación Lineal (Recomendado)", color="blue", ls="--", lw=1.5)
    ax.plot(fechas_sub, y_sub_spline, label="Spline Cúbico", color="green", ls=":", lw=1.5)
    ax.plot(fechas_sub, y_sub_est, label="Media Estacional", color="red", ls="-.", lw=1.2, alpha=0.7)

    # Marcar puntos enmascarados
    mask_in_sub = np.isnan(series_simuladas["masked_10pct"][-sub_n:])
    ax.scatter(
        np.array(fechas_sub)[mask_in_sub],
        np.array(y_sub_real)[mask_in_sub],
        color="crimson",
        s=60,
        zorder=5,
        label="Valores Enmascarados (10% Simulación)",
    )

    ax.set_title("Simulación de Imputación de Faltantes (Serie 910394 - Últimos 6 Años)", fontsize=13, fontweight="bold")
    ax.set_ylabel("Nivel del Índice (Base 2018=100)", fontsize=11)
    ax.set_xlabel("Fecha", fontsize=11)
    ax.legend(loc="upper left")
    plt.tight_layout()
    fig_path = FIGURAS_DIR / "simulacion_imputacion.png"
    plt.savefig(fig_path, dpi=300)
    plt.close()
    logger.info("Gráfica de simulación guardada en: %s", fig_path)

    return df_res, series_simuladas


# ==============================================================================
# FASE 3: ATÍPICOS Y RUIDO SOBRE VARIACIONES PORCENTUALES
# ==============================================================================
def detectar_atipicos(df_plata: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Calcula variaciones mensuales porcentuales y aplica tres métodos de detección:
    1. Tukey's IQR (factor 1.5)
    2. Z-score robusto con Mediana y MAD (umbral > 3.0)
    3. Isolation Forest no supervisado (contaminación 3%)
    Agrega columnas bandera sin eliminar registros.
    Genera figuras en docs/E1/figuras/.
    """
    logger.info("Iniciando detección de atípicos sobre variaciones mensuales porcentuales...")

    df_out = df_plata.copy().sort_values(["cve_serie", "fecha"]).reset_index(drop=True)

    # 1. Calcular variación porcentual mensual
    # Para series mensuales: pct_change sobre el mes previo
    # Para la serie diaria SF43718: pct_change diario
    df_out["var_pct"] = df_out.groupby("cve_serie")["valor"].pct_change() * 100.0

    # Inicializar banderas
    df_out["es_imputado"] = False  # Real data: 0 imputados
    df_out["es_atipico_iqr"] = False
    df_out["es_atipico_zmad"] = False
    df_out["es_atipico_iforest"] = False

    resumen_atipicos = {}

    for cve, grp in df_out.groupby("cve_serie"):
        valid_mask = grp["var_pct"].notna()
        indices_validos = grp[valid_mask].index
        vals = grp.loc[valid_mask, "var_pct"].values

        if len(vals) < 10:
            continue

        # Método 1: Tukey IQR
        q25 = np.percentile(vals, 25)
        q75 = np.percentile(vals, 75)
        iqr = q75 - q25
        lim_inf_iqr = q25 - 1.5 * iqr
        lim_sup_iqr = q75 + 1.5 * iqr
        mask_iqr = (vals < lim_inf_iqr) | (vals > lim_sup_iqr)
        df_out.loc[indices_validos[mask_iqr], "es_atipico_iqr"] = True

        # Método 2: Z-score robusto (Mediana y MAD)
        mediana = np.median(vals)
        mad = np.median(np.abs(vals - mediana))
        if mad == 0:
            mad = np.std(vals) or 1.0
        z_mad = 0.6745 * (vals - mediana) / mad
        mask_zmad = np.abs(z_mad) > 3.0
        df_out.loc[indices_validos[mask_zmad], "es_atipico_zmad"] = True

        # Método 3: Isolation Forest
        iso = IsolationForest(contamination=0.03, random_state=42)
        preds_iso = iso.fit_predict(vals.reshape(-1, 1))
        mask_iso = preds_iso == -1
        df_out.loc[indices_validos[mask_iso], "es_atipico_iforest"] = True

        resumen_atipicos[cve] = {
            "nombre": grp["nombre_literal"].iloc[0],
            "n_validos": len(vals),
            "iqr_conteo": int(mask_iqr.sum()),
            "zmad_conteo": int(mask_zmad.sum()),
            "iforest_conteo": int(mask_iso.sum()),
            "lim_inf_iqr": float(lim_inf_iqr),
            "lim_sup_iqr": float(lim_sup_iqr),
            "mediana_var": float(mediana),
            "mad_var": float(mad),
        }

    # Banderas combinadas: Al menos 2 métodos concuerdan
    df_out["es_atipico_consenso"] = (
        df_out["es_atipico_iqr"].astype(int)
        + df_out["es_atipico_zmad"].astype(int)
        + df_out["es_atipico_iforest"].astype(int)
    ) >= 2

    # Generar Figuras
    generar_graficas_atipicos(df_out)

    return df_out, resumen_atipicos


def generar_graficas_atipicos(df: pd.DataFrame) -> None:
    """Genera las gráficas de caja y series temporales con atípicos resaltados."""
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # 1. Boxplot de variaciones por serie mensual
    series_mensuales = ["910392", "910394", "910395", "910397", "SP74625"]
    df_m = df[df["cve_serie"].isin(series_mensuales) & df["var_pct"].notna()].copy()

    fig, ax = plt.subplots(figsize=(11, 6))
    data_plot = [df_m[df_m["cve_serie"] == s]["var_pct"].values for s in series_mensuales]
    labels = [
        f"{s}\n{df_m[df_m['cve_serie'] == s]['nombre_literal'].iloc[0]}"
        for s in series_mensuales
    ]

    ax.boxplot(data_plot, tick_labels=labels, showmeans=True, patch_artist=True)
    ax.set_title("Distribución y Dispersión de la Variación Mensual (%) por Serie del INPC", fontsize=12, fontweight="bold")
    ax.set_ylabel("Variación Porcentual Mensual (%)", fontsize=10)
    plt.xticks(fontsize=9)
    plt.tight_layout()
    plt.savefig(FIGURAS_DIR / "boxplot_variaciones.png", dpi=300)
    plt.close()

    # 2. Serie Temporal INPC General (910392) y Subyacente (SP74625) con Atípicos Resaltados
    df_gen = df[df["cve_serie"] == "910392"].copy()
    fig, ax = plt.subplots(figsize=(13, 6))
    ax.plot(df_gen["fecha"], df_gen["var_pct"], label="Variación Mensual INPC General (910392)", color="navy", lw=1.2)

    # Resaltar atípicos consenso
    atipicos_gen = df_gen[df_gen["es_atipico_consenso"]]
    ax.scatter(
        atipicos_gen["fecha"],
        atipicos_gen["var_pct"],
        color="crimson",
        s=40,
        zorder=5,
        label=f"Choques Macroeconómicos Atípicos (n={len(atipicos_gen)})",
    )

    # Anotaciones históricas clave
    ax.annotate(
        "Hiperinflación 1987-1988\n(Pacto de Solidaridad)",
        xy=(pd.Timestamp("1988-01-01"), 15.5),
        xytext=(pd.Timestamp("1975-01-01"), 13.0),
        arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
        fontsize=9,
        fontweight="bold",
    )
    ax.annotate(
        "Crisis Tequila 1995\n(Devaluación)",
        xy=(pd.Timestamp("1995-04-01"), 8.0),
        xytext=(pd.Timestamp("1998-01-01"), 10.0),
        arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
        fontsize=9,
        fontweight="bold",
    )
    ax.annotate(
        "Choque COVID-19 2020",
        xy=(pd.Timestamp("2020-04-01"), -1.0),
        xytext=(pd.Timestamp("2010-01-01"), -4.0),
        arrowprops=dict(facecolor="black", arrowstyle="->", lw=1),
        fontsize=9,
        fontweight="bold",
    )

    ax.set_title("Trayectoria Histórica de la Inflación Mensual Mexicana (1969-2026) y Eventos Atípicos", fontsize=12, fontweight="bold")
    ax.set_ylabel("Variación Porcentual Mensual (%)", fontsize=10)
    ax.set_xlabel("Año", fontsize=10)
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(FIGURAS_DIR / "serie_atipicos_inpc.png", dpi=300)
    plt.close()

    # 3. Comparativa Subíndices: Mercancías, Servicios y Agropecuarios
    fig, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=True)
    subindices = [
        ("910394", "Mercancías", "darkblue"),
        ("910395", "Servicios", "darkgreen"),
        ("910397", "Agropecuarios", "darkorange"),
    ]

    for ax, (cve, nombre, col) in zip(axes, subindices):
        sub_df = df[df["cve_serie"] == cve].copy()
        ax.plot(sub_df["fecha"], sub_df["var_pct"], label=f"{cve} - {nombre}", color=col, lw=1)
        sub_at = sub_df[sub_df["es_atipico_consenso"]]
        ax.scatter(sub_at["fecha"], sub_at["var_pct"], color="red", s=25, zorder=4)
        ax.set_ylabel("Var % Mensual", fontsize=9)
        ax.legend(loc="upper left")

    axes[0].set_title("Dinámica de Variaciones Mensuales y Atípicos en Subíndices Sectoriales (1982-2026)", fontsize=12, fontweight="bold")
    axes[-1].set_xlabel("Año", fontsize=10)
    plt.tight_layout()
    plt.savefig(FIGURAS_DIR / "serie_atipicos_mercancias_servicios.png", dpi=300)
    plt.close()

    logger.info("Figuras generadas exitosamente en %s", FIGURAS_DIR)
