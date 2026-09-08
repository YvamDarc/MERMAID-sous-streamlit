from __future__ import annotations

import html
import json
import re
import uuid
from typing import Any

import pandas as pd
import streamlit as st

from diagram_generators import COLOR_STYLES, generate_diagram
from templates import DIAGRAM_TYPES, TYPE_HELP, get_empty, get_template

try:
    from streamlit_flow import streamlit_flow
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode
    from streamlit_flow.layouts import LayeredLayout
    from streamlit_flow.state import StreamlitFlowState

    FLOW_AVAILABLE = True
except ImportError:
    FLOW_AVAILABLE = False


APP_VERSION = "1.0.0"
THEMES = {
    "default": "Clair",
    "neutral": "Neutre",
    "forest": "Forêt",
    "dark": "Sombre",
    "base": "Personnalisable",
}


st.set_page_config(
    page_title="Mermaid Studio",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.html(
    """
    <style>
      :root { --ms-primary:#2563eb; --ms-border:#dbe3ef; }
      .block-container { padding-top: 1.4rem; padding-bottom: 3rem; }
      [data-testid="stSidebar"] { border-right: 1px solid var(--ms-border); }
      .ms-hero {
        padding: 1.1rem 1.25rem; border: 1px solid var(--ms-border);
        border-radius: 16px; background: linear-gradient(135deg,#eff6ff,#f8fafc 58%,#f5f3ff);
        margin-bottom: 1rem;
      }
      .ms-hero h1 { margin: 0; color:#0f172a; font-size:2rem; }
      .ms-hero p { margin:.35rem 0 0; color:#475569; }
      .ms-tip {
        padding:.8rem 1rem; border-left:4px solid var(--ms-primary);
        background:#eff6ff; border-radius:0 10px 10px 0; color:#1e3a8a;
      }
      .ms-small { color:#64748b; font-size:.88rem; }
      div[data-testid="stDataEditor"] { border:1px solid var(--ms-border); border-radius:12px; overflow:hidden; }
      div[data-testid="stMetric"] { border:1px solid var(--ms-border); padding:.65rem .8rem; border-radius:12px; background:#fff; }
      .stTabs [data-baseweb="tab-list"] { gap:.35rem; }
      .stTabs [data-baseweb="tab"] { border-radius:9px; padding:.45rem .8rem; }
    </style>
    """
)


def initialize_state() -> None:
    if "projects" not in st.session_state:
        st.session_state.projects = {key: get_template(key) for key in DIAGRAM_TYPES}
    if "revisions" not in st.session_state:
        st.session_state.revisions = {key: 0 for key in DIAGRAM_TYPES}
    if "code_revisions" not in st.session_state:
        st.session_state.code_revisions = {key: 0 for key in DIAGRAM_TYPES}
    if "canvas_states" not in st.session_state:
        st.session_state.canvas_states = {}
    if "diagram_type_selector" not in st.session_state:
        st.session_state.diagram_type_selector = "flowchart"


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9àâäéèêëîïôöùûüç]+", "-", value)
    return value.strip("-") or "diagramme"


def records_from_df(df: pd.DataFrame) -> list[dict[str, Any]]:
    clean = df.astype(object).where(pd.notna(df), None)
    return clean.to_dict(orient="records")


def normalize_project(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Le fichier doit contenir un objet JSON.")
    diagram_type = data.get("diagram_type")
    if diagram_type not in DIAGRAM_TYPES:
        raise ValueError("Le type de diagramme du fichier n’est pas reconnu.")
    base = get_empty(diagram_type)
    base["title"] = str(data.get("title") or base["title"])
    base["theme"] = data.get("theme") if data.get("theme") in THEMES else "default"
    if isinstance(data.get("settings"), dict):
        base["settings"].update(data["settings"])
    if isinstance(data.get("tables"), dict):
        for table, rows in data["tables"].items():
            if isinstance(rows, list):
                base["tables"][table] = [row for row in rows if isinstance(row, dict)]
    base["custom_code"] = str(data.get("custom_code") or "")
    base["use_custom_code"] = bool(data.get("use_custom_code", False))
    return base


def reset_project(diagram_type: str, empty: bool = False) -> None:
    st.session_state.projects[diagram_type] = (
        get_empty(diagram_type) if empty else get_template(diagram_type)
    )
    st.session_state.revisions[diagram_type] += 1
    st.session_state.code_revisions[diagram_type] += 1
    st.session_state.canvas_states.pop(diagram_type, None)


def load_uploaded_project() -> None:
    uploaded = st.session_state.get("project_upload")
    if uploaded is None:
        st.session_state.import_message = ("error", "Sélectionnez d’abord un fichier.")
        return
    try:
        raw = uploaded.getvalue().decode("utf-8-sig")
        if uploaded.name.lower().endswith(".json"):
            project = normalize_project(json.loads(raw))
            diagram_type = project["diagram_type"]
            st.session_state.projects[diagram_type] = project
            st.session_state.diagram_type_selector = diagram_type
        else:
            diagram_type = st.session_state.diagram_type_selector
            project = st.session_state.projects[diagram_type]
            project["custom_code"] = raw
            project["use_custom_code"] = True
        st.session_state.revisions[diagram_type] += 1
        st.session_state.code_revisions[diagram_type] += 1
        st.session_state.canvas_states.pop(diagram_type, None)
        st.session_state.import_message = ("success", "Le projet a été chargé.")
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        st.session_state.import_message = ("error", f"Import impossible : {exc}")


def edit_table(
    project: dict[str, Any],
    table_name: str,
    columns: list[str],
    column_config: dict[str, Any],
    key_prefix: str,
    height: int | None = None,
) -> list[dict[str, Any]]:
    records = project.setdefault("tables", {}).get(table_name, [])
    frame = pd.DataFrame(records)
    for column in columns:
        if column not in frame.columns:
            frame[column] = None
    frame = frame[columns]
    calculated_height = height or min(520, max(180, 84 + 35 * (len(frame) + 1)))
    edited = st.data_editor(
        frame,
        column_config=column_config,
        hide_index=True,
        num_rows="dynamic",
        width="stretch",
        height=calculated_height,
        key=f"{key_prefix}_{table_name}",
    )
    updated = records_from_df(edited)
    project["tables"][table_name] = updated
    return updated


def text_col(label: str, help_text: str = "", required: bool = False, width: str = "medium"):
    return st.column_config.TextColumn(label, help=help_text or None, required=required, width=width)


def select_col(label: str, options: list[str], help_text: str = "", width: str = "medium"):
    return st.column_config.SelectboxColumn(label, options=options, help=help_text or None, width=width)


def render_builder(project: dict[str, Any], revision: int) -> None:
    diagram_type = project["diagram_type"]
    prefix = f"build_{diagram_type}_{revision}"
    st.subheader(DIAGRAM_TYPES[diagram_type])
    st.caption(TYPE_HELP[diagram_type])

    if diagram_type == "flowchart":
        direction_labels = {
            "TD": "Haut → bas",
            "LR": "Gauche → droite",
            "BT": "Bas → haut",
            "RL": "Droite → gauche",
        }
        current = project["settings"].get("direction", "TD")
        project["settings"]["direction"] = st.selectbox(
            "Sens général du schéma",
            list(direction_labels),
            index=list(direction_labels).index(current) if current in direction_labels else 0,
            format_func=direction_labels.get,
            key=f"{prefix}_direction",
        )
        st.markdown("##### 1. Les blocs")
        nodes = edit_table(
            project,
            "nodes",
            ["id", "texte", "forme", "groupe", "couleur"],
            {
                "id": text_col("Identifiant", "Nom court et unique, par exemple validation.", True, "small"),
                "texte": text_col("Texte affiché", "Texte visible dans le bloc.", True, "large"),
                "forme": select_col("Forme", ["Rectangle", "Arrondi", "Stade", "Sous-processus", "Base de données", "Cercle", "Décision", "Hexagone"]),
                "groupe": text_col("Groupe", "Les blocs portant le même groupe sont réunis.", width="medium"),
                "couleur": select_col("Couleur", list(COLOR_STYLES), width="small"),
            },
            prefix,
        )
        node_ids = [str(row.get("id")) for row in nodes if row.get("id")]
        st.markdown("##### 2. Les connexions")
        edit_table(
            project,
            "edges",
            ["source", "destination", "libellé", "style"],
            {
                "source": select_col("Depuis", node_ids or [""], "Bloc de départ."),
                "destination": select_col("Vers", node_ids or [""], "Bloc d’arrivée."),
                "libellé": text_col("Texte sur la liaison", "Par exemple Oui, Non ou Validé.", width="large"),
                "style": select_col("Trait", ["Flèche", "Double flèche", "Ligne", "Pointillée", "Épaisse"]),
            },
            prefix,
        )

    elif diagram_type == "sequence":
        project["settings"]["autonumber"] = st.toggle(
            "Numéroter automatiquement les échanges",
            value=bool(project["settings"].get("autonumber", True)),
            key=f"{prefix}_autonumber",
        )
        st.markdown("##### 1. Les participants")
        participants = edit_table(
            project,
            "participants",
            ["id", "nom", "type"],
            {
                "id": text_col("Identifiant", "Nom court et unique.", True, "small"),
                "nom": text_col("Nom affiché", required=True, width="large"),
                "type": select_col("Représentation", ["Participant", "Acteur"]),
            },
            prefix,
        )
        participant_ids = [str(row.get("id")) for row in participants if row.get("id")]
        st.markdown("##### 2. Les échanges")
        edit_table(
            project,
            "messages",
            ["ordre", "source", "destination", "message", "style", "activation", "note"],
            {
                "ordre": st.column_config.NumberColumn("Ordre", min_value=1, step=1, width="small"),
                "source": select_col("Émetteur", participant_ids or [""]),
                "destination": select_col("Destinataire", participant_ids or [""]),
                "message": text_col("Message", required=True, width="large"),
                "style": select_col("Type", ["Message", "Réponse", "Flèche simple", "Réponse simple", "Signal", "Échec"]),
                "activation": select_col("Activation", ["Aucune", "Active la cible", "Désactive la cible"]),
                "note": text_col("Note facultative", width="large"),
            },
            prefix,
            height=360,
        )

    elif diagram_type == "mindmap":
        project["settings"]["root_title"] = st.text_input(
            "Sujet central",
            value=project["settings"].get("root_title", project["title"]),
            key=f"{prefix}_root",
        )
        ideas = project["tables"].get("ideas", [])
        idea_ids = [str(row.get("id")) for row in ideas if row.get("id")]
        edit_table(
            project,
            "ideas",
            ["id", "texte", "parent", "forme"],
            {
                "id": text_col("Identifiant", "Nom court et unique.", True, "small"),
                "texte": text_col("Idée affichée", required=True, width="large"),
                "parent": select_col("Rattachée à", [""] + idea_ids, "Laissez vide pour rattacher au sujet central."),
                "forme": select_col("Forme", ["Simple", "Arrondi", "Cercle", "Nuage", "Hexagone"]),
            },
            prefix,
            height=420,
        )

    elif diagram_type == "timeline":
        st.markdown('<div class="ms-tip">Une nouvelle section est créée dès que le contenu de la colonne <b>Section</b> change.</div>', unsafe_allow_html=True)
        edit_table(
            project,
            "events",
            ["section", "période", "événement"],
            {
                "section": text_col("Section", "Par exemple Cadrage ou Déploiement."),
                "période": text_col("Date ou période", required=True),
                "événement": text_col("Événement", required=True, width="large"),
            },
            prefix,
            height=420,
        )

    elif diagram_type == "gantt":
        left, right = st.columns(2)
        with left:
            axis_formats = ["%d/%m", "%d/%m/%Y", "%m/%Y", "%Y"]
            current_axis = project["settings"].get("axis_format", "%d/%m")
            project["settings"]["axis_format"] = st.selectbox(
                "Format des dates sur l’axe",
                axis_formats,
                index=axis_formats.index(current_axis) if current_axis in axis_formats else 0,
                key=f"{prefix}_axis",
            )
        with right:
            project["settings"]["excludes_weekends"] = st.toggle(
                "Exclure les week-ends",
                value=bool(project["settings"].get("excludes_weekends", False)),
                key=f"{prefix}_weekends",
            )
        tasks = project["tables"].get("tasks", [])
        task_ids = [str(row.get("id")) for row in tasks if row.get("id")]
        edit_table(
            project,
            "tasks",
            ["section", "tâche", "id", "début", "fin", "durée_jours", "dépend_de", "statut"],
            {
                "section": text_col("Section"),
                "tâche": text_col("Tâche", required=True, width="large"),
                "id": text_col("Identifiant", required=True, width="small"),
                "début": text_col("Début", "Format AAAA-MM-JJ.", width="small"),
                "fin": text_col("Fin", "Format AAAA-MM-JJ. Facultatif si une durée est indiquée.", width="small"),
                "durée_jours": st.column_config.NumberColumn("Durée (jours)", min_value=0, step=1, width="small"),
                "dépend_de": select_col("Après la tâche", [""] + task_ids, "Si renseigné, les dates de début et de fin ne sont pas utilisées."),
                "statut": select_col("Statut", ["À faire", "En cours", "Terminé", "Critique", "Critique terminé", "Jalon"]),
            },
            prefix,
            height=430,
        )

    elif diagram_type == "er":
        st.markdown("##### 1. Les entités et leurs attributs")
        edit_table(
            project,
            "attributes",
            ["entité", "type", "attribut", "clé", "commentaire"],
            {
                "entité": text_col("Entité", "Par exemple CLIENT.", True),
                "type": text_col("Type", "Par exemple int, string ou decimal.", True, "small"),
                "attribut": text_col("Attribut", required=True),
                "clé": select_col("Clé", ["", "PK", "FK", "UK"], width="small"),
                "commentaire": text_col("Commentaire", width="large"),
            },
            prefix,
            height=330,
        )
        st.markdown("##### 2. Les relations")
        edit_table(
            project,
            "relations",
            ["source", "destination", "cardinalité", "libellé"],
            {
                "source": text_col("Entité de départ", required=True),
                "destination": text_col("Entité d’arrivée", required=True),
                "cardinalité": select_col("Cardinalité", ["1 à 1", "1 à 0 ou 1", "1 à plusieurs (0+)", "1 à plusieurs (1+)", "0/1 à plusieurs", "Plusieurs à plusieurs"]),
                "libellé": text_col("Verbe de relation", "Par exemple contient ou appartient à.", width="large"),
            },
            prefix,
        )

    elif diagram_type == "class":
        st.markdown("##### 1. Les membres des classes")
        edit_table(
            project,
            "members",
            ["classe", "visibilité", "type", "membre", "nature"],
            {
                "classe": text_col("Classe", required=True),
                "visibilité": select_col("Visibilité", ["Public", "Privé", "Protégé", "Package"]),
                "type": text_col("Type", required=True),
                "membre": text_col("Attribut ou méthode", required=True, width="large"),
                "nature": select_col("Nature", ["Attribut", "Méthode"]),
            },
            prefix,
            height=330,
        )
        st.markdown("##### 2. Les relations entre classes")
        edit_table(
            project,
            "class_relations",
            ["source", "destination", "relation", "libellé"],
            {
                "source": text_col("Classe source", required=True),
                "destination": text_col("Classe cible", required=True),
                "relation": select_col("Relation", ["Association", "Héritage", "Composition", "Agrégation", "Dépendance", "Réalisation"]),
                "libellé": text_col("Libellé", width="large"),
            },
            prefix,
        )

    elif diagram_type == "journey":
        edit_table(
            project,
            "steps",
            ["section", "étape", "score", "acteurs"],
            {
                "section": text_col("Phase"),
                "étape": text_col("Étape", required=True, width="large"),
                "score": st.column_config.NumberColumn("Satisfaction", help="Note de 1 à 5.", min_value=1, max_value=5, step=1),
                "acteurs": text_col("Acteurs", "Séparez plusieurs acteurs par une virgule.", width="large"),
            },
            prefix,
            height=420,
        )

    elif diagram_type == "pie":
        project["settings"]["show_data"] = st.toggle(
            "Afficher les valeurs sur le graphique",
            value=bool(project["settings"].get("show_data", True)),
            key=f"{prefix}_show_data",
        )
        edit_table(
            project,
            "slices",
            ["catégorie", "valeur"],
            {
                "catégorie": text_col("Catégorie", required=True, width="large"),
                "valeur": st.column_config.NumberColumn("Valeur", min_value=0, format="%.2f", required=True),
            },
            prefix,
        )

    elif diagram_type == "quadrant":
        st.markdown("##### Libellés des axes et quadrants")
        c1, c2 = st.columns(2)
        fields = [
            ("x_low", "Début de l’axe horizontal"),
            ("x_high", "Fin de l’axe horizontal"),
            ("y_low", "Début de l’axe vertical"),
            ("y_high", "Fin de l’axe vertical"),
            ("q1", "Quadrant 1 — haut droite"),
            ("q2", "Quadrant 2 — haut gauche"),
            ("q3", "Quadrant 3 — bas gauche"),
            ("q4", "Quadrant 4 — bas droite"),
        ]
        for index, (field, label) in enumerate(fields):
            with (c1 if index % 2 == 0 else c2):
                project["settings"][field] = st.text_input(
                    label,
                    value=project["settings"].get(field, ""),
                    key=f"{prefix}_{field}",
                )
        st.markdown("##### Éléments à positionner")
        edit_table(
            project,
            "points",
            ["élément", "x", "y"],
            {
                "élément": text_col("Élément", required=True, width="large"),
                "x": st.column_config.NumberColumn("Position X", help="Entre 0 et 1.", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"),
                "y": st.column_config.NumberColumn("Position Y", help="Entre 0 et 1.", min_value=0.0, max_value=1.0, step=0.05, format="%.2f"),
            },
            prefix,
            height=360,
        )

    elif diagram_type == "state":
        st.markdown("##### 1. Les états")
        states = edit_table(
            project,
            "states",
            ["id", "libellé", "type"],
            {
                "id": text_col("Identifiant", required=True, width="small"),
                "libellé": text_col("Texte affiché", required=True, width="large"),
                "type": select_col("Type", ["État", "Choix", "Fork", "Join"]),
            },
            prefix,
        )
        state_ids = [str(row.get("id")) for row in states if row.get("id")]
        st.markdown("##### 2. Les transitions")
        edit_table(
            project,
            "transitions",
            ["source", "destination", "condition"],
            {
                "source": select_col("Depuis", ["Début"] + state_ids + ["Fin"]),
                "destination": select_col("Vers", ["Début"] + state_ids + ["Fin"]),
                "condition": text_col("Condition ou action", width="large"),
            },
            prefix,
            height=360,
        )


def preview_html(code: str, theme: str, title: str, include_toolbar: bool = True) -> str:
    uid = uuid.uuid4().hex
    source_id = f"mermaid-source-{uid}"
    target_id = f"mermaid-target-{uid}"
    error_id = f"mermaid-error-{uid}"
    svg_button_id = f"mermaid-svg-{uid}"
    png_button_id = f"mermaid-png-{uid}"
    safe_code = html.escape(code)
    safe_title = html.escape(slugify(title))
    dark = theme == "dark"
    background = "#111827" if dark else "#ffffff"
    foreground = "#e5e7eb" if dark else "#0f172a"
    toolbar = ""
    if include_toolbar:
        toolbar = f"""
        <div class="ms-render-toolbar">
          <button id="{svg_button_id}" disabled>Télécharger en SVG</button>
          <button id="{png_button_id}" disabled>Télécharger en PNG</button>
        </div>
        """
    return f"""
    <section id="mermaid-wrapper-{uid}" class="ms-render-wrapper">
      {toolbar}
      <pre id="{source_id}" style="display:none">{safe_code}</pre>
      <div id="{error_id}" class="ms-render-error" hidden></div>
      <div id="{target_id}" class="ms-render-target" aria-label="Aperçu du diagramme"></div>
    </section>
    <style>
      #mermaid-wrapper-{uid} {{
        border:1px solid {'#374151' if dark else '#dbe3ef'}; border-radius:14px;
        background:{background}; color:{foreground}; min-height:360px; overflow:auto;
      }}
      #mermaid-wrapper-{uid} .ms-render-toolbar {{
        position:sticky; top:0; z-index:3; display:flex; justify-content:flex-end; gap:.5rem;
        padding:.65rem; background:{'#111827ee' if dark else '#fffffff0'};
        border-bottom:1px solid {'#374151' if dark else '#e2e8f0'};
      }}
      #mermaid-wrapper-{uid} button {{
        border:1px solid {'#4b5563' if dark else '#cbd5e1'}; border-radius:8px;
        background:{'#1f2937' if dark else '#f8fafc'}; color:{foreground};
        padding:.4rem .72rem; cursor:pointer; font:500 13px system-ui;
      }}
      #mermaid-wrapper-{uid} button:hover {{ border-color:#2563eb; color:#2563eb; }}
      #mermaid-wrapper-{uid} button:disabled {{ opacity:.45; cursor:not-allowed; }}
      #{target_id} {{ min-height:300px; display:flex; align-items:center; justify-content:center; padding:1.25rem; }}
      #{target_id} svg {{ max-width:100%; height:auto; }}
      #{error_id} {{ margin:1rem; padding:1rem; border-radius:10px; background:#fee2e2; color:#991b1b; white-space:pre-wrap; }}
    </style>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      const source = document.getElementById("{source_id}").textContent.trim();
      const target = document.getElementById("{target_id}");
      const errorBox = document.getElementById("{error_id}");
      const svgButton = document.getElementById("{svg_button_id}");
      const pngButton = document.getElementById("{png_button_id}");
      mermaid.initialize({{
        startOnLoad:false,
        securityLevel:"strict",
        theme:"{theme}",
        fontFamily:"Inter, ui-sans-serif, system-ui, sans-serif",
        flowchart:{{ useMaxWidth:true, htmlLabels:false, curve:"basis" }},
        sequence:{{ useMaxWidth:true, wrap:true }},
        gantt:{{ useMaxWidth:true }}
      }});
      try {{
        await mermaid.parse(source);
        const result = await mermaid.render("mermaid-svg-{uid}", source);
        target.innerHTML = result.svg;
        if (result.bindFunctions) result.bindFunctions(target);
        if (svgButton) svgButton.disabled = false;
        if (pngButton) pngButton.disabled = false;
      }} catch (error) {{
        errorBox.hidden = false;
        errorBox.textContent = "Le diagramme contient une erreur Mermaid.\n\n" + (error?.message || String(error));
      }}
      function downloadBlob(blob, filename) {{
        const link = document.createElement("a");
        link.href = URL.createObjectURL(blob); link.download = filename; link.click();
        setTimeout(() => URL.revokeObjectURL(link.href), 1000);
      }}
      if (svgButton) svgButton.addEventListener("click", () => {{
        const svg = target.querySelector("svg");
        if (!svg) return;
        const serialized = new XMLSerializer().serializeToString(svg);
        downloadBlob(new Blob([serialized], {{type:"image/svg+xml;charset=utf-8"}}), "{safe_title}.svg");
      }});
      if (pngButton) pngButton.addEventListener("click", () => {{
        const svg = target.querySelector("svg");
        if (!svg) return;
        const copy = svg.cloneNode(true);
        const box = svg.getBoundingClientRect();
        const width = Math.max(1, Math.ceil(box.width));
        const height = Math.max(1, Math.ceil(box.height));
        copy.setAttribute("width", width); copy.setAttribute("height", height);
        const blob = new Blob([new XMLSerializer().serializeToString(copy)], {{type:"image/svg+xml;charset=utf-8"}});
        const url = URL.createObjectURL(blob); const image = new Image();
        image.onload = () => {{
          const scale = 2; const canvas = document.createElement("canvas");
          canvas.width = width * scale; canvas.height = height * scale;
          const context = canvas.getContext("2d"); context.scale(scale, scale);
          context.fillStyle = "{background}"; context.fillRect(0, 0, width, height);
          context.drawImage(image, 0, 0, width, height); URL.revokeObjectURL(url);
          canvas.toBlob((png) => png && downloadBlob(png, "{safe_title}.png"), "image/png");
        }};
        image.src = url;
      }});
    </script>
    """


def standalone_html(code: str, theme: str, title: str) -> str:
    safe_code = html.escape(code)
    safe_title = html.escape(title)
    background = "#111827" if theme == "dark" else "#ffffff"
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{safe_title}</title>
  <style>
    body {{ margin:0; padding:2rem; background:{background}; font-family:Arial,sans-serif; }}
    .mermaid {{ display:flex; justify-content:center; }}
  </style>
</head>
<body>
  <pre class="mermaid">{safe_code}</pre>
  <script type="module">
    import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
    mermaid.initialize({{startOnLoad:true,securityLevel:"strict",theme:"{theme}"}});
  </script>
</body>
</html>"""


def project_counts(project: dict[str, Any]) -> tuple[int, int]:
    tables = project.get("tables", {})
    if project["diagram_type"] == "flowchart":
        return len(tables.get("nodes", [])), len(tables.get("edges", []))
    if project["diagram_type"] == "sequence":
        return len(tables.get("participants", [])), len(tables.get("messages", []))
    if project["diagram_type"] in {"er", "class", "state"}:
        keys = list(tables)
        return len(tables.get(keys[0], [])), len(tables.get(keys[1], []))
    first = next(iter(tables.values()), [])
    return len(first), 0


def canvas_state_from_project(project: dict[str, Any]) -> "StreamlitFlowState":
    direction = project.get("settings", {}).get("direction", "TD")
    horizontal = direction in {"LR", "RL"}
    reverse = direction in {"RL", "BT"}
    nodes = []
    for index, row in enumerate(project["tables"].get("nodes", [])):
        node_id = str(row.get("id") or f"bloc_{index + 1}")
        fill, stroke, text_color = COLOR_STYLES.get(str(row.get("couleur") or "Blanc"), COLOR_STYLES["Blanc"])
        x = (index % 3) * 260 if not horizontal else (index // 3) * 280
        y = (index // 3) * 150 if not horizontal else (index % 3) * 150
        if reverse:
            x, y = -x, -y
        nodes.append(
            StreamlitFlowNode(
                id=node_id,
                pos=(x, y),
                data={"content": str(row.get("texte") or node_id)},
                node_type="default",
                source_position="right" if horizontal else "bottom",
                target_position="left" if horizontal else "top",
                draggable=True,
                selectable=True,
                connectable=True,
                deletable=True,
                style={
                    "width": "190px",
                    "background": fill,
                    "border": f"2px solid {stroke}",
                    "color": text_color,
                    "borderRadius": "10px",
                    "padding": "10px",
                },
            )
        )
    edges = []
    for index, row in enumerate(project["tables"].get("edges", [])):
        source = str(row.get("source") or "")
        target = str(row.get("destination") or "")
        if not source or not target:
            continue
        edge_type = "smoothstep" if row.get("style") == "Pointillée" else "default"
        edges.append(
            StreamlitFlowEdge(
                id=f"edge_{index}_{source}_{target}",
                source=source,
                target=target,
                edge_type=edge_type,
                label=str(row.get("libellé") or ""),
                animated=row.get("style") == "Pointillée",
                deletable=True,
                label_show_bg=True,
            )
        )
    return StreamlitFlowState(nodes, edges)


def apply_canvas_to_project(project: dict[str, Any], state: "StreamlitFlowState") -> None:
    old_nodes = {str(row.get("id")): row for row in project["tables"].get("nodes", [])}
    new_nodes = []
    for node in state.nodes:
        old = old_nodes.get(node.id, {})
        new_nodes.append(
            {
                "id": node.id,
                "texte": str(node.data.get("content") or node.id),
                "forme": old.get("forme", "Rectangle"),
                "groupe": old.get("groupe", ""),
                "couleur": old.get("couleur", "Blanc"),
            }
        )
    old_edges = {
        (str(row.get("source")), str(row.get("destination")), str(row.get("libellé") or "")): row
        for row in project["tables"].get("edges", [])
    }
    new_edges = []
    for edge in state.edges:
        key = (edge.source, edge.target, str(edge.label or ""))
        old = old_edges.get(key, {})
        new_edges.append(
            {
                "source": edge.source,
                "destination": edge.target,
                "libellé": str(edge.label or ""),
                "style": old.get("style", "Pointillée" if edge.animated else "Flèche"),
            }
        )
    project["tables"]["nodes"] = new_nodes
    project["tables"]["edges"] = new_edges


def render_canvas(project: dict[str, Any], revision: int) -> None:
    if project["diagram_type"] != "flowchart":
        st.info("Le canvas libre est réservé aux processus et organigrammes. Pour ce type de diagramme, l’éditeur guidé reste plus lisible.")
        return
    if not FLOW_AVAILABLE:
        st.error("Le composant visuel n’est pas installé. Exécutez : pip install streamlit-flow-component")
        return

    st.subheader("Canvas visuel")
    st.markdown(
        "Déplacez les blocs à la souris. Faites un **clic droit dans le vide** pour ajouter un bloc, "
        "un **clic droit sur un bloc** pour le modifier et tirez une liaison entre les poignées pour relier deux blocs."
    )
    controls = st.columns([1, 1, 3])
    if controls[0].button("Recharger le tableau", key=f"canvas_reload_{revision}", width="stretch"):
        st.session_state.canvas_states["flowchart"] = canvas_state_from_project(project)
        st.rerun()

    if "flowchart" not in st.session_state.canvas_states:
        st.session_state.canvas_states["flowchart"] = canvas_state_from_project(project)

    state = st.session_state.canvas_states["flowchart"]
    direction = project.get("settings", {}).get("direction", "TD")
    layout_direction = {"TD": "down", "BT": "up", "LR": "right", "RL": "left"}.get(direction, "down")
    returned = streamlit_flow(
        key=f"visual_canvas_{revision}",
        state=state,
        height=620,
        fit_view=True,
        show_controls=True,
        show_minimap=True,
        allow_new_edges=True,
        animate_new_edges=False,
        layout=LayeredLayout(direction=layout_direction, node_node_spacing=70, node_layer_spacing=100),
        enable_pane_menu=True,
        enable_node_menu=True,
        enable_edge_menu=True,
        hide_watermark=False,
    )
    if returned.timestamp != state.timestamp:
        st.session_state.canvas_states["flowchart"] = returned

    if st.button("Appliquer les modifications au schéma", type="primary", key=f"canvas_apply_{revision}"):
        apply_canvas_to_project(project, st.session_state.canvas_states["flowchart"])
        st.session_state.revisions["flowchart"] += 1
        st.success("Les blocs et connexions du canvas ont été repris dans le projet.")
        st.rerun()


initialize_state()

st.sidebar.title("Mermaid Studio")
diagram_type = st.sidebar.selectbox(
    "Type de diagramme",
    options=list(DIAGRAM_TYPES),
    format_func=DIAGRAM_TYPES.get,
    key="diagram_type_selector",
)
project = st.session_state.projects[diagram_type]
revision = st.session_state.revisions[diagram_type]

project["title"] = st.sidebar.text_input(
    "Titre du projet",
    value=project.get("title", "Diagramme"),
    key=f"title_{diagram_type}_{revision}",
)
theme_keys = list(THEMES)
current_theme = project.get("theme", "default")
project["theme"] = st.sidebar.selectbox(
    "Thème graphique",
    options=theme_keys,
    index=theme_keys.index(current_theme) if current_theme in theme_keys else 0,
    format_func=THEMES.get,
    key=f"theme_{diagram_type}_{revision}",
)

st.sidebar.markdown("---")
c1, c2 = st.sidebar.columns(2)
if c1.button("Modèle", help="Recharge l’exemple de ce type.", width="stretch"):
    reset_project(diagram_type, empty=False)
    st.rerun()
if c2.button("Projet vide", help="Efface les données de ce type.", width="stretch"):
    reset_project(diagram_type, empty=True)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(TYPE_HELP[diagram_type])
st.sidebar.caption(f"Version {APP_VERSION} · Mermaid 11")

st.html(
    f"""
    <div class="ms-hero">
      <h1>Mermaid Studio</h1>
      <p>Créez un {html.escape(DIAGRAM_TYPES[diagram_type].lower())} sans écrire de code, puis exportez-le.</p>
    </div>
    """
)

count_a, count_b = project_counts(project)
metric_cols = st.columns(3)
metric_cols[0].metric("Type", DIAGRAM_TYPES[diagram_type])
metric_cols[1].metric("Éléments", count_a)
metric_cols[2].metric("Relations", count_b if count_b else "—")

tabs = st.tabs(
    [
        "1 · Construire",
        "2 · Aperçu",
        "3 · Canvas visuel",
        "4 · Code avancé",
        "5 · Importer / exporter",
        "Aide",
    ]
)

with tabs[0]:
    render_builder(project, revision)

generated_code, warnings = generate_diagram(project)
active_code = project.get("custom_code", "") if project.get("use_custom_code") else generated_code

with tabs[1]:
    st.subheader("Aperçu du diagramme")
    if project.get("use_custom_code"):
        st.info("L’aperçu utilise actuellement le code Mermaid personnalisé de l’onglet « Code avancé ».")
    if warnings and not project.get("use_custom_code"):
        with st.expander(f"{len(warnings)} point(s) à vérifier", expanded=True):
            for warning in dict.fromkeys(warnings):
                st.warning(warning)
    st.html(preview_html(active_code, project["theme"], project["title"]), unsafe_allow_javascript=True)

with tabs[2]:
    render_canvas(project, revision)

with tabs[3]:
    st.subheader("Code Mermaid")
    if not project.get("use_custom_code"):
        st.caption("Ce code est produit automatiquement à partir de l’éditeur guidé.")
        st.code(generated_code, language="mermaid", line_numbers=True)
        if st.button("Créer une copie modifiable", type="primary", key=f"manual_start_{diagram_type}_{revision}"):
            project["custom_code"] = generated_code
            project["use_custom_code"] = True
            st.session_state.code_revisions[diagram_type] += 1
            st.rerun()
    else:
        st.warning("Le mode manuel est actif : les changements faits dans les tableaux ne modifient plus l’aperçu.")
        project["custom_code"] = st.text_area(
            "Code personnalisé",
            value=project.get("custom_code", generated_code),
            height=520,
            key=f"custom_code_{diagram_type}_{st.session_state.code_revisions[diagram_type]}",
        )
        col_manual_1, col_manual_2 = st.columns([1, 2])
        if col_manual_1.button("Revenir au mode guidé", key=f"manual_stop_{diagram_type}_{revision}"):
            project["use_custom_code"] = False
            st.session_state.code_revisions[diagram_type] += 1
            st.rerun()
        col_manual_2.caption("Le code personnalisé reste conservé dans le projet si vous revenez plus tard au mode manuel.")

with tabs[4]:
    st.subheader("Télécharger le projet")
    filename = slugify(project["title"])
    download_cols = st.columns(3)
    download_cols[0].download_button(
        "Projet complet (.json)",
        data=json.dumps(project, ensure_ascii=False, indent=2),
        file_name=f"{filename}.json",
        mime="application/json",
        width="stretch",
    )
    download_cols[1].download_button(
        "Code Mermaid (.mmd)",
        data=active_code,
        file_name=f"{filename}.mmd",
        mime="text/plain",
        width="stretch",
    )
    download_cols[2].download_button(
        "Page autonome (.html)",
        data=standalone_html(active_code, project["theme"], project["title"]),
        file_name=f"{filename}.html",
        mime="text/html",
        width="stretch",
    )
    st.caption("Les boutons SVG et PNG se trouvent directement au-dessus du diagramme dans l’onglet Aperçu.")

    st.markdown("---")
    st.subheader("Charger un projet ou du code Mermaid")
    st.file_uploader(
        "Fichier JSON, MMD ou TXT",
        type=["json", "mmd", "txt"],
        key="project_upload",
        help="Un JSON restaure tout le projet. Un fichier MMD/TXT active le mode Mermaid manuel.",
    )
    st.button("Charger le fichier", on_click=load_uploaded_project, type="primary")
    import_message = st.session_state.pop("import_message", None)
    if import_message:
        level, message = import_message
        (st.success if level == "success" else st.error)(message)

with tabs[5]:
    st.subheader("Mode d’emploi")
    st.markdown(
        """
1. Choisissez le type de diagramme dans la barre latérale.
2. Ajoutez ou supprimez des lignes dans les tableaux avec les contrôles du tableau.
3. Consultez immédiatement le résultat dans **Aperçu**.
4. Pour un processus, utilisez éventuellement le **Canvas visuel** pour déplacer, ajouter ou relier des blocs à la souris.
5. Téléchargez le résultat en PNG, SVG, Mermaid, HTML ou en projet JSON réutilisable.

Le bouton **Modèle** recharge un exemple complet. Le bouton **Projet vide** permet de repartir de zéro. Les identifiants sont des noms courts servant à établir les connexions ; ils ne sont pas nécessairement affichés sur le schéma.
        """
    )
    st.markdown("##### Types disponibles")
    help_frame = pd.DataFrame(
        [{"Type": label, "Utilisation": TYPE_HELP[key]} for key, label in DIAGRAM_TYPES.items()]
    )
    st.dataframe(help_frame, hide_index=True, width="stretch")
    st.info("Conseil : conservez régulièrement le projet JSON. Il permet de retrouver tous les tableaux, paramètres et éventuelles modifications manuelles.")
