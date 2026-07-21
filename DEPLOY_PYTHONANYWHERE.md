# Деплой Steam Clone на PythonAnywhere

Сайт будет доступен по адресу: `https://ВАШ_ЛОГИН.pythonanywhere.com`

## 1. Аккаунт

1. Зарегистрируйтесь: https://www.pythonanywhere.com  
2. Free plan достаточно для старта (HTTP, SQLite, ~512 MB).

## 2. Загрузить код

### Вариант A — через Git (рекомендуется)

В **Bash console** на PythonAnywhere:

```bash
cd ~
git clone https://github.com/Qudrat2013/steam_clone.git
cd steam_clone
```

### Вариант B — вручную

Web → Files → загрузить ZIP проекта и распаковать в `/home/ВАШ_ЛОГИН/steam_clone`.

## 3. Виртуальное окружение

```bash
cd ~/steam_clone
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> На free tier выберите Python **3.10+** (лучше 3.12). Django 5/6 требует современный Python.

## 4. Переменные окружения

```bash
cd ~/steam_clone
nano .env
```

Вставьте (подставьте свой логин PythonAnywhere):

```env
DJANGO_SECRET_KEY=сгенерируйте-длинный-случайный-ключ-минимум-50-символов
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=ВАШ_ЛОГИН.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://ВАШ_ЛОГИН.pythonanywhere.com
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
```

Сохранить: `Ctrl+O`, Enter, `Ctrl+X`.

## 5. База и статика

```bash
cd ~/steam_clone
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
# опционально — демо FAQ/поддержка:
python manage.py seed_support
```

## 6. Web App (WSGI)

1. **Web** → **Add a new web app** → Manual configuration → Python 3.12  
2. **Source code**: `/home/ВАШ_ЛОГИН/steam_clone`  
3. **Working directory**: `/home/ВАШ_ЛОГИН/steam_clone`  
4. **Virtualenv**: `/home/ВАШ_ЛОГИН/steam_clone/venv`  
5. Откройте **WSGI configuration file** и замените содержимое на:

```python
import os
import sys

path = '/home/ВАШ_ЛОГИН/steam_clone'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'steam_clone.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

6. **Static files** (раздел Static files):

| URL        | Directory                              |
|------------|----------------------------------------|
| `/static/` | `/home/ВАШ_ЛОГИН/steam_clone/staticfiles` |
| `/media/`  | `/home/ВАШ_ЛОГИН/steam_clone/media`       |

7. Нажмите **Reload** зелёной кнопкой.

## 7. Медиа и картинки

Создайте папки и при необходимости загрузите аватар по умолчанию:

```bash
mkdir -p ~/steam_clone/media/avatars
# загрузите default.png в media/avatars/ через Files
```

## 8. Обновление после правок

```bash
cd ~/steam_clone
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# Web → Reload
```

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| DisallowedHost | `DJANGO_ALLOWED_HOSTS` = ваш домен |
| 400 CSRF | `CSRF_TRUSTED_ORIGINS=https://логин.pythonanywhere.com` |
| нет CSS | `collectstatic` + Static files mapping |
| ModuleNotFoundError | Virtualenv path в Web tab |
| 500 | **Web → Log files → Error log** |

## Безопасность

- Не коммитьте `.env` и `db.sqlite3`
- На production всегда `DJANGO_DEBUG=False`
- Смените Gmail App Password, если он когда-либо попал в git
