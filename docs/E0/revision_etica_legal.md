# Revisión Ética y Legal de Fuentes de Datos (Entrega E0)

**Proyecto:** Observatorio de Datos - Comercio minorista de dulces, botanas y bebidas/helados fríos en puestos escolares (Colima, México)  
**Fecha:** Noviembre 2026  
**Alcance:** Ingesta de datos de fuentes secundarias (INEGI y Banxico) y resguardo de datos cualitativos primarios.

---

## 1. Principios Éticos del Observatorio

1. **Privacidad de Sujetos de Información (Entrevista Primaria):**
   - Conforme a la ficha de la propuesta (`docs/E0/propuesta.md`), la identidad de la vendedora entrevistada se mantiene anónima para proteger su negocio e integridad económica.
   - Solo se registran patrones agregados de comportamiento de compra, estacionalidad escolar y necesidades informativas.

2. **Extracción Responsable y Sostenible:**
   - No se utiliza scraping no autorizado ni técnicas de evasión de bloqueos (anti-bot bypass, proxies rotativos no declarados).
   - Se emplean exclusivamente las **APIs oficiales para desarrolladores** de las instituciones gubernamentales.
   - Las peticiones incorporan cabeceras `User-Agent` identificables con propósito académico y contacto.
   - Se implementan pausas de cortesía (`rate limiting` con pausas mínimas de 1 a 2 segundos entre solicitudes) para evitar sobrecarga en la infraestructura pública.

3. **Seguridad y Confidencialidad de Accesos:**
   - Cero credenciales o tokens en el código fuente (`hardcoded`).
   - Gestión estricta a través de variables de entorno locales (`.env` ignorado en `.gitignore`) y secretos cifrados en GitHub Actions (`secrets.INEGI_API_TOKEN`, `secrets.BANXICO_API_TOKEN`).

---

## 2. Marco Legal y Términos de Uso por Fuente

### Fuente A: INEGI (Instituto Nacional de Estadística y Geografía)
* **Mecanismo de acceso:** API de Indicadores del INEGI (versión REST JSON).
* **Fundamento Legal:**
  - Ley del Sistema Nacional de Información Estadística y Geográfica (LSNIEG).
  - *Términos de Libre Uso de la Información del INEGI*: Los datos producidos y difundidos por el INEGI son un bien público de libre acceso.
* **Condiciones de Uso:**
  - Se permite la descarga, procesamiento, análisis, redistribución y creación de obras derivadas.
  - **Obligación de Atribución:** Citar explícitamente la fuente: *"Fuente: INEGI, Sistema de Consulta de Indicadores / INPC por genérico"*.
  - **No alteración de la verdad:** Los datos deben presentarse sin distorsión maliciosa de las cifras originales.
* **Políticas Técnicas y Robots.txt:**
  - La API de desarrolladores está diseñada expresamente para consumo automatizado mediante token personal intransferible.
  - No se vulneran directivas de `robots.txt`, ya que se interactúa con la ruta oficial de servicios web autorizados `/app/api/indicadores/desarrolladores/...`.

### Fuente B: Banco de México (Banxico)
* **Mecanismo de acceso:** API REST del Sistema de Información Económica (SIE).
* **Fundamento Legal y Términos:**
  - *Términos y Condiciones del Banco de México para el uso del SIE API*: Banxico pone a disposición del público y de la comunidad de desarrolladores las series estadísticas con fines informativos, de investigación y académicos.
* **Condiciones de Uso:**
  - Uso no exclusivo y gratuito.
  - **Obligación de Atribución:** Mencionar a Banco de México como origen de los datos (*"Fuente: Banco de México, SIE"*).
  - Prohibición expresa de presentar el observatorio como un producto oficial respaldado o certificado por el Banco de México.
* **Límites Operativos:**
  - Banxico establece límites de frecuencia por token. El código respeta estas cuotas realizando llamadas puntuales por lote y serializadas.

---

## 3. Matriz de Cumplimiento

| Criterio | INEGI (INPC) | Banxico (SIE) | Estado |
| :--- | :--- | :--- | :--- |
| **Canal de ingesta** | API Oficial Desarrolladores | API Oficial REST SIE | Cumple |
| **Autenticación** | Token vía `INEGI_API_TOKEN` | Token vía `BANXICO_API_TOKEN` | Cumple |
| **Cabecera User-Agent** | Identificable (`ObservatorioEscolarColima/1.0`) | Identificable (`ObservatorioEscolarColima/1.0`) | Cumple |
| **Pausas / Rate Limiting** | Sí (mínimo 1.5s entre llamadas) | Sí (mínimo 1.5s entre llamadas) | Cumple |
| **Atribución requerida** | Sí (requerido por Términos de Libre Uso) | Sí (requerido por Términos SIE) | Cumple |
| **Datos personales sensibles**| Ninguno (solo índices agregados de precios) | Ninguno (solo series macroeconómicas) | Cumple |
| **Almacenamiento crudo** | Formato JSON inmutable en `datos/bronce/` | Formato JSON inmutable en `datos/bronce/` | Cumple |
