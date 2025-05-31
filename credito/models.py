from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from django.core.validators import MinValueValidator, MaxValueValidator

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
