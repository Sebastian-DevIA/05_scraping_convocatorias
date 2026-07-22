# Manual de usuario — Sistema de búsqueda de convocatorias

Guía completa para usar, configurar, ejecutar, instalar en otro equipo y escalar
la herramienta que rastrea convocatorias reales (licitaciones, fondos, RFP/EOI)
de SECOP II, PNUD, MinCiencias, MinTIC y UNGM.

---

## 1. Qué es y para qué sirve

Es un buscador propio de oportunidades de negocio: revisa periódicamente cinco
fuentes oficiales, guarda las convocatorias que coinciden con tus palabras
clave, y te deja buscarlas, filtrarlas y **validar que la entidad que las
publica existe de verdad** antes de que inviertas tiempo armando una propuesta.

No inventa ni completa datos. Si una fuente no publica una fecha o un monto,
la herramienta lo deja vacío — nunca lo rellena. Cada convocatoria siempre
trae el enlace a su publicación oficial (`url_original`) para que la
verificación final la hagas tú, contra la fuente real.

---

## 2. Cómo funciona (arquitectura)

```
Fuentes oficiales          Conectores            Pipeline                Postgres        API REST        Frontend
SECOP II (API Socrata) ┐                     ┌─ normaliza fechas/estado
PNUD                   │   1 módulo Python   │  a UTC y vocabulario     │
MinCiencias            ├─▶ por fuente, con   ─┤  canónico                ├─▶ FastAPI ──▶  Buscador web
MinTIC                 │   reintentos y      │  dedupe por hash          │              (dashboard,
UNGM (inactiva, stub)  ┘   rate-limit        └─ upsert (solo actualiza  │               filtros, fichas)
                                                 si cambió el contenido) ┘
```

Un **worker** (APScheduler) repite este ciclo automáticamente cada
`SCRAPE_INTERVAL_MINUTES` (6 horas por defecto). También puedes dispararlo a
mano desde el botón **"Actualizar ahora"** del frontend o con `POST
/api/v1/scraping/run`.

### ¿Qué "modelos" usa? (aclaración importante)

Hay dos sentidos distintos para "modelo" y conviene no mezclarlos:

- **Modelos de datos** (lo que realmente usa la aplicación en producción):
  tres tablas — `Fuente`, `Convocatoria`, `Ejecucion` — en PostgreSQL. La
  búsqueda por palabra clave usa el buscador de texto completo nativo de
  Postgres en español (`tsvector` + `websearch_to_tsquery`), no un modelo de
  lenguaje. El mapeo de fechas, estados y tipos es **determinístico** (reglas
  Python), no generativo. Esto es intencional: para datos oficiales de
  contratación pública, un resultado 100% reproducible y auditable vale más
  que uno "inteligente" pero probabilístico.
- **Modelos de IA usados para construir y mantener el proyecto**: el código
  de este sistema (conectores, pipeline, API y frontend) se desarrolló con
  **Claude Code**, un agente de codificación de Anthropic, orquestando
  sub-agentes especializados (backend, frontend, QA, seguridad) bajo un
  "tech lead". Esa IA no corre en producción ni toca tus datos en vivo — solo
  se usa cuando tú (u otra persona) le pide ayuda para programar, depurar o
  extender la herramienta. Ver la sección 8 para cómo aprovechar esto en el
  día a día, incluso gratis.

### Stack técnico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Alembic |
| Ingesta | httpx + tenacity (conectores plugin, auto-registrados) |
| Programación de tareas | APScheduler (proceso `worker`) |
| Base de datos | PostgreSQL 16 (JSONB + full-text español) |
| Frontend | HTML/CSS/JS vanilla (sin frameworks), servido por nginx |
| Orquestación | Docker Compose (4 servicios: `db`, `api`, `worker`, `frontend`) |

---

## 3. Guía de uso de la interfaz

Abre `http://localhost:8090` (o el dominio donde lo despliegues).

### Dashboard (`#/dashboard`)
KPIs generales (total, abiertas, nuevas en 7 días, cierran en 7 días),
distribución por fuente/estado/departamento, y un listado de las convocatorias
abiertas que cierran más pronto.

### Buscar (`#/convocatorias`)
El buscador completo. Filtros disponibles:

| Filtro | Qué hace |
|---|---|
| Palabra clave | Búsqueda de texto completo sobre título + descripción |
| Fuente | SECOP, PNUD, MinCiencias, MinTIC |
| Estado | `abierta`, `cerrada`, `adjudicada`, `vencida`, `desconocido` |
| Tipo | `licitacion`, `subvencion`, `fondo`, `rfp`, `eoi`, `otro` |
| Departamento | Texto exacto (ej. "Antioquia") |
| Publicada desde/hasta | Rango de fecha de publicación |
| Cierra desde/hasta | Rango de fecha de cierre |
| Monto mínimo/máximo | En la moneda de cada convocatoria (normalmente COP) |
| Orden | Por fecha de publicación, cierre, monto o última vez visto |

Cada resultado muestra, de forma destacada, la **entidad emisora** y su
ubicación, y un botón directo **"Ver publicación oficial y verificar
entidad"**.

### Ficha de detalle
Al hacer clic en "Ver ficha y validar" se abre un panel con:
- Bloque de **validación de organización**: nombre de la entidad, ubicación,
  botón grande al aviso oficial, y ayudas de verificación externa (búsqueda
  en RUES y en la web por el nombre real de la entidad).
- Monto, fechas de publicación/apertura/cierre, ID externo de la fuente.
- Descripción y requisitos (si la fuente los publica; si no, se indica
  explícitamente que hay que revisarlos en la publicación oficial).

### Fuentes (`#/fuentes`)
Salud de cada conector: última ejecución, ítems obtenidos/nuevos/actualizados,
mensaje de error si algo falló, botón para **ejecutar esa fuente ahora** y su
historial completo de corridas.

---

## 4. Cómo se ejecuta

Requisitos: **Docker Desktop** (Windows/Mac) o **Docker Engine + Compose**
(Linux). En Windows, con WSL2 activado.

```bash
cp .env.example .env        # ajusta credenciales antes de arrancar
docker compose up -d --build
```

Al arrancar, el contenedor `api` aplica las migraciones (`alembic upgrade
head`) y siembra las 5 fuentes automáticamente (operación idempotente — no
duplica nada si ya corrió antes). El `worker` hace una primera pasada de
scraping inmediata y luego repite cada `SCRAPE_INTERVAL_MINUTES`.

| Servicio | URL/puerto en el host |
|---|---|
| Frontend | http://localhost:8090 |
| API | http://localhost:8100/api/v1 |
| Health check | http://localhost:8100/api/v1/health |
| Postgres | localhost:5433 |

Otros comandos útiles:

```bash
docker compose logs -f api            # logs de la API
docker compose logs -f worker         # logs del scraping periódico
docker compose run --rm api pytest    # tests (Postgres real, no SQLite)
curl -X POST "http://localhost:8100/api/v1/scraping/run"                 # todas las fuentes
curl -X POST "http://localhost:8100/api/v1/scraping/run?fuente=secop"    # una sola fuente
docker compose down                   # apaga todo, conserva los datos
docker compose down -v                # apaga y BORRA la base de datos (irreversible)
```

---

## 5. Configuración (`.env`)

Copia `.env.example` a `.env` (este archivo real nunca se sube a git — está
en `.gitignore`) y ajusta lo que necesites:

| Variable | Default | Qué controla |
|---|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `convocatorias` | Credenciales de la base. Cambia la contraseña antes de usar esto en serio. |
| `DATABASE_URL` | apunta al servicio `db` interno | Cadena de conexión que usan `api` y `worker`. |
| `DB_PORT` / `API_PORT` / `FRONTEND_PORT` | `5433` / `8100` / `8090` | Puertos publicados en tu máquina (host). Cámbialos si chocan con otro proyecto. |
| `SCRAPE_INTERVAL_MINUTES` | `360` (6 h) | Cada cuánto se repite el scraping automático. |
| `SCRAPE_KEYWORDS` | `tecnología,TIC,inclusión digital,...` | Lista de palabras clave (separadas por coma) que filtran qué convocatorias se guardan. Edítala sin tocar código para orientar la búsqueda a tu sector. |
| `SECOP_APP_TOKEN` | vacío | Token opcional de Socrata (datos.gov.co) para subir la cuota de rate-limit de SECOP II. Se pide gratis en [datos.gov.co](https://www.datos.gov.co). |
| `HTTP_USER_AGENT` | `ConvocatoriasBot/0.1 (+contacto: ...)` | Identificación del bot ante las fuentes — buena práctica dejar un contacto real. |
| `LOG_LEVEL` | `INFO` | Verbosidad de los logs (`DEBUG` para diagnosticar problemas de un conector). |

---

## 6. Instalarlo y usarlo en otra PC (local)

1. Instala **Docker Desktop** (Windows/Mac) y actívale la integración con tu
   distro de WSL si estás en Windows (*Settings → Resources → WSL
   Integration*).
2. Copia la carpeta completa del proyecto al nuevo equipo (o clónala si la
   subes a un repositorio Git privado).
3. `cp .env.example .env` y ajusta credenciales/puertos si ya tienes algo
   corriendo en esos puertos.
4. `docker compose up -d --build` desde la raíz del proyecto.
5. Espera a que `docker compose ps` muestre `db` y `api` como `healthy`
   (puede tardar 1–2 minutos la primera vez, porque construye las imágenes).
6. Abre `http://localhost:8090`.

### Problema conocido en Windows + WSL
Si el proyecto vive en el sistema de archivos de WSL y Docker Desktop corre
en Windows, el servicio `frontend` (el único con bind-mount) puede fallar con
un error de `distro-services/*.sock`. No es un bug del proyecto, es una
integración de Docker Desktop. Soluciones, en orden de preferencia — están
detalladas con comandos exactos en el `README.md` del proyecto (sección
"Solución de problemas"):
1. Activar la integración WSL de tu distro en Docker Desktop.
2. Levantar `docker compose up` desde una terminal **dentro** de WSL, no
   desde PowerShell.
3. Workaround temporal sin bind-mount (copiar los estáticos a un nginx
   aparte) — solo para verificar que todo funciona mientras arreglas 1 o 2.

---

## 7. Cuando toque escalar

- **Llevarlo a un servidor/VPS**: el mismo `docker compose up -d --build`
  funciona en cualquier máquina Linux con Docker. Pon un dominio propio
  delante con un reverse proxy (nginx, Caddy o Traefik) que dé TLS
  automático, y publica solo los puertos 80/443 hacia afuera — no expongas
  `5433` (Postgres) a internet.
- **Respaldar la base de datos**: `docker compose exec db pg_dump -U
  convocatorias convocatorias > backup.sql` (prográmalo con un cron del
  sistema operativo, no del proyecto).
- **Más volumen de datos**: sube `SCRAPE_INTERVAL_MINUTES` (menos frecuente)
  o bájalo (más frecuente) según cuánto cambien las fuentes; ajusta
  `SCRAPE_KEYWORDS` para no traer más de lo que necesitas.
- **Agregar una fuente nueva**: la arquitectura es de plugin — un archivo
  nuevo en `backend/app/connectors/<fuente>.py` con una clase que hereda de
  `BaseConnector` y se auto-registra. No hay que tocar el resto del sistema.
  Requiere criterio técnico (o pedirle a un agente de IA que lo haga, ver
  sección 8) para mapear la fuente nueva al contrato de `RawConvocatoria`.
- **Más carga concurrente**: Postgres y FastAPI escalan verticalmente sin
  cambios (dale más CPU/RAM al contenedor); si el volumen crece mucho,
  considera mover Postgres a un servicio administrado (RDS, Cloud SQL,
  Supabase, etc.) y dejar `DATABASE_URL` apuntando ahí.

---

## 8. Usar un agente de IA gratuito para mantenerlo o ampliarlo

Este proyecto se construyó con **Claude Code**, el agente de codificación de
Anthropic, que también tiene una capa de uso gratuita (sujeta a límites de
uso que cambian con el tiempo — revisa el plan vigente en
[claude.com/pricing](https://claude.com/pricing) antes de asumir cuotas
específicas). Con eso, o con cualquier asistente de código con acceso a
archivos y terminal, puedes pedirle tareas como:

- "Instala este proyecto en esta PC y levántalo con Docker" — le pasas la
  carpeta y sigue exactamente los pasos de la sección 6.
- "SECOP cambió su formato y el conector ya no trae datos" — le pides que
  revise `backend/app/connectors/secop.py`, capture una respuesta real de la
  fuente y actualice el mapeo sin inventar campos.
- "Agrega una fuente nueva de convocatorias de [organismo X]" — con la URL
  pública de esa fuente, puede crear el conector siguiendo el mismo patrón
  que los cinco existentes.
- "Prepara un backup automático y un dominio con HTTPS" — puede escribir el
  script de cron y la configuración del reverse proxy de la sección 7.

Recomendación de uso responsable: pídele siempre que **verifique en vivo**
(con `curl`, `docker compose ps`, tests reales) antes de decirte que algo
"ya funciona" — es la misma regla dura que sostiene el resto del proyecto:
cero resultados inventados, todo verificado contra la realidad.

---

## 9. Mantenimiento y solución de problemas

| Síntoma | Qué revisar |
|---|---|
| El frontend no carga | `docker compose ps` → ¿`api` está `healthy`? `docker compose logs frontend` |
| No aparecen convocatorias nuevas | Panel **Fuentes** → revisa `error_mensaje` de la última ejecución de cada conector |
| Una fuente da error repetido | La fuente pudo cambiar su estructura/API — revisa `docker compose logs worker` y considera pedirle a un agente de IA que audite ese conector puntual |
| Quiero borrar todo y empezar de cero | `docker compose down -v` (irreversible — borra la base de datos) y vuelve a `docker compose up -d --build` |
| Cambié `.env` y no aplica | Reinicia los contenedores: `docker compose up -d --build` (recrea `api` y `worker` con la nueva configuración) |

---

## 10. Preguntas frecuentes

**¿Puede traer convocatorias falsas o inventadas?**
No. Es una regla dura del proyecto: todo dato ausente en la fuente queda
`null`, nunca se rellena. Cada convocatoria trae su enlace oficial para que
la verifiques tú mismo.

**¿Necesito internet para usarlo?**
Solo el `worker` necesita salir a internet para scrapear las fuentes. El
dashboard y la búsqueda funcionan contra tu base de datos local aunque no
haya internet en ese momento (mostrará lo último que se scrapeó).

**¿Corre en Mac o Linux, o solo Windows?**
Corre igual en cualquier sistema con Docker — el único detalle particular de
Windows es la integración WSL descrita en la sección 6.

**¿Cuánto tarda un scraping completo?**
Depende de cada fuente (paginación y límites de rate-limit); en la práctica,
minutos, no horas. Se ve en tiempo real en el panel **Fuentes**.

---

## 11. Glosario rápido

| Término | Significado |
|---|---|
| SECOP II | Sistema Electrónico de Contratación Pública de Colombia |
| PNUD | Programa de las Naciones Unidas para el Desarrollo (avisos de adquisiciones) |
| UNGM | United Nations Global Marketplace (fuente inactiva por ahora — requiere navegador headless) |
| RFP / EOI | Request for Proposal / Expression of Interest — tipos de convocatoria internacionales |
| RUES | Registro Único Empresarial y Social de Colombia — para verificar que una entidad exista legalmente |
| Conector | Módulo de código que sabe leer una fuente específica y traducirla al formato común del sistema |
| Dedupe | Proceso que evita guardar la misma convocatoria dos veces, usando un hash único |
