import { useCallback, useRef, useState } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

import CustomWorkflowNode from './CustomWorkflowNode';
import './WorkflowGenerator.css';
import WorkflowSidebar from './WorkflowSidebar';

const nodeTypes = {
  customNode: CustomWorkflowNode,
};

const initialNodes = [
  {
    id: 'start',
    type: 'input',
    data: { label: 'start' },
    position: { x: 100, y: 100 },
    style: { background: '#f0f0f0', border: '2px solid #999' },
  },
  {
    id: 'end',
    type: 'output',
    data: { label: 'end' },
    position: { x: 500, y: 100 },
    style: { background: '#f0f0f0', border: '2px solid #999' },
  },
];

const initialEdges = [];

let id = 0;
const getId = () => `dndnode_${id++}`;

const WorkflowFlow = () => {
  const reactFlowWrapper = useRef(null);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [reactFlowInstance, setReactFlowInstance] = useState(null);
  const [workflowName, setWorkflowName] = useState('ml_workflow');
  const [workflowDescription, setWorkflowDescription] = useState('');
  const [isExporting, setIsExporting] = useState(false);

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();

      const reactFlowBounds = reactFlowWrapper.current.getBoundingClientRect();
      const type = event.dataTransfer.getData('application/reactflow');

      if (typeof type === 'undefined' || !type) {
        return;
      }

      const position = reactFlowInstance.project({
        x: event.clientX - reactFlowBounds.left,
        y: event.clientY - reactFlowBounds.top,
      });

      const isCustomComponent = type === 'custom_component';
      const nodeLabel = isCustomComponent ? 'nuovo_componente' : type;
      const stepName = isCustomComponent ? 'nuovo_componente' : type;

      const newNode = {
        id: getId(),
        type: 'customNode',
        position,
        data: { 
          label: nodeLabel,
          stepName: stepName,
          decorator: null,
          onChange: onNodeChange,
          isCustom: isCustomComponent
        },
      };

      setNodes((nds) => nds.concat(newNode));
    },
    [reactFlowInstance, setNodes]
  );

  const onNodeChange = useCallback((nodeId, newData) => {
    setNodes((nds) =>
      nds.map((node) =>
        node.id === nodeId ? { ...node, data: { ...node.data, ...newData } } : node
      )
    );
  }, [setNodes]);

  const exportWorkflow = useCallback(async () => {
    setIsExporting(true);
    
    try {
      // URL per il backend Django tramite localhost (porta esposta)
      const djangoApiUrl = 'http://localhost:8000';
      
      // Verifica che ci sia un nome workflow valido
      const finalWorkflowName = workflowName && workflowName.trim() !== '' 
        ? workflowName.trim() 
        : "ml_workflow_" + Date.now();
      
      // Prepara i dati nel formato richiesto dall'API Django
      const apiPayload = {
        config_name: finalWorkflowName,
        config_data: {
          imports: [
            'os',
            'sys',
            'torch',
            'mlflow',
            {
              from: 'tensorflow',
              elements: ['keras']
            }
          ],
          class: {
            name: finalWorkflowName,
            steps: nodes.map(node => {
              const connectedEdges = edges.filter(edge => edge.source === node.id);
              const nextSteps = connectedEdges.map(edge => {
                const targetNode = nodes.find(n => n.id === edge.target);
                return targetNode?.data?.stepName || targetNode?.data?.label || targetNode?.id;
              }).filter(step => step !== null);

              const step = {
                name: node.data.stepName || node.data.label || node.id
              };

              // Gestione decoratori
              if (node.id !== 'start' && node.id !== 'end' && 
                  node.data.decorator && 
                  typeof node.data.decorator === 'object' && 
                  node.data.decorator.name && 
                  node.data.decorator.name.trim() !== '') {
                
                const decoratorObj = {
                  name: node.data.decorator.name.trim()
                };
                
                if (node.data.decorator.params) {
                  if (typeof node.data.decorator.params === 'object' && 
                      Object.keys(node.data.decorator.params).length > 0) {
                    decoratorObj.parameters = node.data.decorator.params;
                  } else if (typeof node.data.decorator.params === 'string' && 
                            node.data.decorator.params.trim() !== '') {
                    decoratorObj.parameters = node.data.decorator.params.trim();
                  }
                }
                
                step.decorators = [decoratorObj];
              }

              // Gestione collegamenti
              if (nextSteps.length === 1) {
                step.next = nextSteps[0];
              } else if (nextSteps.length > 1) {
                step.next = nextSteps;
              }

              return step;
            })
          }
        }
      };

      console.log('STEP 1: Invio workflow al backend Django:', apiPayload);

      // STEP 1: Invio POST API al backend Django per salvare il workflow
      const workflowResponse = await fetch(`${djangoApiUrl}/api/workflow-generator/workflows/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(apiPayload)
      });

      if (!workflowResponse.ok) {
        const errorData = await workflowResponse.json().catch(() => ({}));
        throw new Error(`Errore API Workflow: ${workflowResponse.status} - ${errorData.message || workflowResponse.statusText}`);
      }

      const workflowResult = await workflowResponse.json();
      console.log('STEP 1 completato - Workflow salvato:', workflowResult);

      // STEP 2: Se c'è una descrizione, invia la seconda API per generare il codice
      let codeGenerated = false;
      
      console.log('STEP 2: Invio richiesta generazione codice LLM');
      
      const llmPayload = {
        model: "6",
        workflow_id: `${workflowResult.id || 'generated'}`,
        user_prompt: `Completa questo workflow e aggiungi miglioramenti per le performance: ${workflowDescription.trim()}`
      };

      try {
        const llmResponse = await fetch(`${djangoApiUrl}/api/llm/workflow-analysis/quick_analysis/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(llmPayload)
        });

        if (llmResponse.ok) {
          const llmResult = await llmResponse.json();
          console.log('✅ STEP 2 completato - Codice generato:', llmResult);
          codeGenerated = true;
        } else {
          const errorData = await llmResponse.json().catch(() => ({}));
          console.warn('Errore nella generazione LLM:', errorData);
        }
      } catch (llmError) {
        console.warn('Errore nella chiamata LLM:', llmError);
      }
      
      // Download del file JSON per backup
      const fileName = `${finalWorkflowName}_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`;
      const dataStr = JSON.stringify(apiPayload, null, 2);
      const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
      
      const linkElement = document.createElement('a');
      linkElement.setAttribute('href', dataUri);
      linkElement.setAttribute('download', fileName);
      linkElement.click();

      // STEP 3: Reindirizzamento alla pagina di editing
      // Usa il workflow ID e il nome file dal response per costruire il path completo
      let actualFileName = 'ml_workflow'; // Default name
      let workflowId = null;
      
      if (workflowResult) {
        workflowId = workflowResult.id;
        console.log('Workflow ID ricevuto:', workflowId);
        
        if (workflowResult.generated_class_name) {
          actualFileName = workflowResult.generated_class_name;
          console.log('Usando nome file dal response:', actualFileName);
        } else {
          // Fallback al nome dalla configurazione
          actualFileName = finalWorkflowName.replace(/[^a-zA-Z0-9_]/g, '_');
          console.log('Fallback al nome pulito:', actualFileName);
        }
      }
      
      // Costruisci il path per SSH deployment con cartella workflow_id
      let editUrl;
      if (workflowId) {
        // Jupyter notebook-dir è /app/workflows, quindi il path relativo è solo {workflow_id}/{filename}.py
        editUrl = `http://127.0.0.1:8888/edit/${workflowId}/${actualFileName}.py`;
        console.log('Path SSH deployment (senza workflows prefix):', editUrl);
      } else {
        // Fallback per path diretto nella directory workflows
        editUrl = `http://127.0.0.1:8888/edit/${actualFileName}.py`;
        console.log('Path diretto fallback:', editUrl);
      }
      
      console.log('STEP 3: Reindirizzamento a:', editUrl);
      console.log('Nome file finale:', actualFileName);
      console.log('Workflow ID:', workflowId);
      console.log('Codice generato da LLM:', codeGenerated);
      console.log('Path completo nel container:', `/app/workflows/${workflowId}/${actualFileName}.py`);
      
      // Mostra messaggio di successo prima del reindirizzamento
      const successMessage = codeGenerated 
        ? `✅ Workflow salvato e codice generato con successo!\n File deployato in: workflows/${workflowId}/${actualFileName}.py\nReindirizzamento alla pagina di editing...`
        : `✅ Workflow salvato con successo!\n File deployato in: workflows/${workflowId}/${actualFileName}.py\nReindirizzamento alla pagina di editing...`;
      
      alert(successMessage);
      
      // Prova prima window.location.href come fallback
      try {
        console.log('Tentativo reindirizzamento con window.open...');
        const newWindow = window.open(editUrl, '_blank');
        
        // Se window.open fallisce (popup bloccato), usa window.location.href
        if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
          console.log('Popup bloccato, uso window.location.href...');
          setTimeout(() => {
            window.location.href = editUrl;
          }, 500);
        } else {
          console.log('✅ Reindirizzamento riuscito con window.open');
        }
      } catch (redirectError) {
        console.error('❌ Errore nel reindirizzamento:', redirectError);
        // Fallback finale
        setTimeout(() => {
          window.location.href = editUrl;
        }, 500);
      }

    } catch (error) {
      console.error('❌ Errore nel processo:', error);
      alert(`❌ Errore: ${error.message}`);
    } finally {
      setIsExporting(false);
    }
  }, [nodes, edges, workflowName, workflowDescription]);

  return (
    <div className="workflow-container">
      <div className="workflow-header">
        <h1>ML Workflow Builder</h1>
        <div className="workflow-controls">
          <div className="workflow-inputs">
            <input
              type="text"
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              placeholder="Nome del workflow"
              className="workflow-name-input"
            />
            <textarea
              value={workflowDescription}
              onChange={(e) => setWorkflowDescription(e.target.value)}
              placeholder="Descrizione aggiuntiva per la generazione del codice Python (opzionale)..."
              className="workflow-description-input"
              rows={3}
            />
          </div>
          <button 
            onClick={exportWorkflow} 
            className="export-btn"
            disabled={isExporting}
          >
            {isExporting ? 'Elaborazione in corso...' : 'Genera Workflow + Codice'}
          </button>
        </div>
      </div>
      
      <div className="workflow-main">
        <WorkflowSidebar />
        <div className="reactflow-wrapper" ref={reactFlowWrapper}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onInit={setReactFlowInstance}
            onDrop={onDrop}
            onDragOver={onDragOver}
            nodeTypes={nodeTypes}
            fitView
          >
            <Controls />
            <MiniMap />
            <Background variant="dots" gap={12} size={1} />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
};

const WorkflowGenerator = () => {
  return (
    <div className="container">
      <ReactFlowProvider>
        <WorkflowFlow />
      </ReactFlowProvider>
    </div>
  );
};

export default WorkflowGenerator;