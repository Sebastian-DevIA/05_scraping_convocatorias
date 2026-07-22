# Contrato REST — `/api/v1` (CONGELADO en Fase 0)

Este documento es la **fuente de verdad** de la API. El frontend (agente F) trabaja
SOLO contra este contrato. El agente E (API) implementa exactamente estas formas.
Si algo debe cambiar, se cambia aquí primero y se avisa.

## Convenciones globales

- **Prefijo**: todas las rutas cuelgan de `/api/v1`.
- **Fechas**: ISO 8601 en **UTC**, con offset explícito. Ej: `"2026-07-21T14:30:00+00:00"`.
  Si un valor de fecha no existe o no se pudo parsear en la fuente → `null` (nunca inventado).
- **Montos**: `monto` es un **string decimal** (para no perder precisión), ej. `"150000000.00"`, o `null`.
- **Paginación**: envoltorio uniforme `{ "items": [...], "total": <int>, "page": <int>, "page_size": <int> }`.
  `page` es base 1. `page_size` por defecto 20, máximo 100.
- **Errores**: formato FastAPI estándar.
  - `404` → `{ "detail": "..." }`
  - `422` (validación de query/params) → `{ "detail": [ { "loc": [...], "msg": "...", "type": "..." } ] }`
- **Enums canónicos**:
  - `estado` de convocatoria: `abierta | cerrada | adjudicada | vencida | desconocido`.
  - `tipo` de convocatoria: `licitacion | subvencion | fondo | rfp | eoi | otro`.
  - `tipo` de fuente: `api | html | js`.
  - `trigger` de ejecución: `cron | manual`.
  - `estado` de ejecución: `en_curso | ok | parcial | error`.

> Todos los cuerpos JSON de abajo son **ejemplos de documentación** (valores ilustrativos),
> no datos reales almacenados.

---

## `GET /api/v1/health`

Estado del servicio y chequeo de BD. No paginado. Sin auth.

**200 OK**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "database": "ok",
  "time": "2026-07-21T14:30:00+00:00"
}
```
- `status`: `"ok"` si la BD responde, `"degraded"` si no.
- `database`: `"ok" | "error"`.

---

## `GET /api/v1/convocatorias`

Listado paginado con filtros.

### Query params (todos opcionales)

| Param | Tipo | Descripción |
|---|---|---|
| `q` | string | Búsqueda full-text (tsquery español) sobre título + descripción. |
| `fuente` | string | Código de fuente (`secop`, `pnud`, ...). |
| `estado` | string | Estado canónico. |
| `tipo` | string | Tipo canónico. |
| `departamento` | string | Departamento exacto. |
| `fecha_publicacion_desde` | date (`YYYY-MM-DD`) | Límite inferior de `fecha_publicacion`. |
| `fecha_publicacion_hasta` | date | Límite superior de `fecha_publicacion`. |
| `fecha_cierre_desde` | date | Límite inferior de `fecha_cierre`. |
| `fecha_cierre_hasta` | date | Límite superior de `fecha_cierre`. |
| `monto_min` | number | Monto mínimo. |
| `monto_max` | number | Monto máximo. |
| `orden` | string | Campo de orden: `fecha_publicacion` (default), `fecha_cierre`, `monto`, `ultima_vez_visto`. Prefijo `-` = descendente. Default `-fecha_publicacion`. |
| `page` | int ≥ 1 | Página (base 1). Default 1. |
| `page_size` | int 1..100 | Tamaño de página. Default 20. |

### 200 OK — `ConvocatoriaPageResponse`
```json
{
  "items": [
    {
      "id": 1284,
      "id_externo": "CO1.BDOS.5551234",
      "fuente_id": 1,
      "fuente_codigo": "secop",
      "fuente_nombre": "SECOP II (Colombia Compra Eficiente)",
      "titulo": "Implementación de solución de inclusión digital para población vulnerable",
      "descripcion": "Adquisición e implementación de plataforma tecnológica...",
      "entidad": "Alcaldía de Medellín",
      "tipo": "licitacion",
      "modalidad": "Licitación Pública",
      "estado": "abierta",
      "monto": "850000000.00",
      "moneda": "COP",
      "departamento": "Antioquia",
      "ciudad": "Medellín",
      "pais": "Colombia",
      "fecha_publicacion": "2026-07-10T05:00:00+00:00",
      "fecha_apertura": "2026-07-12T05:00:00+00:00",
      "fecha_cierre": "2026-07-28T05:00:00+00:00",
      "url_original": "https://community.secop.gov.co/Public/Tendering/...",
      "keywords_match": ["inclusión digital", "población vulnerable", "tecnología"],
      "primera_vez_visto": "2026-07-11T06:00:00+00:00",
      "ultima_vez_visto": "2026-07-21T06:00:00+00:00",
      "creado_en": "2026-07-11T06:00:00+00:00",
      "actualizado_en": "2026-07-21T06:00:00+00:00"
    }
  ],
  "total": 137,
  "page": 1,
  "page_size": 20
}
```

---

## `GET /api/v1/convocatorias/{id}`

Detalle de una convocatoria. Incluye `requisitos`.

### Query params
| Param | Tipo | Descripción |
|---|---|---|
| `include_raw` | bool | Si `true`, incluye `raw` (payload íntegro de la fuente). Default `false`. |

### 200 OK — `ConvocatoriaDetailResponse`
Igual que un item de la lista, **más**:
```json
{
  "id": 1284,
  "...": "(todos los campos de ConvocatoriaResponse)",
  "requisitos": "1. Experiencia mínima de 3 años...\n2. Certificación ISO...",
  "raw": null
}
```
- `requisitos`: `string | null`.
- `raw`: `object | null`. Es `null` salvo que se pida `?include_raw=true`.

### 404 Not Found
```json
{ "detail": "Convocatoria no encontrada" }
```

---

## `GET /api/v1/stats`

Métricas agregadas para el dashboard. No paginado.

### 200 OK — `StatsResponse`
```json
{
  "total": 137,
  "abiertas": 58,
  "nuevas_7d": 12,
  "cierran_7d": 9,
  "por_fuente": [
    { "codigo": "secop", "nombre": "SECOP II (Colombia Compra Eficiente)", "total": 110 },
    { "codigo": "pnud", "nombre": "PNUD - Procurement Notices", "total": 15 }
  ],
  "por_estado": [
    { "clave": "abierta", "total": 58 },
    { "clave": "cerrada", "total": 61 },
    { "clave": "vencida", "total": 18 }
  ],
  "por_departamento": [
    { "clave": "Antioquia", "total": 24 },
    { "clave": "Bogotá D.C.", "total": 19 }
  ]
}
```
- `nuevas_7d`: convocatorias con `primera_vez_visto` en los últimos 7 días.
- `cierran_7d`: convocatorias `abierta` cuyo `fecha_cierre` cae en los próximos 7 días.

---

## `GET /api/v1/fuentes`

Todas las fuentes con su **última ejecución embebida** (salud del conector).

### 200 OK — `FuenteListResponse`
```json
{
  "items": [
    {
      "id": 1,
      "codigo": "secop",
      "nombre": "SECOP II (Colombia Compra Eficiente)",
      "url_base": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
      "tipo": "api",
      "activa": true,
      "config": {
        "keywords": ["tecnología", "TIC", "inclusión digital"],
        "max_paginas": 20,
        "rate_limit_seconds": 1.0
      },
      "creado_en": "2026-07-11T06:00:00+00:00",
      "actualizado_en": "2026-07-21T06:00:00+00:00",
      "ultima_ejecucion": {
        "id": 342,
        "fuente_id": 1,
        "trigger": "cron",
        "inicio": "2026-07-21T06:00:00+00:00",
        "fin": "2026-07-21T06:02:14+00:00",
        "estado": "ok",
        "items_obtenidos": 480,
        "items_nuevos": 12,
        "items_actualizados": 5,
        "items_marcados_cerrados": 0,
        "error_mensaje": null
      }
    },
    {
      "id": 5,
      "codigo": "ungm",
      "nombre": "UNGM (ONU) - United Nations Global Marketplace",
      "url_base": "https://www.ungm.org/Public/Notice",
      "tipo": "js",
      "activa": false,
      "config": { "keywords": [], "max_paginas": 5, "rate_limit_seconds": 2.0 },
      "creado_en": "2026-07-11T06:00:00+00:00",
      "actualizado_en": "2026-07-11T06:00:00+00:00",
      "ultima_ejecucion": null
    }
  ],
  "total": 5
}
```
- `ultima_ejecucion`: `EjecucionResponse | null` (null si la fuente nunca corrió).

---

## `GET /api/v1/fuentes/{codigo}/ejecuciones`

Historial de ejecuciones de una fuente (más recientes primero).

### Query params
| Param | Tipo | Descripción |
|---|---|---|
| `limit` | int 1..100 | Máximo de ejecuciones a devolver. Default 20. |

### 200 OK — `EjecucionListResponse`
```json
{
  "items": [
    {
      "id": 342,
      "fuente_id": 1,
      "trigger": "cron",
      "inicio": "2026-07-21T06:00:00+00:00",
      "fin": "2026-07-21T06:02:14+00:00",
      "estado": "ok",
      "items_obtenidos": 480,
      "items_nuevos": 12,
      "items_actualizados": 5,
      "items_marcados_cerrados": 0,
      "error_mensaje": null
    }
  ],
  "total": 87
}
```

### 404 Not Found
```json
{ "detail": "Fuente no encontrada" }
```

---

## `POST /api/v1/scraping/run`

Dispara una corrida manual (todas las fuentes o una). Responde **202** de inmediato
(el trabajo corre en segundo plano, protegido por `pg_advisory_lock`). El frontend
hace polling a `GET /api/v1/fuentes` hasta que las ejecuciones dejen de estar `en_curso`.

### Query params
| Param | Tipo | Descripción |
|---|---|---|
| `fuente` | string | Código de fuente a ejecutar. Si se omite → todas las activas. |

### 202 Accepted
```json
{
  "status": "accepted",
  "trigger": "manual",
  "fuente": "secop",
  "detail": "Scraping encolado."
}
```
- `fuente`: el código solicitado, o `null` si se ejecutan todas.

### 404 Not Found (si `fuente` no existe)
```json
{ "detail": "Fuente no encontrada" }
```

### 409 Conflict (opcional, si ya hay una corrida en curso y no se puede encolar)
```json
{ "detail": "Ya hay un scraping en curso." }
```
