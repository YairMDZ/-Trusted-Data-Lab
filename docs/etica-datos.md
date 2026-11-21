# Declaración de Ética, Legalidad y Gobernanza de Datos

**Proyecto:** Observatorio de Datos — Comercio Minorista de Dulces, Botanas y Bebidas/Helados Fríos en Puestos Escolares (Colima, México)  
**Institución:** Tecnológico Nacional de México — Instituto Tecnológico de Colima  
**Asignatura:** Ingeniería de Datos (ATD-2602) | 7mo Semestre, Ago–Dic 2026  
**Estudiante:** Yair Alejandro Molina Díaz (No. Control: 23460519)  
**Fecha de auditoría:** 20 de noviembre de 2026  

---

## Convención de Trazabilidad Legal

En apego estricto a las reglas de honestidad documental de este observatorio, **cada afirmación legal o regulatoria** en este documento indica explícitamente uno de dos estados:
* **`verificada (con enlace)`**: comprobada directamente en la fuente oficial durante la elaboración de la entrega.
* **`pendiente de verificación por el estudiante`**: requiere lectura o confirmación manual directa por el estudiante antes de cualquier uso fuera del ámbito académico.

---

## 1. Fuentes Oficiales, Términos de Uso, Licencias y Uso Comercial

| Fuente | Servicio / Endpoint | Marco Legal / Licencia | ¿Permite Uso Comercial? | Estado de Verificación |
| :--- | :--- | :--- | :---: | :--- |
| **INEGI — Indicadores (INPC)** | API BIE-BISE v2.0 (`910392`, `910394`, `910395`, `910397`) | *Términos de Libre Uso de la Información del INEGI* y LSNIEG | **Sí** (con atribución obligatoria al INEGI, sin distorsión ni falsa asociación oficial) | **verificada (con enlace):** [`https://www.inegi.org.mx/inegi/terminos.html`](https://www.inegi.org.mx/inegi/terminos.html) y [`https://www.inegi.org.mx/servicios/api_indicadores.html`](https://www.inegi.org.mx/servicios/api_indicadores.html) |
| **INEGI — DENUE** | API REST DENUE v1 + Descarga Masiva Estatal `denue_06_csv.zip` | *Términos de Libre Uso de la Información del INEGI* y LSNIEG | **Sí** (explotación comercial permitida citando fuente y fecha de actualización) | **verificada (con enlace):** [`https://www.inegi.org.mx/inegi/terminos.html`](https://www.inegi.org.mx/inegi/terminos.html) y [`https://www.inegi.org.mx/servicios/api_denue.html`](https://www.inegi.org.mx/servicios/api_denue.html) |
| **INEGI — Marco Geoestadístico** | Servicio Web GAIA `wscatgeo v2` (`mgem/06`, dic. 2025) y portal `temas/mg/` | *Términos de Libre Uso de la Información del INEGI* | **Sí** (bajo la misma licencia general de libre uso institucional del INEGI) | **verificada (con enlace):** [`https://www.inegi.org.mx/inegi/terminos.html`](https://www.inegi.org.mx/inegi/terminos.html) y [`https://www.inegi.org.mx/temas/mg/`](https://www.inegi.org.mx/temas/mg/) |
| **Banco de México — API SIE** | `SieAPIRest/service/v1` (`SP74625`, `SF43718`) | *Salvedad de uso* del API SIE y Leyendas Legales de Banxico (uso de token obligatorio, límites de consulta por periodo, atribución obligatoria a Banco de México) | **No confirmado en documento completo durante la auditoría automatizada** | **pendiente de verificación por el estudiante** — Durante la auditoría en vivo (`2026-11-20`), las páginas HTML de [`https://www.banxico.org.mx/SieAPIRest/service/v1/`](https://www.banxico.org.mx/SieAPIRest/service/v1/) y [`https://www.banxico.org.mx/footer-es/leyendas-legales.html`](https://www.banxico.org.mx/footer-es/leyendas-legales.html) interrumpieron la conexión TLS (`ConnectionResetError 10054`). El estudiante debe abrir ambos enlaces en navegador para confirmar las cláusulas exactas sobre redistribución y uso comercial antes de un uso comercial. |

### Condiciones Obligatorias de Atribución (INEGI — `verificada (con enlace)`):
Conforme a [`https://www.inegi.org.mx/inegi/terminos.html`](https://www.inegi.org.mx/inegi/terminos.html), toda obra derivada, tabla o mapa debe:
1. Otorgar crédito expreso al INEGI indicando el producto y fecha de actualización (*"Fuente: INEGI, DENUE / Marco Geoestadístico / INPC..."*).
2. No alterar ni suprimir metadatos originales en la capa cruda (respetado mediante archivos inmutables en `datos/bronce/`).
3. No distorsionar la información ni aparentar patrocinio o postura oficial del Instituto.

---

## 2. Análisis Directo de `robots.txt` por Dominio

Se consultó el archivo `robots.txt` de cada dominio utilizado por los extractores el **20 de noviembre de 2026**:

1. **`https://www.inegi.org.mx/robots.txt`** — **`verificada (con enlace)`** (HTTP 200):
   * Declara explícitamente `User-Agent: *` con directivas **`Allow: /app`**, **`Allow: /temas`**, **`Allow: /datos`**, **`Allow: /datosprimarios`**, **`Allow: /servicios`** y **`Allow: /contenidos/productos`**.
   * Sus directivas `Disallow` (sección `#SNM 18.03.2025`) restringen únicamente rutas de registro de usuarios (`/auth/register/`) y descargas de variables internas del catálogo SNM (`/catalog/*/variable/*`, `/metadata/export_variable/*`).
   * **Conclusión:** Las rutas consultadas (`/app/api/indicadores/`, `/app/api/denue/`, `/contenidos/masiva/denue/`) están permitidas.
2. **`https://gaia.inegi.org.mx/robots.txt`** — **`verificada (con enlace)`** (HTTP 404 Not Found):
   * El subdominio no publica un archivo `robots.txt` con restricciones `Disallow`. El consumo del servicio web público oficial `wscatgeo/v2/geo/mgem/06` se realiza en una sola petición GET con `User-Agent` identificable bajo los Términos de Libre Uso de INEGI.
3. **`https://www.banxico.org.mx/robots.txt`** — **`verificada (con enlace)`** (HTTP 200):
   * Declara `Disallow: /dyn`, `Disallow: /dyn/`, `Disallow: /ALEPH` y `Disallow: /V`.
   * **Conclusión:** La ruta de la API REST oficial (`/SieAPIRest/service/v1/series/...`) **no está bloqueada** por `robots.txt` y está diseñada específicamente para consumo automatizado autenticado mediante encabezado `Bmx-Token`.
4. **Límites numéricos exactos de cuota diaria (INEGI DENUE API y Banxico SIE):**
   * **`pendiente de verificación por el estudiante`**: Aunque ambos organismos imponen límites de tasa (*throttling* o inhabilitación temporal del token ante exceso de consultas), los umbrales numéricos vigentes por minuto/día del API DENUE no se encontraron publicados de manera unívoca en el portal público, y la página HTML del portal SIE de Banxico presentó rechazo TLS durante esta verificación.

---

## 3. Privacidad y Minimización de Datos Personales

### A. Campos Personales Presentes en el Origen Crudo (DENUE)
Aunque el DENUE es un directorio público estadístico levantado bajo la LSNIEG, el archivo estatal crudo (`datos/bronce/denue/denue_colima_raw_*.zip`, 42 columnas) contiene campos que, en el caso de **microempresas familiares y comercios escolares** (`0 a 5 personas`), frecuentemente constituyen datos personales o de contacto identificables:
* `nom_estab` (nombre comercial, con frecuencia coincide con el nombre propio del propietario, ej. *"Abarrotes Don..."* o nombre y apellido),
* `raz_social` (razón social o nombre de persona física con actividad empresarial),
* `telefono`, `correoelec`, `www` (canales directos de contacto),
* Domicilio exacto desagregado (`nom_vial`, `numero_ext`, `numero_int`, `edificio`, `nomb_asent`, `cod_postal`, `manzana`).

### B. Controles Técnicos Implementados (`verificada` en código y pruebas automatizadas)
1. **Minimización en Capa Plata (`src/denue/plata_geo.py`):** Se descartan los **29 campos** personales, de contacto y domicilio detallado antes de persistir `datos/plata/denue_colima_plata.parquet`. Se conservan exclusivamente el identificador oficial censal (`id_establecimiento`), código/nombre literal SCIAN, estrato de personal (`estrato_personal`), claves geográficas (`cve_ent`, `cve_mun`, `cve_loc`, `ageb`), ubicación puntual (`latitud`, `longitud`, `geometry`) y metadatos de captura.
2. **Agregación obligatoria en Capa Oro (`src/denue/oro_geo.py`):** Ninguna tabla de `datos/oro/` contiene puntos ni coordenadas individuales; únicamente se publican conteos y densidades agregadas por **municipio**, **localidad** y **AGEB**.
3. **Verificación continua en CI (`pytest`):**
   * `tests/test_geo_pipeline.py::test_minimizacion_datos_personales_en_plata_real` falla automáticamente si reaparece cualquier campo prohibido en Plata.
   * `tests/test_linaje.py::test_oro_sin_puntos_ni_coordenadas_individuales` falla automáticamente si alguna tabla en Oro expone `latitud`, `longitud`, `geometry` o campos personales.
4. **Protección de la entrevista cualitativa de campo (E0):** En todos los documentos del observatorio se mantiene el anonimato absoluto de la persona entrevistada (no se registra nombre, domicilio ni escuela específica donde opera).

### C. Marco Nacional de Protección de Datos Personales
* **`pendiente de verificación por el estudiante`**: Confirmar la aplicabilidad específica de la *Ley Federal de Protección de Datos Personales en Posesión de los Particulares (LFPDPPP)* y las excepciones de información de fuentes de acceso público en caso de redistribuir la capa Bronce en repositorios públicos de terceros. Por principio precautorio, este observatorio minimiza datos en Plata y agrega estrictamente en Oro.

### D. Opción de Gobernanza: Desacoplamiento de Archivos Crudos de Bronce sin Pérdida de Linaje (Descarga On-Demand con Manifiesto Criptográfico)
* **Problema identificado:** El archivo crudo descargado del INEGI (`datos/bronce/denue/denue_colima_raw_*.zip`, 3.61 MB) contiene los 42 campos censales completos, incluidos nombres personales de microempresarios, razones sociales, teléfonos y correos. Aunque es un conjunto de datos público institucional, versionar directamente archivos con datos personales en un repositorio Git público puede suscitar observaciones de privacidad o inflar innecesariamente el historial de Git.
* **Propuesta técnica para mantener el linaje sin versionar el ZIP en Git (documentada como opción futura; actualmente se conserva en Bronce para trazabilidad de la entrega):**
  1. **Manifiesto inmutable con hash SHA-256 (`datos/linaje/manifiesto_bronce.parquet`):** El repositorio Git versiona únicamente el manifiesto criptográfico de auditoría, registrando el nombre del archivo, URL oficial de descarga del INEGI (`https://www.inegi.org.mx/contenidos/masiva/denue/denue_06_csv.zip`), tamaño en bytes (`3,788,726 B`), fecha de corte y el hash SHA-256 (`948e292e567ce16a...`).
  2. **Descarga y verificación bajo demanda (`src/denue/extractor_denue.py`):** Se añade `datos/bronce/denue/*.zip` al `.gitignore`. Al clonar el proyecto o ejecutar el pipeline en GitHub Actions / entorno local, el script extractor verifica la existencia local del archivo; si no está presente, lo descarga de la URL oficial abierta del INEGI y comprueba inmediatamente su integridad con `hashlib.sha256() == manifiesto['sha256']`. Si el hash no coincide exactamente, el pipeline aborta con error fatal.
  3. **Minimización inmediata hacia Capa Plata:** El script `src/denue/plata_geo.py` procesa el ZIP descargado localmente, descarta de inmediato los 29 campos personales y persiste la Capa Plata (`denue_colima_plata.parquet`) y las tablas agregadas de Capa Oro, las cuales **sí se versionan en Git** libres de cualquier dato personal.
  4. **Preservación total del linaje y verificación contra manifiesto:** La función `trazar(id_registro)` y la tabla de linaje continúan funcionando de forma idéntica, pues enlazan los identificadores de Plata y Oro con el hash SHA-256 oficial del manifiesto. Se hace constar que la reproducibilidad histórica exacta de la descarga depende de que el INEGI mantenga la versión descargada accesible en sus servidores públicos oficiales.  
     *(Aclaración técnica sobre CI: la comprobación de hash en la línea 62 de `.github/workflows/denue.yml` no es una verificación de integridad de la fuente ni de su contenido histórico, sino una mera aserción local de no-corrupción de escritura para asegurar que los bytes guardados en el disco del runner coinciden con lo que el script descargó; la integridad real del observatorio se comprueba exclusivamente contra el manifiesto criptográfico de Bronce).*

### E. Debate de Gobernanza y Privacidad: ¿Versionar o no en Git los Puntos Individuales de Capa Plata (`datos/plata/denue_colima_plata.*`)?
* **Estado de la decisión:** `[PENDIENTE DE DECISIÓN POR EL ESTUDIANTE]`
* **Contexto del dilema ético-técnico:**  
  La capa Plata (`datos/plata/denue_colima_plata.parquet` y `.geojson`) contiene 4,504 registros filtrados con sus coordenadas geográficas exactas (`longitud`, `latitud`), nombre comercial (`nom_estab`), código SCIAN y estrato de personal ocupado. Aunque el pipeline aplica minimización estricta descartando 29 campos identificadores directos (razón social, nombre del propietario, teléfono, correo, calle, número exterior, colonia y código postal), persiste un dilema de privacidad sobre si estos puntos geográficos individuales deben ser versionados en el repositorio público de Git:
  - **Riesgo ético y legal identificado:** Gran parte de los establecimientos estudiados en el comercio escolar (tienditas de abarrotes, papelerías y dulcerías de 0 a 5 personas) son operados por **personas físicas** (microempresarios y familias), cuyos negocios con frecuencia coinciden físicamente con su **domicilio particular**. Aunque no se publique el nombre civil ni la calle:
    - **`hipótesis`**: Se plantea como **hipótesis** que las coordenadas capturadas en el DENUE poseen una resolución submunicipal con un radio de incertidumbre de aproximadamente 15 metros. En la metodología oficial del DENUE (INEGI), la georreferenciación en campo se levanta mediante dispositivos móviles con GPS y digitalización visual sobre ortofotos, sin que el INEGI certifique un margen de error métrico formal por predio.
    - **`hipótesis`**: Se formula como **hipótesis** la factibilidad teórica de **reidentificación indirecta** del domicilio y hábitos de vida de personas físicas concretas al cruzar dichas coordenadas con herramientas de imágenes a nivel de calle (como Google Street View), mapas comerciales o catastro municipal. Dicho riesgo se documenta como potencial bajo el principio precautorio, sin que haya sido demostrado empíricamente en este observatorio.
* **Opciones en evaluación:**
  1. **Opción A — Versionar la Capa Plata en Git:**
     - *Ventajas:* Facilita la auditoría reproducible inmediata de la entrega, permitiendo recrear mapas y análisis espaciales sin requerir descargar o descomprimir el ZIP crudo de Bronce. Los datos provienen de una fuente abierta oficial de INEGI donde ya son públicos.
     - *Riesgos:* Exposición permanente, indexable e irrevocable en el historial de Git de coordenadas exactas asociadas potencialmente a domicilios de personas físicas.
  2. **Opción B — No versionar puntos individuales en Git (ignorar Plata geoespacial y versionar solo Oro):**
     - *Ventajas:* Principio de máxima precaución (*privacy by design*). En Git público solo se versionan los agregados espaciales de Capa Oro (10 municipios, 26 localidades y 487 AGEBs), donde ningún microcomercio o persona física es re-identificable. La Capa Plata se genera localmente o en el runner efímero de CI cuando se ejecuta el pipeline.
     - *Riesgos:* Requiere que todo usuario ejecute `src/denue/plata_geo.py` localmente tras clonar el repositorio, incrementando la fricción inicial.
* **Recomendación preliminar:** Mantener la Capa Oro estrictamente agregada en Git y dejar a consideración del estudiante y del comité académico si `datos/plata/denue_colima_plata.*` se añade al `.gitignore` o se publica en el repositorio público.

---

## 4. Mitigación de Sesgos y Limitaciones Metodológicas

| Riesgo / Sesgo Identificado | Impacto Analítico | Mitigación Aplicada en el Observatorio | Estado |
| :--- | :--- | :--- | :---: |
| **Subregistro de comercio informal y ambulante en el DENUE** | El DENUE registra unidades con ubicación física fija o semifija visible; **no captura vendedores ambulantes sin puesto fijo** (como los puestos escolares itinerantes descritos en la entrevista de E0). Subestima la competencia real alrededor de escuelas. | Declaración explícita en todos los reportes y diccionarios de que las densidades geoespaciales miden exclusivamente *unidades económicas censadas por INEGI* y no el universo informal. | **verificada** (metodología DENUE INEGI y hallazgo E0) |
| **Desfase temporal del directorio DENUE** | El archivo descargado corresponde a la edición `20/05/2026` (con fechas de alta hasta `2026-04`); microcomercios de alta rotación pueden haber cerrado o abierto posteriormente. | Conservación de `fecha_alta` en Plata y `fecha_min_origen`/`fecha_max_origen` + `fecha_ingesta` en el linaje de Oro; automatización de actualización mensual (`denue.yml`). | **verificada** (metadatos internos del ZIP crudo) |
| **Escala geográfica nacional del INPC** | En la API pública de INEGI (`910392`–`910397`) y Banxico (`SP74625`), las series activas del INPC son **nacionales (`00`)** y no específicas de la ciudad de Colima (verificado en E0). | Se utilizan como indicadores macroeconómicos de referencia nacional de costos y nunca se presentan como inflación local exclusiva del municipio de Colima. | **verificada** (`docs/E0/series_seleccionadas.md`) |
| **Inexistencia de clase SCIAN única para fiestas y piñatas** | No existe una clase SCIAN llamada "artículos para fiestas y piñatas"; dichos comercios se dispersan entre `322299`, `461160`, `465912` y `465311`. | Reporte honesto en `docs/E2/analisis_fuente_denue.md` sin inventar ni forzar equivalencias artificiales; se emplea la clase oficial `461160` (dulcerías y repostería) con su nombre literal. | **verificada** (Catálogo SCIAN INEGI) |
| **Territorio insular en el cálculo de área municipal** | Los polígonos oficiales de Manzanillo (`007`) y Tecomán (`009`) incluyen el Archipiélago de Revillagigedo, lo cual distorsionaría la visualización y ligeramente el área. | Se calculan y reportan por separado `area_km2_oficial` y `area_km2_continental` en `EPSG:6372`, y los mapas estatales indican explícitamente la vista continental. | **verificada** (geometría GAIA dic. 2025) |

---

## 5. Prácticas Éticas y Técnicas de los Extractores

1. **Identificación transparente (`User-Agent`):** Todos los extractores (`src/extractor.py` y `src/denue/extractor_denue.py`) envían encabezados `User-Agent` identificables del proyecto académico. (**verificada** en código).
2. **Pausas de cortesía (*rate limiting*):** Pausa explícita de **2.0 segundos** entre peticiones consecutivas y entre servicios distintos, sin paralelismo ni reintentos agresivos. (**verificada** en código).
3. **Minimización de carga sobre servidores públicos:** Para DENUE Colima, tras una única sonda cortés con timeout de 15 s a la API REST v1, se emplea el paquete estatal oficial (`denue_06_csv.zip`, 1 sola petición HTTP de 3.61 MB) en lugar de emitir >140 peticiones paginadas a `BuscarAreaAct`. Para mapas, se usan exclusivamente los polígonos oficiales del Marco Geoestadístico (505 KB) sin descargar teselas de OpenStreetMap ni servicios de terceros. (**verificada** en código).
4. **Higiene de credenciales y secretos:** Los tokens (`INEGI_API_TOKEN`, `BANXICO_API_TOKEN`, `INEGI_DENUE_TOKEN`) nunca se escriben en el código ni en Git; se leen únicamente desde variables de entorno / GitHub Secrets. Además, `src/denue/extractor_denue.py` aplica enmascaramiento estricto (`***MASKED***`) en logs, metadatos JSON y mensajes de error, validado en `tests/test_geo_pipeline.py::test_enmascarado_de_token`. (**verificada** en código y pruebas).
5. **No borrado silencioso y conciliación:** Ningún registro crudo se descarta en silencio; el 100% de los descartes (por alcance SCIAN, duplicados históricos o fallos de calidad) se registra en `datos/cuarentena/` con conciliación contable estricta (`entrada == Plata + Cuarentena`). (**verificada** en ejecución y pruebas).
