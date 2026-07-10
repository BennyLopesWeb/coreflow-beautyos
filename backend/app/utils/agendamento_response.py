"""
Helpers para serializar agendamentos com dados do modelo reservado.
"""
from app.models.agendamento import Agendamento
from app.schemas.agendamento import AgendamentoResponse
from app.schemas.service_image import _label_modelo
from app.utils.service_image_precos import resolver_precos_imagem


def agendamento_para_response(ag: Agendamento) -> AgendamentoResponse:
    """
    Converte Agendamento em AgendamentoResponse com valores do modelo.

    Prioriza valores persistidos na reserva (snapshot); recalcula só se ausentes.

    Args:
        ag: Instância do agendamento.

    Returns:
        AgendamentoResponse enriquecido com dados do modelo escolhido.
    """
    imagem_url = None
    imagem_label = None
    modelo_nome = None
    valor_total_reserva = ag.valor_total
    valor_sinal_reserva = ag.valor_sinal
    valor_restante_reserva = ag.valor_restante
    duracao_reserva_minutos = None

    if ag.service_image:
        imagem_url = ag.service_image.url
        modelo_nome = _label_modelo(ag.service_image)
        imagem_label = modelo_nome

        if valor_total_reserva is None and ag.tranca:
            try:
                precos = resolver_precos_imagem(ag.service_image, ag.tranca)
                valor_total_reserva = precos["valor_total"]
                valor_sinal_reserva = precos["valor_sinal"]
                valor_restante_reserva = precos["valor_restante"]
                duracao_reserva_minutos = precos["duracao_minutos"]
            except ValueError:
                pass
        elif ag.tranca:
            try:
                duracao_reserva_minutos = resolver_precos_imagem(
                    ag.service_image, ag.tranca
                )["duracao_minutos"]
            except ValueError:
                duracao_reserva_minutos = ag.service_image.duracao_minutos

    return AgendamentoResponse(
        id=ag.id,
        cliente_id=ag.cliente_id,
        tranca_id=ag.tranca_id,
        data_hora=ag.data_hora,
        observacoes=ag.observacoes,
        sinal_pago=ag.sinal_pago,
        comprovante_url=ag.comprovante_url,
        service_image_id=ag.service_image_id,
        modelo_nome=modelo_nome,
        imagem_url=imagem_url,
        imagem_label=imagem_label,
        valor_total_reserva=valor_total_reserva,
        valor_sinal_reserva=valor_sinal_reserva,
        valor_restante_reserva=valor_restante_reserva,
        duracao_reserva_minutos=duracao_reserva_minutos,
        status_pagamento=ag.status_pagamento,
        status=ag.status,
        created_at=ag.created_at,
        updated_at=ag.updated_at,
    )
