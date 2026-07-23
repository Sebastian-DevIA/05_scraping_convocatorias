// SPA de busqueda de convocatorias. Trabaja SOLO contra docs/api-contract.md.
// Sin dependencias externas: fetch + hash-router. Foco de negocio: encontrar
// convocatorias reales y VALIDAR la entidad emisora antes de invertir tiempo.

const API = "/api/v1";

const ESTADOS = ["abierta", "cerrada", "adjudicada", "vencida", "desconocido"];
const TIPOS = ["licitacion", "subvencion", "fondo", "rfp", "eoi", "otro"];
const ORDENES = [
  ["-fecha_publicacion", "Publicacion (recientes primero)"],
  ["fecha_publicacion", "Publicacion (antiguas primero)"],
  ["fecha_cierre", "Cierre (proximas primero)"],
  ["-fecha_cierre", "Cierre (lejanas primero)"],
  ["-monto", "Monto (mayor primero)"],
  ["monto", "Monto (menor primero)"],
  ["-ultima_vez_visto", "Visto por ultima vez"],
];

const FILTER_KEYS = [
  "q", "fuente", "estado", "tipo", "departamento", "apto_fundaciones_nuevas",
  "fecha_publicacion_desde", "fecha_publicacion_hasta",
  "fecha_cierre_desde", "fecha_cierre_hasta",
  "monto_min", "monto_max", "orden",
];

// `selected`: ids (como string) de convocatorias marcadas "para participar".
// Persiste entre páginas y vistas para poder exportarlas juntas a Excel.
const state = { page: 1, pageSize: 20, filters: emptyFilters(), fuentesCache: null, selected: new Set() };

function emptyFilters() {
  return {
    q: "", fuente: "", estado: "", tipo: "", departamento: "", apto_fundaciones_nuevas: "",
    fecha_publicacion_desde: "", fecha_publicacion_hasta: "",
    fecha_cierre_desde: "", fecha_cierre_hasta: "",
    monto_min: "", monto_max: "", orden: "-fecha_publicacion",
  };
}

const app = document.querySelector("#app");
const refreshBtn = document.querySelector("#refreshBtn");
const dialog = document.querySelector("#detailDialog");
const detailTitle = document.querySelector("#detailTitle");
const detailBody = document.querySelector("#detailBody");
const toastEl = document.querySelector("#toast");
document.querySelector("#closeDialog").addEventListener("click", () => dialog.close());
dialog.addEventListener("click", (ev) => { if (ev.target === dialog) dialog.close(); });

async function api(path, options) {
  const res = await fetch(API + path, options);
  if (!res.ok) {
    let detail = res.status + " " + res.statusText;
    try {
      const body = await res.json();
      if (body && body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (_) { /* sin cuerpo JSON */ }
    throw new Error(detail);
  }
  return res.json();
}

async function fuentes(force) {
  if (!state.fuentesCache || force) state.fuentesCache = await api("/fuentes");
  return state.fuentesCache;
}

const nfCOP = new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
const nfNum = new Intl.NumberFormat("es-CO", { maximumFractionDigits: 0 });

function money(value, moneda) {
  if (value === null || value === undefined || value === "") return "Sin monto publicado";
  const n = Number(value);
  if (Number.isNaN(n)) return "Sin monto publicado";
  if (!moneda || moneda === "COP") return nfCOP.format(n);
  return nfNum.format(n) + " " + moneda;
}

function fdate(value) {
  if (!value) return "Sin fecha";
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium" }).format(new Date(value));
}
function fdatetime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("es-CO", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
function daysToClose(value) {
  if (!value) return null;
  return Math.ceil((new Date(value).getTime() - Date.now()) / 86400000);
}
function badge(value, cls) {
  return '<span class="badge ' + (cls || value || "") + '">' + escapeHtml(value || "sin dato") + "</span>";
}
function escapeHtml(value) {
  const map = { "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "\x27": "&#039;" };
  return String(value == null ? "" : value).replace(/[&<>"\x27]/g, (ch) => map[ch]);
}
function escapeAttr(value) { return escapeHtml(value).replace(/"/g, "&quot;"); }
// Escapa y preserva saltos de linea (para descripcion/requisitos multilinea).
function escapeMultiline(value) { return escapeHtml(value).replace(/\n/g, "<br>"); }

function toast(msg, kind) {
  toastEl.textContent = msg;
  toastEl.className = "toast show " + (kind || "");
  toastEl.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(() => { toastEl.hidden = true; }, 4500);
}
function setActiveNav(name) {
  document.querySelectorAll("nav [data-nav]").forEach((a) => a.classList.toggle("active", a.dataset.nav === name));
}
function scrollTop() { window.scrollTo({ top: 0, behavior: "smooth" }); }

function buildParams() {
  const p = new URLSearchParams({ page: state.page, page_size: state.pageSize });
  for (const [k, v] of Object.entries(state.filters)) {
    if (v === "" || v === null || v === undefined) continue;
    if (k === "orden" && v === "-fecha_publicacion") continue;
    p.set(k, v);
  }
  return p.toString();
}

// ---------------------------------------------------------------- DASHBOARD
async function renderDashboard() {
  setActiveNav("dashboard");
  app.innerHTML = '<p class="muted loading">Cargando panel...</p>';
  const [stats, soon] = await Promise.all([
    api("/stats"),
    api("/convocatorias?estado=abierta&orden=fecha_cierre&page_size=8"),
  ]);

  const barras = (arr, keyName) => {
    if (!arr.length) return '<p class="muted">Sin datos.</p>';
    const max = Math.max.apply(null, arr.map((x) => x.total)) || 1;
    return arr.slice(0, 8).map((x) =>
      '<div class="bar-row"><span class="bar-label" title="' + escapeAttr(x[keyName]) + '">' + escapeHtml(x[keyName]) +
      '</span><span class="bar-track"><span class="bar-fill" style="width:' + Math.max(4, (x.total / max) * 100) +
      '%"></span></span><span class="bar-val">' + nfNum.format(x.total) + "</span></div>"
    ).join("");
  };

  app.innerHTML =
    '<section class="grid kpis">' +
      '<div class="card kpi"><span>Total convocatorias</span><strong>' + nfNum.format(stats.total) + "</strong></div>" +
      '<div class="card kpi ok"><span>Abiertas</span><strong>' + nfNum.format(stats.abiertas) + "</strong></div>" +
      '<div class="card kpi"><span>Nuevas (7 dias)</span><strong>' + nfNum.format(stats.nuevas_7d) + "</strong></div>" +
      '<div class="card kpi warn"><span>Cierran (7 dias)</span><strong>' + nfNum.format(stats.cierran_7d) + "</strong></div>" +
    "</section>" +
    '<section class="grid cols-3" style="margin-top:16px">' +
      '<div class="card"><h3>Por fuente</h3><div class="bars">' + barras(stats.por_fuente, "nombre") + "</div></div>" +
      '<div class="card"><h3>Por estado</h3><div class="bars">' + barras(stats.por_estado, "clave") + "</div></div>" +
      '<div class="card"><h3>Por departamento</h3><div class="bars">' + barras(stats.por_departamento, "clave") + "</div></div>" +
    "</section>" +
    '<section class="card" style="margin-top:16px">' +
      '<div class="section-head"><h3>Cierran pronto (abiertas)</h3>' +
      '<a class="link" href="#/convocatorias?estado=abierta&orden=fecha_cierre">Ver todas &rarr;</a></div>' +
      '<div class="results">' + (soon.items.map(cardConvocatoria).join("") || '<p class="muted">Sin convocatorias abiertas con fecha de cierre.</p>') + "</div>" +
    "</section>";
  bindCards();
}

// ------------------------------------------------------------------ BUSCAR
async function renderConvocatorias() {
  setActiveNav("convocatorias");
  app.innerHTML = '<p class="muted loading">Buscando...</p>';
  const [data, fus] = await Promise.all([api("/convocatorias?" + buildParams()), fuentes()]);

  const f = state.filters;
  const activos = FILTER_KEYS.filter((k) => k !== "orden" && f[k]).length;
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  const optsOrden = ORDENES.map(([v, t]) => '<option value="' + v + '"' + (f.orden === v ? " selected" : "") + ">" + t + "</option>").join("");
  const optsFuente = fus.items.map((x) => '<option value="' + escapeAttr(x.codigo) + '"' + (f.fuente === x.codigo ? " selected" : "") + ">" + escapeHtml(x.nombre) + "</option>").join("");
  const optsEstado = ESTADOS.map((v) => "<option" + (f.estado === v ? " selected" : "") + ">" + v + "</option>").join("");
  const optsTipo = TIPOS.map((v) => "<option" + (f.tipo === v ? " selected" : "") + ">" + v + "</option>").join("");

  let html = '<form id="filters" class="card filters" autocomplete="off">';
  html += '<div class="filter-row wide">';
  html += '<label>Palabra clave<input id="f_q" placeholder="Ej. software, inclusion digital, energia..." value="' + escapeAttr(f.q) + '" /></label>';
  html += '<label>Orden<select id="f_orden">' + optsOrden + "</select></label>";
  html += "</div>";
  html += '<div class="filter-row">';
  html += '<label>Fuente<select id="f_fuente"><option value="">Todas</option>' + optsFuente + "</select></label>";
  html += '<label>Estado<select id="f_estado"><option value="">Todos</option>' + optsEstado + "</select></label>";
  html += '<label>Tipo<select id="f_tipo"><option value="">Todos</option>' + optsTipo + "</select></label>";
  html += '<label>Departamento<input id="f_departamento" placeholder="Ej. Antioquia" value="' + escapeAttr(f.departamento) + '" /></label>';
  html += "</div>";
  html += '<div class="filter-row">';
  html += '<label class="check" title="Convocatorias marcadas (heuristica) como accesibles para fundaciones nuevas, primerizas o sin trayectoria previa. Verifica siempre en la publicacion oficial.">';
  html += '<input type="checkbox" id="f_apto"' + (f.apto_fundaciones_nuevas === "true" ? " checked" : "") + " />";
  html += "<span>Solo aptas para fundaciones nuevas / primerizas</span></label>";
  html += "</div>";
  html += '<div class="filter-row">';
  html += '<label>Publicada desde<input type="date" id="f_fpd" value="' + escapeAttr(f.fecha_publicacion_desde) + '" /></label>';
  html += '<label>Publicada hasta<input type="date" id="f_fph" value="' + escapeAttr(f.fecha_publicacion_hasta) + '" /></label>';
  html += '<label>Cierra desde<input type="date" id="f_fcd" value="' + escapeAttr(f.fecha_cierre_desde) + '" /></label>';
  html += '<label>Cierra hasta<input type="date" id="f_fch" value="' + escapeAttr(f.fecha_cierre_hasta) + '" /></label>';
  html += "</div>";
  html += '<div class="filter-row">';
  html += '<label>Monto minimo<input type="number" min="0" step="1000" id="f_mmin" placeholder="0" value="' + escapeAttr(f.monto_min) + '" /></label>';
  html += '<label>Monto maximo<input type="number" min="0" step="1000" id="f_mmax" placeholder="Sin limite" value="' + escapeAttr(f.monto_max) + '" /></label>';
  html += '<div class="filter-actions"><button type="submit" class="primary">Buscar</button><button type="button" id="clearFilters">Limpiar</button></div>';
  html += "</div></form>";
  html += '<div class="results-head"><span class="muted">' + nfNum.format(data.total) + " resultado(s)" + (activos ? " &middot; " + activos + " filtro(s) activo(s)" : "");
  html += '</span><span class="muted">Pagina ' + data.page + " de " + totalPages + "</span></div>";
  const cards = data.items.map(cardConvocatoria).join("") || '<div class="card"><p class="muted">No hay convocatorias para estos filtros. Prueba ampliar el rango o quitar filtros.</p></div>';
  html += '<div class="results">' + cards + "</div>";
  html += '<div class="pager"><button id="prev"' + (data.page <= 1 ? " disabled" : "") + ">&larr; Anterior</button>";
  html += '<span class="muted">' + nfNum.format(data.total) + ' resultados</span>';
  html += '<button id="next"' + (data.page >= totalPages ? " disabled" : "") + ">Siguiente &rarr;</button></div>";
  app.innerHTML = html;

  document.querySelector("#filters").addEventListener("submit", (ev) => { ev.preventDefault(); applyFilters(); });
  document.querySelector("#clearFilters").addEventListener("click", () => {
    state.filters = emptyFilters(); state.page = 1; location.hash = "#/convocatorias"; renderConvocatorias();
  });
  document.querySelector("#prev").addEventListener("click", () => { if (state.page > 1) { state.page--; renderConvocatorias(); scrollTop(); } });
  document.querySelector("#next").addEventListener("click", () => { state.page++; renderConvocatorias(); scrollTop(); });
  bindCards();
}

function applyFilters() {
  const g = (id) => (document.querySelector(id) ? document.querySelector(id).value : "").trim();
  const apto = document.querySelector("#f_apto");
  state.filters = {
    q: g("#f_q"), fuente: g("#f_fuente"), estado: g("#f_estado"), tipo: g("#f_tipo"), departamento: g("#f_departamento"),
    apto_fundaciones_nuevas: apto && apto.checked ? "true" : "",
    fecha_publicacion_desde: g("#f_fpd"), fecha_publicacion_hasta: g("#f_fph"),
    fecha_cierre_desde: g("#f_fcd"), fecha_cierre_hasta: g("#f_fch"),
    monto_min: g("#f_mmin"), monto_max: g("#f_mmax"), orden: g("#f_orden") || "-fecha_publicacion",
  };
  state.page = 1;
  renderConvocatorias();
}

function cardConvocatoria(c) {
  const d = daysToClose(c.fecha_cierre);
  let cierreTag = "";
  if (d !== null) {
    const cls = d < 0 ? "vencida" : d <= 7 ? "warn" : "muted";
    const txt = d < 0 ? "Cerro hace " + Math.abs(d) + " d" : d === 0 ? "Cierra hoy" : "Cierra en " + d + " d";
    cierreTag = '<span class="pill ' + cls + '">' + txt + "</span>";
  }
  const loc = [c.ciudad, c.departamento, c.pais].filter(Boolean).join(", ") || "Ubicacion no informada";
  const kws = (c.keywords_match || []).slice(0, 5).map((k) => '<span class="kw">' + escapeHtml(k) + "</span>").join("");
  const aptoBadge = c.apto_fundaciones_nuevas ? ' <span class="badge apto" title="Marcada (heuristica) como accesible para fundaciones nuevas o primerizas. Verifica en la publicacion oficial.">Fundaciones nuevas</span>' : "";
  let h = '<article class="card conv">';
  h += '<div class="conv-top"><div class="conv-badges">' + badge(c.estado) + ' <span class="badge fuente">' + escapeHtml(c.fuente_codigo) + "</span> " + badge(c.tipo, "tipo") + aptoBadge + "</div>" + cierreTag + "</div>";
  h += '<h3 class="conv-title">' + escapeHtml(c.titulo) + "</h3>";
  h += '<div class="entidad-block" title="Organizacion que publica esta convocatoria">';
  h += '<span class="entidad-label">Entidad emisora</span>';
  h += '<span class="entidad-name">' + escapeHtml(c.entidad || "No informada por la fuente") + "</span>";
  h += '<span class="entidad-loc">' + escapeHtml(loc) + "</span></div>";
  h += '<div class="conv-meta"><span><b>Monto</b> ' + escapeHtml(money(c.monto, c.moneda)) + "</span>";
  h += "<span><b>Publicada</b> " + fdate(c.fecha_publicacion) + "</span>";
  h += "<span><b>Cierre</b> " + fdate(c.fecha_cierre) + "</span></div>";
  h += kws ? '<div class="kws">' + kws + "</div>" : "";
  const sel = state.selected.has(String(c.id));
  h += '<div class="conv-actions">';
  h += '<label class="participar" title="Selecciona esta convocatoria para incluirla en la descarga a Excel"><input type="checkbox" data-select="' + c.id + '"' + (sel ? " checked" : "") + ' /> <span>Participar</span></label>';
  h += '<button class="ghost" data-detail="' + c.id + '">Ver ficha y validar</button>';
  h += '<a class="verify" href="' + escapeAttr(c.url_original) + '" target="_blank" rel="noopener noreferrer">Ver publicacion oficial y verificar entidad &nearr;</a></div>';
  h += "</article>";
  return h;
}

// ------------------------------------------------------------------ FUENTES
async function renderFuentes() {
  setActiveNav("fuentes");
  app.innerHTML = '<p class="muted loading">Cargando fuentes...</p>';
  const data = await fuentes(true);
  app.innerHTML =
    '<div class="results-head"><span class="muted">' + data.total + " fuentes configuradas &middot; salud del ultimo scraping</span></div>" +
    '<section class="grid source-list">' + data.items.map(cardFuente).join("") + "</section>" +
    '<div id="ejecHist"></div>';

  document.querySelectorAll("[data-run]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const cod = btn.dataset.run;
      btn.disabled = true; btn.textContent = "Encolando...";
      try {
        await api("/scraping/run?fuente=" + encodeURIComponent(cod), { method: "POST" });
        toast("Scraping de " + cod + " encolado. Actualizando estado...", "ok");
        pollFuentes();
      } catch (e) {
        toast("No se pudo ejecutar " + cod + ": " + e.message, "error");
        btn.disabled = false; btn.textContent = "Ejecutar fuente";
      }
    });
  });
  document.querySelectorAll("[data-hist]").forEach((btn) => btn.addEventListener("click", () => showHistorial(btn.dataset.hist)));
}

function cardFuente(f) {
  const e = f.ultima_ejecucion;
  const estadoTag = e ? badge(e.estado) : badge(f.activa ? "sin ejecucion" : "inactiva", f.activa ? "muted" : "vencida");
  const kws = ((f.config && f.config.keywords) || []).slice(0, 6).map((k) => '<span class="kw">' + escapeHtml(k) + "</span>").join("");
  let h = '<article class="card source ' + (f.activa ? "" : "off") + '">';
  h += '<div class="conv-top"><h3>' + escapeHtml(f.nombre) + "</h3>" + estadoTag + "</div>";
  h += '<p class="muted mono">' + escapeHtml(f.codigo) + " &middot; tipo " + escapeHtml(f.tipo) + " &middot; " + (f.activa ? "activa" : "inactiva") + "</p>";
  h += '<p class="muted url">' + escapeHtml(f.url_base) + "</p>";
  if (e) {
    h += '<div class="exec-grid">';
    h += "<div><span>Obtenidos</span><b>" + nfNum.format(e.items_obtenidos || 0) + "</b></div>";
    h += "<div><span>Nuevos</span><b>" + nfNum.format(e.items_nuevos || 0) + "</b></div>";
    h += "<div><span>Actualizados</span><b>" + nfNum.format(e.items_actualizados || 0) + "</b></div>";
    h += "<div><span>Cerrados</span><b>" + nfNum.format(e.items_marcados_cerrados || 0) + "</b></div>";
    h += "</div>";
    h += '<p class="muted small">Ultima corrida: ' + fdatetime(e.inicio) + " &rarr; " + fdatetime(e.fin) + " (" + escapeHtml(e.trigger) + ")</p>";
    h += e.error_mensaje ? '<p class="err-msg">&#9888; ' + escapeHtml(e.error_mensaje) + "</p>" : "";
  } else {
    h += '<p class="muted small">Sin ejecuciones registradas.</p>';
  }
  h += kws ? '<div class="kws">' + kws + "</div>" : "";
  h += '<div class="conv-actions"><button data-run="' + escapeAttr(f.codigo) + '"' + (f.activa ? "" : " disabled") + ">Ejecutar fuente</button>";
  h += '<button class="ghost" data-hist="' + escapeAttr(f.codigo) + '">Historial</button></div>';
  h += "</article>";
  return h;
}

async function showHistorial(codigo) {
  const cont = document.querySelector("#ejecHist");
  cont.innerHTML = '<p class="muted loading">Cargando historial de ' + escapeHtml(codigo) + "...</p>";
  try {
    const data = await api("/fuentes/" + encodeURIComponent(codigo) + "/ejecuciones?limit=20");
    const rows = data.items.map((e) =>
      "<tr><td>" + fdatetime(e.inicio) + "</td><td>" + fdatetime(e.fin) + "</td><td>" + badge(e.estado) + "</td><td>" + escapeHtml(e.trigger) + "</td>" +
      "<td>" + nfNum.format(e.items_obtenidos || 0) + "</td><td>" + nfNum.format(e.items_nuevos || 0) + "</td><td>" + nfNum.format(e.items_actualizados || 0) + "</td>" +
      '<td class="err-cell">' + (e.error_mensaje ? escapeHtml(e.error_mensaje) : "-") + "</td></tr>"
    ).join("") || '<tr><td colspan="8" class="muted">Sin ejecuciones.</td></tr>';
    cont.innerHTML =
      '<section class="card" style="margin-top:16px"><div class="section-head"><h3>Historial &middot; ' + escapeHtml(codigo) + " (" + data.total + " corridas)</h3></div>" +
      '<table class="hist"><thead><tr><th>Inicio</th><th>Fin</th><th>Estado</th><th>Trigger</th><th>Obt.</th><th>Nuevos</th><th>Act.</th><th>Error</th></tr></thead><tbody>' +
      rows + "</tbody></table></section>";
    cont.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (e) {
    cont.innerHTML = '<section class="card"><p class="err-msg">No se pudo cargar el historial: ' + escapeHtml(e.message) + "</p></section>";
  }
}

let pollTimer = null;
async function pollFuentes(tries) {
  tries = tries || 0;
  clearTimeout(pollTimer);
  const data = await fuentes(true);
  const enCurso = data.items.some((f) => f.ultima_ejecucion && f.ultima_ejecucion.estado === "en_curso");
  if (location.hash.indexOf("#/fuentes") === 0) renderFuentes();
  if (enCurso && tries < 40) {
    pollTimer = setTimeout(() => pollFuentes(tries + 1), 5000);
  } else if (!enCurso) {
    state.fuentesCache = null;
    toast("Scraping finalizado. Estado actualizado.", "ok");
  }
}

function bindCards() {
  document.querySelectorAll("[data-detail]").forEach((btn) => btn.addEventListener("click", () => showDetail(btn.dataset.detail)));
  document.querySelectorAll("[data-select]").forEach((cb) => cb.addEventListener("change", () => {
    const id = cb.dataset.select;
    if (cb.checked) state.selected.add(id); else state.selected.delete(id);
    updateSelectionBar();
  }));
  updateSelectionBar();
}

// ------------------------------------------------- SELECCION + EXPORT EXCEL
function updateSelectionBar() {
  const bar = document.querySelector("#selectionBar");
  if (!bar) return;
  const count = state.selected.size;
  bar.hidden = count === 0;
  const label = document.querySelector("#selectionCount");
  if (label) label.textContent = count + " convocatoria(s) seleccionada(s) para participar";
}

function clearSelection() {
  state.selected.clear();
  document.querySelectorAll("[data-select]").forEach((cb) => { cb.checked = false; });
  updateSelectionBar();
}

async function exportarSeleccionExcel() {
  const ids = Array.from(state.selected).map((x) => Number(x)).filter((n) => !Number.isNaN(n));
  if (!ids.length) { toast("No hay convocatorias seleccionadas.", "error"); return; }
  const btn = document.querySelector("#exportExcelBtn");
  const orig = btn ? btn.textContent : "";
  if (btn) { btn.disabled = true; btn.textContent = "Generando Excel..."; }
  try {
    const res = await fetch(API + "/convocatorias/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids }),
    });
    if (!res.ok) {
      let detail = res.status + " " + res.statusText;
      try { const b = await res.json(); if (b && b.detail) detail = typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail); } catch (_) { /* sin json */ }
      throw new Error(detail);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "convocatorias_seleccionadas.xlsx";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    toast("Excel generado con " + ids.length + " convocatoria(s).", "ok");
  } catch (e) {
    toast("No se pudo generar el Excel: " + e.message, "error");
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = orig; }
  }
}

// ------------------------------------------------------------------ DETALLE
async function showDetail(id) {
  detailTitle.textContent = "Cargando...";
  detailBody.innerHTML = '<p class="muted loading">Cargando ficha...</p>';
  dialog.showModal();
  let c;
  try { c = await api("/convocatorias/" + id); }
  catch (e) { detailBody.innerHTML = '<p class="err-msg">No se pudo cargar: ' + escapeHtml(e.message) + "</p>"; return; }

  detailTitle.textContent = c.titulo;
  const loc = [c.ciudad, c.departamento, c.pais].filter(Boolean).join(", ") || "No informada";
  const rues = c.entidad ? "https://www.rues.org.co/#/consulta?query=" + encodeURIComponent(c.entidad) : null;
  const buscar = c.entidad ? "https://www.google.com/search?q=" + encodeURIComponent(c.entidad) : null;

  let h = '<p class="detail-badges">' + badge(c.estado) + ' <span class="badge fuente">' + escapeHtml(c.fuente_nombre) + "</span> " + badge(c.tipo, "tipo");
  h += c.modalidad ? ' <span class="badge">' + escapeHtml(c.modalidad) + "</span>" : "";
  h += c.apto_fundaciones_nuevas ? ' <span class="badge apto" title="Marcada (heuristica) como accesible para fundaciones nuevas o primerizas. Verifica en la publicacion oficial.">Fundaciones nuevas</span>' : "";
  h += "</p>";
  h += '<section class="verify-card">';
  h += '<div class="verify-head"><span class="verify-kicker">Validar organizacion emisora</span>';
  h += "<h3>" + escapeHtml(c.entidad || "Entidad no informada por la fuente") + "</h3>";
  h += '<p class="muted">' + escapeHtml(loc) + "</p></div>";
  h += '<a class="verify big" href="' + escapeAttr(c.url_original) + '" target="_blank" rel="noopener noreferrer">Ver publicacion oficial y verificar entidad &nearr;</a>';
  h += '<p class="verify-note">Confirma en la fuente oficial que la organizacion y el proceso existen antes de gestionar el requisito.</p>';
  if (rues || buscar) {
    h += '<div class="verify-aids"><span class="muted small">Ayudas de verificacion (busqueda externa por el nombre real de la entidad):</span><div>';
    h += rues ? '<a class="link" href="' + escapeAttr(rues) + '" target="_blank" rel="noopener noreferrer">Buscar en RUES (Colombia)</a>' : "";
    h += buscar ? '<a class="link" href="' + escapeAttr(buscar) + '" target="_blank" rel="noopener noreferrer">Buscar en la web</a>' : "";
    h += "</div></div>";
  }
  h += "</section>";
  h += '<div class="detail-grid">';
  h += "<div><span>Monto</span><b>" + escapeHtml(money(c.monto, c.moneda)) + "</b></div>";
  h += "<div><span>Publicacion</span><b>" + fdate(c.fecha_publicacion) + "</b></div>";
  h += "<div><span>Apertura</span><b>" + fdate(c.fecha_apertura) + "</b></div>";
  h += "<div><span>Cierre</span><b>" + fdate(c.fecha_cierre) + "</b></div>";
  h += '<div><span>ID externo</span><b class="mono">' + escapeHtml(c.id_externo) + "</b></div>";
  h += "<div><span>Ultima vez visto</span><b>" + fdatetime(c.ultima_vez_visto) + "</b></div>";
  h += "</div>";
  if (c.keywords_match && c.keywords_match.length) {
    h += '<div class="kws">' + c.keywords_match.map((k) => '<span class="kw">' + escapeHtml(k) + "</span>").join("") + "</div>";
  }
  h += '<div class="detail-section"><h4>Descripcion</h4><p class="pre">' + (c.descripcion ? escapeMultiline(c.descripcion) : '<span class="muted">Sin descripcion en la fuente.</span>') + "</p></div>";
  h += '<div class="detail-section"><h4>Requisitos</h4><p class="pre">' + (c.requisitos ? escapeMultiline(c.requisitos) : '<span class="muted">No publicados en el listado de la fuente. Verificalos en la publicacion oficial.</span>') + "</p></div>";
  h += '<div class="detail-section ai-resumen-block"><div class="ai-resumen-head"><h4>Resumen con IA</h4><button type="button" class="ghost" id="resumirBtn">Resumir con IA</button></div><div id="resumenBox"></div></div>';
  detailBody.innerHTML = h;
  const rb = document.querySelector("#resumirBtn");
  if (rb) rb.addEventListener("click", () => resumirConIA(c.id));
}

// ------------------------------------------------------------- ASISTENTE IA
let aiLastQuestion = "";

async function renderAsistente() {
  setActiveNav("asistente");
  let h = '<section class="card ai-intro">';
  h += '<h2>Asistente de busqueda <span class="ai-tag" title="Interpretado por un modelo de IA">IA</span></h2>';
  h += '<p class="muted">Escribe en lenguaje natural lo que buscas. La IA lo traduce a filtros y muestra convocatorias <b>reales</b> de la base de datos. Si la IA no esta disponible, se usa una busqueda por palabra clave simple con tu misma pregunta.</p>';
  h += '<form id="aiForm" class="ai-form" autocomplete="off">';
  h += '<input id="aiQ" maxlength="500" placeholder="Ej. fondos de innovacion abiertos en Antioquia" value="' + escapeAttr(aiLastQuestion) + '" />';
  h += '<button type="submit" class="primary">Preguntar</button></form>';
  h += '<div class="ai-examples"><span class="muted small">Ejemplos:</span>';
  h += '<button type="button" class="chip" data-ex="licitaciones de software abiertas">licitaciones de software abiertas</button>';
  h += '<button type="button" class="chip" data-ex="convocatorias de educacion en Bogota">convocatorias de educacion en Bogota</button>';
  h += '<button type="button" class="chip" data-ex="subvenciones para fundaciones nuevas o primerizas">subvenciones para fundaciones nuevas o primerizas</button></div>';
  h += '</section><div id="aiResults"></div>';
  app.innerHTML = h;
  document.querySelector("#aiForm").addEventListener("submit", (ev) => { ev.preventDefault(); runAsistente(document.querySelector("#aiQ").value); });
  document.querySelectorAll(".chip[data-ex]").forEach((b) => b.addEventListener("click", () => { document.querySelector("#aiQ").value = b.dataset.ex; runAsistente(b.dataset.ex); }));
  if (aiLastQuestion) runAsistente(aiLastQuestion);
}

async function runAsistente(pregunta) {
  pregunta = (pregunta || "").trim();
  const box = document.querySelector("#aiResults");
  if (!box) return;
  if (!pregunta) { box.innerHTML = ""; return; }
  aiLastQuestion = pregunta;
  box.innerHTML = '<p class="muted loading">Consultando al asistente...</p>';
  let data;
  try {
    data = await api("/ai/buscar", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pregunta }) });
  } catch (e) {
    box.innerHTML = '<div class="card"><p class="err-msg">No se pudo consultar el asistente: ' + escapeHtml(e.message) + "</p></div>";
    return;
  }
  const r = data.resultado;
  const filtros = data.filtros_interpretados || {};
  const chips = Object.keys(filtros).length
    ? Object.entries(filtros).map(([k, v]) => '<span class="kw">' + escapeHtml(k) + ": " + escapeHtml(String(v)) + "</span>").join("")
    : '<span class="muted small">sin filtros</span>';
  const banner = (data.ia_disponible && !data.fallback)
    ? '<div class="ai-banner ok"><span class="ai-tag">IA</span> Consulta interpretada por IA. Verifica siempre en la publicacion oficial.</div>'
    : '<div class="ai-banner warn"><span class="ai-tag">IA</span> El asistente de IA no esta disponible; se uso busqueda por palabra clave simple con tu pregunta.</div>';
  let h = '<section class="card ai-interpret">' + banner;
  h += '<div class="ai-filters"><span class="muted small">Filtros aplicados:</span> ' + chips + "</div></section>";
  h += '<div class="results-head"><span class="muted">' + nfNum.format(r.total) + " resultado(s)</span></div>";
  const cards = r.items.map(cardConvocatoria).join("") || '<div class="card"><p class="muted">No hay convocatorias para esta consulta. Prueba reformular o usa el buscador con filtros.</p></div>';
  h += '<div class="results">' + cards + "</div>";
  box.innerHTML = h;
  bindCards();
}

async function resumirConIA(id) {
  const btn = document.querySelector("#resumirBtn");
  const box = document.querySelector("#resumenBox");
  if (!box) return;
  if (btn) { btn.disabled = true; btn.textContent = "Resumiendo..."; }
  box.innerHTML = '<p class="muted loading">Generando resumen con IA...</p>';
  try {
    const data = await api("/ai/convocatorias/" + id + "/resumen", { method: "POST" });
    if (data.ia_disponible && data.resumen) {
      box.innerHTML = '<div class="ai-resumen"><div class="ai-resumen-tag"><span class="ai-tag">IA</span> Resumen generado por IA &mdash; verifica siempre la publicacion oficial</div><p>' + escapeHtml(data.resumen) + "</p></div>";
    } else {
      box.innerHTML = '<div class="ai-banner warn"><span class="ai-tag">IA</span> ' + escapeHtml(data.mensaje || "El servicio de IA no esta disponible ahora mismo.") + "</div>";
    }
  } catch (e) {
    box.innerHTML = '<div class="ai-banner warn"><span class="ai-tag">IA</span> No se pudo generar el resumen: ' + escapeHtml(e.message) + "</div>";
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = "Resumir con IA"; }
  }
}

// ------------------------------------------------------------ REFRESH + ROUTER
async function refreshAll() {
  refreshBtn.disabled = true;
  const orig = refreshBtn.textContent;
  refreshBtn.textContent = "Encolando...";
  try {
    await api("/scraping/run", { method: "POST" });
    toast("Scraping de todas las fuentes encolado. Puede tardar unos minutos.", "ok");
    state.fuentesCache = null;
    pollFuentes();
  } catch (e) {
    toast("No se pudo iniciar el scraping: " + e.message, "error");
  } finally {
    refreshBtn.disabled = false;
    refreshBtn.textContent = orig;
  }
}

function hydrateFiltersFromHash(query) {
  if (!query) return;
  const p = new URLSearchParams(query);
  const nf = emptyFilters();
  for (const k of FILTER_KEYS) { if (p.has(k)) nf[k] = p.get(k); }
  state.filters = nf;
  state.page = p.has("page") ? Math.max(1, parseInt(p.get("page"), 10) || 1) : 1;
}

async function route() {
  try {
    const raw = location.hash || "#/dashboard";
    const parts = raw.slice(1).split("?");
    const path = parts[0], query = parts[1];
    if (path.indexOf("/convocatorias") === 0) { hydrateFiltersFromHash(query); return await renderConvocatorias(); }
    if (path.indexOf("/asistente") === 0) return await renderAsistente();
    if (path.indexOf("/fuentes") === 0) return await renderFuentes();
    return await renderDashboard();
  } catch (error) {
    app.innerHTML = '<section class="card"><h2>No se pudo cargar</h2><p class="err-msg">' + escapeHtml(error.message) +
      '</p><p class="muted">Verifica que la API responde en <code>/api/v1/health</code> y reintenta.</p>' +
      '<button onclick="location.reload()">Reintentar</button></section>';
  }
}

refreshBtn.addEventListener("click", refreshAll);

// Barra de seleccion + descarga a Excel (elementos estaticos en index.html).
const exportExcelBtn = document.querySelector("#exportExcelBtn");
const clearSelectionBtn = document.querySelector("#clearSelectionBtn");
if (exportExcelBtn) exportExcelBtn.addEventListener("click", exportarSeleccionExcel);
if (clearSelectionBtn) clearSelectionBtn.addEventListener("click", clearSelection);

// --- Widget flotante de soporte con IA ---
const supportFab = document.querySelector("#supportFab");
const supportPanel = document.querySelector("#supportPanel");
function toggleSupport(open) {
  const willOpen = open === undefined ? supportPanel.hidden : open;
  supportPanel.hidden = !willOpen;
  supportFab.setAttribute("aria-expanded", String(willOpen));
  if (willOpen) { const i = document.querySelector("#supportInput"); if (i) i.focus(); }
}
async function supportAsk(pregunta) {
  const log = document.querySelector("#supportLog");
  const input = document.querySelector("#supportInput");
  pregunta = (pregunta || "").trim();
  if (!pregunta) return;
  log.insertAdjacentHTML("beforeend", '<div class="sup-msg user">' + escapeHtml(pregunta) + '</div>');
  input.value = ""; input.disabled = true;
  const pending = document.createElement("div");
  pending.className = "sup-msg ai pending"; pending.textContent = "Pensando...";
  log.appendChild(pending); log.scrollTop = log.scrollHeight;
  try {
    const data = await api("/ai/soporte", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pregunta }) });
    pending.classList.remove("pending");
    pending.innerHTML = '<span class="ai-tag">IA</span> ' + escapeHtml(data.respuesta);
    if (!data.ia_disponible) pending.classList.add("warn");
  } catch (e) {
    pending.classList.remove("pending"); pending.classList.add("warn");
    pending.textContent = "No se pudo obtener ayuda: " + e.message;
  } finally {
    input.disabled = false; input.focus(); log.scrollTop = log.scrollHeight;
  }
}
if (supportFab) {
  supportFab.addEventListener("click", () => toggleSupport());
  document.querySelector("#supportClose").addEventListener("click", () => toggleSupport(false));
  document.querySelector("#supportForm").addEventListener("submit", (ev) => { ev.preventDefault(); supportAsk(document.querySelector("#supportInput").value); });
}
window.addEventListener("hashchange", route);
route();
