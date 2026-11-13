# Relatoría Técnica y Reflexiva — Entrega E1: Flujo a Capas Plata y Oro, Limpieza Estadística y Puerta de Calidad

**Proyecto:** Observatorio de Datos — Comercio Minorista en Puestos Escolares (Colima, México)  
**Asignatura:** Ingeniería de Datos (ATD-2602) | 7mo Semestre, Periodo Ago-Dic 2026  
**Estudiante:** Yair Alejandro Molina Díaz (No. Control: 23460519)  
**Institución:** Tecnológico Nacional de México — Instituto Tecnológico de Colima  
**Docente:** Prof. Armando Román Gallardo Heredia  
**Fecha:** Noviembre 2026  
**Estado:** *Borrador técnico estructurado con marcadores para registro de experiencia personal del estudiante*

---

> [!NOTE]
> Este documento contiene la relatoría técnica estructurada de la Entrega E1. Las secciones técnicas describen los hechos y decisiones de ingeniería implementados en el código. Las secciones marcadas como `[ESPACIO PERSONAL DEL ESTUDIANTE]` están reservadas para que Yair Alejandro Molina Díaz registre sus tiempos reales de desarrollo, reflexiones cualitativas y aprendizajes subjetivos de acuerdo con su bitácora PSP (`calidad/tiempo-yair-molina.csv` y `calidad/defectos-yair-molina.csv`).

---

## 1. Qué se Hizo (Resumen del Proceso de Ingeniería)

Durante esta segunda entrega (E1) se construyó la infraestructura completa de procesamiento, validación y almacenamiento para transitar desde la capa de ingesta cruda (**Bronce**) hacia las capas procesadas y analíticas (**Plata** y **Oro**):

1. **Diseño y Estructuración Modular (`src/pipeline/`):**  
   Se diseñó una arquitectura desacoplada en 5 módulos especializados:
   - `integracion.py`: Extracción, parseo de JSON heterogéneos de INEGI y Banxico, estandarización de fechas ISO al primer día del mes, tipado numérico, deduplicación temporal y agregación cambiaria diario-a-mensual.
   - `limpieza.py`: Diagnóstico de continuidad calendárica, caracterización de faltantes estructurales (hipótesis: el índice subyacente no existía), no imputados, experimento de sensibilidad de imputación (enmascaramiento al 5% y 10%) y detección de atípicos sobre variaciones porcentuales mensuales ($\Delta\%$) con IQR, Z-score robusto (MAD) e Isolation Forest.
   - `calidad.py`: Puerta de Calidad automática declarativa con `Pandera`, validación perezosa (*lazy*), segregación estricta a cuarentena con payload original y conciliación contable matemática.
   - `transformacion.py`: Normalización Min-Max y Z-score con persistencia desacoplada de parámetros (`parametros_escalamiento.json`), jerarquías temporales (mes, trimestre, semestre, año) y operativas (calendario escolar), y discretización de variaciones por cuantiles y umbrales de dominio.
   - `reduccion.py`: Alineación al periodo histórico común (1982–2026), cálculo de multicolinealidad mediante Factor de Inflación de la Varianza (VIF) y materialización de las tablas de la Capa Oro.
   - `run.py`: Orquestador principal que ejecuta el pipeline secuencialmente garantizando trazabilidad y código de salida `0`.

2. **Gobernanza de Calidad y Cuarentena:**  
   Se implementó una regla de contabilidad estricta: ningún dato se descarta en silencio. Todos los registros no aptos (duplicados de capturas anteriores, series legadas no seleccionadas y valores textuales `"N/E"`) fueron dirigidos a `datos/cuarentena/` con timestamp, regla violada y motivo explícito.

3. **Pruebas y Automatización CI/CD:**  
   - Se implementaron 7 pruebas unitarias con `pytest` en `tests/test_pipeline.py`, evaluando esquemas válidos, 4 casos sintéticos no válidos creados exclusivamente en tiempo de prueba (valores negativos, fuera de rango, fechas duplicadas y series no aprobadas), descuadres contables y agregación cambiaria.
   - Se configuró el flujo de GitHub Actions en `.github/workflows/procesar.yml` con permisos restringidos (`contents: write`), control de concurrencia y ejecución programada los lunes a las 13:00 UTC (posterior a la captura de bronce).

4. **Documentación Ejecutable y Diccionarios:**  
   - Se elaboró el cuaderno interactivo `docs/E1/limpieza.ipynb`, narrando y visualizando cada etapa con gráficos generados y ejecutado al 100% mediante `nbconvert`.
   - Se crearon los documentos técnicos de apoyo: `docs/E1/reporte_calidad.md`, `docs/E1/diccionario_datos.md` y `docs/E1/ENTREGA.md`.

---

## 2. Decisiones Técnicas y su Justificación

| Decisión Técnica | Alternativa Descartada | Justificación de Ingeniería |
| :--- | :--- | :--- |
| **Deduplicación por Timestamp de Captura** | Conservar la primera captura o promediar valores | La política institucional de INEGI y Banxico actualiza o corrige cifras históricas en publicaciones posteriores. Por ello, la regla de negocio más sólida es que **prevalece la captura más reciente**, enviando las versiones anteriores a cuarentena con trazabilidad. |
| **Doble Criterio de Agregación para Tipo de Cambio (SF43718)** | Usar únicamente el promedio mensual o únicamente el último día | El promedio mensual representa el costo financiero medio para reposición continua de mercancías, mientras que el cierre del mes refleja la cotización de liquidación contable. Proveer ambas columnas en la tabla agregada dota de flexibilidad analítica a las siguientes etapas sin perder información. |
| **Detección de Atípicos sobre Variaciones ($\Delta\%$) y NO sobre Niveles** | Aplicar IQR directamente sobre los valores de índice | Los niveles de precio del INPC presentan una tendencia no estacionaria ascendente marcada por cambios estructurales (hiperinflación de los años 80 y 90). El IQR directo sobre niveles clasificaría erróneamente todos los datos de 1980 a 2000 como "atípicos" debido al cambio de base 2018. Trabajar sobre diferencias porcentuales mensuales aísla la verdadera volatilidad económica de corto plazo. |
| **Conservación con Banderas de Atípicos Macroeconómicos** | Imputar o truncar (*winsorizar*) los atípicos | Los picos detectados (1987-1988, 1995, 2020) corresponden a eventos macroeconómicos reales de la historia de México (pico inflacionario del pacto económico, crisis del Tequila y choque de oferta por COVID-19). Truncarlos distorsionaría la verdadera varianza del proceso económico. |
| **Validación Perezosa (*Lazy*) con Pandera** | Validación temprana (*fail-fast*) tradicional | La validación *lazy* recolecta la totalidad de los errores en un solo pase, permitiendo enviar todos los registros anómalos a cuarentena y conciliar la base completa, en lugar de detener el pipeline en el primer error. |
| **Desacoplamiento de Parámetros de Escalamiento** | Normalizar directamente sin guardar metadatos | Para que cualquier modelo en capas futuras pueda predecir y comunicar resultados interpretables para la comerciante de Colima (en porcentaje o pesos), es indispensable poder revertir la normalización. Por ello, los mínimos, máximos, medias y desviaciones se almacenaron en un JSON estructurado. |
| **No Aplicación de Muestreo** | Submuestrear la serie temporal | Con 537 periodos mensuales comunes, el volumen es analíticamente manejable y computacionalmente liviano. Submuestrear destruiría la autocorrelación temporal necesaria para el análisis de series de tiempo. |

---

## 3. Problemas Encontrados y Cómo se Resolvieron

1. **Conflicto de Capturas Históricas Múltiples:**  
   - *Problema:* En la carpeta `datos/bronce/` existían múltiples capturas de diferentes fechas que acumulaban más de 69,000 registros, conteniendo versiones duplicadas de las mismas observaciones temporales.
   - *Solución:* Se programó una función de deduplicación determinista en `integracion.py` que ordena las capturas por timestamp, selecciona la última observación y etiqueta los 53,030 duplicados como `"duplicado_captura_anterior"`, enviándolos de forma auditable a la tabla de cuarentena.

2. **Valores No Numéricos en Series Históricas de Banxico:**  
   - *Problema:* La serie del INPC Subyacente (`SP74625`) contenía 936 observaciones con la cadena `"N/E"` entre 1969 y 1981 (156 meses distintos $\times$ 6 capturas históricas), lo que provocaba errores al castear a tipo flotante.
   - *Solución:* Se identificó que se trata de un **faltante estructural (hipótesis: el índice subyacente no existía), no imputado**. Se implementó una regla de filtrado tipado: estos 936 registros fueron catalogados como `"valor_no_numerico_ne"` y enviados a cuarentena con su valor original sin imputar artificialmente, preservando la integridad de los datos numéricos continuos a partir de enero de 1982.

3. **Incompatibilidad de Frecuencias Temporales (Diario vs. Mensual):**  
   - *Problema:* La serie `SF43718` (Tipo de cambio FIX) registra cotizaciones diarias hábiles (8,794 filas), mientras que las series del INPC son mensuales (537 filas).
   - *Solución:* Se construyó una tabla agregada mensual con doble criterio estadístico (`promedio_mensual` y `cierre_mensual`), permitiendo unirla sin pérdida de grano con la matriz analítica de la Capa Oro.

4. **Conciliación Contable Estricta:**  
   - *Problema:* El riesgo latente en pipelines de datos es la pérdida silenciosa de filas por filtros implícitos de Pandas (`dropna`, `merge` internos o conversiones de tipo con errores coercitivos).
   - *Solución:* Se diseñó la función `conciliar_registros()` en `calidad.py` que calcula activamente la igualdad matemática entre entradas y salidas ($69,249 = 11,635 + 57,614$). Si la diferencia es distinta de cero, el sistema levanta una excepción crítica y bloquea la materialización de Oro.

---

## 4. Aprendizajes Clave

1. **La Calidad de Datos es un Proceso Activo y Auditable:**  
   En la práctica académica habitual, la "limpieza de datos" suele reducirse a eliminar filas con valores nulos o atípicos de forma arbitraria (`df.dropna()`). En esta entrega se constató que en la ingeniería de datos profesional el descarte sin justificación es inaceptable: toda fila excluida debe tener una justificación formal, una regla asociada y una ubicación de cuarentena recuperable.
2. **Importancia de la Estacionariedad en Series Temporales:**  
   Aplicar métodos estadísticos estándar como Tukey's IQR o Z-score sobre series no estacionarias (como los niveles del INPC) genera falsos positivos masivos. La transformación matemática a variaciones porcentuales mensuales ($\Delta\%$) es un requisito teórico indispensable antes del análisis de calidad en series económicas.
3. **Gobernanza Declarativa con Pandera:**  
   A diferencia de las validaciones artesanales con bloques `if/else`, definir contratos de datos con `Pandera` permite que los esquemas actúen como documentación viva y validadores de tiempo de ejecución, facilitando además la integración en pruebas unitarias continuas con `pytest`.

---

## 5. Pendientes y Conexión con la Entrega E2

Para la siguiente etapa (**Entrega E2: Factores de Influencia y Relaciones Estadísticas**), se identifican los siguientes puntos de partida:
1. **Modelación de la Estacionalidad Escolar vs. Climática:**  
   Analizar formalmente si los picos de variación en *Mercancías* (`910394`) y *Agropecuarios* (`910397`) coinciden con las temporadas de calor en Colima (marzo–junio) y con el inicio del ciclo escolar (agosto–septiembre).
2. **Análisis de Rezagos Temporales (*Lags*):**  
   Probar empíricamente la hipótesis sobre la transmisión del tipo de cambio FIX (`SF43718`) y las variaciones en precios al consumidor de mercancías hacia los costos de insumos de los puestos escolares con rezagos de 1 y 2 periodos ($t-1$, $t-2$), aprovechando que las columnas ya fueron generadas en la tabla `matriz_mensual_macro.parquet`.
3. **Descomposición de Series de Tiempo:**  
   Separar formalmente las componentes de tendencia, ciclo, estacionalidad y ruido mediante métodos como STL (*Seasonal and Trend decomposition using Loess*) sobre las series de la Capa Oro.

---

## 6. Registro Personal de Experiencia y Reflexión PSP (Estudiante)

<!-- ======================================================================= -->
<!-- ESPACIO RESERVADO PARA YAIR ALEJANDRO MOLINA DÍAZ                      -->
<!-- Instrucciones: Rellena esta sección con tus propias palabras,          -->
<!-- documentando tus horas invertidas (contrastadas con tu tiempo-*.csv),  -->
<!-- los defectos más retadores de resolver (según defectos-*.csv) y       -->
<!-- tu reflexión sobre el desarrollo de esta Entrega E1.                   -->
<!-- ======================================================================= -->

### A. Tiempos de Desarrollo y Esfuerzo Invertido (PSP Fase por Fase)
> *[COMPLETAR POR EL ESTUDIANTE: Escribe aquí un resumen cualitativo de las fases que más tiempo te tomaron (por ejemplo, diseño de Pandera, resolución de duplicados, elaboración del notebook o configuración de GitHub Actions), haciendo referencia a los registros reales de `calidad/tiempo-yair-molina.csv`]*

### B. Análisis de Defectos Encontrados y Eficacia de Detección
> *[COMPLETAR POR EL ESTUDIANTE: Describe cuáles fueron los defectos más difíciles de detectar o resolver durante las pruebas de la Entrega E1 (por ejemplo, formateo de strings en el logging, advertencias de eventos en asyncio con Windows, o validaciones de tipos en Pandera), en concordancia con `calidad/defectos-yair-molina.csv`]*

### C. Reflexión Personal y Conclusiones del Estudiante
> *[COMPLETAR POR EL ESTUDIANTE: Escribe aquí tu conclusión personal sobre lo aprendido en esta etapa, cómo se vincula con la comerciante escolar de Colima que entrevistaste en la E0, y cómo visualizas la utilidad de estas tablas limpias para la toma de decisiones en su puesto]*
