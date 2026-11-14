"""Moteur de templates minimal, deterministe et sans evaluation de code.

Syntaxe :
  {{ a.b }}                          valeur (variable absente = erreur)
  {{#if a.b}} ... {{else}} ... {{/if}}   condition sur la veracite
  {{#each a.list}} ... {{/each}}      boucle ; {{ this }} / {{ this.champ }}
  {{! commentaire }}                  ignore

Les valeurs inserees ne sont jamais reinterpretees : une description contenant
"{{ ... }}" est recopiee telle quelle.
"""
import re

TOKEN = re.compile(r"\{\{(!.*?|[^{}]*)\}\}", re.S)
PATH = re.compile(r"^(this|[A-Za-z_][A-Za-z0-9_]*)(\.[A-Za-z0-9_]+)*$")
BLOCKS = {"if", "each"}


class TemplateError(ValueError):
    pass


def _parse_tag(raw):
    raw = raw.strip()
    if raw.startswith("!"):
        return ("comment", None)
    if raw == "else":
        return ("else", None)
    if raw[:1] in "#/":
        kind, _, arg = raw[1:].partition(" ")
        if kind not in BLOCKS:
            raise TemplateError("Bloc inconnu : " + kind)
        arg = arg.strip()
        if raw[0] == "/":
            if arg:
                raise TemplateError("Fermeture invalide : " + raw)
            return ("close", kind)
        if not PATH.fullmatch(arg):
            raise TemplateError("Expression invalide : " + arg)
        return ("open", (kind, arg))
    if not PATH.fullmatch(raw):
        raise TemplateError("Expression invalide : %r" % raw)
    return ("var", raw)


def _standalone(source, start, end, position):
    """Etend une balise de bloc seule sur sa ligne a la ligne entiere."""
    line_start = source.rfind("\n", 0, start) + 1
    line_end = source.find("\n", end)
    line_end = len(source) if line_end < 0 else line_end + 1
    if line_start >= position and not source[line_start:start].strip() and not source[end:line_end].strip():
        return line_start, line_end
    return start, end


def compile_template(source):
    """Retourne l'arbre syntaxique d'un template (liste de noeuds)."""
    root = []
    stack = [("root", None, root, None)]  # (type, arg, corps courant, corps si-vrai)
    position = 0
    for match in TOKEN.finditer(source):
        kind, value = _parse_tag(match.group(1))
        start, end = match.start(), match.end()
        if kind != "var":
            start, end = _standalone(source, start, end, position)
        stack[-1][2].append(("text", source[position:start]))
        position = end
        if kind == "var":
            stack[-1][2].append(("var", value))
        elif kind == "open":
            body = []
            stack.append((value[0], value[1], body, None))
        elif kind == "else":
            block, arg, body, _ = stack[-1]
            if block != "if" or stack[-1][3] is not None:
                raise TemplateError("else hors d'un bloc if")
            stack[-1] = (block, arg, [], body)
        elif kind == "close":
            block, arg, body, true_body = stack.pop()
            if block != value:
                raise TemplateError("Fermeture /%s inattendue" % value)
            if block == "if":
                node = ("if", arg, true_body if true_body is not None else body, body if true_body is not None else [])
            else:
                node = ("each", arg, body)
            stack[-1][2].append(node)
    if len(stack) != 1:
        raise TemplateError("Bloc non ferme : " + stack[-1][0])
    root.append(("text", source[position:]))
    return root


def _lookup(path, scopes):
    head, *rest = path.split(".")
    for scope in reversed(scopes):
        if head in scope:
            value = scope[head]
            break
    else:
        raise TemplateError("Variable inconnue : " + path)
    for part in rest:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            raise TemplateError("Variable inconnue : " + path)
    return value


def _render(nodes, scopes, out):
    for node in nodes:
        kind = node[0]
        if kind == "text":
            out.append(node[1])
        elif kind == "var":
            value = _lookup(node[1], scopes)
            if isinstance(value, (dict, list, tuple)):
                raise TemplateError("Valeur non affichable : " + node[1])
            out.append("" if value is None else str(value))
        elif kind == "if":
            _render(node[2] if _lookup(node[1], scopes) else node[3], scopes, out)
        else:
            items = _lookup(node[1], scopes)
            if not isinstance(items, (list, tuple)):
                raise TemplateError("Liste attendue : " + node[1])
            for item in items:
                _render(node[2], scopes + [{"this": item}], out)


def render(source, context):
    out = []
    _render(compile_template(source), [dict(context)], out)
    return _tidy("".join(out))


def _tidy(text):
    """Supprime les espaces de fin et les lignes vides multiples."""
    lines = [line.rstrip() for line in text.splitlines()]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return text.strip("\n") + "\n"
