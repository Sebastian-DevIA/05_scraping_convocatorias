#!/usr/bin/env bash
# Smoke test end-to-end del sistema de convocatorias.
#
# Uso (desde la raíz del repo, en WSL, con el stack levantado):
#   bash scripts/smoke_e2e.sh
#
# Verifica la cadena completa: API viva -> frontend sirviendo -> run de
# scraping real -> ejecuciones terminadas -> datos REALES en BD (fechas
# recientes y url_original presentes) -> stats para el dashboard.
set -euo pipefail

API="${API_URL:-http://localhost:8100/api/v1}"
FRONT="${FRONTEND_URL:-http://localhost:8090}"
POLL_TIMEOUT="${POLL_TIMEOUT:-600}" # segundos máximos esperando el run
POLL_INTERVAL=5

fail() { echo "❌ $1" >&2; exit 1; }
ok()   { echo "✅ $1"; }

command -v python3 >/dev/null || fail "python3 no está disponible"
command -v curl >/dev/null || fail "curl no está disponible"

# --- 1. Health ---------------------------------------------------------------
HEALTH=$(curl -sf "$API/health") || fail "API no responde en $API/health"
echo "$HEALTH" | python3 -c '
import json, sys
d = json.load(sys.stdin)
assert d.get("status") == "ok" and d.get("database") == "ok", d
' || fail "health degradado: $HEALTH"
ok "health: API y BD ok"

# --- 2. Frontend -------------------------------------------------------------
curl -sf -o /dev/null "$FRONT/" || fail "frontend no responde en $FRONT"
ok "frontend sirviendo en $FRONT"

# --- 3. Disparar scraping manual (todas las fuentes activas) ------------------
HTTP=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$API/scraping/run")
case "$HTTP" in
  202) ok "scraping/run encolado (202)" ;;
  409) ok "ya había un scraping en curso (409); se espera a que termine" ;;
  *)   fail "POST /scraping/run devolvió HTTP $HTTP" ;;
esac

# --- 4. Esperar a que no queden ejecuciones en_curso --------------------------
echo "⏳ esperando fin del scraping (máx ${POLL_TIMEOUT}s)..."
SECONDS_WAITED=0
sleep 3
while :; do
  EN_CURSO=$(curl -sf "$API/fuentes" | python3 -c '
import json, sys
d = json.load(sys.stdin)
en_curso = [
    f["codigo"] for f in d.get("items", [])
    if (f.get("ultima_ejecucion") or {}).get("estado") == "en_curso"
]
print(",".join(en_curso))
')
  [ -z "$EN_CURSO" ] && break
  SECONDS_WAITED=$((SECONDS_WAITED + POLL_INTERVAL))
  [ "$SECONDS_WAITED" -ge "$POLL_TIMEOUT" ] && fail "timeout esperando fuentes: $EN_CURSO"
  sleep "$POLL_INTERVAL"
done
ok "scraping terminado (sin ejecuciones en_curso)"

# --- 5. Salud de ejecuciones por fuente ---------------------------------------
curl -sf "$API/fuentes" | python3 -c '
import json, sys
d = json.load(sys.stdin)
fallo = False
for f in d.get("items", []):
    if not f.get("activa"):
        print(f"   · {f['"'"'codigo'"'"']}: inactiva (esperado)")
        continue
    ej = f.get("ultima_ejecucion")
    if not ej:
        print(f"   · {f['"'"'codigo'"'"']}: SIN ejecuciones")
        fallo = True
        continue
    linea = (
        f"   · {f['"'"'codigo'"'"']}: {ej['"'"'estado'"'"']} "
        f"(obtenidos={ej['"'"'items_obtenidos'"'"']}, nuevos={ej['"'"'items_nuevos'"'"']}, "
        f"actualizados={ej['"'"'items_actualizados'"'"']})"
    )
    print(linea)
    if ej["estado"] == "error":
        print(f"     error: {ej.get('"'"'error_mensaje'"'"')}")
sys.exit(1 if fallo else 0)
' || fail "hay fuentes activas sin ejecuciones registradas"
ok "todas las fuentes activas tienen ejecución registrada"

# --- 6. Datos reales y verificables (regla dura: nada inventado) ---------------
STATS=$(curl -sf "$API/stats") || fail "GET /stats falló"
TOTAL=$(echo "$STATS" | python3 -c 'import json,sys; print(json.load(sys.stdin)["total"])')
[ "$TOTAL" -gt 0 ] || fail "no hay convocatorias en BD tras el run (total=0)"
ok "stats: $TOTAL convocatorias en BD"

SQL_CHECK=$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tA -F"|" -c "
SELECT
  (SELECT count(*) FROM convocatorias),
  (SELECT count(*) FROM convocatorias WHERE url_original IS NULL OR url_original = '"''"'),
  (SELECT count(*) FROM convocatorias WHERE fecha_publicacion >= now() - interval '"'"'18 months'"'"')
;"')
TOTAL_DB=$(echo "$SQL_CHECK" | cut -d'|' -f1)
SIN_URL=$(echo "$SQL_CHECK" | cut -d'|' -f2)
RECIENTES=$(echo "$SQL_CHECK" | cut -d'|' -f3)
[ "$SIN_URL" = "0" ] || fail "$SIN_URL convocatorias sin url_original (violación de regla dura)"
[ "$RECIENTES" -gt 0 ] || fail "ninguna convocatoria con fecha_publicacion reciente (¿datos no reales?)"
ok "BD: $TOTAL_DB filas, todas con url_original, $RECIENTES con fecha_publicacion reciente"

echo
echo "── Muestra (verificar manualmente que las URLs abren) ──"
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "
SELECT left(titulo, 60) AS titulo, estado, to_char(fecha_publicacion, '"'"'YYYY-MM-DD'"'"') AS publicada, left(url_original, 70) AS url
FROM convocatorias ORDER BY fecha_publicacion DESC NULLS LAST LIMIT 5;"'

echo
ok "SMOKE E2E COMPLETO 🎉"
