"""
Batería de Pruebas Unitarias para el Pipeline Geoespacial (Fase 3 - Entrega E2).
Incluye casos sintéticos inválidos creados EXCLUSIVAMENTE dentro de las pruebas:
- Coordenada fuera de rango (bounding box de Colima).
- Coordenada fuera del polígono real de Colima (océano / otro estado).
- Código SCIAN inexistente en el catálogo oficial.
- Identificador de establecimiento duplicado.
- Conciliación estricta ante descuadre.
- Minimización de datos personales y enmascarado de tokens.
"""

import sys
from pathlib import Path
import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Polygon

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.denue.extractor_denue import enmascarar_token
from src.denue.plata_geo import (
    CAMPOS_PERSONALES_Y_NO_ANALITICOS_DESCARTADOS,
    CRS_ALMACENAMIENTO,
    PuertaCalidadGeo,
    esquema_denue_plata,
)


@pytest.fixture
def registro_geo_valido():
    """Fila sintética válida ubicada en Colima capital."""
    return pd.DataFrame([{
        "id_establecimiento": "9000001",
        "codigo_act": "461160",
        "nombre_act": "Comercio al por menor de dulces y materias primas para repostería",
        "categoria": "dulces",
        "estrato_personal": "0 a 5 personas",
        "cve_ent": "06",
        "cve_mun": "002",
        "municipio": "Colima",
        "cve_loc": "0001",
        "localidad": "Colima",
        "ageb": "0412",
        "latitud": 19.2433,
        "longitud": -103.7247,
        "fecha_alta": "2020-11",
        "fecha_captura_utc": "2026-11-20T20:00:00+00:00",
        "archivo_origen": "denue_colima_raw_test.zip",
    }])


@pytest.fixture
def poligono_colima_sintetico():
    """Polígono sintético sencillo alrededor de Colima capital para pruebas unitarias."""
    poly = Polygon([
        (-103.85, 19.10),
        (-103.55, 19.10),
        (-103.55, 19.35),
        (-103.85, 19.35),
        (-103.85, 19.10),
    ])
    return gpd.GeoDataFrame(
        [{"cve_ent": "06", "cve_mun": "002", "nomgeo": "Colima", "geometry": poly}],
        crs=CRS_ALMACENAMIENTO,
    )


def test_esquema_geo_pandera_conforme(registro_geo_valido, poligono_colima_sintetico, tmp_path):
    """Un registro geoespacial válido pasa Pandera y la contención espacial sin rechazos."""
    puerta = PuertaCalidadGeo(cuarentena_dir=tmp_path)
    gdf_val, df_cuar = puerta.validar_y_segregar(registro_geo_valido, gdf_marco=poligono_colima_sintetico)

    assert len(gdf_val) == 1
    assert len(df_cuar) == 0
    assert str(gdf_val.crs) == CRS_ALMACENAMIENTO
    assert puerta.conciliar(1, gdf_val, df_cuar) is True


def test_caso_sintetico_coordenada_fuera_de_rango(registro_geo_valido, tmp_path):
    """CASO SINTÉTICO: Coordenada fuera del rango del estado de Colima (CDMX: 19.43, -99.13)."""
    df_inv = registro_geo_valido.copy()
    df_inv.loc[0, "latitud"] = 25.6866
    df_inv.loc[0, "longitud"] = -100.3161

    puerta = PuertaCalidadGeo(cuarentena_dir=tmp_path)
    gdf_val, df_cuar = puerta.validar_y_segregar(df_inv)

    assert len(gdf_val) == 0
    assert len(df_cuar) == 1
    assert df_cuar["regla_violada"].iloc[0] == "pandera_geo_schema_check"
    assert "latitud" in df_cuar["motivo_texto"].iloc[0] or "longitud" in df_cuar["motivo_texto"].iloc[0]
    assert puerta.conciliar(1, gdf_val, df_cuar) is True


def test_caso_sintetico_coordenada_fuera_de_poligono(registro_geo_valido, poligono_colima_sintetico, tmp_path):
    """CASO SINTÉTICO: Punto dentro del bbox amplio pero fuera del polígono de Colima."""
    df_inv = registro_geo_valido.copy()
    df_inv.loc[0, "latitud"] = 18.50
    df_inv.loc[0, "longitud"] = -106.00

    puerta = PuertaCalidadGeo(cuarentena_dir=tmp_path)
    gdf_val, df_cuar = puerta.validar_y_segregar(df_inv, gdf_marco=poligono_colima_sintetico)

    assert len(gdf_val) == 0
    assert len(df_cuar) == 1
    assert df_cuar["regla_violada"].iloc[0] == "coordenada_fuera_limites_colima"
    assert puerta.conciliar(1, gdf_val, df_cuar) is True


def test_caso_sintetico_codigo_scian_inexistente(registro_geo_valido, tmp_path):
    """CASO SINTÉTICO: Código de actividad SCIAN inexistente ('999999')."""
    df_inv = registro_geo_valido.copy()
    df_inv.loc[0, "codigo_act"] = "999999"

    puerta = PuertaCalidadGeo(cuarentena_dir=tmp_path)
    gdf_val, df_cuar = puerta.validar_y_segregar(df_inv)

    assert len(gdf_val) == 0
    assert len(df_cuar) == 1
    assert "codigo_act" in df_cuar["motivo_texto"].iloc[0]
    assert puerta.conciliar(1, gdf_val, df_cuar) is True


def test_caso_sintetico_id_duplicado(registro_geo_valido, tmp_path):
    """CASO SINTÉTICO: Dos registros con el mismo id_establecimiento."""
    df_dup = pd.concat([registro_geo_valido, registro_geo_valido.copy()], ignore_index=True)

    puerta = PuertaCalidadGeo(cuarentena_dir=tmp_path)
    gdf_val, df_cuar = puerta.validar_y_segregar(df_dup)

    assert len(gdf_val) == 0
    assert len(df_cuar) == 2
    assert all("id_establecimiento" in m or "unique" in m for m in df_cuar["motivo_texto"])
    assert puerta.conciliar(2, gdf_val, df_cuar) is True


def test_conciliacion_geo_falla_si_hay_descuadre(tmp_path):
    """La conciliación geoespacial lanza ValueError si se pierden registros en silencio."""
    puerta = PuertaCalidadGeo(cuarentena_dir=tmp_path)
    gdf_v = gpd.GeoDataFrame([{"id_establecimiento": "1", "geometry": None}])
    df_c = pd.DataFrame([{"id_establecimiento": "2"}])

    with pytest.raises(ValueError, match="FALLA CRÍTICA DE CONCILIACIÓN GEOESPACIAL"):
        puerta.conciliar(5, gdf_v, df_c)


def test_enmascarado_de_token():
    """Verifica que el token nunca queda expuesto en URLs ni mensajes de error."""
    tok_falso = "abcd1234-ef56-7890-abcd-1234567890ef"
    url = f"https://www.inegi.org.mx/app/api/denue/v1/consulta/Cuantificar/461160/06/0/{tok_falso}"
    enmascarado = enmascarar_token(url, tok_falso)
    assert tok_falso not in enmascarado
    assert "***MASKED***" in enmascarado


def test_minimizacion_datos_personales_en_plata_real():
    """Verifica que la Capa Plata geoespacial real no conserva ningún campo personal prohibido."""
    ruta_plata = BASE_DIR / "datos" / "plata" / "denue_colima_plata.parquet"
    if not ruta_plata.exists():
        pytest.skip("Capa Plata geoespacial aún no generada.")
    gdf = gpd.read_parquet(ruta_plata)
    cols_prohibidas = set(CAMPOS_PERSONALES_Y_NO_ANALITICOS_DESCARTADOS.keys())
    interseccion = set(gdf.columns) & cols_prohibidas
    assert len(interseccion) == 0, f"Se encontraron campos personales prohibidos en Plata: {interseccion}"
    assert gdf.crs is not None and gdf.crs.to_epsg() == 4326
