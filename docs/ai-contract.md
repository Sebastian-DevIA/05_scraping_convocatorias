# Contrato REST — capa de IA `/api/v1/ai` (NUEVO, aparte del contrato congelado)

Este documento describe **solo** los endpoints de IA. El contrato de
convocatorias/fuentes/stats/scraping (`docs/api-contract.md`) **sigue
congelado** y no cambia. Estos endpoints son una capa nueva, opcional y
**degradable**.

## Reglas duras que esta capa respeta (heredadas de `CLAUDE.md`)

- **CERO datos inventados.** La IA nunca inventa convocatorias ni datos de
  negocio. Solo: (a) traduce lenguaje natural a los filtros ya soportados por
  `docs/api-contract.md` y deja que Postgres traiga los resultados **reales**;
  (b) resume texto que **ya existe** en la BD; (c) responde dudas de uso con el
  manual real (`docs/MANUAL_USUARIO.md`) como contexto.
- **Degradación con gracia.** Si el proveedor de IA no está disponible, la app
  nunca inventa ni se rompe:
  - `/ai/buscar` cae a un filtro `q=<pregunta original>` (texto plano).
  - `/ai/convocatorias/{id}/resumen` y `/ai/soporte` devuelven un mensaje claro
    de "servicio de IA no disponible", con `ia_disponible: false`.
- Toda respuesta de IA debe quedar **marcada como generada por IA** en el
  frontend.

## Proveedores (backend)

Failover configurable por `AI_PROVIDER_ORDER` (default `ollama,openrouter`):

1. **Ollama** local (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`) — dentro de la red de
   compose, sin puerto publicado.
2. **OpenRouter** (`OPENROUTER_API_KEY`, `OPENROUTER_MODEL`) — respaldo remoto,
   API compatible con OpenAI. La key vive **solo en el backend**; nunca se
   expone al frontend ni se loguea.

Si `AI_ENABLED=false`, todos los endpoints responden el fallback sin tocar red.

## Límites

- `pregunta`: 1..500 caracteres (fuera de rango → `422`).
- Rate-limit: 20 peticiones / 60 s por IP sobre `/ai/*` (exceso → `429`).

---

## `POST /api/v1/ai/buscar`

Búsqueda en lenguaje natural. La IA propone filtros; se reutiliza el servicio de
listado real. **Siempre responde 200.**

**Request**
```json
{ "pregunta": "fondos de innovación abiertos en Antioquia" }
```

**200 OK**
```json
{
  "filtros_interpretados": { "q": "innovación", "tipo": "fondo", "estado": "abierta", "departamento": "Antioquia" },
  "ia_disponible": true,
  "fallback": false,
  "resultado": { "items": [ ... ], "total": 12, "page": 1, "page_size": 20 }
}
```
- `ia_disponible`: `true` si la interpretación la hizo la IA; `false` si la IA
  no estaba disponible.
- `fallback`: `true` si se usó búsqueda por texto plano (`q=<pregunta>`) porque
  la IA no estaba disponible **o** su salida no fue un JSON de filtros válido.
- `resultado`: exactamente el envoltorio paginado de `GET /convocatorias`
  (mismos `items`, datos **reales** de la BD).

---

## `POST /api/v1/ai/convocatorias/{id}/resumen`

Resume la descripción/requisitos **reales** de una convocatoria existente.

- `404` si la convocatoria no existe (`{ "detail": "Convocatoria no encontrada" }`).

**200 OK (IA disponible)**
```json
{ "resumen": "La convocatoria busca...", "ia_disponible": true, "mensaje": null }
```

**200 OK (IA no disponible — degradado)**
```json
{ "resumen": null, "ia_disponible": false, "mensaje": "El servicio de IA no está disponible ahora mismo..." }
```
El frontend muestra el resumen etiquetado como generado por IA, **sin ocultar**
la descripción/requisitos originales.

---

## `POST /api/v1/ai/soporte`

Responde dudas de uso de la herramienta con el manual real como contexto.

**Request**
```json
{ "pregunta": "¿cómo disparo un scraping manual?" }
```

**200 OK (IA disponible)**
```json
{ "respuesta": "Usa el botón 'Actualizar ahora'...", "ia_disponible": true }
```

**200 OK (IA no disponible — degradado)**
```json
{ "respuesta": "El servicio de IA no está disponible ahora mismo...", "ia_disponible": false }
```
