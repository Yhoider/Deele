'use strict';

/* Interfaz del proyecto de estaciones.
   Los algoritmos corren en Python (servidor.py); aquí solo se dibuja y se
   suman coberturas para responder al instante mientras el visitante juega. */

const FONDO = '#0e141b';
const COLOR = { hurto: '#3987e5', accidente: '#199e70', incendio: '#d95926' };
const CORTO = { hurto: 'CAI', accidente: 'Tránsito', incendio: 'Bomberos' };
const SIGLA = { hurto: 'C', accidente: 'T', incendio: 'B' };
// Lista de respaldo; al iniciar se reemplaza por la que informa el servidor,
// que incluye las zonas generadas con generar_zonas.py.
let ESCENARIOS = [
  { id: 'pequena', titulo: 'Barrio', oficial: true },
  { id: 'comuna', titulo: 'Laureles', oficial: true },
  { id: 'ciudad', titulo: 'Medellín', oficial: true },
];
const METODOS = [
  { id: 'base', nombre: 'Voraz por valor', explicacion: 'En cada paso toma la estación que más valor nuevo aporta, sin mirar cuánto cuesta.' },
  { id: 'densidad', nombre: 'Voraz por valor / costo', explicacion: 'En cada paso toma la estación que más valor nuevo aporta por cada millón invertido.' },
  { id: 'local', nombre: 'Búsqueda local', explicacion: 'Parte de las dos propuestas voraces y las mejora: quita una, dos o tres estaciones, vuelve a llenar el presupuesto y se queda con el cambio si el valor sube. Repite hasta que ningún cambio mejora.' },
  { id: 'optimo', nombre: 'Óptimo exacto', explicacion: 'Búsqueda con poda: descarta las ramas que ya no pueden superar a la mejor propuesta conocida, y así prueba cuál es la mejor posible.' },
  { id: 'manual', nombre: 'Tu propuesta', explicacion: 'Haz clic en un lote del mapa para poner o quitar una estación. ¿Puedes superar al algoritmo?' },
];
const HEURISTICAS = ['base', 'densidad', 'local'];
// Del radio mayor al menor: un halo ancho y tenue, una banda media y una línea nítida,
// para que se distingan aunque varias estaciones alcancen la misma vía.
const ANCHOS_COBERTURA = [7, 2.6, 1.1];
const FUERZA_COBERTURA = [0.2, 0.45, 0.85];
const TOPE_ANCHO_COBERTURA = [16, 8, 3.5]; // en píxeles, para que el halo no tape el mapa al acercar
// Al aparecer una estación, su alcance se expande por las vías en el orden en
// que Dijkstra las recorre: de la más cercana a la más lejana, hasta el radio.
const VELOCIDAD_ONDA = 2;   // metros de vía que avanza por milisegundo
const BANDA_FRENTE = 150;   // metros detrás del frente que se dibujan resaltados

const $ = (s) => document.querySelector(s);
const nf = new Intl.NumberFormat('es-CO');
const num = (v) => nf.format(Math.round(v));
const pct = (a, b) => (b ? (100 * a / b).toLocaleString('es-CO', { maximumFractionDigits: 1 }) + ' %' : '—');
const limitar = (v, a, b) => Math.max(a, Math.min(b, v));
const esc = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const color = (tipo) => COLOR[tipo] || '#8693a4';
const corto = (tipo) => CORTO[tipo] || tipo;
const mayuscula = (t) => t.charAt(0).toUpperCase() + t.slice(1);
const radioTexto = (m) => (m >= 1000 ? `${(m / 1000).toLocaleString('es-CO')} km` : `${m} m`);

function mezcla(hex, proporcion) {
  // Color opaco equivalente a pintar `hex` con esa opacidad sobre el fondo.
  const canal = (h, i) => parseInt(h.slice(i, i + 2), 16);
  const partes = [1, 3, 5].map((i) => Math.round(canal(hex, i) * proporcion + canal(FONDO, i) * (1 - proporcion)));
  return `rgb(${partes.join(',')})`;
}

const E = {
  nombre: null, d: null, presupuesto: 0, metodo: null,
  heuristicas: null, optimo: null, manual: [],
  pasos: null, temporizador: null, ev: null, puesto: new Map(),
  foco: null, previa: null, menu: null,
  calles: new Map(), marcas: {}, capas: {}, turno: 0, sondeo: null,
  ondas: new Map(), frentes: [], cubiertoVisible: null,
};
const V = { k: 1, tx: 0, ty: 0, kBase: 1, libre: false };

const mapa = $('#mapa');
const lienzoCalles = $('#capa-calles');
const lienzoDatos = $('#capa-datos');
const cCalles = lienzoCalles.getContext('2d');
const cDatos = lienzoDatos.getContext('2d');
let ancho = 0, alto = 0, dpr = 1;

/* ---------------- Datos ---------------- */

async function api(ruta) {
  const r = await fetch(ruta);
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
}

function aviso(texto) {
  const caja = $('#aviso');
  caja.hidden = !texto;
  if (texto) caja.textContent = texto;
}

function avisarFallo(que, error) {
  // `fetch` lanza TypeError cuando no hay conexión: el servidor está apagado.
  const causa = error instanceof TypeError
    ? 'el servidor no responde. Ejecuta de nuevo <b>servidor.py</b> y recarga la página.'
    : esc(error.message);
  anunciar(`${que}: ${causa}`, 8000);
}

function preparar(d) {
  const n = d.nodos.length / 2;
  let latMedia = 0, lonMedia = 0;
  for (let i = 0; i < n; i++) { latMedia += d.nodos[2 * i]; lonMedia += d.nodos[2 * i + 1]; }
  latMedia /= n; lonMedia /= n;
  const metrosPorGrado = 111320, cos = Math.cos(latMedia * Math.PI / 180);
  const X = new Float64Array(n), Y = new Float64Array(n);
  const caja = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
  for (let i = 0; i < n; i++) {
    X[i] = (d.nodos[2 * i + 1] - lonMedia) * cos * metrosPorGrado;
    Y[i] = -(d.nodos[2 * i] - latMedia) * metrosPorGrado;
    caja.minX = Math.min(caja.minX, X[i]); caja.maxX = Math.max(caja.maxX, X[i]);
    caja.minY = Math.min(caja.minY, Y[i]); caja.maxY = Math.max(caja.maxY, Y[i]);
  }
  E.X = X; E.Y = Y; E.caja = caja;
  E.tramos = Int32Array.from(d.tramos);
  E.tipo = Object.fromEntries(d.tipos.map((t) => [t.id, t]));
  E.lotes = d.lotes.map((l) => ({ ...l, x: X[l.nodo], y: Y[l.nodo] }));
  E.lotePorId = new Map(E.lotes.map((l) => [l.id, l]));

  // El encuadre inicial sigue a los lotes e incidentes: la red de la ciudad
  // incluye vías rurales lejanas que dejarían la zona urbana muy pequeña.
  const interes = { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity };
  for (const nodo of [...d.lotes.map((l) => l.nodo), ...d.incidentes.nodo]) {
    interes.minX = Math.min(interes.minX, X[nodo]); interes.maxX = Math.max(interes.maxX, X[nodo]);
    interes.minY = Math.min(interes.minY, Y[nodo]); interes.maxY = Math.max(interes.maxY, Y[nodo]);
  }
  E.interes = Number.isFinite(interes.minX) ? interes : caja;

  // Varios incidentes en la misma esquina se abren en espiral para que se vean todos.
  const inc = d.incidentes, total = inc.nodo.length;
  E.desX = new Float32Array(total); E.desY = new Float32Array(total);
  E.totalTipo = Object.fromEntries(d.tipos.map((t) => [t.id, 0]));
  const vistos = new Map();
  for (let i = 0; i < total; i++) {
    E.totalTipo[d.tipos[inc.tipo[i]].id]++;
    const j = vistos.get(inc.nodo[i]) || 0;
    vistos.set(inc.nodo[i], j + 1);
    if (j > 0) {
      const r = 1.7 * Math.sqrt(j);
      E.desX[i] = Math.cos(j * 2.4) * r; E.desY[i] = Math.sin(j * 2.4) * r;
    }
  }
}

function evaluar(lista) {
  // Misma cuenta que `evaluar_propuesta` en Python, más el aporte de cada paso.
  const cubierto = new Uint8Array(E.d.incidentes.nodo.length);
  const casos = Object.fromEntries(E.d.tipos.map((t) => [t.id, 0]));
  let costo = 0, valor = 0;
  const filas = [];
  for (const [loteId, tipo] of lista) {
    const opcion = E.lotePorId.get(loteId).opciones[tipo];
    let nuevos = 0;
    for (const i of opcion.incidentes) if (!cubierto[i]) { cubierto[i] = 1; nuevos++; }
    const aporte = nuevos * E.tipo[tipo].peso;
    casos[tipo] += nuevos; costo += opcion.costo; valor += aporte;
    filas.push({ lote: loteId, tipo, costo: opcion.costo, nuevos, aporte, alcance: opcion.incidentes.length });
  }
  return { cubierto, casos, costo, valor, filas };
}

function listaActual() {
  if (E.metodo === 'manual') return E.manual;
  if (E.metodo === 'optimo') return E.optimo && E.optimo.estado === 'listo' ? E.optimo.estaciones : [];
  return E.heuristicas ? E.heuristicas[E.metodo].estaciones : [];
}
const listaVisible = () => (E.pasos == null ? listaActual() : listaActual().slice(0, E.pasos));
const claveActual = () => `${E.nombre}|${E.presupuesto}`;

async function cargarEscenario(nombre) {
  const turno = ++E.turno;
  detenerAnimacion(); cerrarMenu(); clearTimeout(E.sondeo);
  pintarEscenarios(nombre);
  aviso('Cargando la red vial…');
  let d;
  try { d = await api(`/api/instancia?nombre=${nombre}`); } catch (error) { aviso(`No se pudo cargar: ${error.message}`); return; }
  if (turno !== E.turno) return;
  E.nombre = nombre; E.d = d;
  preparar(d);
  E.presupuesto = d.presupuesto;
  E.heuristicas = null; E.optimo = null; E.manual = []; E.calles = new Map(); E.foco = null; E.previa = null;
  E.ondas = new Map(); E.frentes = []; E.cubiertoVisible = null; E.puesto = new Map();
  const deslizador = $('#presupuesto');
  deslizador.min = d.presupuesto / 5; deslizador.max = d.presupuesto * 2; deslizador.step = d.presupuesto / 40;
  deslizador.value = d.presupuesto;
  pintarLeyenda();
  $('#resumen').textContent = `${d.descripcion} ${num(d.nodos.length / 2)} intersecciones · ${num(d.tramos.length / 2)} tramos de vía · ${d.lotes.length} lotes · ${num(d.incidentes.nodo.length)} incidentes.`;
  ajustarLienzos(); encuadrar();
  try { await actualizarHeuristicas(); } catch (error) { aviso(`No se pudo calcular: ${error.message}`); return; }
  if (turno !== E.turno) return;
  aviso(null);
  if (!E.metodo || (E.metodo === 'optimo' && !d.exacto_viable)) E.metodo = mejorHeuristica();
  if (d.lotes.length <= 8 || E.metodo === 'optimo') pedirOptimo();
  recalcular();
  pedirDibujo(true);
}

let pedidoHeuristicas = null;
function actualizarHeuristicas() {
  // Una sola consulta a la vez: si el presupuesto cambia mientras el servidor
  // calcula (la búsqueda local tarda hasta 2 s en la ciudad), se repite al terminar.
  if (pedidoHeuristicas) return pedidoHeuristicas;
  $('#propuestas').classList.add('calculando');
  pedidoHeuristicas = (async () => {
    try {
      for (;;) {
        const clave = claveActual();
        const r = await api(`/api/heuristicas?nombre=${E.nombre}&presupuesto=${E.presupuesto}`);
        if (clave === claveActual()) { E.heuristicas = r; return; }
      }
    } finally {
      pedidoHeuristicas = null;
      $('#propuestas').classList.remove('calculando');
    }
  })();
  return pedidoHeuristicas;
}

function mejorHeuristica() {
  return HEURISTICAS.reduce((a, b) => (E.heuristicas[b].valor > E.heuristicas[a].valor ? b : a));
}

async function pedirOptimo(iniciar = true) {
  if (!E.d || !E.d.exacto_viable) return;
  const clave = claveActual();
  clearTimeout(E.sondeo);
  let r;
  try { r = await api(`/api/optimo?nombre=${E.nombre}&presupuesto=${E.presupuesto}&iniciar=${iniciar ? 1 : 0}`); } catch (error) {
    if (clave !== claveActual()) return;
    E.optimo = null; // vuelve a «Clic para calcularlo», para poder reintentar
    avisarFallo('No se pudo calcular el óptimo', error);
    pintarPropuestas();
    return;
  }
  if (clave !== claveActual()) return;
  E.optimo = r.estado === 'inexistente' ? null : r;
  if (r.estado === 'corriendo') {
    E.sondeo = setTimeout(() => pedirOptimo(false), 200);
    pintarPropuestas();
  } else {
    recalcular();
  }
}

/* ---------------- Cobertura por calles ---------------- */

function callesDe(lote) {
  const guardado = E.calles.get(lote);
  if (guardado !== undefined) return guardado;
  E.calles.set(lote, null);
  const nombre = E.nombre, almacen = E.calles;
  api(`/api/calles?nombre=${nombre}&lote=${encodeURIComponent(lote)}`).then((r) => {
    if (almacen !== E.calles) return;
    // Los tramos llegan ordenados por distancia: los de cada tipo son los primeros `hasta[tipo]`.
    almacen.set(lote, {
      tramos: Int32Array.from(r.tramos), metros: Float32Array.from(r.metros),
      hasta: r.hasta, casos: new Map(r.casos),
    });
    reconstruirMarcas(); pedirDibujo(false);
  }).catch((error) => {
    almacen.delete(lote);
    if (almacen !== E.calles) return;
    E.ondas.delete(lote);
    avisarFallo('No se pudo cargar el alcance por vías', error);
  });
  return null;
}

function contarHasta(metros, limite, tope) {
  // Cuántos de los primeros `tope` tramos quedan a `limite` metros o menos (búsqueda binaria).
  let a = 0, b = tope;
  while (a < b) {
    const medio = (a + b) >> 1;
    if (metros[medio] <= limite) a = medio + 1; else b = medio;
  }
  return a;
}

function reconstruirMarcas() {
  const total = E.tramos.length / 2, ahora = performance.now();
  for (const t of E.d.tipos) {
    if (E.marcas[t.id] && E.marcas[t.id].length === total) E.marcas[t.id].fill(0);
    else E.marcas[t.id] = new Uint8Array(total);
  }
  // Mientras haya ondas, un incidente solo cuenta como cubierto cuando la onda llega a él.
  const cubierto = E.ondas.size ? new Uint8Array(E.d.incidentes.nodo.length) : null;
  E.frentes = [];
  let enCurso = false;
  for (const [lote, tipo] of listaVisible()) {
    const calles = callesDe(lote);
    const onda = E.ondas.get(lote);
    let alcance = Infinity;
    if (onda) {
      if (!calles) continue; // la onda arranca cuando el servidor responde con sus calles
      if (onda.inicio == null) onda.inicio = ahora;
      alcance = (ahora - onda.inicio) * VELOCIDAD_ONDA;
      if (alcance >= E.tipo[tipo].radio_m) { E.ondas.delete(lote); alcance = Infinity; }
      else enCurso = true;
    }
    if (cubierto) {
      for (const i of E.lotePorId.get(lote).opciones[tipo].incidentes) {
        if (alcance === Infinity || calles.casos.get(i) <= alcance) cubierto[i] = 1;
      }
    }
    if (!calles) continue;
    let hasta = calles.hasta[tipo];
    if (alcance !== Infinity) {
      hasta = contarHasta(calles.metros, alcance, hasta);
      const desde = contarHasta(calles.metros, alcance - BANDA_FRENTE, hasta);
      E.frentes.push({ tipo, tramos: calles.tramos.subarray(desde, hasta) });
    }
    const marcas = E.marcas[tipo], T = calles.tramos;
    for (let j = 0; j < hasta; j++) marcas[T[j]] = 1;
  }
  E.cubiertoVisible = E.ondas.size ? cubierto : null;
  if (enCurso) seguirOndas();
}

let cuadroOnda = 0;
function seguirOndas() {
  if (cuadroOnda) return;
  cuadroOnda = requestAnimationFrame(() => {
    cuadroOnda = 0;
    if (!E.d || !E.ev) return;
    reconstruirMarcas(); dibujarDatos();
  });
}

function recalcular() {
  if (!E.d || !E.heuristicas) return;
  const lista = listaVisible(), antes = E.puesto;
  E.ev = evaluar(lista);
  E.puesto = new Map(lista);
  for (const lote of [...E.ondas.keys()]) if (!E.puesto.has(lote)) E.ondas.delete(lote);
  // Cada estación nueva (o que cambió de tipo) expande su alcance desde el lote.
  for (const [lote, tipo] of lista) if (antes.get(lote) !== tipo) E.ondas.set(lote, { inicio: null });
  reconstruirMarcas();
  pintarPanel();
  pedirDibujo(false);
}

/* ---------------- Mapa ---------------- */

function ajustarLienzos() {
  const r = mapa.getBoundingClientRect();
  ancho = r.width; alto = r.height; dpr = window.devicePixelRatio || 1;
  for (const lienzo of [lienzoCalles, lienzoDatos]) {
    lienzo.width = Math.round(ancho * dpr); lienzo.height = Math.round(alto * dpr);
  }
}

function encuadrar() {
  if (!E.d) return;
  // Se reserva espacio arriba para los anuncios y abajo para la leyenda.
  const lado = Math.min(70, ancho * 0.08), arriba = 56, abajo = alto > 460 ? 158 : 56;
  const caja = E.interes;
  const w = caja.maxX - caja.minX || 1, h = caja.maxY - caja.minY || 1;
  V.k = V.kBase = Math.min((ancho - 2 * lado) / w, (alto - arriba - abajo) / h);
  V.tx = (ancho - w * V.k) / 2 - caja.minX * V.k;
  V.ty = arriba + (alto - arriba - abajo - h * V.k) / 2 - caja.minY * V.k;
  V.libre = false; // pasa a true cuando el visitante mueve o acerca el mapa
}

function zoomEn(px, py, factor) {
  const k = limitar(V.k * factor, V.kBase * 0.25, Math.max(V.kBase * 60, 2));
  const f = k / V.k;
  V.tx = px - (px - V.tx) * f; V.ty = py - (py - V.ty) * f; V.k = k; V.libre = true;
  cerrarMenu(); ocultarGlobo();
  pedirDibujo(true);
}

const grosorCalle = () => limitar(V.k * 14, 0.6, 5);

let dibujoPendiente = null;
function pedirDibujo(conCalles) {
  if (dibujoPendiente) { dibujoPendiente.calles = dibujoPendiente.calles || conCalles; return; }
  dibujoPendiente = { calles: conCalles };
  requestAnimationFrame(() => {
    const { calles } = dibujoPendiente;
    dibujoPendiente = null;
    if (calles) dibujarCalles();
    dibujarDatos();
  });
}

function trazar(c, indices) {
  const X = E.X, Y = E.Y, T = E.tramos;
  c.beginPath();
  for (const j of indices) { c.moveTo(X[T[2 * j]], Y[T[2 * j]]); c.lineTo(X[T[2 * j + 1]], Y[T[2 * j + 1]]); }
}

function dibujarCalles() {
  const c = cCalles;
  c.setTransform(1, 0, 0, 1, 0, 0);
  c.clearRect(0, 0, lienzoCalles.width, lienzoCalles.height);
  if (!E.d) return;
  c.setTransform(dpr * V.k, 0, 0, dpr * V.k, dpr * V.tx, dpr * V.ty);
  const X = E.X, Y = E.Y, T = E.tramos;
  c.beginPath();
  for (let i = 0; i < T.length; i += 2) { c.moveTo(X[T[i]], Y[T[i]]); c.lineTo(X[T[i + 1]], Y[T[i + 1]]); }
  c.lineCap = 'round';
  c.lineWidth = grosorCalle() / V.k;
  c.strokeStyle = '#2a3646';
  c.stroke();
}

function dibujarDatos() {
  const c = cDatos;
  c.setTransform(1, 0, 0, 1, 0, 0);
  c.clearRect(0, 0, lienzoDatos.width, lienzoDatos.height);
  if (!E.d || !E.ev) return;
  const { k, tx, ty } = V, X = E.X, Y = E.Y, T = E.tramos;
  const base = grosorCalle();
  const tipoFoco = E.foco ? E.puesto.get(E.foco) : null;
  const resalte = E.previa || (tipoFoco ? { lote: E.foco, tipo: tipoFoco } : null);

  // 1. Calles que cada estación alcanza por la red vial (bandas anidadas por tipo).
  c.setTransform(dpr * k, 0, 0, dpr * k, dpr * tx, dpr * ty);
  c.lineCap = 'round';
  const porRadio = [...E.d.tipos].sort((a, b) => b.radio_m - a.radio_m);
  porRadio.forEach((t, puestoEnOrden) => {
    const marcas = E.marcas[t.id];
    if (E.capas[t.id] === false) return;
    let hay = false;
    c.beginPath();
    for (let j = 0; j < marcas.length; j++) {
      if (!marcas[j]) continue;
      hay = true;
      c.moveTo(X[T[2 * j]], Y[T[2 * j]]); c.lineTo(X[T[2 * j + 1]], Y[T[2 * j + 1]]);
    }
    if (!hay) return;
    const fuerza = FUERZA_COBERTURA[puestoEnOrden] || 0.5;
    c.strokeStyle = mezcla(color(t.id), resalte ? fuerza * 0.4 : fuerza);
    c.lineWidth = Math.min(base * (ANCHOS_COBERTURA[puestoEnOrden] || 1) + 0.6, TOPE_ANCHO_COBERTURA[puestoEnOrden] || 3.5) / k;
    c.stroke();
  });
  // Frente de cada onda en expansión: lo último que Dijkstra acaba de alcanzar.
  for (const frente of E.frentes) {
    if (E.capas[frente.tipo] === false || !frente.tramos.length) continue;
    trazar(c, frente.tramos);
    c.strokeStyle = color(frente.tipo);
    c.lineWidth = (base * 1.5 + 1.5) / k;
    c.stroke();
    c.globalAlpha = 0.75; c.strokeStyle = '#ffffff';
    c.lineWidth = (base * 0.5 + 0.5) / k;
    c.stroke();
    c.globalAlpha = 1;
  }
  if (resalte) {
    const calles = callesDe(resalte.lote);
    if (calles) {
      trazar(c, calles.tramos.subarray(0, calles.hasta[resalte.tipo]));
      c.strokeStyle = color(resalte.tipo);
      c.lineWidth = (base * 1.5 + 1) / k;
      c.stroke();
    }
  }

  // 2. Incidentes: llenos si quedan cubiertos, huecos (o tenues) si no.
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  const inc = E.d.incidentes, cubierto = (E.ondas.size && E.cubiertoVisible) || E.ev.cubierto;
  const r = limitar(k * 16, 1.3, 5);
  for (let ti = 0; ti < E.d.tipos.length; ti++) {
    const tinta = color(E.d.tipos[ti].id);
    for (const estado of [0, 1]) {
      c.beginPath();
      for (let i = 0; i < inc.nodo.length; i++) {
        if (inc.tipo[i] !== ti || cubierto[i] !== estado) continue;
        const sx = X[inc.nodo[i]] * k + tx + E.desX[i] * r, sy = Y[inc.nodo[i]] * k + ty + E.desY[i] * r;
        if (sx < -8 || sy < -8 || sx > ancho + 8 || sy > alto + 8) continue;
        if (r < 2) c.rect(sx - r, sy - r, 2 * r, 2 * r);
        else { c.moveTo(sx + r, sy); c.arc(sx, sy, r, 0, 6.2832); }
      }
      if (estado) {
        c.globalAlpha = 1; c.fillStyle = tinta; c.fill();
        if (r >= 3) { c.strokeStyle = FONDO; c.lineWidth = 1; c.stroke(); }
      } else if (r >= 3) {
        c.globalAlpha = 1; c.fillStyle = FONDO; c.fill();
        c.strokeStyle = tinta; c.lineWidth = 1.5; c.stroke();
      } else {
        c.globalAlpha = 0.4; c.fillStyle = tinta; c.fill();
      }
    }
  }
  c.globalAlpha = 1;

  // 3. Lotes libres y estaciones.
  const editable = E.metodo === 'manual';
  const conNombre = E.lotes.length <= 20 || k > V.kBase * 3;
  const ultimo = E.pasos ? listaActual()[E.pasos - 1] : null;
  const muchos = E.lotes.length > 40;
  const radioEstacion = muchos ? limitar(7 + (k / V.kBase - 1) * 2, 7, 10) : 10;
  c.textAlign = 'center'; c.textBaseline = 'middle';
  for (const estacion of [false, true]) {
    for (const l of E.lotes) {
      const tipo = E.puesto.get(l.id);
      if (Boolean(tipo) !== estacion) continue;
      const sx = l.x * k + tx, sy = l.y * k + ty;
      if (sx < -30 || sy < -30 || sx > ancho + 30 || sy > alto + 30) continue;
      const activo = l.id === E.foco || l.id === E.menu;
      if (tipo) {
        const radio = radioEstacion;
        if (activo || (ultimo && ultimo[0] === l.id)) {
          c.beginPath(); c.arc(sx, sy, radio + 5, 0, 6.2832);
          c.strokeStyle = '#e9eef4'; c.lineWidth = 2; c.stroke();
        }
        c.beginPath(); c.arc(sx, sy, radio, 0, 6.2832);
        c.fillStyle = color(tipo); c.fill();
        c.strokeStyle = FONDO; c.lineWidth = 2; c.stroke();
        c.fillStyle = '#ffffff'; c.font = `700 ${radioEstacion < 9 ? 9 : 11}px system-ui, sans-serif`;
        c.fillText(SIGLA[tipo] || '•', sx, sy + 0.5);
      } else {
        const lado = editable ? 7 : (muchos ? 4 : 5);
        c.beginPath(); c.rect(sx - lado, sy - lado, 2 * lado, 2 * lado);
        c.fillStyle = FONDO; c.fill();
        c.strokeStyle = activo ? '#e9eef4' : (editable ? '#b3bdca' : '#8693a4');
        c.lineWidth = activo ? 2 : 1.5;
        c.setLineDash(l.hipotetico ? [3, 2] : []); c.stroke(); c.setLineDash([]);
        if (editable) {
          c.beginPath(); c.moveTo(sx - 3.5, sy); c.lineTo(sx + 3.5, sy); c.moveTo(sx, sy - 3.5); c.lineTo(sx, sy + 3.5);
          c.strokeStyle = '#b3bdca'; c.lineWidth = 1.5; c.stroke();
        }
      }
      if (conNombre) {
        c.font = '600 11px system-ui, sans-serif';
        c.lineWidth = 3; c.strokeStyle = FONDO; c.strokeText(l.id, sx, sy - (tipo ? 20 : 15));
        c.fillStyle = '#b3bdca'; c.fillText(l.id, sx, sy - (tipo ? 20 : 15));
      }
    }
  }
}

/* ---------------- Interacción con el mapa ---------------- */

function loteCerca(px, py) {
  let mejor = null, distancia = 16 * 16;
  for (const l of E.lotes || []) {
    const dx = l.x * V.k + V.tx - px, dy = l.y * V.k + V.ty - py, d2 = dx * dx + dy * dy;
    if (d2 < distancia) { distancia = d2; mejor = l; }
  }
  return mejor;
}

function posicion(e) {
  const r = lienzoDatos.getBoundingClientRect();
  return { x: e.clientX - r.left, y: e.clientY - r.top };
}

function colocar(caja, px, py) {
  caja.hidden = false;
  const w = caja.offsetWidth, h = caja.offsetHeight;
  caja.style.left = `${limitar(px + 16, 8, Math.max(8, ancho - w - 8))}px`;
  caja.style.top = `${limitar(py + 16, 8, Math.max(8, alto - h - 8))}px`;
}

function ocultarGlobo() { $('#globo').hidden = true; }

function mostrarGlobo(l, px, py) {
  const tipo = E.puesto.get(l.id);
  let html = `<strong>Lote ${esc(l.id)}</strong>${l.hipotetico ? ' (hipotético)' : ''} · factor de zona ×${l.factor.toLocaleString('es-CO')}`;
  if (tipo) {
    const fila = E.ev.filas.find((f) => f.lote === l.id);
    html += `<div class="fila"><i class="punto" style="background:${color(tipo)}"></i><strong>${esc(E.tipo[tipo].estacion)}</strong></div>`
      + `<div class="fila"><span>Costo</span><span>${num(fila.costo)} M</span></div>`
      + `<div class="fila"><span>Alcance por vía</span><span>${radioTexto(E.tipo[tipo].radio_m)}</span></div>`
      + `<div class="fila"><span>Casos a su alcance</span><span>${num(fila.alcance)}</span></div>`
      + `<div class="fila"><span>Casos nuevos que aporta</span><span>${num(fila.nuevos)}</span></div>`;
  } else {
    for (const t of E.d.tipos) {
      const o = l.opciones[t.id];
      html += `<div class="fila"><i class="punto" style="background:${color(t.id)}"></i><span>${corto(t.id)} · ${num(o.incidentes.length)} casos</span><span>${num(o.costo)} M</span></div>`;
    }
  }
  if (E.metodo === 'manual') html += `<div class="pista">Clic para ${tipo ? 'cambiar o quitar' : 'poner una estación'}</div>`;
  const globo = $('#globo');
  globo.innerHTML = html;
  colocar(globo, px, py);
}

function cerrarMenu() {
  if (!E.menu && !E.previa) return;
  E.menu = null; E.previa = null;
  $('#menu-lote').hidden = true;
  pedirDibujo(false);
}

function abrirMenu(l) {
  ocultarGlobo();
  E.menu = l.id;
  callesDe(l.id);
  const actual = new Map(E.manual).get(l.id);
  const sinEste = E.manual.filter(([lote]) => lote !== l.id);
  const antes = evaluar(E.manual);
  let html = `<header><strong>Lote ${esc(l.id)}${l.hipotetico ? ' (hipotético)' : ''}</strong><span>factor de zona ×${l.factor.toLocaleString('es-CO')}</span></header>`;
  for (const t of E.d.tipos) {
    const con = evaluar([...sinEste, [l.id, t.id]]);
    const cabe = con.costo <= E.presupuesto;
    const cambio = con.valor - antes.valor;
    const detalle = actual === t.id ? 'Ya está aquí'
      : !cabe ? `No alcanza: faltan ${num(con.costo - E.presupuesto)} M`
      : `${cambio >= 0 ? '+' : '−'}${num(Math.abs(cambio))} de valor · alcance ${radioTexto(t.radio_m)}`;
    html += `<button type="button" class="opcion" data-tipo="${t.id}" aria-pressed="${actual === t.id}" ${cabe || actual === t.id ? '' : 'disabled'}>`
      + `<i class="punto" style="background:${color(t.id)}"></i><b>${corto(t.id)}</b><span class="costo">${num(l.opciones[t.id].costo)} M</span>`
      + `<small>${detalle}</small></button>`;
  }
  if (actual) html += '<button type="button" class="enlace quitar" data-quitar>Quitar la estación</button>';
  const menu = $('#menu-lote');
  menu.innerHTML = html;
  colocar(menu, l.x * V.k + V.tx, l.y * V.k + V.ty);
  pedirDibujo(false);
}

$('#menu-lote').addEventListener('click', (e) => {
  const boton = e.target.closest('button');
  if (!boton || !E.menu) return;
  const lote = E.menu;
  const sinEste = E.manual.filter(([l]) => l !== lote);
  if (boton.dataset.quitar !== undefined) E.manual = sinEste;
  else if (boton.getAttribute('aria-pressed') !== 'true') E.manual = [...sinEste, [lote, boton.dataset.tipo]];
  cerrarMenu();
  recalcular();
});
$('#menu-lote').addEventListener('pointerover', (e) => {
  const boton = e.target.closest('button.opcion');
  const previa = boton && E.menu ? { lote: E.menu, tipo: boton.dataset.tipo } : null;
  if ((previa && previa.tipo) !== (E.previa && E.previa.tipo)) { E.previa = previa; pedirDibujo(false); }
});
$('#menu-lote').addEventListener('pointerleave', () => { if (E.previa) { E.previa = null; pedirDibujo(false); } });

const punteros = new Map();
let gesto = null;

lienzoDatos.addEventListener('pointerdown', (e) => {
  lienzoDatos.setPointerCapture(e.pointerId);
  const p = posicion(e);
  punteros.set(e.pointerId, p);
  if (punteros.size === 1) gesto = { x0: p.x, y0: p.y, movido: false, pinza: 0 };
  else if (punteros.size === 2) {
    const [a, b] = [...punteros.values()];
    gesto.pinza = Math.hypot(a.x - b.x, a.y - b.y); gesto.movido = true;
  }
});

lienzoDatos.addEventListener('pointermove', (e) => {
  const p = posicion(e), previo = punteros.get(e.pointerId);
  if (!previo) {
    if (!E.d || !E.ev) return;
    const l = loteCerca(p.x, p.y);
    lienzoDatos.classList.toggle('sobre-lote', Boolean(l) && E.metodo === 'manual');
    const id = l ? l.id : null;
    if (id !== E.foco) { E.foco = id; pintarFocoTabla(); pedirDibujo(false); }
    if (l && !E.menu) mostrarGlobo(l, p.x, p.y); else ocultarGlobo();
    return;
  }
  if (punteros.size === 1) {
    if (!gesto.movido && Math.hypot(p.x - gesto.x0, p.y - gesto.y0) < 4) return;
    gesto.movido = true;
    lienzoDatos.classList.add('arrastrando');
    V.tx += p.x - previo.x; V.ty += p.y - previo.y; V.libre = true;
    punteros.set(e.pointerId, p);
    cerrarMenu(); ocultarGlobo();
    pedirDibujo(true);
  } else if (punteros.size === 2) {
    punteros.set(e.pointerId, p);
    const [a, b] = [...punteros.values()];
    const separacion = Math.hypot(a.x - b.x, a.y - b.y);
    if (gesto.pinza > 0 && separacion > 0) zoomEn((a.x + b.x) / 2, (a.y + b.y) / 2, separacion / gesto.pinza);
    gesto.pinza = separacion;
  }
});

function soltar(e) {
  if (!punteros.has(e.pointerId)) return;
  punteros.delete(e.pointerId);
  lienzoDatos.classList.remove('arrastrando');
  if (punteros.size === 0 && gesto && !gesto.movido && e.type === 'pointerup') {
    const p = posicion(e), l = loteCerca(p.x, p.y);
    if (l && E.metodo === 'manual') abrirMenu(l);
    else {
      cerrarMenu();
      if (l) anunciar('Para editar el mapa, elige «Tu propuesta» en el panel', 2600);
    }
  }
}
lienzoDatos.addEventListener('pointerup', soltar);
lienzoDatos.addEventListener('pointercancel', soltar);
lienzoDatos.addEventListener('pointerleave', () => {
  ocultarGlobo();
  if (E.foco && !punteros.size) { E.foco = null; pintarFocoTabla(); pedirDibujo(false); }
});
lienzoDatos.addEventListener('wheel', (e) => {
  e.preventDefault();
  const p = posicion(e);
  zoomEn(p.x, p.y, Math.exp(-e.deltaY * 0.0015));
}, { passive: false });
lienzoDatos.addEventListener('dblclick', (e) => { const p = posicion(e); zoomEn(p.x, p.y, 1.8); });

$('#acercar').addEventListener('click', () => zoomEn(ancho / 2, alto / 2, 1.5));
$('#alejar').addEventListener('click', () => zoomEn(ancho / 2, alto / 2, 1 / 1.5));
$('#encuadrar').addEventListener('click', () => { encuadrar(); cerrarMenu(); pedirDibujo(true); });

new ResizeObserver(() => {
  const antes = { ancho, alto };
  ajustarLienzos();
  if (!E.d) return;
  if (!antes.ancho || !V.libre) encuadrar();
  else { V.tx += (ancho - antes.ancho) / 2; V.ty += (alto - antes.alto) / 2; }
  cerrarMenu();
  pedirDibujo(true);
}).observe(mapa);

/* ---------------- Animación paso a paso ---------------- */

let relojAnuncio = null;
function anunciar(html, duracion) {
  const caja = $('#paso');
  clearTimeout(relojAnuncio);
  caja.hidden = !html;
  if (html) caja.innerHTML = html;
  if (html && duracion) relojAnuncio = setTimeout(() => { caja.hidden = true; }, duracion);
}

function detenerAnimacion() {
  if (E.temporizador) clearInterval(E.temporizador);
  E.temporizador = null;
  if (E.pasos != null) { E.pasos = null; anunciar(null); }
  $('#animar').textContent = '▶ Ver cómo decide';
}

function animar() {
  if (E.temporizador) { detenerAnimacion(); recalcular(); return; }
  const total = listaActual().length;
  if (!total) return;
  cerrarMenu();
  E.pasos = 0;
  $('#animar').textContent = '■ Detener';
  const esLocal = E.metodo === 'local';
  anunciar(esLocal ? 'Propuesta final de la búsqueda local, estación por estación…' : 'Sin estaciones: el algoritmo empieza a elegir…');
  recalcular();
  E.temporizador = setInterval(() => {
    E.pasos++;
    recalcular();
    const f = E.ev.filas[E.pasos - 1];
    anunciar(`${esLocal ? 'Estación' : 'Paso'} ${E.pasos} de ${total} · <b>${esc(f.lote)} → ${corto(f.tipo)}</b> · +${num(f.aporte)} de valor por ${num(f.costo)} M`);
    if (E.pasos >= total) {
      clearInterval(E.temporizador); E.temporizador = null;
      $('#animar').textContent = '▶ Ver cómo decide';
      setTimeout(() => { if (!E.temporizador && E.pasos != null) { E.pasos = null; anunciar(null); recalcular(); } }, 2200);
    }
  }, limitar(9000 / total, 380, 1200));
}
$('#animar').addEventListener('click', animar);

/* ---------------- Panel ---------------- */

function pintarEscenarios(activo) {
  $('#escenarios').innerHTML = ESCENARIOS.map((e) =>
    `<button type="button" role="radio" aria-checked="${e.id === activo}" data-id="${esc(e.id)}"${e.oficial ? '' : ' title="Zona no oficial: parte de sus lotes son hipotéticos"'}>${esc(e.titulo)}</button>`).join('');
}
$('#escenarios').addEventListener('click', (e) => {
  const boton = e.target.closest('button');
  if (boton && boton.dataset.id !== E.nombre) cargarEscenario(boton.dataset.id);
});

function pintarLeyenda() {
  const tipos = E.d.tipos.map((t) =>
    `<li><button type="button" data-capa="${t.id}" aria-pressed="${E.capas[t.id] !== false}" title="Mostrar u ocultar su cobertura"><i class="punto" style="background:${color(t.id)}"></i>${mayuscula(t.id)} → ${corto(t.id)} · alcance ${radioTexto(t.radio_m)}</button></li>`).join('');
  $('#leyenda').innerHTML = tipos
    + '<li><i class="punto"></i>incidente cubierto<i class="punto hueco separa"></i>sin cubrir</li>'
    + '<li><i class="cuadro"></i>lote libre<i class="trazo separa"></i>vías al alcance de una estación</li>'
    + (E.lotes.some((l) => l.hipotetico) ? '<li><i class="cuadro punteado"></i>lote hipotético (zona no oficial)</li>' : '');
}

$('#leyenda').addEventListener('click', (e) => {
  const boton = e.target.closest('button[data-capa]');
  if (!boton) return;
  E.capas[boton.dataset.capa] = E.capas[boton.dataset.capa] === false;
  pintarLeyenda(); pedirDibujo(false);
});

function potencia(lotes) {
  const log = lotes * Math.log10(4), exp = Math.floor(log);
  if (exp < 7) return `4<sup>${lotes}</sup> = ${num(4 ** lotes)}`;
  return `4<sup>${lotes}</sup> ≈ ${(10 ** (log - exp)).toLocaleString('es-CO', { maximumFractionDigits: 1 })} × 10<sup>${exp}</sup>`;
}

function notaOptimo() {
  const lotes = E.d.lotes.length, o = E.optimo;
  if (!E.d.exacto_viable) return { valor: null, nota: `No viable: habría que revisar ${potencia(lotes)} propuestas` };
  if (!o) return { valor: null, nota: 'Clic para calcularlo' };
  const segundos = o.segundos < 0.1 ? 'menos de 0,1 s' : `${o.segundos.toLocaleString('es-CO', { maximumFractionDigits: o.segundos < 10 ? 1 : 0 })} s`;
  if (o.estado === 'corriendo') {
    return { valor: o.mejor_valor || null, nota: `Explorando… ${num(o.nodos)} ramas · ${num(o.podas)} podadas · ${segundos}` };
  }
  if (!o.probado) return { valor: o.valor, nota: `Sin probar: se agotó el tiempo tras ${num(o.nodos)} ramas` };
  const fraccion = (100 * o.nodos / 4 ** lotes).toLocaleString('es-CO', { maximumSignificantDigits: 1 });
  return { valor: o.valor, nota: `Probado en ${segundos}: revisó ${num(o.nodos)} ramas, el ${fraccion} % de ${potencia(lotes)}` };
}

function notaManual(ev) {
  if (!E.manual.length) return { texto: 'Elígela y haz clic en un lote del mapa' };
  if (ev.costo > E.presupuesto) return { texto: `Excede el presupuesto en ${num(ev.costo - E.presupuesto)} M` };
  const mejor = Math.max(...HEURISTICAS.map((h) => E.heuristicas[h].valor));
  const o = E.optimo && E.optimo.estado === 'listo' && E.optimo.probado ? E.optimo.valor : null;
  if (o != null && ev.valor >= o) return { texto: '¡Igualaste el óptimo! No existe una propuesta mejor.', logro: true };
  if (ev.valor > mejor) return { texto: '¡Superaste a las tres heurísticas!', logro: true };
  if (ev.valor === mejor) return { texto: 'Empataste con la mejor heurística', logro: true };
  return { texto: `Te faltan ${num(mejor - ev.valor)} para alcanzar a la mejor heurística` };
}

function pintarPropuestas() {
  const tope = E.d.valor_alcanzable, mejor = mejorHeuristica();
  const optimo = E.optimo && E.optimo.estado === 'listo' && E.optimo.probado ? E.optimo.valor : null;
  const manual = evaluar(E.manual);
  $('#propuestas').innerHTML = METODOS.map((m) => {
    let valor = null, nota = '', logro = false, etiqueta = '', inactivo = false;
    if (HEURISTICAS.includes(m.id)) {
      valor = E.heuristicas[m.id].valor;
      nota = optimo != null ? `${pct(valor, optimo)} del óptimo` : `${pct(valor, tope)} del tope`;
      const partida = E.heuristicas[m.id].valor_inicial;
      if (partida != null && valor > partida) nota += ` · +${num(valor - partida)} sobre la mejor voraz`;
      if (m.id === mejor) etiqueta = '<span class="p-etiqueta">mejor heurística</span>';
    } else if (m.id === 'optimo') {
      ({ valor, nota } = notaOptimo());
      inactivo = !E.d.exacto_viable;
    } else {
      valor = E.manual.length ? manual.valor : null;
      ({ texto: nota, logro = false } = notaManual(manual));
    }
    return `<button type="button" class="propuesta" role="radio" data-id="${m.id}" aria-checked="${m.id === E.metodo}" ${inactivo ? 'aria-disabled="true"' : ''}>`
      + `<span><span class="p-nombre">${m.nombre}</span>${etiqueta}</span>`
      + `<span class="p-valor">${valor == null ? '—' : num(valor)}</span>`
      + `<span class="p-barra"><i style="width:${valor == null ? 0 : limitar(100 * valor / tope, 0, 100)}%"></i></span>`
      + `<span class="p-nota${logro ? ' logro' : ''}">${nota}</span></button>`;
  }).join('');
}
$('#propuestas').addEventListener('click', (e) => {
  const fila = e.target.closest('.propuesta');
  if (!fila || fila.getAttribute('aria-disabled') === 'true') return;
  detenerAnimacion(); cerrarMenu();
  E.metodo = fila.dataset.id;
  if (E.metodo === 'optimo' && !E.optimo) pedirOptimo();
  if (E.metodo === 'manual' && !E.manual.length) anunciar('Haz clic en un lote (cuadro con +) para poner una estación', 4000);
  recalcular();
});

function pintarResultado() {
  const ev = E.ev, d = E.d;
  const totalCasos = d.incidentes.nodo.length;
  const cubiertos = Object.values(ev.casos).reduce((a, b) => a + b, 0);
  const excede = ev.costo > E.presupuesto;
  $('#cifras').innerHTML =
    `<div class="cifra"><div class="c-titulo">Valor</div><div class="c-valor">${num(ev.valor)}</div><div class="c-sub">${pct(ev.valor, d.valor_alcanzable)} del tope</div></div>`
    + `<div class="cifra"><div class="c-titulo">Inversión (millones)</div><div class="c-valor">${num(ev.costo)}</div>`
    + `<div class="c-sub${excede ? ' alerta' : ''}">${excede ? `⚠ excede por ${num(ev.costo - E.presupuesto)}` : `sobran ${num(E.presupuesto - ev.costo)}`}</div>`
    + `<div class="medidor${excede ? ' alerta' : ''}"><i style="width:${limitar(100 * ev.costo / E.presupuesto, 0, 100)}%"></i></div></div>`
    + `<div class="cifra"><div class="c-titulo">Casos cubiertos</div><div class="c-valor">${num(cubiertos)}</div><div class="c-sub">${pct(cubiertos, totalCasos)} de ${num(totalCasos)}</div></div>`;
  $('#por-tipo').innerHTML = d.tipos.map((t) =>
    `<div class="tipo-fila"><i class="punto" style="background:${color(t.id)}"></i><span>${mayuscula(t.id)} · ×${t.peso}</span>`
    + `<div class="medidor"><i style="width:${E.totalTipo[t.id] ? 100 * ev.casos[t.id] / E.totalTipo[t.id] : 0}%;background:${color(t.id)}"></i></div>`
    + `<span class="cuenta">${num(ev.casos[t.id])} / ${num(E.totalTipo[t.id])}</span></div>`).join('');
}

function pintarTabla() {
  const cuerpo = $('#tabla tbody');
  if (!E.ev.filas.length) {
    const texto = E.metodo === 'manual' ? 'Tu propuesta está vacía: haz clic en un lote del mapa.'
      : E.metodo === 'optimo' && (!E.optimo || E.optimo.estado !== 'listo') ? 'El óptimo aún no está calculado.'
      : 'Sin estaciones.';
    cuerpo.innerHTML = `<tr><td class="vacio" colspan="6">${texto}</td></tr>`;
    return;
  }
  cuerpo.innerHTML = E.ev.filas.map((f, i) =>
    `<tr data-lote="${esc(f.lote)}"><td>${i + 1}</td><td>${esc(f.lote)}</td>`
    + `<td><i class="punto" style="background:${color(f.tipo)}"></i>${corto(f.tipo)}</td>`
    + `<td class="num">${num(f.costo)}</td><td class="num">${num(f.nuevos)}</td><td class="num">${num(f.aporte)}</td></tr>`).join('');
  pintarFocoTabla();
}

function pintarFocoTabla() {
  for (const fila of document.querySelectorAll('#tabla tbody tr')) fila.classList.toggle('foco', fila.dataset.lote === E.foco);
}
$('#tabla tbody').addEventListener('pointerover', (e) => {
  const fila = e.target.closest('tr[data-lote]');
  const id = fila ? fila.dataset.lote : null;
  if (id !== E.foco) { E.foco = id; pintarFocoTabla(); pedirDibujo(false); }
});
$('#tabla tbody').addEventListener('pointerleave', () => { if (E.foco) { E.foco = null; pintarFocoTabla(); pedirDibujo(false); } });

function pintarPanel() {
  const d = E.d, metodo = METODOS.find((m) => m.id === E.metodo);
  $('#presupuesto-valor').textContent = `${num(E.presupuesto)} millones`;
  $('#presupuesto-original').hidden = E.presupuesto === d.presupuesto;
  pintarPropuestas();
  $('#tope').textContent = `Valor = casos cubiertos × prioridad. El tope (${num(d.valor_alcanzable)}) es lo que se cubriría sin límite de presupuesto.`;
  $('#explicacion').textContent = metodo.explicacion;
  const esHeuristica = HEURISTICAS.includes(E.metodo);
  $('#animar').hidden = !esHeuristica;
  $('#animar').disabled = !listaActual().length;
  $('#copiar').hidden = E.metodo !== 'manual';
  $('#vaciar').hidden = E.metodo !== 'manual' || !E.manual.length;
  pintarResultado();
  pintarTabla();
}

$('#copiar').addEventListener('click', () => { cerrarMenu(); E.manual = E.heuristicas[mejorHeuristica()].estaciones.map((par) => [...par]); recalcular(); });
$('#vaciar').addEventListener('click', () => { cerrarMenu(); E.manual = []; recalcular(); });

let relojPresupuesto = null;
function cambiarPresupuesto(valor) {
  if (!E.d || valor === E.presupuesto) return;
  detenerAnimacion(); cerrarMenu(); clearTimeout(E.sondeo);
  E.presupuesto = valor; E.optimo = null;
  $('#presupuesto-valor').textContent = `${num(valor)} millones`;
  clearTimeout(relojPresupuesto);
  relojPresupuesto = setTimeout(async () => {
    try { await actualizarHeuristicas(); } catch (error) { aviso(`No se pudo calcular: ${error.message}`); return; }
    if (E.d.lotes.length <= 8 || E.metodo === 'optimo') pedirOptimo();
    recalcular();
  }, 120);
}
$('#presupuesto').addEventListener('input', (e) => cambiarPresupuesto(Number(e.target.value)));
$('#presupuesto-original').addEventListener('click', () => { $('#presupuesto').value = E.d.presupuesto; cambiarPresupuesto(E.d.presupuesto); });

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') cerrarMenu(); });

async function iniciar() {
  try { ESCENARIOS = await api('/api/instancias'); } catch (error) { /* se queda la lista de respaldo */ }
  ajustarLienzos();
  cargarEscenario(ESCENARIOS.some((e) => e.id === 'comuna') ? 'comuna' : ESCENARIOS[0].id);
}
iniciar();
