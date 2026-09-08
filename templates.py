"""French sample projects used by Mermaid Studio's guided editors."""

from __future__ import annotations

from copy import deepcopy


DIAGRAM_TYPES = {
    "flowchart": "Processus / organigramme",
    "sequence": "Diagramme de séquence",
    "mindmap": "Carte mentale",
    "timeline": "Chronologie",
    "gantt": "Planning de Gantt",
    "er": "Schéma de données (ER)",
    "class": "Diagramme de classes",
    "journey": "Parcours utilisateur",
    "pie": "Diagramme circulaire",
    "quadrant": "Matrice à quatre quadrants",
    "state": "Diagramme d’états",
}


TYPE_HELP = {
    "flowchart": "Construisez des procédures, arbres de décision et organigrammes avec des blocs reliés.",
    "sequence": "Décrivez les échanges successifs entre personnes, services ou applications.",
    "mindmap": "Organisez des idées autour d’un sujet central à l’aide d’une relation parent-enfant.",
    "timeline": "Présentez des événements par période et par grande section.",
    "gantt": "Planifiez des tâches avec dates, durées, dépendances et statuts.",
    "er": "Modélisez des tables, leurs attributs, leurs clés et leurs cardinalités.",
    "class": "Décrivez des classes, membres et relations techniques.",
    "journey": "Visualisez les étapes d’un parcours et la satisfaction associée.",
    "pie": "Comparez simplement la répartition de plusieurs catégories.",
    "quadrant": "Positionnez des éléments selon deux axes compris entre 0 et 1.",
    "state": "Représentez les états successifs d’un dossier, objet ou processus.",
}


TEMPLATES = {
    "flowchart": {
        "diagram_type": "flowchart",
        "title": "Circuit de validation d’une facture",
        "theme": "default",
        "settings": {"direction": "TD"},
        "tables": {
            "nodes": [
                {"id": "reception", "texte": "Réception de la facture", "forme": "Arrondi", "groupe": "Traitement", "couleur": "Bleu"},
                {"id": "controle", "texte": "Contrôle des informations", "forme": "Rectangle", "groupe": "Traitement", "couleur": "Blanc"},
                {"id": "conforme", "texte": "Facture conforme ?", "forme": "Décision", "groupe": "Validation", "couleur": "Orange"},
                {"id": "validation", "texte": "Validation du responsable", "forme": "Rectangle", "groupe": "Validation", "couleur": "Vert"},
                {"id": "rejet", "texte": "Demande de correction", "forme": "Rectangle", "groupe": "Validation", "couleur": "Rouge"},
                {"id": "paiement", "texte": "Mise en paiement", "forme": "Base de données", "groupe": "Règlement", "couleur": "Violet"},
            ],
            "edges": [
                {"source": "reception", "destination": "controle", "libellé": "", "style": "Flèche"},
                {"source": "controle", "destination": "conforme", "libellé": "", "style": "Flèche"},
                {"source": "conforme", "destination": "validation", "libellé": "Oui", "style": "Flèche"},
                {"source": "conforme", "destination": "rejet", "libellé": "Non", "style": "Flèche"},
                {"source": "rejet", "destination": "reception", "libellé": "Facture corrigée", "style": "Pointillée"},
                {"source": "validation", "destination": "paiement", "libellé": "Bon à payer", "style": "Épaisse"},
            ],
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "sequence": {
        "diagram_type": "sequence",
        "title": "Transmission d’une facture",
        "theme": "default",
        "settings": {"autonumber": True},
        "tables": {
            "participants": [
                {"id": "client", "nom": "Client", "type": "Acteur"},
                {"id": "portail", "nom": "Plateforme", "type": "Participant"},
                {"id": "cabinet", "nom": "Cabinet comptable", "type": "Acteur"},
            ],
            "messages": [
                {"ordre": 1, "source": "client", "destination": "portail", "message": "Dépose la facture", "style": "Message", "activation": "Active la cible", "note": "Contrôle du format"},
                {"ordre": 2, "source": "portail", "destination": "cabinet", "message": "Transmet la pièce", "style": "Message", "activation": "Désactive la cible", "note": ""},
                {"ordre": 3, "source": "cabinet", "destination": "client", "message": "Confirme le traitement", "style": "Réponse", "activation": "Aucune", "note": ""},
            ],
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "mindmap": {
        "diagram_type": "mindmap",
        "title": "Préparation du bilan",
        "theme": "default",
        "settings": {"root_title": "Préparation du bilan"},
        "tables": {
            "ideas": [
                {"id": "collecte", "texte": "Collecte", "parent": "", "forme": "Arrondi"},
                {"id": "banque", "texte": "Banques", "parent": "collecte", "forme": "Simple"},
                {"id": "factures", "texte": "Factures manquantes", "parent": "collecte", "forme": "Simple"},
                {"id": "revision", "texte": "Révision", "parent": "", "forme": "Arrondi"},
                {"id": "tiers", "texte": "Comptes de tiers", "parent": "revision", "forme": "Simple"},
                {"id": "fiscal", "texte": "Fiscalité", "parent": "revision", "forme": "Hexagone"},
                {"id": "restitution", "texte": "Restitution client", "parent": "", "forme": "Cercle"},
            ]
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "timeline": {
        "diagram_type": "timeline",
        "title": "Déploiement du projet",
        "theme": "default",
        "settings": {},
        "tables": {
            "events": [
                {"section": "Cadrage", "période": "Septembre 2026", "événement": "Recueil des besoins"},
                {"section": "Cadrage", "période": "Octobre 2026", "événement": "Validation du périmètre"},
                {"section": "Déploiement", "période": "Novembre 2026", "événement": "Phase pilote"},
                {"section": "Déploiement", "période": "Décembre 2026", "événement": "Généralisation"},
            ]
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "gantt": {
        "diagram_type": "gantt",
        "title": "Planning de clôture",
        "theme": "default",
        "settings": {"axis_format": "%d/%m", "excludes_weekends": True},
        "tables": {
            "tasks": [
                {"section": "Collecte", "tâche": "Relancer les pièces", "id": "pieces", "début": "2026-09-07", "fin": "2026-09-11", "durée_jours": 5, "dépend_de": "", "statut": "En cours"},
                {"section": "Révision", "tâche": "Réviser les cycles", "id": "revision", "début": "", "fin": "", "durée_jours": 7, "dépend_de": "pieces", "statut": "Critique"},
                {"section": "Finalisation", "tâche": "Valider le bilan", "id": "validation", "début": "", "fin": "", "durée_jours": 2, "dépend_de": "revision", "statut": "À faire"},
                {"section": "Finalisation", "tâche": "Restitution client", "id": "restitution", "début": "", "fin": "", "durée_jours": 0, "dépend_de": "validation", "statut": "Jalon"},
            ]
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "er": {
        "diagram_type": "er",
        "title": "Base de facturation",
        "theme": "default",
        "settings": {},
        "tables": {
            "attributes": [
                {"entité": "CLIENT", "type": "int", "attribut": "id_client", "clé": "PK", "commentaire": "Identifiant unique"},
                {"entité": "CLIENT", "type": "string", "attribut": "nom", "clé": "", "commentaire": ""},
                {"entité": "FACTURE", "type": "int", "attribut": "id_facture", "clé": "PK", "commentaire": ""},
                {"entité": "FACTURE", "type": "int", "attribut": "id_client", "clé": "FK", "commentaire": ""},
                {"entité": "FACTURE", "type": "decimal", "attribut": "montant_ht", "clé": "", "commentaire": ""},
                {"entité": "LIGNE", "type": "int", "attribut": "id_ligne", "clé": "PK", "commentaire": ""},
                {"entité": "LIGNE", "type": "int", "attribut": "id_facture", "clé": "FK", "commentaire": ""},
            ],
            "relations": [
                {"source": "CLIENT", "destination": "FACTURE", "cardinalité": "1 à plusieurs (0+)", "libellé": "reçoit"},
                {"source": "FACTURE", "destination": "LIGNE", "cardinalité": "1 à plusieurs (1+)", "libellé": "contient"},
            ],
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "class": {
        "diagram_type": "class",
        "title": "Gestion des documents",
        "theme": "default",
        "settings": {},
        "tables": {
            "members": [
                {"classe": "Document", "visibilité": "Protégé", "type": "string", "membre": "référence", "nature": "Attribut"},
                {"classe": "Document", "visibilité": "Public", "type": "void", "membre": "valider", "nature": "Méthode"},
                {"classe": "Facture", "visibilité": "Privé", "type": "decimal", "membre": "montant", "nature": "Attribut"},
                {"classe": "Facture", "visibilité": "Public", "type": "decimal", "membre": "calculerTVA", "nature": "Méthode"},
            ],
            "class_relations": [
                {"source": "Document", "destination": "Facture", "relation": "Héritage", "libellé": ""},
            ],
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "journey": {
        "diagram_type": "journey",
        "title": "Parcours de dépôt des pièces",
        "theme": "default",
        "settings": {},
        "tables": {
            "steps": [
                {"section": "Dépôt", "étape": "Se connecter", "score": 4, "acteurs": "Client"},
                {"section": "Dépôt", "étape": "Importer les factures", "score": 3, "acteurs": "Client"},
                {"section": "Traitement", "étape": "Contrôler les pièces", "score": 4, "acteurs": "Cabinet"},
                {"section": "Traitement", "étape": "Corriger une anomalie", "score": 2, "acteurs": "Client, Cabinet"},
            ]
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "pie": {
        "diagram_type": "pie",
        "title": "Répartition du chiffre d’affaires",
        "theme": "default",
        "settings": {"show_data": True},
        "tables": {
            "slices": [
                {"catégorie": "Prestations", "valeur": 62},
                {"catégorie": "Ventes", "valeur": 28},
                {"catégorie": "Autres produits", "valeur": 10},
            ]
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "quadrant": {
        "diagram_type": "quadrant",
        "title": "Priorisation des actions",
        "theme": "default",
        "settings": {
            "x_low": "Effort faible",
            "x_high": "Effort élevé",
            "y_low": "Impact faible",
            "y_high": "Impact élevé",
            "q1": "Projets stratégiques",
            "q2": "Actions rapides",
            "q3": "À différer",
            "q4": "À éviter",
        },
        "tables": {
            "points": [
                {"élément": "Automatiser les relances", "x": 0.25, "y": 0.82},
                {"élément": "Changer de logiciel", "x": 0.82, "y": 0.70},
                {"élément": "Refaire un modèle", "x": 0.35, "y": 0.38},
                {"élément": "Saisie manuelle", "x": 0.75, "y": 0.20},
            ]
        },
        "custom_code": "",
        "use_custom_code": False,
    },
    "state": {
        "diagram_type": "state",
        "title": "Cycle de traitement d’un dossier",
        "theme": "default",
        "settings": {},
        "tables": {
            "states": [
                {"id": "recu", "libellé": "Dossier reçu", "type": "État"},
                {"id": "controle", "libellé": "En contrôle", "type": "État"},
                {"id": "decision", "libellé": "Décision", "type": "Choix"},
                {"id": "valide", "libellé": "Validé", "type": "État"},
                {"id": "correction", "libellé": "À corriger", "type": "État"},
            ],
            "transitions": [
                {"source": "Début", "destination": "recu", "condition": ""},
                {"source": "recu", "destination": "controle", "condition": "Prise en charge"},
                {"source": "controle", "destination": "decision", "condition": "Contrôle terminé"},
                {"source": "decision", "destination": "valide", "condition": "Conforme"},
                {"source": "decision", "destination": "correction", "condition": "Anomalie"},
                {"source": "correction", "destination": "controle", "condition": "Correction reçue"},
                {"source": "valide", "destination": "Fin", "condition": ""},
            ],
        },
        "custom_code": "",
        "use_custom_code": False,
    },
}


EMPTY_TABLES = {
    "flowchart": {"nodes": [], "edges": []},
    "sequence": {"participants": [], "messages": []},
    "mindmap": {"ideas": []},
    "timeline": {"events": []},
    "gantt": {"tasks": []},
    "er": {"attributes": [], "relations": []},
    "class": {"members": [], "class_relations": []},
    "journey": {"steps": []},
    "pie": {"slices": []},
    "quadrant": {"points": []},
    "state": {"states": [], "transitions": []},
}


def get_template(diagram_type: str) -> dict:
    return deepcopy(TEMPLATES[diagram_type])


def get_empty(diagram_type: str) -> dict:
    project = get_template(diagram_type)
    project["title"] = f"Nouveau {DIAGRAM_TYPES[diagram_type].lower()}"
    project["tables"] = deepcopy(EMPTY_TABLES[diagram_type])
    project["custom_code"] = ""
    project["use_custom_code"] = False
    return project
