# 🎮 Steam Clone — Django

Полноценный клон Steam на Django: магазин, библиотека, друзья, чат, маркет, кошелёк, поддержка, Steam Plus, REST API + Swagger.

## Локальный запуск

```bash
# 1. Зависимости
pip install -r requirements.txt

# 2. Переменные окружения
cp .env.example .env
# отредактируйте .env (SECRET_KEY, email при необходимости)

# 3. Миграции
python manage.py migrate

# 4. Суперпользователь
python manage.py createsuperuser

# 5. (опционально) демо FAQ
python manage.py seed_support

# 6. Сервер
python manage.py runserver
```

Открыть: **http://127.0.0.1:8000**

- Админка: http://127.0.0.1:8000/admin/
- Swagger API: http://127.0.0.1:8000/swagger/
- Панель модерации: http://127.0.0.1:8000/dashboard/

## Что внутри

| Раздел | Описание |
|--------|----------|
| Магазин | Игры, скидки, отзывы, wishlist |
| Корзина / библиотека | Покупки, скачивание |
| Друзья / чат | Статусы, стикеры |
| Инвентарь / трейды / маркет | Предметы и торговля |
| Кошелёк | Баланс, пополнения |
| Steam Plus | Discovery Queue, daily bonus, points, news |
| Support | FAQ, тикеты, баны, возвраты, промокоды |
| Dashboard | Админ-панель модерации |
| REST API | Token auth + Swagger / ReDoc |

## Публикация на PythonAnywhere

Подробная инструкция: **[DEPLOY_PYTHONANYWHERE.md](DEPLOY_PYTHONANYWHERE.md)**

Кратко:

1. `git clone` репозитория на PythonAnywhere  
2. `venv` + `pip install -r requirements.txt`  
3. `.env` с `DJANGO_DEBUG=False` и вашим доменом  
4. `migrate` + `collectstatic`  
5. Web app → WSGI → static/media mapping → **Reload**

## Структура

```
steam_clone/
├── manage.py
├── requirements.txt
├── steam_clone/          # settings, urls, wsgi
├── games/ users/ cart/   # ядро
├── friends/ chat/ groups/
├── inventory/ trades/ marketplace/ wallet/
├── steamplus/ support/ dashboard/
├── api/                  # DRF + Swagger
├── templates/ static/
└── DEPLOY_PYTHONANYWHERE.md
```
