document.addEventListener('DOMContentLoaded', function() {
    // Inicializa la instancia de Cytoscape
    var cy = cytoscape({
        container: document.getElementById('cy'),
        boxSelectionEnabled: false,
        autounselectify: true,
        style: [
            {
                selector: 'node',
                style: {
                    'label': 'data(nombre)',
                    'text-valign': 'center',
                    'color': 'black',
                    'background-color': '#f8f9fa',
                    'border-color': '#dee2e6',
                    'border-width': 1,
                    'shape': 'round-rectangle',
                    'width': 200,
                    'height': 80,
                    'padding': 10
                }
            },
            {
                selector: 'edge',
                style: {
                    'width': 3,
                    'line-color': '#ccc',
                    'target-arrow-color': '#ccc',
                    'target-arrow-shape': 'triangle',
                    'curve-style': 'bezier',
                    'label': 'data(nombre_paso)',
                    'color': '#495057',
                    'text-background-color': 'white',
                    'text-background-opacity': 1,
                    'text-background-padding': '3px',
                    'font-size': 12,
                    'text-wrap': 'wrap'
                }
            },
            {
                selector: '.eh-handle',
                style: {
                    'background-color': '#fff',
                    'border-width': 2,
                    'border-color': '#2196F3',
                    'shape': 'ellipse',
                    'opacity': 0,
                    'width': 10,
                    'height': 10
                }
            }
        ],
        layout: {
            name: 'grid',
            rows: 1
        }
    });

    // Convierte los datos de Flask a un formato compatible con Cytoscape
    const elements = [];
    FLASK_NODOS.forEach(nodo => {
        // Agrega el nodo principal
        elements.push({
            data: { 
                id: `node-${nodo.id}`, 
                nombre: nodo.nombre,
                prompt_agent: nodo.prompt_agent,
                proximo_paso: nodo.proximo_paso
            }
        });

        // Agrega los bordes (aristas) por cada "próximo_paso"
        if (nodo.proximo_paso && nodo.proximo_paso.length > 0) {
            nodo.proximo_paso.forEach(paso => {
                elements.push({
                    data: {
                        id: `edge-${nodo.id}-${paso.next_nodo}`,
                        source: `node-${nodo.id}`,
                        target: `node-${paso.next_nodo}`,
                        nombre_paso: paso.nombre
                    }
                });
            });
        }
    });

    // Carga los elementos en la instancia de Cytoscape
    cy.add(elements);
    cy.layout({ name: 'breadthfirst', directed: true, padding: 10 });

    // Habilita el arrastre de nodos
    cy.nodes().bind('free', function(e) {
        console.log(`Node ${e.target.data('id')} moved to (${e.target.position().x}, ${e.target.position().y})`);
    });

    // Manejar el clic en el nodo para abrir el modal de edición
    cy.nodes().on('tap', function(e){
        const nodeId = e.target.data('id').split('-')[1];
        const nodeToEdit = FLASK_NODOS.find(n => n.id == nodeId);

        if (nodeToEdit) {
            document.getElementById('edit_node_id').value = nodeToEdit.id;
            document.getElementById('edit_nombre').value = nodeToEdit.nombre;
            document.getElementById('edit_prompt_agent').value = nodeToEdit.prompt_agent;
            
            const proximoPasoString = JSON.stringify(nodeToEdit.proximo_paso, null, 2);
            document.getElementById('edit_proximo_paso').value = proximoPasoString;
            
            const editForm = document.getElementById('editNodeForm');
            editForm.action = `/node/${nodeToEdit.id}/edit`;
            
            var editModal = new bootstrap.Modal(document.getElementById('editNodeModal'));
            editModal.show();
        }
    });
});