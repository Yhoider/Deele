const colores = { hurto: '#2d6cdf', accidente: '#f6a21a', incendio: '#ef5f65' };
const $ = (selector) => document.querySelector(selector);
const formato = new Intl.NumberFormat('es-CO');
let datosActuales;

function punto(coordenadas, limites) {
  const [latitud, longitud] = coordenadas;
  const margen = 42;
  return [margen + ((longitud - limites.minLon) / (limites.maxLon - limites.minLon || 1)) * (1000 - margen * 2), 650 - margen - ((latitud - limites.minLat) / (limites.maxLat - limites.minLat || 1)) * (650 - margen * 2)];
}

function dibujarMapa(datos) {
  const svg = $('#map');
  const nodos = datos.nodos;
  const coordenadas = Object.values(nodos);
  const limites = {
    minLat: Math.min(...coordenadas.map(([lat]) => lat)), maxLat: Math.max(...coordenadas.map(([lat]) => lat)),
    minLon: Math.min(...coordenadas.map(([, lon]) => lon)), maxLon: Math.max(...coordenadas.map(([, lon]) => lon)),
  };
  const cubiertos = Object.fromEntries(Object.entries(datos.cubiertos).map(([tipo, ids]) => [tipo, new Set(ids.map(String))]));
  const elegidos = Object.fromEntries(datos.propuesta.estaciones);
  const lineas = datos.aristas.map(([origen, destino]) => {
    const a = punto(nodos[origen], limites), b = punto(nodos[destino], limites);
    return `<line class="road" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>`;
  }).join('');
  const incidentes = Object.entries(datos.incidentes).map(([id, incidente]) => {
    const [x, y] = punto(nodos[incidente.nodo], limites), color = colores[incidente.tipo];
    const lleno = cubiertos[incidente.tipo].has(id);
    return `<circle class="incident" cx="${x}" cy="${y}" r="${Object.keys(datos.incidentes).length < 1500 ? 3.5 : 2}" fill="${lleno ? color : '#f8fafc'}" stroke="${color}"/>`;
  }).join('');
  const lotes = Object.entries(datos.lotes).map(([lote, dato]) => {
    const [x, y] = punto(nodos[dato.nodo], limites), color = colores[elegidos[lote]] || '#a5b4c3';
    return `<rect class="lot" x="${x - 5}" y="${y - 5}" width="10" height="10" rx="2" fill="${color}"/>`;
  }).join('');
  svg.innerHTML = `<g>${lineas}</g><g>${incidentes}</g><g>${lotes}</g>`;
}

function llenarInterfaz(datos) {
  const propuesta = datos.propuesta;
  const casos = Object.values(propuesta.casos_cubiertos).reduce((suma, actual) => suma + actual, 0);
  const total = Object.keys(datos.incidentes).length;
  $('#valor').textContent = formato.format(propuesta.valor);
  $('#costo').textContent = `${formato.format(propuesta.costo_total)} M`;
  $('#presupuesto').textContent = `de ${formato.format(datos.parametros.presupuesto_millones)} M disponibles`;
  $('#casos').textContent = formato.format(casos);
  $('#porcentaje').textContent = `${total ? Math.round(casos * 100 / total) : 0}% del histórico analizado`;
  $('#cantidad-estaciones').textContent = propuesta.estaciones.length;
  $('#justificacion').textContent = datos.justificacion;
  $('#titulo-propuesta').textContent = `Propuesta para ${datos.instancia}`;
  $('#metodo-usado').textContent = $('#metodo').value === 'exacta' ? 'ÓPTIMO EXACTO' : 'HEURÍSTICA';
  $('#tabla-estaciones').innerHTML = datos.filas.map((fila) => `<tr><td>${fila.lote}</td><td>${fila.tipo[0].toUpperCase() + fila.tipo.slice(1)}</td><td>${formato.format(fila.costo)} M</td><td>${fila.casos}</td><td><span class="priority p-${fila.tipo}">${fila.tipo}</span></td></tr>`).join('');
  $('#barras-cobertura').innerHTML = Object.entries(propuesta.casos_cubiertos).map(([tipo, cantidad]) => {
    const totalTipo = Object.values(datos.incidentes).filter((incidente) => incidente.tipo === tipo).length;
    const porcentaje = totalTipo ? cantidad * 100 / totalTipo : 0;
    return `<div><div class="bar-label"><span>${tipo}</span><span>${cantidad} / ${totalTipo}</span></div><div class="bar"><i style="width:${porcentaje}%;background:${colores[tipo]}"></i></div></div>`;
  }).join('');
  dibujarMapa(datos);
}

async function cargar() {
  const instancia = $('#instancia').value;
  const metodo = $('#metodo').value;
  if (instancia === 'ciudad' && metodo === 'exacta') $('#metodo').value = 'heuristica';
  $('#actualizar').disabled = true;
  $('#estado').textContent = 'Calculando propuesta con el motor del proyecto…';
  try {
    const respuesta = await fetch(`/api/propuesta?instancia=${instancia}&metodo=${$('#metodo').value}`);
    const datos = await respuesta.json();
    if (!respuesta.ok) throw new Error(datos.error);
    datosActuales = datos;
    llenarInterfaz(datos);
    $('#estado').textContent = 'Análisis actualizado con datos reales.';
  } catch (error) {
    $('#estado').textContent = `No se pudo cargar: ${error.message}`;
  } finally {
    $('#actualizar').disabled = false;
  }
}

$('#actualizar').addEventListener('click', cargar);
$('#instancia').addEventListener('change', cargar);
$('#metodo').addEventListener('change', cargar);
window.addEventListener('resize', () => datosActuales && dibujarMapa(datosActuales));
cargar();
