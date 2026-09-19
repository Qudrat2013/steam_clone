import io
import zipfile
from pathlib import Path

from django.http import HttpResponse, FileResponse
from django.shortcuts import render

BASE_DIR = Path(__file__).resolve().parent.parent
EXE_PATH = BASE_DIR / 'static' / 'downloads' / 'SteamCloneLauncher.exe'


def launcher_game_page(request):
    return render(request, 'hz.html')


def download_launcher(request):
    """Отдаёт exe-лаунчер, если собран; иначе ZIP-архив с исходниками."""
    if EXE_PATH.exists():
        response = FileResponse(EXE_PATH.open('rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="SteamCloneLauncher.exe"'
        response['Content-Length'] = EXE_PATH.stat().st_size
        return response

    files = [
        (BASE_DIR / 'launcher_api' / 'launcher.py', 'steam_clone_launcher/launcher.py'),
        (BASE_DIR / 'run_launcher.bat', 'steam_clone_launcher/run_launcher.bat'),
        (BASE_DIR / 'requirements-launcher.txt', 'steam_clone_launcher/requirements-launcher.txt'),
        (BASE_DIR / 'README.md', 'steam_clone_launcher/README.md'),
    ]
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for src, arcname in files:
            if src.exists():
                zf.write(str(src), arcname)
    response = HttpResponse(buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="steam_clone_launcher.zip"'
    return response
