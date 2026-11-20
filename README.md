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

Python 3.12 est recommandé. Depuis la racine du dépôt :

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Dans deux terminaux, toujours depuis la racine du dépôt :

```bash
.venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

```bash
.venv/bin/streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

L'interface est disponible à `http://127.0.0.1:8501`. FastAPI expose également sa
documentation interactive à `http://127.0.0.1:8000/docs`. Streamlit communique avec FastAPI
par HTTP ; il ne charge plus directement le fichier Parquet ni le modèle.

## Tester et vérifier le style

```bash
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
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
L'onglet scénario présente aussi l'importance par permutation des variables, calculée sur
l'année de test : elle indique quelles variables aident le modèle à classer les accidents graves,
pas quelles sont les causes des accidents. Des variables corrélées peuvent se partager cette
importance.

## Architecture

- `backend/api.py` : API FastAPI (`/health`, `/options`, `/dashboard`, `/scenario`).
- `backend/data.py` : validation, préparation et agrégations métier.
- `backend/model.py` : variables préalables à l'accident, pipeline sklearn, test temporel et score.
- `frontend/app.py` : interface Streamlit, appels HTTP à l'API et graphiques.
- `data/securite_routiere.parquet` : données nécessaires au fonctionnement autonome de l'appli.
- `tests/` : tests des filtres, créneaux de contrôle, absence de fuite de cible et test temporel.
- `requirements-backend.txt` et `requirements-frontend.txt` : dépendances séparées des deux services.
- `.env.example` : exemple des variables de configuration ; copier en `.env` pour le lancement local.

FastAPI lit et met en cache le Parquet au premier appel ; le modèle est entraîné et mis en cache
au premier appel à `/scenario`. Streamlit met en cache les réponses HTTP pour éviter de redemander
les mêmes données à chaque rafraîchissement.

## Présentation et répartition à trois

Déroulé possible pour une démonstration de 5 minutes :

1. **Membre 1 (1 min)** — décision métier, source, filtres communs et trois indicateurs.
2. **Membre 2 (2 min)** — carte, classement par commune, choix d'une commune pour afficher
   ses accidents et classement des trois créneaux.
3. **Membre 3 (2 min)** — comparaison météo, nuit/jour et routes, puis scénario ML et test temporel.

Puis répondez ensemble aux questions. Chaque membre doit pouvoir expliquer le filtre, une
agrégation et la différence entre le score ML et un risque réel. Pour préparer l'oral :

- **Pourquoi Streamlit ?** Le cours le couvre et il convient à un tableau de bord Python.
  Streamlit gère l'interface et les filtres ; FastAPI centralise les données, agrégations et
  prédictions derrière des routes HTTP.
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

## Déploiement sur un VPS Linux

### Commandes de lancement

Depuis la racine du dépôt, après installation des dépendances, les commandes de production sont :

```bash
.venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port 8000
.venv/bin/streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

FastAPI reste lié à `127.0.0.1` : seule l'application Streamlit doit être publiée derrière le
reverse proxy HTTPS. Ne pas ouvrir le port 8000 au public. Le port 8501 est destiné au reverse
proxy ; le domaine public doit servir Streamlit en HTTPS et autoriser les WebSockets nécessaires
au rafraîchissement de l'interface.

### Variables et fichiers à configurer

Les variables lues par l'application sont :

| Variable | Utilisée par | Valeur par défaut / exemple | Rôle |
|---|---|---|---|
| `API_BASE_URL` | Streamlit | `http://127.0.0.1:8000` | URL FastAPI joignable depuis le processus Streamlit ; utiliser l'adresse privée du backend s'ils sont sur deux machines. |
| `BAAC_DATA_PATH` | FastAPI | `data/securite_routiere.parquet` à la racine du dépôt | Chemin du fichier Parquet sur le VPS. |

En local, les valeurs se mettent dans `.env` à la racine (à créer depuis `.env.example`, non
versionné). Sur un VPS avec systemd, stocker les valeurs de production dans un fichier dédié,
par exemple `/etc/vigie-routiere/vigie.env`, puis le référencer avec
`EnvironmentFile=/etc/vigie-routiere/vigie.env` dans les deux services. Le chemin du dépôt,
l'utilisateur Linux, le nom de domaine, l'adresse API et le chemin des données sont à adapter.
Protéger ce fichier (`root` ou utilisateur de service, permissions `0640`) et ne pas y mettre de
secrets dans Git.

### Préparation et vérification

Exemple pour un dépôt installé dans `/opt/vigie-routiere` :

```bash
cd /opt/vigie-routiere
python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-backend.txt -r requirements-frontend.txt
sudo install -d -o root -g vigie -m 0750 /etc/vigie-routiere
sudo install -o root -g vigie -m 0640 .env.example /etc/vigie-routiere/vigie.env
sudoedit /etc/vigie-routiere/vigie.env
```

Avant de créer les services, vérifier les deux commandes de lancement ci-dessus. Vérifier ensuite
l'API avec `curl http://127.0.0.1:8000/health` (réponse attendue : `{"status":"ok"}`), puis
`curl http://127.0.0.1:8000/options`. `/docs` permet d'inspecter les paramètres et le contrat des
routes.

### Services systemd

Créer au préalable le compte et le groupe système `vigie`, et donner à ce compte les droits de
lecture/traversée sur le dépôt, l'environnement virtuel et le fichier Parquet.

Créer `/etc/systemd/system/vigie-backend.service` :

```ini
[Unit]
Description=Vigie Loiret FastAPI
After=network.target

[Service]
User=vigie
Group=vigie
WorkingDirectory=/opt/vigie-routiere
EnvironmentFile=/etc/vigie-routiere/vigie.env
ExecStart=/opt/vigie-routiere/.venv/bin/uvicorn backend.api:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Créer `/etc/systemd/system/vigie-frontend.service` avec :

```ini
[Unit]
Description=Vigie Loiret Streamlit
After=network.target vigie-backend.service
Requires=vigie-backend.service

[Service]
User=vigie
Group=vigie
WorkingDirectory=/opt/vigie-routiere
EnvironmentFile=/etc/vigie-routiere/vigie.env
ExecStart=/opt/vigie-routiere/.venv/bin/streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Avec Nginx en reverse proxy local sur le même VPS, Streamlit peut écouter sur `127.0.0.1` comme
dans l'unité ci-dessus. Après avoir configuré le proxy HTTPS vers `127.0.0.1:8501` :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now vigie-backend vigie-frontend
sudo systemctl status vigie-backend vigie-frontend
sudo journalctl -u vigie-backend -u vigie-frontend -f
```

En cas d'erreur, vérifier les journaux systemd, le droit de lecture du Parquet par l'utilisateur
`vigie`, la valeur de `BAAC_DATA_PATH`, et la connectivité vers `API_BASE_URL`. Les premiers accès
à `/options` et `/scenario` peuvent prendre plus longtemps pendant le chargement des données et
l'entraînement du modèle.

Le workflow GitHub Actions `.github/workflows/deploy.yml` suppose également un dépôt dans
`/opt/vigie-routiere`, un environnement `.venv`, l'accès SSH et les secrets GitHub `VPS_HOST`,
`VPS_USER`, `VPS_SSH_KEY`, `VPS_PORT`, ainsi que les deux services systemd ci-dessus. Adapter
son chemin si le dépôt est installé ailleurs.

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
