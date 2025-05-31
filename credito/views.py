from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
import json

from .models import Cliente, SolicitacaoCredito, AnaliseCredito, HistoricoCredito
from .forms import (
    CustomUserCreationForm, ClienteForm, SolicitacaoCreditoForm, 
    HistoricoCreditoForm, FiltroSolicitacaoForm
)
from .credit_analyzer import CreditAnalyzer, processar_solicitacao_credito

def home(request):
    """Página inicial"""
    context = {
        'total_clientes': Cliente.objects.count(),
        'total_solicitacoes': SolicitacaoCredito.objects.count(),
        'aprovacoes_mes': SolicitacaoCredito.objects.filter(
            status='APROVADO',
            data_aprovacao__month=timezone.now().month
        ).count(),
        'volume_aprovado': SolicitacaoCredito.objects.filter(
            status='APROVADO'
        ).aggregate(Sum('valor_aprovado'))['valor_aprovado__sum'] or 0
    }
    return render(request, 'home.html', context)

def about(request):
    """Página sobre"""
    return render(request, 'about.html')

def contact(request):
    """Página de contato"""
    if request.method == 'POST':
        messages.success(request, 'Mensagem enviada com sucesso! Entraremos em contato em breve.')
        return redirect('contact')
    return render(request, 'contact.html')

def register(request):
    """Registro de usuário e cliente"""
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        cliente_form = ClienteForm(request.POST)
        
        if user_form.is_valid() and cliente_form.is_valid():
            user = user_form.save()
            cliente = cliente_form.save(commit=False)
            cliente.usuario = user
            cliente.save()
            
            username = user_form.cleaned_data.get('username')
            messages.success(request, f'Conta criada para {username}! Você já pode fazer login.')
            return redirect('login')
    else:
        user_form = CustomUserCreationForm()
        cliente_form = ClienteForm()
    
    return render(request, 'registration/register.html', {
        'user_form': user_form,
        'cliente_form': cliente_form
    })

@login_required
def dashboard(request):
    """Dashboard do cliente"""
    try:
        cliente = request.user.cliente
    except Cliente.DoesNotExist:
        messages.error(request, 'Perfil de cliente não encontrado. Entre em contato com o suporte.')
        return redirect('home')
    
    # Estatísticas do cliente
    solicitacoes = SolicitacaoCredito.objects.filter(cliente=cliente)
    
    context = {
        'cliente': cliente,
        'total_solicitacoes': solicitacoes.count(),
        'solicitacoes_aprovadas': solicitacoes.filter(status='APROVADO').count(),
        'solicitacoes_pendentes': solicitacoes.filter(status='PENDENTE').count(),
        'valor_total_aprovado': solicitacoes.filter(status='APROVADO').aggregate(
            Sum('valor_aprovado'))['valor_aprovado__sum'] or 0,
        'ultimas_solicitacoes': solicitacoes.order_by('-data_solicitacao')[:5]
    }
    
    return render(request, 'dashboard.html', context)

class SolicitacaoCreditoListView(LoginRequiredMixin, ListView):
    model = SolicitacaoCredito
    template_name = 'credito/solicitacao_list.html'
    context_object_name = 'solicitacoes'
    paginate_by = 10

    def get_queryset(self):
        queryset = SolicitacaoCredito.objects.filter(
            cliente__usuario=self.request.user
        ).order_by('-data_solicitacao')
        
        # Filtros
        form = FiltroSolicitacaoForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data['status']:
                queryset = queryset.filter(status=form.cleaned_data['status'])
            if form.cleaned_data['data_inicio']:
                queryset = queryset.filter(data_solicitacao__date__gte=form.cleaned_data['data_inicio'])
            if form.cleaned_data['data_fim']:
                queryset = queryset.filter(data_solicitacao__date__lte=form.cleaned_data['data_fim'])
            if form.cleaned_data['valor_min']:
                queryset = queryset.filter(valor_solicitado__gte=form.cleaned_data['valor_min'])
            if form.cleaned_data['valor_max']:
                queryset = queryset.filter(valor_solicitado__lte=form.cleaned_data['valor_max'])
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtro_form'] = FiltroSolicitacaoForm(self.request.GET)
        return context

class SolicitacaoCreditoCreateView(LoginRequiredMixin, CreateView):
    model = SolicitacaoCredito
    form_class = SolicitacaoCreditoForm
    template_name = 'credito/solicitacao_form.html'
    success_url = reverse_lazy('credito_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            kwargs['cliente'] = self.request.user.cliente
        except Cliente.DoesNotExist:
            pass
        return kwargs

    def form_valid(self, form):
        try:
            form.instance.cliente = self.request.user.cliente
            response = super().form_valid(form)
            
            messages.success(
                self.request, 
                'Solicitação de crédito enviada com sucesso! Você receberá uma resposta em breve.'
            )
            
            # Processar análise automática
            resultado = processar_solicitacao_credito(self.object.id)
            
            if resultado.get('aprovado'):
                messages.success(
                    self.request,
                    f'Parabéns! Seu crédito foi aprovado automaticamente no valor de '
                    f'{resultado["valor_aprovado"]:,.2f} AOA com taxa de '
                    f'{resultado["taxa_juros"]}% ao ano.'
                )
            elif not resultado.get('erro'):
                messages.info(
                    self.request,
                    f'Sua solicitação foi analisada. {resultado.get("motivo", "")}'
                )
            
            return response
            
        except Cliente.DoesNotExist:
            messages.error(self.request, 'Perfil de cliente não encontrado.')
            return redirect('register')

class SolicitacaoCreditoDetailView(LoginRequiredMixin, DetailView):
    model = SolicitacaoCredito
    template_name = 'credito/solicitacao_detail.html'
    context_object_name = 'solicitacao'

    def get_queryset(self):
        return SolicitacaoCredito.objects.filter(cliente__usuario=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Buscar análise detalhada se existir
        try:
            context['analise'] = AnaliseCredito.objects.get(solicitacao=self.object)
        except AnaliseCredito.DoesNotExist:
            context['analise'] = None
        
        return context

@login_required
def processar_analise_ajax(request, pk):
    """Processar análise via AJAX"""
    if request.method == 'POST':
        try:
            solicitacao = get_object_or_404(
                SolicitacaoCredito, 
                pk=pk, 
                cliente__usuario=request.user
            )
            
            if solicitacao.status != 'PENDENTE':
                return JsonResponse({
                    'success': False, 
                    'message': 'Solicitação já foi processada'
                })
            
            resultado = processar_solicitacao_credito(pk)
            
            if resultado.get('erro'):
                return JsonResponse({
                    'success': False, 
                    'message': resultado['erro']
                })
            
            return JsonResponse({
                'success': True,
                'aprovado': resultado.get('aprovado', False),
                'valor_aprovado': float(resultado.get('valor_aprovado', 0)),
                'taxa_juros': float(resultado.get('taxa_juros', 0)),
                'score': resultado.get('score', 0),
                'message': 'Análise processada com sucesso!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'message': f'Erro ao processar: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'})

class HistoricoCreditoListView(LoginRequiredMixin, ListView):
    model = HistoricoCredito
    template_name = 'credito/historico_list.html'
    context_object_name = 'historicos'
    paginate_by = 10

    def get_queryset(self):
        return HistoricoCredito.objects.filter(
            cliente__usuario=self.request.user
        ).order_by('-data_contratacao')

class HistoricoCreditoCreateView(LoginRequiredMixin, CreateView):
    model = HistoricoCredito
    form_class = HistoricoCreditoForm
    template_name = 'credito/historico_form.html'
    success_url = reverse_lazy('historico_list')

    def form_valid(self, form):
        try:
            form.instance.cliente = self.request.user.cliente
            messages.success(self.request, 'Histórico de crédito adicionado com sucesso!')
            return super().form_valid(form)
        except Cliente.DoesNotExist:
            messages.error(self.request, 'Perfil de cliente não encontrado.')
            return redirect('register')

class HistoricoCreditoUpdateView(LoginRequiredMixin, UpdateView):
    model = HistoricoCredito
    form_class = HistoricoCreditoForm
    template_name = 'credito/historico_form.html'
    success_url = reverse_lazy('historico_list')

    def get_queryset(self):
        return HistoricoCredito.objects.filter(cliente__usuario=self.request.user)

class HistoricoCreditoDeleteView(LoginRequiredMixin, DeleteView):
    model = HistoricoCredito
    template_name = 'credito/historico_confirm_delete.html'
    success_url = reverse_lazy('historico_list')

    def get_queryset(self):
        return HistoricoCredito.objects.filter(cliente__usuario=self.request.user)

@login_required
def perfil_cliente(request):
    """Visualizar e editar perfil do cliente"""
    try:
        cliente = request.user.cliente
    except Cliente.DoesNotExist:
        messages.error(request, 'Perfil não encontrado.')
        return redirect('register')
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('perfil')
    else:
        form = ClienteForm(instance=cliente)
    
    return render(request, 'perfil.html', {
        'form': form,
        'cliente': cliente
    })

@login_required
def relatorios(request):
    """Relatórios e estatísticas do cliente"""
    try:
        cliente = request.user.cliente
    except Cliente.DoesNotExist:
        messages.error(request, 'Perfil não encontrado.')
        return redirect('home')
    
    # Dados para gráficos
    solicitacoes = SolicitacaoCredito.objects.filter(cliente=cliente)
    
    # Solicitações por status
    status_data = list(solicitacoes.values('status').annotate(
        count=Count('id')
    ))
    
    # Solicitações por mês (últimos 12 meses)
    from django.db.models import TruncMonth
    monthly_data = list(solicitacoes.annotate(
        month=TruncMonth('data_solicitacao')
    ).values('month').annotate(
        count=Count('id'),
        valor_total=Sum('valor_solicitado')
    ).order_by('month'))
    
    # Histórico de score (se disponível)
    analises = AnaliseCredito.objects.filter(
        solicitacao__cliente=cliente
    ).order_by('data_analise')
    
    score_history = [
        {
            'data': analise.data_analise.strftime('%Y-%m-%d'),
            'score': analise.score_total
        }
        for analise in analises
    ]
    
    context = {
        'cliente': cliente,
        'status_data': json.dumps(status_data),
        'monthly_data': json.dumps(monthly_data, default=str),
        'score_history': json.dumps(score_history),
        'total_solicitado': solicitacoes.aggregate(Sum('valor_solicitado'))['valor_solicitado__sum'] or 0,
        'total_aprovado': solicitacoes.filter(status='APROVADO').aggregate(Sum('valor_aprovado'))['valor_aprovado__sum'] or 0,
    }
    
    return render(request, 'relatorios.html', context)

# Views para admin/staff (se necessário)
@login_required
def admin_dashboard(request):
    """Dashboard administrativo"""
    if not request.user.is_staff:
        messages.error(request, 'Acesso negado.')
        return redirect('home')
    
    # Estatísticas gerais
    context = {
        'total_clientes': Cliente.objects.count(),
        'total_solicitacoes': SolicitacaoCredito.objects.count(),
        'solicitacoes_pendentes': SolicitacaoCredito.objects.filter(status='PENDENTE').count(),
        'taxa_aprovacao': SolicitacaoCredito.objects.filter(
            status__in=['APROVADO', 'REJEITADO']
        ).aggregate(
            aprovadas=Count('id', filter=Q(status='APROVADO')),
            total=Count('id')
        ),
        'volume_total': SolicitacaoCredito.objects.filter(
            status='APROVADO'
        ).aggregate(Sum('valor_aprovado'))['valor_aprovado__sum'] or 0
    }
    
    return render(request, 'admin/dashboard.html', context)
