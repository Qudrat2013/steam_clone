from django.contrib import admin
from .models import UserDevice

@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    # Колонки в общем списке (добавили страну и город)
    list_display = ('user', 'device_type', 'country', 'city', 'ip_address', 'last_activity')
    
    # Поиск по юзернейму, IP, браузеру, ОС, стране и городу
    search_fields = ('user__username', 'ip_address', 'browser', 'os', 'country', 'city')
    
    # Фильтры в правой панели
    list_filter = ('device_type', 'os', 'browser', 'country', 'city', 'last_activity')
    
    # Запрещаем редактировать эти поля в админке, чтобы ничего не сломать
    readonly_fields = ('user', 'session_key', 'ip_address', 'country', 'city', 'device_type', 'browser', 'os', 'last_activity')

    # Красивое распределение полей внутри карточки устройства
    fieldsets = (
        ('Информация о пользователе', {
            'fields': ('user', 'session_key')
        }),
        ('Данные подключения и Локация', {
            'fields': ('ip_address', 'country', 'city', 'last_activity')
        }),
        ('Характеристики устройства', {
            'fields': ('device_type', 'browser', 'os')
        }),
    )

    def has_add_permission(self, request):
        # Запрещаем создавать устройства вручную через кнопку "Добавить"
        return False