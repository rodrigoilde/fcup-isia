"""Diretório público dos nomes e JID dos agentes.

Os nomes não têm identidade civil: são os pseudónimos estáveis da decisão D7 (por exemplo "vol7",
"dev12"). O servidor XMPP corre em localhost, por isso os JID têm a forma `nome@localhost`.
"""

DOMAIN = "localhost"
KIND_BY_PREFIX = {"hub": "hub", "ems": "ems", "vol": "volunteer", "dev": "device", "wit": "bystander"}


class Directory:
    """Nomes dos agentes de um run.

    Attributes:
        hub_ids (list[int]): Ids dos hubs (um por célula).
        ems_names (list[str]): Nomes das ambulâncias.
    """

    def __init__(self, hubs=(), ems_units: int = 0):
        self.hub_ids = sorted(hubs)
        self.ems_names = [self.ems(i) for i in range(ems_units)]

    @staticmethod
    def jid(name: str) -> str:
        """JID de um agente a partir do seu nome."""
        return f"{name}@{DOMAIN}"

    @staticmethod
    def name_of(jid) -> str:
        """Nome de um agente a partir do seu JID (com ou sem recurso)."""
        return str(jid).split("@")[0]

    @staticmethod
    def kind_of(name: str) -> str:
        """Tipo de agente ("hub", "ems", "volunteer", "device", "bystander") pelo prefixo do nome."""
        for prefix, kind in KIND_BY_PREFIX.items():
            if name.startswith(prefix):
                return kind
        return "unknown"

    @staticmethod
    def hub(hub_id: int) -> str:
        """Nome do hub da célula `hub_id`."""
        return f"hub{hub_id}"

    @staticmethod
    def hub_id(name: str) -> int:
        """Id da célula de um hub a partir do nome."""
        return int(name[3:])

    @staticmethod
    def ems(i: int) -> str:
        """Nome da ambulância i."""
        return f"ems{i}"

    @staticmethod
    def volunteer(i: int) -> str:
        """Nome do voluntário i."""
        return f"vol{i}"

    @staticmethod
    def device(i: int) -> str:
        """Nome do dispositivo i."""
        return f"dev{i}"

    @staticmethod
    def bystander(i: int) -> str:
        """Nome do cidadão (potencial testemunha) i."""
        return f"wit{i}"
