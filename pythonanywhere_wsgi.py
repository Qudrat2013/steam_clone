"""
WSGI entry for PythonAnywhere.

1. Web → WSGI configuration file — replace the whole file with this content
2. Change YOUR_USERNAME to your PythonAnywhere username
3. Web → Reload
"""
import os
import sys
from pathlib import Path

# >>> REPLACE YOUR_USERNAME with your PythonAnywhere login
USERNAME = 'YOUR_USERNAME'
project_home = f'/home/{USERNAME}/steam_clone'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load .env from project root (python-dotenv is in requirements.txt)
env_path = Path(project_home) / '.env'
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'steam_clone.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
