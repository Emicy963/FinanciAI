from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('credito.urls')),
]

# Configuração para servir arquivos de mídia durante desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customização do Admin
admin.site.site_header = "FinanciAI Angola - Administração"
admin.site.site_title = "FinanciAI Admin"
admin.site.index_title = "Painel de Administração"

