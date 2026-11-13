"""
Paquete src.pipeline para Entrega E1:
Automatización del flujo de datos hacia las capas Plata y Oro,
con limpieza estadística, puerta de calidad Pandera y cuarentena.
"""

from .integracion import integrar_datos_bronce
from .limpieza import diagnosticar_faltantes, experimento_imputacion, detectar_atipicos
from .calidad import PuertaCalidad, esquema_plata_long
from .transformacion import transformar_y_normalizar
from .reduccion import construir_capa_oro

__all__ = [
    "integrar_datos_bronce",
    "diagnosticar_faltantes",
    "experimento_imputacion",
    "detectar_atipicos",
    "PuertaCalidad",
    "esquema_plata_long",
    "transformar_y_normalizar",
    "construir_capa_oro",
]
