from rest_framework import serializers
from .models import Curso, Polo, Candidato, Inscricao, Pais, Cidade, HistoricoEducacional, UsuarioAdmin, Tela, InscricaoLog
from drf_extra_fields.fields import Base64ImageField
import base64
import os
from django.core.files.base import ContentFile


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = '__all__'
        
class PoloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Polo
        fields = '__all__'
        
class CandidatoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Candidato
        fields = '__all__'
        extra_fields = ['anexo_cpf_base64', 'anexo_rg_base64']

    def to_internal_value(self, data):
        # Converte a sigla da nacionalidade em PK antes de validar
        nacionalidade_sigla = data.get('nacionalidade')
        if nacionalidade_sigla:
            try:
                pais_instance = Pais.objects.get(sigla=nacionalidade_sigla)
                data['nacionalidade'] = pais_instance.pk
            except Pais.DoesNotExist:
                raise serializers.ValidationError({"nacionalidade": "Pais com essa sigla não existe."})

        # Verifica e converte o ID do polo em PK
        polo_sigla = data.get('polo_ofertante')
        if polo_sigla:
            try:
                polo_instance = Polo.objects.get(nome=polo_sigla)
                data['polo_ofertante'] = polo_instance.pk
            except Polo.DoesNotExist:
                raise serializers.ValidationError({"polo_ofertante": "Polo com esse nome não existe."})

        # Função auxiliar para processar anexos base64
        def process_base64_file(base64_data, field_name):
            if base64_data and isinstance(base64_data, str) and base64_data.startswith('data:'):
                try:
                    format, imgstr = base64_data.split(';base64,')
                    ext = format.split('/')[-1]
                    file_name = f"{field_name}_{data.get('cpf', 'unknown')}.{ext}"
                    file = ContentFile(base64.b64decode(imgstr), name=file_name)
                    return file
                except Exception:
                    # Se houver qualquer erro no processamento, retornamos None
                    return None
            return None

        # Processar anexo_cpf (base64)
        anexo_cpf = process_base64_file(data.get('anexo_cpf'), 'anexo_cpf')
        if anexo_cpf:
            data['anexo_cpf'] = anexo_cpf
        elif 'anexo_cpf' in data:
            del data['anexo_cpf']  # Remove o campo se não for um base64 válido

        # Processar anexo_rg (base64)
        anexo_rg = process_base64_file(data.get('anexo_rg'), 'anexo_rg')
        if anexo_rg:
            data['anexo_rg'] = anexo_rg
        elif 'anexo_rg' in data:
            del data['anexo_rg']  # Remove o campo se não for um base64 válido

        return super().to_internal_value(data)

class PaisSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pais
        fields = '__all__'
        
class CidadeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cidade
        fields = '__all__'

class InscricaoSerializer(serializers.ModelSerializer):
    candidato = CandidatoSerializer()  # Inclui o serializador de Candidato
    
    class Meta:
        model = Inscricao
        fields = '__all__'
        
    # Torna o campo 'hash' opcional (não exigido no POST)
    hash = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    curso = serializers.CharField(required=False, allow_blank=True)
    data_criacao = serializers.CharField(required=False, allow_blank=True)
    data_modificacao = serializers.CharField(required=False, allow_blank=True)

class HistoricoEducacionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricoEducacional
        fields = '__all__'
        extra_fields = ['anexo_historico_escolar_base64']
        extra_kwargs = {'candidato': {'required': False}}

    def to_internal_value(self, data):
        # Função auxiliar para processar anexos base64
        def process_base64_file(base64_data, field_name):
            if base64_data and isinstance(base64_data, str) and base64_data.startswith('data:'):
                try:
                    format, imgstr = base64_data.split(';base64,')
                    ext = format.split('/')[-1]
                    file_name = f"{field_name}_{data.get('id', 'unknown')}.{ext}"
                    file = ContentFile(base64.b64decode(imgstr), name=file_name)
                    return file
                except Exception:
                    # Se houver qualquer erro no processamento, retornamos None
                    return None
            return None

        # Processar anexo_historico_escolar (base64)
        anexo_historico_escolar = process_base64_file(data.get('anexo_historico_escolar'), 'anexo_historico_escolar')
        if anexo_historico_escolar:
            data['anexo_historico_escolar'] = anexo_historico_escolar
        elif 'anexo_historico_escolar' in data:
            del data['anexo_historico_escolar']  # Remove o campo se não for um base64 válido

        return super().to_internal_value(data)

class UsuarioAdminRegistroSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioAdmin
        fields = ('username', 'email', 'password', 'nome_completo')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = UsuarioAdmin.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']
        )
        user.nome_completo = validated_data.get('nome_completo', '')
        user.save()
        return user

class UsuarioAdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class TelaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tela
        fields = ('id', 'nome', 'descricao', 'rota')

class UsuarioAdminUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(required=False, write_only=True)
    telas = TelaSerializer(many=True, read_only=True)
    
    class Meta:
        model = UsuarioAdmin
        fields = ('id', 'email', 'password', 'nome_completo', 'ativo', 'telas', 'username')
        read_only_fields = ('id',)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if password:
            instance.set_password(password)
            
        instance.save()
        return instance
    
class UsuarioAdminListSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsuarioAdmin
        fields = ('id', 'username', 'email', 'nome_completo', 'ativo')

class InscricaoLogSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    usuario_nome = serializers.CharField(source='usuario.nome_completo', read_only=True)

    class Meta:
        model = InscricaoLog
        fields = ['id', 'inscricao', 'status', 'status_display', 'data_registro', 'observacoes', 'usuario', 'usuario_nome']