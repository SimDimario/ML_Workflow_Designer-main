import os
import paramiko
import tempfile
from scp import SCPClient
from django.utils import timezone
from django.conf import settings
from typing import Optional, Dict, Any
from .models import SSHConnection, FileDeployment


class SSHDeploymentError(Exception):
    """Eccezione personalizzata per errori di deployment SSH"""
    pass


class SSHDeploymentService:
    """Servizio per gestire i deployment SSH"""
    
    def __init__(self, ssh_connection: SSHConnection):
        self.ssh_connection = ssh_connection
        self.ssh_client = None
        self.scp_client = None
    
    def connect(self) -> bool:
        """Stabilisce la connessione SSH"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Parametri di connessione
            connect_params = {
                'hostname': self.ssh_connection.host,
                'port': self.ssh_connection.port,
                'username': self.ssh_connection.username,
                'timeout': 30
            }
            
            # Usa password o chiave privata
            if self.ssh_connection.password:
                connect_params['password'] = self.ssh_connection.password
            elif self.ssh_connection.private_key_path and os.path.exists(self.ssh_connection.private_key_path):
                connect_params['key_filename'] = self.ssh_connection.private_key_path
            else:
                raise SSHDeploymentError("Nessuna credenziale valida fornita (password o chiave privata)")
            
            self.ssh_client.connect(**connect_params)
            self.scp_client = SCPClient(self.ssh_client.get_transport())
            
            return True
            
        except Exception as e:
            raise SSHDeploymentError(f"Errore di connessione SSH: {str(e)}")
    
    def disconnect(self):
        """Chiude la connessione SSH"""
        if self.scp_client:
            self.scp_client.close()
        if self.ssh_client:
            self.ssh_client.close()
    
    def create_remote_directory(self, remote_path: str) -> bool:
        """Crea una directory remota se non esiste"""
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(f'mkdir -p "{remote_path}"')
            return stdout.channel.recv_exit_status() == 0
        except Exception as e:
            raise SSHDeploymentError(f"Errore nella creazione della directory remota: {str(e)}")
    
    def upload_file_content(self, file_content: str, remote_file_path: str) -> bool:
        """Carica il contenuto di un file sul server remoto"""
        try:
            # Crea un file temporaneo con il contenuto
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                # Crea la directory remota se necessario
                remote_dir = os.path.dirname(remote_file_path)
                self.create_remote_directory(remote_dir)
                
                # Carica il file
                self.scp_client.put(temp_file_path, remote_file_path)
                
                # Verifica che il file sia stato caricato
                stdin, stdout, stderr = self.ssh_client.exec_command(f'test -f "{remote_file_path}" && echo "exists"')
                result = stdout.read().decode().strip()
                
                return result == "exists"
                
            finally:
                # Rimuovi il file temporaneo
                os.unlink(temp_file_path)
                
        except Exception as e:
            raise SSHDeploymentError(f"Errore nel caricamento del file: {str(e)}")
    
    def execute_command(self, command: str) -> Dict[str, Any]:
        """Esegue un comando sul server remoto"""
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            
            exit_status = stdout.channel.recv_exit_status()
            stdout_content = stdout.read().decode()
            stderr_content = stderr.read().decode()
            
            return {
                'exit_status': exit_status,
                'stdout': stdout_content,
                'stderr': stderr_content,
                'success': exit_status == 0
            }
            
        except Exception as e:
            raise SSHDeploymentError(f"Errore nell'esecuzione del comando: {str(e)}")


def deploy_workflow_file(
    ssh_connection_id: str,
    file_content: str,
    file_name: str,
    workflow_id: Optional[str] = None,
    user=None,
    deployment_notes: str = ""
) -> FileDeployment:
    """
    Deploya un file workflow sul server remoto via SSH
    
    Args:
        ssh_connection_id: ID della connessione SSH da utilizzare
        file_content: Contenuto del file da deployare
        file_name: Nome del file
        workflow_id: ID del workflow associato (opzionale)
        user: Utente che effettua il deployment
        deployment_notes: Note aggiuntive
    
    Returns:
        FileDeployment: Oggetto che traccia il deployment
    """
    try:
        # Recupera la connessione SSH
        ssh_connection = SSHConnection.objects.get(id=ssh_connection_id, is_active=True)
        
        # Crea il record di deployment
        deployment = FileDeployment.objects.create(
            ssh_connection=ssh_connection,
            user=user,
            file_name=file_name,
            file_content=file_content,
            workflow_id=workflow_id,
            deployment_notes=deployment_notes,
            status='pending'
        )
        
        # Costruisci il path remoto
        if workflow_id:
            remote_file_path = os.path.join(
                ssh_connection.remote_base_path,
                f"workflow_{workflow_id}",
                file_name
            ).replace('\\', '/')  # Assicurati che usi slash Unix
        else:
            remote_file_path = os.path.join(
                ssh_connection.remote_base_path,
                "generated_files",
                file_name
            ).replace('\\', '/')
        
        deployment.remote_file_path = remote_file_path
        deployment.status = 'uploading'
        deployment.started_at = timezone.now()
        deployment.save()
        
        # Effettua il deployment
        service = SSHDeploymentService(ssh_connection)
        service.connect()
        
        try:
            success = service.upload_file_content(file_content, remote_file_path)
            
            if success:
                deployment.status = 'completed'
                deployment.completed_at = timezone.now()
            else:
                deployment.status = 'failed'
                deployment.error_message = "File upload failed - file not found after upload"
                
        finally:
            service.disconnect()
        
        deployment.save()
        return deployment
        
    except SSHConnection.DoesNotExist:
        raise SSHDeploymentError(f"Connessione SSH con ID {ssh_connection_id} non trovata")
    except Exception as e:
        if 'deployment' in locals():
            deployment.status = 'failed'
            deployment.error_message = str(e)
            deployment.save()
        raise SSHDeploymentError(f"Errore nel deployment: {str(e)}")


def get_ml_runner_connection() -> Optional[SSHConnection]:
    """Recupera la connessione SSH per il container ml_runner"""
    try:
        return SSHConnection.objects.get(name="ml_runner", is_active=True)
    except SSHConnection.DoesNotExist:
        return None


def create_ml_runner_connection() -> SSHConnection:
    """Crea la connessione SSH di default per il container ml_runner"""
    connection, created = SSHConnection.objects.get_or_create(
        name="ml_runner",
        defaults={
            'host': 'ml_runner',  # Nome del container Docker nella rete
            'port': 22,
            'username': 'root',
            'password': 'password',  # Password configurata nel Dockerfile
            'remote_base_path': '/app/workflows',  # Path base nel container ml_runner
            'is_active': True
        }
    )
    
    # Log per debug
    import logging
    logger = logging.getLogger(__name__)
    if created:
        logger.info(f"✅ Nuova connessione SSH creata per ml_runner: {connection.host}:{connection.port}")
    else:
        logger.info(f"🔄 Connessione SSH esistente per ml_runner: {connection.host}:{connection.port}")
    
    return connection


def deploy_workflow_to_ml_runner(
    file_content: str,
    file_name: str,
    workflow_id: Optional[str] = None,
    user=None
) -> FileDeployment:
    """
    Deployment semplificato per il container ml_runner usando volumi condivisi
    Invece di SSH, scrive direttamente nel volume condiviso
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Path della directory workflows nel volume condiviso
        from django.conf import settings
        
        # Il container Django ha accesso alla directory tramite volume mount
        # Verifica se esiste una directory workflows condivisa
        project_root = settings.BASE_DIR.parent.parent  # /app -> root del progetto
        workflows_shared_dir = os.path.join(project_root, 'prova_ml_runner', 'ml_runner', 'workflows')
        
        logger.info(f"🔍 Cercando directory workflows in: {workflows_shared_dir}")
        
        if not os.path.exists(workflows_shared_dir):
            logger.warning(f"⚠️ Directory workflows non trovata: {workflows_shared_dir}")
            # Prova percorsi alternativi
            alt_paths = [
                os.path.join(settings.BASE_DIR.parent, 'workflows'),  # /app/workflows (mount point)
                '/app/workflows',  # Path assoluto del mount
                os.path.join(project_root, 'workflows')  # root/workflows
            ]
            
            for alt_path in alt_paths:
                logger.info(f"🔍 Tentativo path alternativo: {alt_path}, exists: {os.path.exists(alt_path)}")
                if os.path.exists(alt_path):
                    workflows_shared_dir = alt_path
                    logger.info(f"✅ Trovato path alternativo: {workflows_shared_dir}")
                    break
            else:
                logger.info("🔄 Fallback al deployment SSH...")
                # Fallback al deployment SSH normale
                connection = get_ml_runner_connection()
                if not connection:
                    connection = create_ml_runner_connection()
                return deploy_workflow_file(
                    ssh_connection_id=str(connection.id),
                    file_content=file_content,
                    file_name=file_name,
                    workflow_id=workflow_id,
                user=user,
                deployment_notes="Deployment automatico via SSH"
            )
        
        # Scrivi direttamente nel volume condiviso
        local_file_path = os.path.join(workflows_shared_dir, file_name)
        logger.info(f"Scrivendo file nel volume condiviso: {local_file_path}")
        
        with open(local_file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        # Verifica che il file sia stato scritto
        if not os.path.exists(local_file_path):
            raise SSHDeploymentError("File non scritto correttamente nel volume condiviso")
        
        file_size = os.path.getsize(local_file_path)
        logger.info(f"✅ File scritto con successo: {local_file_path} ({file_size} bytes)")
        
        # Crea un record di deployment per tracciamento
        connection = get_ml_runner_connection()
        if not connection:
            connection = create_ml_runner_connection()
            
        deployment = FileDeployment.objects.create(
            ssh_connection=connection,
            user=user,
            file_name=file_name,
            file_content=file_content,
            local_file_path=local_file_path,
            remote_file_path=f"/app/workflows/{file_name}",
            workflow_id=workflow_id,
            deployment_notes="Deployment automatico via volume condiviso",
            status='completed',
            started_at=timezone.now(),
            completed_at=timezone.now()
        )
        
        return deployment
        
    except Exception as e:
        logger.error(f"❌ Errore nel deployment via volume condiviso: {str(e)}")
        raise SSHDeploymentError(f"Errore nel deployment: {str(e)}")


def deploy_workflow_to_ml_runner_with_folder(
    file_content: str,
    file_name: str,
    workflow_id: str,
    user=None
) -> FileDeployment:
    """
    Deployment con cartella specifica per workflow nel container ml_runner
    Usa SSH per deployare nel container remoto (i volumi non sono condivisi tra containers)
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Deployment SSH con cartella workflow {workflow_id}")
        
        # Ottieni la connessione SSH per ml_runner
        connection = get_ml_runner_connection()
        if not connection:
            connection = create_ml_runner_connection()
            logger.info("✅Connessione ml_runner creata")
        
        # Path remoto nel container ml_runner: /app/workflows/{workflow_id}/{file_name}
        remote_file_path = f"/app/workflows/{workflow_id}/{file_name}"
        logger.info(f"Path remoto: {remote_file_path}")
        
        # Crea il record di deployment
        deployment = FileDeployment.objects.create(
            ssh_connection=connection,
            user=user,
            file_name=file_name,
            file_content=file_content,
            remote_file_path=remote_file_path,
            workflow_id=workflow_id,
            deployment_notes=f"SSH deployment con cartella {workflow_id}",
            status='pending'
        )
        
        deployment.status = 'uploading'
        deployment.started_at = timezone.now()
        deployment.save()
        logger.info(f"Deployment record creato: {deployment.id}")
        
        # Effettua il deployment via SSH
        service = SSHDeploymentService(connection)
        
        try:
            logger.info(f"🔌 Tentativo connessione SSH a {connection.host}:{connection.port}")
            service.connect()
            logger.info("✅ Connessione SSH stabilita con successo")
            
            # Test connessione con comando semplice
            test_result = service.execute_command('echo "SSH test successful"')
            logger.info(f"Test SSH: {test_result['stdout'].strip() if test_result['success'] else 'FAILED'}")
            
            # Crea la directory del workflow
            workflow_dir = f"/app/workflows/{workflow_id}"
            logger.info(f"Creando directory: {workflow_dir}")
            dir_success = service.create_remote_directory(workflow_dir)
            logger.info(f"Directory creata: {dir_success}")
            
            # Verifica che la directory esista
            check_result = service.execute_command(f'ls -la /app/workflows/ | grep {workflow_id}')
            logger.info(f"Verifica directory: {check_result['stdout'].strip()}")
            
            # Carica il file
            logger.info(f"Uploading file: {remote_file_path}")
            success = service.upload_file_content(file_content, remote_file_path)
            
            if success:
                # Verifica che il file sia stato caricato
                verify_result = service.execute_command(f'ls -la "{remote_file_path}"')
                logger.info(f"Verifica file: {verify_result['stdout'].strip()}")
                
                deployment.status = 'completed'
                deployment.completed_at = timezone.now()
                logger.info(f"✅ File deployato con successo: {remote_file_path}")
            else:
                deployment.status = 'failed'
                deployment.error_message = "SSH upload failed - file not found after upload"
                logger.error("❌ Upload SSH fallito")
                
        except Exception as ssh_error:
            logger.error(f"❌ Errore durante operazioni SSH: {str(ssh_error)}")
            deployment.status = 'failed'
            deployment.error_message = f"Errore SSH: {str(ssh_error)}"
        finally:
            service.disconnect()
            logger.info("🔌 Connessione SSH chiusa")
        
        deployment.save()
        return deployment
        
    except Exception as e:
        logger.error(f"❌ Errore nel deployment SSH: {str(e)}")
        if 'deployment' in locals():
            deployment.status = 'failed'
            deployment.error_message = str(e)
            deployment.save()
        raise SSHDeploymentError(f"Errore nel deployment SSH: {str(e)}")
    