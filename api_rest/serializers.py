from rest_framework import serializers
from .models import (
    Escola, CensoEscolar, Infraestrutura, Educacao,
    Acessibilidade, Internet, Funcionarios, Cotas,
    Cidade, Estado, Avaliacao
)

class EstadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Estado
        fields = ['id', 'nome', 'sigla', 'regiao']

class CidadeSerializer(serializers.ModelSerializer):
    estado = EstadoSerializer()
    
    class Meta:
        model = Cidade
        fields = ['id', 'nome', 'estado']

class CotasSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cotas
        fields = '__all__'

class EducacaoSerializer(serializers.ModelSerializer):
    cotas = CotasSerializer(read_only=True)

    class Meta:
        model = Educacao
        fields = '__all__'

class AcessibilidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Acessibilidade
        fields = '__all__'

class InternetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Internet
        fields = '__all__'

class FuncionariosSerializer(serializers.ModelSerializer):
    class Meta:
        model = Funcionarios
        fields = '__all__'

class InfraestruturaSerializer(serializers.ModelSerializer):
    acessibilidade = AcessibilidadeSerializer(read_only=True)
    internet_aluno = InternetSerializer(read_only=True)
    funcionarios = FuncionariosSerializer(read_only=True)

    class Meta:
        model = Infraestrutura
        fields = '__all__'

class CensoEscolarSerializer(serializers.ModelSerializer):
    infraestrutura = InfraestruturaSerializer(read_only=True)
    educacao = EducacaoSerializer(read_only=True)

    class Meta:
        model = CensoEscolar
        fields = '__all__'

class AvaliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avaliacao
        fields = ['id', 'email', 'nota', 'comentario', 'data_criacao']

class EscolaListSerializer(serializers.ModelSerializer):
    cidade = CidadeSerializer(read_only=True)
    average_avaliacoes = serializers.FloatField(read_only=True)

    class Meta:
        model = Escola
        fields = ['id', 'nome', 'bairro', 'cidade', 'average_avaliacoes']

class EscolaSerializer(serializers.ModelSerializer):
    censos = CensoEscolarSerializer(many=True, read_only=True)
    cidade = CidadeSerializer(read_only=True)
    avaliacoes = AvaliacaoSerializer(many=True, read_only=True)

    class Meta:
        model = Escola
        fields = '__all__'