# Mermaid Studio

Mermaid Studio est une application Streamlit permettant de créer des diagrammes Mermaid sans saisir leur syntaxe. Les tableaux et formulaires guident la création, tandis que Mermaid assure automatiquement la mise en page.

## Fonctions principales

- 11 types de diagrammes : processus et organigrammes, séquences, cartes mentales, chronologies, Gantt, modèles entité-relation, classes, parcours utilisateur, secteurs, matrices et états ;
- modèles français prêts à modifier ;
- ajout et suppression de lignes directement dans les tableaux ;
- canvas visuel pour les processus et organigrammes ;
- aperçu Mermaid avec signalement des erreurs ;
- mode Mermaid manuel facultatif ;
- import d’un projet JSON ou d’un fichier Mermaid ;
- export JSON, MMD, HTML autonome, SVG et PNG.

## Lancement rapide sous Windows

1. Installez Python 3.11 ou une version plus récente.
2. Décompressez le dossier.
3. Double-cliquez sur `lancer_app.bat`.
4. Lors du premier lancement, laissez quelques instants à Python pour installer les dépendances.

## Lancement en ligne de commande

```bash
python -m venv .venv
```

Sous Windows :

```bash
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Sous macOS ou Linux :

```bash
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Utilisation

1. Choisissez un type de diagramme dans la barre latérale.
2. Modifiez le modèle ou cliquez sur **Projet vide**.
3. Ajoutez les éléments et relations dans les tableaux.
4. Consultez l’onglet **Aperçu**.
5. Pour un processus, le **Canvas visuel** permet de déplacer et relier les blocs à la souris. Faites un clic droit dans le vide pour créer un bloc ou sur un bloc pour le modifier.
6. Téléchargez le projet JSON pour pouvoir le reprendre ultérieurement.

## Connexion internet

L’affichage Mermaid charge la bibliothèque Mermaid 11 depuis jsDelivr. Une connexion internet est donc nécessaire dans le navigateur. L’application peut être rendue totalement autonome en hébergeant localement le fichier JavaScript Mermaid et en adaptant l’import présent dans `app.py`.

## Sécurité

Le rendu Mermaid utilise le niveau de sécurité `strict`. N’activez pas de code HTML ou JavaScript provenant d’une source inconnue dans le mode avancé.
