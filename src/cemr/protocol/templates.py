"""Template do SPADE que nunca coincide com nenhuma mensagem.

O SPADE entrega cada mensagem a todos os behaviours cujo template coincide, e um behaviour sem
template coincide com tudo. Por isso cada agente tem um único router sem template, que encaminha
as mensagens de forma explícita, e os outros behaviours levam NEVER para não receberem cópias.
"""

from spade.template import BaseTemplate


class NeverTemplate(BaseTemplate):
    """Template que rejeita todas as mensagens."""

    def match(self, message) -> bool:
        return False


NEVER = NeverTemplate()
