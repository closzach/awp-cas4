# Vigie routière — sécurité routière dans le Loiret

Application de données pour aider le service sécurité routière de la préfecture à choisir
**où et quand concentrer ses actions de prévention et de contrôle**.

## Décision et questions métier

> **Décision à soutenir :** parmi les accidents corporels recensés dans le Loiret, quelles
> communes, routes et plages horaires méritent d'être examinées en priorité pour organiser
> les actions de prévention ?

L'application répond aux questions du cas 4 :

1. **Quelles communes et routes ont le plus d'accidents graves ?** Carte des accidents,
   classement des communes et comparaison descriptive des routes.
2. **À quelle heure, quel jour ? La nuit est-elle plus grave ?** Carte de chaleur jour × heure,
   trois créneaux hebdomadaires classés par nombre d'accidents graves et comparaison de la part
   grave selon l'éclairage.
3. **La pluie ou le brouillard changent-ils la gravité ?** Comparaison des parts observées par
   météo, avec les effectifs visibles et un avertissement contre toute conclusion causale.
4. **Quels trois créneaux couvrir ?** Classement des trois couples jour/heure les plus fréquents
   parmi les accidents graves. Chaque créneau correspond ici à une heure ; sa couverture est
   calculée sur les accidents graves historiques de la sélection.

Sur l'ensemble du fichier, Orléans arrive en tête avec 90 accidents graves. Les trois créneaux
classés sont samedi 17 h (21 cas graves), jeudi 17 h (19) et dimanche 18 h (19) : ensemble,
ils représentent 59 des 1 207 accidents graves observés (4,9 %). La part grave est de 44,2 %
la nuit (357/807) contre 33,9 % en plein jour (751/2 218). Le brouillard affiche 63,9 %, mais
sur seulement 36 accidents. Ce sont des constats descriptifs, pas des taux de risque routier ni
des estimations de l'effet d'un contrôle.

## Démarrer en local

Python 3.12 est recommandé pour être cohérent avec le déploiement Streamlit du cours.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
streamlit run app.py
```

Le navigateur s'ouvre sur `http://localhost:8501`. Les filtres de période, commune et type de
route se trouvent dans la barre latérale et s'appliquent aux graphiques et indicateurs.

## Tester et vérifier le style

```powershell
python -m pytest
python -m ruff check .
```

## Données et précautions

- **Source :** fichier BAAC / ONISR fourni pour le projet, sous Licence Ouverte.
- **Périmètre :** 3 242 accidents corporels, dans le Loiret, de 2019 à 2025 inclus.
- Une ligne représente un accident ; elle ne représente ni le trafic, ni une exposition au risque.
- Un accident est dit **grave** ici s'il a entraîné au moins un hospitalisé ou un décès
  (définition de la variable fournie). Cette cible n'est pas un indicateur du nombre de victimes.
- Les données source contiennent le caractère de remplacement `�` dans certains libellés ;
  l'interface le remplace par `e` afin d'éviter de montrer un symbole illisible. Les valeurs
  d'origine et les mesures ne sont pas modifiées.
- Une part élevée d'accidents graves dans une catégorie ne prouve pas que cette catégorie
  provoque les accidents. Il n'y a pas de mesure de circulation, de kilomètres parcourus,
  d'effectif de contrôle ou de précision géographique permettant de mesurer un risque causal.
- Les catégories ayant moins de 20 accidents sont masquées dans les comparaisons de gravité,
  mais restent visibles sur la carte et dans les détails.

## Couche de machine learning

Le modèle est une **forêt aléatoire** qui classe la gravité parmi les accidents corporels
historiques, en utilisant seulement des caractéristiques disponibles avant l'accident :
mois, jour de semaine, heure, coordonnées, vitesse maximale affichée, luminosité, météo et type
de route. Le nombre de victimes, l'indicateur `grave` et les autres résultats de l'accident
sont exclus des variables : les utiliser créerait une fuite de cible.

L'évaluation respecte le temps : apprentissage sur 2019–2024 et test sur l'année la plus récente
(2025). Les métriques affichées comprennent AUC ROC, exactitude, précision, rappel, F1,
l'effectif du test et la comparaison avec une règle majoritaire. Après cette évaluation, le
modèle de prédiction est réentraîné sur toutes les années. Le score de scénario sert à comparer
des contextes ; il n'est pas une probabilité individuelle calibrée et ne mesure pas le risque
par véhicule-kilomètre.

Sur le jeu fourni, le test 2025 porte sur 413 accidents (apprentissage : 2 829). Le résultat
reproductible est AUC ROC **0,81**, rappel **74 %**, précision **67 %** et exactitude **76,8 %**,
contre **62,7 %** pour la règle majoritaire. L'AUC mesure la qualité du classement ; le rappel,
la proportion de cas graves détectés au seuil choisi. Ces chiffres restent estimés sur un seul
millésime de test.

La carte et les graphiques sont descriptifs ; seul l'onglet scénario utilise le modèle. Cette
séparation évite de présenter une association observée comme une prédiction.

## Architecture

- `app.py` : interface Streamlit, interactions, filtres et graphiques.
- `data.py` : validation, préparation et agrégations métier, séparées de l'affichage.
- `model.py` : variables préalables à l'accident, pipeline sklearn, test temporel et score.
- `data/securite_routiere.parquet` : données nécessaires au fonctionnement autonome de l'appli.
- `tests/` : tests des filtres, créneaux de contrôle, absence de fuite de cible et test temporel.

Le fichier Parquet est lu avec `st.cache_data` et le modèle entraîné avec `st.cache_resource`.
L'évaluation se fait sur 2025 avant le réentraînement du modèle final sur tout l'historique.

## Présentation et répartition à trois

Déroulé possible pour une démonstration de 5 minutes :

1. **Membre 1 (1 min)** — décision métier, source, filtres communs et trois indicateurs.
2. **Membre 2 (2 min)** — carte, classement par commune, choix d'une commune pour afficher
   ses accidents et classement des trois créneaux.
3. **Membre 3 (2 min)** — comparaison météo, nuit/jour et routes, puis scénario ML et test temporel.

Puis répondez ensemble aux questions. Chaque membre doit pouvoir expliquer le filtre, une
agrégation et la différence entre le score ML et un risque réel. Pour préparer l'oral :

- **Pourquoi Streamlit ?** Le cours le couvre, il convient à un tableau de bord Python et permet
  de relier filtres, graphiques et détail sans construire une API distincte.
- **Pourquoi une forêt aléatoire ?** Elle capte des relations non linéaires entre l'heure,
  la localisation, la météo et le type de route ; la comparaison hors année vérifie son
  classement sur une période future.
- **Pourquoi ne pas prédire le nombre d'accidents ?** Le fichier ne contient que les accidents
  corporels observés, pas le trafic exposé. On peut comparer des historiques ou des scénarios,
  pas prédire le risque de circulation ni l'effet d'un contrôle.
- **Que signifie l'AUC ?** La capacité à classer un cas grave devant un cas non grave ; 0,5
  correspond au hasard. Ce n'est pas une garantie de calibration ni une mesure de causalité.
- **Que faudrait-il ajouter pour décider réellement des contrôles ?** Comptages de trafic,
  accidents non corporels, exposition horaire et géographique, localisation plus précise,
  coûts et résultats des contrôles.

## Mise en ligne

Le dépôt contient `app.py`, `requirements.txt` et le Parquet pour un déploiement Streamlit
Community Cloud. Depuis le dépôt GitHub du groupe, créez une application en sélectionnant
`app.py`, puis choisissez Python 3.12. **L'application n'est pas publiée par cette étape** :
ajoutez son URL au README avant la soutenance pour obtenir les points « en ligne et fonctionnelle ».

## Correspondance avec le barème

| Attendu | Réponse dans le projet |
|---|---|
| En ligne et fonctionnelle | App Streamlit et instructions de publication ci-dessus |
| Interactivité | 3 filtres partagés, choix d'une commune et tableau de détail |
| Pertinence métier | Décision explicite et réponses aux quatre questions du cas |
| Lisibilité / accessibilité | Interface responsive, titres-conclusions, légendes textuelles et effectifs |
| Couche ML | Score de scénario et métriques sur l'année tenue à l'écart |
| Qualité du code | Calculs séparés, cache et tests ciblés |
| Framework / soutenance | Streamlit justifié, explications et rôles proposés |
| Version intermédiaire / retours | À compléter par le groupe après la démo intermédiaire |
