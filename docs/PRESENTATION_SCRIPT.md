# Script de présentation (10 à 12 minutes)

Pour chaque partie : **diapositive** (ce qui apparaît), **à dire** (texte oral), **à comprendre** (concepts), **transition**, **questions possibles**. Les durées sont indicatives ; le total fait environ 11 minutes.

Les diapositives correspondantes (15 diapositives, notes de l’orateur incluses) : https://claude.ai/artifact/8oomN1FHyVESFZbBMTm5jL (privé jusqu’à partage ; exportable en PowerPoint ou PDF).

---

## 1. Introduction et contexte (1 min)

**Diapositive.** Titre « HoneyBadger : un piège à attaquants qui apprend à les reconnaître ». Noms du groupe. Une phrase : « Les serveurs exposés sur Internet sont attaqués en permanence. »

**À dire.**
« Bonjour. Tout serveur connecté à Internet reçoit, en quelques minutes, des tentatives de connexion automatiques : des robots essaient des mots de passe, cherchent des fichiers de configuration, tentent d'installer des logiciels malveillants. Notre projet, HoneyBadger, est un piège pour ces attaquants : il les laisse entrer dans un faux système, enregistre tout ce qu'ils font, et nous avons étudié si l'apprentissage automatique peut reconnaître ces attaques. »

**À comprendre.** Honeypot ; attaques automatisées (robots, botnets).

**Transition.** « Concrètement, quel problème voulons-nous résoudre ? »

**Questions possibles.** « Pourquoi ce sujet ? » → voir `PROFESSOR_QA.md` n° 3.

---

## 2. Problématique (1 min)

**Diapositive.** Trois points : on ne sait pas ce que font les attaquants ; observer un vrai serveur est risqué ; analyser des milliers d'événements à la main est impossible.

**À dire.**
« Pour se défendre, une équipe de sécurité doit savoir ce que les attaquants font réellement : quels mots de passe, quelles commandes, quels fichiers. Observer un vrai serveur attaqué est dangereux. Et même avec les données, les analyser à la main ne passe pas à l'échelle. Notre question est donc double : comment observer les attaques sans risque, et peut-on les reconnaître automatiquement ? »

**À comprendre.** Pourquoi un faux système : aucun utilisateur légitime, donc tout trafic est suspect.

**Transition.** « Voici nos objectifs. »

**Questions possibles.** « Qui utiliserait ce système ? » → équipe SOC, enseignement, recherche.

---

## 3. Objectifs (1 min)

**Diapositive.**
1. Capturer les attaques SSH et web sans risque.
2. Classer chaque action selon MITRE ATT&CK et l'afficher en direct.
3. Évaluer l'apprentissage automatique : objectif 1 avec étiquettes (paire 1), objectif 2 sans étiquettes (paire 2), objectif 3 regroupement (paire 3).

**À dire.**
« Nous avions trois objectifs. Capturer les attaques sans jamais mettre en danger la machine. Classer chaque action dans le vocabulaire standard MITRE ATT&CK, et tout montrer en direct. Enfin, évaluer si l'apprentissage automatique reconnaît les attaques : avec étiquettes, sans étiquettes, et en les regroupant par familles. »

**À comprendre.** MITRE ATT&CK : un catalogue commun de techniques d'attaque, chacune avec un identifiant (T1110, T1105...).

**Transition.** « Comment y répondons-nous ? »

**Questions possibles.** « Pourquoi trois méthodes d'apprentissage ? » → Chacune répond à une situation différente : avec étiquettes, sans étiquettes, et pour nommer le type d'attaque une fois l'alerte levée.

---

## 4. Solution proposée (1 min)

**Diapositive.** Capture d'écran du tableau de bord (`docs/img/dashboard_live.png`) et trois mots : Capturer, Comprendre, Apprendre.

**À dire.**
« HoneyBadger expose un faux serveur SSH et un faux site web qui acceptent tout. Chaque action devient un événement, enrichi automatiquement par sa localisation et sa technique ATT&CK, stocké, et affiché en direct sur ce tableau de bord. À côté, nos notebooks testent des modèles d'apprentissage sur un jeu de données public de 25 000 connexions étiquetées. »

**À comprendre.** Événement ; enrichissement ; tableau de bord en temps réel.

**Transition.** « Voyons comment c'est construit. »

---

## 5. Architecture (1 min 30)

**Diapositive.** Le schéma de flux : Attaquant → capteurs SSH :8022 / HTTP :8081 → bus → pipeline (GeoIP, MITRE) → PostgreSQL → API + WebSocket → tableau de bord ; Prometheus et Grafana pour la supervision.

**À dire.**
« Tout le cœur tient dans un seul programme Python asynchrone. Les deux capteurs déposent les événements sur un bus interne et continuent immédiatement : le piège ne ralentit jamais. Le pipeline enrichit chaque événement, le stocke dans PostgreSQL et le pousse au tableau de bord par WebSocket. Prometheus et Grafana surveillent le système et déclenchent des alertes. Six conteneurs, une seule commande : docker compose. »

**À comprendre.** Programmation asynchrone ; bus d'événements (découplage) ; WebSocket ; conteneurs.

**Transition.** « Quelles technologies et quelle méthode ? »

**Questions possibles.** « Pourquoi pas Kafka ? » → un seul processus, une file en mémoire suffit (`PROFESSOR_QA.md` n° 6).

---

## 6. Technologies et méthodologie (1 min)

**Diapositive.** Deux colonnes. Système : Python asyncio, asyncssh, aiohttp, PostgreSQL, React, Docker, Prometheus/Grafana. Analyse : pandas, scikit-learn, Google Colab ; séparation 80/20 sans fuite ; validation croisée ; métriques adaptées (y compris silhouette et stabilité pour le regroupement).

**À dire.**
« Côté système : Python asynchrone, asyncssh et aiohttp pour les faux services, PostgreSQL, React pour l'interface. Côté analyse : pandas et scikit-learn dans des notebooks exécutables sur Colab. Notre méthode évite la fuite de données : 20 % des connexions sont mises de côté et ne servent qu'une fois, les lignes identiques restent du même côté, et tout le prétraitement est appris sur l'entraînement seulement. »

**À comprendre.** Séparation entraînement/validation ; fuite de données ; validation croisée.

**Transition.** « Quelques points d'implémentation importants. »

---

## 7. Implémentation (1 min 30)

**Diapositive.** Trois encadrés : 1. « Aucun mot de passe en clair » (`sha256:…`) ; 2. « Rien n'est exécuté » (faux shell) ; 3. extrait des règles de `classify()`.

**À dire.**
« Trois choix d'implémentation. Un : les mots de passe ne sont jamais stockés en clair, seulement leur empreinte SHA-256 ; on l'a vérifié sur un export complet de la base. Deux : le shell est simulé ; quand l'attaquant tape wget, on note l'adresse mais rien n'est téléchargé. Trois : la classification ATT&CK utilise des règles dans un ordre fixe : téléchargement, exploitation, commande, identifiants, scan. En testant le vrai système, nous avons aussi trouvé et corrigé sept bugs, par exemple des injections SQL perdues parce que la partie après le point d'interrogation de l'URL n'était pas enregistrée. »

**À comprendre.** Hachage ; règles ordonnées ; expression régulière ; test de bout en bout.

**Transition.** « Passons à la démonstration. »

**Questions possibles.** « SHA-256 sans sel ? » → `PROFESSOR_QA.md` n° 11.

---

## 8. Démonstration en direct (3 min)

Suivre `docs/DEMO_GUIDE.md`, partie A (étapes A2 à A5).

**Diapositive.** « Démonstration », puis basculer sur le navigateur et le terminal.

**À dire (pendant la démo).**
- Connexion SSH : « Je me connecte avec n'importe quel mot de passe… le serveur accepte. Je tape whoami, puis un wget : la réponse est crédible, mais rien n'est téléchargé. »
- Requêtes web : « Un robot cherche le fichier .env, puis tente une injection SQL. »
- Tableau de bord : « Chaque action apparaît en direct avec sa technique : T1059 pour la commande, T1105 pour le téléchargement, T1595 pour le scan, T1190 pour l'injection. »
- Simulateur : « Le simulateur envoie une vague d'attaques réalistes mais inoffensives : on voit le pic sur le graphique. »

**À comprendre.** Ce que chaque technique représente ; pourquoi la carte est vide en local (127.0.0.1 n'a pas de localisation).

**Transition.** « Et l'apprentissage automatique, que donne-t-il ? »

**En cas de problème.** Basculer sur le mode démo du tableau de bord (voir `DEMO_GUIDE.md`, tableau des problèmes) et passer directement aux résultats.

---

## 9. Résultats et évaluation (2 min)

**Diapositive.** Trois tableaux.
- Objectif 1 : forêt aléatoire, précision 1,000, rappel 0,996, F1 0,998 ; 2 339 attaques sur 2 349, 0 fausse alerte. Référence naïve : 0 attaque.
- Objectif 2 : sans étiquettes, environ 84 % des attaques pour 1 % de fausses alertes (One-Class SVM 0,843, Isolation Forest 0,832) ; LOF rate toutes les attaques SYN flood.
- Objectif 3 : 5 familles d'attaques stables (SYN flood 60 %, scan de ports 22 %, balayage ICMP 8 %, flood ICMP/UDP 8 %, attaque après connexion 2 %), chacune avec une technique MITRE proposée ; stabilité ARI ≥ 0,97 sur la validation.
- Une ligne : avec seulement les variables de HoneyBadger : F1 0,984 (objectif 1), rappel 0,46 (objectif 2), familles à moitié conservées (ARI 0,57, objectif 3).

**À dire.**
« Sur 5 039 connexions jamais vues, la forêt aléatoire attrape 2 339 attaques sur 2 349, sans aucune fausse alerte ; la référence naïve n'en attrape aucune. Ces chiffres sont reproduits à l'identique sur deux versions des bibliothèques. Sans étiquettes, en n'apprenant que le trafic normal, on attrape encore environ 84 % des attaques pour 1 % de fausses alertes : c'est le prix de l'absence d'étiquettes. Enfin, en regroupant les attaques sans étiquettes, on retrouve cinq familles qu'un analyste reconnaît : SYN floods, scans de ports, balayages et floods ICMP, et attaques après connexion sur le web. Trois algorithmes différents trouvent les mêmes groupes, et ils se retrouvent à l'identique sur des données jamais vues. Les noms MITRE restent des hypothèses, car le jeu ne dit pas le type d'attaque. Attention : ce jeu de données est connu pour être plus facile que le trafic réel ; ces scores montrent que la méthode fonctionne, pas que le problème est résolu. Le résultat le plus utile pour notre honeypot est celui-ci : avec seulement les informations qu'il enregistre aujourd'hui, la détection sans étiquettes tombe à 46 %. Il doit donc enregistrer les octets échangés et la façon dont chaque connexion se termine. »

**À comprendre.** Précision, rappel, F1, ROC-AUC ; faux positif et faux négatif ; pourquoi l'exactitude seule ne suffit pas.

**Transition.** « Pour finir, les limites et la suite. »

**Questions possibles.** « 99,8 %, c'est trop beau ? » → `PROFESSOR_QA.md` n° 22. « Comment avez-vous choisi le nombre de groupes ? » → `PROFESSOR_QA.md` n° 34.

---

## 10. Limites, améliorations et conclusion (1 min)

**Diapositive.** Limites : jeu de données public et facile ; pas de SSH normal ; variables manquantes dans le honeypot ; définitions T1110 à trancher. Suite : enregistrer octets et fin de connexion ; collecter du vrai trafic ; appliquer les familles aux sessions du honeypot.

**À dire.**
« Nos limites : les modèles sont évalués sur un jeu public, pas sur notre honeypot ; ce jeu n'a aucune connexion SSH normale ; et il reste une question de définition entre force brute et credential stuffing, que nous avons documentée plutôt que masquée. La suite : enregistrer les octets et la fin des connexions, exposer le honeypot sur un vrai serveur, étiqueter un échantillon, et appliquer nos familles d'attaques aux sessions du honeypot. En conclusion, HoneyBadger capture et explique les attaques sans risque, et notre analyse montre quelles informations il lui faut pour les reconnaître automatiquement. Merci, nous sommes prêts pour vos questions. »

---

## Pitch de 2 minutes

« Tout serveur connecté à Internet est attaqué en permanence par des robots qui essaient des mots de passe et installent des logiciels malveillants. Pour se défendre, il faut savoir ce qu'ils font, sans risquer un vrai système.

HoneyBadger est un honeypot : un faux serveur SSH et un faux site web qui acceptent tout. Le shell est simulé : rien n'est exécuté, rien n'est téléchargé, et aucun mot de passe n'est stocké en clair. Chaque action est classée automatiquement selon MITRE ATT&CK, le vocabulaire des équipes de sécurité, et affichée en direct sur un tableau de bord. Tout démarre avec une seule commande Docker.

Nous avons ensuite étudié si l'apprentissage automatique peut reconnaître les attaques, sur 25 000 connexions publiques étiquetées. Avec étiquettes, une forêt aléatoire attrape 99,6 % des attaques sans fausse alerte. Sans étiquettes, ce qui correspond à la situation réelle d'un honeypot, on en attrape encore environ 84 % pour 1 % de fausses alertes. Et en regroupant les attaques, on retrouve cinq familles stables (floods, scans, balayages, attaques après connexion) qu'un analyste sait nommer.

Surtout, l'analyse montre ce qui manque au honeypot pour y arriver lui-même : enregistrer les octets échangés et la façon dont chaque connexion se termine. Le système a été testé de bout en bout : 97 tests automatiques, 10 scénarios d'attaque réussis sur 13, et des résultats reproduits à l'identique. »
