document.addEventListener("DOMContentLoaded", async () => {
  const canvasId = "jsplumb-canvas";
  const journeyId = document.getElementById(canvasId).dataset.journeyId;

  function getCSRFToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute('content') : '';
  }

  const instance = jsPlumb.getInstance({
    Connector: ["Flowchart", { stub: 30, gap: 2, cornerRadius: 5 }],
    Endpoint: ["Dot", { radius: 4 }],
    PaintStyle: { stroke: "#4caf50", strokeWidth: 2 },
    HoverPaintStyle: { stroke: "#2196f3", strokeWidth: 3 },
    Anchors: ["Bottom", "Top"],
    Container: canvasId,
  });

  instance.registerConnectionType("basic", {
    anchor: ["Bottom", "Top"],
    connector: "Flowchart",
  });

  // --- Botón eliminar conexiones ---
  const deleteButton = document.createElement("div");
  deleteButton.classList.add("connection-delete-button");
  deleteButton.innerHTML = "×";
  deleteButton.style.display = "none";
  document.getElementById(canvasId).appendChild(deleteButton);

  let currentConnection = null;
  let hideTimeout = null;
  let lastMousePosition = { x: 0, y: 0 };

  // --- Cargar nodos y conexiones ---
  instance.bind("ready", async () => {
    const res = await fetch(`/leadjourney/api/journey_data/${journeyId}`);
    const data = await res.json();

    data.nodes.forEach((node) => {
      createNode(instance, node.id, node.name, node.x, node.y, node.prompt);
    });

    data.connections.forEach((conn) => {
      const connection = instance.connect({
        uuids: [`${conn.source}-output`, `${conn.target}-input`],
        type: "basic",
      });
      setupConnectionEvents(connection);
    });

    // Guardar nuevas conexiones
    instance.bind("connection", async (info) => {
      const sourceId = info.sourceId.replace("nodo-", "");
      const targetId = info.targetId.replace("nodo-", "");

      try {
        const response = await fetch("/leadjourney/api/create_connection", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": getCSRFToken(),
          },
          body: JSON.stringify({
            journey_id: journeyId,
            source_id: sourceId,
            target_id: targetId,
          }),
        });
        const result = await response.json();
        if (result.status !== "success") {
          showToast("No se pudo guardar la conexión", "danger");
        }
      } catch (err) {
        console.error("Error guardando conexión:", err);
        showToast("Error de red al guardar conexión", "danger");
      }

      setupConnectionEvents(info.connection);
    });

    centerViewOnNodes(data.nodes);
  });

  // --- Configuración de conexiones (hover + delete) ---
  function setupConnectionEvents(connection) {
    const el = connection.canvas;
    if (!el) return;

    el.style.cursor = "pointer";
    el.addEventListener("mouseenter", (e) => {
      if (hideTimeout) clearTimeout(hideTimeout);
      currentConnection = connection;
      updateDeleteButtonPosition(e);
      deleteButton.style.display = "block";
    });
    el.addEventListener("mouseleave", () => {
      hideTimeout = setTimeout(() => {
        deleteButton.style.display = "none";
        currentConnection = null;
      }, 2000);
    });
  }

  function updateDeleteButtonPosition(event) {
    const containerEl = document.getElementById(canvasId);
    const rect = containerEl.getBoundingClientRect();
    const x = event.clientX - rect.left + containerEl.scrollLeft - 10;
    const y = event.clientY - rect.top + containerEl.scrollTop - 10;
    deleteButton.style.left = `${x}px`;
    deleteButton.style.top = `${y}px`;
    lastMousePosition = { x, y };
  }

  deleteButton.addEventListener("click", async () => {
    if (!currentConnection) return;
    if (!confirm("¿Eliminar esta conexión?")) return;

    const sourceId = currentConnection.sourceId.replace("nodo-", "");
    const targetId = currentConnection.targetId.replace("nodo-", "");

    try {
      const res = await fetch("/leadjourney/api/delete_connection", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ source_id: sourceId, target_id: targetId }),
      });
      const result = await res.json();
      if (result.status === "success") {
        instance.deleteConnection(currentConnection);
        showToast("Conexión eliminada");
      } else {
        showToast("Error al eliminar conexión", "danger");
      }
    } catch (err) {
      console.error("Error eliminando conexión:", err);
    }

    deleteButton.style.display = "none";
    currentConnection = null;
  });

  // --- Guardar posición de nodo ---
  async function saveNodePosition(nodeId, x, y) {
    try {
      await fetch("/leadjourney/api/save_positions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCSRFToken(),
        },
        body: JSON.stringify({ node_id: nodeId, x, y }),
      });
    } catch (err) {
      console.error("Error guardando posición:", err);
    }
  }

  // --- Crear nodo visual ---
  function createNode(instance, id, title, x, y, promptValue = "") {
    const node = document.createElement("div");
    node.className = "node-box";
    node.id = `nodo-${id}`;
    node.style.left = `${x || 100}px`;
    node.style.top = `${y || 100}px`;
    node.innerHTML = `<strong>${title}</strong>`;
    node.dataset.prompt = promptValue;
    document.getElementById(canvasId).appendChild(node);

    instance.draggable(node, {
      stop: () => {
        const rect = node.getBoundingClientRect();
        const canvasRect = document.getElementById(canvasId).getBoundingClientRect();
        saveNodePosition(id, rect.left - canvasRect.left, rect.top - canvasRect.top);
      },
    });

    node.addEventListener("dblclick", async () => {
      document.getElementById("edit-node-id").value = id;
      document.getElementById("edit-node-name").value = title;
      document.getElementById("edit-node-prompt").value = node.dataset.prompt || "";

      // Traer ramas desde /api/nodos/<id>
      const res = await fetch(`/leadjourney/api/nodos/${id}`);
      const nodo = await res.json();
      const container = document.getElementById("edit-next-steps-container");
      container.innerHTML = "";
      nodo.next_steps.forEach((s) => {
        const div = document.createElement("div");
        div.innerHTML = `
          <input type="hidden" value="${s.id}">
          <input type="text" class="form-control mb-1" value="${s.etiqueta || ''}" placeholder="Etiqueta">
          <input type="text" class="form-control mb-1" value="${s.condicion_logica || ''}" placeholder="Condición">
        `;
        container.appendChild(div);
      });

      new bootstrap.Modal(document.getElementById("editNodeModal")).show();
    });

    instance.addEndpoint(node, { uuid: `${id}-output`, anchor: "Bottom", isSource: true, maxConnections: -1 });
    instance.addEndpoint(node, { uuid: `${id}-input`, anchor: "Top", isTarget: true, maxConnections: -1 });
  }

  // --- Centrar vista ---
  function centerViewOnNodes(nodes) {
    if (!nodes.length) return;
    const minX = Math.min(...nodes.map((n) => n.x));
    const maxX = Math.max(...nodes.map((n) => n.x));
    const minY = Math.min(...nodes.map((n) => n.y));
    const maxY = Math.max(...nodes.map((n) => n.y));
    const canvas = document.getElementById(canvasId);
    canvas.scrollTo({ top: (minY + maxY) / 2 - canvas.clientHeight / 2, left: (minX + maxX) / 2 - canvas.clientWidth / 2, behavior: "smooth" });
  }

  // --- Crear nodo desde modal ---
  document.getElementById("nodeForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const nombre = document.getElementById("node-name").value;
    const prompt = document.getElementById("node-prompt").value;

    const res = await fetch("/leadjourney/api/nodos", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
      body: JSON.stringify({ journey_id: journeyId, nombre, prompt_agent: prompt }),
    });
    const data = await res.json();
    if (data.status === "success") location.reload();
    else alert("Error creando nodo: " + data.message);
  });

  // --- Guardar cambios de nodo ---
  document.getElementById("editNodeForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const id = document.getElementById("edit-node-id").value;
    const nombre = document.getElementById("edit-node-name").value;
    const prompt = document.getElementById("edit-node-prompt").value;

    const res = await fetch(`/leadjourney/api/nodos/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", "X-CSRFToken": getCSRFToken() },
      body: JSON.stringify({ nombre, prompt_agent: prompt }),
    });
    const result = await res.json();
    if (result.status === "success") location.reload();
    else alert("Error al actualizar nodo: " + result.message);
  });

  // --- Eliminar nodo ---
  document.getElementById("delete-node-btn").addEventListener("click", async () => {
    const nodeId = document.getElementById("edit-node-id").value;
    if (!confirm("¿Seguro que deseas eliminar este nodo?")) return;

    const res = await fetch(`/leadjourney/api/nodos/${nodeId}`, {
      method: "DELETE",
      headers: { "X-CSRFToken": getCSRFToken() },
    });
    const result = await res.json();
    if (result.status === "success") location.reload();
    else alert("Error al eliminar nodo: " + result.message);
  });

  // --- Toasts ---
function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-bg-${type} border-0 show`;
  toast.role = "alert";
  toast.style.position = "fixed";
  toast.style.top = "20px";
  toast.style.right = "20px";
  toast.style.zIndex = "9999";   // 👈 aquí está el fix
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

});
