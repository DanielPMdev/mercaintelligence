# Despliegue de MercaIntelligence con Cloudflare Pages + Render

Esta guía asume que el repositorio de GitHub contiene el proyecto completo de MercaIntelligence, con frontend y backend en el mismo monorepo.

## Objetivo

- Frontend Vue 3 en Cloudflare Pages.
- Backend Flask en Render.
- Sin Elasticsearch ni Kibana en el despliegue público para mantener el coste cerca de cero.

## Estructura que se va a desplegar

- `frontend/` contiene la app Vue + Vite.
- `src/api/app.py` contiene la API Flask.
- `data/` y `models/` contienen los Parquet y modelos necesarios en tiempo de ejecución.

## Antes de empezar

Comprueba estas condiciones:

1. El repo de GitHub es el proyecto completo de MercaIntelligence.
2. El backend puede arrancar solo con los datos locales y los modelos ya entrenados.
3. El frontend puede consumir la API mediante una URL configurada por variable de entorno.
4. No vas a desplegar Elasticsearch ni Kibana.

## Cambios mínimos recomendados en el código

### 1. Frontend: URL de la API por variable de entorno

En [frontend/src/services/api.js](frontend/src/services/api.js), cambia la base URL para que use una variable de entorno de Vite:

```js
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})
```

Con esto, en producción el frontend llamará directamente al backend de Render u otro hosting equivalente. En local seguirá funcionando con el proxy de Vite apuntando a `http://localhost:5000`.

Importante: si frontend y backend viven en dominios distintos, la URL debe incluir el prefijo `/api`, por ejemplo `https://tu-backend.onrender.com/api`. El backend ya tiene CORS habilitado en [src/api/app.py](src/api/app.py), así que no necesitas un proxy adicional.

### 2. Frontend: fallback SPA para Vue Router

Crea el archivo [frontend/public/_redirects](frontend/public/_redirects) con este contenido:

```txt
/* /index.html 200
```

Esto evita errores 404 al refrescar rutas como `/ipc`, `/anomalias` o `/marcas`.

### 3. Backend: arranque en producción

El backend ya expone Flask en [src/api/app.py](src/api/app.py). Para producción, Render debe arrancarlo con Gunicorn.

Si `gunicorn` no está en `requirements.txt`, añádelo:

```txt
gunicorn
```

## Paso a paso: backend en Render

### 1. Crear el servicio

1. Entra en Render y conecta tu cuenta de GitHub.
2. Crea un nuevo servicio de tipo Web Service.
3. Selecciona el repositorio completo de MercaIntelligence.
4. Indica que el backend está en el repo raíz, no en una carpeta separada.

### 2. Configurar el build

Usa estos valores:

- Runtime: Python 3
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn src.api.app:app --bind 0.0.0.0:$PORT`

### 3. Variables de entorno

Si Render te permite configurar variables, no necesitas muchas para el backend. En principio basta con que la API pueda leer los ficheros locales del repo.

### 4. Verificación del backend

Cuando Render termine de desplegar, prueba estas rutas:

- `/health`
- `/api/categorias`
- `/api/productos`

Si `/health` responde bien, el backend está operativo.

## Paso a paso: frontend en Cloudflare Pages

### 1. Crear el proyecto

1. Entra en Cloudflare y ve a Pages.
2. Crea un proyecto nuevo desde GitHub.
3. Selecciona el mismo repositorio completo de MercaIntelligence.

### 2. Configurar el build

Usa estos valores:

- Framework preset: Vite
- Root directory: `frontend`
- Build command: `pnpm install --frozen-lockfile && pnpm build`
- Build output directory: `dist`

### 3. Configurar la variable de entorno

Añade esta variable en Cloudflare Pages:

- `VITE_API_URL = https://tu-backend.onrender.com/api`

Sustituye `tu-backend.onrender.com` por la URL real que te dé Render.

### 4. Verificación del frontend

Cuando Cloudflare termine de desplegar, abre la URL pública y comprueba:

- que carga la página principal;
- que navega entre vistas sin errores;
- que las peticiones a la API van al dominio de Render;
- que no aparecen errores CORS.

## Flujo recomendado de despliegue

El orden más seguro es este:

1. Primero despliega el backend en Render.
2. Verifica que `/health` responde bien.
3. Después despliega el frontend en Cloudflare Pages.
4. Configura `VITE_API_URL` con la URL del backend ya activo.
5. Prueba el flujo completo desde el navegador.

## Checklist rápido

- [ ] El repo de GitHub contiene frontend y backend juntos.
- [ ] `frontend/src/services/api.js` usa `VITE_API_URL`.
- [ ] Existe `frontend/public/_redirects` con `/* /index.html 200`.
- [ ] `requirements.txt` incluye `gunicorn`.
- [ ] Render arranca con `gunicorn src.api.app:app --bind 0.0.0.0:$PORT`.
- [ ] Cloudflare Pages construye desde `frontend/`.
- [ ] `VITE_API_URL` apunta a la URL real de Render.

## Automatizacion recomendada de la Ingesta Diaria (GitHub Actions)

El scraper se ejecuta diariamente via GitHub Actions en un self-hosted runner y hace commit de los CSVs generados. Para despliegue, la ingesta no debe depender de `--watch`: `watchdog` solo vigila carpetas locales de una maquina encendida, no carpetas remotas de GitHub.

La opcion recomendada es que `MercaIntelligence` sea el dueno de su propia ingesta:

1. `WebScraping_Mercadona` ejecuta el scraper.
2. `WebScraping_Mercadona` commitea y pushea el CSV diario en su repo.
3. `WebScraping_Mercadona` dispara un evento `repository_dispatch` hacia `MercaIntelligence`.
4. `MercaIntelligence` arranca su workflow de ingesta.
5. Ese workflow clona temporalmente el repo del scraper, localiza el CSV nuevo y ejecuta `src/etl/ingesta_incremental.py --csv`.
6. `MercaIntelligence` commitea sus datos derivados (`data/raw`, `data/processed`, `data/state`).
7. Render detecta el push en `MercaIntelligence` y redeploya el backend.

Con este diseno el scraper solo produce datos crudos, mientras que `MercaIntelligence` controla su Data Lake, sus Parquet y su estado incremental.

### Coste en GitHub Actions

El workflow de ingesta de `MercaIntelligence` es corto: checkout de dos repos, instalacion de dependencias ligeras, transformacion de un CSV y commit. En un repo privado puede consumir minutos de GitHub-hosted runners, pero deberia entrar sobradamente en la capa gratuita para un uso diario normal. Si se quiere reducir aun mas el consumo, se puede ejecutar tambien en un self-hosted runner.

### Secret necesario

En ambos repos debe existir un secret con un Personal Access Token:

- `PAT_TOKEN`: token con acceso de lectura al repo `WebScraping_Mercadona` y escritura al repo `MercaIntelligence`.

Para repos privados no conviene depender de `GITHUB_TOKEN` entre repos distintos; usa un PAT o un GitHub App token.

### 1. Workflow nuevo en MercaIntelligence

Crea el archivo `.github/workflows/ingesta-mercadona.yml` en el repo `MercaIntelligence`:

```yaml
name: Ingesta incremental Mercadona

on:
  repository_dispatch:
    types: [mercadona_csv_ready]
  workflow_dispatch:
    inputs:
      csv_name:
        description: "Nombre opcional del CSV a procesar"
        required: false

permissions:
  contents: write

jobs:
  ingesta:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout MercaIntelligence
        uses: actions/checkout@v4
        with:
          path: mercaintelligence
          token: ${{ secrets.PAT_TOKEN }}

      - name: Checkout WebScraping_Mercadona
        uses: actions/checkout@v4
        with:
          repository: danielpmprojects/WebScraping_Mercadona
          path: scraper
          token: ${{ secrets.PAT_TOKEN }}

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Instalar dependencias
        working-directory: mercaintelligence
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Localizar CSV
        id: csv
        shell: bash
        run: |
          if [ -n "${{ github.event.client_payload.csv_name }}" ]; then
            CSV="scraper/data/${{ github.event.client_payload.csv_name }}"
          elif [ -n "${{ inputs.csv_name }}" ]; then
            CSV="scraper/data/${{ inputs.csv_name }}"
          else
            CSV=$(ls -t scraper/data/*_Mercadona_*.csv | head -n 1)
          fi

          test -f "$CSV"
          echo "csv_path=$CSV" >> "$GITHUB_OUTPUT"
          echo "CSV seleccionado: $CSV"

      - name: Ejecutar ingesta incremental
        working-directory: mercaintelligence
        env:
          INGESTA_SKIP_ES: "1"
        run: |
          python src/etl/ingesta_incremental.py --csv "../${{ steps.csv.outputs.csv_path }}"

      - name: Commit datos actualizados
        working-directory: mercaintelligence
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"

          git add -f data/raw data/processed data/state

          if git diff --cached --quiet; then
            echo "No hay cambios que commitear."
            exit 0
          fi

          git commit -m "chore(datos): ingesta incremental Mercadona [skip ci]"
          git push
```

### 2. Cambio en el workflow del scraper

En el repo `WebScraping_Mercadona`, anade este paso al final de `.github/workflows/scraping.yml`, despues del paso que hace push del CSV:

```yaml
      - name: Disparar ingesta en MercaIntelligence
        if: success()
        shell: powershell
        env:
          MI_PAT: ${{ secrets.PAT_TOKEN }}
        run: |
          $csv = Get-ChildItem -Path data/ -Filter "*_Mercadona_*.csv" |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1

          if (-not $csv) {
            Write-Error "No se encontro ningun CSV para disparar la ingesta."
            exit 1
          }

          $body = @{
            event_type = "mercadona_csv_ready"
            client_payload = @{
              csv_name = $csv.Name
            }
          } | ConvertTo-Json -Depth 5

          Invoke-RestMethod `
            -Method Post `
            -Uri "https://api.github.com/repos/danielpmprojects/mercaintelligence/dispatches" `
            -Headers @{
              Authorization = "Bearer $env:MI_PAT"
              Accept = "application/vnd.github+json"
              "X-GitHub-Api-Version" = "2022-11-28"
            } `
            -Body $body
```

### 3. Ajuste necesario en `ingesta_incremental.py`

Antes de usar este workflow en despliegue sin Elasticsearch, conviene hacer opcional la indexacion. Ahora el script crea el cliente de Elasticsearch al importar:

```python
es = get_es_client()
```

Eso puede romper la ingesta en GitHub Actions si no hay Elasticsearch levantado. La solucion recomendada es que `INGESTA_SKIP_ES=1` desactive la conexion y la indexacion.

### 4. Decision sobre `.gitignore` y datos

Actualmente `.gitignore` ignora `data/` y `models/`. Con esa configuracion, Git no anadira los nuevos Parquet ni CSV salvo que el workflow use `git add -f`.

Hay dos opciones viables:

1. Mantener `data/` ignorado y usar `git add -f data/raw data/processed data/state` en el workflow.
2. Cambiar `.gitignore` para ignorar `data/` por defecto pero permitir solo las carpetas necesarias.

Para este proyecto academico, la opcion mas clara es la segunda:

```gitignore
# Data files
data/*
!data/raw/
!data/raw/**
!data/processed/
!data/processed/**
!data/state/
!data/state/**
```

Si tambien necesitas desplegar predicciones, NLP, anomalias o modelos desde Render, tendras que permitir esas carpetas equivalentes o mover esos artefactos a un almacenamiento externo. Para una produccion mas realista, lo ideal seria no versionar datasets grandes en Git y usar S3/R2, pero para un TFE y un despliegue sencillo puede ser aceptable versionar los Parquet necesarios.

Este esquema asegura que por cada ejecucion exitosa del web scraping se actualicen los datos transformados en `MercaIntelligence`. Una vez los Parquet se pusheen, Render detectara el cambio y el backend Flask cargara los datos actualizados en el siguiente arranque.

> La seccion siguiente conserva la propuesta anterior como referencia historica, pero la recomendacion principal para el despliegue es el flujo por `repository_dispatch` descrito arriba.

## Opcion anterior no recomendada: ingesta desde el workflow del scraper

Puesto que el scraper se ejecuta diariamente vía GitHub Actions en un self-hosted runner y hace commit de los CSVs generados, la ingesta en MercaIntelligence debe conectarse de forma secuencial a ese proceso, descartando ya el enfoque anterior basado en un "*watcher*" (`--watch`) que era únicamente útil para máquinas locales siempre encendidas.

El flujo robusto para sincronizar el proyecto `WebScraping_Mercadona` y `MercaIntelligence` usando GitHub Actions es actualizar el workflow del scraper (`scraping.yml`) para que, una vez termine de generar el CSV diario, actualice los Data Lakes de MercaIntelligence antes o durante el propio proceso de commit.

Puedes añadir este bloque `Run ETL Incremental` en tu archivo `scraping.yml` (justo después del paso donde el scraper acaba y genera su CSV, pero antes de subir cambios). Este paso:
1. Clona el repositorio de `MercaIntelligence`.
2. Ejecuta el script `ingesta_incremental.py` pasándole como fuente el archivo CSV exacto del día.
3. El script guarda el CSV dentro de `data/raw/` de MercaIntelligence y actualiza los ficheros `.parquet` (`ultimo_precio.parquet` y las nuevas particiones).
4. Hace push de los nuevos datos y predicciones calculadas.

```yaml
      # ... pasos previos del webdriver / spyder.py ...

      - name: Clonar MercaIntelligence para ingesta
        uses: actions/checkout@v4
        with:
          repository: <usuario_github>/mercaintelligence
          path: mercaintelligence
          token: ${{ secrets.PAT_TOKEN }}
          
      - name: Ingesta Incremental ETL
        run: |
          # 1. Instalar dependencias necesarias para la ingesta
          pip install pandas pyarrow watchdog Elasticsearch requests
          
          # 2. Localizar el CSV generado de hoy por el Scraper
          $CSV_HOY = Get-ChildItem -Path data/ -Filter "*_Mercadona_*.csv" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
          
          # 3. Procesar ese único CSV contra el código de MercaIntelligence (en modo --csv)
          cd mercaintelligence
          python src/etl/ingesta_incremental.py --csv "..\$($CSV_HOY.FullName)"
          cd ..

      - name: Commit en MercaIntelligence (Datos Actualizados)
        run: |
          cd mercaintelligence
          git config --global user.name "GitHub Actions Bot"
          git config --global user.email "actions@github.com"
          git add data/raw/ data/processed/ data/state/
          git commit -m "chore(datos): Ingesta incremental de $($CSV_HOY.Name) [skip ci]" || echo "No hay cambios para commitear"
          git push
```

Este esquema asegura que por cada ejecución existosa del web scraping en `WebScraping_Mercadona`, se actualicen los datos transformados en el repo de `MercaIntelligence`. Una vez el nuevo `.parquet` y los datos en crudo sean pusheados, Render lo detectará y al servir el backend de Flask en la nube cargará ya los datos actualizados.

## Notas importantes

- No despliegues Elasticsearch ni Kibana si quieres mantener el coste bajo.
- La API carga datos de `data/` y modelos de `models/`, así que esos directorios deben estar incluidos en el repo o disponibles en el entorno de Render.
- Render puede dormir en planes gratuitos o muy baratos; eso es normal en servicios de bajo coste.

## Resultado esperado

Al terminar, tendrás:

- Frontend estático servido por Cloudflare Pages.
- API Flask accesible en Render.
- Navegación SPA funcionando.
- Coste muy bajo o cercano a cero.

## Siguiente paso

Si quieres, puedo dejarte ahora mismo los cambios exactos en el código del repo para que esta guía funcione sin pasos manuales adicionales.
