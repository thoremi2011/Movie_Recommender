import os
from pathlib import Path

def create_directory(path):
    """Create directory if it doesn't exist"""
    Path(path).mkdir(parents=True, exist_ok=True)

def create_file(path):
    """Create empty file if it doesn't exist"""
    Path(path).touch()

def create_project_structure():
    """Create the complete project structure"""
    
    # Root directories
    directories = [
        'src/api',
        'src/model',
        'src/demo',
        'src/utils',
        'ci/.github/workflows',
        'docs',
        'infra/terraform',
        'tests',
        'data/raw',
        'data/processed',
        'notebooks'
    ]
    
    # Create all directories
    for directory in directories:
        create_directory(directory)
    
    # Define all files to create
    files = [
        # API files
        'src/api/__init__.py',
        'src/api/main.py',
        'src/api/routes.py',
        
        # Model files
        'src/model/__init__.py',
        'src/model/embeddings.py',
        'src/model/similarity.py',
        
        # Demo files
        'src/demo/__init__.py',
        'src/demo/app.py',
        
        # Utils files
        'src/utils/__init__.py',
        'src/utils/config.py',
        'src/utils/preprocessing.py',
        
        # Test files
        'tests/__init__.py',
        'tests/test_api.py',
        'tests/test_model.py',
        
        # Documentation files
        'docs/installation.md',
        'docs/user-guide.md',
        'docs/technical-docs.md',
        'docs/deployment.md',
        
        # CI/CD files
        'ci/.github/workflows/main.yml',
        
        # Infrastructure files
        'infra/terraform/main.tf',
        'infra/terraform/variables.tf',
        'infra/terraform/outputs.tf',
        
        # Root files
        'requirements.txt',
        'Dockerfile',
        'run_services.py',
        '.gitignore',
        'README.md'
    ]
    
    # Create all files
    for file_path in files:
        create_file(file_path)

if __name__ == "__main__":
    create_project_structure()
    print("✅ Project structure created successfully!") 