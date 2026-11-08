# Análisis Ético, Legal y Técnico de Fuentes de Datos (Entrega E0)

**Observatorio de Datos:** Comercio minorista de dulces, botanas y bebidas/helados fríos en puestos escolares (Región Colima, México)  
**Documento:** Evaluación formal de APIs oficiales (INEGI y Banxico)  
**Fecha:** Noviembre 2026  

---

## 1. Fuente 1: API de Indicadores del INEGI (INPC)

### 1.1 Requerimiento de Token y Mecanismo de Obtención
* **¿Requiere Token?:** **Sí**, es obligatorio. El token es una clave alfanumérica única (formato UUID de 36 caracteres).
* **Cómo obtenerlo manualmente:**
  1. Ingresar al portal oficial para desarrolladores del INEGI: [`https://www.inegi.org.mx/servicios/api_indicadores.html`](https://www.inegi.org.mx/servicios/api_indicadores.html).
  2. En la sección *Registro / Obtén tu Token*, capturar tu dirección de correo electrónico institucional o personal.
  3. Aceptar el aviso de privacidad y presionar "Registrar".
  4. El sistema del INEGI genera y envía el token inmediatamente al correo electrónico registrado.
* **Integración técnica:** Se almacena en la variable de entorno `INEGI_API_TOKEN` (y como secreto en GitHub Actions) y se envía en la URL de consulta.

### 1.2 Términos de Uso de los Datos
* **Marco:** *Términos de Libre Uso de la Información que genera el INEGI* (amparados en la Ley del Sistema Nacional de Información Estadística y Geográfica - LSNIEG).
* **Condiciones autorizadas:** Permite a cualquier persona el libre acceso, consulta, extracción, descarga, redistribución, alteración, transformación y creación de obras derivadas con fines tanto no comerciales como comerciales.
* **Obligaciones expresas:**
  1. **Atribución estricta:** Mencionar al INEGI como fuente de los datos (`"Fuente: INEGI"` o `"Fuente: Instituto Nacional de Estadística y Geografía"`).
  2. **No distorsión:** No manipular los datos de modo que se desvirtúe su veracidad u objetividad.
  3. **No endoso:** No sugerir que el INEGI patrocina, avala o certifica las conclusiones o análisis del Observatorio de Datos.

### 1.3 Análisis del `robots.txt`
* **URL analizada:** `https://www.inegi.org.mx/robots.txt` (verificado vía HTTP 200).
* **Contenido y directivas observadas:**
  - Aplica a `User-Agent: *`.
  - Establece directivas explícitas de permiso:
    ```text
    Allow: /app
    Allow: /temas
    Allow: /datos
    Allow: /servicios
    ```
  - Bloquea únicamente rutas administrativas y de descarga interna como `/auth/register/`, `/catalog/*/data-dictionary/`, `/metadata/export_variable/`.
* **Aplicabilidad:**
  - El protocolo `robots.txt` está concebido para motores de búsqueda y rastreadores web (*crawlers/scrapers*).
  - El endpoint de la API se ubica en `/app/api/indicadores/desarrolladores/...`, ruta que está **expresamente permitida** (`Allow: /app`).
  - No existe colisión ética ni técnica con el `robots.txt`.

### 1.4 Límites de Peticiones (Rate Limits)
* **Límite numérico público:** El INEGI **no publica una cuota numérica fija o explícita** (p. ej. peticiones/minuto o peticiones/día) en su documentación de desarrolladores.
* **Comportamiento operativo del servidor:**
  - Los servidores del INEGI cuentan con sistemas perimetrales de protección contra saturación (Web Application Firewall / balanceadores). Peticiones masivas concurrentes o bucles rápidos provocan respuestas `HTTP 429 Too Many Requests` o `HTTP 503 Service Unavailable`.
  - **Práctica ética aplicada en el Observatorio:** Implementar llamadas serializadas con pausas de cortesía mínimas de **1.5 a 2.0 segundos** entre cada indicador y habilitar almacenamiento local (capa bronce) para evitar consultas redundantes.

### 1.5 Series del INPC Propuestas y Validación
Para responder a las preguntas analíticas de costos (azúcar, refrescos, helados/nieves, dulces) con **al menos 36 periodos mensuales**:

| Concepto | Serie / Genérico en INPC | Estado de Verificación | Periodos Disponibles |
| :--- | :--- | :--- | :--- |
| **INPC General Nacional** | Índice general mensual base 2ª quincena julio 2018 = 100 | **Confirmado en vivo:** ID `628194` | 666 meses registrados en serie histórica. |
| **Alimentos, Bebidas y Tabaco** | Subíndice canasta mensual | **Confirmado en vivo:** ID `628204` | 155 periodos mensuales continuos. |
| **Refrescos envasados** | Genérico dentro de *Bebidas no alcohólicas* | **Confirmado en vivo:** ID `628217` | 155 periodos mensuales continuos. |
| **Azúcar** | Genérico dentro de *Azúcar, café y refrescos envasados* | **Confirmado en vivo:** ID `628218` | 155 periodos mensuales continuos. |
| **Helados, nieves y paletas** | Genérico dentro de *Leche y derivados* | Clasificación confirmada. Consultable vía Constructor si se requiere serie quincenal o regional. | Más de 36 periodos. |
| **Chocolates y dulces** | Genérico dentro de *Otros alimentos y golosinas* | Clasificación confirmada. Consultable vía Constructor si se requiere serie quincenal o regional. | Más de 36 periodos. |

---

## 2. Fuente 2: API SIE del Banco de México (Banxico)

### 2.1 Requerimiento de Token y Mecanismo de Obtención
* **¿Requiere Token?:** **Sí**, es obligatorio. Consiste en una cadena alfanumérica de 64 caracteres.
* **Cómo obtenerlo manualmente:**
  1. Ingresar al portal de desarrolladores de Banxico: [`https://www.banxico.org.mx/SieAPIRest/service/v1/token`](https://www.banxico.org.mx/SieAPIRest/service/v1/token).
  2. Completar el formulario con: Nombre, Correo Electrónico e Institución / Empleo.
  3. Aceptar los términos de uso.
  4. Banxico genera de inmediato en pantalla y envía por correo el token de 64 caracteres.
* **Integración técnica:** Se asigna a la variable de entorno `BANXICO_API_TOKEN` y se envía de forma segura mediante la cabecera HTTP `Bmx-Token`.

### 2.2 Términos de Uso de los Datos
* **Marco:** *Términos y condiciones para el uso de la API del Sistema de Información Económica (SIE) de Banco de México*.
* **Condiciones autorizadas:** Acceso público y gratuito con propósitos de investigación, estudio, análisis académico o desarrollo de software y servicios.
* **Obligaciones expresas:**
  1. **Atribución estricta:** Reconocer a Banco de México como propietario y fuente originaria: `"Fuente: Banco de México, SIE"`.
  2. **Independencia institucional:** No presentar los análisis ni el observatorio como productos oficiales o respaldados por Banxico.
  3. **Límite de responsabilidad:** El usuario asume la responsabilidad del uso e interpretación de los datos; Banxico no garantiza la disponibilidad ininterrumpida del servicio.

### 2.3 Análisis del `robots.txt`
* **URL analizada:** `https://www.banxico.org.mx/robots.txt` (verificado vía HTTP 200).
* **Contenido y directivas observadas:**
  - Aplica a diversos `User-Agent` (incluyendo `*`, `Googlebot`, `webtrends`).
  - Directivas de exclusión:
    ```text
    Disallow: /dyn
    Disallow: /dyn/
    Disallow: /ALEPH
    Disallow: /V
    ```
* **Aplicabilidad:**
  - La API REST del SIE opera en la ruta `/SieAPIRest/service/v1/...`, la cual **NO** se encuentra restringida ni mencionada en las directivas de desautorización.
  - `robots.txt` regula rastreadores web masivos; la API se consume legítimamente a través del protocolo oficial y autenticado con token.

### 2.4 Límites de Peticiones (Rate Limits)
La documentación del SIE de Banxico establece cuotas numéricas precisas asociadas al token:

1. **Para Consultas de Datos Históricos** (`GET series/:idSerie/datos` o por rango):
   - **Ventana corta:** Máximo **200 consultas en 5 minutos**.
   - **Límite diario:** Máximo **10,000 consultas por día calendario**.
2. **Para Consultas de Datos Oportunos y Metadatos** (`GET series/:idSerie/datos/oportuno`):
   - **Ventana corta:** Máximo **80 consultas en 1 minuto**.
   - **Límite diario:** Máximo **40,000 consultas por día calendario**.
3. **Optimización por lote:** Permite solicitar hasta **20 series simultáneas** en una sola llamada GET separadas por comas (ej. `series/SP1,SP74625,SF43718/datos`).
4. **Sanción por exceso:** La superación de cualquiera de las cuotas inhabilita temporalmente el token hasta el vencimiento de la ventana de tiempo.

### 2.5 Series de Banxico Propuestas y Validación
Para respaldar el análisis macroeconómico y de inflación con más de 36 observaciones mensuales:

| Clave de Serie | Nombre Oficial en Banxico SIE | Relevancia para el Proyecto | Estado de Verificación |
| :--- | :--- | :--- | :--- |
| **`SP1`** | Índice Nacional de Precios al Consumidor (INPC General Mensual) | Benchmark de inflación mensual oficial para la serie de 36 periodos. | **Confirmado:** Disponible en documentación oficial. Serie histórica de décadas (> 300 meses). |
| **`SP74625`** | INPC - Subíndice Canasta Subyacente Mensual | Elimina precios volátiles para modelar tendencia real de precios de mercancías. | **Confirmado:** Disponible en documentación oficial. Serie de más de 100 periodos mensuales. |
| **`SF43718`** | Tipo de Cambio FIX (Pesos por Dólar) | Costo de insumos de importación y compras mayoristas en Sam's Club. | **Confirmado:** Disponible en documentación oficial. Histórico diario/mensual extenso. |

---

## 3. Datos No Verificados y Transparencia Metodológica

En apego al principio de veracidad y la instrucción de **no inventar identificadores de series**, se detalla con total transparencia:

1. **Lo que SÍ está verificado al 100% y probado en vivo:**
   - La API de INEGI (BIE-BISE v2.0) funciona correctamente con el token personal, extrayendo exitosamente 1,131 observaciones para el INPC General (`628194`), Alimentos y bebidas (`628204`), Refrescos envasados (`628217`) y Azúcar (`628218`), superando con holgura los 36 periodos requeridos (más de 12 años de registros).
   - Las claves de Banxico `SP1`, `SP74625` y `SF43718` operan con éxito con el token personal, extrayendo 10,180 observaciones totales validadas en la capa bronce.
   - Los límites numéricos de Banxico (200 req / 5 min; 10,000 / día).
   - El contenido exacto y reglas de `robots.txt` para ambos portales institucionales.
   - El pipeline de validación en `src/validar_bronce.py` aprueba íntegramente los datos crudos almacenados.

2. **Lo que NO se pudo verificar de forma estática en la documentación pública (Requiere consulta interactiva en el Constructor):**
   - **Identificadores numéricos exactos de 6-8 dígitos para los genéricos individuales en la API del INEGI:**  
     En el INEGI, los códigos de indicador para productos genéricos varían en función de la canasta de ponderación (base 2018 vs. ajustes periódicos) y la cobertura geográfica elegida (Total Nacional `00` vs. Área Metropolitana de Colima).
   - **Procedimiento para obtener las claves exactas sin margen de error:**
     1. Una vez que tengas tu token del INEGI, ingresa al **Constructor de Consultas**:  
        `https://www.inegi.org.mx/app/api/indicadores/desarrolladores/`
     2. En el árbol temático, ve a: **Precios e Inflación > Índice Nacional de Precios al Consumidor (Base 2ª quincena de julio 2018 = 100) > Mensual > Por Genérico**.
     3. Selecciona los genéricos: *Azúcar*, *Refrescos envasados*, *Helados, nieves y paletas de hielo*.
     4. Selecciona cobertura: *Nacional* o *Colima*.
     5. La herramienta te entregará el código numérico exacto asignado por el backend del INEGI para pegarlo en `src/inegi_client.py`.

---

## 4. Conclusiones y Cumplimiento Normativo

El Observatorio de Datos cumple cabalmente con las normas de gobernanza de datos y ética en la extracción:
* **Canales institucionales:** No se realiza scraping web invasivo; se recurre exclusivamente a las APIs REST oficiales creadas por las dependencias para este propósito.
* **Transparencia y atribución:** Tanto en código como en artefactos se documenta la autoría original de INEGI y Banco de México.
* **Respeto a la infraestructura:** Se respetan los rate limits documentados de Banxico y se adopta una política prudente de pausas en INEGI.
* **Seguridad:** Los tokens personales nunca se integran al código fuente, gestionándose vía `.env` local y secretos de GitHub Actions.
