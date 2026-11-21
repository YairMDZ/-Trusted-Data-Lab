# Diccionario de Datos Geoespaciales (Entrega E2)

**Proyecto:** Observatorio de Datos — Comercio Minorista en Puestos Escolares (Colima, México)  
**Fuentes Oficiales:** INEGI DENUE (Colima, entidad `06`) e INEGI Marco Geoestadístico (dic. 2025, servicio GAIA `wscatgeo v2`)  
**Licencia:** Términos de Libre Uso de la Información del INEGI (`https://www.inegi.org.mx/inegi/terminos.html`)

---

## 1. Sistemas de Referencia de Coordenadas (CRS) y Justificación Técnica

| Uso | Código EPSG | Nombre Oficial | Justificación Técnica |
| :--- | :---: | :--- | :--- |
| **Almacenamiento e intercambio** | `EPSG:4326` | WGS 84 (Geográfico 2D, grados decimales) | Estándar internacional RFC 7946 para GeoJSON y GeoParquet; coincide con las coordenadas latitud/longitud del DENUE y es equivalente operacionalmente a `EPSG:6365` (ITRF2008 geográfico) reportado por el servicio GAIA del INEGI. |
| **Cálculo de áreas y distancias** | `EPSG:6372` | Mexico ITRF2008 / Lambert Conformal Conic (CCL) | Proyección oficial del INEGI para el Marco Geoestadístico Nacional en metros. Evita la distorsión angular de calcular áreas o distancias en grados decimales y garantiza exactitud métrica ($	ext{km}^2$) en el estado de Colima. |

> **Nota sobre superficie oficial vs. superficie continental:**  
> En el Marco Geoestadístico oficial del INEGI, los municipios de Manzanillo (`007`) y Tecomán (`009`) incluyen territorio insular del **Archipiélago de Revillagigedo** en el Océano Pacífico (hasta $-114.76^\circ$ O). Por ello, la tabla Oro municipal reporta tanto `area_km2_oficial` (polígono completo del INEGI) como `area_km2_continental` (porción continental de Colima donde operan el 100% de las escuelas y comercios estudiados).

---

## 2. Tabla de Capa Plata: `datos/plata/denue_colima_plata.parquet` (y `.geojson`)

Contiene los establecimientos válidos de las 15 clases SCIAN de estudio tras la Puerta de Calidad Pandera y minimización estricta de datos personales. **CRS:** `EPSG:4326`.

| Columna | Tipo | Unidad / Dominio | Descripción |
| :--- | :---: | :--- | :--- |
| `id_establecimiento` | `STRING` | Identificador único | Clave numérica única del establecimiento en el DENUE (`id`). |
| `codigo_act` | `STRING` | Clave SCIAN (6 dígitos) | Código literal del catálogo oficial SCIAN (`6111xx`, `461110`, `461160`, `461170`). |
| `nombre_act` | `STRING` | Texto literal oficial | Nombre literal de la actividad económica según el catálogo SCIAN del INEGI. |
| `categoria` | `STRING` | Categórico (4 valores) | Agrupación analítica: `escuela_basica`, `abarrotes`, `dulces`, `helados_paletas`. |
| `estrato_personal` | `STRING` | Categórico censal | Estrato de personal ocupado reportado por DENUE (`0 a 5 personas`, etc.). |
| `cve_ent` | `STRING` | `"06"` | Clave oficial de la entidad federativa Colima. |
| `cve_mun` | `STRING` | `"001"` a `"010"` | Clave oficial del municipio según el Marco Geoestadístico. |
| `municipio` | `STRING` | Texto oficial | Nombre oficial del municipio de Colima. |
| `cve_loc` | `STRING` | Clave de 4 dígitos | Clave oficial de localidad geoestadística. |
| `localidad` | `STRING` | Texto oficial | Nombre oficial de la localidad. |
| `ageb` | `STRING` | Clave alfanumérica | Clave del Área Geoestadística Básica (AGEB) reportada en DENUE. |
| `latitud` | `FLOAT64` | Grados decimales (°N) | Latitud geográfica validada dentro de los polígonos oficiales de Colima. |
| `longitud` | `FLOAT64` | Grados decimales (°O) | Longitud geográfica validada dentro de los polígonos oficiales de Colima. |
| `fecha_alta` | `STRING` | `YYYY-MM` | Mes y año de incorporación del establecimiento en el directorio DENUE. |
| `fecha_captura_utc` | `STRING` | ISO 8601 UTC | Fecha y hora de descarga del archivo crudo en `datos/bronce/denue/`. |
| `archivo_origen` | `STRING` | Nombre de archivo | Archivo ZIP crudo de origen en Bronce. |
| `geometry` | `POINT` | `EPSG:4326` | Geometría puntual derivada de `(longitud, latitud)`. |

---

## 3. Tablas Agregadas de Capa Oro (`datos/oro/`) — Sin Puntos Individuales

Por principio de privacidad y diseño de capa analítica, **ninguna tabla de `datos/oro/` contiene puntos ni coordenadas individuales**. Todas las tablas incorporan adicionalmente columnas de linaje y trazabilidad generadas en la Fase 5 (`id_registro`, `fuente`, `archivos_origen_bronce`, `fecha_ingesta`, `n_registros_origen`, `fecha_min_origen`, `fecha_max_origen`, `hash_captura`, `run_id`).

### A. `datos/oro/densidad_comercial_escolar_municipios.parquet` (10 filas)

| Columna | Tipo | Unidad | Descripción y Fórmula |
| :--- | :---: | :--- | :--- |
| `cve_ent`, `cve_mun`, `municipio` | `STRING` | Catálogo INEGI | Identificadores oficiales del municipio en Colima (`06001`–`06010`). |
| `pob_total_censo2020` | `INT64` | Habitantes | Población total oficial del municipio (INEGI, Censo de Población y Vivienda 2020). |
| `area_km2_oficial` | `FLOAT64` | $\text{km}^2$ | Superficie total del polígono oficial INEGI calculada en `EPSG:6372`. |
| `area_km2_continental` | `FLOAT64` | $\text{km}^2$ | Superficie continental del municipio en `EPSG:6372` (excluye Archipiélago de Revillagigedo). |
| `n_escuelas_basicas` | `INT64` | Establecimientos | Conteo de escuelas de educación básica (`6111xx`). |
| `n_abarrotes` | `INT64` | Establecimientos | Conteo de tiendas de abarrotes, ultramarinos y misceláneas (`461110`). |
| `n_dulces` | `INT64` | Establecimientos | Conteo de comercio al por menor de dulces y materias primas para repostería (`461160`). |
| `n_helados_paletas` | `INT64` | Establecimientos | Conteo de comercio al por menor de paletas de hielo y helados (`461170`). |
| `n_comercios_total` | `INT64` | Establecimientos | Suma de `n_abarrotes + n_dulces + n_helados_paletas`. |
| `n_unidades_estudio` | `INT64` | Establecimientos | Total de unidades económicas del estudio en el municipio (`n_escuelas_basicas + n_comercios_total`). |
| `comercios_por_escuela` | `FLOAT64` | Ratio | `n_comercios_total / n_escuelas_basicas`. |
| `dulces_helados_por_escuela` | `FLOAT64` | Ratio | `(n_dulces + n_helados_paletas) / n_escuelas_basicas`. |
| `escuelas_por_km2_continental` | `FLOAT64` | $\text{escuelas}/\text{km}^2$ | `n_escuelas_basicas / area_km2_continental`. |
| `comercios_por_km2_continental` | `FLOAT64` | $\text{comercios}/\text{km}^2$ | `n_comercios_total / area_km2_continental`. |
| `escuelas_por_km2_oficial` | `FLOAT64` | $\text{escuelas}/\text{km}^2$ | `n_escuelas_basicas / area_km2_oficial`. |
| `comercios_por_km2_oficial` | `FLOAT64` | $\text{comercios}/\text{km}^2$ | `n_comercios_total / area_km2_oficial`. |
| `escuelas_por_10k_hab` | `FLOAT64` | Tasa / 10k hab. | `n_escuelas_basicas / (pob_total_censo2020 / 10,000)`. |
| `comercios_por_10k_hab` | `FLOAT64` | Tasa / 10k hab. | `n_comercios_total / (pob_total_censo2020 / 10,000)`. |

### B. `datos/oro/densidad_comercial_escolar_ageb.parquet` (487 filas) y `densidad_comercial_escolar_localidad.parquet` (26 filas)

Desagregaciones territoriales por clave de AGEB (`cve_mun`, `cve_loc`, `ageb`) y por localidad (`cve_mun`, `cve_loc`, `localidad`) con los mismos conteos (`n_escuelas_basicas`, `n_abarrotes`, `n_dulces`, `n_helados_paletas`, `n_comercios_total`, `n_unidades_estudio`) y razón `comercios_por_escuela` (`NaN` cuando `n_escuelas_basicas == 0`, sin imputación artificial).

---

## 4. Registro de Minimización de Datos Personales (Campos Descartados en Capa Plata)

De los **42 campos originales** presentes en el archivo crudo del DENUE en Bronce, se descartaron **29 campos** con información personal, de contacto o domicilio exacto antes de construir la Capa Plata:

| Campo Descartado | Justificación de Minimización |
| :--- | :--- |
| `nom_estab` | Nombre comercial del establecimiento; en microempresas suele corresponder al nombre personal del propietario. |
| `raz_social` | Razón social o nombre de persona física con actividad empresarial (dato identificativo). |
| `telefono` | Número telefónico de contacto (dato personal / de contacto no requerido para el estudio). |
| `correoelec` | Correo electrónico del establecimiento o propietario (dato personal identificable). |
| `www` | Sitio web o perfil de red social comercial (no requerido para agregación territorial). |
| `clee` | Clave Estadística de Establecimiento (código redundante al conservar id_establecimiento). |
| `tipo_vial` | Tipo de vialidad de domicilio exacto (descartado por minimización espacial). |
| `nom_vial` | Nombre de calle/vialidad de domicilio exacto (descartado por minimización espacial). |
| `tipo_v_e_1` | Entrecalle 1 (domicilio detallado innecesario). |
| `nom_v_e_1` | Nombre de entrecalle 1 (domicilio detallado innecesario). |
| `tipo_v_e_2` | Entrecalle 2 (domicilio detallado innecesario). |
| `nom_v_e_2` | Nombre de entrecalle 2 (domicilio detallado innecesario). |
| `tipo_v_e_3` | Entrecalle 3 (domicilio detallado innecesario). |
| `nom_v_e_3` | Nombre de entrecalle 3 (domicilio detallado innecesario). |
| `numero_ext` | Número exterior del domicilio exacto (descartado por minimización). |
| `letra_ext` | Letra exterior del domicilio exacto (descartado por minimización). |
| `edificio` | Nombre de edificio (descartado por minimización). |
| `edificio_e` | Piso o nivel de edificio (descartado por minimización). |
| `numero_int` | Número interior del domicilio (descartado por minimización). |
| `letra_int` | Letra interior del domicilio (descartado por minimización). |
| `tipo_asent` | Tipo de asentamiento humano (descartado por minimización). |
| `nomb_asent` | Nombre de colonia o asentamiento (descartado por minimización). |
| `tipoCenCom` | Tipo de centro comercial (descartado por minimización). |
| `nom_CenCom` | Nombre de centro comercial (descartado por minimización). |
| `num_local` | Número de local comercial (descartado por minimización). |
| `cod_postal` | Código postal (no requerido al contar con clave municipal, localidad y AGEB). |
| `manzana` | Clave de manzana censal (descartada para reducir reidentificación microespacial). |
| `tipoUniEco` | Tipo de unidad económica (fijo/semifijo; informativo secundario). |
| `entidad` | Nombre de entidad redundante con cve_ent='06'. |
