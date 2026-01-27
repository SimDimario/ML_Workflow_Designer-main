import os
import argparse
import requests
from chameleon.ml_runner.metaflow.runner.templating.workflow_runner import run_workflow


def main():
    
    parser = argparse.ArgumentParser(description='ML runner')
    parser.add_argument('--mode', type=str, choices=['fetch', 'run'], required=True, help='mode can be either fetch or run')
    parser.add_argument('--workflow-path', type=str, default='', help='path to save workflow script')
    args = parser.parse_args()
    
    if args.mode == 'fetch':
    
        response = requests.get("http://djangobe:8000/api/llm/workflow-analysis/latest_generated")
        
        if response.status_code != 200:
            print(f"Error fetching workflow analysis: {response.status_code}")
            return
        
        body = response.json()
        
        workflows_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "workflows")
        workflow_path = os.path.join(workflows_dir, body.get("file_name"))
        
        with open(workflow_path, 'w') as f:
            f.write(body.get("content"))
            
        print(f'Generated workflow script at: {workflow_path}')
    
    elif args.mode == 'run':
        
        if not args.workflow_path:
            print("Workflow path is required in run mode.")
            return
        
        run_workflow(args.workflow_path)

if __name__ == "__main__":
    main()
