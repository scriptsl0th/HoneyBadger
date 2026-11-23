# Rapport de projet : HoneyBadger

*Honeypot SSH/HTTP avec classification MITRE ATT&CK et évaluation de la détection d'intrusions par apprentissage automatique.*

Groupe de six étudiants. Version du 21 novembre 2026, sur la base du commit `93a9d69` et des modifications locales décrites dans `CHANGELOG.md`.

---

## Résumé

HoneyBadger est un honeypot construit par l'équipe : un faux serveur SSH et un faux site web acceptent les connexions des attaquants, simulent un système crédible sans rien exécuter, et enregistrent chaque action. Un pipeline asynchrone enrichit chaque événement (géolocalisation, technique MITRE ATT&CK, sévérité), le stocke dans PostgreSQL et l'affiche en temps réel sur un tableau de bord React ; Prometheus et Grafana assurent la supervision. Le honeypot ne disposant pas d'étiquettes, nous avons évalué l'apprentissage automatique sur un jeu public de 25 192 connexions étiquetées. Avec étiquettes, une forêt aléatoire détecte 99,6 % des attaques sans fausse alerte (F1 = 0,998). Sans étiquettes, en n'apprenant que le trafic normal, un One-Class SVM détecte 84,3 % des attaques pour 1 % de fausses alertes. Par regroupement (clustering), les 11 743 attaques se répartissent en cinq familles stables et interprétables (SYN flood, scan de ports, balayage ICMP, flood ICMP/UDP, attaque après connexion), rattachées à des techniques MITRE ATT&CK à titre d'hypothèse. Restreints aux variables que le honeypot sait calculer, ces résultats se dégradent (F1 = 0,984, rappel 45,9 %, familles partiellement confondues) : le honeypot doit enregistrer les octets échangés et l'issue des connexions. Le système a été testé de bout en bout ; sept bugs ont été trouvés et corrigés.

## 1. Introduction

Tout serveur exposé sur Internet reçoit en permanence des tentatives d'intrusion automatisées. Comprendre ces attaques (identifiants essayés, commandes, logiciels malveillants, pages web sondées) permet de mieux défendre les vrais systèmes. Un honeypot est un système leurre sans utilisateur légitime : tout trafic qu'il reçoit est suspect, ce qui fournit des données d'attaque propres sans exposer de ressources réelles.

**Objectifs.**
1. Capturer les attaques SSH et HTTP sans risque pour la machine hôte.
2. Classer chaque action selon MITRE ATT&CK et la visualiser en temps réel.
3. Évaluer la détection automatique d'attaques : avec étiquettes (objectif 1), sans étiquettes (objectif 2) et par regroupement des attaques en familles (objectif 3).

## 2. Contexte

- **MITRE ATT&CK** est une base publique de techniques d'attaque identifiées par un code (par exemple T1110, *Brute Force*). L'utiliser permet de décrire les événements dans le vocabulaire des équipes de sécurité.
- **NSL-KDD** (Tavallaee et al., 2009) est une version nettoyée du jeu KDD Cup 1999. Il reste un banc d'essai classique, mais il est souvent critiqué comme peu représentatif du trafic actuel. Le jeu Kaggle utilisé a exactement la taille des fichiers NSL-KDD « 20 % » et « KDDTest+ ».
- **Détection d'anomalies** : Isolation Forest (Liu et al., 2008), One-Class SVM (Schölkopf et al., 2001) et Local Outlier Factor (Breunig et al., 2000) apprennent ce qui est normal et signalent ce qui s'en écarte.
- **Regroupement** : K-Means, mélange gaussien et DBSCAN (Ester et al., 1996) forment des groupes sans étiquettes ; la qualité se mesure par le score de silhouette (Rousseeuw, 1987), les indices de Davies-Bouldin et de Calinski-Harabasz, et la stabilité (indice de Rand ajusté).

## 3. Architecture

| Composant | Rôle | Fichiers |
|---|---|---|
| Capteur SSH | Accepte toute connexion, shell simulé, interception de `wget`/`curl` | `backend/sshd.py`, `backend/fakeshell.py` |
| Capteur HTTP | Pages appâts, extraction et hachage des identifiants | `backend/httpd.py`, `backend/http_routes.py` |
| Bus d'événements | Files `asyncio` en mémoire qui découplent capture et traitement | `backend/bus.py` |
| Pipeline | GeoIP → classification ATT&CK → identifiants → charges utiles → stockage | `backend/pipeline.py`, `backend/mitre.py` |
| Stockage | PostgreSQL, migrations Alembic, rétention de 6 mois | `backend/storage.py`, `backend/db/` |
| API | REST (`/events`, `/stats`, `/stats/timeseries`) et WebSocket | `backend/api.py` |
| Tableau de bord | Console React en temps réel | `dashboard/` |
| Supervision | Prometheus, Grafana, Alertmanager | `monitoring/` |

Le système se lance par `docker compose up` (six conteneurs). Principes de sécurité : aucun mot de passe en clair (empreintes `sha256:`), aucune commande exécutée, aucune charge utile téléchargée, base accessible uniquement en local.

## 4. Méthodologie d'apprentissage

**Données.** 25 192 connexions étiquetées (13 449 normales, 11 743 attaques), 41 variables ; 22 544 connexions non étiquetées. Aucune valeur manquante ; deux colonnes constantes supprimées.

**Protocole.** Séparation 80/20 stratifiée par classe ; les vecteurs de variables identiques sont regroupés pour ne jamais apparaître des deux côtés. Tout le prétraitement (encodage one-hot, `log1p` et standardisation pour les modèles sensibles à l'échelle) est ajusté sur l'entraînement seulement. Graine aléatoire 42. Les 5 039 connexions de validation (2 349 attaques) servent une seule fois.

**Objectif 1 (supervisé).** Référence naïve, régression logistique, arbre de décision, forêt aléatoire ; hyperparamètres choisis par validation croisée groupée à 5 plis sur l'entraînement, en maximisant le F1 de la classe attaque.

**Objectif 2 (non supervisé).** Isolation Forest, One-Class SVM et LOF entraînés sur les seules connexions normales (8 607). Seuil d'alerte : 99e percentile des scores sur 2 152 autres connexions normales, soit environ 1 % de fausses alertes. Les étiquettes ne servent qu'à l'évaluation.

**Objectif 3 (regroupement).** K-Means, mélange gaussien et DBSCAN appliqués aux seules attaques : 9 394 de la partie entraînement pour apprendre les groupes, 2 349 de la validation pour vérifier qu'ils se généralisent. `log1p`, standardisation et encodage one-hot ajustés sur les attaques d'entraînement ; ACP pour la visualisation en 2D. Nombre de groupes choisi par la méthode du coude, la silhouette et Davies-Bouldin (k = 6).

**Métriques.** Précision, rappel, F1, ROC-AUC, PR-AUC, matrice de confusion ; pour l'objectif 2, rappel à 1 % de faux positifs ; pour l'objectif 3, silhouette, Davies-Bouldin, Calinski-Harabasz et stabilité (ARI) entre graines, sous-échantillons et partition de validation. L'exactitude seule n'est pas utilisée pour conclure.

## 5. Résultats

**Objectif 1.**

| Modèle | Précision | Rappel | F1 | Fausses alertes | Attaques manquées |
|---|---|---|---|---|---|
| Référence naïve | 0,000 | 0,000 | 0,000 | 0 | 2 349 |
| Régression logistique | 0,989 | 0,977 | 0,983 | 25 | 53 |
| Arbre de décision | 0,997 | 0,995 | 0,996 | 8 | 11 |
| Forêt aléatoire | 1,000 | 0,996 | 0,998 | 0 | 10 |

F1 en validation croisée de la forêt : 0,9975 ± 0,0007. Variables les plus utilisées : octets envoyés et reçus, drapeau TCP, service.

**Objectif 2.**

| Modèle | ROC-AUC | Rappel à 1 % de faux positifs |
|---|---|---|
| Isolation Forest | 0,983 | 0,832 |
| One-Class SVM | 0,977 | 0,843 |
| Local Outlier Factor | 0,932 | 0,196 |
| Score aléatoire | 0,503 | 0,009 |

LOF manque 100 % des 1 340 attaques de type SYN flood (drapeau `S0`). Les deux autres détecteurs manquent surtout des connexions qui se terminent normalement.

**Objectif 3.**

| Modèle | Groupes | Silhouette | Davies-Bouldin | Stabilité (ARI min. entre graines) |
|---|---|---|---|---|
| K-Means | 6 | 0,568 | 0,893 | 0,999 |
| Mélange gaussien | 6 | 0,558 | 0,952 | 0,870 |
| DBSCAN | 22 (+ 2,3 % de bruit) | 0,575 | 0,619 | déterministe |

Les trois méthodes trouvent le même découpage (ARI de 0,90 à 0,97). Sur la partition de validation, les groupes K-Means se retrouvent à l'identique (ARI = 0,97). Familles obtenues et technique MITRE proposée (hypothèse, invérifiable faute d'étiquettes de type d'attaque) : SYN flood, 60 % (T1499) ; scan de ports refusés, 22 % (T1595) ; balayage ICMP, 8 % (T1595) ; flood ICMP/UDP, 8 % (T1498) ; attaque après connexion sur HTTP/FTP, 2 % (T1190/T1078) ; plus une connexion isolée. Aucune famille de force brute : seules 11 attaques comportent des échecs de connexion.

**Lien avec HoneyBadger.** Avec seulement les 11 variables que le honeypot peut calculer : F1 = 0,984 (objectif 1), rappel = 0,459 à 1 % de faux positifs (objectif 2) et ARI = 0,57 avec les familles complètes (objectif 3 : sans l'issue de la connexion TCP, scans et SYN floods se confondent).

**Reproductibilité.** `python scripts/run_analysis.py` réexécute les trois notebooks et vérifie 74 valeurs : 74/74 avec scikit-learn 1.9. Les objectifs 1 et 2 ont aussi été vérifiés avec pandas 2.2 / scikit-learn 1.6.

## 6. Validation du système

Le système complet (PostgreSQL, backend, tableau de bord) a été exécuté et attaqué avec les 13 scénarios de l'équipe. Avant corrections : la suite pytest ne s'exécutait pas, 7 scénarios sur 13 réussissaient et le backend produisait 10 erreurs. Après corrections : 97 tests réussis, 10 scénarios sur 13, aucune erreur. Les sept bugs corrigés sont détaillés dans `docs/TEST_REPORT.md`. Les trois échecs restants relèvent d'une définition à trancher entre force brute (T1110) et *credential stuffing* (T1110.004), et d'une règle T1078 inatteignable.

## 7. Discussion et limites

- Les scores d'apprentissage proviennent d'un jeu public ancien, plus facile que le trafic réel. Ils valident la méthode, pas une performance en production.
- Aucune connexion SSH normale dans les données : les fausses alertes SSH ne sont pas mesurables.
- Les variables les plus utiles (octets, issue de la connexion) ne sont pas enregistrées par le honeypot.
- Les noms de familles et les techniques MITRE de l'objectif 3 sont des hypothèses : le jeu de données n'indique pas le type d'attaque.
- La pile Docker n'a pas pu être démarrée dans l'environnement de test ; ses composants ont été testés sans Docker.

## 8. Conclusion et perspectives

HoneyBadger capture, classe et visualise les attaques sans risque pour l'hôte. L'analyse montre qu'une détection automatique est possible, très précise avec étiquettes et encore utile sans étiquettes, à condition que le honeypot enregistre les bonnes informations. Perspectives : enregistrer les octets et l'issue des connexions ; exposer le honeypot sur un serveur réel ; étiqueter un échantillon de sessions et évaluer avec une séparation temporelle ; appliquer les familles de l'objectif 3 aux sessions du honeypot et les comparer aux techniques déjà attribuées par ses règles ; trancher la définition des techniques T1110.

## Références

- Breiman, L. (2001). Random Forests. *Machine Learning*, 45(1), 5–32.
- Breunig, M. M., Kriegel, H.-P., Ng, R. T., & Sander, J. (2000). LOF: Identifying Density-Based Local Outliers. *ACM SIGMOD*.
- Ester, M., Kriegel, H.-P., Sander, J., & Xu, X. (1996). A Density-Based Algorithm for Discovering Clusters in Large Spatial Databases with Noise. *KDD*.
- Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *IEEE ICDM*.
- Rousseeuw, P. J. (1987). Silhouettes: a graphical aid to the interpretation and validation of cluster analysis. *Journal of Computational and Applied Mathematics*, 20, 53–65.
- Pedregosa, F., et al. (2011). Scikit-learn: Machine Learning in Python. *Journal of Machine Learning Research*, 12, 2825–2830.
- Schölkopf, B., Platt, J. C., Shawe-Taylor, J., Smola, A. J., & Williamson, R. C. (2001). Estimating the Support of a High-Dimensional Distribution. *Neural Computation*, 13(7), 1443–1471.
- Tavallaee, M., Bagheri, E., Lu, W., & Ghorbani, A. A. (2009). A Detailed Analysis of the KDD CUP 99 Data Set. *IEEE CISDA*.
- MITRE ATT&CK : https://attack.mitre.org
- Jeu de données : https://www.kaggle.com/datasets/sampadab17/network-intrusion-detection
