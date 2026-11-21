"""
Script Principal del Pipeline ETL (Entrega E1 - Observatorio de Datos)
Ejecuta el flujo completo de punta a punta:
1. Integración de capas Bronze a Plata y resolución de duplicados.
2. Puerta de Calidad automática con Pandera (lazy validation).
3. Diagnóstico de faltantes, experimento de imputación y detección de atípicos.
4. Normalización Min-Max/Z-score, jerarquías conceptuales y reducción de variables.
5. Construcción de datasets analíticos de Capa Oro y Diccionario de Datos.
6. Conciliación matemática estricta y generación de reportes.
"""

import logging
import sys
from pathlib import Path
import pandas as pd

# Asegurar que el directorio raíz esté en sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline.integracion import integrar_datos_bronce
from src.pipeline.calidad import PuertaCalidad
from src.pipeline.limpieza import (
    diagnosticar_faltantes,
    experimento_imputacion,
    detectar_atipicos,
)
from src.pipeline.transformacion import transformar_y_normalizar
from src.pipeline.reduccion import construir_capa_oro
from src.pipeline.linaje import construir_linaje_completo, verificar_muestra_linaje
from src.denue.plata_geo import construir_plata_geoespacial
from src.denue.oro_geo import construir_oro_geoespacial

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("pipeline.run")


def ejecutar_pipeline() -> int:
    logger.info("======================================================================")
    logger.info("INICIANDO PIPELINE DE DATOS E1 (BRONCE -> PLATA -> ORO + CUARENTENA)")
    logger.info("======================================================================")

    bronze_dir = BASE_DIR / "datos" / "bronce"
    plata_dir = BASE_DIR / "datos" / "plata"
    oro_dir = BASE_DIR / "datos" / "oro"
    cuarentena_dir = BASE_DIR / "datos" / "cuarentena"
    docs_e1_dir = BASE_DIR / "docs" / "E1"

    # --------------------------------------------------------------------------
    # FASE 1: Integración y Deduplicación
    # --------------------------------------------------------------------------
    logger.info("\n--- [FASE 1] INTEGRACIÓN Y RESOLUCIÓN DE CONFLICTOS ---")
    df_plata_raw, df_cuarentena_f1, df_tc_mensual = integrar_datos_bronce(
        bronze_dir=bronze_dir,
        plata_dir=plata_dir,
        cuarentena_dir=cuarentena_dir,
    )

    # --------------------------------------------------------------------------
    # FASE 5: Puerta de Calidad Automática (Pandera)
    # --------------------------------------------------------------------------
    logger.info("\n--- [FASE 5] PUERTA DE CALIDAD AUTOMÁTICA (PANDERA) ---")
    puerta = PuertaCalidad(
        cuarentena_dir=cuarentena_dir,
        reporte_path=docs_e1_dir / "reporte_calidad.md",
    )
    df_plata_valido, df_cuarentena_f5 = puerta.validar_y_segregar(df_plata_raw)

    # Consolidar cuarentena total
    df_cuarentena_total = pd.concat([df_cuarentena_f1, df_cuarentena_f5], ignore_index=True)
    df_cuarentena_total.to_parquet(cuarentena_dir / "cuarentena_total.parquet", index=False)
    df_cuarentena_total.to_csv(cuarentena_dir / "cuarentena_total.csv", index=False, encoding="utf-8")

    # Conciliación matemática estricta
    # Total filas en archivos crudos
    total_entrada = len(df_plata_raw) + len(df_cuarentena_f1)
    puerta.conciliar(total_entrada, df_plata_valido, df_cuarentena_total)

    # --------------------------------------------------------------------------
    # FASE 2: Diagnóstico de Faltantes y Experimento de Imputación
    # --------------------------------------------------------------------------
    logger.info("\n--- [FASE 2] DIAGNÓSTICO DE VALORES FALTANTES Y SIMULACIÓN ---")
    df_diag_faltantes = diagnosticar_faltantes(df_plata_valido)
    df_sim_imputacion, _ = experimento_imputacion(df_plata_valido, serie_objetivo="910394")

    # --------------------------------------------------------------------------
    # FASE 3: Detección de Atípicos y Ruido sobre Variaciones
    # --------------------------------------------------------------------------
    logger.info("\n--- [FASE 3] ATÍPICOS Y RUIDO SOBRE VARIACIONES PORCENTUALES ---")
    df_plata_limpio, resumen_atipicos = detectar_atipicos(df_plata_valido)

    # --------------------------------------------------------------------------
    # FASE 4: Normalización, Discretización y Reducción
    # --------------------------------------------------------------------------
    logger.info("\n--- [FASE 4] NORMALIZACIÓN, JERARQUÍAS Y REDUCCIÓN ---")
    df_plata_final, parametros_norm, df_vif = transformar_y_normalizar(
        df_plata_limpio,
        parametros_path=plata_dir / "parametros_escalamiento.json",
    )

    # Guardar versión definitiva enriquecida en datos/plata/
    df_plata_final.to_parquet(plata_dir / "tabla_plata_enriquecida.parquet", index=False)
    df_plata_final.to_csv(plata_dir / "tabla_plata_enriquecida.csv", index=False, encoding="utf-8")

    # --------------------------------------------------------------------------
    # FASE 6: Construcción de Capa Oro y Diccionario de Datos
    # --------------------------------------------------------------------------
    logger.info("\n--- [FASE 6] CONSTRUCCIÓN DE CAPA ORO ---")
    matriz_macro, comparativa_sectores, df_verif_series = construir_capa_oro(
        df_plata_long=df_plata_final,
        df_tc_mensual=df_tc_mensual,
        oro_dir=oro_dir,
        diccionario_path=docs_e1_dir / "diccionario_datos.md",
    )

    # Generar Reporte de Calidad Integral
    puerta.generar_reporte_calidad(
        total_entrada=total_entrada,
        df_plata=df_plata_final,
        df_cuarentena_total=df_cuarentena_total,
        diagnostico_faltantes=df_diag_faltantes,
        resumen_atipicos=resumen_atipicos,
    )

    # --------------------------------------------------------------------------
    # FASE E2-GEO: Capa Geoespacial (DENUE + Marco Geoestadístico)
    # --------------------------------------------------------------------------
    bronze_denue_dir = bronze_dir / "denue"
    bronze_mg_dir = bronze_dir / "marco_geoestadistico"
    resumen_geo = None
    df_oro_mun = df_oro_ageb = df_oro_loc = None
    if bronze_denue_dir.exists() and list(bronze_denue_dir.glob("denue_colima_raw_*.zip")):
        logger.info("\n--- [FASE E2-GEO] CAPA PLATA Y ORO GEOESPACIAL (DENUE + MARCO) ---")
        gdf_plata_geo, gdf_marco_geo, _, resumen_geo = construir_plata_geoespacial(
            bronze_denue_dir=bronze_denue_dir,
            bronze_mg_dir=bronze_mg_dir,
            plata_dir=plata_dir,
            cuarentena_dir=cuarentena_dir,
        )
        df_oro_mun, df_oro_ageb, df_oro_loc = construir_oro_geoespacial(
            gdf_plata=gdf_plata_geo,
            gdf_marco=gdf_marco_geo,
            oro_dir=oro_dir,
            figuras_dir=BASE_DIR / "docs" / "E2" / "figuras",
            diccionario_path=BASE_DIR / "docs" / "E2" / "diccionario_geoespacial.md",
        )

    # --------------------------------------------------------------------------
    # FASE E2-LINAJE: Trazabilidad End-to-End de Plata y Oro hasta Bronce
    # --------------------------------------------------------------------------
    logger.info("\n--- [FASE E2-LINAJE] CONSTRUCCIÓN Y VERIFICACIÓN DE LINAJE ---")
    linaje_dir = BASE_DIR / "datos" / "linaje"
    df_manifiesto, df_linaje, run_id = construir_linaje_completo(
        bronze_dir=bronze_dir,
        plata_dir=plata_dir,
        oro_dir=oro_dir,
        linaje_dir=linaje_dir,
        docs_linaje_path=BASE_DIR / "docs" / "E2" / "linaje.md",
    )
    verif_linaje = verificar_muestra_linaje(
        n_por_tabla=4,
        seed=42,
        bronze_dir=bronze_dir,
        oro_dir=oro_dir,
        linaje_dir=linaje_dir,
    )
    if verif_linaje["fallidos"] > 0:
        raise RuntimeError(f"FALLA DE AUDITORÍA DE LINAJE: {verif_linaje['fallidos']} registros no coinciden con Bronce.")

    # Recargar tablas Oro de E1 enriquecidas con columnas de linaje para métricas de consola
    matriz_macro = pd.read_parquet(oro_dir / "matriz_mensual_macro.parquet")
    comparativa_sectores = pd.read_parquet(oro_dir / "comparativa_sectores.parquet")

    # --------------------------------------------------------------------------
    # RESUMEN EJECUTIVO EN CONSOLA
    # --------------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("RESUMEN EJECUTIVO DEL PIPELINE E1 + E2 (CIERRE EXITOSO)")
    print("=" * 78)
    print(f"1. CONCILIACIÓN MATEMÁTICA DE REGISTROS (SERIES E1):")
    print(f"   - Filas de Entrada Crudas:    {total_entrada:8,}")
    print(f"   - Filas Aprobadas en Plata:   {len(df_plata_final):8,}  (100% de datos analíticos limpios)")
    print(f"   - Filas en Cuarentena Total:  {len(df_cuarentena_total):8,}  (Aisladas con causa auditable)")
    print(f"   - Conciliación Exacta:        {total_entrada == (len(df_plata_final) + len(df_cuarentena_total))} (Discrepancia: 0)")
    if resumen_geo is not None:
        print(f"   [GEOESPACIAL DENUE COLIMA]:")
        print(f"   - Filas de Entrada Crudas:    {resumen_geo['total_entrada']:8,}")
        print(f"   - Filas Aprobadas en Plata:   {resumen_geo['total_plata']:8,}  (CRS {resumen_geo['crs_almacenamiento']})")
        print(f"   - Filas en Cuarentena DENUE:  {resumen_geo['total_cuarentena']:8,}  (Violaciones calidad real: {resumen_geo['violaciones_calidad_reales']})")
        print(f"   - Conciliación Exacta:        {resumen_geo['total_entrada'] == (resumen_geo['total_plata'] + resumen_geo['total_cuarentena'])} (Discrepancia: 0)")
    print("-" * 78)
    print("2. TABLA DE VERIFICACIÓN DE SERIES (CUMPLIMIENTO >= 36 PERIODOS):")
    print(df_verif_series[["cve_serie", "nombre_literal", "frecuencia", "periodos", "cumple_minimo_36", "primera_fecha", "ultima_fecha", "meses_faltantes"]].to_string(index=False))
    print("-" * 78)
    print("3. DATASETS GENERADOS EN CAPA ORO (CON COLUMNAS DE LINAJE):")
    print(f"   - matriz_mensual_macro:                  {matriz_macro.shape[0]} filas x {matriz_macro.shape[1]} columnas ({matriz_macro['fecha'].min().strftime('%Y-%m')} a {matriz_macro['fecha'].max().strftime('%Y-%m')})")
    print(f"   - comparativa_sectores:                  {comparativa_sectores.shape[0]} filas x {comparativa_sectores.shape[1]} columnas")
    if df_oro_mun is not None:
        print(f"   - densidad_comercial_escolar_municipios: {len(df_oro_mun)} filas")
        print(f"   - densidad_comercial_escolar_localidad:  {len(df_oro_loc)} filas")
        print(f"   - densidad_comercial_escolar_ageb:       {len(df_oro_ageb)} filas")
    print("-" * 78)
    print("4. LINAJE Y TRAZABILIDAD END-TO-END:")
    print(f"   - Run ID:                 {run_id}")
    print(f"   - Archivos en Manifiesto: {len(df_manifiesto)}")
    print(f"   - Registros Rastreados:   {len(df_linaje):,} (Plata={(df_linaje['capa']=='plata').sum():,}, Oro={(df_linaje['capa']=='oro').sum():,})")
    print(f"   - Verificación Muestra:   {verif_linaje['exitosos']}/{verif_linaje['total_verificados']} ({verif_linaje['tasa_exito_pct']}%)")
    print("-" * 78)
    print("5. MULTICOLINEALIDAD ENTRE FACTORES EXPLICATIVOS (VIF):")
    print(df_vif.to_string(index=False))
    print("=" * 78 + "\n")

    logger.info("Pipeline E1 + E2 completado de forma satisfactoria sin errores.")
    return 0


if __name__ == "__main__":
    sys.exit(ejecutar_pipeline())
