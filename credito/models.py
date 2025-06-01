from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from datetime import date

class Cliente(models.Model):
    TIPOS_DOCUMENTOS_CHOICES = [
        ('BI', 'Bilhete de Identidade'),
        ('PASSAPORTE', 'Passaporte'),
    ]

    ESTADO_CIVIL_CHOICES = [
        ('SOLTEIRO', 'Solteiro(a)'),
        ('CASADO', 'Casado(a)'),
        ('DIVORCIADO', 'Divorciado(a)'),
        ('VIUVO', 'Viúvo(a)'),
    ]
    
    PROVINCIA_CHOICES = [
        ('LUANDA', 'Luanda'),
        ('BENGUELA', 'Benguela'),
        ('HUAMBO', 'Huambo'),
        ('NAMIBE', 'Namibe'),
        ('HUILA', 'Huíla'),
        ('CABINDA', 'Cabinda'),
        ('UIGE', 'Uíge'),
        ('ZAIRE', 'Zaire'),
        ('MALANJE', 'Malanje'),
        ('LUNDA_NORTE', 'Lunda Norte'),
        ('LUNDA_SUL', 'Lunda Sul'),
        ('MOXICO', 'Moxico'),
        ('CUANDO_CUBANGO', 'Cuando Cubango'),
        ('CUNENE', 'Cunene'),
        ('BIE', 'Bié'),
        ('BENGO', 'Bengo'),
        ('CUANZA_NORTE', 'Cuanza Norte'),
        ('CUANZA_SUL', 'Cuanza Sul'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE)

    # Dados Pessoais
    tipo_documento = models.CharField(max_length=10, choices=TIPOS_DOCUMENTOS_CHOICES, default='BI')
    numero_documento = models.CharField(max_length=20, unique=True, verbose_name='Número do Documento')
    data_nascimento = models.DateField()
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, default='SOLTEIRO')
    telefone = models.CharField(max_length=15, blank=True, null=True)
    telefone_alternativo = models.CharField(max_length=15, blank=True, null=True)

    # Endereço
    provincia = models.CharField(max_length=20, choices=PROVINCIA_CHOICES)
    municipio = models.CharField(max_length=100)
    bairro = models.CharField(max_length=100)
    endereco_completo = models.TextField()

    # Dados profissionais
    profissao = models.CharField(max_length=100)
    empresa = models.CharField(max_length=100)
    salario_mensal = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    tempo_servico_anos = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    
    # Dados bancários
    banco_principal = models.CharField(max_length=100)
    numero_conta = models.CharField(max_length=30)
    possui_outras_contas = models.BooleanField(default=False)
    
    # Score e histórico
    score_credito = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(1000)])
    limite_credito_atual = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Dados do sistema
    data_cadastro = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.usuario.first_name} {self.usuario.last_name} - {self.numero_documento}"
    
    @property
    def idade(self):
        if not self.data_nascimento:
            return None
        today = date.today()  # Uso correto
        age = today.year - self.data_nascimento.year
        # Ajuste para aniversário não ocorrido neste ano
        if (today.month, today.day) < (self.data_nascimento.month, self.data_nascimento.day):
            age -= 1
        return age
    
    @property
    def nome_completo(self):
        return f"{self.usuario.first_name} {self.usuario.last_name}"

class SolicitacaoCredito(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Análise Pendente'),
        ('ANALISE', 'Em Análise'),
        ('APROVADO', 'Aprovado'),
        ('REJEITADO', 'Rejeitado'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    FINALIDADE_CHOICES = [
        ('PESSOAL', 'Crédito Pessoal'),
        ('HABITACAO', 'Crédito Habitação'),
        ('AUTOMOVEL', 'Crédito Automóvel'),
        ('EDUCACAO', 'Crédito Educação'),
        ('CONSOLIDACAO', 'Consolidação de Dívidas'),
        ('NEGOCIO', 'Capital de Giro'),
        ('OUTROS', 'Outros'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="solicitacoes_credito")
    
    # Dados da solicitação
    valor_solicitado = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('10000.00'))]  # Mínimo 10,000 AOA
    )
    finalidade = models.CharField(max_length=15, choices=FINALIDADE_CHOICES)
    prazo_meses = models.IntegerField(
        validators=[MinValueValidator(3), MaxValueValidator(240)]  # 3 meses a 20 anos
    )
    
    # Resultado da análise
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDENTE')
    valor_aprovado = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    taxa_juros_anual = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Taxa de juros anual em %"
    )
    
    # Observações da análise
    motivo_rejeicao = models.TextField(blank=True, null=True)
    observacoes_analise = models.TextField(blank=True, null=True)
    
    # Timestamps
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_analise = models.DateTimeField(null=True, blank=True)
    data_aprovacao = models.DateTimeField(null=True, blank=True)
    
    # Dados do analista (para auditoria)
    analisado_por = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="analises_realizadas"
    )
    
    def __str__(self):
        return f"Solicitação #{self.id} - {self.cliente.nome_completo} - {self.get_status_display()}"
    
    @property
    def valor_parcela_estimada(self):
        if self.valor_aprovado and self.taxa_juros_anual and self.prazo_meses:
            # Cálculo simplificado da parcela (SAC)
            valor = float(self.valor_aprovado)
            taxa_mensal = float(self.taxa_juros_anual) / 12 / 100
            parcelas = self.prazo_meses
            
            if taxa_mensal > 0:
                parcela = valor * (taxa_mensal * (1 + taxa_mensal)**parcelas) / ((1 + taxa_mensal)**parcelas - 1)
                return Decimal(str(round(parcela, 2)))
            else:
                return self.valor_aprovado / self.prazo_meses
        return None
    
    class Meta:
        ordering = ['-data_solicitacao']
        verbose_name = "Solicitação de Crédito"
        verbose_name_plural = "Solicitações de Crédito"

class AnaliseCredito(models.Model):
    """Modelo para armazenar detalhes da análise automática"""
    
    solicitacao = models.OneToOneField(
        SolicitacaoCredito, 
        on_delete=models.CASCADE,
        related_name="analise_detalhada"
    )
    
    # Scores individuais dos critérios
    score_idade = models.IntegerField(default=0)
    score_renda = models.IntegerField(default=0)
    score_tempo_servico = models.IntegerField(default=0)
    score_historico = models.IntegerField(default=0)
    score_divida_renda = models.IntegerField(default=0)
    score_localizacao = models.IntegerField(default=0)
    
    # Score final e decisão
    score_total = models.IntegerField(default=0)
    risco_calculado = models.CharField(max_length=10, choices=[
        ('BAIXO', 'Baixo'),
        ('MEDIO', 'Médio'),
        ('ALTO', 'Alto'),
        ('CRITICO', 'Crítico'),
    ])
    
    # Detalhes da análise
    relacao_divida_renda = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    capacidade_pagamento = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Log da análise
    detalhes_analise = models.JSONField(default=dict, blank=True)
    data_analise = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Análise - Solicitação #{self.solicitacao.id} - Score: {self.score_total}"


class HistoricoCredito(models.Model):
    """Histórico de créditos anteriores do cliente"""
    
    TIPO_CREDITO_CHOICES = [
        ('PESSOAL', 'Crédito Pessoal'),
        ('HABITACAO', 'Crédito Habitação'),
        ('AUTOMOVEL', 'Crédito Automóvel'),
        ('CARTAO', 'Cartão de Crédito'),
        ('OUTROS', 'Outros'),
    ]
    
    STATUS_CHOICES = [
        ('ATIVO', 'Ativo'),
        ('QUITADO', 'Quitado em Dia'),
        ('QUITADO_ATRASO', 'Quitado com Atraso'),
        ('INADIMPLENTE', 'Inadimplente'),
        ('RENEGOCIADO', 'Renegociado'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="historico_credito")
    
    tipo_credito = models.CharField(max_length=15, choices=TIPO_CREDITO_CHOICES)
    instituicao = models.CharField(max_length=100)
    valor_original = models.DecimalField(max_digits=12, decimal_places=2)
    valor_em_aberto = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    data_contratacao = models.DateField()
    prazo_original_meses = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    
    dias_atraso_maximo = models.IntegerField(default=0)
    parcelas_pagas = models.IntegerField(default=0)
    parcelas_total = models.IntegerField()
    
    data_registro = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.cliente.nome_completo} - {self.get_tipo_credito_display()} - {self.get_status_display()}"
    
    class Meta:
        ordering = ['-data_contratacao']
