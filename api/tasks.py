from django.db import transaction
from django.utils import timezone
from .models import Inscricao, InscricaoLog
from zoneinfo import ZoneInfo

def update_expired_inscricoes():
    try:
        with transaction.atomic():
            # Converter o tempo atual para UTC-3
            now = timezone.now().astimezone(ZoneInfo("America/Sao_Paulo"))
            
            # Identificar inscrições expiradas
            inscricoes_expiradas = Inscricao.objects.filter(
                status='0',
                curso__prazo_validacao__lt=now
            )

            # Criar logs antes do update
            logs = [
                InscricaoLog(
                    inscricao=inscricao,
                    status='3',
                    observacoes='Inscrição aprovada automaticamente por prazo expirado',
                    usuario_id=1,
                    data_registro = (timezone.now())
                )
                for inscricao in inscricoes_expiradas
            ]

            # Criar logs
            if logs:
                InscricaoLog.objects.bulk_create(logs)

            # Atualizar status das inscrições
            inscricoes_expiradas.update(
                status='3',
                data_modificacao=now
            )

            print(f"Atualizadas {len(logs)} inscrições")
    except Exception as e:
        print(f"Erro ao atualizar inscrições: {str(e)}")