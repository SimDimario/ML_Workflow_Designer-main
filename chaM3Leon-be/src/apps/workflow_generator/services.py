import os
import json
import tempfile
from django.utils import timezone
from .models import WorkflowGeneration
from chameleon.ml_runner.metaflow.runner.templating.configuration_parser import generate_workflow
import shutil

class WorkflowGenerationError(Exception):
    pass

def generate_workflow_from_config(workflow_generation):
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        workflow_generation.status = 'processing'
        workflow_generation.save()
        logger.info(f"Iniziando generazione workflow ID: {workflow_generation.id}")
        
        # Assicurati che la directory di output esista prima di tutto
        output_dir = workflow_generation.output_directory
        logger.info(f"Creando directory di output: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(output_dir):
            raise WorkflowGenerationError(f"Impossibile creare la directory di output: {output_dir}")
        
        logger.info(f"✅ Directory di output creata: {output_dir}")
        
        temp_dir = tempfile.mkdtemp()
        logger.debug(f"Directory temporanea creata: {temp_dir}")
        config_path = os.path.join(temp_dir, 'config.json')
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(workflow_generation.config_data, f, indent=2)
        logger.debug(f"Config JSON scritto in: {config_path}")
        
        logger.info("Chiamando generate_workflow...")
        generated_file_path = generate_workflow(config_path, temp_dir)
        logger.info(f"File generato dal templating: {generated_file_path}")
        
        if os.path.exists(generated_file_path):
            with open(generated_file_path, 'r', encoding='utf-8') as f:
                generated_content = f.read()
            logger.debug(f"Contenuto letto: {len(generated_content)} caratteri")
        else:
            raise WorkflowGenerationError(f"File generato non trovato: {generated_file_path}")
        
        class_name = workflow_generation.config_data.get('class', {}).get('name', 'workflow')
        file_name = f"{class_name}.py"
        output_path = os.path.join(output_dir, file_name)
        
        logger.info(f"Salvando file finale in: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(generated_content)
        
        # Verifica che il file sia stato scritto correttamente
        if not os.path.exists(output_path):
            raise WorkflowGenerationError(f"File non salvato correttamente: {output_path}")
        
        file_size = os.path.getsize(output_path)
        logger.info(f"✅ File salvato con successo: {output_path} ({file_size} bytes)")
        
        workflow_generation.generated_class_name = class_name
        workflow_generation.generated_file_path = output_path
        workflow_generation.generated_content = generated_content
        workflow_generation.status = 'completed'
        workflow_generation.completed_at = timezone.now()
        workflow_generation.save()
        
        logger.info(f"✅ Workflow generato con successo: {workflow_generation.id}")
        
        # NON deployare qui - il deployment avverrà dopo l'elaborazione LLM
        logger.info("Deployment pianificato dopo elaborazione LLM...")
                
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        return workflow_generation
        
    except Exception as e:
        logger.error(f"Errore durante la generazione del workflow: {str(e)}")
        logger.error(f"Tipo errore: {type(e).__name__}")
        workflow_generation.status = 'failed'
        workflow_generation.error_message = str(e)
        workflow_generation.save()
        raise WorkflowGenerationError(f"Errore durante la generazione del workflow: {str(e)}")

def process_uploaded_json(uploaded_file):
    try:
        content = uploaded_file.read().decode('utf-8')
        return json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise WorkflowGenerationError(f"Errore nel parsing del JSON: {str(e)}")
