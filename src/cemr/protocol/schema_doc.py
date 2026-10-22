"""Generate the message-schema tables of docs/04-protocols-and-messages.md from the payload dataclasses.

    python -m cemr.protocol.schema_doc --write docs/04-protocols-and-messages.md

Only the text between the GENERATED markers is replaced, so the hand-written parts stay intact.
"""

import argparse
import inspect
from pathlib import Path

from . import messages
from .ontology import PT_NAMES, Protocol

BEGIN = "<!-- BEGIN GENERATED: message schemas -->"
END = "<!-- END GENERATED: message schemas -->"


def _type_name(cls, name: str) -> str:
    annotation = cls.__annotations__[name]
    return annotation if isinstance(annotation, str) else getattr(annotation, "__name__", str(annotation))


def _cell(text: str) -> str:
    """Escape pipes so they do not split markdown table cells (also needed inside code spans)."""
    return text.replace("|", "\\|")


def render() -> str:
    by_protocol: dict[Protocol, list[type]] = {}
    for cls in messages.all_payloads():
        by_protocol.setdefault(cls.PROTOCOL, []).append(cls)
    out = []
    for protocol in Protocol:
        out.append(f"### {protocol.code} · {protocol.value.split('-', 1)[1]}\n")
        for cls in by_protocol[protocol]:
            perfs = ", ".join(f"`{p}`" for p in cls.PERFORMATIVES)
            scope = " · local (same agent or device)" if cls.LOCAL else ""
            out.append(f"**`{cls.__name__}`** · {perfs}{scope}\n")
            docstring = inspect.getdoc(cls)
            if docstring and not docstring.startswith(cls.__name__ + "("):
                out.append(" ".join(docstring.split()) + "\n")
            out.append("| Field | Type | Description |\n|---|---|---|")
            for name, _, text in messages.field_docs(cls):
                out.append(f"| `{name}` | `{_cell(_type_name(cls, name))}` | {_cell(text)} |")
            out.append("")
    out.append("### Correspondence with the Portuguese identifiers of the analysis\n")
    out.append("| Analysis (PT) | Code (EN) |\n|---|---|")
    for pt, en in PT_NAMES.items():
        out.append(f"| `{pt}` | `{en}` |")
    return "\n".join(out) + "\n"


def write(path: Path) -> None:
    text = path.read_text()
    start, end = text.index(BEGIN) + len(BEGIN), text.index(END)
    path.write_text(text[:start] + "\n\n" + render() + "\n" + text[end:])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", type=Path, help="markdown file with the GENERATED markers")
    args = parser.parse_args()
    if args.write:
        write(args.write)
    else:
        print(render())
