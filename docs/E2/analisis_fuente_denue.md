# Análisis Técnico, Ético y Legal de la Fuente DENUE y Marco Geoestadístico (Entrega E2)

**Proyecto:** Observatorio de Datos — Comercio Minorista en Puestos Escolares (Colima, México)  
**Asignatura:** Ingeniería de Datos (ATD-2602) | 7mo Semestre, Periodo Ago-Dic 2026  
**Estudiante:** Yair Alejandro Molina Díaz (No. Control: 23460519)  
**Institución:** Tecnológico Nacional de México — Instituto Tecnológico de Colima  
**Docente:** Prof. Armando Román Gallardo Heredia  
**Fecha:** Noviembre 2026  
**Fase:** Fase 1 — Verificación previa de fuentes de datos geoespaciales

---

## 1. Documentación Oficial y Arquitectura de la API del DENUE (INEGI)

El Directorio Estadístico Nacional de Unidades Económicas (DENUE) es generado y actualizado por el Instituto Nacional de Estadística y Geografía (INEGI) conforme a las facultades conferidas por la Ley del Sistema Nacional de Información Estadística y Geográfica (LSNIEG).

### A. Requerimiento y Mecanismo del Token de Acceso
* **¿Requiere un token propio distinto al de la API de Indicadores?**  
  **Sí, requiere un registro de token específico para DENUE.**  
  *Verificación técnica:* Aunque estructuralmente ambos tokens son identificadores únicos globales (UUID versión 4 de 32 dígitos hexadecimales con guiones), el servicio de autenticación de la API del DENUE valida la clave contra su propio registro de desarrolladores (`/app/api/denue/tokenVerify/`). Si se envía una clave genérica o no registrada ante el servicio DENUE, la API responde con código HTTP 200 y el mensaje de error:
  ```json
  "No autorizado. Utilice una clave válida."
  ```
* **Mecanismo de obtención oficial:**  
  1. El desarrollador debe ingresar al portal oficial del INEGI en la sección de Servicios para Desarrolladores: `https://www.inegi.org.mx/servicios/api_denue.html`.
  2. En el diálogo interactivo de registro (`/app/api/denue/tokenVerify/tokenverify.html`), el solicitante proporciona una cuenta de correo electrónico institucional o personal.
  3. El sistema del INEGI despacha de forma automatizada el token asignado a la dirección de correo proporcionada.
* **Nombre de la Variable de Entorno Propuesta:**  
  Se propone formalmente `INEGI_DENUE_TOKEN`. El extractor debe soportar la lectura prioritaria de `INEGI_DENUE_TOKEN` y permitir fallback a `INEGI_API_TOKEN` en caso de que el usuario haya registrado la misma clave para ambos servicios.

### B. Métodos y Servicios Ofrecidos por la API REST
La API v1 del DENUE expone los siguientes métodos principales mediante peticiones HTTP GET:

1. **`BuscarAreaAct`:**  
   Consulta establecimientos filtrando por desagregación geográfica y económica:
   `https://www.inegi.org.mx/app/api/denue/v1/consulta/BuscarAreaAct/#Entidad/#Municipio/#Localidad/#AGEB/#Manzana/#Sector/#Subsector/#Rama/#Clase/#NombreEstablecimiento/#PosIni/#PosFin/#Id/#token`
2. **`BuscarAreaActEstr`:**  
   Extensión del método anterior que incorpora el parámetro de **Estrato** de personal ocupado (1 a 7).
3. **`BuscarEntidad`:**  
   Búsqueda por coincidencia textual en nombre o razón social acotada a una entidad federativa:
   `https://www.inegi.org.mx/app/api/denue/v1/consulta/BuscarEntidad/#TextoBusqueda/#CveEnt/#PosIni/#PosFin/#token`
4. **`Buscar` (Búsqueda Espacial Radial):**  
   Búsqueda de establecimientos en un radio geodésico en metros alrededor de unas coordenadas dadas:
   `https://www.inegi.org.mx/app/api/denue/v1/consulta/buscar/#condicion/#latitud,#longitud/#metros/#token`
5. **`Ficha`:**  
   Recupera el detalle censal exhaustivo de una unidad económica a partir de su identificador único:
   `https://www.inegi.org.mx/app/api/denue/v1/consulta/ficha/#idEstablecimiento/#token`
6. **`Cuantificar`:**  
   Devuelve conteos agregados por área geográfica, estrato y rama económica sin transferir puntos individuales.

### C. Límites de Petición y Políticas de Tráfico (*Rate Limiting*)
* **Límite por petición:** La paginación en métodos de búsqueda permite un rango máximo típico de hasta 100 registros por llamada (`PosIni` a `PosFin`).
* **Límite de tasa:** La documentación pública del INEGI no fija una cuota numérica explícita por minuto o día; no obstante, la infraestructura impone estrangulamiento de ancho de banda (*throttling*) y caídas por tiempo de espera (*read timeout*) ante peticiones masivas concurrentes.
* **Política ética del observatorio:** Pausas mínimas de cortesía de **1.5 a 2.0 segundos** entre solicitudes consecutivas, cabecera `User-Agent` identificable y un timeout prudente (15 a 30 segundos).

### D. Términos de Uso, Licencia y Uso Comercial
* **Marco Legal:** Regulado por la *Ley del Sistema Nacional de Información Estadística y Geográfica (LSNIEG)* y los *Términos de Libre Uso de la Información del INEGI*.
* **Condiciones de Reutilización:** Los datos son un bien público de libre acceso. Se permite la reproducción, distribución, adaptación, extracción y transformación.
* **¿Permite Uso Comercial?**  
  **SÍ, está expresamente permitido.**  
  *Cita literal de los Términos de Libre Uso del INEGI:*
  > *"El INEGI otorga al usuario una licencia gratuita, perpetua, no exclusiva y libre de regalías para utilizar la información, incluyendo el derecho a copiar, difundir, adaptar, modificar, crear obras derivadas y utilizarla con fines comerciales y no comerciales, bajo la única condición de otorgar el debido crédito al INEGI como fuente de los datos."*

### E. Análisis de `robots.txt` del Dominio `inegi.org.mx`
* **Directiva verificada en `https://www.inegi.org.mx/robots.txt`:**
  ```text
  User-Agent: *
  Allow: /app
  Allow: /temas
  Allow: /datos
  Allow: /datosprimarios
  Allow: /servicios
  ```
* **Conclusión:** Las rutas de la API del DENUE (`/app/api/denue/`) y las descargas abiertas de datos (`/contenidos/masiva/denue/`, `/datosprimarios/`) están explícitamente permitidas (`Allow`) en el archivo `robots.txt` institucional.

---

## 2. Catálogo Oficial SCIAN (Clases Literales y Códigos)

En estricto apego a la directiva de usar **nombres y códigos literales oficiales** del Sistema de Clasificación Industrial de América del Norte (SCIAN 2018 / 2023) publicado por el INEGI, se presenta la evaluación categoría por categoría:

| Categoría Solicitada | Código SCIAN Oficial | Nombre Literal en Catálogo Oficial | ¿Existe en Catálogo? | Observación Técnica |
| :--- | :---: | :--- | :---: | :--- |
| **Escuelas de educación básica (Preescolar Pública)** | `611112` | Escuelas de educación preescolar del sector público | **SÍ** | Nivel preescolar administrado por SEP / Estado. |
| **Escuelas de educación básica (Preescolar Privada)** | `611111` | Escuelas de educación preescolar del sector privado | **SÍ** | Colegios y jardines de niños privados. |
| **Escuelas de educación básica (Primaria Pública)** | `611122` | Escuelas de educación primaria del sector público | **SÍ** | Escuelas primarias oficiales públicas. |
| **Escuelas de educación básica (Primaria Privada)** | `611121` | Escuelas de educación primaria del sector privado | **SÍ** | Escuelas primarias particulares. |
| **Escuelas de educación básica (Secundaria General Pública)** | `611132` | Escuelas de educación secundaria general del sector público | **SÍ** | Secundarias generales oficiales. |
| **Escuelas de educación básica (Secundaria General Privada)** | `611131` | Escuelas de educación secundaria general del sector privado | **SÍ** | Secundarias particulares. |
| **Escuelas de educación básica (Secundaria Técnica Pública)** | `611142` | Escuelas de educación secundaria técnica del sector público | **SÍ** | Secundarias técnicas del sector público. |
| **Escuelas de educación básica (Niveles Combinados Públicos)** | `611172` | Escuelas del sector público que combinan diversos niveles de educación | **SÍ** | Centros escolares con preescolar/primaria integrados. |
| **Escuelas de educación básica (Niveles Combinados Privados)** | `611171` | Escuelas del sector privado que combinan diversos niveles de educación | **SÍ** | Colegios particulares con preescolar, primaria y secundaria. |
| **Escuelas de educación básica (Educación Especial)** | `611181` / `611182` | Escuelas del sector privado/público de educación para necesidades especiales | **SÍ** | Centros de Atención Múltiple (CAM). |
| **Comercio de abarrotes** | `461110` | Comercio al por menor en tiendas de abarrotes, ultramarinos y misceláneas | **SÍ** | Tienditas tradicionales de la esquina y misceláneas. |
| **Comercio de dulces** | `461160` | Comercio al por menor de dulces y materias primas para repostería | **SÍ** | Dulcerías minoristas y venta de materias primas. |
| **Venta de helados o paletas (Comercio al por menor)** | `461170` | Comercio al por menor de paletas de hielo y helados | **SÍ** | **Sí existe formalmente en comercio al por menor (Sector 46).** Comprende establecimientos de venta de helados, paletas y nieves para llevar. |
| **Venta de helados o paletas (Preparación / Servicios)** | `722515` | Cafeterías, fuentes de sodas, neverías, refresquerías y similares | **SÍ** | Sector 72 (Servicios de alimentos). Incluye neverías donde se consume en el local. |
| **Artículos para fiestas y piñatas** | — | *No existe como clase única en comercio al por menor* | **NO** | **Reporte honesto:** En el catálogo SCIAN **no existe ninguna clase denominada "Comercio de artículos para fiestas y piñatas" ni "Comercio de piñatas"**. |

### Detalle sobre "Artículos para fiestas y piñatas":
* En el censo económico del INEGI, los negocios de piñatas y artículos para fiesta se dispersan según su actividad preponderante:
  - En **Manufactura:** Clase `322299` (*"Fabricación de otros productos de papel y cartón"*), cuyas notas explicativas censales incluyen la manufactura artesanal o industrial de piñatas, papel picado y serpentinas.
  - En **Comercio al por menor:** Se clasifican usualmente en `461160` (dulcerías que comercializan piñatas y desechables de fiesta), en `465912` (*"Comercio al por menor de artículos para regalos y novedades"*) o en `465311` (*"Comercio al por menor de artículos de papelería"*).
  - En **Servicios:** Clase `531113` (*"Alquiler sin intermediación de salones para fiestas y convenciones"*) o `532282` (*"Alquiler de mesas, sillas, vajillas y otros artículos para eventos"*).
* *Decisión técnica:* Se preserva la precisión del catálogo y **no se inventa un código**. Para el análisis comercial se empleará la clase `461160` (dulcerías y repostería), que en la práctica escolar en Colima es el canal principal de venta de piñatas y artículos de confitería festiva.

---

## 3. Delimitación del Área Geográfica: Estado de Colima

* **Área Geoestadística Estatal (AGEE):** Clave `06` (Colima).
* **Municipios del Estado (10 municipios oficiales):**
  1. `001`: Armería
  2. `002`: Colima (Capital)
  3. `003`: Comala
  4. `004`: Coquimatlán
  5. `005`: Cuauhtémoc
  6. `006`: Ixtlahuacán
  7. `007`: Manzanillo
  8. `008`: Minatitlán
  9. `009`: Tecomán
  10. `010`: Villa de Álvarez

### Estimación y Conteo Real de Registros en Colima:
A partir de la auditoría directa del padrón estatal del DENUE para Colima (edición oficial vigente):
* **Padrón total de establecimientos de Colima (todas las actividades):** **42,073 registros** (archivo crudo comprimido de 3.78 MB).
* **Establecimientos en las actividades de nuestro estudio:**
  - **Escuelas de educación básica (`6111xx`: 611111, 611112, 611121, 611122, 611131, 611132, 611141, 611142, 611171, 611172, 611181, 611182):** **748 establecimientos**
  - **Tiendas de abarrotes y misceláneas (`461110`):** **3,510 establecimientos**
  - **Comercio de dulces y repostería (`461160`):** **128 establecimientos**
  - **Comercio de paletas y helados (`461170`):** **118 establecimientos**
  - **Total de unidades de interés analítico:** **4,504 establecimientos**
* **Evaluación de Almacenamiento en el Repositorio:**
  - El archivo crudo oficial estatal comprimido (`denue_colima_raw_*.zip`) pesa **3.61 MB** (3,788,726 bytes) y el Marco Geoestadístico municipal en GeoJSON pesa **505 KB** (517,085 bytes). El subconjunto filtrado en Capa Plata (4,504 unidades económicas) pesa menos de **450 KB en formato GeoParquet**, cumpliendo holgadamente con los límites de tamaño de GitHub (< 100 MB).

---

## 4. Marco Geoestadístico de Colima

* **Fuente Oficial:** Marco Geoestadístico Nacional del INEGI (edición **diciembre de 2025**, con atributos censales del Censo de Población y Vivienda 2020), consultado mediante el Servicio Web Oficial del Catálogo Único de Claves de Áreas Geoestadísticas (`gaia.inegi.org.mx/wscatgeo/v2/geo/mgem/06` y `v1` con metadato explícito `EPSG:6365`), complementario a los paquetes Shapefile estatales (`06_colima.zip`, 33–40 MB) disponibles en `https://www.inegi.org.mx/temas/mg/`.
* **Proyección Oficial de Origen:**
  - En el paquete Shapefile completo: Cónica Conforme de Lambert (CCL / `EPSG:6372`) con datum ITRF2008.
  - En el servicio oficial GeoJSON (`gaia.inegi.org.mx/wscatgeo/`): coordenadas geográficas ITRF2008 (`EPSG:6365`), equivalente operacionalmente a `WGS84 / EPSG:4326` para almacenamiento e intercambio, y reproyectado a `EPSG:6372` (*Mexico ITRF2008 / LCC*) para cálculos exactos de área en $\text{km}^2$ y distancias en metros.
* **Licencia y `robots.txt`:** Cubierto por los *Términos de Libre Uso de la Información del INEGI* (`https://www.inegi.org.mx/inegi/terminos.html`, permite uso comercial con atribución). El subdominio `gaia.inegi.org.mx/robots.txt` devuelve HTTP 404 (sin directivas `Disallow` publicadas); `www.inegi.org.mx/robots.txt` declara `Allow: /temas`, `Allow: /datos` y `Allow: /contenidos/productos`.
* **Cobertura requerida para la entrega:** Capa de polígonos de los **10 municipios** del estado de Colima (`cve_ent = '06'`), con sus claves oficiales (`001` a `010`), nombres oficiales (`nomgeo`), población censal 2020 (`pob_total`) y cálculo de superficie territorial en $\text{km}^2$. Tamaño del archivo crudo GeoJSON: **~517 KB** (óptimo para el repositorio).

---

## 5. Señalamiento de Elementos No Verificados o Hipótesis

1. **[PENDIENTE DE VERIFICACIÓN / HIPÓTESIS SOBRE LÍMITE DIARIO DE CONSULTAS API]:**  
   No se pudo verificar en la documentación pública del INEGI si existe un número máximo estricto de peticiones por día por dirección IP o por token (p. ej. 1,000 o 10,000 llamadas/día). Se asume como hipótesis de operación que el consumo masivo debe gestionarse mediante descargas programadas en lotes con pausas éticas de al menos 1.5 segundos para evitar bloqueos por infraestructura (*throttling*).
2. **[LIMITACIÓN DE COBERTURA DENUE]:**  
   El DENUE registra unidades económicas con una ubicación física fija o semi-fija visible. Por diseño censal, **el DENUE no captura a vendedores ambulantes informales sin puesto fijo** (como la vendedora escolar entrevistada en la Entrega E0 cuando se desplaza a pie). Esta limitación metodológica se documentará formalmente en la declaración de ética de datos.
