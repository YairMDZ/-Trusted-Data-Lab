# Documento de Entrega E1 - Observatorio de Datos

**Proyecto:** Observatorio de Datos - Comercio minorista de dulces, botanas y bebidas/helados fríos en puestos escolares  
**Región:** Colima, Colima, México  
**Materia:** Ingeniería de Datos (ATD-2602)  
**Semestre:** 7mo Semestre, Ago-Dic 2026  
**Alumno:** Yair Alejandro Molina Díaz (No. Control: 23460519)  
**Institución:** Tecnológico Nacional de México — Instituto Tecnológico de Colima  
**Docente:** Prof. Armando Román Gallardo Heredia  
**Fecha:** Noviembre 2026  

---

## 1. Objetivo de la Entrega E1

Automatizar e instrumentar el flujo integral de datos desde la capa **Bronce** hacia las capas **Plata** y **Oro**, incorporando limpieza estadística rigurosa, resolución de conflictos entre capturas heterogéneas, estandarización de esquemas temporales y conceptuales, detección y caracterización de atípicos macroeconómicos, y una **Puerta de Calidad automática estricta** basada en esquemas declarativos de Pandera con desvío a **Cuarentena** y conciliación contable de registros (100% auditable, sin borrado en silencio).

---

## 2. Matriz de Entregables del Repositorio

| Entregable | Ruta en el Repositorio | Estado Real | Descripción y Evidencia |
| :--- | :--- | :---: | :--- |
| **Módulos del Pipeline ETL** | [`src/pipeline/`](../../src/pipeline/) | **Listo** | Paquete modular en Python con responsabilidades desacopladas: `integracion.py`, `limpieza.py`, `calidad.py`, `transformacion.py`, `reduccion.py` y `run.py`. |
| **Orquestador Principal** | [`src/pipeline/run.py`](../../src/pipeline/run.py) | **Listo** | Ejecutable de punta a punta que procesa las capturas de bronce, audita calidad, resuelve duplicados, ejecuta transformaciones y materializa Plata, Oro y Cuarentena con código de retorno 0. |
| **Capa Plata (Datos Limpios)** | [`datos/plata/`](../../datos/plata/) | **Listo** | Formato Parquet columnar: `tabla_plata_long.parquet` (11,635 filas, 6 series analíticas estandarizadas) y `tipo_cambio_mensual.parquet` (421 periodos agregados con doble criterio). |
| **Parámetros de Escalamiento** | [`datos/plata/parametros_escalamiento.json`](../../datos/plata/parametros_escalamiento.json) | **Listo** | Metadatos desacoplados con parámetros de reversibilidad matemática para normalizaciones Min-Max y Z-score (mínimo, máximo, media, desviación estándar). |
| **Capa Oro (Tablas de Negocio)** | [`datos/oro/`](../../datos/oro/) | **Listo** | `matriz_mensual_macro.parquet` (537 periodos mensuales comunes 1982–2026 $\times$ 31 variables analíticas con rezagos y variables temporales) y `comparativa_sectores.parquet` (1,611 filas para análisis comparativo de Mercancías, Servicios y Agropecuarios). |
| **Capa de Cuarentena** | [`datos/cuarentena/`](../../datos/cuarentena/) | **Listo** | `cuarentena_total.parquet` y `cuarentena_total.csv` (57,614 registros segregados con motivo formal, regla violada, timestamp de auditoría y payload original completo). |
| **Puerta de Calidad Pandera** | [`src/pipeline/calidad.py`](../../src/pipeline/calidad.py) | **Listo** | Validación declarativa perezosa (*lazy*) con `pandera.DataFrameSchema`, auditoría contable de conciliación e informe automático de reglas. |
| **Suite de Pruebas Unitarias** | [`tests/test_pipeline.py`](../../tests/test_pipeline.py) | **Listo** | 7 pruebas unitarias con `pytest` que evalúan el esquema feliz, 4 casos sintéticos inválidos aislados en tests (negativos, rango, duplicados, clave no autorizada), prueba de descuadre contable y agregación cambiaria. |
| **Workflow de Procesamiento CI** | [`.github/workflows/procesar.yml`](../../.github/workflows/procesar.yml) | **Listo** | Flujo CI programado los lunes a las 13:00 UTC (posterior a la captura) y manual (`workflow_dispatch`), con control de concurrencia, permisos mínimos (`contents: write`) y fallo en rojo ante violaciones de esquema o conciliación. |
| **Reporte de Calidad de Datos** | [`docs/E1/reporte_calidad.md`](reporte_calidad.md) | **Listo** | Bitácora de validación de calidad con matriz de conciliación matemática, desglose de cuarentena y auditoría de reglas. |
| **Diccionario de Datos Oro** | [`docs/E1/diccionario_datos.md`](diccionario_datos.md) | **Listo** | Catálogo técnico de las 31 columnas de la matriz macro y de la tabla comparativa de sectores, especificando tipos de dato, unidades y descripciones. |
| **Figuras de Diagnóstico** | [`docs/E1/figuras/`](figuras/) | **Listo** | Gráficas generadas por el pipeline: `simulacion_imputacion.png`, `boxplot_variaciones.png`, `serie_atipicos_inpc.png`, `serie_atipicos_mercancias_servicios.png`. |
| **Cuaderno Narrativo** | [`docs/E1/limpieza.ipynb`](limpieza.ipynb) | **Listo** | Notebook Jupyter interactivo que narra cada fase paso a paso, ejecutado exitosamente con `nbconvert --execute` (1.94 MB) con gráficos y tablas renderizadas. |
| **Borrador de Relatoría PSP** | [`docs/relatoria-E1.md`](../relatoria-E1.md) | **Listo** | Estructura reflexiva con qué se hizo, decisiones técnicas, problemas y soluciones, aprendizajes y pendientes para E2, con marcadores para vivencias del estudiante. |

---

## 3. Instrucciones de Ejecución y Reproducibilidad

### A. Preparación del Entorno
Se requiere Python 3.10 o superior (validado en Python 3.12).
```bash
# 1. Crear y activar entorno virtual (opcional pero recomendado)
python -m venv .venv
source .venv/bin/activate  # En Linux/macOS
.venv\Scripts\Activate.ps1 # En Windows PowerShell

# 2. Instalar dependencias exactas
pip install -r requirements.txt
```

### B. Ejecución del Pipeline Completo
El script `run.py` ejecuta todas las fases secuencialmente (integración, limpieza, validación Pandera, transformaciones, capa Oro y reportes):
```bash
python src/pipeline/run.py
```
*Salida esperada:* Mensajes informativos de cada fase en consola, generación de archivos en `datos/plata/`, `datos/oro/`, `datos/cuarentena/`, `docs/E1/` y código de salida `0`.

### C. Ejecución de la Suite de Pruebas Automatizadas
```bash
pytest -v tests/
```
*Resultado verificado:* `7 passed in ~9s`.

### D. Re-ejecución del Cuaderno Narrativo
```bash
jupyter nbconvert --to notebook --execute --inplace docs/E1/limpieza.ipynb
```

---

## 4. Auditoría y Conciliación Contable de Registros

Para garantizar la regla fundamental de **cero pérdida de datos en silencio**, el pipeline implementa una comprobación contable estricta en tiempo de ejecución:

$$\text{Registros Crudos Ingresados (Total)} = \text{Registros en Plata} + \text{Registros en Cuarentena}$$

### Resumen Contable Exacto:
* **Total de observaciones leídas de `datos/bronce/`:** **69,249**
* **Total de observaciones válidas en Capa Plata:** **11,635**
  - Series analíticas mensuales consolidadas: 2,841 filas (distribuidas en 5 series: 910392, 910394, 910395, 910397, SP74625).
  - Serie cambiaria diaria FIX (SF43718 deduplicada): 8,794 filas.
* **Total de observaciones segregadas en Cuarentena:** **57,614**
  - `duplicado_captura_anterior`: 53,030 observaciones (capturas históricas repetidas con marca de tiempo anterior).
  - `serie_no_seleccionada`: 3,648 observaciones (series descartadas `628xxx` y `SP1`).
  - `valor_no_numerico_ne`: 936 observaciones (valores `"N/E"` de la serie `SP74625` entre 1969 y 1981: exactamente 156 meses distintos $\times$ 6 capturas).
* **Descuadre / Discrepancia:** **0 (Conciliación Exacta al 100%)**

---

## 5. Decisiones Técnicas y Arquitectónicas

1. **Resolución de Conflictos de Captura:**
   - *Regla aplicada:* Se agrupa por clave de serie (`cve_serie`) y periodo de referencia (`fecha`). Ante múltiples capturas en el tiempo, **prevalece la captura con `timestamp_captura` más reciente**. Los registros desplazados se envían íntegros a cuarentena con el motivo `"duplicado de captura anterior"`.
2. **Doble Criterio de Agregación para Tipo de Cambio (SF43718):**
   - El tipo de cambio FIX se publica en frecuencia diaria hábil bancaria, mientras los precios son mensuales.
   - *Criterio A (`promedio_mensual`):* Media aritmética de todas las cotizaciones del mes. Representa el costo financiero medio de reposición de mercancías para importaciones o compras continuas de insumos.
   - *Criterio B (`cierre_mensual`):* Última cotización registrada en el mes calendario (último día hábil). Representa el nivel cambiario de liquidación o cierre contable del mes.
3. **No aplicación de IQR directo sobre niveles de precios:**
   - Los niveles del INPC y sus componentes presentan una tendencia secular estocástica no estacionaria con cambios de régimen estructural (hiperinflación de los años 80, crisis de 1995, etc.). Aplicar IQR o Z-score sobre niveles clasificaría erróneamente toda la década de 1980 y principios de 1990 como "atípica" debido a la diferencia de escala con la base 2018.
   - *Solución:* Los métodos de atípicos (IQR 1.5x, Robust Z-score con MAD $>3.0$, e Isolation Forest) se ejecutaron exclusivamente sobre las **variaciones porcentuales mensuales ($\Delta\%$ mensual)**.
4. **Preservación de Choques Económicos Reales:**
   - Los valores atípicos detectados corresponden a eventos macroeconómicos históricos documentados (Pico de inflación 1987–1988 con variaciones $>15\%$ mensual, crisis cambiaria y financiera de 1995, choque de cadenas de suministro por COVID-19 en 2020).
   - *Decisión:* No se eliminaron ni se truncaron (*winsorization*), ya que reflejan la verdadera volatilidad económica del entorno mexicano. Se marcaron mediante banderas booleanas (`es_atipico_iqr`, `es_atipico_mad`, `es_atipico_iforest`).
5. **Normalización Reversible con Parámetros Desacoplados:**
   - Las normalizaciones Min-Max $[0, 1]$ y Z-score ($\mu=0, \sigma=1$) sobre variaciones mensuales se calcularon y sus parámetros se exportaron a `datos/plata/parametros_escalamiento.json`. Esto garantiza que en fases analíticas posteriores (modelación E2/E3) sea posible revertir las predicciones a unidades económicas reales ($\Delta\%$).
6. **Manejo de Multicolinealidad (VIF):**
   - El análisis del Factor de Inflación de la Varianza (VIF) sobre las variaciones sectoriales evidenció que *Mercancías* ($\text{VIF} \approx 5.74$) y *Servicios* ($\text{VIF} \approx 6.18$) presentan correlación moderada-alta debido a la tendencia común de la inflación subyacente. Por su parte, *Agropecuarios* ($\text{VIF} \approx 1.99$) muestra baja colinealidad al responder a factores de oferta climáticos y de cosechas. Se mantuvieron todas las variables para no perder riqueza analítica sectorial.

---

## 6. Hallazgos Honestos y Limitaciones

* **Ausencia de Faltantes Reales en Datos Activos:**
  Se reporta honestamente que en las series oficiales activas vigentes (`910392`, `910394`, `910395`, `910397`, `SP74625` post-1982 y `SF43718`) **no existen meses faltantes en el calendario temporal** (cobertura 100% continua).
* **Naturaleza de los Valores `"N/E"` en Banxico:**
  La serie `SP74625` (Subyacente) contiene 936 registros entre 1969 y 1981 con valor textual `"N/E"` (correspondientes a 156 meses distintos $\times$ 6 capturas históricas). Se trata de un **faltante estructural (hipótesis: el índice subyacente no existía), no imputado**, y no de una omisión accidental. Estos registros fueron enviados a cuarentena por su naturaleza no numérica.
* **Aclaración sobre la Afirmación de E0 ("0 meses faltantes"):**
  Se anota formalmente que la afirmación de la Entrega E0 de "0 meses faltantes" para `SP74625` contaba los registros con `"N/E"` como presentes en el calendario cronológico (existía una fila por mes, aunque con texto). En esta Entrega E1, al exigir tipado numérico estricto para las capas Plata y Oro, dichos registros se segregaron a cuarentena como faltante estructural no numérico, iniciando la serie numérica válida continua en `1982-01-01` (537 meses ininterrumpidos).
* **Tratamiento del Tipo de Cambio Mensual (SF43718):**
  - **Periodo 1982-01 a 1991-10 en `matriz_mensual_macro`:** Tiene valor vacío (`NaN`), **NO se imputó**. Se conserva como faltante histórico oficial (la serie FIX inició en noviembre de 1991) y se acompaña de la columna bandera booleana `tc_disponible` (`False` de 1982-01 a 1991-10; `True` a partir de 1991-11).
  - **Noviembre de 2026:** Se identifica y marca formalmente como **mes incompleto** (`es_mes_incompleto = True` en `tipo_cambio_mensual`), ya que la captura de datos solo abarca cotizaciones hábiles hasta el día 6 de noviembre de 2026 (4 días cotizados).
* **Simulación de Imputación Aislada:**
  Dado que los datos reales no tienen faltantes, el experimento comparativo de imputación (enmascarando aleatoriamente 5% y 10% en `910394`) fue un ejercicio de sensibilidad **estrictamente de simulación**. No se aplicó ninguna imputación artificial a los datos reales de Plata ni Oro.
* **No aplicación de Muestreo:**
  Debido a que el volumen mensual común abarca 537 observaciones históricas (1982–2026), aplicar técnicas de submuestreo (*sampling*) reduciría innecesariamente el tamaño de muestra sin aportar ganancias computacionales. Se conservó el 100% de la historia disponible.

---

## 7. Distinción Metodológica: Hechos Oficiales, Hipótesis y Supuestos del Dominio

* **Hecho Oficial Documentado:**  
  Banco de México calculó metodológicamente el subíndice subyacente (`SP74625`) a partir de enero de 1982; las fechas anteriores carecen de valor monetario oficial.
* **Hecho Oficial Observado:**  
  Las series del INPC base 2018 (`910xxx`) reportadas por INEGI no presentan interrupciones mensuales desde enero de 1982 hasta septiembre de 2026 (537 meses continuos).
* **[SUPUESTO APROXIMADO DEL DOMINIO]:**  
  La definición de la jerarquía de calendario escolar (*"Periodo de Clases"* vs. *"Vacaciones Escolares"*) se construyó como un **supuesto aproximado del dominio; la entrevista solo menciona vacaciones escolares y mayor venta en verano** (vacaciones de verano en julio-agosto, decembrinas en diciembre-enero, y Semana Santa en abril). Se modela como supuesto operativo del micronegocio y no como norma estadística oficial.
* **[HIPÓTESIS DE TRANSMISIÓN DE PRECIOS]:**  
  Se postula como hipótesis analítica que las variaciones en el subíndice de precios al consumidor de *Mercancías* (`910394`) y en el *Tipo de Cambio FIX* (`SF43718`) transmiten presiones de costos a las golosinas y botanas con un rezago temporal de 1 a 2 meses ($t-1$, $t-2$), periodo durante el cual los comerciantes minoristas resurtan inventarios.
