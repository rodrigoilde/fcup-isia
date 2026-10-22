"""Public directory of agent names and JIDs.

Names carry no civil identity: they are the stable pseudonyms of D7 (e.g. "vol7", "dev12").
The run prefix keeps parallel runs apart when they share one XMPP server.
"""

KIND_BY_PREFIX = {"hub": "hub", "ems": "ems", "vol": "volunteer", "dev": "device", "wit": "bystander"}


class Directory:
    def __init__(self, prefix: str, domain: str = "localhost", hubs=(), ems_units=0):
        self.prefix = prefix
        self.domain = domain
        self.hub_ids = sorted(hubs)
        self.ems_names = [self.ems(i) for i in range(ems_units)]

    def jid(self, name: str) -> str:
        return f"{self.prefix}-{name}@{self.domain}"

    def name_of(self, jid) -> str:
        local = str(jid).split("/")[0].split("@")[0]
        return local[len(self.prefix) + 1:] if local.startswith(self.prefix + "-") else local

    @staticmethod
    def kind_of(name: str) -> str:
        for prefix, kind in KIND_BY_PREFIX.items():
            if name.startswith(prefix):
                return kind
        return "unknown"

    @staticmethod
    def hub(hub_id: int) -> str:
        return f"hub{hub_id}"

    @staticmethod
    def hub_id(name: str) -> int:
        return int(name[3:])

    @staticmethod
    def ems(i: int) -> str:
        return f"ems{i}"

    @staticmethod
    def volunteer(i: int) -> str:
        return f"vol{i}"

    @staticmethod
    def device(i: int) -> str:
        return f"dev{i}"

    @staticmethod
    def bystander(i: int) -> str:
        return f"wit{i}"
