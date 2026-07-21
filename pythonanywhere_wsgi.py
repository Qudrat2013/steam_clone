"""
Скопируйте это в WSGI-файл на PythonAnywhere
(Web → WSGI configuration file), заменив YOUR_USERNAME.
"""
import os
import sys

# >>> ЗАМЕНИТЕ YOUR_USERNAME на логин PythonAnywhere
path = '/home/YOUR_USERNAME/steam_clone'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'steam_clone.settings')

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
