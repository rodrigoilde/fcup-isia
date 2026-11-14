"""Codificação das mensagens em JSON (o conteúdo FIPA-ACL, em língua "json").

O corpo leva um campo "type" com o nome da classe da mensagem, por isso a descodificação não
depende do envelope. As classes estão nos módulos `messages_*`, um por sub-organização; o envelope
(remetente, destinatário, thread, performativa, protocolo, ontologia, língua) é montado em
`agents/base.py`.
"""

import json
from dataclasses import asdict

from . import messages_assistance, messages_detection, messages_dispatch, messages_hubs, messages_response

MODULES = (messages_detection, messages_dispatch, messages_response, messages_assistance, messages_hubs)


def payload_classes() -> list[type]:
    """Todas as classes de mensagem, pela ordem dos protocolos."""
    classes = []
    for module in MODULES:
        for value in vars(module).values():
            if isinstance(value, type) and hasattr(value, "PROTOCOL") and value.__module__ == module.__name__:
                classes.append(value)
    return classes


PAYLOADS = {cls.__name__: cls for cls in payload_classes()}


def encode(payload) -> str:
    """Converte uma mensagem em JSON, com o nome da classe no campo "type"."""
    data = asdict(payload)
    data["type"] = type(payload).__name__
    return json.dumps(data, separators=(",", ":"))


def decode(body: str):
    """Reconstrói a mensagem a partir do JSON produzido por `encode`.

    Raises:
        KeyError: Se o campo "type" não corresponder a nenhuma mensagem conhecida.
    """
    data = json.loads(body)
    cls = PAYLOADS[data.pop("type")]
    return cls(**data)
