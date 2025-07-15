from django.urls import path
from . import views

app_name = 'puente'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/registrar-auto/', views.registrar_auto, name='registrar_auto'),
    path('api/solicitar-cruce/', views.solicitar_cruce, name='solicitar_cruce'),
    path('api/finalizar-cruce/', views.finalizar_cruce, name='finalizar_cruce'),
    path('api/estado-puente/', views.estado_puente, name='estado_puente'),
    path('api/estado-colas/', views.estado_colas, name='estado_colas'),
] 