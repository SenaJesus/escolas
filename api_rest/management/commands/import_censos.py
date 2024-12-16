import os
import pandas as pd
import warnings
from warnings import simplefilter
simplefilter(action='ignore', category=FutureWarning)

from django.core.management.base import BaseCommand
from api_rest.models import (
    Estado, Cidade, Escola, CensoEscolar,
    Acessibilidade, Internet, Funcionarios,
    Infraestrutura, Cotas, Educacao
)
from django.conf import settings
from pandas.errors import PerformanceWarning
from tqdm import tqdm

warnings.simplefilter(action='ignore', category=PerformanceWarning)


def chunked_queryset_fetch(model, field_name, values, chunk_size=500):
    result = []
    values_list = list(values)
    for i in range(0, len(values_list), chunk_size):
        chunk = values_list[i:i+chunk_size]
        qs = model.objects.filter(**{f"{field_name}__in": chunk})
        result.extend(qs)
    return result

def chunked_censos_fetch(escola_ids, ano, chunk_size=500):
    result = []
    escola_ids_list = list(escola_ids)
    for i in range(0, len(escola_ids_list), chunk_size):
        chunk = escola_ids_list[i:i+chunk_size]
        qs = CensoEscolar.objects.filter(escola_id__in=chunk, ano=ano)
        result.extend(qs)
    return result

class Command(BaseCommand):
    help = 'Importa dados dos censos escolares para o banco de dados a partir de arquivos CSV'

    def handle(self, *args, **options):
        self.stdout.write("Apagando dados existentes...")
        Infraestrutura.objects.all().delete()
        Acessibilidade.objects.all().delete()
        Internet.objects.all().delete()
        Funcionarios.objects.all().delete()
        Cotas.objects.all().delete()
        Educacao.objects.all().delete()
        CensoEscolar.objects.all().delete()

        self.stdout.write(self.style.WARNING("Dados antigos apagados com sucesso."))

        self.stdout.write("Iniciando nova importação de censos...")

        censos_path = os.path.join(settings.BASE_DIR, 'censos')
        
        if not os.path.exists(censos_path):
            self.stderr.write(self.style.ERROR(f'Diretório "censos" não encontrado em {censos_path}.'))
            return

        censo_files = [f for f in os.listdir(censos_path) if f.startswith('censo_') and f.endswith('.csv')]

        if not censo_files:
            self.stdout.write(self.style.WARNING('Nenhum arquivo de censo encontrado na pasta "censos/".'))
            return

        self.stdout.write("Carregando Estados, Cidades e Escolas existentes...")

        estados_existentes = Estado.objects.all()
        estado_cache = {estado.sigla: estado for estado in estados_existentes}

        cidades_existentes = Cidade.objects.select_related('estado').all()
        cidade_cache = {(cidade.nome, cidade.estado.sigla): cidade for cidade in cidades_existentes}

        escolas_existentes = Escola.objects.all()
        escola_cache = {str(escola.codigo_ibge).strip(): escola for escola in escolas_existentes}

        for censo_file in censo_files:
            self.stdout.write(f'Importando {censo_file}...')
            file_path = os.path.join(censos_path, censo_file)
            ano_censo = self.extract_year_from_filename(censo_file)
            if not ano_censo:
                self.stderr.write(f'Não foi possível extrair o ano do arquivo {censo_file}. Pulando esse arquivo...')
                continue

            try:
                df = pd.read_csv(
                    file_path,
                    encoding='latin1',
                    delimiter=';',
                    decimal=',',
                    low_memory=False,
                    na_filter=False,    
                    keep_default_na=False,
                    converters={'NU_TELEFONE': lambda x: str(int(float(x))) if x.strip() and x.strip() != '.' else ''},
                    dtype={
                        'TP_SITUACAO_FUNCIONAMENTO': 'str',
                        'TP_DEPENDENCIA': 'Int64',
                        'TP_CATEGORIA_ESCOLA_PRIVADA': 'Int64'
                    }
                )
            except Exception as e:
                self.stderr.write(f'Erro ao ler {censo_file}: {e}')
                continue

            df['NU_TELEFONE'] = df['NU_TELEFONE'].astype(str)

            df = self.limpar_dados(df)
            total_rows = len(df)
            self.stdout.write(f"Total de linhas após limpeza: {total_rows}")

            dados_estados = []
            dados_cidades = []
            dados_escolas = []
            dados_censos = []

            def str_or_none(val):
                if pd.isna(val) or val == '' or val == 'nan':
                    return None
                return str(val)

            for index, row in tqdm(df.iterrows(), total=total_rows, desc=f'Importando {censo_file}', unit='linhas'):
                estado_sigla = str(row.get('SG_UF', '')).strip()
                estado_nome = str(row.get('NO_UF', '')).strip()
                estado_regiao = row.get('NO_REGIAO', 'Desconhecida')
                ddd = str_or_none(row.get('NU_DDD', ''))
                telefone = str_or_none(row.get('NU_TELEFONE', ''))

                if estado_sigla and estado_sigla not in estado_cache:
                    dados_estados.append((estado_sigla, estado_nome, estado_regiao))

                cidade_nome = str(row.get('NO_MUNICIPIO', '')).strip()
                if cidade_nome and estado_sigla and (cidade_nome, estado_sigla) not in cidade_cache:
                    dados_cidades.append((cidade_nome, estado_sigla))

                escola_codigo_ibge = str(row.get('CO_ENTIDADE', '')).strip()
                if not escola_codigo_ibge or escola_codigo_ibge.lower() == 'nan':
                    continue

                val_tp_cat_priv = row.get('TP_CATEGORIA_ESCOLA_PRIVADA', '')
                if pd.isna(val_tp_cat_priv):
                    categoria_escola_privada = None
                else:
                    cat_str = str(val_tp_cat_priv).strip()
                    if cat_str == '' or cat_str.lower() == 'nan':
                        categoria_escola_privada = None
                    else:
                        categoria_escola_privada = int(cat_str)

                inicio_ano_letivo = row.get('DT_ANO_LETIVO_INICIO')
                fim_ano_letivo = row.get('DT_ANO_LETIVO_TERMINO')
                if inicio_ano_letivo == '' or inicio_ano_letivo == 'nan':
                    inicio_ano_letivo = None
                if fim_ano_letivo == '' or fim_ano_letivo == 'nan':
                    fim_ano_letivo = None

                def str_or_empty(val):
                    if pd.isna(val):
                        return ''
                    return str(val)

                endereco = str_or_empty(row.get('DS_ENDERECO', ''))
                numero = str_or_empty(row.get('NU_ENDERECO', ''))
                complemento = str_or_empty(row.get('DS_COMPLEMENTO', ''))
                bairro = str_or_empty(row.get('NO_BAIRRO', ''))
                cep = str_or_empty(row.get('CO_CEP', ''))
                ddd = str_or_none(row.get('NU_DDD', ''))
                telefone = str_or_none(row.get('NU_TELEFONE', ''))

                nome_entidade = str_or_empty(row.get('NO_ENTIDADE', 'Sem Nome')) or 'Sem Nome'
                tipo_dep = row.get('TP_DEPENDENCIA', 1)
                if pd.isna(tipo_dep):
                    tipo_dep = 1
                else:
                    tipo_dep = int(tipo_dep)

                loc = row.get('TP_LOCALIZACAO', 1)
                if pd.isna(loc):
                    loc = 1
                else:
                    loc = int(loc)

                dados_escolas.append({
                    'codigo_ibge': escola_codigo_ibge,
                    'nome': nome_entidade,
                    'tipo_dependencia': tipo_dep,
                    'categoria_escola_privada': categoria_escola_privada,
                    'localizacao': loc,
                    'cidade_nome': cidade_nome,
                    'estado_sigla': estado_sigla,
                    'endereco': endereco,
                    'numero': numero,
                    'complemento': complemento,
                    'bairro': bairro,
                    'cep': cep,
                    'ddd': ddd,
                    'telefone': telefone,
                    'inicio_ano_letivo': inicio_ano_letivo,
                    'fim_ano_letivo': fim_ano_letivo,
                })

                dados_censos.append((escola_codigo_ibge, ano_censo, row))

            dados_estados = list(set(dados_estados))
            dados_cidades = list(set(dados_cidades))

            novos_estados = []
            for (estado_sigla, estado_nome, estado_regiao) in dados_estados:
                if estado_sigla not in estado_cache:
                    est = Estado(sigla=estado_sigla, nome=estado_nome, regiao=estado_regiao)
                    novos_estados.append(est)

            if novos_estados:
                self.stdout.write("Criando novos estados...")
                Estado.objects.bulk_create(novos_estados, ignore_conflicts=True)
                self.stdout.write("Buscando novos estados do banco...")
                siglas_estados = [e.sigla for e in novos_estados]
                est_db = chunked_queryset_fetch(Estado, 'sigla', siglas_estados, 500)
                for est in est_db:
                    estado_cache[est.sigla] = est
                self.stdout.write(f'{len(novos_estados)} novos estados adicionados.')

            novos_cids = []
            for (cidade_nome, estado_sigla) in dados_cidades:
                if (cidade_nome, estado_sigla) not in cidade_cache:
                    estado = estado_cache.get(estado_sigla)
                    if not estado:
                        continue
                    cid = Cidade(nome=cidade_nome, estado=estado)
                    novos_cids.append(cid)

            if novos_cids:
                self.stdout.write("Criando novas cidades...")
                Cidade.objects.bulk_create(novos_cids, ignore_conflicts=True)
                self.stdout.write("Buscando novas cidades do banco...")
                nomes_cidades = [c.nome for c in novos_cids]
                cids_db = chunked_queryset_fetch(Cidade, 'nome', nomes_cidades, 500)
                for cid in cids_db:
                    cidade_cache[(cid.nome, cid.estado.sigla)] = cid
                self.stdout.write(f'{len(novos_cids)} novas cidades adicionadas.')

            novos_escolas = []
            codigos_escolas_novas = []
            escolas_para_atualizar = []
            
            self.stdout.write("Verificando escolas existentes/novas...")
            for esc_data in dados_escolas:
                codigo_ibge = esc_data['codigo_ibge']
                cid = cidade_cache.get((esc_data['cidade_nome'], esc_data['estado_sigla']))

                if not cid:
                    continue

                i_ano = esc_data['inicio_ano_letivo']
                if i_ano == '' or i_ano == 'nan':
                    i_ano = None
                f_ano = esc_data['fim_ano_letivo']
                if f_ano == '' or f_ano == 'nan':
                    f_ano = None

                if codigo_ibge not in escola_cache:
                    esc = Escola(
                        codigo_ibge=codigo_ibge,
                        nome=esc_data['nome'],
                        tipo_dependencia=esc_data['tipo_dependencia'],
                        categoria_escola_privada=esc_data['categoria_escola_privada'],
                        localizacao=esc_data['localizacao'],
                        cidade=cid,
                        endereco=esc_data['endereco'],
                        numero=esc_data['numero'],
                        complemento=esc_data['complemento'],
                        bairro=esc_data['bairro'],
                        cep=esc_data['cep'],
                        ddd=esc_data['ddd'],
                        telefone=esc_data['telefone'],
                        inicio_ano_letivo=i_ano,
                        fim_ano_letivo=f_ano
                    )
                    novos_escolas.append(esc)
                    codigos_escolas_novas.append(codigo_ibge)
                else:
                    escola_existente = escola_cache[codigo_ibge]
                    anos_existentes = CensoEscolar.objects.filter(escola=escola_existente).values_list('ano', flat=True)
                    if anos_existentes:
                        max_ano = max(anos_existentes)
                    else:
                        max_ano = 0
                    if ano_censo > max_ano:
                        escolas_para_atualizar.append((escola_existente, esc_data, i_ano, f_ano, cid))

            if novos_escolas:
                self.stdout.write("Criando novas escolas...")
                Escola.objects.bulk_create(novos_escolas, ignore_conflicts=True)
                self.stdout.write("Buscando novas escolas do banco...")
                esc_db = chunked_queryset_fetch(Escola, 'codigo_ibge', codigos_escolas_novas, 500)
                for e_db in esc_db:
                    escola_cache[e_db.codigo_ibge] = e_db
                self.stdout.write(f'{len(novos_escolas)} novas escolas adicionadas.')

            if escolas_para_atualizar:
                self.stdout.write("Atualizando escolas com dados mais recentes (usando bulk_update)...")

                escola_ids = [e.pk for (e, _, _, _, _) in escolas_para_atualizar]
                escolas_dict = Escola.objects.in_bulk(escola_ids)

                for (escola_existente, esc_data, i_ano, f_ano, cid) in escolas_para_atualizar:
                    e = escolas_dict[escola_existente.pk]
                    e.nome = esc_data['nome']
                    e.tipo_dependencia = esc_data['tipo_dependencia']
                    e.categoria_escola_privada = esc_data['categoria_escola_privada']
                    e.localizacao = esc_data['localizacao']
                    e.cidade = cid
                    e.endereco = esc_data['endereco']
                    e.numero = esc_data['numero']
                    e.complemento = esc_data['complemento']
                    e.bairro = esc_data['bairro']
                    e.cep = esc_data['cep']
                    e.ddd = esc_data['ddd']
                    e.telefone = esc_data['telefone']
                    e.inicio_ano_letivo = i_ano
                    e.fim_ano_letivo = f_ano

                campos = [
                    'nome', 'tipo_dependencia', 'categoria_escola_privada', 'localizacao',
                    'cidade', 'endereco', 'numero', 'complemento', 'bairro', 'cep', 'ddd', 'telefone',
                    'inicio_ano_letivo', 'fim_ano_letivo'
                ]

                Escola.objects.bulk_update(list(escolas_dict.values()), campos)
                self.stdout.write(f"{len(escolas_para_atualizar)} escolas atualizadas com sucesso.")

                for e in escolas_dict.values():
                    escola_cache[e.codigo_ibge] = e

            self.stdout.write("Criando censos...")
            novos_censos = []
            censos_temp = []
            for (codigo_ibge, ano, row) in dados_censos:
                esc = escola_cache.get(codigo_ibge)
                if esc:
                    censo = CensoEscolar(escola=esc, ano=ano)
                    novos_censos.append(censo)
                    censos_temp.append((censo, row))

            if novos_censos:
                CensoEscolar.objects.bulk_create(novos_censos, ignore_conflicts=True)
                self.stdout.write(f'{len(novos_censos)} novos censos adicionados.')

            escola_ids = {c.escola_id for c in novos_censos}
            censos_db = chunked_censos_fetch(escola_ids, ano_censo, 500)
            censo_map = {(c.escola_id, c.ano): c for c in censos_db}

            self.stdout.write("Montando dados de Acessibilidade, Internet, Funcionarios, Cotas...")
            novos_acessibilidades = []
            novos_internets = []
            novos_funcionarios = []
            novos_cotas = []
            infra_rel = []
            edu_rel = []

            for censo, row in censos_temp:
                censo_db = censo_map.get((censo.escola_id, censo.ano))
                if not censo_db:
                    continue
                aces = Acessibilidade(
                    corrimao=row.get('IN_ACESSIBILIDADE_CORRIMAO', False),
                    elevador=row.get('IN_ACESSIBILIDADE_ELEVADOR', False),
                    pisos_tateis=row.get('IN_ACESSIBILIDADE_PISOS_TATEIS', False),
                    vao_livre=row.get('IN_ACESSIBILIDADE_VAO_LIVRE', False),
                    rampas=row.get('IN_ACESSIBILIDADE_RAMPAS', False),
                    sinal_sonoro=row.get('IN_ACESSIBILIDADE_SINAL_SONORO', False),
                    sinal_tatil=row.get('IN_ACESSIBILIDADE_SINAL_TATIL', False),
                    sinal_visual=row.get('IN_ACESSIBILIDADE_SINAL_VISUAL', False),
                )
                novos_acessibilidades.append(aces)

                inte = Internet(
                    internet_aluno=row.get('IN_INTERNET_ALUNOS', False),
                    internet_administrativo=row.get('IN_INTERNET_ADMINISTRATIVO', False),
                    internet_aprendizagem=row.get('IN_INTERNET_APRENDIZAGEM', False),
                    internet_comunidade=row.get('IN_INTERNET_COMUNIDADE', False),
                    internet_computador_aluno=row.get('IN_ACESSO_INTERNET_COMPUTADOR', False),
                    internet_computador_pessoal_aluno=row.get('IN_ACES_INTERNET_DISP_PESSOAIS', False),
                )
                novos_internets.append(inte)

                func = Funcionarios(
                    administrativos_quantidade=row.get('QT_PROF_ADMINISTRATIVOS', 0),
                    servico_geral_quantidade=row.get('QT_PROF_SERVICOS_GERAIS', 0),
                    bibliotecario_quantidade=row.get('QT_PROF_BIBLIOTECARIO', 0),
                    saude_quantidade=row.get('QT_PROF_SAUDE', 0),
                    coordenador_quantidade=row.get('QT_PROF_COORDENADOR', 0),
                    fonoaudiologo_quantidade=row.get('QT_PROF_FONOAUDIOLOGO', 0),
                    nutricionista_quantidade=row.get('QT_PROF_NUTRICIONISTA', 0),
                    psicologo_quantidade=row.get('QT_PROF_PSICOLOGO', 0),
                    alimentacao_quantidade=row.get('QT_PROF_ALIMENTACAO', 0),
                    pedagogia_quantidade=row.get('QT_PROF_PEDAGOGIA', 0),
                    secretario_quantidade=row.get('QT_PROF_SECRETARIO', 0),
                    seguranca_quantidade=row.get('QT_PROF_SEGURANCA', 0),
                    monitores_quantidade=row.get('QT_PROF_MONITORES', 0),
                    gestao_quantidade=row.get('QT_PROF_GESTAO', 0),
                    assistente_social_quantidade=row.get('QT_PROF_ASSIST_SOCIAL', 0),
                )
                novos_funcionarios.append(func)

                co = Cotas(
                    ppi=row.get('N_RESERVA_PPI', False),
                    renda=row.get('IN_RESERVA_RENDA', False),
                    escola_publica=row.get('IN_RESERVA_PUBLICA', False),
                    pcd=row.get('IN_RESERVA_PCD', False),
                    outros=row.get('IN_RESERVA_OUTROS', False),
                )
                novos_cotas.append(co)

                infra_rel.append((censo_db, row))
                edu_rel.append((censo_db, row))

            self.stdout.write("Criando registros de Acessibilidade, Internet, Funcionarios e Cotas...")
            if novos_acessibilidades:
                Acessibilidade.objects.bulk_create(novos_acessibilidades)
                self.stdout.write(f"Criado {len(novos_acessibilidades)} registros de Acessibilidade.")
            if novos_internets:
                Internet.objects.bulk_create(novos_internets)
                self.stdout.write(f"Criado {len(novos_internets)} registros de Internet.")
            if novos_funcionarios:
                Funcionarios.objects.bulk_create(novos_funcionarios)
                self.stdout.write(f"Criado {len(novos_funcionarios)} registros de Funcionarios.")
            if novos_cotas:
                Cotas.objects.bulk_create(novos_cotas)
                self.stdout.write(f"Criado {len(novos_cotas)} registros de Cotas.")

            def fetch_last_objects(model, count):
                objs = list(model.objects.all().order_by('-id')[:count])
                objs.reverse()
                return objs

            acess_db = fetch_last_objects(Acessibilidade, len(novos_acessibilidades)) if novos_acessibilidades else []
            inte_db = fetch_last_objects(Internet, len(novos_internets)) if novos_internets else []
            funcs_db = fetch_last_objects(Funcionarios, len(novos_funcionarios)) if novos_funcionarios else []
            cotas_db = fetch_last_objects(Cotas, len(novos_cotas)) if novos_cotas else []

            self.stdout.write("Criando Infraestrutura e Educacao...")
            novas_infraestruturas = []
            novas_educacoes = []
            for i, (censo_db, row) in enumerate(infra_rel):
                aces = acess_db[i]
                inte_obj = inte_db[i]
                func_obj = funcs_db[i]

                infra = Infraestrutura(
                    censo=censo_db,
                    agua_potavel=row.get('IN_AGUA_POTAVEL', False),
                    almoxarifado=row.get('IN_ALMOXARIFADO', False),
                    area_verde=row.get('IN_AREA_VERDE', False),
                    auditorio=row.get('IN_AUDITORIO', False),
                    banheiro=row.get('IN_BANHEIRO', False),
                    banheiro_infantil=row.get('IN_BANHEIRO_EI', False),
                    banheiro_pne=row.get('IN_BANHEIRO_PNE', False),
                    banheiro_funcionarios=row.get('IN_BANHEIRO_FUNCIONARIOS', False),
                    banheiro_chuveiro=row.get('IN_BANHEIRO_CHUVEIRO', False),
                    biblioteca=row.get('IN_BIBLIOTECA', False),
                    cozinha=row.get('IN_COZINHA', False),
                    dormitorio_aluno=row.get('IN_DORMITORIO_ALUNO', False),
                    dormitorio_professor=row.get('IN_DORMITORIO_PROFESSOR', False),
                    lab_ciencias=row.get('IN_LABORATORIO_CIENCIAS', False),
                    lab_informatica=row.get('IN_LABORATORIO_INFORMATICA', False),
                    patio_coberto=row.get('IN_PATIO_COBERTO', False),
                    patio_descoberto=row.get('IN_PATIO_DESCOBERTO', False),
                    parque_infantil=row.get('IN_PARQUE_INFANTIL', False),
                    piscina=row.get('IN_PISCINA', False),
                    quadra_esportes_coberta=row.get('IN_QUADRA_ESPORTES_COBERTA', False),
                    quadra_esportes_descoberta=row.get('IN_QUADRA_ESPORTES_DESCOBERTA', False),
                    sala_artes=row.get('IN_SALA_ATELIE_ARTES', False),
                    sala_musica=row.get('IN_SALA_MUSICA_CORAL', False),
                    sala_danca=row.get('IN_SALA_ESTUDIO_DANCA', False),
                    sala_recreativa=row.get('IN_SALA_MULTIUSO', False),
                    sala_diretoria=row.get('IN_SALA_DIRETORIA', False),
                    sala_leitura=row.get('IN_SALA_LEITURA', False),
                    sala_professor=row.get('IN_SALA_PROFESSOR', False),
                    sala_repouso_aluno=row.get('IN_SALA_REPOUSO_ALUNO', False),
                    sala_secretaria=row.get('IN_SECRETARIA', False),
                    sala_atendimento_especial=row.get('IN_SALA_ATENDIMENTO_ESPECIAL', False),
                    terreirao_recreativo=row.get('IN_TERREIRAO', False),
                    acessibilidade=aces,
                    salas_quantidade=row.get('QT_SALAS_UTILIZADAS', 0),
                    salas_quantidade_fora=row.get('QT_SALAS_UTILIZADAS_FORA', 0),
                    salas_quantidade_dentro=row.get('QT_SALAS_UTILIZADAS_DENTRO', 0),
                    salas_climatizadas=row.get('QT_SALAS_UTILIZA_CLIMATIZADAS', 0),
                    salas_acessibilidade=row.get('QT_SALAS_UTILIZADAS_ACESSIVEIS', 0),
                    dvd_quantidade=row.get('QT_EQUIP_DVD', 0),
                    som_quantidade=row.get('QT_EQUIP_SOM', 0),
                    tv_quantidade=row.get('QT_EQUIP_TV', 0),
                    lousa_digital_quantidade=row.get('QT_EQUIP_LOUSA_DIGITAL', 0),
                    projetor_quantidade=row.get('QT_EQUIP_MULTIMIDIA', 0),
                    computador_quantidade=row.get('QT_DESKTOP_ALUNO', 0),
                    notebook_quantidade=row.get('QT_COMP_PORTATIL_ALUNO', 0),
                    tablet_quantidade=row.get('QT_TABLET_ALUNO', 0),
                    internet_aluno=inte_obj,
                    funcionarios=func_obj,
                    alimentacao=row.get('IN_ALIMENTACAO', False),
                    rede_social=row.get('IN_REDES_SOCIAIS', False),
                )
                novas_infraestruturas.append(infra)

            for i, (censo_db, row) in enumerate(edu_rel):
                co = cotas_db[i]
                edu = Educacao(
                    censo=censo_db,
                    educacao_indigena=row.get('IN_EDUCACAO_INDIGENA', False),
                    exame_selecao=row.get('IN_EXAME_SELECAO', False),
                    cotas=co,
                    gremio=row.get('IN_ORGAO_GREMIO_ESTUDANTIL', False),
                    ead=row.get('IN_EAD', False),
                    ed_inf_matricula_quantidade=row.get('QT_MAT_INF', 0),
                    ed_inf_docentes_quantidade=row.get('QT_DOC_INF', 0),
                    ed_inf_creche_matricula_quantidade=row.get('QT_MAT_INF_CRE', 0),
                    ed_inf_creche_docentes_quantidade=row.get('QT_DOC_INF_CRE', 0),
                    ed_inf_pre_escola_matricula_quantidade=row.get('QT_MAT_INF_PRE', 0),
                    ed_inf_pre_escola_docentes_quantidade=row.get('QT_DOC_INF_PRE', 0),
                    ed_fund_matricula_quantidade=row.get('QT_MAT_FUND', 0),
                    ed_fund_docentes_quantidade=row.get('QT_DOC_FUND', 0),
                    ed_fund_anos_iniciais_matricula_quantidade=row.get('QT_MAT_FUND_AI', 0),
                    ed_fund_anos_iniciais_docentes_quantidade=row.get('QT_DOC_FUND_AI', 0),
                    ed_fund_anos_finais_matricula_quantidade=row.get('QT_MAT_FUND_AF', 0),
                    ed_fund_anos_finais_docentes_quantidade=row.get('QT_DOC_FUND_AF', 0),
                    medio_matricula_quantidade=row.get('QT_MAT_MED', 0),
                    medio_docentes_quantidade=row.get('QT_DOC_MED', 0),
                    medio_tecnico_matricula_quantidade=row.get('QT_MAT_MED_CT', 0),
                    medio_tecnico_docentes_quantidade=row.get('QT_DOC_MED_CT', 0),
                    ed_profissional_matricula_quantidade=row.get('QT_MAT_PROF', 0),
                    ed_profissional_docentes_quantidade=row.get('QT_DOC_PROF', 0),
                    ed_tecnica_matricula_quantidade=row.get('QT_MAT_PROF_TEC', 0),
                    ed_tecnica_docentes_quantidade=row.get('QT_DOC_PROF_TEC', 0),
                    eja_matricula_quantidade=row.get('QT_MAT_EJA', 0),
                    eja_docentes_quantidade=row.get('QT_DOC_EJA', 0),
                    eja_fund_matricula_quantidade=row.get('QT_MAT_EJA_FUND', 0),
                    eja_fund_docentes_quantidade=row.get('QT_DOC_EJA_FUND', 0),
                    eja_fund_inicial_matricula_quantidade=row.get('QT_MAT_EJA_FUND_AI', 0),
                    eja_fund_inicial_docentes_quantidade=row.get('QT_DOC_EJA_FUND_AI', 0),
                    eja_fund_final_matricula_quantidade=row.get('QT_MAT_EJA_FUND_AF', 0),
                    eja_fund_final_docentes_quantidade=row.get('QT_DOC_EJA_FUND_AF', 0),
                    eja_medio_matricula_quantidade=row.get('QT_MAT_EJA_MED', 0),
                    eja_medio_docentes_quantidade=row.get('QT_DOC_EJA_MED', 0),
                    ed_especial_matricula_quantidade=row.get('QT_MAT_ESP', 0),
                    ed_especial_docentes_quantidade=row.get('QT_DOC_ESP', 0),
                )
                novas_educacoes.append(edu)

            self.stdout.write("Inserindo Infraestrutura no banco...")
            if novas_infraestruturas:
                Infraestrutura.objects.bulk_create(novas_infraestruturas)
                self.stdout.write(f'{len(novas_infraestruturas)} novas infraestruturas adicionadas.')

            self.stdout.write("Inserindo Educacao no banco...")
            if novas_educacoes:
                Educacao.objects.bulk_create(novas_educacoes)
                self.stdout.write(f'{len(novas_educacoes)} novas educações adicionadas.')

        self.stdout.write(self.style.SUCCESS('Importação de censos concluída com sucesso!'))
        self.stdout.write(f"Total de escolas no banco: {Escola.objects.count()}")

    def extract_year_from_filename(self, filename):
        try:
            base = os.path.splitext(filename)[0]
            parts = base.split('_')
            if len(parts) >= 2:
                year = int(parts[1])
                return year
        except (ValueError, IndexError):
            self.stderr.write(f'Formato de arquivo inválido para extração do ano: {filename}')
            return None
        return None

    def limpar_dados(self, df):
        import locale
        df.replace(88888, '', inplace=True)
        df.replace('99999999999999', '', inplace=True)
        df.replace([-1, '9999'], '', inplace=True)

        for col in df.select_dtypes(['object']).columns:
            df[col] = df[col].astype(str).str.strip().replace('nan', '')

        date_format = '%d%b%y:%H:%M:%S'
        date_cols = ['DT_ANO_LETIVO_INICIO', 'DT_ANO_LETIVO_TERMINO']
        try:
            locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, 'C')

        for col in date_cols:
            if col not in df.columns:
                df[col] = ''
            else:
                parsed = pd.to_datetime(df[col], format=date_format, errors='coerce')
                df[col] = parsed.apply(lambda x: x.date().isoformat() if pd.notnull(x) else '')

        numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
        numeric_cols = numeric_cols.difference(['NU_TELEFONE', 'NU_DDD'])
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)

        campos_com_ponto_zero = ['NU_DDD', 'NU_TELEFONE']
        for c in campos_com_ponto_zero:
            if c in df.columns:
                df[c] = df[c].fillna('').astype(str).replace('nan', '')
                df[c] = df[c].str.replace(r'\.0$', '', regex=True)

        if 'TP_CATEGORIA_ESCOLA_PRIVADA' in df.columns:
            df['TP_CATEGORIA_ESCOLA_PRIVADA'] = pd.to_numeric(
                df['TP_CATEGORIA_ESCOLA_PRIVADA'], errors='coerce'
            ).fillna(0).astype('Int64')

        boolean_cols = [
            'IN_ACESSIBILIDADE_CORRIMAO',
            'IN_ACESSIBILIDADE_ELEVADOR',
            'IN_ACESSIBILIDADE_PISOS_TATEIS',
            'IN_ACESSIBILIDADE_VAO_LIVRE',
            'IN_ACESSIBILIDADE_RAMPAS',
            'IN_ACESSIBILIDADE_SINAL_SONORO',
            'IN_ACESSIBILIDADE_SINAL_TATIL',
            'IN_ACESSIBILIDADE_SINAL_VISUAL',
            'IN_INTERNET_ALUNOS',
            'IN_INTERNET_ADMINISTRATIVO',
            'IN_INTERNET_APRENDIZAGEM',
            'IN_INTERNET_COMUNIDADE',
            'IN_ACESSO_INTERNET_COMPUTADOR',
            'IN_ACES_INTERNET_DISP_PESSOAIS',
            'N_RESERVA_PPI',
            'IN_RESERVA_RENDA',
            'IN_RESERVA_PUBLICA',
            'IN_RESERVA_PCD',
            'IN_RESERVA_OUTROS',
            'IN_EDUCACAO_INDIGENA',
            'IN_EXAME_SELECAO',
            'IN_ORGAO_GREMIO_ESTUDANTIL',
            'IN_EAD',
            'IN_ALIMENTACAO',
            'IN_REDES_SOCIAIS',
            'IN_AGUA_POTAVEL',
            'IN_ALMOXARIFADO',
            'IN_AREA_VERDE',
            'IN_AUDITORIO',
            'IN_BANHEIRO',
            'IN_BANHEIRO_EI',
            'IN_BANHEIRO_PNE',
            'IN_BANHEIRO_FUNCIONARIOS',
            'IN_BANHEIRO_CHUVEIRO',
            'IN_BIBLIOTECA',
            'IN_COZINHA',
            'IN_DORMITORIO_ALUNO',
            'IN_DORMITORIO_PROFESSOR',
            'IN_LABORATORIO_CIENCIAS',
            'IN_LABORATORIO_INFORMATICA',
            'IN_PATIO_COBERTO',
            'IN_PATIO_DESCOBERTO',
            'IN_PARQUE_INFANTIL',
            'IN_PISCINA',
            'IN_QUADRA_ESPORTES_COBERTA',
            'IN_QUADRA_ESPORTES_DESCOBERTA',
            'IN_SALA_ATELIE_ARTES',
            'IN_SALA_MUSICA_CORAL',
            'IN_SALA_ESTUDIO_DANCA',
            'IN_SALA_MULTIUSO',
            'IN_SALA_DIRETORIA',
            'IN_SALA_LEITURA',
            'IN_SALA_PROFESSOR',
            'IN_SALA_REPOUSO_ALUNO',
            'IN_SECRETARIA',
            'IN_SALA_ATENDIMENTO_ESPECIAL',
            'IN_TERREIRAO',
        ]

        for col in boolean_cols:
            if col not in df.columns:
                df[col] = ''
            df[col] = df[col].astype(str).str.strip().str.lower().replace('nan', '')
            bool_map = {
                '1': True, 'sim': True, 's': True, 'true': True,
                '0': False, 'não': False, 'n': False, 'nao': False,
                '': False
            }
            df[col] = df[col].map(bool_map).fillna(False).astype(bool)

        count_cols = [
            'QT_SALAS_UTILIZADAS',
            'QT_SALAS_UTILIZADAS_FORA',
            'QT_SALAS_UTILIZADAS_DENTRO',
            'QT_SALAS_UTILIZA_CLIMATIZADAS',
            'QT_SALAS_UTILIZADAS_ACESSIVEIS',
            'QT_EQUIP_DVD',
            'QT_EQUIP_SOM',
            'QT_EQUIP_TV',
            'QT_EQUIP_LOUSA_DIGITAL',
            'QT_EQUIP_MULTIMIDIA',
            'QT_DESKTOP_ALUNO',
            'QT_COMP_PORTATIL_ALUNO',
            'QT_TABLET_ALUNO',
            'QT_PROF_ADMINISTRATIVOS',
            'QT_PROF_SERVICOS_GERAIS',
            'QT_PROF_BIBLIOTECARIO',
            'QT_PROF_SAUDE',
            'QT_PROF_COORDENADOR',
            'QT_PROF_FONOAUDIOLOGO',
            'QT_PROF_NUTRICIONISTA',
            'QT_PROF_PSICOLOGO',
            'QT_PROF_ALIMENTACAO',
            'QT_PROF_PEDAGOGIA',
            'QT_PROF_SECRETARIO',
            'QT_PROF_SEGURANCA',
            'QT_PROF_MONITORES',
            'QT_PROF_GESTAO',
            'QT_PROF_ASSIST_SOCIAL',
            'QT_MAT_INF',
            'QT_MAT_INF_CRE',
            'QT_MAT_INF_PRE',
            'QT_MAT_FUND',
            'QT_MAT_FUND_AI',
            'QT_MAT_FUND_AF',
            'QT_MAT_MED',
            'QT_MAT_MED_CT',
            'QT_MAT_PROF',
            'QT_MAT_PROF_TEC',
            'QT_MAT_EJA',
            'QT_MAT_EJA_FUND',
            'QT_MAT_EJA_FUND_AI',
            'QT_MAT_EJA_FUND_AF',
            'QT_MAT_EJA_MED',
            'QT_MAT_ESP',
            'QT_DOC_INF',
            'QT_DOC_INF_CRE',
            'QT_DOC_INF_PRE',
            'QT_DOC_FUND',
            'QT_DOC_FUND_AI',
            'QT_DOC_FUND_AF',
            'QT_DOC_MED',
            'QT_DOC_MED_CT',
            'QT_DOC_PROF',
            'QT_DOC_PROF_TEC',
            'QT_DOC_EJA',
            'QT_DOC_EJA_FUND',
            'QT_DOC_EJA_FUND_AI',
            'QT_DOC_EJA_FUND_AF',
            'QT_DOC_EJA_MED',
            'QT_DOC_ESP',
        ]

        for col in count_cols:
            if col not in df.columns:
                df[col] = 0
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

        return df