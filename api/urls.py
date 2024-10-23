from django.urls import path
from .views import CursoListView
from .views import PolosByCursoView, PostInscricao, GetSearchCidade, CandidatoPorHashView, InscricaoDetailView, MediaImageView, UpdateInscricao, RegistroView, LoginView, VerificarTokenView, SolicitarRecuperacaoSenhaView, AlterarSenhaView, VerificarAcessoTela, GraficosView, PoloListView, CursoCreateView, CursoDetailView, CursoUpdateView
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('cursos/', CursoListView.as_view(), name='curso-list'),
    path('cursos/<int:curso_id>/polos/', PolosByCursoView.as_view(), name='polos-by-curso'),
    path('inscricao/', PostInscricao.as_view(), name='inscricao'),
    path('buscar-cidades/', GetSearchCidade.as_view(), name='buscar-cidades'),
    path('candidatos/<str:hash>/', CandidatoPorHashView.as_view(), name='candidato-por-hash'),
    path('inscricoes/<int:inscricao_id>/<str:hash>', InscricaoDetailView.as_view(), name='inscricao-detail'),
    path('media-image/<str:filename>/', MediaImageView.as_view(), name='media-image'),
    path('inscricao/alterar/', UpdateInscricao.as_view(), name='update-inscricao'),
    path('admin/registro/', RegistroView.as_view(), name='registro'),
    path('admin/login/', LoginView.as_view(), name='login'),
    path('admin/verificar-token/', VerificarTokenView.as_view(), name='verificar_token'),
    path('admin/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('admin/recuperar-senha/', SolicitarRecuperacaoSenhaView.as_view(), name='recuperar-senha'),
    path('admin/alterar-senha/', AlterarSenhaView.as_view(), name='alterar-senha'),
    path('admin/verificar-acesso/', VerificarAcessoTela.as_view(), name='verificar-acesso'),
    path('admin/graficos/', GraficosView.as_view(), name='graficos'),
    path('admin/curso-novo', CursoCreateView.as_view(), name='curso-novo'),
    path('polos/', PoloListView.as_view(), name='polo-list'),
    path('admin/cursos/<int:pk>/', CursoDetailView.as_view(), name='curso-detail'),
    path('admin/cursos/<int:pk>/update/', CursoUpdateView.as_view(), name='curso-update'),
]
