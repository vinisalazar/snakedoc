from pathlib import Path
from typing import Set

from docutils import nodes
from docutils.nodes import Node
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.errors import SphinxError
from sphinx.locale import _


class SmkLinkcodeError(SphinxError):
    category = "linkcode error"


def smk_linkcode_resolve(domain, info):
    if len(info["source"]) == 0:
        return ""

    parts = info["source"].split(":")
    if len(parts) == 2:
        filename, lineno = parts
    elif len(parts) == 1:
        filename = parts[0]
        lineno = None
    try:
        filename = str(Path(filename).relative_to(Path.cwd().parent))
    except ValueError as err:
        raise ValueError(
            f"Rule lists {filename} as it's source, but this is not relative to {Path.cwd().parent}"
        ) from err

    return f"{info['baseurl']}{filename}{info['linesep']+lineno if lineno else ''}"


def doctree_read(app: Sphinx, doctree: Node) -> None:
    env = app.builder.env

    resolve_target = getattr(env.config, "smk_linkcode_resolve", None)
    if env.config.smk_linkcode_resolve is None:
        resolve_target = smk_linkcode_resolve
    baseurl_target = getattr(env.config, "smk_linkcode_baseurl", "")
    linesep_target = getattr(env.config, "smk_linkcode_linesep", "#L")

    domain_keys = {
        "smk": ["source"],
    }

    for objnode in list(doctree.findall(addnodes.desc)):
        domain = objnode.get("domain")
        uris: Set[str] = set()
        for signode in objnode:
            if not isinstance(signode, addnodes.desc_signature):
                continue

            # Convert signode to a specified format
            info = {}
            for key in domain_keys.get(domain, []):
                value = signode.get(key)
                if not value:
                    value = ""
                info[key] = value
            if not info:
                continue

            # Call user code to resolve the link
            info["baseurl"] = baseurl_target
            info["linesep"] = linesep_target
            uri = resolve_target(domain, info)
            if not uri:
                # no source
                continue

            if uri in uris or not uri:
                # only one link per name, please
                continue
            uris.add(uri)

            inline = nodes.inline("", _("[source]"), classes=["viewcode-link"])
            onlynode = addnodes.only(expr="html")
            onlynode += nodes.reference("", "", inline, internal=False, refuri=uri)
            signode += onlynode
