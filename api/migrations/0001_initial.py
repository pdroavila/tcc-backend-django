# Generated by Django 5.0.4 on 2024-09-14 17:39

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Candidato',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('email', models.CharField(max_length=255)),
                ('nome_completo', models.CharField(max_length=255)),
                ('nome_social', models.CharField(blank=True, max_length=255, null=True)),
                ('nome_mae', models.CharField(max_length=255)),
                ('cpf', models.CharField(max_length=50)),
                ('anexo_cpf', models.CharField(max_length=255)),
                ('registro_geral', models.CharField(max_length=50)),
                ('anexo_rg', models.CharField(max_length=255)),
                ('data_nascimento', models.DateField()),
                ('telefone_celular', models.CharField(max_length=11)),
                ('genero', models.IntegerField()),
                ('estado_civil', models.IntegerField()),
                ('portador_necessidades_especiais', models.IntegerField()),
                ('necessidade_especial', models.CharField(blank=True, max_length=255, null=True)),
                ('renda_per_capita', models.IntegerField()),
                ('etnia', models.IntegerField()),
            ],
            options={
                'db_table': 'candidato',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Cidade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(blank=True, max_length=120, null=True)),
                ('ibge', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'cidade',
                'db_table_comment': 'Municipios das Unidades Federativas',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Curso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('descricao', models.CharField(blank=True, max_length=255, null=True)),
                ('prazo_inscricoes', models.DateTimeField()),
            ],
            options={
                'db_table': 'curso',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Endereco',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('area', models.IntegerField()),
                ('cep', models.CharField(max_length=8)),
                ('estado', models.CharField(max_length=50)),
                ('cidade', models.CharField(max_length=100)),
                ('bairro', models.CharField(max_length=100)),
                ('logradouro', models.CharField(max_length=255)),
                ('numero', models.CharField(max_length=10)),
                ('complemento', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'endereco',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Estado',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('nome', models.CharField(blank=True, max_length=75, null=True)),
                ('uf', models.CharField(blank=True, max_length=2, null=True)),
                ('ibge', models.IntegerField(blank=True, null=True)),
                ('pais', models.IntegerField(blank=True, null=True)),
                ('ddd', models.CharField(blank=True, max_length=50, null=True)),
            ],
            options={
                'db_table': 'estado',
                'db_table_comment': 'Unidades Federativas',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Funcao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=50, unique=True)),
                ('descricao', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'funcao',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='HistoricoEducacional',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('tipo_escola', models.IntegerField()),
                ('nivel_escolaridade', models.IntegerField()),
                ('anexo_historico_escolar', models.CharField(max_length=255)),
            ],
            options={
                'db_table': 'historico_educacional',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Inscricao',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('hash', models.CharField(max_length=128)),
                ('status', models.IntegerField()),
                ('data_criacao', models.DateTimeField()),
                ('data_modificacao', models.DateTimeField()),
            ],
            options={
                'db_table': 'inscricao',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Pais',
            fields=[
                ('id', models.IntegerField(primary_key=True, serialize=False)),
                ('nome', models.CharField(blank=True, max_length=60, null=True)),
                ('nome_pt', models.CharField(blank=True, max_length=60, null=True)),
                ('sigla', models.CharField(blank=True, max_length=2, null=True)),
                ('bacen', models.IntegerField(blank=True, null=True)),
            ],
            options={
                'db_table': 'pais',
                'db_table_comment': 'PaÝses e Naþ§es',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Permissao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=50, unique=True)),
                ('descricao', models.CharField(blank=True, max_length=255, null=True)),
            ],
            options={
                'db_table': 'permissao',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='Polo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('logradouro', models.CharField(max_length=255)),
                ('numero', models.IntegerField()),
                ('bairro', models.IntegerField()),
            ],
            options={
                'db_table': 'polo',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='UsuarioAdmin',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=50, unique=True)),
                ('password', models.CharField(max_length=255)),
                ('email', models.CharField(max_length=255, unique=True)),
                ('nome_completo', models.CharField(max_length=255)),
                ('ativo', models.IntegerField(blank=True, null=True)),
                ('data_criacao', models.DateTimeField(blank=True, null=True)),
                ('data_modificacao', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'usuario_admin',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='CursoPolo',
            fields=[
                ('curso', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to='api.curso')),
            ],
            options={
                'db_table': 'curso_polo',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='FuncaoPermissao',
            fields=[
                ('funcao', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to='api.funcao')),
            ],
            options={
                'db_table': 'funcao_permissao',
                'managed': False,
            },
        ),
        migrations.CreateModel(
            name='UsuarioAdminFuncao',
            fields=[
                ('usuario_admin', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to='api.usuarioadmin')),
            ],
            options={
                'db_table': 'usuario_admin_funcao',
                'managed': False,
            },
        ),
    ]
