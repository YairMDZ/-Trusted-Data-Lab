# Observatorio de Datos: Comercio Minorista en Puestos Escolares (Colima, México)

> **Entrega E0 - Repositorio Oficial del Observatorio de Datos**  
> Proyecto enfocado en el monitoreo y análisis de precios e insumos para microcomerciantes de dulces, botanas y bebidas/helados fríos en entornos escolares de la región de Colima.

---

## 1. Contexto del Problema y Justificación

A partir de la entrevista primaria documentada en [`docs/E0/propuesta.md`](docs/E0/propuesta.md), se identificaron las dinámicas operativas de un puesto escolar típico:
- **Demanda estacional:** Fuertemente vinculada al calendario escolar y a variaciones de temperatura (mayor venta de productos fríos y congelados en temporadas cálidas).
- **Abastecimiento reactivo:** Compras periódicas en tiendas de mayoreo (p. ej. Sam's Club) cuando se agota el inventario, sin pronósticos ni cobertura contra aumentos de precios.
- **Vulnerabilidad a costos:** La rentabilidad del micronegocio depende directamente de los precios de insumos básicos (azúcar, refrescos, jarabes, lácteos y empaques).

### Preguntas Analíticas del Observatorio
* **E1 (Pronóstico):** ¿Cuál será el índice de precios mensual de insumos clave (helados, refrescos, azúcar) en los próximos meses?
* **E2 (Factores):** ¿Cómo influyen la estacionalidad (verano vs. invierno), la inflación y el tipo de producto en el costo de los insumos?
* **E3 (Grupos):** ¿Qué grupos de productos (fríos, dulces, botanas) presentan dinámicas de precios correlacionadas a lo largo del año?

---

## 2. Fuentes de Datos Oficiales y Revisión Ética

El observatorio se abastece exclusivamente mediante **APIs oficiales para desarrolladores**:
1. **INEGI (Instituto Nacional de Estadística y Geografía):** Consulta de series mensuales del Índice Nacional de Precios al Consumidor (INPC) desglosadas por genérico (azúcar, refrescos, alimentos).
2. **Banco de México (Banxico SIE API):** Consulta de series macroeconómicas, inflación subyacente de mercancías y tipo de cambio.

> [!NOTE]  
> Para consultar el desglose detallado de los términos de libre uso, robots.txt, políticas de rate limiting y salvaguarda de privacidad, consulta la [Revisión Ética y Legal en docs/E0/revision_etica_legal.md](docs/E0/revision_etica_legal.md).

---

## 3. Estructura del Repositorio

```text
Trusted Data Lab/
├── .github/
│   └── workflows/
│       └── captura.yml                 # Workflow de CI para extracción semanal y validación
├── calidad/                            # Reservado para archivos CSV de control de calidad (PSP)
├── datos/
│   └── bronce/                         # Datos crudos extraídos de las APIs (formato JSON inmutable)
├── docs/
│   └── E0/
│       ├── propuesta.md                # Propuesta y notas de la entrevista inicial (intacta)
│       └── revision_etica_legal.md     # Dictamen ético, legal y términos de uso de APIs
├── src/
│   ├── config.py                       # Configuración centralizada y lectura de variables de entorno
│   ├── inegi_client.py                 # Extractor ético para API Indicadores INEGI
│   ├── banxico_client.py               # Extractor ético para API SIE Banxico
│   └── validar_bronce.py               # Script de validación de calidad de la capa bronce
├── .env.example                        # Plantilla de variables de entorno requeridas
├── .gitignore                          # Exclusión de credenciales y cachés (conserva datos/bronce/)
├── README.md                           # Documentación principal del observatorio
└── requirements.txt                    # Dependencias mínimas (requests y stdlib)
```

---

## 4. Configuración y Ejecución Local

### Prerrequisitos
- Python 3.9 o superior.
- Tokens de acceso de desarrollador para:
  - **INEGI:** [Solicitar token de desarrollador INEGI](https://www.inegi.org.mx/servicios/api_indicadores.html)
  - **Banxico:** [Generar token del SIE Banxico](https://www.banxico.org.mx/SieAPIRest/service/v1/token)

### Pasos de instalación

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd "Trusted Data Lab"
   ```

2. **Crear y activar entorno virtual (opcional pero recomendado):**
   ```bash
   python -m venv .venv
   # En Windows PowerShell:
   .venv\Scripts\Activate.ps1
   # En Linux/macOS:
   source .venv/bin/activate
   ```

3. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno:**
   Copia el archivo `.env.example` a `.env` y coloca tus claves:
   ```bash
   cp .env.example .env
   ```
   Edita `.env` con tus tokens reales:
   ```ini
   INEGI_API_TOKEN=tu_token_aqui
   BANXICO_API_TOKEN=tu_token_aqui
   ```

5. **Ejecutar extracción y validación:**
   ```bash
   # Extracción INEGI
   python src/inegi_client.py

   # Extracción Banxico
   python src/banxico_client.py

   # Validación de integridad de la capa bronce
   python src/validar_bronce.py
   ```

---

## 5. Automatización en GitHub Actions

El flujo automatizado se encuentra en `.github/workflows/captura.yml`. Para que funcione correctamente en GitHub:
1. Dirígete a tu repositorio en GitHub: **Settings > Secrets and variables > Actions**.
2. Agrega los siguientes secretos con sus respectivos valores:
   - `INEGI_API_TOKEN`
   - `BANXICO_API_TOKEN`

El workflow se ejecutará automáticamente en cada `push` o puede dispararse manualmente mediante el botón **Run workflow** (`workflow_dispatch`).
