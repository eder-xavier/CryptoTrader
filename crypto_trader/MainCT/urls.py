from django.urls import path
from . import views

app_name = 'MainCT'

urlpatterns = [
    path('', views.index, name='index'),
    path('buscar/', views.buscar_criptos, name='buscar_criptos'),
    path('recomendacoes/', views.recomendacoes, name='recomendacoes'),
    path('portfolio/', views.portfolio, name='portfolio'),
]