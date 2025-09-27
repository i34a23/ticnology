document.addEventListener('DOMContentLoaded', function() {
    // Inicializa la instancia de Cytoscape
    const cy = cytoscape({
        container: document.getElementById('cy'),
        boxSelectionEnabled: false,
        autounselectify: true,
        style: [
            {
                selector: 'node',
                style: {
                    'content': 'data(nombre)',
                    'text-valign': 'center',
                    'color': 'black',
                    'background-color': '#f8f9fa',
                    'border-color': '#dee2e6',
                    'border-width': 1,
                    'shape': 'round-rectangle',
                    'width': 200,
                    'height': 80,
                    'padding': 10,
                    'font-size': 14
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
                selector: '.create-node-edge',
                style: {
                    'line-color': '#2196F3',
                    'target-arrow-color': '#2196F3'
                }
            },
            {
                selector: '.create-node-handle',
                style: {
                    'background-color': '#2196F3',
                    'border-color': '#fff',
                    'border-width': 2,
                    'shape': 'round-rectangle',
                    'width': 25,
                    'height': 25,
                    'content': '+',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'color': 'white',
                    'font-size': 20,
                    'font-weight': 'bold',
                }
            },
            {
                selector: ':selected',
                style: {
                    'border-width': '3px',
                    'border-color': '#007bff'
                }
            }
        ],
        layout: {
            name: 'breadthfirst',
            directed: true,
            padding: 10
        }
    });

    const nodes = [];
    const edges = [];
    const tempNodes = [];

    // Verificamos si FLASK_NODOS existe y es un array
    if (typeof FLASK_NODOS !== 'undefined' && Array.isArray(FLASK_NODOS)) {
        FLASK_NODOS.forEach(nodo => {
            nodes.push({
                data: {
                    id: `node-${nodo.id}`,
                    nombre: nodo.nombre,
                    prompt_agent: nodo.prompt_agent,
                    proximo_paso: nodo.proximo_paso,
                    id_journey: nodo.id_journey
                }
            });

            if (nodo.proximo_paso && Array.isArray(nodo.proximo_paso)) {
                nodo.proximo_paso.forEach((paso, index) => {
                    if (paso.next_nodo) {
                        // Si el nodo hijo ya existe, creamos la conexión normal
                        edges.push({
                            data: {
                                id: `edge-${nodo.id}-${paso.next_nodo}`,
                                source: `node-${nodo.id}`,
                                target: `node-${paso.next_nodo}`,
                                nombre_paso: paso.nombre
                            }
                        });
                    } else {
                        // Si el nodo hijo no existe (next_nodo: null), creamos un "nodo temporal" para el botón '+'
                        const tempNodeId = `temp-node-${nodo.id}-${index}`;
                        tempNodes.push({
                            group: 'nodes',
                            data: { id: tempNodeId },
                            classes: 'create-node-handle',
                            position: { // Posicionamos el conector a la derecha del nodo padre
                                x: (nodo.x || 0) + 250,
                                y: (nodo.y || 0) + (index * 50)
                            }
                        });

                        // Conectamos el nodo padre al nodo temporal con un estilo especial
                        edges.push({
                            group: 'edges',
                            data: {
                                id: `edge-${nodo.id}-${tempNodeId}`,
                                source: `node-${nodo.id}`,
                                target: tempNodeId,
                                nombre_paso: paso.nombre,
                                parent_id: nodo.id,
                                connector_name: paso.nombre
                            },
                            classes: 'create-node-edge'
                        });
                    }
                });
            }
        });
    }

    cy.add(nodes);
    cy.add(tempNodes);
    cy.add(edges);
    
    // Aplica el diseño después de que todos los elementos estén en el gráfico
    cy.layout({ name: 'breadthfirst', directed: true, padding: 10 }).run();

    // Habilita el arrastre de nodos
    cy.nodes().bind('free', function(e) {
        console.log(`Node ${e.target.data('id')} moved to (${e.target.position().x}, ${e.target.position().y})`);
    });

    // Manejar el clic en el botón '+' para crear el nuevo nodo
    cy.on('tap', '.create-node-handle', function(e) {
        const edgeData = e.target.incomers('edge').data();
        const parentNodeId = edgeData.parent_id;
        const connectorName = edgeData.connector_name;
        const journeyId = FLASK_NODOS[0] ? FLASK_NODOS[0].id_journey : null;

        if (!journeyId) {
            alert('No se pudo encontrar el ID del Journey. Crea al menos un nodo primero.');
            return;
        }

        const childName = prompt(`Ingresa el nombre para el nodo "${connectorName}":`);

        if (childName) {
            fetch('/create_child_node', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    parent_id: parentNodeId,
                    child_name: childName,
                    journey_id: journeyId,
                    connector_name: connectorName
                }),
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    const new_node_id = data.new_node_id;
                    const new_node_nombre = data.new_node_nombre;
                    const oldEdgeId = `edge-${parentNodeId}-${e.target.data('id')}`;

                    // Elimina el borde temporal y el nodo de creación
                    cy.remove(cy.getElementById(oldEdgeId));
                    cy.remove(e.target);

                    // Agrega el nuevo nodo real
                    cy.add({
                        group: 'nodes',
                        data: {
                            id: `node-${new_node_id}`,
                            nombre: new_node_nombre,
                            proximo_paso: [], // Nuevo nodo sin conexiones
                            id_journey: journeyId
                        },
                        position: { x: e.target.position('x'), y: e.target.position('y') }
                    });

                    // Agrega la nueva conexión final
                    cy.add({
                        group: 'edges',
                        data: {
                            id: `edge-${parentNodeId}-${new_node_id}`,
                            source: `node-${parentNodeId}`,
                            target: `node-${new_node_id}`,
                            nombre_paso: connectorName
                        }
                    });

                    // Vuelve a aplicar el layout para reorganizar los nodos
                    cy.layout({ name: 'breadthfirst', directed: true, padding: 10 }).run();
                } else {
                    alert('Error al crear el nodo: ' + data.error);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Hubo un problema al conectar con el servidor.');
            });
        }
    });

    // Manejar el clic en el nodo para abrir el modal de edición
    cy.nodes().on('cxttap', function(e){
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