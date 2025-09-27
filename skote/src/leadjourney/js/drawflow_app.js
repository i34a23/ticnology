export function initDrawflow(journeyId, initialData, fetchData) {
  const container = document.getElementById('drawflow');
  if (!window.Drawflow || !container) {
    console.error('❌ Drawflow no está definido o falta el contenedor DOM');
    alert('No se pudo inicializar el editor. Verifica que Drawflow está bien importado y el contenedor existe.');
    return;
  }

  const editor = new window.Drawflow(container);
  editor.reroute = true;
  editor.editor_mode = 'edit';
  editor.start();

  console.log('✅ Editor Drawflow inicializado.');

  if ('zoom_value' in editor) {
    editor.zoom_value = 0.9;
  } else if (typeof editor.zoom_out === 'function') {
    editor.zoom_out();
  }

  function sanitizeDrawflow(raw) {
    const safeBase = { drawflow: { Home: { data: {} } } };
    if (!raw || typeof raw !== 'object' || !raw.drawflow || !raw.drawflow.Home) {
      console.warn('⚠️ Datos drawflow corruptos. Se usará base vacía.');
      return safeBase;
    }

    const df = raw.drawflow;
    const home = df.Home;
    const data = (home && typeof home === 'object' && home.data && typeof home.data === 'object')
      ? home.data : {};

    const sanitizedNodes = {};

    Object.entries(data).forEach(([id, node]) => {
      try {
        if (!node || typeof node !== 'object') return;

        const name = typeof node.name === 'string' && node.name.trim() ? node.name : `node_${id}`;
        const pos_x = Number.isFinite(node.pos_x) ? node.pos_x : 120;
        const pos_y = Number.isFinite(node.pos_y) ? node.pos_y : 120;
        
        // HTML por defecto con conectores arriba y abajo
        const defaultHtml = `
          <div class="flow-node-box">
            <div class="input input_1" style="position:absolute; top: -8px; left: 50%; transform: translateX(-50%);"></div>
            <div class="output output_1" style="position:absolute; bottom: -8px; left: 50%; transform: translateX(-50%);"></div>
            <strong>${name}</strong>
          </div>
        `;
        
        const html = (typeof node.html === 'string' && node.html.trim())
          ? node.html : defaultHtml;
        const className = typeof node.class === 'string' ? node.class : 'flow-node';
        const typenode = typeof node.typenode === 'boolean' ? node.typenode : false;

        const nodeData = (node.data && typeof node.data === 'object') ? node.data : {};

        // Función para normalizar puertos - FORZAR solo 1 input y 1 output
        function normalizePorts(ports, keyPrefix) {
          const out = {};
          if (ports && typeof ports === 'object') {
            // Buscar el primer puerto válido o crear uno por defecto
            const firstPortKey = Object.keys(ports)[0];
            if (firstPortKey && ports[firstPortKey]) {
              const connections = (ports[firstPortKey] && Array.isArray(ports[firstPortKey].connections))
                ? ports[firstPortKey].connections.filter(c => c && typeof c === 'object')
                : [];
              out[`${keyPrefix}_1`] = { connections };
            } else {
              out[`${keyPrefix}_1`] = { connections: [] };
            }
          } else {
            out[`${keyPrefix}_1`] = { connections: [] };
          }
          return out;
        }

        // Solo permitir 1 input y 1 output
        const inputs = normalizePorts(node.inputs, 'input');
        const outputs = normalizePorts(node.outputs, 'output');

        sanitizedNodes[id] = {
          id: node.id ?? (isNaN(id) ? id : Number(id)),
          name,
          data: nodeData,
          class: className,
          html,
          typenode,
          inputs,
          outputs,
          pos_x,
          pos_y
        };
      } catch (e) {
        console.warn('⚠️ Nodo descartado por corrupción de datos:', id, e);
      }
    });

    return { drawflow: { Home: { data: sanitizedNodes } } };
  }

  function loadJourneyData() {
    console.log('📡 Solicitando datos del journey...');
    fetchData(journeyId)
      .then(raw => {
        const safe = sanitizeDrawflow(raw);
        try {
          editor.import(safe);
          console.log('✅ Flowchart importado exitosamente:', safe);
        } catch (err) {
          console.error('❌ Error al importar drawflow. Se carga vacío:', err);
          editor.clear();
          editor.import(initialData);
        }
      })
      .catch(error => {
        console.error('❌ Error al obtener datos desde fetchData:', error);
        editor.clear();
        editor.import(initialData);
      });
  }

  loadJourneyData();

  return editor;
}