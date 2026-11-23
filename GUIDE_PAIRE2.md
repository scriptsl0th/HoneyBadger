---
title: "HoneyBadger · Paire 2 — Guide pas à pas"
subtitle: "Détecter les attaques sans étiquettes (détection d’anomalies) · pour Siwar et Shayma"
date: "22 novembre 2026"
---

# 0. En bref

Ce zip contient **tout le travail de l’objectif 2** (Paire 2), prêt à être exécuté, vérifié et présenté :

- le notebook déjà exécuté, avec ses résultats visibles ;
- les données ;
- un script qui vérifie automatiquement que vous obtenez les mêmes résultats.

Le travail a été préparé par Aymen pour vous. **Il vous reste à l’exécuter, le relire, le comprendre et le confirmer** (section 6). Rien n’a encore été mis sur GitHub : il y sera ajouté seulement après votre accord.

Temps nécessaire : environ 10 minutes pour l’exécuter et le vérifier, puis 1 à 2 heures pour le relire et le comprendre.

# 1. Contenu du zip

| Fichier | À quoi il sert |
|---|---|
| `notebooks/pair2_anomaly_detection.ipynb` | **Le notebook de la Paire 2.** Il est déjà exécuté : on peut le lire tel quel, graphiques compris. |
| `data/Train_data.csv` | Données d’entraînement : 25 192 connexions réseau étiquetées (normal / anomaly). |
| `data/Test_data.csv` | Données de test : 22 544 connexions sans étiquette. |
| `results/predictions/pair2_predictions.csv` | Résultat produit par le notebook : un score d’anomalie par ligne de `Test_data.csv`. |
| `results/pair2_results.json` | Les réglages et les résultats chiffrés, enregistrés par le notebook. |
| `scripts/run_analysis.py` | Réexécute le notebook et vérifie les 24 chiffres clés. |
| `scripts/expected_results.json` | Les chiffres de référence utilisés par cette vérification. |
| `requirements-analysis.txt` | Liste des bibliothèques Python à installer (option B). |
| `docs/RESULTS_AND_ANALYSIS.md` | Résultats des objectifs 1 et 2, avec leur interprétation. |
| `docs/PROFESSOR_QA.md` | Questions probables du professeur, avec des réponses (en français). |
| `docs/PRESENTATION_SCRIPT.md` | Le script de la présentation orale (en français). |
| `GUIDE_PAIRE2.pdf` / `.md` | Ce guide. |

**Données :** elles viennent du jeu public Kaggle *sampadab17/network-intrusion-detection* (<https://www.kaggle.com/datasets/sampadab17/network-intrusion-detection>). Sa licence n’est pas indiquée sur Kaggle : gardez les CSV pour le travail du groupe et **ne les mettez jamais sur GitHub** (le fichier `.gitignore` du projet les exclut déjà).

# 2. Ce que fait votre partie, en 5 phrases

1. **La question :** peut-on repérer les attaques **sans jamais montrer d’attaque au modèle** ?
2. **L’idée :** le modèle apprend uniquement à quoi ressemble le trafic **normal** ; tout ce qui s’en éloigne trop devient suspect.
3. **Trois détecteurs sont comparés :** Isolation Forest, One-Class SVM et Local Outlier Factor (LOF).
4. **Le seuil d’alerte** est choisi pour que 1 % seulement du trafic normal déclenche une fausse alerte. Il est fixé sur des connexions normales mises de côté, sans utiliser d’étiquette d’attaque.
5. **Le résultat :** le meilleur détecteur attrape environ 84 % des attaques pour 1 % de fausses alertes. Avec étiquettes (Paire 1), on fait mieux : l’écart mesure la valeur des étiquettes.

# 3. Option A — Google Colab (recommandée, rien à installer)

1. **Décompressez le zip** sur votre ordinateur : clic droit › *Extraire tout*.
2. Ouvrez **<https://colab.research.google.com>** et connectez-vous avec votre compte Google.
3. Menu **Fichier › Importer un notebook** › onglet **Importer** › choisissez `pair2_anomaly_detection.ipynb`.
4. **Ajoutez les données avant d’exécuter quoi que ce soit :**
   - cliquez sur l’icône **dossier** (*Fichiers*) dans la barre de gauche ;
   - cliquez sur l’icône **Importer** (une feuille avec une flèche vers le haut) ;
   - sélectionnez **`Train_data.csv`** et **`Test_data.csv`** ;
   - attendez que les deux fichiers apparaissent dans la liste, puis cliquez sur **OK** si Colab affiche un avertissement sur la suppression des fichiers.
5. Menu **Exécution › Tout exécuter** (ou Ctrl + F9).
6. Attendez la fin : environ **1 à 3 minutes**. Une cellule en cours affiche une petite roue qui tourne ; quand toutes les cellules ont un numéro, c’est fini.
7. **Vérifiez** que les chiffres correspondent au tableau de la section 5.
8. Pour garder vos résultats :
   - dans le panneau *Fichiers*, ouvrez le dossier `results` ;
   - téléchargez `pair2_results.json` (clic sur les trois points › *Télécharger*) ;
   - faites de même pour `pair2_predictions.csv`.

**Attention :** Colab efface les fichiers importés quand la session se ferme. Si vous revenez plus tard, refaites l’étape 4 avant de tout exécuter.

**Si vous avez oublié l’étape 4,** la cellule « Load the data » essaie d’abord de télécharger les données depuis Kaggle. Si cela échoue, elle affiche un bouton **« Choisir des fichiers »** : sélectionnez alors les deux CSV.

# 4. Option B — Sur votre PC Windows

À faire une seule fois :

1. Installez **Python 3.10 ou plus récent** depuis <https://www.python.org/downloads/>. Pendant l’installation, **cochez « Add python.exe to PATH »**.
2. Décompressez le zip, par exemple dans `C:\Users\<vous>\Documents\HoneyBadger-Paire2`.
3. Ouvrez ce dossier dans l’Explorateur de fichiers, cliquez dans la barre d’adresse, tapez `powershell` puis Entrée.
4. Dans PowerShell, tapez ces commandes une par une :

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-analysis.txt notebook
```

Si PowerShell refuse d’activer l’environnement (« l’exécution de scripts est désactivée »), tapez d’abord la commande suivante, puis recommencez la deuxième ligne :

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Ensuite, à chaque fois, deux façons de travailler :

- **Vérifier automatiquement** (exécute tout le notebook et compare les 24 chiffres clés) :

  ```powershell
  .venv\Scripts\Activate.ps1
  python scripts\run_analysis.py --only pair2
  ```

  Résultat attendu, en moins d’une minute : `pair2: 24/24 checks passed` puis `All checks passed.`

- **Ouvrir le notebook pour le lire et l’exécuter cellule par cellule :**

  ```powershell
  .venv\Scripts\Activate.ps1
  jupyter notebook notebooks/pair2_anomaly_detection.ipynb
  ```

  Le navigateur s’ouvre. Pour exécuter une cellule, faites Maj + Entrée ; pour tout exécuter, utilisez le menu *Run › Run All Cells*.

# 5. Les résultats à retrouver

Ces résultats portent sur **5 039 connexions de validation** (2 349 attaques et 2 690 connexions normales), jamais utilisées pour l’entraînement.

| Détecteur | ROC-AUC | Rappel à 1 % de fausses alertes | Attaques détectées au seuil | Fausses alertes |
|---|---|---|---|---|
| Score aléatoire (référence) | 0,503 | 0,009 | 28 | 32 |
| **One-Class SVM (retenu)** | **0,977** | **0,843** | **1 849** | **21** |
| Isolation Forest | 0,983 | 0,832 | 1 973 | 32 |
| Local Outlier Factor | 0,932 | 0,196 | 269 | 21 |
| Forêt aléatoire avec étiquettes (Paire 1, pour comparer) | 1,000 | 1,000 | 2 339 | 0 |

Autres chiffres que le notebook doit afficher :

- **Données utilisées :** 8 607 connexions normales pour l’entraînement, 2 152 connexions normales pour fixer le seuil, et 51 colonnes après préparation.
- **Variables que HoneyBadger enregistre aujourd’hui :** avec ces 11 variables seulement, le rappel à 1 % de fausses alertes tombe de 0,843 à **0,459**.
- **Fichier de test :** 8 301 des 22 544 connexions sont signalées comme anomalies.

Une petite différence à la 3^e^ décimale est normale si votre version de scikit-learn est différente. Le script de vérification accepte un écart de 0,002 sur les taux ; les nombres entiers, eux, doivent être identiques.

**Pourquoi deux colonnes de rappel ?** Le « rappel à 1 % » se lit sur la courbe ROC. Les « attaques détectées au seuil » appliquent le seuil fixé à l’avance sur les connexions normales mises de côté. Les deux colonnes sont donc proches, mais pas identiques.

# 6. Relire, comprendre, confirmer (ce qu’il vous reste à faire)

## 6.1 Relisez le notebook section par section

| Section du notebook | Ce qu’il faut savoir expliquer |
|---|---|
| 1. Business understanding | La question posée et pourquoi elle compte pour un honeypot : on a rarement des attaques étiquetées. |
| 2. Data understanding | Environ 47 % d’attaques dans les données étiquetées. C’est trop pour des « anomalies rares », d’où l’entraînement sur le **normal seulement**. |
| 3. Data preparation | Mise à l’échelle et encodage *one-hot* (51 colonnes), appris **uniquement sur l’entraînement** pour éviter la fuite de données. |
| 4.1 Modeling | Les trois détecteurs, la référence aléatoire, et le tableau de la section 5. |
| 4.2 Results in pictures | Lire une courbe ROC et une matrice de confusion. |
| 4.3 False-alarm budget | Plus le budget de fausses alertes est grand, plus on attrape d’attaques : c’est le réglage principal. |
| 4.4 Which attacks are missed? | **LOF rate les 1 340 attaques SYN flood (état S0)** : elles se ressemblent toutes et forment un groupe dense, donc LOF les juge « normales ». |
| 4.5 Sensitivity | Les résultats restent stables quand on change les réglages : ils ne tiennent pas à un réglage chanceux. |
| 4.6 HoneyBadger question | Avec ce que le honeypot enregistre aujourd’hui, le rappel tombe à 0,459 : il faudrait enregistrer les octets échangés et la façon dont chaque connexion se termine. |
| 6. Conclusion | La réponse à la question en 4 paragraphes. |

## 6.2 Les mots à maîtriser

- **Détection d’anomalies / apprentissage non supervisé :** apprendre le « normal » sans étiquette d’attaque.
- **Isolation Forest :** une attaque est facile à isoler avec peu de coupures aléatoires.
- **One-Class SVM :** trace une frontière autour du trafic normal ; ce qui est dehors est suspect.
- **LOF :** compare la densité d’un point à celle de ses 20 voisins.
- **Rappel :** la part des attaques attrapées. **Taux de fausses alertes :** la part du trafic normal signalé à tort.
- **ROC-AUC :** la probabilité qu’une attaque ait un score plus élevé qu’une connexion normale ; 0,5 correspond au hasard et 1 à la perfection.
- **Fuite de données :** utiliser, sans le vouloir, des informations du jeu de validation pendant l’entraînement.

## 6.3 Questions probables du professeur

1. **« Pourquoi ne pas utiliser les étiquettes ? »** Dans un vrai honeypot, on n’a presque jamais d’attaques étiquetées. Ici, les étiquettes servent seulement à **mesurer** le résultat, jamais à entraîner.
2. **« Comment avez-vous choisi le seuil ? »** Sur 2 152 connexions normales mises de côté : le seuil laisse passer 99 % d’entre elles, ce qui donne 1 % de fausses alertes. Aucune attaque n’a servi à le choisir.
3. **« Pourquoi One-Class SVM et pas Isolation Forest, qui a une meilleure ROC-AUC ? »** Au budget de 1 % de fausses alertes, qui est le critère choisi, One-Class SVM a le meilleur rappel (0,843 contre 0,832). Les deux sont presque à égalité ; le notebook le dit.
4. **« Pourquoi LOF échoue-t-il ? »** Les attaques SYN flood sont très nombreuses et identiques entre elles. Elles forment un groupe dense, et LOF ne repère que ce qui est isolé.
5. **« Ces résultats valent-ils pour le vrai trafic ? »** Pas directement : ce jeu de données est connu pour être plus facile que le trafic réel, et il ne contient aucune connexion SSH normale. La section 4.6 montre ce qui manque à HoneyBadger.

D’autres questions, avec leurs réponses, se trouvent dans `docs/PROFESSOR_QA.md`.

## 6.4 Comment confirmer

Une fois le notebook exécuté et relu, envoyez **à Aymen** une des deux réponses suivantes :

- **« Confirmé »** : il ajoutera alors le notebook et `results/pair2_results.json` au dépôt GitHub du projet, dans une pull request ;
- **ou la liste de ce que vous voulez changer** : une phrase, un chiffre, une explication. Il vous renverra une version corrigée.

Si vous préférez l’ajouter vous-mêmes sur GitHub (compte GitHub nécessaire, et accès au dépôt donné par Aziz), voici les commandes :

```powershell
git clone https://github.com/scriptsl0th/HoneyBadger.git
cd HoneyBadger
git checkout -b pair2-anomaly-detection
# copiez pair2_anomaly_detection.ipynb dans notebooks\ et le dossier results\ (PAS les fichiers .csv)
git add notebooks/pair2_anomaly_detection.ipynb results/pair2_results.json
git commit -m "Add Pair 2 anomaly detection notebook"
git push -u origin pair2-anomaly-detection
```

Ouvrez ensuite le lien affiché par `git push` pour créer la pull request.

## 6.5 Préparez votre partie de l’oral (environ 1 minute)

Le texte se trouve dans `docs/PRESENTATION_SCRIPT.md`, à la diapositive « Résultats, objectif 2 ». Voici l’idée à dire :

> « Sans étiquettes, en n’apprenant que le trafic normal, on attrape encore environ 84 % des attaques pour 1 % de fausses alertes : c’est le prix de l’absence d’étiquettes. LOF échoue sur les SYN flood, car ces connexions se ressemblent toutes et forment un groupe dense. Et avec seulement ce que HoneyBadger enregistre aujourd’hui, on tombe à 46 % : il faut enregistrer plus d’informations par connexion. »

# 7. En cas de problème

| Problème | Solution |
|---|---|
| `FileNotFoundError: Missing ['Train_data.csv', ...]` | Les CSV ne sont pas au bon endroit. Dans Colab, refaites l’étape 4. Sur PC, mettez-les dans le dossier `data/` du dépôt. |
| `ValueError: Train_data.csv differs from the reviewed Kaggle file` | Le fichier CSV a été modifié, par exemple ouvert puis enregistré dans Excel. Reprenez-le depuis le zip, **sans l’ouvrir dans Excel**. |
| `ModuleNotFoundError` (sur PC) | L’environnement n’est pas activé : tapez `.venv\Scripts\Activate.ps1`, puis relancez. |
| `python` n’est pas reconnu | Python n’a pas été ajouté au PATH : réinstallez-le en cochant « Add python.exe to PATH ». |
| Colab : « Session expirée » ou fichiers disparus | Normal après une pause. Réimportez les deux CSV, puis *Exécution › Tout exécuter*. |
| `Kernel is running over TCP without encryption` | Message normal du script de vérification sur votre propre PC : ignorez-le. |
| Un chiffre diffère légèrement (3^e^ décimale) | Différence de version des bibliothèques : c’est acceptable. Si un **nombre entier** diffère (fausses alertes, attaques manquées), prévenez Aymen. |

# 8. Rappels importants

- Les CSV ne vont **jamais** sur GitHub.
- Le notebook a été préparé pour vous : **relisez-le vraiment** et soyez capables d’expliquer chaque section. Si le professeur demande qui a fait quoi, répondez honnêtement.
- La Paire 3 (regroupement des attaques par familles) n’est pas encore commencée et ne fait pas partie de ce zip.
