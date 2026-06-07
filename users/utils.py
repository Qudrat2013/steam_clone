from .models import UserDevice

def get_client_ip(request):
    """Корректно получает IP-адрес, даже если сайт за прокси-сервером"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def register_user_device(request, user):
    """Записывает новое устройство или обновляет данные текущей сессии"""
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    ip = get_client_ip(request)
    
    # Считываем данные из middleware (django-user-agents)
    user_agent = request.user_agent
    
    if user_agent.is_mobile:
        device_type = "Mobile"
    elif user_agent.is_tablet:
        device_type = "Tablet"
    elif user_agent.is_pc:
        device_type = "PC"
    else:
        device_type = "Unknown"
        
    browser = f"{user_agent.browser.family} {user_agent.browser.version_string}"
    os = f"{user_agent.os.family} {user_agent.os.version_string}"
    
    # Сохраняем в базу
    UserDevice.objects.update_or_create(
        session_key=session_key,
        defaults={
            'user': user,
            'ip_address': ip,
            'device_type': device_type,
            'browser': browser,
            'os': os
        }
    )