"""
Batería de Pruebas Unitarias para Linaje y Trazabilidad (Fase 5 - Entrega E2).
"""

import sys
from pathlib import Path
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline.linaje import (
    COLUMNAS_LINAJE_ORO,
    trazar,
    verificar_muestra_linaje,
)

TABLAS_ORO = [
    "matriz_mensual_macro",
    "comparativa_sectores",
    "densidad_comercial_escolar_municipios",
    "densidad_comercial_escolar_localidad",
    "densidad_comercial_escolar_ageb",
]


def test_manifiesto_bronce_completo():
    """Verifica que el manifiesto de Bronce registra archivos con hashes SHA-256 de 64 caracteres."""
    ruta = BASE_DIR / "datos" / "linaje" / "manifiesto_bronce.parquet"
    assert ruta.exists(), "Debe existir datos/linaje/manifiesto_bronce.parquet"
    df_man = pd.read_parquet(ruta)
    assert len(df_man) >= 16, "Se esperan al menos los 14 archivos E1 + 1 DENUE + 1 Marco Geoestadístico"
    assert df_man["sha256"].str.len().eq(64).all(), "Todos los hashes deben ser SHA-256 válidos (64 hex)"
    assert df_man["fuente"].notna().all()


@pytest.mark.parametrize("tabla", TABLAS_ORO)
def test_columnas_linaje_en_todas_las_tablas_oro(tabla):
    """Verifica que todas las tablas de Capa Oro incluyen las 9 columnas de linaje sin nulos."""
    ruta = BASE_DIR / "datos" / "oro" / f"{tabla}.parquet"
    assert ruta.exists(), f"No existe la tabla Oro esperada: {ruta}"
    df = pd.read_parquet(ruta)
    for col in COLUMNAS_LINAJE_ORO:
        assert col in df.columns, f"Falta columna de linaje '{col}' en {tabla}"
        assert df[col].notna().all(), f"Hay valores nulos en columna de linaje '{col}' de {tabla}"
    assert df["id_registro"].is_unique, f"id_registro debe ser único en {tabla}"


@pytest.mark.parametrize("tabla", TABLAS_ORO)
def test_oro_sin_puntos_ni_coordenadas_individuales(tabla):
    """Verifica la regla de privacidad: ninguna tabla en datos/oro/ expone puntos ni coordenadas individuales."""
    df = pd.read_parquet(BASE_DIR / "datos" / "oro" / f"{tabla}.parquet")
    prohibidas = {"latitud", "longitud", "geometry", "nom_estab", "raz_social", "telefono", "correoelec", "www"}
    assert len(set(df.columns) & prohibidas) == 0


def test_trazar_registros_reales_y_error_inexistente():
    """Verifica que trazar() devuelve la ruta completa hasta Bronce para E1 y E2."""
    for rid in [
        "oro:matriz_mensual_macro:2026-09-01",
        "oro:comparativa_sectores:910394:2026-09-01",
        "oro:densidad_comercial_escolar_municipios:002",
    ]:
        res = trazar(rid)
        assert res["id_registro"] == rid
        assert len(res["archivos_bronce"]) >= 1
        assert all(len(a["sha256"]) == 64 for a in res["archivos_bronce"])
        assert res["n_registros_origen"] >= 1

    with pytest.raises(KeyError):
        trazar("oro:tabla_inexistente:0000")


def test_verificacion_muestra_aleatoria_linaje_contra_bronce():
    """Verifica que una muestra aleatoria de las 5 tablas Oro coincide 100% con los crudos en Bronce."""
    zips_denue = list((BASE_DIR / "datos" / "bronce" / "denue").glob("denue_colima_raw_*.zip"))
    if not zips_denue:
        pytest.skip(
            "Auditoría profunda de linaje geoespacial contra Bronce omitida: el archivo "
            "'datos/bronce/denue/*.zip' no está presente en este clon local (ignorado en .gitignore "
            "por tamaño y protección de datos personales). Para auditar contra el paquete crudo oficial, "
            "ejecute 'python src/denue/extractor_denue.py' para descargarlo bajo demanda."
        )

    rep = verificar_muestra_linaje(n_por_tabla=4, seed=42)
    assert rep["total_verificados"] == 20
    assert rep["fallidos"] == 0, f"Fallos en verificación de linaje: {rep['detalle']}"
    assert rep["tasa_exito_pct"] == 100.0
