from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Cliente, SolicitacaoCredito, HistoricoCredito
from django.core.exceptions import ValidationError
import datetime

class CustomUserCreationForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30, 
        required=True, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome'
        })
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sobrenome'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email'
        })
    )

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "password1", "password2")
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome de usuário'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Senha'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmar senha'
        })

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        exclude = ['usuario', 'score_credito', 'limite_credito_atual', 'ativo']
        widgets = {
            'tipo_documento': forms.Select(attrs={'class': 'form-select'}),
            'numero_documento': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 123456789BA123'
            }),
            'data_nascimento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'estado_civil': forms.Select(attrs={'class': 'form-select'}),
            'telefone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: +244 912 345 678'
            }),
            'telefone_alternativo': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: +244 923 456 789'
            }),
            'provincia': forms.Select(attrs={'class': 'form-select'}),
            'municipio': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Município'
            }),
            'bairro': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bairro'
            }),
            'endereco_completo': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Endereço completo com referências'
            }),
            'profissao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Engenheiro, Professor, Comerciante'
            }),
            'empresa': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da empresa onde trabalha'
            }),
            'salario_mensal': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 150000.00',
                'step': '0.01'
            }),
            'tempo_servico_anos': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 5'
            }),
            'banco_principal': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: BAI, BFA, BIC'
            }),
            'numero_conta': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Número da conta bancária'
            }),
            'possui_outras_contas': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    # Campos adicionais para o usuário (não fazem parte do modelo Cliente)
    nome_completo = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome completo'
        }),
        label='Nome Completo'
    )
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'seu@email.com'
        }),
        label='Email'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se estamos editando um cliente existente, preencher os campos do usuário
        if self.instance and self.instance.pk and hasattr(self.instance, 'usuario'):
            user = self.instance.usuario
            self.fields['nome_completo'].initial = f"{user.first_name} {user.last_name}".strip()
            self.fields['email'].initial = user.email

    def save(self, commit=True):
        cliente = super().save(commit=False)
        
        # Atualizar dados do usuário relacionado
        if hasattr(cliente, 'usuario') and cliente.usuario:
            user = cliente.usuario
            nome_completo = self.cleaned_data.get('nome_completo', '')
            email = self.cleaned_data.get('email', '')
            
            # Dividir nome completo em primeiro e último nome
            nomes = nome_completo.split()
            if nomes:
                user.first_name = nomes[0]
                user.last_name = ' '.join(nomes[1:]) if len(nomes) > 1 else ''
            
            user.email = email
            
            if commit:
                user.save()
        
        if commit:
            cliente.save()
        
        return cliente

    def clean_data_nascimento(self):
        data_nascimento = self.cleaned_data['data_nascimento']
        hoje = datetime.date.today()
        idade = hoje.year - data_nascimento.year - ((hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day))
        
        if idade < 18:
            raise ValidationError("Cliente deve ter pelo menos 18 anos.")
        if idade > 80:
            raise ValidationError("Idade máxima permitida é 80 anos.")
        
        return data_nascimento

    def clean_numero_documento(self):
        numero = self.cleaned_data['numero_documento']
        if len(numero) < 10:
            raise ValidationError("Número do documento deve ter pelo menos 10 caracteres.")
        return numero.upper()

    def clean_salario_mensal(self):
        salario = self.cleaned_data['salario_mensal']
        if salario < 30000:  # Salário mínimo em Angola (aproximadamente)
            raise ValidationError("Salário informado está abaixo do mínimo permitido.")
        return salario


class SolicitacaoCreditoForm(forms.ModelForm):
    renda_mensal = forms.DecimalField(
        max_digits=15,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 150000.00',
            'step': '0.01'
        }),
        label='Renda Mensal (AOA)'
    )
    
    profissao = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: Engenheiro, Professor'
        }),
        label='Profissão'
    )
    
    tempo_emprego = forms.IntegerField(
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 24'
        }),
        label='Tempo de Emprego (Meses)'
    )
    
    tem_conta_bancaria = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Possui Conta Bancária'
    )
    
    tem_historico_credito = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='Possui Histórico de Crédito'
    )
    
    observacoes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Informações adicionais...'
        }),
        label='Observações'
    )
    class Meta:
        model = SolicitacaoCredito
        fields = ['valor_solicitado', 'finalidade', 'prazo_meses']
        widgets = {
            'valor_solicitado': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 500000.00',
                'step': '0.01',
                'min': '10000'
            }),
            'finalidade': forms.Select(attrs={'class': 'form-select'}),
            'prazo_meses': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 24',
                'min': '3',
                'max': '240'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.cliente = kwargs.pop('cliente', None)
        super().__init__(*args, **kwargs)

    def clean_valor_solicitado(self):
        valor = self.cleaned_data['valor_solicitado']
        if valor < 50000:  # Atualizar para coincidir com o template
            raise ValidationError("Valor mínimo para solicitação é de 50.000,00 AOA.")
        if valor > 5000000:  # Atualizar para coincidir com o template
            raise ValidationError("Valor máximo para solicitação é de 5.000.000,00 AOA.")
        
        # Verificar capacidade de pagamento baseada na renda informada
        renda_mensal = self.cleaned_data.get('renda_mensal')
        if renda_mensal:
            # Máximo de 5x a renda mensal
            valor_maximo = renda_mensal * 5
            if valor > valor_maximo:
                raise ValidationError(f"Valor solicitado excede 5x sua renda mensal. Máximo permitido: {valor_maximo:,.2f} AOA")
        
        return valor

    def clean_prazo_meses(self):
        prazo = self.cleaned_data['prazo_meses']
        if prazo < 6:
            raise ValidationError("Prazo mínimo é de 6 meses.")
        if prazo > 60:
            raise ValidationError("Prazo máximo é de 60 meses.")
        
        finalidade = self.cleaned_data.get('finalidade')
        
        # Regras específicas por finalidade (se ainda quiser manter)
        if finalidade == 'PESSOAL' and prazo > 60:
            raise ValidationError("Prazo máximo para crédito pessoal é de 60 meses.")
        elif finalidade == 'AUTOMOVEL' and prazo > 84:
            raise ValidationError("Prazo máximo para crédito automóvel é de 84 meses.")
        elif finalidade == 'HABITACAO' and prazo > 240:
            raise ValidationError("Prazo máximo para crédito habitação é de 240 meses.")
        
        return prazo


class HistoricoCreditoForm(forms.ModelForm):
    class Meta:
        model = HistoricoCredito
        exclude = ['cliente', 'data_registro']
        widgets = {
            'tipo_credito': forms.Select(attrs={'class': 'form-select'}),
            'instituicao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nome da instituição financeira'
            }),
            'valor_original': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'valor_em_aberto': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01'
            }),
            'data_contratacao': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'prazo_original_meses': forms.NumberInput(attrs={
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'dias_atraso_maximo': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'parcelas_pagas': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),
            'parcelas_total': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        valor_original = cleaned_data.get('valor_original')
        valor_em_aberto = cleaned_data.get('valor_em_aberto')
        parcelas_pagas = cleaned_data.get('parcelas_pagas')
        parcelas_total = cleaned_data.get('parcelas_total')

        if valor_em_aberto and valor_original and valor_em_aberto > valor_original:
            raise ValidationError("Valor em aberto não pode ser maior que o valor original.")

        if parcelas_pagas and parcelas_total and parcelas_pagas > parcelas_total:
            raise ValidationError("Parcelas pagas não pode ser maior que o total de parcelas.")

        return cleaned_data


class FiltroSolicitacaoForm(forms.Form):
    STATUS_CHOICES = [('', 'Todos os Status')] + SolicitacaoCredito.STATUS_CHOICES
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    data_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    data_fim = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    valor_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Valor mínimo'
        })
    )
    valor_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Valor máximo'
        })
    )
