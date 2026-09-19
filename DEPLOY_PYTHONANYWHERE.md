# Деплой Steam Clone на PythonAnywhere

Сайт: `https://ВАШ_ЛОГИН.pythonanywhere.com`

## 🚀 Быстрый способ (рекомендуется) — 1 команда

1. Зарегистрируйся на https://www.pythonanywhere.com (Free-плана хватает).
2. Открой **Bash console** и выполни:

```bash
git clone https://github.com/Qudrat2013/steam_clone.git ~/steam_clone && cd ~/steam_clone && bash setup_pythonanywhere.sh
```

Код уже в GitHub: `https://github.com/Qudrat2013/steam_clone` (ветка `main`).
Скрипт сам: создаст venv, установит зависимости, сгенерирует `.env`
со секретным ключом и твоим доменом, сделает миграции и collectstatic.

3. Следуй финальной подсказке скрипта (Web tab: пути, WSGI, static mapping) → **Reload**.
4. Положи на хостинг сборку лаунчера (в git её нет — это артефакт):

```bash
# вариант A: в браузере — Files → Upload в папку
#            /home/ЛОГИН/steam_clone/static/downloads/
# вариант B: с домашнего ПК, из папки проекта (нужен API-токен:
#            Account → API token → Create a new API token)
python upload_to_pythonanywhere.py ЛОГИН API_ТОКЕН
```

Суперюзер (если нужен доступ в админку):

```bash
cd ~/steam_clone && source venv/bin/activate && python manage.py createsuperuser
```

## 1. Аккаунт

1. Регистрация: https://www.pythonanywhere.com  
2. Free plan достаточно (HTTP/HTTPS, SQLite, ~512 MB).

## 2. Загрузить код

### Вариант A — Git (рекомендуется)

В **Bash console** на PythonAnywhere:

```bash
cd ~
git clone https://github.com/Qudrat2013/steam_clone.git
cd steam_clone
```

### Вариант B — ZIP

Web → Files → загрузить ZIP → распаковать в `/home/ВАШ_ЛОГИН/steam_clone`.

## 3. Виртуальное окружение

```bash
cd ~/steam_clone
python3.12 -m venv venv
# если 3.12 нет: python3.10 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Django 5/6 нужен Python **3.10+**. В Web app выберите ту же версию, что и venv.

## 4. Переменные окружения

```bash
cd ~/steam_clone
nano .env
```

```env
DJANGO_SECRET_KEY=сгенерируйте-длинный-случайный-ключ-минимум-50-символов
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=ВАШ_ЛОГИН.pythonanywhere.com
CSRF_TRUSTED_ORIGINS=https://ВАШ_ЛОГИН.pythonanywhere.com
DJANGO_SECURE_SSL_REDIRECT=False
EMAIL_HOST_USER=you@gmail.com
EMAIL_HOST_PASSWORD=your-gmail-app-password
```

Сохранить: `Ctrl+O`, Enter, `Ctrl+X`.

Сгенерировать SECRET_KEY:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 5. База и статика

```bash
cd ~/steam_clone
source venv/bin/activate
mkdir -p media/avatars media/games media/items media/groups/avatars media/groups/banners media/stickers
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
# опционально — демо FAQ:
python manage.py seed_support
```

## 6. Web App (WSGI)

1. **Web** → **Add a new web app** → **Manual configuration** → Python 3.12 (или 3.10)  
2. **Source code**: `/home/ВАШ_ЛОГИН/steam_clone`  
3. **Working directory**: `/home/ВАШ_ЛОГИН/steam_clone`  
4. **Virtualenv**: `/home/ВАШ_ЛОГИН/steam_clone/venv`  
5. Откройте **WSGI configuration file**, удалите всё и вставьте:

```python
import os
import sys
from pathlib import Path

# >>> замените ВАШ_ЛОГИН
USERNAME = 'ВАШ_ЛОГИН'
project_home = f'/home/{USERNAME}/steam_clone'

if project_home not in sys.path:
    sys.path.insert(0, project_home)

env_path = Path(project_home) / '.env'
if env_path.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass

os.environ['DJANGO_SETTINGS_MODULE'] = 'steam_clone.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

6. **Static files** (раздел Static files):

| URL        | Directory                                   |
|------------|---------------------------------------------|
| `/static/` | `/home/ВАШ_ЛОГИН/steam_clone/staticfiles`   |
| `/media/`  | `/home/ВАШ_ЛОГИН/steam_clone/media`         |

7. Нажмите **Reload** (зелёная кнопка).

## 7. Обновление после правок

```bash
cd ~/steam_clone
source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
# Web → Reload
```

Если изменилась сборка лаунчера — с домашнего ПК:

```powershell
python upload_to_pythonanywhere.py ЛОГИН API_ТОКЕН
```

### ⚠ GitHub недоступен с домашнего ПК?

У некоторых провайдеров `github.com:443` блокируется (при этом `api.github.com`
работает). Тогда обычный `git push` не проходит. Варианты:
1. Раздать интернет с телефона/другого провайдера и сделать `git push`.
2. Обновлять код прямо на PythonAnywhere в консоли: там `git clone`/`git pull`
   с GitHub работают всегда.
3. Заливать изменённые файлы через **Files → Upload** или скриптом
   `upload_to_pythonanywhere.py --local ФАЙЛ --remote /home/ЛОГИН/...`.

## Частые ошибки

| Ошибка | Решение |
|--------|---------|
| DisallowedHost | `DJANGO_ALLOWED_HOSTS` = ваш домен без пробелов |
| 400 CSRF | `CSRF_TRUSTED_ORIGINS=https://логин.pythonanywhere.com` |
| нет CSS | `collectstatic` + Static files mapping в Web tab |
| ModuleNotFoundError | Virtualenv path в Web tab, Reload |
| 500 | **Web → Log files → Error log** |
| нет картинок | mapping `/media/` + папки `media/...` |
| sqlite locked | не запускайте два `migrate` параллельно |

## Безопасность

- Не коммитьте `.env` и `db.sqlite3`
- На production: `DJANGO_DEBUG=False`
- Не публикуйте Gmail App Password
- Пополнение баланса: заявки модерируются в `/dashboard/` (staff)


## 🎮 Лаунчер и хостинг

После деплоя лаунчер может работать с облачным сайтом:

- **Скачивание лаунчера**: `https://домен/launcher-api/download/` — качается exe из `static/downloads/`
  (файл заливается отдельно, см. пункт 4 быстрого старта).
- **Адрес сервера в лаунчере**: на экране входа есть поле
  «Адрес сервера» + кнопка **ПОДКЛЮЧИТЬ**. Впиши `http://127.0.0.1:8000` для
  локального сайта или `https://логин.pythonanywhere.com` для хостинга —
  адрес сохраняется в `%LOCALAPPDATA%\SteamCloneLauncher\config.json` и
  используется при следующих запусках. Рядом подсвечивается статус
  (🟢 сервер на связи / 🔴 недоступен) — это запрос к `/launcher-api/client/ping/`.
- **Регистрация / QR-вход**: работает из коробки. QR-код содержит публичный
  адрес (`https://домен/launcher-api/qr/<код>/`), поэтому телефон открывает
  его откуда угодно — Wi-Fi и локальная сеть не нужны. При локальном запуске
  (адрес 127.0.0.1) QR-ссылка автоматически становится `http://<LAN-IP>:8000/...`,
  чтобы телефон в той же сети тоже мог её открыть.
- **Чат, магазин, покупки, бонус, профиль** — работают через тот же API.
- **Ограничение QR**: 15 сек кулдаун; каждые 5 обновлений -> бан 20 мин -> 1 ч -> 2 ч -> 4 ч.

⚠ **Запуск .exe игр**: файлы игр лежат на диске сервера. Если лаунчер запущен
на другом ПК, путь `exe_path` на нём не существует — у карточки будет кнопка
«УСТАНОВИТЬ» (открывает страницу игры на сайте). Варианты:
1. Играть с того же ПК, где лежит проект (сервер локально).
2. Позже можно добавить в лаунчер скачивание файлов игр (по запросу).

## 💾 Диск (важно для Free-плана)

Бесплатный аккаунт PythonAnywhere — **512 МБ** диска на всё. В проекте
папка `media/games/files` (455 МБ) — это exe-файлы игр, они в git не входят и
на хостинг их копировать не нужно: сервер их не запускает. Нужны только:

| Что | Размер | Как попадает |
|-----|--------|--------------|
| код (`git clone`) | ~1 МБ | `git clone` |
| статика (`collectstatic`) | ~60 МБ | `collectstatic` |
| картинки игр/аватары (`media/...`) | ~20 МБ | Upload по желанию |
| `static/downloads/SteamCloneLauncher.exe` | ~36 МБ | `upload_to_pythonanywhere.py` |
| `db.sqlite3` | <1 МБ | создаётся `migrate` |

Проверить занятое место: **Files** → сверху показывает квоту.

## 📦 Что добавилось в requirements

- `qrcode>=7.4` — генерация QR-кодов для входа в лаунчер (обязательно на хостинге).
