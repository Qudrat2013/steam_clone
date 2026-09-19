#!/usr/bin/env bash
# ============================================================
#  Steam Clone — установка на PythonAnywhere (одна команда)
#  Запуск в Bash console:  bash setup_pythonanywhere.sh
# ============================================================
set -e

DOMAIN="$USER.pythonanywhere.com"
PROJ="$HOME/steam_clone"

echo "==> Домен: $DOMAIN"

# 1. Код
if [ ! -d "$PROJ" ]; then
  echo "==> Клонирую репозиторий..."
  git clone https://github.com/Qudrat2013/steam_clone.git "$PROJ"
fi
cd "$PROJ"
git pull --rebase 2>/dev/null || true

# 2. Виртуальное окружение
if [ ! -d venv ]; then
  echo "==> Создаю venv..."
  (python3 -m venv venv 2>/dev/null || python3.10 -m venv venv)
fi
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

# 3. .env (если нет — создаю с новым ключом)
if [ ! -f .env ]; then
  KEY=$(python -c "import secrets; print(secrets.token_urlsafe(50))")
  cat > .env <<EOF
DJANGO_SECRET_KEY=$KEY
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=$DOMAIN,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://$DOMAIN
DJANGO_SECURE_SSL_REDIRECT=False
EOF
  echo "==> .env создан (секретный ключ сгенерирован)"
else
  echo "==> .env уже существует — не трогаю"
fi

# 4. Папки media
mkdir -p media/avatars media/games/files media/games/headers \
         media/games/backgrounds media/games/screenshots \
         media/items media/stickers media/groups/avatars media/groups/banners

# 5. База + статика
echo "==> Миграции..."
python manage.py migrate --noinput
echo "==> Сбор статики..."
python manage.py collectstatic --noinput

echo ""
echo "======================================================"
echo " ГОТОВО! Осталось в Web-интерфейсе (Web tab):"
echo "------------------------------------------------------"
echo " Source dir / Working dir: $PROJ"
echo " Virtualenv:               $PROJ/venv"
echo " WSGI файл: содержимое pythonanywhere_wsgi.py,"
echo "   в нём замени YOUR_USERNAME на $USER"
echo " Static files:"
echo "   /static/ -> $PROJ/staticfiles"
echo "   /media/  -> $PROJ/media"
echo " Затем зелёная кнопка Reload."
echo " Сайт: https://$DOMAIN"
echo "======================================================"