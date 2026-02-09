# PRD - Page Insight (Sandvik Machining Insights)

## 1. Contexte et objectif

Cette PRD décrit la logique fonctionnelle et technique de la page `insight` (Streamlit) afin de permettre la ré-implémentation côté backend pour une nouvelle web app. Elle couvre :

- la configuration des machines et la logique de regroupement,
- les sources de données et les appels API,
- la structure des données retournées,
- le traitement/formatage appliqué avant affichage,
- l'expérience utilisateur (par machine et par condition),
- les exigences de fiabilité pour un backend consommable.

## 2. Portée

### Inclus
- Récupération et agrégation des métriques Sandvik Machining Insights.
- Filtrage par groupe de machines et plage de dates.
- Normalisation des identifiants machines (cleaning).
- Formatage des colonnes et types.
- Comportement UI (sélection de groupe, états d'erreurs, affichage).

### Non inclus
- Analyse avancée (graphes, KPI dérivés, alertes).
- Authentification utilisateur de la nouvelle web app.
- Données d'autres systèmes (BC, FASTEMS, SigmaNest, etc.).

## 3. Sources de données

### API Sandvik Machining Insights

- **Base URL** : `https://machininginsights.sandvikcoromant.com`
- **OAuth Token** : `POST /api/v1/auth/oauth/token`
- **Timeseries Metrics** : `POST /api/v3/timeseries-metrics/flattened`
- **Plant Device** (optionnel) : `GET /api/v1/plant/device`

Le tenant utilisé est `produitsgilbert`.

## 4. Configuration des machines (groupes)

Les machines sont exposées via des groupes, chaque groupe mappe vers une liste de `device` (UUIDs lisibles Sandvik). Cette configuration est statique dans la page.

Groupes et devices :

- **DMC 100 (Machines 1-4)**
  - `produitsgilbert_DMC_100_01_5a1286`
  - `produitsgilbert_DMC_100_02_3c11c4`
  - `produitsgilbert_DMC_100_03_9ad22c`
  - `produitsgilbert_DMC_100_04_d81500`
- **NLX-2500 (Machines 1-5)**
  - `produitsgilbert_NLX-2500-01_1f62d2`
  - `produitsgilbert_NLX-2500-02_c48076`
  - `produitsgilbert_NLX-2500-03_7db86c`
  - `produitsgilbert_NLX-2500-04_aae59b`
  - `produitsgilbert_NLX-2500-05_1291f0`
- **TOU-MZ350 (Machines 1-3)**
  - `produitsgilbert_TOU-MZ350-01_dd405f`
  - `produitsgilbert_TOU-MZ350-02_97ae33`
  - `produitsgilbert_TOU-MZ350-03_f3e3e6`
- **DMC 340 (Machine 1)**
  - `produitsgilbert_DMC_340_01_53afe9`
- **DEC 370 (Machine 1)**
  - `produitsgilbert_DEC_370_01_90441a`
- **MTV 655 (Machine 1)**
  - `produitsgilbert_MTV_655_01_65b08f`

La sélection "Toutes les machines" combine tous les devices.

## 5. Logique de sélection et conditions UI

### Sélection de groupe

- **Option "Toutes les machines"**
  - Utilise **tous** les devices.
  - Période par défaut : **10 derniers jours** (défini côté backend).
  - Aucun sélecteur de date n'est affiché.

- **Option groupe spécifique**
  - Utilise uniquement les devices du groupe.
  - Affiche un **sélecteur de dates** :
    - `start_date` par défaut = aujourd'hui - 14 jours
    - `end_date` par défaut = aujourd'hui
  - Si `start_date > end_date` : erreur UI et arrêt du traitement.

### Bouton de chargement

La page déclenche la requête lors du clic sur **"Charger les données"**. La sélection d’un groupe ouvre les contrôles, puis l'utilisateur lance le chargement.

### États utilisateur

- **Chargement** : spinner "Chargement des données depuis Sandvik Insights..."
- **Aucun résultat** : warning "Aucune donnée trouvée pour la sélection actuelle."
- **Erreur API** : message d’erreur + indication de vérifier la connexion Sandvik.

## 6. Appels API requis

### 6.1 OAuth Token

**Endpoint** : `POST /api/v1/auth/oauth/token`  
**Headers** :
```
Content-Type: application/x-www-form-urlencoded
X-Tenant: produitsgilbert
```

**Body (form urlencoded)** :
```
grant_type=password
username=apiuser
password=********
client_id=tenant_produitsgilbert
client_secret=********
```

**Réponse** : JSON avec `access_token`.

Le token est requis pour toutes les requêtes suivantes (Authorization Bearer).

### 6.2 Timeseries Metrics (principal)

**Endpoint** : `POST /api/v3/timeseries-metrics/flattened`  
**Headers** :
```
Authorization: Bearer <access_token>
Content-Type: application/json
X-Tenant: produitsgilbert
```

**Payload (structure)** :
- `filters.must` :
  - `entity.device` = liste des devices sélectionnés
  - `entity.plant` = `produitsgilbert`
  - `timestamp` range :
    - `gte` : start_date en UTC (00:00:00)
    - `lt` : end_date en UTC (23:59:59)
- `bins` :
  - `dimensions.workday` (date_histogram, day)
  - `dimensions.part_kind` (terms)
  - `entity.device` (terms)
- `metrics` :
  - `duration_sum`
  - `total_part_count`
  - `good_part_count`
  - `bad_part_count`
  - `cycle_time`
  - `producing_duration`
  - `pdt_duration`
  - `udt_duration`
  - `setup_duration`
  - `producing_percentage`
  - `pdt_percentage`
  - `udt_percentage`
  - `setup_percentage`

### 6.3 Plant Device (optionnel)

**Endpoint** : `GET /api/v1/plant/device`  
Permet de découvrir les devices disponibles (uuid).  
Le page `insight` n'utilise pas cet endpoint en runtime; la configuration des devices est statique.

## 7. Logique de regroupement (grouping)

Le regroupement principal est effectué côté API via les `bins` :

1. **`by_workday`** : regroupe par date de production (`dimensions.workday`).
2. **`by_kind`** : regroupe par type de pièce (`dimensions.part_kind`).
3. **`by_device`** : regroupe par machine (`entity.device`).

La réponse est un tableau aplati : une ligne = combinaison unique `(device, workday, part_kind)` avec métriques associées.

## 8. Transformations et nettoyage des données

Les transformations suivantes sont appliquées avant affichage :

1. **Nettoyage du nom machine**
   - Retire le préfixe `produitsgilbert_`.
   - Retire le suffixe `_xxxxxx` (6 caractères hex).
   - Exemple :
     - `produitsgilbert_DMC_100_01_5a1286` -> `DMC_100_01`

2. **Formatage du `workday`**
   - Converti en date (`YYYY-MM-DD`) à partir de la valeur string.

3. **Formatage du `kind`**
   - Regex : `^(\d{7})-(\d{3})-(\dOP)$` -> `\1_\2-\3`
   - Exemple :
     - `8322066-003-2OP` -> `8322066_003-2OP`

4. **Ordre des colonnes**
   - Si `device` présent, il est déplacé en première colonne.

5. **Avertissement data vide**
   - Si `cycle_time` est null partout **et** `total_part_count` = 0, un warning est loggé.

## 9. Schéma de réponse attendu côté backend

Le backend doit retourner un tableau d’objets JSON aligné avec la structure suivante (champs typiques) :

- `device` (string, cleaned)
- `workday` (date string `YYYY-MM-DD`)
- `kind` (string, formaté)
- `duration_sum` (number, ms)
- `total_part_count` (number)
- `good_part_count` (number)
- `bad_part_count` (number)
- `cycle_time` (number, ms)
- `producing_duration` (number, ms)
- `pdt_duration` (number, ms)
- `udt_duration` (number, ms)
- `setup_duration` (number, ms)
- `producing_percentage` (number, 0.0-1.0)
- `pdt_percentage` (number, 0.0-1.0)
- `udt_percentage` (number, 0.0-1.0)
- `setup_percentage` (number, 0.0-1.0)

Le backend doit conserver les champs tels que fournis par l'API (sans arrondis métier), sauf les transformations listées ci-dessus.

## 10. Ce que l'utilisateur voit (par machine et condition)

### Vue "Toutes les machines"

- Liste consolidée de toutes les machines configurées.
- Période par défaut : 10 derniers jours.
- Table de données détaillées :
  - une ligne par `(workday, device, kind)`
  - colonnes de métriques (durées, quantités, pourcentages).

### Vue "Groupe spécifique"

- Machines limitées au groupe sélectionné.
- Sélection d’une plage de dates (par défaut 14 jours).
- Même table détaillée, filtrée au groupe.

### Conditions d’affichage

- **Pas de données** : message d’alerte.
- **Erreur API** : message d’erreur + guidance de connexion.
- **Plage de dates invalide** : erreur immédiate, pas d’appel API.

## 11. Exigences backend pour la nouvelle web app

### Endpoints recommandés

1. **GET `/api/insight/machines`**
   - Retourne la configuration des groupes (display_name + devices).

2. **POST `/api/insight/timeseries`**
   - Body :
     - `devices: list[str]`
     - `start_date?: YYYY-MM-DD`
     - `end_date?: YYYY-MM-DD`
   - Retourne le tableau de métriques nettoyé.

### Règles clés

- Appliquer les mêmes règles de dates (10 jours par défaut pour toutes machines).
- Appliquer exactement le même nettoyage `device` et `kind`.
- Conserver le format et les unités (ms, ratios).
- Utiliser les bins et metrics identiques.
- Gérer les erreurs API et renvoyer un message clair.

## 12. Observabilité et logs

Logguer systématiquement :

- liste des `devices` demandés,
- plage de dates utilisée,
- erreurs API (HTTP status + message),
- cas sans données.

## 13. Risques et dépendances

- Dépendance forte à l’API Sandvik (auth, disponibilité).
- Mauvaise sélection de dates => absence de données.
- Liste des devices statique : si Sandvik ajoute/retire un device, la page doit être mise à jour.
