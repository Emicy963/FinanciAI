# credito/urls.py (URLs da aplicação de crédito)
from django.urls import path
from . import views

urlpatterns = [
    # Páginas principais
    path('', views.home, name='home'),
    path('sobre/', views.about, name='about'),
    path('contato/', views.contact, name='contact'),
    
    # Autenticação personalizada
    path('registro/', views.register, name='register'),
    
    # Dashboard e perfil
    path('dashboard/', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil_cliente, name='perfil'),
    
    # Solicitações de Crédito
    path('credito/', views.SolicitacaoCreditoListView.as_view(), name='credito_list'),
    path('credito/nova/', views.SolicitacaoCreditoCreateView.as_view(), name='credito_create'),
    path('credito/<int:pk>/', views.SolicitacaoCreditoDetailView.as_view(), name='credito_detail'),
    
    # Processamento de análise via AJAX
    path('credito/<int:pk>/processar/', views.processar_analise_ajax, name='processar_analise'),
    
    # Histórico de Crédito
    path('historico/', views.HistoricoCreditoListView.as_view(), name='historico_list'),
    path('historico/novo/', views.HistoricoCreditoCreateView.as_view(), name='historico_create'),
    path('historico/<int:pk>/editar/', views.HistoricoCreditoUpdateView.as_view(), name='historico_edit'),
    path('historico/<int:pk>/excluir/', views.HistoricoCreditoDeleteView.as_view(), name='historico_delete'),
    
    # Relatórios e Estatísticas
    path('relatorios/', views.relatorios, name='relatorios'),
    
    # URLs administrativas (para staff)
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
]

# URLs auxiliares que podem ser adicionadas conforme necessário
