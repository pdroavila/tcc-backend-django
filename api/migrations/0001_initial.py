# Generated by Django 5.0.4 on 2024-11-06 00:54

import api.models
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='UsuarioAdmin',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('username', models.CharField(max_length=50, unique=True)),
                ('password', models.CharField(max_length=255)),
                ('email', models.EmailField(max_length=255, unique=True)),
                ('nome_completo', models.CharField(max_length=255)),
                ('ativo', models.BooleanField(default=True)),
                ('data_criacao', models.DateTimeField(auto_now_add=True)),
                ('data_modificacao', models.DateTimeField(auto_now=True)),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now)),
                ('token_recuperacao_senha', models.CharField(blank=True, max_length=255, null=True)),
                ('token_expira_em', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'usuario_admin',
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
            },
        ),
        migrations.CreateModel(
            name='Tela',
            fields=[
                ('nome', models.CharField(max_length=255, unique=True)),
                ('descricao', models.CharField(max_length=255)),
                ('rota', models.CharField(max_length=255, unique=True)),
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
            ],
            options={
                'db_table': 'tela',
            },
        ),
        migrations.CreateModel(
            name='Candidato',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('email', models.CharField(max_length=255)),
                ('nome_completo', models.CharField(max_length=255)),
                ('nome_social', models.CharField(blank=True, max_length=255, null=True)),
                ('nome_mae', models.CharField(max_length=255)),
                ('cpf', models.CharField(max_length=50)),
                ('registro_geral', models.CharField(max_length=50)),
                ('anexo_cpf', models.ImageField(blank=True, upload_to=api.models.file_location)),
                ('anexo_rg', models.ImageField(blank=True, upload_to=api.models.file_location)),
                ('data_nascimento', models.DateField()),
                ('telefone_celular', models.CharField(max_length=11)),
                ('genero', models.IntegerField()),
                ('estado_civil', models.IntegerField()),
                ('portador_necessidades_especiais', models.IntegerField()),
                ('necessidade_especial', models.CharField(blank=True, max_length=255, null=True)),
                ('renda_per_capita', models.IntegerField()),
                ('etnia', models.IntegerField()),
                ('cpf_cedula_estrangeira', models.IntegerField()),
                ('rg_cedula_estrangeira', models.IntegerField()),
                ('naturalidade', models.ForeignKey(db_column='naturalidade', on_delete=django.db.models.deletion.DO_NOTHING, to='api.cidade')),
                ('nacionalidade', models.ForeignKey(db_column='nacionalidade', on_delete=django.db.models.deletion.DO_NOTHING, to='api.pais')),
            ],
            options={
                'db_table': 'candidato',
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
                ('candidato', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api.candidato')),
                ('cidade_id', models.ForeignKey(db_column='cidade_id', on_delete=django.db.models.deletion.DO_NOTHING, to='api.cidade')),
            ],
            options={
                'db_table': 'endereco',
            },
        ),
        migrations.AddField(
            model_name='cidade',
            name='uf',
            field=models.ForeignKey(blank=True, db_column='uf', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='api.estado'),
        ),
        migrations.CreateModel(
            name='HistoricoEducacional',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('tipo_escola', models.IntegerField()),
                ('nivel_escolaridade', models.IntegerField()),
                ('anexo_historico_escolar', models.ImageField(blank=True, upload_to=api.models.file_location)),
                ('candidato', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api.candidato')),
            ],
            options={
                'db_table': 'historico_educacional',
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
                ('candidato', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api.candidato')),
                ('curso', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api.curso')),
            ],
            options={
                'db_table': 'inscricao',
            },
        ),
        migrations.CreateModel(
            name='InscricaoLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.PositiveSmallIntegerField(choices=[(0, 'Pendente'), (1, 'Aprovado'), (2, 'Rejeitado')], default=0)),
                ('data_registro', models.DateTimeField()),
                ('observacoes', models.TextField(blank=True, null=True)),
                ('inscricao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.inscricao')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'inscricao_log',
            },
        ),
        migrations.CreateModel(
            name='Polo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('logradouro', models.CharField(max_length=255)),
                ('numero', models.IntegerField()),
                ('bairro', models.CharField(max_length=255)),
                ('cidade', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='api.cidade')),
            ],
            options={
                'db_table': 'polo',
            },
        ),
        migrations.AddField(
            model_name='candidato',
            name='polo_ofertante',
            field=models.ForeignKey(db_column='polo_ofertante', on_delete=django.db.models.deletion.DO_NOTHING, to='api.polo'),
        ),
        migrations.CreateModel(
            name='UsuarioTela',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('tela', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='api.tela')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'usuario_tela',
                'unique_together': {('usuario', 'tela')},
            },
        ),
        migrations.CreateModel(
            name='UsuarioAdminFuncao',
            fields=[
                ('usuario_admin', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('funcao', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api.funcao')),
            ],
            options={
                'db_table': 'usuario_admin_funcao',
                'unique_together': {('usuario_admin', 'funcao')},
            },
        ),
        migrations.CreateModel(
            name='CursoPolo',
            fields=[
                ('curso', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to='api.curso')),
                ('polo', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api.polo')),
            ],
            options={
                'db_table': 'curso_polo',
                'unique_together': {('curso', 'polo')},
            },
        ),
        migrations.CreateModel(
            name='FuncaoPermissao',
            fields=[
                ('funcao', models.OneToOneField(on_delete=django.db.models.deletion.DO_NOTHING, primary_key=True, serialize=False, to='api.funcao')),
                ('permissao', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='api.permissao')),
            ],
            options={
                'db_table': 'funcao_permissao',
                'unique_together': {('funcao', 'permissao')},
            },
        ),
    ]
