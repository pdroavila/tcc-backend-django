# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `# managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
import hashlib
import time
import random
import string
import os
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone
from datetime import timedelta
import uuid
from django.core.validators import MinValueValidator

# Função para gerar um nome único baseado no nome do arquivo e informações adicionais
def generate_hashed_filename(filename):
    # Gera um salt aleatório
    salt = ''.join(random.choices(string.ascii_letters + string.digits, k=16))

    # Cria um hash SHA-256 usando o nome do arquivo, um salt e um timestamp para garantir unicidade
    unique_data = filename + salt + str(time.time())
    hash_object = hashlib.sha256(unique_data.encode('utf-8'))
    hash_filename = hash_object.hexdigest()

    # Recupera a extensão original do arquivo
    file_extension = os.path.splitext(filename)[1]

    # Nome final do arquivo (hash + extensão)
    return f"{hash_filename}{file_extension}"

# Função de localização do arquivo que usa o hash para nomear
def file_location(instance, filename):
    # Gera o nome do arquivo usando o hash
    return generate_hashed_filename(filename)

class Candidato(models.Model):
    id = models.BigAutoField(primary_key=True)
    email = models.CharField(max_length=255)
    nome_completo = models.CharField(max_length=255)
    nome_social = models.CharField(max_length=255, blank=True, null=True)
    nome_mae = models.CharField(max_length=255)
    cpf = models.CharField(max_length=50)
    registro_geral = models.CharField(max_length=50)
    anexo_cpf = models.ImageField(upload_to=file_location, null=False, blank=True)
    anexo_rg = models.ImageField(upload_to=file_location, null=False, blank=True)
    validacao_anexo_cpf = models.PositiveSmallIntegerField(default=0)
    validacao_anexo_rg = models.PositiveSmallIntegerField(default=0)
    nacionalidade = models.ForeignKey('Pais', models.DO_NOTHING, db_column='nacionalidade')
    naturalidade = models.ForeignKey('Cidade', models.DO_NOTHING, db_column='naturalidade')
    data_nascimento = models.DateField()
    telefone_celular = models.CharField(max_length=11)
    polo_ofertante = models.ForeignKey('Polo', models.DO_NOTHING, db_column='polo_ofertante')
    genero = models.IntegerField()
    estado_civil = models.IntegerField()
    portador_necessidades_especiais = models.IntegerField()
    necessidade_especial = models.CharField(max_length=255, blank=True, null=True)
    renda_per_capita = models.IntegerField()
    etnia = models.IntegerField()
    cpf_cedula_estrangeira = models.IntegerField()
    rg_cedula_estrangeira = models.IntegerField()
    

    class Meta:
        # managed = False
        db_table = 'candidato'


class Cidade(models.Model):
    nome = models.CharField(max_length=120, blank=True, null=True)
    ibge = models.IntegerField(blank=True, null=True)
    uf = models.ForeignKey('Estado', models.DO_NOTHING, db_column='uf', blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'cidade'
        db_table_comment = 'Municipios das Unidades Federativas'


class Curso(models.Model):
    nome = models.CharField(max_length=255)
    descricao = models.CharField(max_length=255, blank=True, null=True)
    prazo_inscricoes = models.DateTimeField()
    carga_horaria = models.DecimalField(
        max_digits=5,        # Total de dígitos (incluindo as casas decimais)
        decimal_places=2,    # Número de casas decimais
        validators=[MinValueValidator(0)],  # Garante que a carga horária seja não negativa
    )
    requisitos = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'curso'


class CursoPolo(models.Model):
    curso = models.ForeignKey('Curso', models.DO_NOTHING)
    polo = models.ForeignKey('Polo', models.DO_NOTHING)

    class Meta:
        # managed = False
        db_table = 'curso_polo'
        unique_together = (('curso', 'polo'),)


class Endereco(models.Model):
    id = models.BigAutoField(primary_key=True)
    candidato = models.ForeignKey(Candidato, models.DO_NOTHING)
    area = models.IntegerField()
    cep = models.CharField(max_length=8)
    estado = models.CharField(max_length=50)
    cidade = models.CharField(max_length=100)
    cidade_id = models.ForeignKey(Cidade, models.DO_NOTHING, db_column='cidade_id')  # Field renamed because of name conflict.
    bairro = models.CharField(max_length=100)
    logradouro = models.CharField(max_length=255)
    numero = models.CharField(max_length=10)
    complemento = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'endereco'


class Estado(models.Model):
    id = models.IntegerField(primary_key=True)
    nome = models.CharField(max_length=75, blank=True, null=True)
    uf = models.CharField(max_length=2, blank=True, null=True)
    ibge = models.IntegerField(blank=True, null=True)
    pais = models.IntegerField(blank=True, null=True)
    ddd = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'estado'
        db_table_comment = 'Unidades Federativas'

class HistoricoEducacional(models.Model):
    id = models.BigAutoField(primary_key=True)
    candidato = models.ForeignKey(Candidato, models.DO_NOTHING)
    tipo_escola = models.IntegerField()
    nivel_escolaridade = models.IntegerField()
    anexo_historico_escolar = models.ImageField(upload_to=file_location, null=False, blank=True)

    class Meta:
        # managed = False
        db_table = 'historico_educacional'


class Inscricao(models.Model):
    id = models.BigAutoField(primary_key=True)
    candidato = models.ForeignKey(Candidato, models.DO_NOTHING)
    curso = models.ForeignKey(Curso, models.DO_NOTHING)
    hash = models.CharField(max_length=128)
    status = models.IntegerField()
    data_criacao = models.DateTimeField()
    data_modificacao = models.DateTimeField()

    class Meta:
        # managed = False
        db_table = 'inscricao'


class Pais(models.Model):
    id = models.IntegerField(primary_key=True)
    nome = models.CharField(max_length=60, blank=True, null=True)
    nome_pt = models.CharField(max_length=60, blank=True, null=True)
    sigla = models.CharField(max_length=2, blank=True, null=True)
    bacen = models.IntegerField(blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'pais'
        db_table_comment = 'PaÝses e Naþ§es'

class Polo(models.Model):
    nome = models.CharField(max_length=255)
    logradouro = models.CharField(max_length=255)
    numero = models.IntegerField()
    bairro = models.CharField(max_length=255)
    cidade = models.ForeignKey(Cidade, models.DO_NOTHING, blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'polo'


class UsuarioAdminManager(BaseUserManager):
    def create_user(self, username, email, password=None):
        if not email:
            raise ValueError('Usuários devem ter um endereço de email')
        user = self.model(
            username=username,
            email=self.normalize_email(email),
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

class UsuarioAdmin(AbstractBaseUser):
    id = models.BigAutoField(primary_key=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    nome_completo = models.CharField(max_length=255)
    ativo = models.BooleanField(default=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_modificacao = models.DateTimeField(auto_now=True)
    token_recuperacao_senha = models.CharField(max_length=255, blank=True, null=True)
    token_expira_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'usuario_admin'

    def gerar_token_recuperacao_senha(self):
        self.token_recuperacao_senha = str(uuid.uuid4())
        self.token_expira_em = timezone.now() + timedelta(minutes=10)
        self.save()

    objects = UsuarioAdminManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def __str__(self):
        return self.email

class Tela(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    descricao = models.CharField(max_length=255)
    rota = models.CharField(max_length=255, unique=True)
    id = models.BigAutoField(primary_key=True)

    class Meta:
        db_table = 'tela'

class UsuarioTela(models.Model):
    usuario = models.ForeignKey(UsuarioAdmin, on_delete=models.CASCADE)
    tela = models.ForeignKey(Tela, on_delete=models.CASCADE)
    id = models.BigAutoField(primary_key=True)

    class Meta:
        db_table = 'usuario_tela'
        unique_together = ('usuario', 'tela')

class InscricaoLog(models.Model):
    STATUS_CHOICES = (
        (0, 'Pendente'),
        (1, 'Aprovado'),
        (2, 'Rejeitado'),
    )

    inscricao = models.ForeignKey(Inscricao, on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES, default=0)
    data_registro = models.DateTimeField()
    observacoes = models.TextField(null=True, blank=True)
    usuario = models.ForeignKey(UsuarioAdmin, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        db_table = 'inscricao_log'