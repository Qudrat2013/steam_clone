from django.shortcuts import render

def launcher_game_page(request):
    """Отображает страницу управления играми hz.html"""
    return render(request, 'hz.html')