import React from 'react';

const mlSteps = [
  'get_data',
  'process_data',
  'train_test_split',
  'scale_data',
  'build_model',
  'train_model',
  'evaluate_model',
  'validate_model',
  'save_model',
  'load_model',
  'predict',
  'visualize_results',
  'feature_engineering',
  'hyperparameter_tuning',
  'cross_validation',
  'ensemble_models',
  'data_preprocessing',
  'feature_selection',
  'model_comparison',
  'finalize'
];

const WorkflowSidebar = () => {
  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <aside className="workflow-sidebar">
      <div className="sidebar-description">
        <h3>Componenti ML</h3>
        <p>Trascina i componenti nell'area di lavoro per costruire il tuo workflow</p>
      </div>
      
      <div className="sidebar-nodes">
        {/* Componente personalizzato */}
        <div
          key="custom_component"
          className="sidebar-node custom-component"
          onDragStart={(event) => onDragStart(event, 'custom_component')}
          draggable
        >
          ➕ Componente Personalizzato
        </div>
        
        {/* Separatore */}
        <div className="sidebar-separator">
          <span>Componenti Predefiniti</span>
        </div>
        
        {/* Componenti ML predefiniti */}
        {mlSteps.map((step) => (
          <div
            key={step}
            className="sidebar-node"
            onDragStart={(event) => onDragStart(event, step)}
            draggable
          >
            {step}
          </div>
        ))}
      </div>
    </aside>
  );
};

export default WorkflowSidebar;