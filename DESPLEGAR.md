# Despliegue de MercaIntelligence con Cloudflare Pages + Hugging Face Spaces

Esta guia asume que el repositorio de GitHub contiene el proyecto completo de MercaIntelligence, con frontend y backend en el mismo monorepo.

## Objetivo

- Frontend Vue 3 en Cloudflare Pages.
- Backend Flask en Hugging Face Spaces usando Docker.
- Sin Elasticsearch ni Kibana en el despliegue publico para mantener el coste cerca de cero.
- Ingesta incremental diaria automatizada con GitHub Actions.

## Por que no Render Free

Render Free limita el servicio a 512 MB de memoria. Este backend carga los Parquet historicos con Pandas al arrancar:

```python
df_historico = pd.read_parquet(PARTITIONED_DIR, columns=COLS_CATALOGO)
```

Aunque los Parquet no parezcan enormes en disco, al cargarlos en memoria con Pandas el consumo crece bastante. En Render el despliegue fallo con:

```txt
Out of memory (used over 512Mi)
```

Por eso la alternativa recomendada para este TFE es Hugging Face Spaces Docker. El hardware CPU Basic gratuito de Spaces ofrece mucha mas RAM que Render Free y encaja mejor con un backend de analitica que carga datos en memoria.

## Estructura que se va a desplegar

- `frontend/` contiene la app Vue + Vite.
- `src/api/app.py` contiene la API Flask.
- `data/processed/`, `data/raw/` y `data/state/` contienen los datos necesarios para la API y la ingesta incremental.
- No se despliega Elasticsearch.

## Antes de empezar

Comprueba estas condiciones:

1. El repo de GitHub contiene frontend y backend juntos.
2. `data/processed/` esta versionado en Git o disponible dentro del Space.
3. El backend puede arrancar solo con los Parquet locales.
4. El frontend consume la API mediante `VITE_API_URL`.
5. La ingesta incremental puede ejecutarse con `INGESTA_SKIP_ES=1`.

## Cambios minimos recomendados

### 1. Frontend: URL de la API por variable de entorno

En `frontend/src/services/api.js`, la base URL debe depender de `VITE_API_URL`:

```js
const apiBaseUrl = import.meta.env.VITE_API_URL?.trim() || '/api'

const client = axios.create({
  baseURL: apiBaseUrl.replace(/\/$/, ''),
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
})
```

En produccion, Cloudflare llamara directamente al backend de Hugging Face Spaces. La URL debe incluir `/api`, por ejemplo:

```txt
https://tu-usuario-mercaintelligence.hf.space/api
```

### 2. Frontend: fallback SPA para Vue Router

Debe existir `frontend/public/_redirects` con este contenido:

```txt
/* /index.html 200
```

Esto evita errores 404 al refrescar rutas como `/ipc`, `/anomalias` o `/marcas`.

### 3. Backend: Dockerfile para Hugging Face Spaces

Crea un `Dockerfile` en la raiz del repo para ejecutar Flask en el puerto esperado por Hugging Face Spaces.

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["sh", "-c", "gunicorn src.api.app:app --bind 0.0.0.0:${PORT} --workers 1 --timeout 120"]
```

Notas:

- `--workers 1` evita duplicar la memoria cargando los Parquet varias veces.
- `PORT=7860` es el puerto habitual para Spaces Docker.
- `gunicorn` debe estar en `requirements.txt`.

### 4. Backend: datos versionables

`.gitignore` debe permitir versionar solo las carpetas de datos necesarias:

```gitignore
data/*
!data/raw/
!data/raw/**
!data/processed/
!data/processed/**
!data/state/
!data/state/**
```

Mantener ignoradas otras carpetas de datos evita subir artefactos pesados por accidente.

## Paso a paso: backend en Hugging Face Spaces

### 1. Crear el Space

1. Entra en Hugging Face.
2. Crea un nuevo Space.
3. Selecciona SDK: `Docker`.
4. Elige visibilidad segun tu necesidad:
   - `Public`: codigo y app visibles.
   - `Private`: codigo y app privados.
5. Usa CPU Basic gratuito.

### 2. Conectar el codigo

Tienes dos opciones:

1. Subir el contenido del repo al repositorio Git del Space.
2. Crear un workflow de GitHub Actions que sincronice el repo con Hugging Face Spaces.

Para el TFE, la opcion mas simple es subir al Space los archivos necesarios del backend:

- `Dockerfile`
- `requirements.txt`
- `src/`
- `data/processed/`
- `data/state/`
- `data/raw/` si quieres trazabilidad del CSV original

Si quieres mantener el despliegue automatico, anade un workflow que haga push al remoto del Space cada vez que cambie `main`.

### 3. Variables de entorno en el Space

Configura estas variables en Settings del Space:

```txt
INGESTA_SKIP_ES=1
```

No necesitas `ES_HOST` si no vas a desplegar Elasticsearch.

### 4. Verificacion del backend

Cuando el Space termine de construir, prueba:

```txt
https://tu-usuario-mercaintelligence.hf.space/health
https://tu-usuario-mercaintelligence.hf.space/api/categorias
https://tu-usuario-mercaintelligence.hf.space/api/productos
```

Si `/health` responde, el backend esta operativo.

## Paso a paso: frontend en Cloudflare Pages

### 1. Crear el proyecto

1. Entra en Cloudflare Pages.
2. Crea un proyecto nuevo desde GitHub.
3. Selecciona el repositorio completo de MercaIntelligence.

### 2. Configurar el build

Usa estos valores:

- Framework preset: `Vite`
- Root directory: `frontend`
- Build command: `pnpm install --frozen-lockfile && pnpm build`
- Build output directory: `dist`

### 3. Configurar la variable de entorno

Anade esta variable en Cloudflare Pages:

```txt
VITE_API_URL=https://tu-usuario-mercaintelligence.hf.space/api
```

Sustituye la URL por la URL real del Space.

### 4. Verificacion del frontend

Cuando Cloudflare termine de desplegar, comprueba:

- Que carga la pagina principal.
- Que al refrescar rutas internas no aparece 404.
- Que las peticiones van al dominio de Hugging Face Spaces.
- Que no aparecen errores CORS.

## Flujo recomendado de despliegue

El orden mas seguro es este:

1. Despliega primero el backend en Hugging Face Spaces.
2. Verifica `/health`.
3. Despliega el frontend en Cloudflare Pages.
4. Configura `VITE_API_URL` con la URL del Space.
5. Prueba el flujo completo desde el navegador.

## Automatizacion de la ingesta diaria

El scraper se ejecuta diariamente via GitHub Actions en un self-hosted runner y hace commit de los CSV generados. La ingesta no debe depender de `--watch`, porque `watchdog` solo vigila carpetas locales de una maquina encendida.

La opcion recomendada es que `MercaIntelligence` sea el dueno de su propia ingesta:

1. `WebScraping_Mercadona` ejecuta el scraper.
2. `WebScraping_Mercadona` commitea y pushea el CSV diario en su repo.
3. `WebScraping_Mercadona` dispara un evento `repository_dispatch` hacia `MercaIntelligence`.
4. `MercaIntelligence` arranca su workflow de ingesta.
5. Ese workflow clona temporalmente el repo del scraper, localiza el CSV nuevo y ejecuta `src/etl/ingesta_incremental.py --csv`.
6. `MercaIntelligence` commitea `data/raw`, `data/processed` y `data/state`.
7. El despliegue del backend se actualiza al sincronizar el repo con Hugging Face Spaces.

## Workflow en MercaIntelligence

Debe existir `.github/workflows/ingesta-mercadona.yml` con este comportamiento:

- Recibir `repository_dispatch` con `mercadona_csv_ready`.
- Clonar `MercaIntelligence`.
- Clonar `WebScraping_Mercadona`.
- Localizar el CSV nuevo.
- Ejecutar la ingesta con `INGESTA_SKIP_ES=1`.
- Commmit y push de `data/raw`, `data/processed` y `data/state`.

Ejemplo de comando principal:

```bash
python src/etl/ingesta_incremental.py --csv "../${{ steps.csv.outputs.csv_path }}"
```

## Cambio en el workflow del scraper

En `WebScraping_Mercadona`, despues de subir el CSV, el workflow debe disparar:

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
        "Content-Type" = "application/json"
      } `
      -Body $body
```

## Secrets necesarios

En ambos repos debe existir:

```txt
PAT_TOKEN
```

Ese token debe tener permisos para:

- Leer `WebScraping_Mercadona`.
- Escribir en `MercaIntelligence`.
- Disparar `repository_dispatch`.

Si automatizas tambien el despliegue hacia Hugging Face Spaces desde GitHub Actions, anade:

```txt
HF_TOKEN
```

## Checklist rapido

- [ ] `frontend/src/services/api.js` usa `VITE_API_URL`.
- [ ] `frontend/public/_redirects` existe.
- [ ] `requirements.txt` incluye `gunicorn`.
- [ ] Existe `Dockerfile` en la raiz para Hugging Face Spaces.
- [ ] `data/processed` y `data/state` estan disponibles en el Space.
- [ ] `INGESTA_SKIP_ES=1` esta configurado en el Space.
- [ ] El Space responde en `/health`.
- [ ] Cloudflare Pages tiene `VITE_API_URL` apuntando al Space con `/api`.
- [ ] El scraper dispara `repository_dispatch`.
- [ ] MercaIntelligence ejecuta la ingesta incremental.

## Resultado esperado

Al terminar, tendras:

- Frontend estatico servido por Cloudflare Pages.
- API Flask servida por Hugging Face Spaces Docker.
- Ingesta diaria automatizada desde GitHub Actions.
- Datos Parquet actualizados tras cada ejecucion del scraper.
- Coste cercano a cero para un uso academico o de demostracion.
