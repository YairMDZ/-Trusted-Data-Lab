"""
Batería de Pruebas Unitarias para el Pipeline E1 (tests/test_pipeline.py)
Incluye casos sintéticos inválidos (creados SOLO dentro de las pruebas)
para verificar el funcionamiento estricto de la Puerta de Calidad Pandera,
la segregación hacia Cuarentena y la conciliación contable.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import pytest
from pandera.errors import SchemaErrors

# Asegurar path al proyecto
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.pipeline.calidad import PuertaCalidad, esquema_plata_long


@pytest.fixture
def registro_valido_base():
    """Fixture con una fila válida conforme al catálogo oficial."""
    return pd.DataFrame([{
        "fecha": pd.Timestamp("2026-09-01"),
        "cve_serie": "910394",
        "nombre_literal": "Mercancías",
        "unidad_literal": "Índice base 2018=100",
        "fuente": "INEGI",
        "valor": 146.075,
        "fecha_captura_utc": "2026-11-09T01:34:25Z",
        "archivo_origen": "inegi_inpc_raw_20261109_013425.json",
    }])


def test_esquema_pandera_conforme(registro_valido_base):
    """Verifica que un registro conforme aprueba el esquema Pandera sin excepciones."""
    df_validado = esquema_plata_long.validate(registro_valido_base, lazy=True)
    assert len(df_validado) == 1
    assert df_validado["valor"].iloc[0] == 146.075


def test_caso_sintetico_valor_negativo(registro_valido_base, tmp_path):
    """
    CASO SINTÉTICO: Crea dentro de la prueba un valor de índice negativo (-25.0).
    Verifica que la Puerta de Calidad lo detecta y lo envía a cuarentena.
    """
    df_invalido = registro_valido_base.copy()
    df_invalido.loc[0, "valor"] = -25.0  # Violación sintética

    puerta = PuertaCalidad(cuarentena_dir=tmp_path, reporte_path=tmp_path / "rep.md")
    df_validos, df_cuarentena = puerta.validar_y_segregar(df_invalido)

    assert len(df_validos) == 0, "El registro con valor negativo no debió pasar a Plata"
    assert len(df_cuarentena) == 1, "El registro con valor negativo debió enviarse a Cuarentena"
    assert df_cuarentena["regla_violada"].iloc[0] == "pandera_schema_check"
    assert "gt(0.0)" in df_cuarentena["motivo_texto"].iloc[0] or "positivo" in df_cuarentena["motivo_texto"].iloc[0]


def test_caso_sintetico_valor_fuera_de_rango(registro_valido_base, tmp_path):
    """
    CASO SINTÉTICO: Crea dentro de la prueba un valor absurdo (50,000.0) que excede el límite plausible.
    Verifica que es segregado a cuarentena.
    """
    df_invalido = registro_valido_base.copy()
    df_invalido.loc[0, "valor"] = 50000.0  # Violación sintética (>1000)

    puerta = PuertaCalidad(cuarentena_dir=tmp_path, reporte_path=tmp_path / "rep.md")
    df_validos, df_cuarentena = puerta.validar_y_segregar(df_invalido)

    assert len(df_validos) == 0
    assert len(df_cuarentena) == 1
    assert "lt(1000.0)" in df_cuarentena["motivo_texto"].iloc[0] or "umbral plausible" in df_cuarentena["motivo_texto"].iloc[0]


def test_caso_sintetico_fecha_duplicada(registro_valido_base, tmp_path):
    """
    CASO SINTÉTICO: Crea dentro de la prueba registros con fechas duplicadas para la misma serie.
    Verifica que Pandera detecta la violación de unicidad.
    """
    fila_dup = registro_valido_base.copy()
    df_dups = pd.concat([registro_valido_base, fila_dup], ignore_index=True)

    puerta = PuertaCalidad(cuarentena_dir=tmp_path, reporte_path=tmp_path / "rep.md")
    df_validos, df_cuarentena = puerta.validar_y_segregar(df_dups)

    # Al haber duplicado en la llave única, se aísla
    assert len(df_cuarentena) >= 1
    assert any("unique" in str(m) or "pandera" in str(r) for m, r in zip(df_cuarentena["motivo_texto"], df_cuarentena["regla_violada"]))


def test_caso_sintetico_clave_no_autorizada(registro_valido_base, tmp_path):
    """
    CASO SINTÉTICO: Crea dentro de la prueba una clave ficticia no autorizada ('SERIE_INVENTADA_999').
    Verifica que se rechaza hacia cuarentena.
    """
    df_invalido = registro_valido_base.copy()
    df_invalido.loc[0, "cve_serie"] = "SERIE_INVENTADA_999"

    puerta = PuertaCalidad(cuarentena_dir=tmp_path, reporte_path=tmp_path / "rep.md")
    df_validos, df_cuarentena = puerta.validar_y_segregar(df_invalido)

    assert len(df_validos) == 0
    assert len(df_cuarentena) == 1
    assert "isin" in df_cuarentena["motivo_texto"].iloc[0] or "no autorizada" in df_cuarentena["motivo_texto"].iloc[0]


def test_conciliacion_falla_si_hay_descuadre(registro_valido_base, tmp_path):
    """Verifica que puerta.conciliar lanza ValueError si hay registros desaparecidos en silencio."""
    puerta = PuertaCalidad(cuarentena_dir=tmp_path, reporte_path=tmp_path / "rep.md")

    total_entrada_esperada = 100
    df_plata = pd.DataFrame([{"a": 1}] * 60)
    df_cuarentena = pd.DataFrame([{"b": 2}] * 30)  # 60 + 30 = 90 != 100

    with pytest.raises(ValueError, match="FALLA CRÍTICA DE CONCILIACIÓN"):
        puerta.conciliar(total_entrada_esperada, df_plata, df_cuarentena)


def test_agregacion_mensual_tipo_cambio():
    """Verifica que la agregación de días hábiles a mensual calcule correctamente promedio y cierre."""
    df_diario_test = pd.DataFrame([
        {"fecha": pd.Timestamp("2026-05-04"), "valor": 18.0},
        {"fecha": pd.Timestamp("2026-05-15"), "valor": 19.0},
        {"fecha": pd.Timestamp("2026-05-29"), "valor": 20.0},  # Último hábil
    ])
    df_diario_test["mes"] = df_diario_test["fecha"].dt.to_period("M").dt.to_timestamp()

    df_agg = df_diario_test.groupby("mes").agg(
        promedio=("valor", "mean"),
        cierre=("valor", "last"),
        conteo=("valor", "count"),
    ).reset_index()

    assert df_agg["promedio"].iloc[0] == pytest.approx(19.0)
    assert df_agg["cierre"].iloc[0] == pytest.approx(20.0)
    assert df_agg["conteo"].iloc[0] == 3
