# Documento de Entrega E2 — Integración Geoespacial, Linaje End-to-End y Ética de Datos

**Proyecto:** Observatorio de Datos — Comercio Minorista de Dulces, Botanas y Bebidas/Helados Fríos en Puestos Escolares  
**Región:** Estado de Colima, México (10 municipios, clave estatal `06`)  
**Materia:** Ingeniería de Datos (ATD-2602) | 7mo Semestre, Ago–Dic 2026  
**Estudiante:** Yair Alejandro Molina Díaz (No. Control: 23460519)  
**Institución:** Tecnológico Nacional de México — Instituto Tecnológico de Colima  
**Docente:** Prof. Armando Román Gallardo Heredia  
**Fecha:** 20 de noviembre de 2026  

---

## 1. Objetivo de la Entrega E2

Integrar una fuente avanzada de datos **geoespaciales** oficiales del INEGI (**DENUE Colima** + **Marco Geoestadístico Municipal**, diciembre 2025) dentro de la arquitectura Medallion (Bronce → Plata → Oro + Cuarentena) del repositorio sin alterar los valores ni las pruebas de la Entrega E1; garantizar el **linaje y trazabilidad matemática end-to-end** de todos los registros de la Capa Oro (tablas E1 y E2) hasta sus archivos crudos en Bronce; y formalizar la **Declaración de Ética, Legalidad y Gobernanza de Datos** del observatorio.

---

## 2. Matriz de Entregables del Repositorio

| Fase | Entregable | Ruta en el Repositorio | Estado Real | Evidencia y Detalles |
| :---: | :--- | :--- | :---: | :--- |
| **F1** | Análisis de fuente DENUE, SCIAN y Marco Geoestadístico | [`docs/E2/analisis_fuente_denue.md`](analisis_fuente_denue.md) | **Listo** | Documenta token, métodos REST, `robots.txt`, licencia comercial INEGI, 15 clases SCIAN literales verificadas, reporte honesto sobre piñatas/fiestas y cobertura de los 10 municipios de Colima. |
| **F2** | Extractor ético geoespacial (Capa Bronce) | [`src/denue/extractor_denue.py`](../../src/denue/extractor_denue.py) | **Listo** | Descarga el paquete masivo estatal DENUE Colima (3.61 MB) y Marco Geoestadístico GAIA (505 KB) de forma abierta (sin requerir token); utiliza `INEGI_DENUE_TOKEN` (o fallback `INEGI_API_TOKEN`) opcionalmente para una sonda previa cortés a la API REST v1 con enmascaramiento estricto (`***MASKED***`), `User-Agent` identificable y pausas de 2.0 s. |
| **F2** | Captura cruda Bronce DENUE y Marco | [`datos/bronce/denue/`](../../datos/bronce/denue/) y [`datos/bronce/marco_geoestadistico/`](../../datos/bronce/marco_geoestadistico/) | **Listo** | `denue_colima_raw_20261120_203817.zip` (42,073 registros crudos; 4,504 en clases de estudio) y `marco_geoestadistico_colima_municipios_20261120_203817.geojson` (10 municipios) + metadatos SHA-256. |
| **F3** | Capa Plata Geoespacial y Puerta de Calidad Pandera | [`src/denue/plata_geo.py`](../../src/denue/plata_geo.py) | **Listo** | GeoPandas con `EPSG:4326` (almacenamiento) y `EPSG:6372` (áreas métricas), validación Pandera `lazy=True`, contención espacial en polígonos de Colima, minimización de 29 campos personales y conciliación estricta `42,073 = 4,504 + 37,569`. |
| **F3** | Datasets Plata y Cuarentena Geoespacial | [`datos/plata/denue_colima_plata.parquet`](../../datos/plata/denue_colima_plata.parquet) y [`datos/cuarentena/cuarentena_denue.parquet`](../../datos/cuarentena/cuarentena_denue.parquet) | **Listo** | 4,504 establecimientos válidos en GeoParquet/GeoJSON (`EPSG:4326`) y 37,569 descartados por diseño en cuarentena (0 violaciones de calidad real). |
| **F3** | Pruebas unitarias geoespaciales | [`tests/test_geo_pipeline.py`](../../tests/test_geo_pipeline.py) | **Listo** | 8 pruebas con casos sintéticos aislados (coordenada fuera de rango, fuera de polígono, SCIAN inexistente, ID duplicado, descuadre de conciliación, enmascarado de token y minimización de datos personales). |
| **F4** | Capa Oro Geoespacial y Cartografía | [`src/denue/oro_geo.py`](../../src/denue/oro_geo.py) | **Listo** | Genera 3 tablas agregadas en `datos/oro/` (10 municipios, 26 localidades, 487 AGEBs) sin puntos individuales, 2 mapas en `docs/E2/figuras/` y diccionario geoespacial. |
| **F4** | Mapas cartográficos | [`docs/E2/figuras/coropleta_comercios_por_escuela_municipios.png`](figuras/coropleta_comercios_por_escuela_municipios.png) y [`docs/E2/figuras/mapa_puntos_escuelas_dulces_colima.png`](figuras/mapa_puntos_escuelas_dulces_colima.png) | **Listo** | Base cartográfica exclusiva del Marco Geoestadístico oficial INEGI (sin teselas externas), título, leyenda, fuente y fecha de captura. |
| **F4** | Diccionario geoespacial | [`docs/E2/diccionario_geoespacial.md`](diccionario_geoespacial.md) | **Listo** | Documenta CRS (`EPSG:4326` y `EPSG:6372`), columnas de Plata/Oro, superficie oficial vs. continental y los 29 campos descartados por minimización. |
| **F5** | Motor de linaje, trazabilidad y auditoría | [`src/pipeline/linaje.py`](../../src/pipeline/linaje.py) y [`tests/test_linaje.py`](../../tests/test_linaje.py) | **Listo** | Añade 9 columnas de linaje a las 5 tablas Oro, crea `datos/linaje/manifiesto_bronce.parquet` (16 archivos) y `datos/linaje/tabla_linaje.parquet` (19,241 registros), `trazar(id_registro)` y auditoría de muestra aleatoria (20/20 = 100%). |
| **F5** | Documentación de linaje | [`docs/E2/linaje.md`](linaje.md) | **Listo** | Describe el esquema de linaje, manifiesto de Bronce y 3 ejemplos reales de rastreo (`matriz_mensual_macro`, `comparativa_sectores` y `densidad_comercial_escolar_municipios`). |
| **F6** | Declaración de ética y legalidad | [`docs/etica-datos.md`](../etica-datos.md) | **Listo** | Términos de uso, licencias, `robots.txt` de los 3 dominios, minimización, sesgos y prácticas del extractor con cada afirmación marcada como verificada o pendiente de verificación. |
| **F7** | Automatización CI/CD | [`.github/workflows/denue.yml`](../../.github/workflows/denue.yml), [`.github/workflows/procesar.yml`](../../.github/workflows/procesar.yml), [`src/pipeline/run.py`](../../src/pipeline/run.py), [`requirements.txt`](../../requirements.txt) | **Listo** | Workflow mensual `denue.yml` con secrets, concurrencia, validación previa al commit y fallo en rojo si falla integridad; `run.py` y `procesar.yml` actualizados para E1 + E2 + linaje. |
| **F8** | Documentación de entrega y borrador de relatoría | [`docs/E2/ENTREGA.md`](ENTREGA.md) y [`docs/relatoria-E2.md`](../relatoria-E2.md) | **Listo** | Ficha técnica completa y borrador de relatoría con secciones A, B y C listas para completar por el estudiante. |

---

## 3. Cómo Ejecutar y Reproducir

```bash
# 1. Instalar dependencias actualizadas (incluye geopandas, shapely, pyproj, pyogrio)
pip install -r requirements.txt

# 2. (Opcional) Captura fresca en Bronce del DENUE Colima y Marco Geoestadístico
#    Nota: La descarga del paquete oficial estatal denue_06_csv.zip y del Marco Geoestadístico es abierta y NO requiere token.
#    La variable INEGI_DENUE_TOKEN (o INEGI_API_TOKEN) es opcional y solo se utiliza para sondear la API REST v1.
python src/denue/extractor_denue.py

# 3. Ejecutar el pipeline completo End-to-End (E1 + Geoespacial E2 + Linaje + Verificación)
python src/pipeline/run.py

# 4. Ejecutar verificación independiente de muestra aleatoria de linaje contra Bronce
python src/pipeline/linaje.py

# 5. Ejecutar toda la batería de pruebas unitarias (E1 + Geoespacial + Linaje)
pytest -v tests/
```

---

## 4. Conciliación Contable y Resultados Verificados

| Flujo | Entrada Cruda (Bronce) | Aprobados (Plata) | Cuarentena | Discrepancia |
| :--- | :---: | :---: | :---: | :---: |
| **Series Macroeconómicas (E1 — 14 JSON)** | **81,046** | **11,641** | **69,405** | **0** |
| **Geoespacial DENUE Colima (E2 — 1 ZIP)** | **42,073** | **4,504** | **37,569** | **0** |

* **Pruebas unitarias (`pytest -v tests/`):** **28 passed en entorno local con Bronce completo** (7 de E1 + 8 geoespaciales + 13 de linaje y privacidad). En un clon limpio de Git donde el ZIP del DENUE no está descargado (ignorado en `.gitignore` por privacidad y tamaño), se ejecutan con éxito **27 passed y 1 skipped**, saltando únicamente la auditoría profunda contra el ZIP crudo con un mensaje prescriptivo claro.
* **Auditoría de linaje (`verificar_muestra_linaje`):** **20 / 20 filas aleatorias verificadas (100.0%)** reconstruyendo valores directamente desde los JSON y ZIP crudos en `datos/bronce/`.

---

## 5. Decisiones Técnicas Clave

1. **Sonda cortés a API REST DENUE v1 + descarga masiva oficial estatal (`denue_06_csv.zip`):** Durante las pruebas reales, los endpoints `Cuantificar` y `BuscarAreaAct` de INEGI produjeron *read timeouts* de 15–20 s; además, recuperar 4,504 unidades paginadas requeriría >140 peticiones a la API REST. La descarga del paquete estatal oficial de Colima (`denue_06_csv.zip`, 3.61 MB) se realiza directamente desde los servidores abiertos de INEGI **sin requerir token**. El token `INEGI_DENUE_TOKEN` se utiliza de forma opcional exclusivamente para sondear la API REST interactiva previa a la descarga masiva, garantizando trazabilidad completa, respeto a servidores públicos y automatización en CI sin dependencias frágiles de tokens de consulta (haciendo constar que la reproducibilidad histórica exacta depende de que el INEGI mantenga la versión descargada accesible en sus servidores públicos).
   - *Aclaración sobre comprobación de hash en CI (`denue.yml` línea 62):* La comprobación `assert hashlib.sha256(z.read_bytes()).hexdigest() == meta_z['sha256']` en la línea 62 de `denue.yml` **no constituye una verificación de integridad de la fuente ni de su contenido histórico**, sino únicamente una verificación local de escritura que confirma que los bytes guardados en el disco del runner coinciden con lo emitido por el script en esa ejecución puntual (ausencia de corrupción en transferencia). La verdadera verificación de integridad histórica se realiza siempre contra el **manifiesto criptográfico de Bronce** (`datos/linaje/manifiesto_bronce.parquet`), que actúa como registro de verdad inmutable del observatorio.
2. **Servicio oficial GAIA `wscatgeo v2` para límites municipales:** Proporciona el GeoJSON oficial del *Marco Geoestadístico, diciembre de 2025* para los 10 municipios de Colima en 505 KB (en lugar de 33–40 MB del paquete Shapefile estatal completo), con población oficial del Censo 2020.
3. **Par de CRS (`EPSG:4326` + `EPSG:6372`) y separación de área continental:** `EPSG:4326` asegura interoperabilidad estándar en GeoParquet/GeoJSON; `EPSG:6372` (*Mexico ITRF2008 / LCC*) garantiza áreas exactas en $\text{km}^2$. Al detectarse que Manzanillo (`007`) y Tecomán (`009`) incluyen el Archipiélago de Revillagigedo, se calculan explícitamente `area_km2_oficial` y `area_km2_continental`.
4. **Minimización de datos personales y cero puntos en Oro:** Se eliminan 29 campos personales/domiciliarios en Plata y se publican únicamente tablas agregadas en Oro; la reconstrucción de linaje de filas agregadas se respalda en `datos/linaje/tabla_linaje.parquet` mediante los IDs oficiales (`id_establecimiento` y `cve_serie@fecha`).

---

## 6. Limitaciones y Elementos No Verificados / Hipótesis

1. **Límites legales de uso comercial de Banco de México (SIE API):** **Pendiente de verificación por el estudiante.** Las páginas HTML de `banxico.org.mx/SieAPIRest/service/v1/` y `leyendas-legales.html` interrumpieron la conexión TLS (`ConnectionResetError 10054`) durante la auditoría automatizada del 20 de noviembre de 2026; debe verificarse manualmente antes de cualquier uso comercial.
2. **Cuotas numéricas diarias exactas de la API DENUE:** **Hipótesis / pendiente de verificación.** No se encontró un umbral numérico público oficial por minuto/día; se aplican pausas éticas de 2.0 s y descarga en un solo lote oficial.
3. **Comercio informal y puestos escolares ambulantes:** El DENUE no registra vendedores ambulantes sin puesto fijo (limitación estructural del censo económico documentada en `docs/etica-datos.md`).
4. **Categoría "artículos para fiestas y piñatas":** **No existe como clase única en el catálogo SCIAN.** Reportado honestamente sin aproximación inventada; los comercios de confitería festiva y dulcería se analizan bajo la clase literal `461160`.
5. **Aplicabilidad específica de la LFPDPPP en redistribución de Bronce:** **Pendiente de verificación por el estudiante** (documentado en `docs/etica-datos.md`).
6. **Recálculo de Z-score y limitación metodológica para etapas de modelado:** La matriz `matriz_mensual_macro` contiene **32 columnas analíticas base** (+ 9 de linaje = 41 columnas). Los datos históricos se conservan salvo las 5 columnas Z-score, que se recalculan al agregar cada mes debido a la actualización de la media y la desviación estándar de la serie completa. Si esta matriz se utiliza para entrenar modelos predictivos en etapas de modelado, el escalado (Z-score o Min-Max) debe ajustarse exclusivamente sobre el conjunto de entrenamiento (*training split*) para prevenir sesgo de anticipación (*look-ahead bias*).
