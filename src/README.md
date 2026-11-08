# Guía de Uso del Extractor a Capa Bronce (`src/extractor.py`)

Extractor automatizado y ético para la ingesta de datos de precios e indicadores económicos desde las APIs del **INEGI** y **Banco de México (Banxico)**.

---

## 1. Requisitos y Dependencias

El extractor utiliza exclusivamente **`requests`** y la biblioteca estándar de Python:

```bash
pip install -r requirements.txt
```

---

## 2. Variables de Entorno Requeridas

El script lee los tokens automáticamente desde el entorno o desde un archivo `.env` en la raíz del proyecto:

| Variable | Descripción | Fuente |
| :--- | :--- | :--- |
| `INEGI_TOKEN` | Token UUID (36 caracteres) para la API de Indicadores del INEGI | [Registro INEGI](https://www.inegi.org.mx/servicios/api_indicadores.html) |
| `BANXICO_TOKEN` | Token alfanumérico (64 caracteres) para el SIE de Banxico | [Registro Banxico](https://www.banxico.org.mx/SieAPIRest/service/v1/token) |

---

## 3. Funcionamiento del Extractor

Al ejecutarse, el script realiza el siguiente flujo:
1. **Validación de Credenciales:** Comprueba la existencia de `INEGI_TOKEN` y `BANXICO_TOKEN`. Si falta alguno, se detiene inmediatamente con mensaje de error explícito y código de salida `1`.
2. **Generación de Timestamp:** Crea una marca temporal unificada en formato `YYYYMMDD_HHMMSS` (ej. `20261108_153000`).
3. **Extracción Ética de INEGI:**
   - Consulta secuencialmente los 4 indicadores del INPC seleccionados (`628194`, `628204`, `628217`, `628218`).
   - Envía cabecera `User-Agent` identificable.
   - Aplica una **pausa de cortesía de 2.0 segundos** entre cada llamada HTTP.
   - Almacena el payload crudo en:  
     `datos/bronce/inegi_inpc_raw_<YYYYMMDD_HHMMSS>.json`
4. **Pausa Intermedia:** Pausa de 2.0 segundos entre la conexión a INEGI y Banxico.
5. **Extracción Ética de Banxico:**
   - Consulta en un solo lote eficiente las series (`SP1`, `SP74625`, `SF43718`) utilizando la cabecera `Bmx-Token`.
   - Almacena el payload crudo en:  
     `datos/bronce/banxico_series_raw_<YYYYMMDD_HHMMSS>.json`
6. **Registro de Auditoría (Logging):**
   - Imprime el avance detallado en la consola estándar (`stdout`).
   - Registra permanentemente los eventos, timestamps y posibles errores de red en el archivo `extraccion.log` en la raíz.

---

## 4. Ejecución

```bash
# Desde la carpeta raíz del proyecto:
python src/extractor.py
```
