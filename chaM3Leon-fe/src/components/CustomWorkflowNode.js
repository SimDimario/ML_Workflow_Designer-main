import React, { useState, useEffect } from 'react';
import { Handle, Position } from 'reactflow';

const CustomWorkflowNode = ({ data, id }) => {
  const [isEditing, setIsEditing] = useState(data.isCustom || false);
  const [stepName, setStepName] = useState(data.stepName || data.label);
  const [decoratorName, setDecoratorName] = useState(data.decorator?.name || '');
  const [decoratorParams, setDecoratorParams] = useState('');

  useEffect(() => {
    setStepName(data.stepName || data.label);
    if (typeof data.decorator === 'string') {
      setDecoratorName(data.decorator);
      setDecoratorParams('');
    } else if (data.decorator && typeof data.decorator === 'object') {
      setDecoratorName(data.decorator.name || '');
      if (data.decorator.params && typeof data.decorator.params === 'object') {
        const paramsString = Object.entries(data.decorator.params)
          .map(([key, value]) => `${key}=${value}`)
          .join(', ');
        setDecoratorParams(paramsString);
      } else {
        setDecoratorParams(data.decorator.params || '');
      }
    } else {
      setDecoratorName('');
      setDecoratorParams('');
    }

    if (data.isCustom && !data.hasBeenEdited) {
      setIsEditing(true);
    }
  }, [data.stepName, data.label, data.decorator, data.isCustom, data.hasBeenEdited]);

  const parseParams = (paramsString) => {
    if (!paramsString || paramsString.trim() === '') return {};
    
    const params = {};
    const pairs = paramsString.split(',');
    
    pairs.forEach(pair => {
      const [key, ...valueParts] = pair.split('=');
      if (key && valueParts.length > 0) {
        const value = valueParts.join('=').trim();
        params[key.trim()] = value;
      }
    });
    
    return params;
  };

  const handleSave = () => {
    if (data.onChange) {
      let decoratorData = null;
      
      if (decoratorName.trim() !== '') {
        decoratorData = {
          name: decoratorName.trim()
        };
        
        const parsedParams = parseParams(decoratorParams);
        if (Object.keys(parsedParams).length > 0) {
          decoratorData.params = parsedParams;
        }
      }

      data.onChange(id, { 
        stepName: stepName.trim(), 
        decorator: decoratorData,
        isCustom: false,
        hasBeenEdited: true
      });
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    if (data.isCustom && !data.hasBeenEdited) {
      setStepName('nuovo_componente');
      setDecoratorName('');
      setDecoratorParams('');
    } else {
      setStepName(data.stepName || data.label);
      if (typeof data.decorator === 'string') {
        setDecoratorName(data.decorator);
        setDecoratorParams('');
      } else if (data.decorator && typeof data.decorator === 'object') {
        setDecoratorName(data.decorator.name || '');
        if (data.decorator.params && typeof data.decorator.params === 'object') {
          const paramsString = Object.entries(data.decorator.params)
            .map(([key, value]) => `${key}=${value}`)
            .join(', ');
          setDecoratorParams(paramsString);
        } else {
          setDecoratorParams(data.decorator.params || '');
        }
      } else {
        setDecoratorName('');
        setDecoratorParams('');
      }
    }
    setIsEditing(false);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSave();
    } else if (e.key === 'Escape') {
      handleCancel();
    }
  };

  const formatDecoratorDisplay = () => {
    if (!decoratorName || decoratorName.trim() === '') return '';
    
    const name = decoratorName.trim();
    
    if (!data.decorator?.params || Object.keys(data.decorator.params).length === 0) {
      return `@${name}`;
    } else {
      const paramsString = Object.entries(data.decorator.params)
        .map(([key, value]) => `${key}=${value}`)
        .join(', ');
      return `@${name}(${paramsString})`;
    }
  };

  const getNodeStyle = () => {
    if (data.isCustom && !data.hasBeenEdited) {
      return { border: '2px dashed #FF9800' };
    } else if (data.isCustom) {
      return { border: '2px solid #9C27B0' };
    }
    return {};
  };

  return (
    <div className="workflow-custom-node" style={getNodeStyle()}>
      <Handle type="target" position={Position.Left} />
      
      {isEditing ? (
        <div className="workflow-node-editor">
          <input
            type="text"
            value={stepName}
            onChange={(e) => setStepName(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Nome step"
            className="workflow-node-input"
            autoFocus
          />
          <input
            type="text"
            value={decoratorName}
            onChange={(e) => setDecoratorName(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Nome decoratore (es: retry, cache)"
            className="workflow-node-input"
          />
          <input
            type="text"
            value={decoratorParams}
            onChange={(e) => setDecoratorParams(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Parametri (es: max_attempts=3, timeout=30)"
            className="workflow-node-input"
          />
          <div className="workflow-params-hint">
            Formato: chiave=valore, chiave2=valore2
          </div>
          <div className="workflow-node-buttons">
            <button onClick={handleSave} className="workflow-save-btn" title="Salva (Enter)">✓</button>
            <button onClick={handleCancel} className="workflow-cancel-btn" title="Annulla (Esc)">✗</button>
          </div>
        </div>
      ) : (
        <div className="workflow-node-content" onDoubleClick={() => setIsEditing(true)}>
          <div className="workflow-node-label">{stepName}</div>
          {decoratorName && decoratorName.trim() !== '' && (
            <div className="workflow-node-decorator">{formatDecoratorDisplay()}</div>
          )}
          <div className="workflow-edit-hint">
            {data.isCustom && !data.hasBeenEdited ? 'Componente personalizzato - Doppio click per configurare' : 'Doppio click per modificare'}
          </div>
        </div>
      )}
      
      <Handle type="source" position={Position.Right} />
    </div>
  );
};

export default CustomWorkflowNode;