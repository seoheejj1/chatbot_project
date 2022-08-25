from django.urls import path
from myapp import views

app_name = 'myapp'

urlpatterns = [
    path('', views.home, name='home'),
    path('rubybot/', views.rubybot, name='rubybot'),
    path('ppukkubot/', views.ppukkubot, name='ppukkubot'),
    path('storage/', views.storage, name='storage'),
    path('pstorage/', views.pstorage, name='pstorage'),
    path('del_view/<table>', views.del_view, name='del_view'),
    path('send_ppukku/',views.send_ppukku, name='send_ppukku'),
]
