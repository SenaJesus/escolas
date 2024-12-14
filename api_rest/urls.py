from django.urls import path
from .views import (
    get_escola,
    listar_escolas_com_filtros,
    listar_todas_escolas,
    listar_estados,
    listar_cidades,
    solicitar_autorizacao,
    confirmar_autorizacao,
    submeter_avaliacao
)

urlpatterns = [
    path('escolas/<int:id>', get_escola, name='escola_detalhes'),
    path('escolas/listar', listar_escolas_com_filtros, name='listar_escolas_com_filtros'),
    path('escolas/todas', listar_todas_escolas, name='listar_todas_escolas'),
    path('estados', listar_estados, name='listar_estados'),
    path('cidades', listar_cidades, name='listar_cidades'),
    path('solicitar-autorizacao', solicitar_autorizacao, name='solicitar_autorizacao'),
    path('confirmar-autorizacao', confirmar_autorizacao, name='confirmar_autorizacao'),
    path('submeter-avaliacao/<int:escola_id>', submeter_avaliacao, name='submeter_avaliacao'),
]