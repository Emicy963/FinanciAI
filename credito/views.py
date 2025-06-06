from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import logout, login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.db import transaction
from django.utils import timezone
import json
import logging

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
logger = logging.getLogger(__name__)

def register(request):
    """Registro de usuário e cliente (corrigido)"""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        user_form = CustomUserCreationForm(request.POST)
        cliente_form = ClienteForm(request.POST)
        
        # Debug: Log dos dados recebidos
        logger.debug(f"POST data: {request.POST}")
        logger.debug(f"User form errors: {user_form.errors}")
        logger.debug(f"Cliente form errors: {cliente_form.errors}")
        
        if user_form.is_valid() and cliente_form.is_valid():
            try:
                # Use transação para garantir consistência
                with transaction.atomic():
                    # Criar usuário
                    user = user_form.save()
                    
                    # Criar cliente
                    cliente = cliente_form.save(commit=False)
                    cliente.usuario = user
                    
                    # Definir score inicial baseado em dados básicos
                    cliente.score_credito = 100  # Score inicial padrão
                    cliente.save()
                
                # Autenticar e fazer login
                username = user_form.cleaned_data.get('username')
                password = user_form.cleaned_data.get('password1')
                user = authenticate(username=username, password=password)
                
                if user:
                    login(request, user)
                    messages.success(
                        request, 
                        f'Conta criada com sucesso! Bem-vindo ao FinanciAI, {user.first_name}!'
                    )
                    return redirect('dashboard')
                else:
                    messages.success(request, 'Conta criada com sucesso! Você já pode fazer login.')
                    return redirect('login')
                    
            except Exception as e:
                logger.error(f'Erro ao criar conta: {str(e)}')
                messages.error(request, f'Erro ao criar conta: {str(e)}')
        else:
            # Mostrar erros específicos
            if user_form.errors:
                for field, errors in user_form.errors.items():
                    for error in errors:
                        messages.error(request, f'Dados de usuário - {field}: {error}')
            
            if cliente_form.errors:
                for field, errors in cliente_form.errors.items():
                    for error in errors:
                        messages.error(request, f'Dados pessoais - {field}: {error}')
    else:
        user_form = CustomUserCreationForm()
        cliente_form = ClienteForm()
    
    return render(request, 'registration/register.html', {
        'user_form': user_form,
        'cliente_form': cliente_form
    })

def login_view(request):
    """View de login melhorada"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Bem-vindo de volta, {user.first_name or user.username}!')
                    
                    # Verifica se tem próxima página
                    next_page = request.GET.get('next', 'dashboard')
                    return redirect(next_page)
                else:
                    messages.error(request, 'Sua conta está desativada.')
            else:
                messages.error(request, 'Nome de usuário ou senha incorretos.')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    """View de logout"""
    if request.user.is_authenticated:
        user_name = request.user.first_name or request.user.username
        logout(request)
        messages.info(request, f'Até logo, {user_name}! Você foi desconectado com sucesso.')
    
    return redirect('home')

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
    
    # Solicitações por mês (últimos 12 meses) - COMPATÍVEL COM VERSÕES ANTIGAS DO DJANGO
    import datetime
    from collections import defaultdict
    
    # Calcula o período dos últimos 12 meses
    today = datetime.date.today()
    one_year_ago = today - datetime.timedelta(days=365)
    
    # Filtra solicitações dos últimos 12 meses
    solicitacoes_last12 = solicitacoes.filter(
        data_solicitacao__gte=one_year_ago,
        data_solicitacao__lte=today
    )
    
    # Agrega dados por mês manualmente
    monthly_dict = defaultdict(lambda: {'count': 0, 'valor_total': 0})
    for s in solicitacoes_last12:
        month_key = s.data_solicitacao.strftime('%Y-%m-01')  # Formato YYYY-MM-01
        monthly_dict[month_key]['count'] += 1
        monthly_dict[month_key]['valor_total'] += s.valor_solicitado
    
    # Prepara dados ordenados por mês
    monthly_data = [
        {'month': month, 'count': data['count'], 'valor_total': data['valor_total']}
        for month, data in sorted(monthly_dict.items())
    ]
    
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
        'monthly_data': json.dumps(monthly_data),
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
