from decimal import Decimal
import datetime
from .models import Cliente, SolicitacaoCredito, AnaliseCredito, HistoricoCredito
from django.utils import timezone

class CreditAnalyzer:
    """
    Sistema de análise automática de crédito baseado em critérios angolanos
    """
    
    # Pesos dos critérios na análise (total deve ser 100)
    PESO_IDADE = 10
    PESO_RENDA = 25
    PESO_TEMPO_SERVICO = 15
    PESO_HISTORICO = 30
    PESO_DIVIDA_RENDA = 15
    PESO_LOCALIZACAO = 5
    
    # Taxas de juros por risco (% ao ano)
    TAXAS_JUROS = {
        'BAIXO': Decimal('18.5'),     # Clientes premium
        'MEDIO': Decimal('22.0'),     # Clientes padrão
        'ALTO': Decimal('26.5'),      # Clientes de risco
        'CRITICO': Decimal('30.0'),   # Risco muito alto
    }
    
    # Critérios mínimos para aprovação
    SCORE_MINIMO_APROVACAO = 650
    IDADE_MINIMA = 18
    IDADE_MAXIMA = 70
    RENDA_MINIMA = Decimal('50000')  # 50.000 AOA
    RELACAO_DIVIDA_RENDA_MAXIMA = Decimal('0.35')  # 35%
    
    def __init__(self, solicitacao):
        self.solicitacao = solicitacao
        self.cliente = solicitacao.cliente
        self.analise = None
        
    def analisar_credito(self):
        """Executa análise completa do crédito"""
        
        # Criar registro de análise
        self.analise = AnaliseCredito.objects.create(
            solicitacao=self.solicitacao
        )
        
        # Executar análises individuais
        score_idade = self._analisar_idade()
        score_renda = self._analisar_renda()
        score_tempo_servico = self._analisar_tempo_servico()
        score_historico = self._analisar_historico()
        score_divida_renda = self._analisar_relacao_divida_renda()
        score_localizacao = self._analisar_localizacao()
        
        # Calcular score total
        score_total = (
            score_idade * self.PESO_IDADE +
            score_renda * self.PESO_RENDA +
            score_tempo_servico * self.PESO_TEMPO_SERVICO +
            score_historico * self.PESO_HISTORICO +
            score_divida_renda * self.PESO_DIVIDA_RENDA +
            score_localizacao * self.PESO_LOCALIZACAO
        ) / 100
        
        # Atualizar análise
        self.analise.score_idade = score_idade
        self.analise.score_renda = score_renda
        self.analise.score_tempo_servico = score_tempo_servico
        self.analise.score_historico = score_historico
        self.analise.score_divida_renda = score_divida_renda
        self.analise.score_localizacao = score_localizacao
        self.analise.score_total = int(score_total)
        
        # Determinar risco e decisão
        risco = self._determinar_risco(score_total)
        self.analise.risco_calculado = risco
        
        # Calcular capacidade de pagamento
        capacidade = self._calcular_capacidade_pagamento()
        self.analise.capacidade_pagamento = capacidade
        
        # Calcular relação dívida/renda
        relacao_divida = self._calcular_relacao_divida_renda()
        self.analise.relacao_divida_renda = relacao_divida
        
        # Criar log detalhado
        self.analise.detalhes_analise = self._criar_log_detalhado(score_total, risco)
        
        self.analise.save()
        
        # Tomar decisão final
        return self._tomar_decisao(score_total, risco, capacidade, relacao_divida)
    
    def _analisar_idade(self):
        """Análise baseada na idade do cliente"""
        idade = self.cliente.idade
        
        if idade < self.IDADE_MINIMA or idade > self.IDADE_MAXIMA:
            return 0  # Fora da faixa etária permitida
        elif 25 <= idade <= 50:
            return 100  # Faixa etária ideal
        elif (18 <= idade < 25) or (50 < idade <= 60):
            return 80   # Boa faixa etária
        else:
            return 60   # Faixa etária de risco
    
    def _analisar_renda(self):
        """Análise baseada na renda mensal"""
        renda = self.cliente.salario_mensal
        
        if renda < self.RENDA_MINIMA:
            return 0  # Renda insuficiente
        elif renda >= Decimal('500000'):  # 500k AOA
            return 100  # Renda excelente
        elif renda >= Decimal('300000'):  # 300k AOA
            return 85   # Renda muito boa
        elif renda >= Decimal('150000'):  # 150k AOA
            return 70   # Renda boa
        elif renda >= Decimal('100000'):  # 100k AOA
            return 55   # Renda razoável
        else:
            return 40   # Renda baixa
    
    def _analisar_tempo_servico(self):
        """Análise baseada no tempo de serviço"""
        tempo = self.cliente.tempo_servico_anos
        
        if tempo >= 10:
            return 100  # Muito estável
        elif tempo >= 5:
            return 85   # Estável
        elif tempo >= 3:
            return 70   # Razoavelmente estável
        elif tempo >= 1:
            return 50   # Pouco tempo
        else:
            return 20   # Muito pouco tempo
    
    def _analisar_historico(self):
        """Análise do histórico de crédito"""
        historicos = HistoricoCredito.objects.filter(cliente=self.cliente)
        
        if not historicos.exists():
            return 70  # Sem histórico (neutro)
        
        score = 100
        pontos_negativos = 0
        
        for hist in historicos:
            if hist.status == 'INADIMPLENTE':
                pontos_negativos += 40
            elif hist.status == 'QUITADO_ATRASO':
                pontos_negativos += 15
            elif hist.status == 'RENEGOCIADO':
                pontos_negativos += 20
            elif hist.dias_atraso_maximo > 90:
                pontos_negativos += 25
            elif hist.dias_atraso_maximo > 30:
                pontos_negativos += 10
        
        score = max(0, score - pontos_negativos)
        return score
    
    def _analisar_relacao_divida_renda(self):
        """Análise da relação dívida/renda atual"""
        relacao = self._calcular_relacao_divida_renda()
        
        if relacao <= Decimal('0.20'):  # 20%
            return 100
        elif relacao <= Decimal('0.30'):  # 30%
            return 80
        elif relacao <= Decimal('0.35'):  # 35%
            return 60
        elif relacao <= Decimal('0.40'):  # 40%
            return 40
        else:
            return 0  # Comprometimento excessivo
    
    def _analisar_localizacao(self):
        """Análise baseada na localização (província)"""
        provincia = self.cliente.provincia
        
        # Províncias com maior desenvolvimento econômico
        provincias_premium = ['LUANDA', 'BENGUELA', 'HUAMBO']
        provincias_boas = ['NAMIBE', 'HUILA', 'CABINDA', 'MALANJE']
        
        if provincia in provincias_premium:
            return 100
        elif provincia in provincias_boas:
            return 80
        else:
            return 60
    
    def _calcular_relacao_divida_renda(self):
        """Calcula a relação dívida/renda atual"""
        historicos_ativos = HistoricoCredito.objects.filter(
            cliente=self.cliente,
            status='ATIVO'
        )
        
        total_dividas = sum(hist.valor_em_aberto for hist in historicos_ativos)
        
        # Adicionar valor da nova solicitação
        total_dividas += self.solicitacao.valor_solicitado
        
        if self.cliente.salario_mensal > 0:
            return total_dividas / self.cliente.salario_mensal
        else:
            return Decimal('1.0')  # Sem renda = 100% comprometimento
    
    def _calcular_capacidade_pagamento(self):
        """Calcula a capacidade de pagamento mensal"""
        renda_liquida = self.cliente.salario_mensal * Decimal('0.70')  # 70% da renda
        
        # Subtrair compromissos existentes
        historicos_ativos = HistoricoCredito.objects.filter(
            cliente=self.cliente,
            status='ATIVO'
        )
        
        compromissos_atuais = Decimal('0')
        for hist in historicos_ativos:
            # Estimar parcela mensal (valor em aberto / meses restantes)
            if hist.parcelas_total > hist.parcelas_pagas:
                meses_restantes = hist.parcelas_total - hist.parcelas_pagas
                parcela_estimada = hist.valor_em_aberto / meses_restantes
                compromissos_atuais += parcela_estimada
        
        return max(Decimal('0'), renda_liquida - compromissos_atuais)
    
    def _determinar_risco(self, score):
        """Determina o nível de risco baseado no score"""
        if score >= 850:
            return 'BAIXO'
        elif score >= 700:
            return 'MEDIO'
        elif score >= 550:
            return 'ALTO'
        else:
            return 'CRITICO'
    
    def _criar_log_detalhado(self, score_total, risco):
        """Cria log detalhado da análise"""
        return {
            'timestamp': timezone.now().isoformat(),
            'cliente_id': self.cliente.id,
            'solicitacao_id': self.solicitacao.id,
            'scores': {
                'idade': self.analise.score_idade,
                'renda': self.analise.score_renda,
                'tempo_servico': self.analise.score_tempo_servico,
                'historico': self.analise.score_historico,
                'divida_renda': self.analise.score_divida_renda,
                'localizacao': self.analise.score_localizacao,
                'total': score_total
            },
            'criterios': {
                'idade_cliente': self.cliente.idade,
                'renda_mensal': float(self.cliente.salario_mensal),
                'tempo_servico': self.cliente.tempo_servico_anos,
                'provincia': self.cliente.provincia,
                'relacao_divida_renda': float(self.analise.relacao_divida_renda),
                'capacidade_pagamento': float(self.analise.capacidade_pagamento)
            },
            'risco_determinado': risco,
            'valor_solicitado': float(self.solicitacao.valor_solicitado),
            'prazo_meses': self.solicitacao.prazo_meses,
            'finalidade': self.solicitacao.finalidade
        }
    
    def _tomar_decisao(self, score_total, risco, capacidade_pagamento, relacao_divida_renda):
        """Toma a decisão final sobre o crédito"""
        
        # Critérios de rejeição automática
        if score_total < self.SCORE_MINIMO_APROVACAO:
            return self._rejeitar_credito("Score insuficiente para aprovação")
        
        if self.cliente.idade < self.IDADE_MINIMA or self.cliente.idade > self.IDADE_MAXIMA:
            return self._rejeitar_credito("Fora da faixa etária permitida")
        
        if self.cliente.salario_mensal < self.RENDA_MINIMA:
            return self._rejeitar_credito("Renda insuficiente")
        
        if relacao_divida_renda > self.RELACAO_DIVIDA_RENDA_MAXIMA:
            return self._rejeitar_credito("Comprometimento de renda excessivo")
        
        # Calcular valor aprovado e taxa
        valor_aprovado = self._calcular_valor_aprovado()
        taxa_juros = self.TAXAS_JUROS[risco]
        
        # Verificar se valor solicitado pode ser aprovado
        if valor_aprovado < self.solicitacao.valor_solicitado * Decimal('0.5'):
            return self._rejeitar_credito("Valor solicitado muito alto para o perfil")
        
        # Aprovar crédito
        return self._aprovar_credito(valor_aprovado, taxa_juros, risco)
    
    def _calcular_valor_aprovado(self):
        """Calcula o valor que pode ser aprovado"""
        # Baseado na capacidade de pagamento e prazo
        capacidade_mensal = self.analise.capacidade_pagamento
        prazo_meses = self.solicitacao.prazo_meses
        
        # Usar uma taxa conservadora para o cálculo
        taxa_mensal = Decimal('0.02')  # 2% ao mês
        
        # Cálculo do valor máximo financiável
        if taxa_mensal > 0:
            fator = (Decimal('1') - (Decimal('1') + taxa_mensal) ** (-prazo_meses)) / taxa_mensal
            valor_max = capacidade_mensal * fator
        else:
            valor_max = capacidade_mensal * prazo_meses
        
        # Limitar ao valor solicitado
        valor_aprovado = min(valor_max, self.solicitacao.valor_solicitado)
        
        # Aplicar limitações adicionais baseadas no score
        score = self.analise.score_total
        if score < 700:
            valor_aprovado *= Decimal('0.8')  # 80% do calculado
        elif score < 800:
            valor_aprovado *= Decimal('0.9')  # 90% do calculado
        
        return max(Decimal('10000'), valor_aprovado)  # Mínimo 10k AOA
    
    def _aprovar_credito(self, valor_aprovado, taxa_juros, risco):
        """Aprova o crédito"""
        self.solicitacao.status = 'APROVADO'
        self.solicitacao.valor_aprovado = valor_aprovado
        self.solicitacao.taxa_juros_anual = taxa_juros
        self.solicitacao.data_aprovacao = timezone.now()
        self.solicitacao.observacoes_analise = f"Aprovado automaticamente. Risco: {risco}. Score: {self.analise.score_total}"
        self.solicitacao.save()
        
        return {
            'aprovado': True,
            'valor_aprovado': valor_aprovado,
            'taxa_juros': taxa_juros,
            'risco': risco,
            'score': self.analise.score_total,
            'parcela_estimada': self.solicitacao.valor_parcela_estimada
        }
    
    def _rejeitar_credito(self, motivo):
        """Rejeita o crédito"""
        self.solicitacao.status = 'REJEITADO'
        self.solicitacao.motivo_rejeicao = motivo
        self.solicitacao.data_analise = timezone.now()
        self.solicitacao.save()
        
        return {
            'aprovado': False,
            'motivo': motivo,
            'score': self.analise.score_total if self.analise else 0
        }


def processar_solicitacao_credito(solicitacao_id):
    """Função utilitária para processar uma solicitação de crédito"""
    try:
        solicitacao = SolicitacaoCredito.objects.get(id=solicitacao_id)
        
        if solicitacao.status != 'PENDENTE':
            return {'erro': 'Solicitação já foi processada'}
        
        # Marcar como em análise
        solicitacao.status = 'ANALISE'
        solicitacao.save()
        
        # Executar análise
        analyzer = CreditAnalyzer(solicitacao)
        resultado = analyzer.analisar_credito()
        
        return resultado
        
    except SolicitacaoCredito.DoesNotExist:
        return {'erro': 'Solicitação não encontrada'}
    except Exception as e:
        return {'erro': f'Erro na análise: {str(e)}'}


def recalcular_score_cliente(cliente_id):
    """Recalcula o score de crédito de um cliente"""
    try:
        cliente = Cliente.objects.get(id=cliente_id)
        
        # Pegar a última análise do cliente
        ultima_analise = AnaliseCredito.objects.filter(
            solicitacao__cliente=cliente
        ).order_by('-data_analise').first()
        
        if ultima_analise:
            cliente.score_credito = ultima_analise.score_total
            cliente.save()
            
        return cliente.score_credito
        
    except Cliente.DoesNotExist:
        return 0
