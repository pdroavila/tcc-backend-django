# Importações da biblioteca padrão
import hashlib
import os
from datetime import datetime, timedelta, date
from decimal import Decimal

# import tensorflow as tf
# import numpy as np
import base64
from PIL import Image
from io import BytesIO

# Importações de terceiros
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.db.models import (
    Case,
    CharField,
    Count,
    F,
    Prefetch,
    Q,
    Value,
    When,
    Count, 
    Avg,
    DecimalField
)
from django.db.models.functions import ExtractYear, Now
from django.shortcuts import get_object_or_404
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.timezone import make_aware

from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import (
    generics,
    serializers,
    status,
    viewsets,
    permissions,
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

# Importações locais
from .models import (
    Candidato,
    Cidade,
    Curso,
    CursoPolo,
    Endereco,
    HistoricoEducacional,
    Inscricao,
    InscricaoLog,
    Pais,
    Polo,
    Tela,
    UsuarioAdmin,
    UsuarioTela,
)

from .serializers import (
    CandidatoSerializer,
    CidadeSerializer,
    CursoSerializer,
    HistoricoEducacionalSerializer,
    InscricaoLogSerializer,
    InscricaoSerializer,
    PoloSerializer,
    TelaSerializer,
    UsuarioAdminListSerializer,
    UsuarioAdminLoginSerializer,
    UsuarioAdminRegistroSerializer,
    UsuarioAdminUpdateSerializer,
    EstatisticasSerializer
)

from .utils import (
    enviar_email,
    enviar_email_aprovacao,
    enviar_email_recuperacao,
    enviar_email_rejeicao,
)

model_path = os.path.join(settings.BASE_DIR, 'models', 'modelo_final.h5')
# modelo_carregado = tf.keras.models.load_model(model_path)

def validate_rg(image, model):
    # Converter imagem em array e garantir que seja gravável
    # img = tf.keras.preprocessing.image.img_to_array(image).copy()
    # # Alternativamente, você pode usar:
    # # img.setflags(write=1)

    # # Redimensionar a imagem
    # img = tf.image.resize(img, [224, 224])

    # # Expandir dimensões
    # img = np.expand_dims(img, axis=0)

    # Normalizar a imagem
    img = img / 255.0  # Evitar operação in-place

    # Fazer a predição
    prediction = model.predict(img)

    return prediction[0][0] > 0.5


"""
Retorna uma lista de cursos com filtros opcionais de nome e datas.
"""
class CursoListView(generics.ListAPIView):
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    pagination_class = None  # Desativa a paginação

    def get_queryset(self):
        queryset = super().get_queryset()
        
        nome = self.request.query_params.get('nome', None)
        data_inicial = self.request.query_params.get('data_inicial', None)
        data_final = self.request.query_params.get('data_final', None)
        polo = self.request.query_params.get('polo', None)

        if nome:
            queryset = queryset.filter(nome__icontains=nome)
        
        if data_inicial:
            try:
                data_inicial = datetime.strptime(data_inicial, '%Y-%m-%d')
                data_inicial = make_aware(data_inicial)  # Converte para timezone-aware
                queryset = queryset.filter(prazo_inscricoes__gte=data_inicial)
            except ValueError:
                pass
        
        if data_final:
            try:
                data_final = datetime.strptime(data_final, '%Y-%m-%d')
                # Ajusta para o final do dia (23:59:59)
                data_final = data_final.replace(hour=23, minute=59, second=59)
                data_final = make_aware(data_final)  # Converte para timezone-aware
                queryset = queryset.filter(prazo_inscricoes__lte=data_final)
            except ValueError:
                pass

        if polo:
            try:
                polo_id = int(polo)
                queryset = queryset.filter(cursopolo__polo_id=polo_id)
            except (ValueError, Polo.DoesNotExist):
                pass

        return queryset

    """
    Retorna os polos associados a um curso específico.
    """
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

    """
    Cria uma nova inscrição para um candidato, incluindo validações e processamento
    de dados como nacionalidade, naturalidade, e polo.
    """
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


    """
    Filtra e retorna uma lista de cidades com base no nome fornecido.
    """
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
            return Cidade.objects.all()

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
        


    """
    Recupera e retorna as informações de um candidato e suas inscrições com base em uma hash única.
    """
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
    
    """
    Retorna os detalhes de uma inscrição específica, incluindo curso, candidato e polos.
    """
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
    

    """
    Busca e retorna um arquivo de mídia (imagem) com base no nome do arquivo.
    """
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
        

    """
    Atualiza os dados de uma inscrição e do candidato, incluindo dados de endereço e histórico educacional.
    """
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
        inscricao.status = 0
        inscricao.data_modificacao = datetime.now()
        inscricao.curso = data['curso'] if 'curso' in data else inscricao.curso
        inscricao.save()

        # Serializa os dados atualizados e retorna a resposta
        serializer = InscricaoSerializer(inscricao)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    """
    Registra um novo usuário admin e retorna tokens de autenticação.
    """
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

    """
    Realiza o login de um usuário admin, retornando tokens de autenticação se as credenciais forem válidas.
    """
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
    
    """
    Verifica a validade do token JWT e retorna informações do usuário autenticado.
    """
class VerificarTokenView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "valid": True,
            "user": request.user.username,
            "user_id": request.user.id
        })
    
    """
    Envia um e-mail de recuperação de senha para um usuário com base no e-mail fornecido.
    """
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
        
    """
    Permite alterar a senha de um usuário usando um token de recuperação.
    """
class AlterarSenhaView(APIView):
    def post(self, request):
        token = request.data.get('token')
        nova_senha = request.data.get('nova_senha')

        try:
            usuario = UsuarioAdmin.objects.get(token_recuperacao_senha=token)

            if (timezone.now()) > timezone.localtime(usuario.token_expira_em):
                return Response({"message": "Token expirado."}, status=status.HTTP_400_BAD_REQUEST)

            print(nova_senha)
            usuario.set_password(nova_senha)
            usuario.token_recuperacao_senha = None 
            usuario.token_expira_em = None
            usuario.save()
            return Response({"message": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)
        except UsuarioAdmin.DoesNotExist:
            return Response({"message": "Token inválido."}, status=status.HTTP_400_BAD_REQUEST)

    """
    Verifica se o usuário tem permissão para acessar uma rota específica.
    """
class VerificarAcessoTela(APIView):
    permission_classes = [IsAuthenticated]

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
        
    """
    Gera e retorna dados para diversos gráficos estatísticos, como inscrições por polo, distribuição por gênero, etc.
    """
class GraficosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        id_polo = request.query_params.get('id_polo')
        base_queryset = Candidato.objects.all()
        endereco_queryset = Endereco.objects.all()
        historico_queryset = HistoricoEducacional.objects.all()

        if id_polo:
            base_queryset = base_queryset.filter(polo_ofertante_id=id_polo)
            endereco_queryset = endereco_queryset.filter(candidato__polo_ofertante_id=id_polo)
            historico_queryset = historico_queryset.filter(candidato__polo_ofertante_id=id_polo)

        # Inscrições por Polo Ofertante
        inscricoes_por_polo = base_queryset.values('polo_ofertante__nome').annotate(
            total=Count('id')
        ).order_by('polo_ofertante__nome')
        
        # Tipo de Escola
        tipo_escola = historico_queryset.annotate(
            escola_tipo=Case(
                When(tipo_escola=0, then=Value('Pública')),
                When(tipo_escola=1, then=Value('Privada')),
                output_field=CharField(),
            )
        ).values('escola_tipo').annotate(total=Count('id'))
        
        # Distribuição por Gênero
        distribuicao_genero = base_queryset.annotate(
            genero_tipo=Case(
                When(genero=0, then=Value('Não informado')),
                When(genero=1, then=Value('Masculino')),
                When(genero=2, then=Value('Feminino')),
                When(genero=3, then=Value('Outro')),
                output_field=CharField(),
            )
        ).values('genero_tipo').annotate(total=Count('id'))
        
        # Estado Civil
        estado_civil = base_queryset.annotate(
            estado_civil_tipo=Case(
                When(estado_civil=0, then=Value('Solteiro(a)')),
                When(estado_civil=1, then=Value('Casado(a)')),
                When(estado_civil=2, then=Value('Divorciado(a)')),
                When(estado_civil=3, then=Value('Viúvo(a)')),
                output_field=CharField(),
            )
        ).values('estado_civil_tipo').annotate(total=Count('id'))

        # Renda per Capita
        renda_per_capita = base_queryset.annotate(
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
        distribuicao_etnia = base_queryset.annotate(
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
        area_residencia = endereco_queryset.annotate(
            area_tipo=Case(
                When(area=0, then=Value('Urbana')),
                When(area=1, then=Value('Rural')),
                output_field=CharField(),
            )
        ).values('area_tipo').annotate(total=Count('id'))

        # Nível de Escolaridade
        nivel_escolaridade = historico_queryset.annotate(
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
    
    """
    Cria um novo curso e associa polos a ele.
    """
class CursoCreateView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        # Extrai os polos da requisição
        polos_ids = request.data.pop('polos', [])
        
        # Cria o curso
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        curso = serializer.save()
        
        # Cria as relações com os polos
        for polo_id in polos_ids:
            CursoPolo.objects.create(
                curso_id=curso.id,
                polo_id=polo_id
            )
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    """
    Retorna uma lista de todos os polos.
    """
class PoloListView(generics.ListAPIView):
    queryset = Polo.objects.all()
    serializer_class = PoloSerializer
    pagination_class = None  # Desativa a paginação

    def get_queryset(self):
        queryset = super().get_queryset()
        nome = self.request.query_params.get('nome', None)
        cidade = self.request.query_params.get('cidade', None)

        if nome:
            queryset = queryset.filter(nome__icontains=nome)

        if cidade:
            queryset = queryset.filter(cidade_id=cidade)

        return queryset

    """
    Retorna os detalhes de um curso específico, incluindo polos associados.
    """
class CursoDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Busca os polos relacionados ao curso
        polos_ids = CursoPolo.objects.filter(
            curso_id=instance.id
        ).values_list('polo_id', flat=True)
        
        # Adiciona os polos ao response
        data = serializer.data
        data['polos'] = list(polos_ids)
        
        return Response(data)
    

    """
    Atualiza os dados de um curso e os polos associados.
    """
class CursoUpdateView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        # Extrai os polos da requisição
        polos_ids = request.data.pop('polos', [])
        
        # Atualiza o curso
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        curso = serializer.save()
        
        # Atualiza as relações com os polos
        # Primeiro remove todas as relações existentes
        CursoPolo.objects.filter(curso_id=curso.id).delete()
        
        # Depois cria as novas relações
        for polo_id in polos_ids:
            CursoPolo.objects.create(
                curso_id=curso.id,
                polo_id=polo_id
            )
        
        # Retorna os dados atualizados incluindo os polos
        data = serializer.data
        data['polos'] = polos_ids
        
        return Response(data)
    

    """
    Filtros de pesquisa para o modelo UsuarioAdmin com base em nome e e-mail.
    """
class UsuarioAdminFilter(filters.FilterSet):
    nome = filters.CharFilter(field_name='nome_completo', lookup_expr='icontains')
    email = filters.CharFilter(lookup_expr='icontains')
    
    class Meta:
        model = UsuarioAdmin
        fields = ['nome', 'email']

    """
    Permite visualizar a lista de telas disponíveis para o usuário autenticado.
    """
class TelaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None  # Desativa a paginação
    queryset = Tela.objects.all()
    serializer_class = TelaSerializer

    """
    Permite gerenciar usuários admin, incluindo criação, atualização, e adição de telas.
    """
class UsuarioAdminViewSet(viewsets.ModelViewSet):
    queryset = UsuarioAdmin.objects.all()
    pagination_class = None  # Desativa a paginação
    # permission_classes = [AllowAny]
    permission_classes = [IsAuthenticated]
    filter_backends = (DjangoFilterBackend,)
    filterset_class = UsuarioAdminFilter  # Alterado para usar a classe de filtro personalizada

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioAdminRegistroSerializer
        elif self.action in ['update', 'partial_update', 'retrieve']:
            return UsuarioAdminUpdateSerializer
        return UsuarioAdminListSerializer

    def create(self, request, *args, **kwargs):
        # Extrair IDs das telas antes de processar o serializer
        telas_ids = request.data.pop('telas', [])
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Criar relações de telas
        for tela_id in telas_ids:
            UsuarioTela.objects.create(
                usuario_id=instance.id,
                tela_id=tela_id
            )

        # Buscar instância atualizada com telas
        serializer = self.get_serializer(instance)
        return Response(serializer.data, status=201)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Extrair IDs das telas antes de processar o serializer
        telas_ids = request.data.pop('telas', None)
        
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if telas_ids is not None:
            # Atualizar relações de telas
            UsuarioTela.objects.filter(usuario_id=instance.id).delete()
            for tela_id in telas_ids:
                UsuarioTela.objects.create(
                    usuario_id=instance.id,
                    tela_id=tela_id
                )

        # Buscar instância atualizada com telas
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # Adicionar telas à resposta
        data['telas'] = TelaSerializer(
            Tela.objects.filter(
                id__in=UsuarioTela.objects.filter(
                    usuario_id=instance.id
                ).values_list('tela_id', flat=True)
            ),
            many=True
        ).data
        
        return Response(data)
    
    """
    Filtros para buscar inscrições com base no candidato, curso, polo e data.
    """
class InscricaoFilter(filters.FilterSet):
    nome = filters.CharFilter(field_name='candidato__nome_completo', lookup_expr='icontains')
    curso = filters.NumberFilter(field_name='curso__id')
    polo = filters.NumberFilter(field_name='candidato__polo_ofertante__id')
    data_inicial = filters.DateFilter(field_name='data_criacao', lookup_expr='gte')
    data_final = filters.DateFilter(field_name='data_criacao', lookup_expr='lte')
    
    class Meta:
        model = Inscricao
        fields = ['status']


    """
    Permite gerenciar inscrições, incluindo listagem, visualização detalhada, e atualização.
    """
class InscricaoViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Inscricao.objects.all().select_related(
        'candidato', 'curso', 'candidato__polo_ofertante'
    )
    serializer_class = InscricaoSerializer
    filterset_class = InscricaoFilter

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Handle pagination if it's enabled
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self._add_polo_and_curso_data(serializer.data, page)
            return self.get_paginated_response(response_data)

        serializer = self.get_serializer(queryset, many=True)
        response_data = self._add_polo_and_curso_data(serializer.data, queryset)
        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response_data = self._add_single_polo_and_curso_data(serializer.data, instance)
        return Response(response_data)

    def _add_polo_and_curso_data(self, serialized_data, instances):
        for item, instance in zip(serialized_data, instances):
            candidato = instance.candidato
            polo = getattr(candidato, 'polo_ofertante', None)
            if polo:
                item['polo'] = {
                    'id': polo.id,
                    'nome': polo.nome,  # Adjust field names as per your model
                    # Include other fields as needed
                }
            else:
                item['polo'] = None

            # Add 'curso' data
            curso = instance.curso
            if curso:
                item['curso'] = {
                    'id': curso.id,
                    'nome': curso.nome,  # Adjust field names as per your model
                    # Include other fields as needed
                }
            else:
                item['curso'] = None
        return serialized_data

    def _add_single_polo_and_curso_data(self, serialized_data, instance):
        candidato = instance.candidato
        polo = getattr(candidato, 'polo_ofertante', None)
        if polo:
            serialized_data['polo'] = {
                'id': polo.id,
                'nome': polo.nome,  # Adjust field names as per your model
                # Include other fields as needed
            }
        else:
            serialized_data['polo'] = None

        # Add 'curso' data
        curso = instance.curso
        if curso:
            serialized_data['curso'] = {
                'id': curso.id,
                'nome': curso.nome,  # Adjust field names as per your model
                # Include other fields as needed
            }
        else:
            serialized_data['curso'] = None

        return serialized_data
    
    # @action(detail=False, methods=['get'])
    # def export(self, request):
    #     queryset = self.filter_queryset(self.get_queryset())
        
    #     response = HttpResponse(content_type='text/csv')
    #     response['Content-Disposition'] = 'attachment; filename="inscricoes.csv"'
        
    #     writer = csv.writer(response)
    #     writer.writerow([
    #         'Nome Completo', 'Email', 'Curso', 'Polo', 
    #         'Situação', 'Data de Inscrição'
    #     ])
        
    #     for inscricao in queryset:
    #         writer.writerow([
    #             inscricao.candidato.nome_completo,
    #             inscricao.candidato.email,
    #             inscricao.curso.nome,
    #             inscricao.polo.nome,
    #             inscricao.status,
    #             inscricao.data_criacao.strftime('%d/%m/%Y')
    #         ])
        
    #     return response

    """
    Aprova uma inscrição, atualizando seu status e registrando um log.
    """
class AprovarInscricaoView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, pk, format=None):
        try:
            # user_id = request.data.get('user_id', '')
            inscricao = Inscricao.objects.get(pk=pk)
            inscricao.status = '1'
            inscricao.save()
            serializer = InscricaoSerializer(inscricao)

            candidato = Candidato.objects.get(id=inscricao.candidato_id)
            curso = Curso.objects.get(id=inscricao.curso_id)
            usuario_admin = UsuarioAdmin.objects.get(id=request.data.get('user_id'))

            InscricaoLog.objects.create(
                inscricao=inscricao,
                status=1, 
                observacoes='Inscrição aprovada.',
                usuario=usuario_admin,
                data_registro = (timezone.now())
            )

            enviar_email_aprovacao(
                candidato,
                curso 
            )

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Inscricao.DoesNotExist:
            return Response({'erro': 'Inscrição não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        
    """
    Rejeita uma inscrição, atualizando seu status e registrando o motivo da rejeição.
    """
class RecusarInscricaoView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, format=None):
        try:
            inscricao = Inscricao.objects.get(pk=pk)
            if inscricao.status == '2':
                return Response({'erro': 'Inscrição já está rejeitada.'}, status=status.HTTP_400_BAD_REQUEST)
            inscricao.status = '2'
            inscricao.save()

            motivo = request.data.get('motivo')
            usuario_admin = UsuarioAdmin.objects.get(id=request.data.get('user_id'))

            candidato = Candidato.objects.get(id=inscricao.candidato_id)
            curso = Curso.objects.get(id=inscricao.curso_id)

            InscricaoLog.objects.create(
                inscricao=inscricao,
                status=0, 
                observacoes=motivo,
                usuario=usuario_admin,
                data_registro = (timezone.now())
            )

            enviar_email_rejeicao(
                candidato,
                curso,
                motivo,
                inscricao.hash
            )

            serializer = InscricaoSerializer(inscricao)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Inscricao.DoesNotExist:
            return Response({'erro': 'Inscrição não encontrada.'}, status=status.HTTP_404_NOT_FOUND)
        
    """
    Retorna o histórico de logs de uma inscrição específica.
    """
class InscricaoHistoricoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, inscricao_id):
        # Verifique se a inscrição existe
        inscricao = get_object_or_404(Inscricao, id=inscricao_id)
        
        # Obtenha todos os logs relacionados à inscrição
        logs = InscricaoLog.objects.filter(inscricao=inscricao).order_by('-data_registro')
        
        serializer = InscricaoLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ValidateRGView(APIView):
    def post(self, request):
        base64_image = request.data.get('image')

        if not base64_image:
            return Response({'error': 'Nenhuma imagem fornecida.'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Decodificar a imagem base64
            header, data = base64_image.split(';base64,')
            img_format = header.split('/')[-1]
            img_data = base64.b64decode(data)
            image = Image.open(BytesIO(img_data)).convert('RGB')
            
            # Validar a imagem
            is_rg = validate_rg(image, modelo_carregado)
            
            return Response({'is_rg': is_rg}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class PoloFilter(filters.FilterSet):
    nome = filters.CharFilter(lookup_expr='icontains')
    cidade = filters.NumberFilter()
    
    class Meta:
        model = Polo
        fields = ['nome', 'cidade']

class PoloViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Polo.objects.all()
    serializer_class = PoloSerializer
    filterset_class = PoloFilter

    def destroy(self, request, *args, **kwargs):
        polo = self.get_object()
        try:
            CursoPolo.objects.filter(polo=polo).delete()
            polo.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"error": "Erro ao excluir polo: " + str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
class EstatisticasViewSet(viewsets.ViewSet):
    def list(self, request):
        polo_id = request.query_params.get('polo_id', None)
        
        # Base query
        queryset = Inscricao.objects.select_related('candidato')
        
        # Filtrar por polo se fornecido
        if polo_id:
            queryset = queryset.filter(candidato__polo_ofertante=polo_id)
        
        # Calcular estatísticas
        hoje = date.today()
        
        # Total de inscrições
        total_inscricoes = queryset.count()
        
        # Média de idade
        media_idade = queryset.annotate(
            idade=hoje.year - ExtractYear('candidato__data_nascimento')
        ).aggregate(
            media_idade=Avg('idade')
        )['media_idade'] or 0
        
        # Média de renda
        # Mapeamento dos valores de renda baseado nos tipos do banco
        RENDA_MAPPING = {
            1: Decimal('1000.00'),    # Até 1 salário mínimo
            2: Decimal('2000.00'),    # 1-2 salários mínimos
            3: Decimal('3500.00'),    # 2-3 salários mínimos
            4: Decimal('5000.00'),    # 3-5 salários mínimos
            5: Decimal('7500.00')     # mais de 5 salários mínimos
        }
        
        media_renda = queryset.annotate(
            valor_renda=Case(
                *[When(candidato__renda_per_capita=k, then=v) 
                  for k, v in RENDA_MAPPING.items()],
                default=Value(Decimal('0.00')),
                output_field=DecimalField(max_digits=10, decimal_places=2),
            )
        ).aggregate(
            media_renda=Avg('valor_renda')
        )['media_renda'] or Decimal('0.00')
        
        estatisticas = {
            'total_inscricoes': total_inscricoes,
            'media_idade': round(Decimal(str(media_idade)), 2),
            'media_renda': round(media_renda, 2)
        }
        
        serializer = EstatisticasSerializer(estatisticas)
        return Response(serializer.data)