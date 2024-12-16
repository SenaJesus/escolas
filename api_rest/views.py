from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import get_object_or_404
from django.db.models import Q, Avg

from .models import Escola, Estado, Cidade, Avaliacao, Autorizacao
from .serializers import (
    EscolaSerializer, EscolaListSerializer, EstadoSerializer, CidadeSerializer
)
from .services import (
    enviar_email_confirmacao,
    criar_ou_atualizar_autorizacao,
    verificar_autorizacao,
    enviar_email_confirmacao_avaliacao,
    gerar_token_para_email
)
from .jwt_utils import verificar_jwt
from .pagination import StandardResultsSetPagination

@api_view(['GET'])
def get_escola(_, id):
    """
    Endpoint para obter os detalhes de uma escola específica, incluindo todas as avaliações.
    """
    try:
        escola = Escola.objects.prefetch_related(
            'censos__infraestrutura__acessibilidade',
            'censos__infraestrutura__internet_aluno',
            'censos__infraestrutura__funcionarios',
            'censos__educacao__cotas',
            'cidade__estado',
            'avaliacoes'
        ).get(pk=id)
    except Escola.DoesNotExist:
        return Response({'error': 'Escola não encontrada!'}, status=status.HTTP_404_NOT_FOUND)

    escola_serializer = EscolaSerializer(escola)
    return Response(escola_serializer.data)

@api_view(['POST'])
def solicitar_autorizacao(request):
    """
    Endpoint para solicitar um código de confirmação via email.
    """
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email é obrigatório.'}, status=status.HTTP_400_BAD_REQUEST)
    
    codigo = criar_ou_atualizar_autorizacao(email)
    enviar_email_confirmacao(email, codigo)
    return Response({'message': 'Código de confirmação enviado para o email.'}, status=status.HTTP_200_OK)

@api_view(['POST'])
def confirmar_autorizacao(request):
    """
    Endpoint para confirmar o código de autorização enviado por email.
    Retorna um token JWT válido se a confirmação for bem-sucedida.
    """
    email = request.data.get('email')
    codigo = request.data.get('codigo')
    
    if not email or not codigo:
        return Response({'error': 'Email e código são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)
    
    is_valid = verificar_autorizacao(email, codigo)
    if is_valid:
        token = gerar_token_para_email(email)
        Autorizacao.objects.filter(email=email, valido=True).update(valido=False)
        return Response({'message': 'Email confirmado com sucesso.', 'token': token}, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Código inválido ou expirado.'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def submeter_avaliacao(request, escola_id):
    """
    Endpoint para submeter uma avaliação para uma escola específica.
    Requer o header 'Authorization: Bearer <token>'.
    """

    email = request.data.get('email')
    nota = request.data.get('nota')
    comentario = request.data.get('comentario', '')

    if not all([email, nota]):
        return Response({'error': 'Email e nota são obrigatórios.'}, status=status.HTTP_400_BAD_REQUEST)

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return Response({'error': 'Token de autorização não fornecido.'}, status=status.HTTP_401_UNAUTHORIZED)

    token = auth_header.split(' ')[1]
    payload = verificar_jwt(token)
    if payload is None:
        return Response({'error': 'Token inválido ou expirado. É necessário confirmar o email novamente.'}, status=status.HTTP_401_UNAUTHORIZED)

    if payload.get('email') != email:
        return Response({'error': 'O token fornecido não corresponde ao email informado.'}, status=status.HTTP_403_FORBIDDEN)

    seis_meses_atras = timezone.now() - timedelta(days=180)
    avaliacao_existente = Avaliacao.objects.filter(
        email=email,
        escola_id=escola_id,
        data_criacao__gte=seis_meses_atras
    ).exists()

    if avaliacao_existente:
        return Response({'error': 'Você já avaliou esta escola nos últimos 6 meses.'}, status=status.HTTP_400_BAD_REQUEST)

    escola = get_object_or_404(Escola, id=escola_id)

    Avaliacao.objects.create(
        escola=escola,
        email=email,
        nota=nota,
        comentario=comentario
    )

    enviar_email_confirmacao_avaliacao(email, escola)
    return Response({'message': 'Avaliação adicionada com sucesso.'}, status=status.HTTP_200_OK)

@api_view(['GET'])
def listar_escolas_com_filtros(request):
    """
    Lista as escolas com filtros opcionais por Estado, Cidade, Nome e Bairro.
    Implementa paginação.
    Retorna apenas nome da escola, endereço, cidade e estado, e a média das avaliações.
    """
    estado = request.GET.get('estado')
    cidade = request.GET.get('cidade')
    nome = request.GET.get('nome')
    bairro = request.GET.get('bairro')

    escolas = Escola.objects.all().prefetch_related(
        'censos__infraestrutura__acessibilidade',
        'censos__infraestrutura__internet_aluno',
        'censos__infraestrutura__funcionarios',
        'censos__educacao__cotas',
        'cidade__estado'
    ).annotate(average_avaliacoes=Avg('avaliacoes__nota'))
    
    if estado:
        escolas = escolas.filter(
            Q(cidade__estado__nome__iexact=estado) |
            Q(cidade__estado__sigla__iexact=estado)
        )
    
    if cidade:
        escolas = escolas.filter(cidade__nome__icontains=cidade)
    
    if nome:
        escolas = escolas.filter(nome__icontains=nome)
    
    if bairro:
        escolas = escolas.filter(bairro__icontains=bairro)
    
    paginator = StandardResultsSetPagination()
    resultado_paginado = paginator.paginate_queryset(escolas, request)
    
    serializer = EscolaListSerializer(resultado_paginado, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
def listar_todas_escolas(request):
    """
    Lista todas as escolas com paginação, ordenadas alfabeticamente pelo estado.
    Retorna apenas nome da escola, endereço, cidade e estado, e a média das avaliações.
    """
    escolas = Escola.objects.all().prefetch_related(
        'censos__infraestrutura__acessibilidade',
        'censos__infraestrutura__internet_aluno',
        'censos__infraestrutura__funcionarios',
        'censos__educacao__cotas',
        'cidade__estado'
    ).annotate(average_avaliacoes=Avg('avaliacoes__nota')) \
     .order_by('cidade__estado__nome')
    
    paginator = StandardResultsSetPagination()
    resultado_paginado = paginator.paginate_queryset(escolas, request)
    
    serializer = EscolaListSerializer(resultado_paginado, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
def listar_estados(_):
    """
    Retorna a lista de todos os estados.
    """
    estados = Estado.objects.all()
    serializer = EstadoSerializer(estados, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def listar_cidades(_):
    """
    Retorna a lista de todas as cidades.
    """
    cidades = Cidade.objects.all()
    serializer = CidadeSerializer(cidades, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)