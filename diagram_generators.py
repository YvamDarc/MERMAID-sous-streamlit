"""Pure-Python generators that turn guided form data into Mermaid syntax."""

from __future__ import annotations

import math
import re
import unicodedata
from collections import defaultdict
from typing import Any


COLOR_STYLES = {
    "Bleu": ("#dbeafe", "#2563eb", "#172554"),
    "Vert": ("#dcfce7", "#16a34a", "#14532d"),
    "Orange": ("#ffedd5", "#ea580c", "#7c2d12"),
    "Rouge": ("#fee2e2", "#dc2626", "#7f1d1d"),
    "Violet": ("#f3e8ff", "#9333ea", "#581c87"),
    "Jaune": ("#fef9c3", "#ca8a04", "#713f12"),
    "Gris": ("#f1f5f9", "#64748b", "#1e293b"),
    "Blanc": ("#ffffff", "#94a3b8", "#0f172a"),
}


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        if isinstance(value, float) and math.isnan(value):
            return default
    except TypeError:
        pass
    return str(value).strip()


def _label(value: Any) -> str:
    """Return a Mermaid-safe label used inside double quotes."""
    value = _text(value)
    value = value.replace("\\", "\\\\").replace('"', "'")
    value = re.sub(r"[\r\n]+", " · ", value)
    return value or "Sans libellé"


def _plain(value: Any) -> str:
    """Return safe single-line text for syntaxes that do not accept quotes."""
    value = _label(value)
    value = value.replace(":", " – ").replace(";", ",")
    return value


def _identifier(value: Any, fallback: str = "element") -> str:
    value = _text(value, fallback)
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    ident = re.sub(r"[^A-Za-z0-9_]", "_", ascii_value)
    ident = re.sub(r"_+", "_", ident).strip("_") or fallback
    if ident[0].isdigit():
        ident = f"n_{ident}"
    return ident


def _records(project: dict[str, Any], table: str) -> list[dict[str, Any]]:
    rows = project.get("tables", {}).get(table, [])
    return [row for row in rows if isinstance(row, dict)]


def _build_id_map(
    rows: list[dict[str, Any]],
    field: str,
    warnings: list[str],
) -> tuple[dict[str, str], list[tuple[dict[str, Any], str]]]:
    mapping: dict[str, str] = {}
    prepared: list[tuple[dict[str, Any], str]] = []
    used: set[str] = set()

    for index, row in enumerate(rows, start=1):
        raw = _text(row.get(field))
        if not raw:
            continue
        if raw in mapping:
            warnings.append(f"Identifiant dupliqué ignoré : {raw}.")
            continue
        base = _identifier(raw, f"element_{index}")
        ident = base
        suffix = 2
        while ident in used:
            ident = f"{base}_{suffix}"
            suffix += 1
        if ident != base:
            warnings.append(
                f"Les identifiants proches de « {raw} » ont été différenciés automatiquement."
            )
        mapping[raw] = ident
        used.add(ident)
        prepared.append((row, ident))
    return mapping, prepared


def _node_declaration(ident: str, label: str, shape: str) -> str:
    shapes = {
        "Rectangle": f'{ident}["{label}"]',
        "Arrondi": f'{ident}("{label}")',
        "Stade": f'{ident}(["{label}"])',
        "Sous-processus": f'{ident}[["{label}"]]',
        "Base de données": f'{ident}[("{label}")]',
        "Cercle": f'{ident}(("{label}"))',
        "Décision": f'{ident}{{"{label}"}}',
        "Hexagone": f'{ident}{{{{"{label}"}}}}',
    }
    return shapes.get(shape, shapes["Rectangle"])


def generate_flowchart(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    settings = project.get("settings", {})
    direction = settings.get("direction", "TD")
    direction = direction if direction in {"TD", "TB", "BT", "LR", "RL"} else "TD"
    nodes = _records(project, "nodes")
    edges = _records(project, "edges")
    id_map, prepared = _build_id_map(nodes, "id", warnings)

    lines = [f"flowchart {direction}"]
    grouped: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    ungrouped: list[tuple[dict[str, Any], str]] = []
    for row, ident in prepared:
        group = _text(row.get("groupe"))
        (grouped[group] if group else ungrouped).append((row, ident))

    for row, ident in ungrouped:
        lines.append(
            f"    {_node_declaration(ident, _label(row.get('texte') or row.get('id')), _text(row.get('forme'), 'Rectangle'))}"
        )

    for group, group_nodes in grouped.items():
        group_id = f"grp_{_identifier(group)}"
        lines.append(f'    subgraph {group_id}["{_label(group)}"]')
        lines.append("        direction TB")
        for row, ident in group_nodes:
            declaration = _node_declaration(
                ident,
                _label(row.get("texte") or row.get("id")),
                _text(row.get("forme"), "Rectangle"),
            )
            lines.append(f"        {declaration}")
        lines.append("    end")

    edge_tokens = {
        "Flèche": ("-->", "-->|{label}|"),
        "Double flèche": ("<-->", "<-->|{label}|"),
        "Ligne": ("---", "---|{label}|"),
        "Pointillée": ("-.->", "-. {label} .->"),
        "Épaisse": ("==>", "==>|{label}|"),
    }
    for row in edges:
        source_raw = _text(row.get("source"))
        target_raw = _text(row.get("destination"))
        if not source_raw and not target_raw:
            continue
        if source_raw not in id_map or target_raw not in id_map:
            warnings.append(
                f"Connexion ignorée : {source_raw or '?'} → {target_raw or '?'} (bloc introuvable)."
            )
            continue
        style = _text(row.get("style"), "Flèche")
        plain_token, labelled_token = edge_tokens.get(style, edge_tokens["Flèche"])
        edge_label = _text(row.get("libellé"))
        token = labelled_token.format(label=_label(edge_label)) if edge_label else plain_token
        lines.append(f"    {id_map[source_raw]} {token} {id_map[target_raw]}")

    for row, ident in prepared:
        color_name = _text(row.get("couleur"), "Blanc")
        fill, stroke, text_color = COLOR_STYLES.get(color_name, COLOR_STYLES["Blanc"])
        lines.append(
            f"    style {ident} fill:{fill},stroke:{stroke},color:{text_color},stroke-width:2px"
        )

    if not prepared:
        lines.append('    vide["Ajoutez votre premier bloc dans le tableau"]')
        warnings.append("Le diagramme ne contient encore aucun bloc.")
    return "\n".join(lines), warnings


def generate_sequence(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    participants = _records(project, "participants")
    messages = _records(project, "messages")
    id_map, prepared = _build_id_map(participants, "id", warnings)
    lines = ["sequenceDiagram"]
    if project.get("settings", {}).get("autonumber", True):
        lines.append("    autonumber")

    for row, ident in prepared:
        keyword = "actor" if _text(row.get("type"), "Participant") == "Acteur" else "participant"
        lines.append(f'    {keyword} {ident} as {_label(row.get("nom") or row.get("id"))}')

    arrows = {
        "Message": "->>",
        "Réponse": "-->>",
        "Flèche simple": "->",
        "Réponse simple": "-->",
        "Signal": "-)",
        "Échec": "-x",
    }
    def message_order(item: tuple[int, dict[str, Any]]) -> tuple[float, int]:
        index, row = item
        try:
            order = float(row.get("ordre") or index + 1)
        except (TypeError, ValueError):
            order = float(index + 1)
            warnings.append(f"Ordre invalide à la ligne {index + 1} : ordre du tableau utilisé.")
        return order, index

    ordered = sorted(enumerate(messages), key=message_order)
    for _, row in ordered:
        source_raw = _text(row.get("source"))
        target_raw = _text(row.get("destination"))
        if not source_raw and not target_raw:
            continue
        if source_raw not in id_map or target_raw not in id_map:
            warnings.append(
                f"Message ignoré : {source_raw or '?'} → {target_raw or '?'} (participant introuvable)."
            )
            continue
        arrow = arrows.get(_text(row.get("style"), "Message"), "->>")
        activation = _text(row.get("activation"), "Aucune")
        if activation == "Active la cible":
            arrow += "+"
        elif activation == "Désactive la cible":
            arrow += "-"
        lines.append(
            f"    {id_map[source_raw]}{arrow}{id_map[target_raw]}: {_plain(row.get('message'))}"
        )
        note = _text(row.get("note"))
        if note:
            lines.append(f"    Note right of {id_map[target_raw]}: {_plain(note)}")

    if not prepared:
        warnings.append("Ajoutez au moins un participant.")
    return "\n".join(lines), warnings


def generate_mindmap(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    rows = _records(project, "ideas")
    id_map, prepared = _build_id_map(rows, "id", warnings)
    root_title = _label(project.get("settings", {}).get("root_title") or project.get("title"))
    lines = ["mindmap", f"  root(({root_title}))"]
    children: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    roots: list[tuple[dict[str, Any], str]] = []

    for row, ident in prepared:
        parent = _text(row.get("parent"))
        if parent and parent in id_map and parent != _text(row.get("id")):
            children[parent].append((row, ident))
        else:
            if parent and parent not in id_map:
                warnings.append(f"Parent introuvable pour « {_text(row.get('id'))} » : placé à la racine.")
            roots.append((row, ident))

    def mind_node(row: dict[str, Any], ident: str) -> str:
        label = _plain(row.get("texte") or row.get("id"))
        shape = _text(row.get("forme"), "Simple")
        patterns = {
            "Simple": f"{ident}[{label}]",
            "Arrondi": f"{ident}({label})",
            "Cercle": f"{ident}(({label}))",
            "Nuage": f"{ident}){label}(",
            "Hexagone": f"{ident}{{{{{label}}}}}",
        }
        return patterns.get(shape, patterns["Simple"])

    visited: set[str] = set()

    def walk(items: list[tuple[dict[str, Any], str]], depth: int) -> None:
        for row, ident in items:
            raw_id = _text(row.get("id"))
            if raw_id in visited:
                warnings.append(f"Boucle détectée autour de « {raw_id} » : branche interrompue.")
                continue
            visited.add(raw_id)
            lines.append("  " * depth + mind_node(row, ident))
            walk(children.get(raw_id, []), depth + 1)

    walk(roots, 2)
    for row, ident in prepared:
        if _text(row.get("id")) not in visited:
            warnings.append(
                f"La branche « {_text(row.get('id'))} » n’était pas rattachée à la racine : elle a été récupérée."
            )
            walk([(row, ident)], 2)
    if not prepared:
        lines.append("    idee[Ajoutez une idée]")
        warnings.append("La carte mentale ne contient encore aucune idée.")
    return "\n".join(lines), warnings


def generate_timeline(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    rows = _records(project, "events")
    title = _plain(project.get("title") or "Chronologie")
    lines = ["timeline", f"    title {title}"]
    current_section = None
    count = 0
    for row in rows:
        period = _text(row.get("période"))
        event = _text(row.get("événement"))
        if not period and not event:
            continue
        section = _text(row.get("section"), "Événements")
        if section != current_section:
            lines.append(f"    section {_plain(section)}")
            current_section = section
        lines.append(f"      {_plain(period or 'Sans date')} : {_plain(event)}")
        count += 1
    if not count:
        lines.append("    section À compléter")
        lines.append("      Maintenant : Ajoutez un événement")
        warnings.append("La chronologie ne contient encore aucun événement.")
    return "\n".join(lines), warnings


def generate_gantt(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    rows = _records(project, "tasks")
    title = _plain(project.get("title") or "Planning")
    settings = project.get("settings", {})
    lines = ["gantt", f"    title {title}", "    dateFormat YYYY-MM-DD"]
    lines.append(f"    axisFormat {_text(settings.get('axis_format'), '%d/%m')}")
    if settings.get("excludes_weekends", False):
        lines.append("    excludes weekends")

    id_map, prepared = _build_id_map(rows, "id", warnings)
    current_section = None
    state_tokens = {
        "À faire": "",
        "En cours": "active",
        "Terminé": "done",
        "Critique": "crit",
        "Critique terminé": "crit, done",
        "Jalon": "milestone",
    }
    for row, ident in prepared:
        section = _text(row.get("section"), "Projet")
        if section != current_section:
            lines.append(f"    section {_plain(section)}")
            current_section = section
        task = _plain(row.get("tâche") or row.get("id"))
        state = _text(row.get("statut"), "À faire")
        prefix = state_tokens.get(state, "")
        dependency = _text(row.get("dépend_de"))
        start = _text(row.get("début"))
        end = _text(row.get("fin"))
        duration = _text(row.get("durée_jours"), "1")
        duration = re.sub(r"[^0-9.]", "", duration) or "1"

        descriptors = [token for token in [prefix, ident] if token]
        if dependency:
            if dependency in id_map:
                descriptors.extend([f"after {id_map[dependency]}", f"{duration}d"])
            else:
                warnings.append(f"Dépendance introuvable pour « {task} » : {dependency}.")
                descriptors.extend([start or "2026-01-01", f"{duration}d"])
        elif start and end:
            descriptors.extend([start, end])
        elif start:
            descriptors.extend([start, f"{duration}d"])
        else:
            descriptors.extend(["2026-01-01", f"{duration}d"])
            warnings.append(f"Date manquante pour « {task} » : 2026-01-01 utilisée.")
        lines.append(f"    {task} :{', '.join(descriptors)}")

    if not prepared:
        warnings.append("Le planning ne contient encore aucune tâche.")
    return "\n".join(lines), warnings


def generate_er(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    attributes = _records(project, "attributes")
    relations = _records(project, "relations")
    entity_names: list[str] = []
    for row in attributes:
        name = _text(row.get("entité"))
        if name and name not in entity_names:
            entity_names.append(name)
    for row in relations:
        for field in ("source", "destination"):
            name = _text(row.get(field))
            if name and name not in entity_names:
                entity_names.append(name)
    entities = [{"name": name} for name in entity_names]
    id_map, prepared = _build_id_map(entities, "name", warnings)

    lines = ["erDiagram"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attributes:
        entity = _text(row.get("entité"))
        if entity:
            grouped[entity].append(row)
    for row, ident in prepared:
        entity = _text(row.get("name"))
        lines.append(f"    {ident} {{")
        entity_attrs = grouped.get(entity, [])
        if not entity_attrs:
            lines.append("        string description")
        for attr in entity_attrs:
            attr_type = _identifier(attr.get("type"), "string")
            attr_name = _identifier(attr.get("attribut"), "champ")
            key = _text(attr.get("clé"))
            key = key if key in {"PK", "FK", "UK"} else ""
            comment = _text(attr.get("commentaire"))
            suffix = f" {key}" if key else ""
            if comment:
                suffix += f' "{_label(comment)}"'
            lines.append(f"        {attr_type} {attr_name}{suffix}")
        lines.append("    }")

    cardinalities = {
        "1 à 1": "||--||",
        "1 à 0 ou 1": "||--o|",
        "1 à plusieurs (0+)": "||--o{",
        "1 à plusieurs (1+)": "||--|{",
        "0/1 à plusieurs": "o|--o{",
        "Plusieurs à plusieurs": "}o--o{",
    }
    for row in relations:
        source = _text(row.get("source"))
        target = _text(row.get("destination"))
        if not source and not target:
            continue
        if source not in id_map or target not in id_map:
            warnings.append(f"Relation ignorée : {source or '?'} ↔ {target or '?'}.")
            continue
        relation = cardinalities.get(_text(row.get("cardinalité")), "||--o{")
        lines.append(
            f'    {id_map[source]} {relation} {id_map[target]} : "{_label(row.get("libellé"))}"'
        )
    if not prepared:
        warnings.append("Ajoutez des attributs ou des relations pour créer les entités.")
    return "\n".join(lines), warnings


def generate_class(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    members = _records(project, "members")
    relations = _records(project, "class_relations")
    class_names: list[str] = []
    for row in members:
        name = _text(row.get("classe"))
        if name and name not in class_names:
            class_names.append(name)
    for row in relations:
        for field in ("source", "destination"):
            name = _text(row.get(field))
            if name and name not in class_names:
                class_names.append(name)
    classes = [{"name": name} for name in class_names]
    id_map, prepared = _build_id_map(classes, "name", warnings)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in members:
        grouped[_text(row.get("classe"))].append(row)

    lines = ["classDiagram"]
    visibility = {"Public": "+", "Privé": "-", "Protégé": "#", "Package": "~"}
    for row, ident in prepared:
        class_name = _text(row.get("name"))
        lines.append(f"    class {ident} {{")
        for member in grouped.get(class_name, []):
            prefix = visibility.get(_text(member.get("visibilité"), "Public"), "+")
            member_type = _plain(member.get("type") or "Any")
            name = _plain(member.get("membre") or "élément")
            if _text(member.get("nature"), "Attribut") == "Méthode" and not name.endswith(")"):
                name += "()"
            lines.append(f"        {prefix}{member_type} {name}")
        lines.append("    }")

    arrows = {
        "Association": "-->",
        "Héritage": "<|--",
        "Composition": "*--",
        "Agrégation": "o--",
        "Dépendance": "..>",
        "Réalisation": "<|..",
    }
    for row in relations:
        source = _text(row.get("source"))
        target = _text(row.get("destination"))
        if not source and not target:
            continue
        if source not in id_map or target not in id_map:
            warnings.append(f"Relation de classes ignorée : {source or '?'} → {target or '?'}.")
            continue
        arrow = arrows.get(_text(row.get("relation"), "Association"), "-->")
        line = f"    {id_map[source]} {arrow} {id_map[target]}"
        if _text(row.get("libellé")):
            line += f" : {_plain(row.get('libellé'))}"
        lines.append(line)
    if not prepared:
        warnings.append("Ajoutez au moins une classe ou une relation.")
    return "\n".join(lines), warnings


def generate_journey(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    rows = _records(project, "steps")
    lines = ["journey", f"    title {_plain(project.get('title') or 'Parcours')}"]
    current_section = None
    count = 0
    for row in rows:
        task = _text(row.get("étape"))
        if not task:
            continue
        section = _text(row.get("section"), "Parcours")
        if section != current_section:
            lines.append(f"    section {_plain(section)}")
            current_section = section
        try:
            score = min(5, max(1, int(float(row.get("score") or 3))))
        except (TypeError, ValueError):
            score = 3
        actors = _text(row.get("acteurs"), "Utilisateur")
        lines.append(f"      {_plain(task)}: {score}: {_plain(actors)}")
        count += 1
    if not count:
        warnings.append("Le parcours ne contient encore aucune étape.")
    return "\n".join(lines), warnings


def generate_pie(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    rows = _records(project, "slices")
    show_data = project.get("settings", {}).get("show_data", True)
    lines = ["pie showData" if show_data else "pie"]
    lines.append(f'    title {_plain(project.get("title") or "Répartition")}')
    count = 0
    for row in rows:
        label = _text(row.get("catégorie"))
        if not label:
            continue
        try:
            value = float(str(row.get("valeur") or 0).replace(",", "."))
        except ValueError:
            warnings.append(f"Valeur invalide pour « {label} » : ligne ignorée.")
            continue
        lines.append(f'    "{_label(label)}" : {value:g}')
        count += 1
    if not count:
        warnings.append("Ajoutez au moins une catégorie numérique.")
    return "\n".join(lines), warnings


def generate_quadrant(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    settings = project.get("settings", {})
    rows = _records(project, "points")
    lines = ["quadrantChart", f"    title {_plain(project.get('title') or 'Matrice')}"]
    lines.append(
        f"    x-axis {_plain(settings.get('x_low') or 'Faible')} --> {_plain(settings.get('x_high') or 'Élevé')}"
    )
    lines.append(
        f"    y-axis {_plain(settings.get('y_low') or 'Faible')} --> {_plain(settings.get('y_high') or 'Élevé')}"
    )
    for index in range(1, 5):
        lines.append(
            f"    quadrant-{index} {_plain(settings.get(f'q{index}') or f'Quadrant {index}')}"
        )
    count = 0
    for row in rows:
        name = _text(row.get("élément"))
        if not name:
            continue
        try:
            x = min(1.0, max(0.0, float(str(row.get("x") or 0).replace(",", "."))))
            y = min(1.0, max(0.0, float(str(row.get("y") or 0).replace(",", "."))))
        except ValueError:
            warnings.append(f"Coordonnées invalides pour « {name} » : ligne ignorée.")
            continue
        lines.append(f"    {_plain(name)}: [{x:.2f}, {y:.2f}]")
        count += 1
    if not count:
        warnings.append("Ajoutez au moins un élément à positionner.")
    return "\n".join(lines), warnings


def generate_state(project: dict[str, Any]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    states = _records(project, "states")
    transitions = _records(project, "transitions")
    id_map, prepared = _build_id_map(states, "id", warnings)
    lines = ["stateDiagram-v2"]
    for row, ident in prepared:
        label = _label(row.get("libellé") or row.get("id"))
        state_type = _text(row.get("type"), "État")
        if state_type not in {"Initial", "Final"}:
            lines.append(f'    state "{label}" as {ident}')
        if state_type == "Choix":
            lines.append(f"    state {ident} <<choice>>")
        elif state_type == "Fork":
            lines.append(f"    state {ident} <<fork>>")
        elif state_type == "Join":
            lines.append(f"    state {ident} <<join>>")

    def resolve(raw: str) -> str | None:
        if raw in {"[*]", "Début", "Fin"}:
            return "[*]"
        return id_map.get(raw)

    for row in transitions:
        source_raw = _text(row.get("source"))
        target_raw = _text(row.get("destination"))
        if not source_raw and not target_raw:
            continue
        source = resolve(source_raw)
        target = resolve(target_raw)
        if not source or not target:
            warnings.append(f"Transition ignorée : {source_raw or '?'} → {target_raw or '?'}.")
            continue
        line = f"    {source} --> {target}"
        if _text(row.get("condition")):
            line += f" : {_plain(row.get('condition'))}"
        lines.append(line)
    if not prepared and not transitions:
        warnings.append("Ajoutez des états et leurs transitions.")
    return "\n".join(lines), warnings


GENERATORS = {
    "flowchart": generate_flowchart,
    "sequence": generate_sequence,
    "mindmap": generate_mindmap,
    "timeline": generate_timeline,
    "gantt": generate_gantt,
    "er": generate_er,
    "class": generate_class,
    "journey": generate_journey,
    "pie": generate_pie,
    "quadrant": generate_quadrant,
    "state": generate_state,
}


def generate_diagram(project: dict[str, Any]) -> tuple[str, list[str]]:
    diagram_type = project.get("diagram_type", "flowchart")
    generator = GENERATORS.get(diagram_type, generate_flowchart)
    return generator(project)
