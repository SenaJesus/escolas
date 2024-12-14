from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from datetime import timedelta

class Estado(models.Model):
    nome = models.CharField(max_length=30, unique=True) # NO_UF
    sigla = models.CharField(max_length=2, unique=True) # SG_UF
    regiao = models.CharField(max_length=30) # NO_REGIAO

    def __str__(self): 
        return f"({self.sigla}): {self.nome} - {self.regiao}"

class Cidade(models.Model):
    nome = models.CharField(max_length=100) # NO_MUNICIPIO
    estado = models.ForeignKey(Estado, on_delete=models.CASCADE, related_name='cidades')

    def __str__(self): 
        return f"{self.nome} - {self.estado.sigla}"

class Escola(models.Model):
    class TipoDependencia(models.IntegerChoices):
        FEDERAL = 1, 'Federal'
        ESTADUAL = 2, 'Estadual'
        MUNICIPAL = 3, 'Municipal'
        PRIVADA = 4, 'Privada'
    
    class CategoriaEscolaPrivada(models.IntegerChoices):
        PARTICULAR = 1, 'Particular'
        COMUNITARIA = 2, 'Comunitária'
        CONFESSIONAL = 3, 'Confessional'
        FILANTROPICA = 4, 'Filantrópica'

    class Localizacao(models.IntegerChoices):
        URBANA = 1, 'Urbana'
        RURAL = 2, 'Rural'

    nome = models.CharField(max_length=255) # NO_ENTIDADE
    codigo_ibge = models.CharField(max_length=10) # CO_ENTIDADE
    tipo_dependencia = models.IntegerField(choices=TipoDependencia.choices) # TP_DEPENDENCIA
    categoria_escola_privada = models.IntegerField(choices=CategoriaEscolaPrivada.choices, blank=True, null=True) # TP_CATEGORIA_ESCOLA_PRIVADA
    localizacao = models.IntegerField(choices=Localizacao.choices) # TP_LOCALIZACAO
    cidade = models.ForeignKey(Cidade, on_delete=models.PROTECT) 
    endereco = models.CharField(max_length=255) # DS_ENDERECO
    numero = models.CharField(max_length=10, blank=True, null=True) # NU_ENDERECO
    complemento = models.CharField(max_length=255, blank=True, null=True) # DS_COMPLEMENTO
    bairro = models.CharField(max_length=100, blank=True, null=True) # NO_BAIRRO
    cep = models.CharField(max_length=8) # CO_CEP
    ddd = models.CharField(max_length=2, blank=True, null=True) # NU_DDD
    telefone = models.CharField(max_length=10, blank=True, null=True) # NU_TELEFONE
    inicio_ano_letivo = models.DateField(blank=True, null=True) # DT_ANO_LETIVO_INICIO
    fim_ano_letivo = models.DateField(blank=True, null=True) # DT_ANO_LETIVO_TERMINO
    
    def clean(self):
        if self.tipo_dependencia != self.TipoDependencia.PRIVADA and self.categoria_escola_privada is not None:
            raise ValidationError("Categoria de escola privada só é aplicável para escolas do tipo 'Privada'.")
        if self.tipo_dependencia == self.TipoDependencia.PRIVADA and self.categoria_escola_privada is None:
            raise ValidationError("Escolas do tipo 'Privada' devem ter uma categoria de escola privada.")

class CensoEscolar(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='censos')
    ano = models.IntegerField() #NU_ANO_CENSO
    class Meta: 
        constraints = [
            models.UniqueConstraint(fields=['escola', 'ano'], name='unique_escola_ano')
        ]

class Acessibilidade(models.Model):
    corrimao = models.BooleanField() # IN_ACESSIBILIDADE_CORRIMAO
    elevador = models.BooleanField() # IN_ACESSIBILIDADE_ELEVADOR
    pisos_tateis = models.BooleanField() # IN_ACESSIBILIDADE_PISOS_TATEIS
    vao_livre = models.BooleanField() # IN_ACESSIBILIDADE_VAO_LIVRE
    rampas = models.BooleanField() # IN_ACESSIBILIDADE_RAMPAS
    sinal_sonoro = models.BooleanField() # IN_ACESSIBILIDADE_SINAL_SONORO
    sinal_tatil = models.BooleanField() # IN_ACESSIBILIDADE_SINAL_TATIL
    sinal_visual = models.BooleanField() # IN_ACESSIBILIDADE_SINAL_VISUAL

class Internet(models.Model):
    internet_aluno = models.BooleanField() # IN_INTERNET_ALUNOS
    internet_administrativo = models.BooleanField() # IN_INTERNET_ADMINISTRATIVO
    internet_aprendizagem = models.BooleanField() # IN_INTERNET_APRENDIZAGEM
    internet_comunidade = models.BooleanField() # IN_INTERNET_COMUNIDADE
    internet_computador_aluno = models.BooleanField() # IN_ACESSO_INTERNET_COMPUTADOR
    internet_computador_pessoal_aluno = models.BooleanField() # IN_ACES_INTERNET_DISP_PESSOAIS

class Funcionarios(models.Model):
    administrativos_quantidade = models.IntegerField(default=0) #QT_PROF_ADMINISTRATIVOS
    servico_geral_quantidade = models.IntegerField(default=0) #QT_PROF_SERVICOS_GERAIS
    bibliotecario_quantidade = models.IntegerField(default=0) #QT_PROF_BIBLIOTECARIO
    saude_quantidade = models.IntegerField(default=0) #QT_PROF_SAUDE
    coordenador_quantidade = models.IntegerField(default=0) #QT_PROF_COORDENADOR
    fonoaudiologo_quantidade = models.IntegerField(default=0) #QT_PROF_FONOAUDIOLOGO
    nutricionista_quantidade = models.IntegerField(default=0) #QT_PROF_NUTRICIONISTA
    psicologo_quantidade = models.IntegerField(default=0) #QT_PROF_PSICOLOGO
    alimentacao_quantidade = models.IntegerField(default=0) #QT_PROF_ALIMENTACAO
    pedagogia_quantidade  = models.IntegerField(default=0) #QT_PROF_PEDAGOGIA
    secretario_quantidade  = models.IntegerField(default=0) #QT_PROF_SECRETARIO
    seguranca_quantidade  = models.IntegerField(default=0) #QT_PROF_SEGURANCA
    monitores_quantidade  = models.IntegerField(default=0) #QT_PROF_MONITORES
    gestao_quantidade  = models.IntegerField(default=0) #QT_PROF_GESTAO
    assistente_social_quantidade  = models.IntegerField(default=0) #QT_PROF_ASSIST_SOCIAL

class Infraestrutura(models.Model):
    censo = models.OneToOneField(CensoEscolar, on_delete=models.CASCADE, related_name='infraestrutura')
    agua_potavel = models.BooleanField() # IN_AGUA_POTAVEL
    almoxarifado = models.BooleanField() # IN_ALMOXARIFADO
    area_verde = models.BooleanField() # IN_AREA_VERDE
    auditorio = models.BooleanField() # IN_AUDITORIO
    banheiro = models.BooleanField() # IN_BANHEIRO
    banheiro_infantil = models.BooleanField() # IN_BANHEIRO_EI
    banheiro_pne = models.BooleanField() # IN_BANHEIRO_PNE
    banheiro_funcionarios = models.BooleanField() # IN_BANHEIRO_FUNCIONARIOS
    banheiro_chuveiro = models.BooleanField() # IN_BANHEIRO_CHUVEIRO
    biblioteca = models.BooleanField() # IN_BIBLIOTECA
    cozinha = models.BooleanField() # IN_COZINHA
    dormitorio_aluno = models.BooleanField() # IN_DORMITORIO_ALUNO
    dormitorio_professor = models.BooleanField() # IN_DORMITORIO_PROFESSOR
    lab_ciencias = models.BooleanField() # IN_LABORATORIO_CIENCIAS
    lab_informatica = models.BooleanField() # IN_LABORATORIO_INFORMATICA
    patio_coberto = models.BooleanField() # IN_PATIO_COBERTO
    patio_descoberto = models.BooleanField() # IN_PATIO_DESCOBERTO
    parque_infantil = models.BooleanField() # IN_PARQUE_INFANTIL
    piscina = models.BooleanField() # IN_PISCINA
    quadra_esportes_coberta = models.BooleanField() # IN_QUADRA_ESPORTES_COBERTA
    quadra_esportes_descoberta = models.BooleanField() # IN_QUADRA_ESPORTES_DESCOBERTA
    sala_artes = models.BooleanField() # IN_SALA_ATELIE_ARTES
    sala_musica = models.BooleanField() # IN_SALA_MUSICA_CORAL
    sala_danca = models.BooleanField() # IN_SALA_ESTUDIO_DANCA
    sala_recreativa = models.BooleanField() # IN_SALA_MULTIUSO
    sala_diretoria = models.BooleanField() # IN_SALA_DIRETORIA
    sala_leitura = models.BooleanField() # IN_SALA_LEITURA
    sala_professor = models.BooleanField() # IN_SALA_PROFESSOR
    sala_repouso_aluno = models.BooleanField() # IN_SALA_REPOUSO_ALUNO
    sala_secretaria = models.BooleanField() # IN_SECRETARIA
    sala_atendimento_especial = models.BooleanField() # IN_SALA_ATENDIMENTO_ESPECIAL
    terreirao_recreativo = models.BooleanField() # IN_TERREIRAO
    acessibilidade = models.OneToOneField(Acessibilidade, on_delete=models.CASCADE)
    salas_quantidade = models.IntegerField(default=0) # QT_SALAS_UTILIZADAS
    salas_quantidade_fora = models.IntegerField(default=0) # QT_SALAS_UTILIZADAS_FORA
    salas_quantidade_dentro = models.IntegerField(default=0) # QT_SALAS_UTILIZADAS_DENTRO
    salas_climatizadas = models.IntegerField(default=0) # QT_SALAS_UTILIZA_CLIMATIZADAS
    salas_acessibilidade = models.IntegerField(default=0) # QT_SALAS_UTILIZADAS_ACESSIVEIS
    dvd_quantidade = models.IntegerField(default=0) # QT_EQUIP_DVD
    som_quantidade = models.IntegerField(default=0) # QT_EQUIP_SOM
    tv_quantidade = models.IntegerField(default=0) # QT_EQUIP_TV
    lousa_digital_quantidade = models.IntegerField(default=0) # QT_EQUIP_LOUSA_DIGITAL
    projetor_quantidade = models.IntegerField(default=0) # QT_EQUIP_MULTIMIDIA
    computador_quantidade = models.IntegerField(default=0) # QT_DESKTOP_ALUNO
    notebook_quantidade = models.IntegerField(default=0) # QT_COMP_PORTATIL_ALUNO
    tablet_quantidade = models.IntegerField(default=0) # QT_TABLET_ALUNO
    internet_aluno = models.OneToOneField(Internet, on_delete=models.CASCADE)
    funcionarios = models.OneToOneField(Funcionarios, on_delete=models.CASCADE) 
    alimentacao = models.BooleanField() #IN_ALIMENTACAO
    rede_social = models.BooleanField() #IN_REDES_SOCIAIS

class Cotas(models.Model):
    ppi = models.BooleanField() #N_RESERVA_PPI
    renda = models.BooleanField() #IN_RESERVA_RENDA
    escola_publica = models.BooleanField() #IN_RESERVA_PUBLICA
    pcd = models.BooleanField() #IN_RESERVA_PCD
    outros = models.BooleanField() #IN_RESERVA_OUTROS

class Educacao(models.Model):
    censo = models.OneToOneField(CensoEscolar, on_delete=models.CASCADE, related_name='educacao')
    educacao_indigena = models.BooleanField() #IN_EDUCACAO_INDIGENA
    exame_selecao = models.BooleanField(blank=True, null=True) #IN_EXAME_SELECAO
    cotas = models.OneToOneField(Cotas, on_delete=models.CASCADE)
    gremio = models.BooleanField() #IN_ORGAO_GREMIO_ESTUDANTIL
    ead = models.BooleanField() #IN_EAD

    ed_inf_matricula_quantidade = models.IntegerField(default=0) # QT_MAT_INF
    ed_inf_docentes_quantidade = models.IntegerField(default=0) # QT_DOC_INF

    ed_inf_creche_matricula_quantidade = models.IntegerField(default=0) # QT_MAT_INF_CRE
    ed_inf_creche_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_INF_CRE
    
    ed_inf_pre_escola_matricula_quantidade = models.IntegerField(default=0) # QT_MAT_INF_PRE
    ed_inf_pre_escola_docentes_quantidade = models.IntegerField(default=0) # QT_DOC_INF_PRE

    ed_fund_matricula_quantidade = models.IntegerField(default=0) # QT_MAT_FUND
    ed_fund_docentes_quantidade = models.IntegerField(default=0) # QT_DOC_FUND
    
    ed_fund_anos_iniciais_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_FUND_AI
    ed_fund_anos_iniciais_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_FUND_AI
    
    ed_fund_anos_finais_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_FUND_AF
    ed_fund_anos_finais_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_FUND_AF

    medio_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_MED
    medio_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_MED

    medio_tecnico_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_MED_CT
    medio_tecnico_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_MED_CT

    ed_profissional_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_PROF
    ed_profissional_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_PROF
    
    ed_tecnica_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_PROF_TEC
    ed_tecnica_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_PROF_TEC

    eja_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_EJA
    eja_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_EJA

    eja_fund_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_EJA_FUND
    eja_fund_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_EJA_FUND

    eja_fund_inicial_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_EJA_FUND_AI
    eja_fund_inicial_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_EJA_FUND_AI

    eja_fund_final_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_EJA_FUND_AF
    eja_fund_final_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_EJA_FUND_AF

    eja_medio_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_EJA_MED
    eja_medio_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_EJA_MED

    ed_especial_matricula_quantidade = models.IntegerField(default=0) #QT_MAT_ESP
    ed_especial_docentes_quantidade = models.IntegerField(default=0) #QT_DOC_ESP

class Avaliacao(models.Model):
    escola = models.ForeignKey(Escola, on_delete=models.PROTECT, related_name='avaliacoes')
    email = models.EmailField()
    nota = models.IntegerField()
    comentario = models.TextField(blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

class Autorizacao(models.Model):
    email = models.EmailField()
    codigo = models.CharField(max_length=6)
    data_criacao = models.DateTimeField(auto_now_add=True)
    valido = models.BooleanField(default=True)
    def validar_expiracao(self): return timezone.now() > self.data_criacao + timedelta(minutes=30)