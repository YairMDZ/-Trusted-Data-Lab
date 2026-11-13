# Diccionario de Datos del Observatorio (Entrega E1)

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
| `var_pct_inpc_general` | `FLOAT` | Porcentaje (%) | Inflación mensual del índice general: $\Delta\% = (I_t/I_{t-1}-1)\times 100$. |
| `var_pct_mercancias` | `FLOAT` | Porcentaje (%) | Variación mensual porcentual del subíndice de Mercancías. |
| `var_pct_servicios` | `FLOAT` | Porcentaje (%) | Variación mensual porcentual del subíndice de Servicios. |
| `var_pct_agropecuarios` | `FLOAT` | Porcentaje (%) | Variación mensual porcentual del subíndice de Agropecuarios. |
| `var_pct_subyacente` | `FLOAT` | Porcentaje (%) | Variación mensual porcentual del subíndice Subyacente. |
| `z_mercancias` | `FLOAT` | Adimensional | Estandarización Z-score del nivel de mercancías: $(x - \mu)/\sigma$. |
| `z_agropecuarios` | `FLOAT` | Adimensional | Estandarización Z-score del nivel de agropecuarios: $(x - \mu)/\sigma$. |
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
| `es_temporada_calor` | `INT` | Booleano (0 o 1) | 1 si mes $\in [4, 5, 6, 7, 8]$ (meses calurosos en Colima); 0 en caso contrario. |
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
