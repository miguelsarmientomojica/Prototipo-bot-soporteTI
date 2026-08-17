// ---------- Elementos ----------
const feed = document.getElementById("feed");
const feedEmpty = document.getElementById("feed-empty");
const tpl = document.getElementById("tpl-ticket");
const btnGenerar = document.getElementById("btn-generar");
const btnReiniciar = document.getElementById("btn-reiniciar");
const btnToggleManual = document.getElementById("btn-toggle-manual");
const formManual = document.getElementById("form-manual");
const chkAuto = document.getElementById("chk-auto");
const selComercio = document.getElementById("man-comercio");
const tabs = document.querySelectorAll(".tab");
const views = { llegada: document.getElementById("view-llegada"), tabla: document.getElementById("view-tabla") };

const ACCION_COLOR = { auto_update: "teal", revision_normal: "amber", revision_prioritaria: "coral" };
const ACCION_LABEL = {
  auto_update: "Auto-clasificado",
  revision_normal: "Revisión normal",
  revision_prioritaria: "Revisión prioritaria",
};
const CATEGORY_COLOR = {
  "Pregunta": "teal", "Pedido": "teal",
  "Incidente": "amber", "Requerimiento": "amber",
  "Problema": "coral", "No soporte": "amber",
};

let autoInterval = null;
let generando = false;
let historial = []; // cache local, se refresca al entrar a la vista de tabla

// ---------- Pestañas ----------
let filtrosInicializados = false;
tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("tab--active"));
    tab.classList.add("tab--active");
    Object.entries(views).forEach(([key, el]) => el.classList.toggle("view--active", key === tab.dataset.view));
    if (tab.dataset.view === "tabla") {
      if (!filtrosInicializados) {
        inicializarFiltros();
        filtrosInicializados = true;
      }
      paginaActual = 0;
      cargarHistorial();
    }
  });
});

// ---------- Comercios (dropdown manual + filtro) ----------
async function cargarComercios() {
  try {
    const resp = await fetch("/api/comercios");
    const comercios = await resp.json();
    selComercio.innerHTML =
      `<option value="">(sin especificar)</option>` +
      comercios.map((c) => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join("");
  } catch (err) {
    selComercio.innerHTML = `<option value="">(sin especificar)</option>`;
  }
}
cargarComercios();

// ---------- Carga inicial (Fase 3): el feed y los contadores ya no nacen
// vacios en cada refresh -- se rellenan con lo que de verdad hay guardado
// en la base de datos. ----------
async function cargarFeedInicial() {
  try {
    const resp = await fetch("/api/tickets/recientes?limit=10");
    const recientes = await resp.json();
    if (recientes.length === 0) return;
    feedEmpty.style.display = "none";
    // vienen del mas reciente al mas antiguo -- se insertan en ese mismo
    // orden con prepend para que el mas reciente quede arriba
    recientes.forEach((data) => {
      const node = tpl.content.cloneNode(true);
      feed.appendChild(node); // appendChild, no prepend: ya vienen ordenados
      const cardRef = feed.lastElementChild;
      cardRef.querySelector(".ticket-card__id").textContent = "#" + data.ticket.id;
      cardRef.querySelector(".ticket-card__subject").textContent = data.ticket.subject;
      cardRef.querySelector(".ticket-card__meta").textContent =
        (data.ticket.solicitante || "") + (data.ticket.tags && data.ticket.tags.length ? " · " + data.ticket.tags.join(", ") : "");
      cardRef.querySelector(".ticket-card__body").textContent = data.ticket.body || "";
      const origenEl = cardRef.querySelector(".ticket-card__origen");
      origenEl.textContent = data.ticket.origen === "manual" ? "Manual" : "Auto";
      if (data.ticket.origen === "manual") origenEl.classList.add("ticket-card__origen--manual");
      if (data.error) {
        cardRef.querySelector(".ticket-card__status").textContent = "Error";
        cardRef.querySelector(".ticket-card__result").innerHTML =
          `<div class="result-row"><span class="result-row__label">Error</span><span>${escapeHtml(data.error)}</span></div>`;
      } else {
        renderResultado(cardRef, data);
      }
    });
  } catch (err) {
    // si falla, el feed simplemente arranca vacio (igual que antes de la Fase 3)
  }
}

async function cargarStatsIniciales() {
  try {
    const resp = await fetch("/api/stats");
    actualizarStats(await resp.json());
  } catch (err) {
    // sin stats previas, los contadores quedan en 0
  }
}

cargarFeedInicial();
cargarStatsIniciales();

// ---------- Formulario manual ----------
btnToggleManual.addEventListener("click", () => {
  formManual.hidden = !formManual.hidden;
  btnToggleManual.textContent = formManual.hidden ? "+ Ticket manual" : "− Ocultar formulario";
});

formManual.addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    subject: document.getElementById("man-subject").value,
    body: document.getElementById("man-body").value,
    solicitante: document.getElementById("man-solicitante").value,
    rol: document.getElementById("man-rol").value,
    comercio: selComercio.value,
  };
  const cardRef = crearTarjetaPendiente();
  await procesarRespuesta(cardRef, fetch("/api/tickets/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }));
  formManual.reset();
});

// ---------- Feed en vivo ----------
function crearTarjetaPendiente() {
  feedEmpty.style.display = "none";
  const node = tpl.content.cloneNode(true);
  feed.prepend(node);
  return feed.firstElementChild;
}

async function procesarRespuesta(cardRef, promesaFetch) {
  const idEl = cardRef.querySelector(".ticket-card__id");
  const subjectEl = cardRef.querySelector(".ticket-card__subject");
  idEl.textContent = "Generando…";
  subjectEl.textContent = "Nuevo ticket entrando al sistema…";

  try {
    const resp = await promesaFetch;
    const data = await resp.json();

    if (!resp.ok) {
      subjectEl.textContent = data.error || "Error al crear el ticket";
      cardRef.querySelector(".ticket-card__status").textContent = "Error";
      return;
    }

    cardRef.querySelector(".ticket-card__id").textContent = "#" + data.ticket.id;
    cardRef.querySelector(".ticket-card__subject").textContent = data.ticket.subject;
    cardRef.querySelector(".ticket-card__meta").textContent =
      (data.ticket.solicitante || "") + (data.ticket.tags && data.ticket.tags.length ? " · " + data.ticket.tags.join(", ") : "");
    cardRef.querySelector(".ticket-card__body").textContent = data.ticket.body || "";

    const origenEl = cardRef.querySelector(".ticket-card__origen");
    origenEl.textContent = data.ticket.origen === "manual" ? "Manual" : "Auto";
    if (data.ticket.origen === "manual") origenEl.classList.add("ticket-card__origen--manual");

    const statusEl2 = cardRef.querySelector(".ticket-card__status");
    statusEl2.textContent = "Analizando IA…";
    statusEl2.className = "ticket-card__status status--analizando";

    await sleep(400);

    if (data.error) {
      statusEl2.textContent = "Error";
      statusEl2.className = "ticket-card__status status--nuevo";
      cardRef.querySelector(".ticket-card__result").innerHTML =
        `<div class="result-row"><span class="result-row__label">Error</span><span>${escapeHtml(data.error)}</span></div>`;
    } else {
      renderResultado(cardRef, data);
      actualizarStats(data.stats);
    }
  } catch (err) {
    subjectEl.textContent = "Error de conexión con el servidor local";
  }
}

async function generarTicket() {
  if (generando) return;
  generando = true;
  btnGenerar.disabled = true;
  const cardRef = crearTarjetaPendiente();
  await procesarRespuesta(cardRef, fetch("/api/tickets", { method: "POST" }));
  generando = false;
  btnGenerar.disabled = false;
}

function renderResultado(cardRef, data) {
  const color = ACCION_COLOR[data.accion] || "amber";
  cardRef.classList.add("ticket-card--" + data.accion);

  const statusEl = cardRef.querySelector(".ticket-card__status");
  statusEl.style.display = "none";

  const r = data.result;
  const pct = Math.round(r.confidence * 100);

  const avisoIncompleto = (r.category_id === "Incidente" && !r.informacion_completa)
    ? `<div class="incompleto-warning">
         ⚠ Información incompleta — falta: ${escapeHtml((r.campos_faltantes || []).join(", ") || "datos mínimos")}.
         No se puede tratar sin esto, se envía a revisión aunque la confianza sea alta.
       </div>`
    : "";

  cardRef.querySelector(".ticket-card__result").innerHTML = `
    ${avisoIncompleto}
    <div class="result-row">
      <span class="stamp stamp--${color}">${escapeHtml(r.category_id)}</span>
      <div style="flex:1">
        <div style="display:flex; justify-content:space-between; font-family:var(--font-mono); font-size:11px; color:var(--ink-muted);">
          <span>confianza</span><span>${pct}%</span>
        </div>
        <div class="confidence-bar"><div class="confidence-bar__fill" style="width:${pct}%; background:var(--${color})"></div></div>
      </div>
    </div>
    <div class="result-row"><span class="result-row__label">Prioridad</span><span>${escapeHtml(r.prioridad_sugerida)}</span></div>
    <div class="result-row"><span class="result-row__label">Comercio</span><span>${escapeHtml(r.comercio_sugerido)}</span></div>
    <div class="result-row"><span class="result-row__label">Vence</span><span>${escapeHtml(r.fecha_vencimiento_sugerida)}</span></div>
    <div class="result-row"><span class="result-row__label">Responsable</span><span>${escapeHtml(r.responsable_sugerido)}</span></div>
    <div class="result-row"><span class="result-row__label">Resumen</span><span>${escapeHtml(r.summary || "")}</span></div>
    <div class="result-row"><span class="result-row__label">Acción</span><span>${escapeHtml(r.suggested_action || "")}</span></div>
    <div class="result-row"><span class="result-row__label">Tiempo</span><span>${data.elapsed_ms} ms</span></div>
  `;
}

function actualizarStats(stats) {
  document.getElementById("stat-total").textContent = stats.total;
  document.getElementById("stat-auto").textContent = stats.por_accion.auto_update || 0;
  document.getElementById("stat-revision").textContent =
    (stats.por_accion.revision_normal || 0) + (stats.por_accion.revision_prioritaria || 0);

  renderBars("chart-categorias", stats.por_categoria, CATEGORY_COLOR, "amber");
  renderBars("chart-acciones", stats.por_accion, ACCION_COLOR, "amber", ACCION_LABEL);
}

function renderBars(containerId, data, colorMap, fallbackColor, labelMap) {
  const container = document.getElementById(containerId);
  const max = Math.max(1, ...Object.values(data));
  container.innerHTML = Object.entries(data)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .map(([key, value]) => {
      const color = colorMap[key] || fallbackColor;
      const label = labelMap ? (labelMap[key] || key) : key;
      const pct = Math.round((value / max) * 100);
      return `<div class="bar-row">
        <span class="bar-row__label">${escapeHtml(label)}</span>
        <span class="bar-row__track"><span class="bar-row__fill" style="width:${pct}%; background:var(--${color})"></span></span>
        <span class="bar-row__count">${value}</span>
      </div>`;
    }).join("");
}

btnGenerar.addEventListener("click", generarTicket);

btnReiniciar.addEventListener("click", async () => {
  feed.innerHTML = "";
  feed.appendChild(feedEmpty);
  feedEmpty.style.display = "block";
  document.getElementById("stat-total").textContent = "0";
  document.getElementById("stat-auto").textContent = "0";
  document.getElementById("stat-revision").textContent = "0";
  document.getElementById("chart-categorias").innerHTML = "";
  document.getElementById("chart-acciones").innerHTML = "";
  await fetch("/api/tickets/reset", { method: "POST" }).catch(() => {});
  historial = [];
  renderTabla();
});

chkAuto.addEventListener("change", () => {
  if (chkAuto.checked) {
    generarTicket();
    autoInterval = setInterval(generarTicket, 5000);
  } else {
    clearInterval(autoInterval);
  }
});

// ---------- Vista de tabla + filtros (Fase 3: filtrado y paginado en SQL) ----------
const fCategoria = document.getElementById("f-categoria");
const fComercio = document.getElementById("f-comercio");
const fPrioridad = document.getElementById("f-prioridad");
const fResponsable = document.getElementById("f-responsable");
const fAccion = document.getElementById("f-accion");
const fConfianza = document.getElementById("f-confianza");
const fConfianzaVal = document.getElementById("f-confianza-val");
const fBusqueda = document.getElementById("f-busqueda");
const btnLimpiarFiltros = document.getElementById("btn-limpiar-filtros");
const tablaBody = document.getElementById("tabla-body");
const filtersCount = document.getElementById("filters-count");
const btnPagAnterior = document.getElementById("btn-pag-anterior");
const btnPagSiguiente = document.getElementById("btn-pag-siguiente");
const pagInfo = document.getElementById("pag-info");

const TAMANO_PAGINA = 20;
let paginaActual = 0; // 0-indexed
let totalFiltrado = 0;
let debounceBusqueda = null;

async function inicializarFiltros() {
  try {
    const resp = await fetch("/api/tickets/filtros");
    const data = await resp.json();
    llenarSelect(fCategoria, data.categorias || []);
    llenarSelect(fComercio, data.comercios || []);
    llenarSelect(fPrioridad, data.prioridades || []);
    llenarSelect(fResponsable, data.responsables || []);
  } catch (err) {
    // si falla, los desplegables quedan solo con "Todas"
  }
}

function llenarSelect(select, valores) {
  const actual = select.value;
  const primera = select.querySelector("option").outerHTML;
  select.innerHTML = primera + valores.map((v) => `<option value="${escapeHtml(v)}">${escapeHtml(v)}</option>`).join("");
  if (valores.includes(actual)) select.value = actual;
}

function construirQueryFiltros() {
  const params = new URLSearchParams();
  params.set("limit", TAMANO_PAGINA);
  params.set("offset", paginaActual * TAMANO_PAGINA);
  if (fCategoria.value) params.set("categoria", fCategoria.value);
  if (fComercio.value) params.set("comercio", fComercio.value);
  if (fPrioridad.value) params.set("prioridad", fPrioridad.value);
  if (fResponsable.value) params.set("responsable", fResponsable.value);
  if (fAccion.value) params.set("accion", fAccion.value);
  if (Number(fConfianza.value) > 0) params.set("confianza_min", Number(fConfianza.value) / 100);
  if (fBusqueda.value.trim()) params.set("busqueda", fBusqueda.value.trim());
  return params;
}

async function cargarHistorial() {
  tablaBody.innerHTML = `<tr><td colspan="11" class="tabla__empty">Cargando…</td></tr>`;
  try {
    const params = construirQueryFiltros();
    const resp = await fetch(`/api/tickets/historial?${params.toString()}`);
    const data = await resp.json();
    totalFiltrado = data.total || 0;
    renderTabla(data.tickets || []);
  } catch (err) {
    tablaBody.innerHTML = `<tr><td colspan="11" class="tabla__empty">Error cargando el historial.</td></tr>`;
  }
}

function renderTabla(filas) {
  const desde = filas.length ? paginaActual * TAMANO_PAGINA + 1 : 0;
  const hasta = paginaActual * TAMANO_PAGINA + filas.length;
  filtersCount.textContent = `${totalFiltrado} tickets en total`;
  pagInfo.textContent = totalFiltrado ? `${desde}–${hasta} de ${totalFiltrado}` : "0 de 0";
  btnPagAnterior.disabled = paginaActual === 0;
  btnPagSiguiente.disabled = hasta >= totalFiltrado;

  if (filas.length === 0) {
    tablaBody.innerHTML = `<tr><td colspan="11" class="tabla__empty">Ningún ticket coincide con estos filtros.</td></tr>`;
    return;
  }

  tablaBody.innerHTML = filas.map((h) => {
    const r = h.result;
    const origenClase = h.ticket.origen === "manual" ? "origen-chip origen-chip--manual" : "origen-chip";
    const infoCompleta = r.category_id === "Incidente"
      ? (r.informacion_completa
          ? `<span title="Completa">✓</span>`
          : `<span class="info-incompleta" title="Falta: ${escapeHtml((r.campos_faltantes || []).join(', '))}">✗</span>`)
      : `<span class="info-na" title="No aplica a esta categoría">—</span>`;
    return `<tr>
      <td class="td-id">#${h.ticket.id}</td>
      <td><span class="${origenClase}">${h.ticket.origen === "manual" ? "Manual" : "Auto"}</span></td>
      <td class="td-asunto" title="${escapeHtml(h.ticket.subject)}">${escapeHtml(h.ticket.subject)}</td>
      <td>${escapeHtml(r.category_id)}</td>
      <td class="td-confianza">${Math.round(r.confidence * 100)}%</td>
      <td>${escapeHtml(r.prioridad_sugerida)}</td>
      <td>${escapeHtml(r.comercio_sugerido)}</td>
      <td>${escapeHtml(r.fecha_vencimiento_sugerida)}</td>
      <td>${escapeHtml(r.responsable_sugerido)}</td>
      <td>${infoCompleta}</td>
      <td><span class="accion-chip accion-chip--${h.accion}">${ACCION_LABEL[h.accion] || h.accion}</span></td>
    </tr>`;
  }).join("");
}

function refiltrarDesdeInicio() {
  paginaActual = 0;
  cargarHistorial();
}

[fCategoria, fComercio, fPrioridad, fResponsable, fAccion].forEach((el) => el.addEventListener("change", refiltrarDesdeInicio));
fBusqueda.addEventListener("input", () => {
  clearTimeout(debounceBusqueda);
  debounceBusqueda = setTimeout(refiltrarDesdeInicio, 350); // evita 1 consulta SQL por cada tecla
});
fConfianza.addEventListener("input", () => {
  fConfianzaVal.textContent = fConfianza.value + "%";
});
fConfianza.addEventListener("change", refiltrarDesdeInicio);
btnLimpiarFiltros.addEventListener("click", () => {
  [fCategoria, fComercio, fPrioridad, fResponsable, fAccion].forEach((el) => (el.value = ""));
  fConfianza.value = 0;
  fConfianzaVal.textContent = "0%";
  fBusqueda.value = "";
  refiltrarDesdeInicio();
});
btnPagAnterior.addEventListener("click", () => {
  if (paginaActual > 0) { paginaActual--; cargarHistorial(); }
});
btnPagSiguiente.addEventListener("click", () => {
  paginaActual++;
  cargarHistorial();
});

// ---------- Utilidades ----------
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str == null ? "" : str;
  return div.innerHTML;
}
function sleep(ms) { return new Promise((res) => setTimeout(res, ms)); }
