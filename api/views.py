from rest_framework import generics
from .models import Curso, CursoPolo, Inscricao, Candidato, Pais, Cidade, Polo, Endereco, HistoricoEducacional
from .serializers import CursoSerializer, PoloSerializer, InscricaoSerializer, CandidatoSerializer, CidadeSerializer, HistoricoEducacionalSerializer, UsuarioAdminLoginSerializer, UsuarioAdminRegistroSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
import hashlib, os
from datetime import datetime
from rest_framework import serializers
from .utils import enviar_email
from rest_framework.views import APIView
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication


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