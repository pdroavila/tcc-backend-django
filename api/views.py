from rest_framework import generics
from .models import Curso, CursoPolo, Inscricao, Candidato, Pais, Cidade, Polo, Endereco, HistoricoEducacional, UsuarioAdmin, UsuarioTela
from .serializers import CursoSerializer, PoloSerializer, InscricaoSerializer, CandidatoSerializer, CidadeSerializer, HistoricoEducacionalSerializer, UsuarioAdminLoginSerializer, UsuarioAdminRegistroSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
import hashlib, os
from datetime import datetime
from rest_framework import serializers
from .utils import enviar_email, enviar_email_recuperacao
from rest_framework.views import APIView
from django.db.models import Prefetch, Count, Case, When, Value, CharField
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from datetime import timedelta




class CursoListView(generics.ListAPIView):
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer

class PolosByCursoView(generics.GenericAPIView):
    serializer_class = PoloSerializer

    def get_queryset(self):
        curso_id = self.kwargs['curso_id']
        try:
            curso = Curso.objects.get(id=curso_id)
        except Curso.DoesNotExist:
            return CursoPolo.objects.none()  # Retorna um queryset vazio se o curso não for encontrado
        return CursoPolo.objects.filter(curso=curso)

    def get(self, request, curso_id):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"erro": "Curso não encontrado."}, status=status.HTTP_404_NOT_FOUND)
        
        polos = [cp.polo for cp in queryset]
        serializer = self.get_serializer(polos, many=True)
        return Response(serializer.data)

class PostInscricao(generics.CreateAPIView):
    queryset = Inscricao.objects.all()
    serializer_class = InscricaoSerializer

    @transaction.atomic  # Garante que todas as operações aconteçam dentro de uma transação
    def perform_create(self, serializer):
        
        data = self.request.data
        candidato_data = data.get('candidato')
        cpf = candidato_data.get('cpf')

        # Processa a nacionalidade
        nacionalidade_pk = candidato_data.get('nacionalidade')
        if nacionalidade_pk:
            try:
                pais_instance = Pais.objects.get(pk=nacionalidade_pk)
                candidato_data['nacionalidade'] = pais_instance
            except Pais.DoesNotExist:
                print(f"Pais com esse PK não existe.")
               
        # Processa a naturalidade
        naturalidade_id = candidato_data.get('naturalidade')
        if naturalidade_id:
            try:
                candidato_data['naturalidade'] = Cidade.objects.get(pk=naturalidade_id)
            except Cidade.DoesNotExist:
                print(f"Cidade incorreta.")
                
        # Processa o polo
        polo_id = candidato_data.get('polo_ofertante')
        if polo_id:
            try:
                candidato_data['polo_ofertante'] = Polo.objects.get(pk=polo_id)
            except Polo.DoesNotExist:
                print(f"Polo incorreto.")
        
        # Processa o curso
        curso_id = data.get('curso')
        if curso_id:
            try:
                curso_instance = Curso.objects.get(pk=curso_id)
                data['curso'] = curso_instance
            except Curso.DoesNotExist:
                print(f"Curso com esse PK não existe.")

        # Verifica se o candidato já está inscrito nesse curso
        inscricao_existente = Inscricao.objects.filter(
            candidato__cpf=cpf,
            curso_id=curso_id
        ).exists()

        if inscricao_existente:
            raise serializers.ValidationError({"error": "O CPF já está inscrito nesse curso."})

        # Verifica quantas inscrições o candidato já tem
        inscricoes_count = Inscricao.objects.filter(candidato__cpf=cpf).count()
        if inscricoes_count >= 3:
            raise serializers.ValidationError({"error": "CPF já inscrito em 3 ou mais cursos."})

        # Filtra apenas os campos válidos para o modelo Candidato
        candidato_fields = {field.name for field in Candidato._meta.get_fields()}
        filtered_candidato_data = {key: value for key, value in candidato_data.items() if key in candidato_fields}

        # Cria o candidato
        candidato = Candidato.objects.create(**filtered_candidato_data)

        # Gera hash
        salt = os.urandom(16).hex()
        unique_string = f"{cpf}{candidato.id}{salt}{candidato_data.get('data_inscricao', '')}"
        hash_value = hashlib.sha512(unique_string.encode()).hexdigest()
        data_criacao = datetime.now()

        # Faz o select da cidade com base no nome fornecido
        cidade_nome = candidato_data.get('cidade')
        cidade_instance = None
        if cidade_nome:
            try:
                cidade_instance = Cidade.objects.get(nome=cidade_nome)
            except Cidade.DoesNotExist:
                raise serializers.ValidationError({"error": f"Cidade '{cidade_nome}' não encontrada."})

        # Salva o endereço
        Endereco.objects.create(
            candidato=candidato,  # Associa o candidato ao endereço
            area=candidato_data.get('area'),
            cep=candidato_data.get('cep'),
            estado=candidato_data.get('estado'),
            cidade=cidade_instance.nome if cidade_instance else None,  # Atribui o nome da cidade
            cidade_id=cidade_instance if cidade_instance else None,  # Atribui o ID da cidade
            bairro=candidato_data.get('bairro'),
            logradouro=candidato_data.get('logradouro'),
            numero=candidato_data.get('numero'),
            complemento=candidato_data.get('complemento', '')  # Campo opcional
        )

        historico_data = {
            'tipo_escola': candidato_data.get('tipo_escola'),
            'nivel_escolaridade': candidato_data.get('nivel_escolaridade'),
            'anexo_historico_escolar': candidato_data.get('anexo_historico_escolar'),
            'candidato': candidato.id,
            'cpf' : candidato.cpf
        } 

         # Use o serializer de HistoricoEducacional para criar o registro e processar o base64 corretamente
        historico_serializer = HistoricoEducacionalSerializer(data=historico_data)
        if historico_serializer.is_valid():
            historico_serializer.save(candidato=candidato)
        else:
            raise serializers.ValidationError(historico_serializer.errors)


        # Cria a inscrição para o candidato
        serializer.save(candidato=candidato, hash=hash_value, status=0, data_criacao=data_criacao, data_modificacao=data_criacao, curso=data['curso'])

        # Envia e-mail de confirmação
        enviar_email(
            candidato, hash_value, data['curso']
        )


class GetSearchCidade(generics.GenericAPIView):
    serializer_class = CidadeSerializer

    def get_queryset(self):
        """
        Sobrescreve o método para aplicar o filtro baseado no parâmetro 'nome'
        """
        nome_cidade = self.request.query_params.get('nome', None)
        if nome_cidade:
            # Filtra as cidades pelo nome, usando icontains para busca parcial
            return Cidade.objects.filter(nome__icontains=nome_cidade)
        else:
            # Retorna uma queryset vazia se o parâmetro 'nome' não for fornecido
            return Cidade.objects.none()

    def get(self, request, *args, **kwargs):
        """
        Lida com a requisição GET e retorna os dados das cidades filtradas
        """
        queryset = self.get_queryset()  # Usa o método get_queryset para obter os resultados filtrados
        if queryset.exists():
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "O parâmetro 'nome' é obrigatório ou não foi encontrada nenhuma cidade."}, status=status.HTTP_400_BAD_REQUEST)
        


class CandidatoPorHashView(APIView):
    def get(self, request, hash, format=None):
        # Passo 1: Buscar a inscrição usando a hash
        inscricao = get_object_or_404(Inscricao, hash=hash)

        # Passo 2: Obter o CPF do candidato vinculado a essa inscrição
        cpf_candidato = inscricao.candidato.cpf

        # Passo 3: Buscar todos os candidatos que possuem o mesmo CPF
        candidatos = Candidato.objects.filter(cpf=cpf_candidato)

        # Passo 4: Buscar todas as inscrições de todos esses candidatos
        # Prefetch as inscrições para evitar consultas extras
        candidatos_com_inscricoes = candidatos.prefetch_related(
            Prefetch('inscricao_set', queryset=Inscricao.objects.select_related('curso'))
        )

        # Serializar os candidatos e suas inscrições
        candidato_data = []
        for candidato in candidatos_com_inscricoes:
            inscricoes = candidato.inscricao_set.all()
            candidato_data.append({
                "id": candidato.id,
                "nome": candidato.nome_completo,
                "cpf": candidato.cpf,
                "inscricoes": [
                    {
                        "id": inscricao.id,
                        "curso": inscricao.curso.nome,
                        "descricao": inscricao.curso.descricao,
                        "data_inscricao": inscricao.data_criacao,
                        "status": inscricao.status
                    }
                    for inscricao in inscricoes
                ]
            })

        return Response(candidato_data, status=status.HTTP_200_OK)
    
class InscricaoDetailView(APIView):
    def get(self, request, inscricao_id, hash, format=None):
        # Obtendo a inscrição específica
        inscricao = get_object_or_404(Inscricao, id=inscricao_id, hash=hash)
        
        # Serializando os dados da inscrição para obter a estrutura básica
        serializer = InscricaoSerializer(inscricao)
        inscricao_data = serializer.data
        

        # Obtendo o curso relacionado e adicionando manualmente os dados
        if inscricao.curso:
            curso = inscricao.curso
            inscricao_data['curso'] = {
                "id": curso.id,
                "nome": curso.nome,
                # Inclua outros campos se necessário
            }

        # Adicionando manualmente o campo 'uf' da nacionalidade do candidato, se disponível
        candidato_data = inscricao_data.get('candidato', None)
        if candidato_data:
            if 'anexo_cpf' in candidato_data and candidato_data['anexo_cpf']:
                candidato_data['anexo_cpf'] = candidato_data['anexo_cpf'].replace('/media/', '')
            if 'anexo_rg' in candidato_data and candidato_data['anexo_rg']:
                candidato_data['anexo_rg'] = candidato_data['anexo_rg'].replace('/media/', '')

        if candidato_data and 'nacionalidade' in candidato_data:
            nacionalidade_id = candidato_data['nacionalidade']
            try:
                # Busca o país com base no ID armazenado em 'nacionalidade'
                pais = Pais.objects.get(id=nacionalidade_id)
                candidato_data['nacionalidade'] = pais.sigla
            except Pais.DoesNotExist:
                # Se o país não for encontrado, mantém a informação original
                candidato_data['nacionalidade'] = None

        # Atualizar a naturalidade com nome e outras informações
        if 'naturalidade' in candidato_data:
            naturalidade_id = candidato_data['naturalidade']
            try:
                cidade = Cidade.objects.get(id=naturalidade_id)
                candidato_data['naturalidade'] = cidade.nome
            except Cidade.DoesNotExist:
                candidato_data['naturalidade'] = None

        # Buscando todos os polos que oferecem o curso relacionado à inscrição
        curso_id = inscricao_data['curso']['id']
        polos_curso = CursoPolo.objects.filter(curso_id=curso_id).select_related('polo')
        polo_options = []

        for curso_polo in polos_curso:
            polo = curso_polo.polo
            polo_options.append({
                "id": polo.id,
                "label": polo.nome,
                "selected": True if polo.id == curso_id else False,
                "logradouro": polo.logradouro or "não definido",
                "numero": polo.numero or 0,
                "bairro": polo.bairro or "não definido",
                "cidade": polo.cidade.id  # Assumindo que cidade tem uma FK para `Cidade`
            })

        # Adicionando os polos à resposta
        inscricao_data['polo_options'] = polo_options

        endereco = Endereco.objects.get(candidato_id=candidato_data['id'])
        candidato_data['endereco'] = {
                            "logradouro": endereco.logradouro,
                            "numero": endereco.numero,
                            "bairro": endereco.bairro,
                            "cidade": endereco.cidade,  
                            "estado": endereco.estado,
                            "cep": endereco.cep,
                            "area": endereco.area,
                            "complemento": endereco.complemento
                        }
        
        try:
            historico = HistoricoEducacional.objects.get(candidato=candidato_data['id'])
            
            # Adicionando os detalhes do histórico educacional
            candidato_data['historico_educacional'] = {
                "tipo_escola": historico.tipo_escola,
                "nivel_escolaridade": historico.nivel_escolaridade,
                "anexo_historico_escolar": historico.anexo_historico_escolar.url.replace('/media/', '') if historico.anexo_historico_escolar else None
            }
        except HistoricoEducacional.DoesNotExist:
            candidato_data['historico_educacional'] = None


        return Response(inscricao_data, status=status.HTTP_200_OK)
    

class MediaImageView(APIView):
    def get(self, request, filename, format=None):
        # Cria o caminho completo para o arquivo de mídia
        file_path = os.path.join(settings.MEDIA_ROOT, filename)

        # Verifica se o arquivo existe e retorna a resposta
        if os.path.exists(file_path):
            try:
                return FileResponse(open(file_path, 'rb'), content_type='image/jpeg')
            except IOError:
                raise Http404
        else:
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        

class UpdateInscricao(APIView):
    @transaction.atomic  # Garante que todas as operações aconteçam dentro de uma transação
    def put(self, request, format=None):
        # Obtendo o ID da inscrição do corpo da requisição
        data = request.data
        inscricao_id = data.get('inscricao_id')

        if not inscricao_id:
            raise serializers.ValidationError({"error": "O campo 'inscricao_id' é obrigatório."})

        # Obtendo a inscrição a ser atualizada
        inscricao = get_object_or_404(Inscricao, id=inscricao_id)
        candidato_data = data.get('candidato')
        if not candidato_data:
            raise serializers.ValidationError({"error": "Os dados do candidato são obrigatórios."})
        
        # Processa a naturalidade
        naturalidade_nome = candidato_data.get('naturalidade_nome')
        if naturalidade_nome:
            try:
                candidato_data['naturalidade'] = Cidade.objects.get(nome=naturalidade_nome).id
            except Cidade.DoesNotExist:
                raise serializers.ValidationError({"error": "Cidade incorreta."})

        # Processa o curso
        curso_id = data.get('curso')
        if curso_id:
            try:
                curso_instance = Curso.objects.get(pk=curso_id)
                data['curso'] = curso_instance
            except Curso.DoesNotExist:
                raise serializers.ValidationError({"error": "Curso com esse PK não existe."})

        # Filtra apenas os campos válidos para o modelo Candidato
        candidato_fields = {field.name for field in Candidato._meta.get_fields()}
        filtered_candidato_data = {key: value for key, value in candidato_data.items() if key in candidato_fields}

        # Atualiza o candidato
        candidato_serializer = CandidatoSerializer(inscricao.candidato, data=filtered_candidato_data, partial=True)
        if not candidato_serializer.is_valid():
            raise serializers.ValidationError(candidato_serializer.errors)
        candidato_serializer.save()

        # Atualiza o Endereço
        cidade_nome = candidato_data.get('cidade')
        cidade_instance = None
        if cidade_nome:
            try:
                cidade_instance = Cidade.objects.get(nome=cidade_nome)
            except Cidade.DoesNotExist:
                raise serializers.ValidationError({"error": f"Cidade '{cidade_nome}' não encontrada."})

        endereco = Endereco.objects.filter(candidato=inscricao.candidato).first()
        if endereco:
            endereco.area = candidato_data.get('area')
            endereco.cep = candidato_data.get('cep')
            endereco.estado = candidato_data.get('estado')
            endereco.cidade = cidade_instance.nome if cidade_instance else endereco.cidade
            endereco.cidade_id = cidade_instance if cidade_instance else endereco.cidade_id
            endereco.bairro = candidato_data.get('bairro')
            endereco.logradouro = candidato_data.get('logradouro')
            endereco.numero = candidato_data.get('numero')
            endereco.complemento = candidato_data.get('complemento', '')
            endereco.save()

        historico_data = {
            'tipo_escola': candidato_data.get('tipo_escola'),
            'nivel_escolaridade': candidato_data.get('nivel_escolaridade'),
            'anexo_historico_escolar': candidato_data.get('anexo_historico_escolar'),
        }

        historico = HistoricoEducacional.objects.filter(candidato=inscricao.candidato).first()

        if historico:
            # Atualizar um histórico existente
            historico_educacional_serializer = HistoricoEducacionalSerializer(
                instance=historico,
                data=historico_data,
                partial=True
            )
        else:
            # Criar um novo histórico
            historico_data['candidato'] = inscricao.candidato.id
            historico_educacional_serializer = HistoricoEducacionalSerializer(data=historico_data)

        if historico_educacional_serializer.is_valid():
            historico_educacional_serializer.save()
        else:
            raise serializers.ValidationError(historico_educacional_serializer.errors)

        # Atualiza a inscrição
        inscricao.status = data.get('status', inscricao.status)
        inscricao.data_modificacao = datetime.now()
        inscricao.curso = data['curso'] if 'curso' in data else inscricao.curso
        inscricao.save()

        # Serializa os dados atualizados e retorna a resposta
        serializer = InscricaoSerializer(inscricao)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class RegistroView(APIView):
    def post(self, request):
        serializer = UsuarioAdminRegistroSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = UsuarioAdminLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            
            user = authenticate(request, username=username, password=password)
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user_id': user.id
                })
            return Response({'error': 'Credenciais inválidas'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class VerificarTokenView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "valid": True,
            "user": request.user.username,
            "user_id": request.user.id
        })
    
class SolicitarRecuperacaoSenhaView(APIView):
    def post(self, request):
        email = request.data.get('email')
        try:
            usuario = UsuarioAdmin.objects.get(email=email)
            usuario.gerar_token_recuperacao_senha()
            enviar_email_recuperacao(usuario, usuario.token_recuperacao_senha)
            return Response({"message": "Se o e-mail existir, o e-mail de recuperação será enviado."}, status=status.HTTP_200_OK)
        except UsuarioAdmin.DoesNotExist:
            return Response({"message": "Se o e-mail existir, o e-mail de recuperação será enviado."}, status=status.HTTP_200_OK)
        
class AlterarSenhaView(APIView):
    def post(self, request):
        token = request.data.get('token')
        nova_senha = request.data.get('nova_senha')

        try:
            usuario = UsuarioAdmin.objects.get(token_recuperacao_senha=token)

            if (timezone.now() - timedelta(hours=3)) > timezone.localtime(usuario.token_expira_em):
                return Response({"message": "Token expirado."}, status=status.HTTP_400_BAD_REQUEST)

            print(nova_senha)
            usuario.set_password(nova_senha)
            usuario.token_recuperacao_senha = None 
            usuario.token_expira_em = None
            usuario.save()
            return Response({"message": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)
        except UsuarioAdmin.DoesNotExist:
            return Response({"message": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

class VerificarAcessoTela(APIView):
    def post(self, request):
        usuario_id = request.data.get('usuario_id')
        rota = request.data.get('rota')
        
        try:
            usuario = UsuarioAdmin.objects.get(id=usuario_id)
            # if usuario.is_root:
            #     return Response({'tem_acesso': True})
            
            tem_acesso = UsuarioTela.objects.filter(
                usuario_id=usuario_id,
                tela__rota=rota
            ).exists()
            
            return Response({'tem_acesso': tem_acesso})
        except UsuarioAdmin.DoesNotExist:
            return Response({'erro': 'Usuário não encontrado'}, status=404)
        

    #     def atribuir_acesso_tela(request):
    # if not request.user.usuarioadmin.is_root:
    #     return Response({'erro': 'Acesso negado'}, status=403)
    
    # usuario_id = request.data.get('usuario_id')
    # tela_id = request.data.get('tela_id')
    
    # try:
    #     usuario = UsuarioAdmin.objects.get(id=usuario_id)
    #     tela = Tela.objects.get(id=tela_id)
        
    #     UsuarioTela.objects.get_or_create(usuario=usuario, tela=tela)
        
    #     return Response({'sucesso': True})
    # except (UsuarioAdmin.DoesNotExist, Tela.DoesNotExist):
    #     return Response({'erro': 'Usuário ou tela não encontrada'}, status=404)
        
class GraficosView(APIView):
    def get(self, request):
        # Inscrições por Polo Ofertante
        inscricoes_por_polo = Candidato.objects.values('polo_ofertante__nome').annotate(total=Count('id')).order_by('polo_ofertante__nome')
        
        # Tipo de Escola (agora usando HistoricoEducacional)
        tipo_escola = HistoricoEducacional.objects.annotate(
                escola_tipo=Case(
                    When(tipo_escola=0, then=Value('Pública')),
                    When(tipo_escola=1, then=Value('Privada')),
                    output_field=CharField(),
                )
            ).values('escola_tipo').annotate(total=Count('id'))   
             
        # Distribuição por Gênero
        distribuicao_genero = Candidato.objects.annotate(
                genero_tipo=Case(
                    When(genero=0, then=Value('Não informado')),
                    When(genero=1, then=Value('Masculino')),
                    When(genero=2, then=Value('Feminino')),
                    When(genero=3, then=Value('Outro')),
                    output_field=CharField(),
                )
            ).values('genero_tipo').annotate(total=Count('id'))
        
         # Estado Civil (com as regras fornecidas)
        estado_civil = Candidato.objects.annotate(
            estado_civil_tipo=Case(
                When(estado_civil=0, then=Value('Solteiro(a)')),
                When(estado_civil=1, then=Value('Casado(a)')),
                When(estado_civil=2, then=Value('Divorciado(a)')),
                When(estado_civil=3, then=Value('Viúvo(a)')),
                output_field=CharField(),
            )
        ).values('estado_civil_tipo').annotate(total=Count('id'))

        # Renda per Capita
        renda_per_capita = Candidato.objects.annotate(
            renda_tipo=Case(
                When(renda_per_capita=1, then=Value('Até 0,5 salário mínimo')),
                When(renda_per_capita=2, then=Value('0,5 a 1,0 salário mínimo')),
                When(renda_per_capita=3, then=Value('1,0 a 1,5 salário mínimo')),
                When(renda_per_capita=4, then=Value('1,5 a 2,5 salários mínimos')),
                When(renda_per_capita=5, then=Value('2,5 a 3,5 salários mínimos')),
                When(renda_per_capita=6, then=Value('Acima de 3,5 salários mínimos')),
                When(renda_per_capita=0, then=Value('Prefiro não informar')),
                output_field=CharField(),
            )
        ).values('renda_tipo').annotate(total=Count('id'))

        # Distribuição por Etnia
        distribuicao_etnia = Candidato.objects.annotate(
            etnia_tipo=Case(
                When(etnia=1, then=Value('Branco')),
                When(etnia=2, then=Value('Preto')),
                When(etnia=3, then=Value('Pardo')),
                When(etnia=4, then=Value('Amarelo')),
                When(etnia=5, then=Value('Indígena')),
                When(etnia=0, then=Value('Não quero informar')),
                output_field=CharField(),
            )
        ).values('etnia_tipo').annotate(total=Count('id'))

        # Área de Residência
        area_residencia = Endereco.objects.annotate(
            area_tipo=Case(
                When(area=0, then=Value('Urbana')),
                When(area=1, then=Value('Rural')),
                output_field=CharField(),
            )
        ).values('area_tipo').annotate(total=Count('id'))

        # Nível de Escolaridade
        nivel_escolaridade = HistoricoEducacional.objects.annotate(
            escolaridade_tipo=Case(
                When(nivel_escolaridade=0, then=Value('Fundamental I - Completo (1º a 5º)')),
                When(nivel_escolaridade=1, then=Value('Fundamental I - Incompleto (1º a 5º)')),
                When(nivel_escolaridade=2, then=Value('Fundamental II - Completo (6º a 9º)')),
                When(nivel_escolaridade=3, then=Value('Fundamental II - Incompleto (6º a 9º)')),
                When(nivel_escolaridade=4, then=Value('Médio - Completo')),
                When(nivel_escolaridade=5, then=Value('Médio - Incompleto')),
                When(nivel_escolaridade=6, then=Value('Superior - Completo')),
                When(nivel_escolaridade=7, then=Value('Superior - Incompleto')),
                When(nivel_escolaridade=8, then=Value('Pós-graduação - Completo')),
                When(nivel_escolaridade=9, then=Value('Pós-graduação - Incompleto')),
                output_field=CharField(),
            )
        ).values('escolaridade_tipo').annotate(total=Count('id'))
        
        return Response({
            'inscricoes_por_polo': list(inscricoes_por_polo),
            'tipo_escola': list(tipo_escola),
            'distribuicao_genero': list(distribuicao_genero),
            'estado_civil': list(estado_civil),
            'renda_per_capita': list(renda_per_capita),
            'distribuicao_etnia': list(distribuicao_etnia),
            'area_residencia': list(area_residencia),
            'nivel_escolaridade': list(nivel_escolaridade)
        })