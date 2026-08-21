# EDUVIA

Application de gestion scolaire pour **une école secondaire** en RDC.

## Vision du projet

- EDUVIA est conçu pour **une seule école** (pas une plateforme multi-écoles).
- Application simple à utiliser au quotidien, mais suffisamment professionnelle
  pour gérer les activités administratives et scolaires principales.
- On évite volontairement toute complexité inutile (pas de gestion multi-tenant,
  pas de fonctionnalités non demandées).

## Avancement

1. ✅ Gestion des élèves (ajouter, lister, rechercher, modifier, supprimer)
2. ✅ Utilisateurs et rôles (connexion, permissions contrôlées côté serveur)
3. ✅ Activation/désactivation des comptes + historique des actions sensibles
4. ✅ Page de profil personnel
5. ✅ Rôle Élève : compte relié à une fiche élève, consultation de son profil scolaire
6. ✅ Rôle Parent/Tuteur : compte relié à un ou plusieurs enfants
7. ✅ Organisation scolaire : années scolaires, options, classes, matières
8. ✅ Dossier élève : fiche consolidée, statuts, historique scolaire
9. ✅ Notes et résultats : attributions enseignant/classe/matière, saisie,
   moyennes, résultats de classe, bulletins PDF téléchargeables
10. ✅ Présences : appel par classe/matière (Présent/Absent/Retard),
    historique consultable par l'administration
11. ✅ Horaires : emploi du temps par classe/matière/enseignant/jour/heure,
    avec détection des conflits, et consultation filtrée par rôle
12. ✅ Frais scolaires et paiements : configuration par classe, enregistrement
    des paiements, calcul automatique du solde, reçus PDF
13. ✅ Bulletins PDF personnalisables : logo, nom, coordonnées, signature,
    cachet de l'école
14. ✅ Reçus PDF personnalisables : mêmes paramètres école + motif du
    paiement, numéro de reçu, solde après paiement
15. ✅ Règlement d'ordre intérieur : bouton accessible à tous, import/
    remplacement réservé au Préfet
16. ✅ Messages du Préfet : communications à sens unique vers les
    enseignants (pas une messagerie)
17. ✅ Sécurité et accès : audit complet, 3 failles trouvées et corrigées
18. ✅ Rôle Secrétariat : accès limité à la finance (paiements des élèves)
19. ✅ Support multi-devises : franc congolais (CDF) et dollar américain
    (USD), gérés et calculés séparément
20. ✅ Changement de mot de passe personnel + configuration serveur pour
    la production (clé secrète, mode debug, cookies de session)

## ⚠️ Avant de déployer en ligne — checklist obligatoire

Le code fonctionne (toutes les fonctionnalités des 17 prompts + les
ajouts ont été testées automatiquement). Mais "fonctionner en local" et
"être prêt pour internet" sont deux choses différentes. Voici ce qui a
été corrigé, et ce qui reste **à ta charge selon ton hébergeur** :

### ✅ Déjà fait dans le code
- Clé secrète configurable via la variable d'environnement
  `EDUVIA_SECRET_KEY` (ne jamais utiliser celle par défaut en production)
- Mode debug désactivé par défaut (`EDUVIA_DEBUG=1` pour l'activer en dev
  uniquement — jamais en ligne)
- Cookies de session sécurisés (`EDUVIA_HTTPS=1` dès que le site est en HTTPS)
- Changement de mot de passe personnel (le Préfet est averti tant qu'il
  garde `admin123`)
- `gunicorn` ajouté aux dépendances (serveur de production — ne jamais
  utiliser `python app.py` en ligne, ce serveur est fait pour le
  développement uniquement)

### 🔲 À faire toi-même au moment du déploiement
1. **HTTPS obligatoire** : configure un certificat SSL (souvent automatique
   chez l'hébergeur, ex: Let's Encrypt) et définis `EDUVIA_HTTPS=1`.
2. **Définir `EDUVIA_SECRET_KEY`** avec une valeur longue et aléatoire
   (ex: générée avec `python3 -c "import secrets; print(secrets.token_hex(32))"`).
3. **Lancer avec gunicorn**, pas `python app.py` :
   `gunicorn -w 2 -b 0.0.0.0:8000 app:app`
4. **Changer le mot de passe admin** dès la première connexion en ligne.
5. **Sauvegardes régulières** du fichier `eduvia.db` (c'est toute la base
   de données de l'école — le perdre serait grave). Une copie
   quotidienne automatique est fortement recommandée.
6. **Espace disque** pour les fichiers uploadés (logo, cachet, règlement)
   dans `static/` — vérifie que ton hébergeur les conserve entre les
   déploiements (certains hébergeurs "sans état" effacent ce dossier à
   chaque redéploiement : il faudrait alors un stockage externe).

### 🔲 Limites connues, non corrigées (à évaluer selon ton usage réel)
- **Pas de protection CSRF** (Flask-WTF n'a pas pu être installé dans mon
  environnement de développement, hors-ligne). Recommandé avant un usage
  à grande échelle.
- **Pas de limitation du nombre de tentatives de connexion** (risque de
  force brute sur les mots de passe). Une bibliothèque comme Flask-Limiter
  réglerait ça.
- **SQLite** convient bien à une seule école avec un nombre d'utilisateurs
  simultanés modéré (quelques dizaines), mais n'est pas fait pour une
  charge très élevée. Si l'école grandit beaucoup, une migration vers
  PostgreSQL serait à envisager (le code est structuré pour que ce soit
  possible plus tard, mais ce n'est pas fait aujourd'hui).
- Les fichiers uploadés (logo, cachet, règlement) sont validés par
  extension mais pas par contenu réel du fichier.

Rien de tout ça n'est insurmontable, mais je préfère te le dire
clairement plutôt que de te laisser croire que "tout marche à 100%"
veut dire "prêt pour la production sans rien vérifier".

## Rôle Secrétariat (ajout après les 17 prompts initiaux)

Un 5ème rôle, dédié à la caisse de l'école. Accès strictement limité :

| Peut faire | Ne peut PAS faire |
|---|---|
| Consulter "Finance" (liste des élèves + soldes) | Voir la liste générale des élèves (notes, dossier académique) |
| Enregistrer un paiement pour un élève | Configurer les frais scolaires (montants attendus — Préfet uniquement) |
| Télécharger un reçu PDF | Accéder aux notes, présences, organisation scolaire, comptes utilisateurs |

C'est délibérément plus restreint que le Préfet sur les paiements : le
secrétariat **encaisse**, mais ne décide pas des montants officiels.

## Devises : CDF et USD (ajout après les 17 prompts initiaux)

Chaque **frais scolaire** et chaque **paiement** a sa propre devise
(franc congolais ou dollar américain) — une classe peut par exemple avoir
un minerval en USD et des frais divers en CDF.

**Règle stricte : les deux devises ne sont jamais additionnées.** Les
soldes (attendu, payé, restant) sont calculés et affichés **séparément**
par devise, partout dans l'application (dossier élève, profil élève/
parent, page Finance, reçus PDF).

⚠️ **Point important à te signaler** : EDUVIA ne gère aucun **taux de
change**. Un solde de 50 USD et un solde de 15 000 CDF restent deux
montants distincts, jamais convertis ou combinés en un seul total — ce
serait risqué de le faire automatiquement vu que les taux fluctuent.
Si un jour tu veux un total converti indicatif, il faudra ajouter un
taux de change configurable ; je ne l'ai pas fait ici pour éviter
d'afficher un chiffre potentiellement trompeur.

## Migration de base de données

Comme pour les changements précédents de structure, si tu as déjà lancé
l'application avec des données de test, **supprime `eduvia.db`** avant
de relancer : la table des rôles et celle des frais/paiements ont changé
de structure (nouveau rôle, nouvelle colonne devise).

## Audit de sécurité (prompt 17)

Ce prompt n'a pas ajouté de nouvelle fonctionnalité : c'est un **audit**
du système déjà construit, avec correction des failles trouvées.

**Failles trouvées et corrigées :**

1. **Un enseignant pouvait consulter le dossier de n'importe quel élève**,
   pas seulement ceux de ses classes attribuées (`/eleves/<id>/dossier`
   ne vérifiait que le rôle, jamais la classe réelle). Corrigé : la liste
   des élèves et le dossier sont maintenant filtrés par attribution
   réelle enseignant↔classe.
2. **Un compte désactivé en pleine session restait utilisable** jusqu'à
   sa prochaine connexion (la vérification `actif` ne se faisait qu'au
   login). Corrigé : le statut est revérifié à **chaque requête** ; dès
   qu'un compte est désactivé, la session est coupée immédiatement.
3. **Fuite d'hygiène de session** : un message flash non affiché pouvait
   survivre à une déconnexion et apparaître dans la session de
   l'utilisateur suivant sur le même navigateur. Corrigé : la session
   est entièrement vidée à la déconnexion.

**Durcissement supplémentaire :** validation du mot de passe (6
caractères minimum) appliquée côté serveur, pas seulement dans le
formulaire HTML (contournable).

**Ce qui était déjà solide** (vérifié, pas modifié) : mots de passe
hachés, permissions par rôle contrôlées côté serveur sur toutes les
routes sensibles, élève/parent déjà strictement limités à leurs propres
données, journal d'audit des actions sensibles.

**Recommandations pour un déploiement en production** (hors du cadre de
ce projet pédagogique) : protection CSRF (ex: Flask-WTF), limitation du
nombre de tentatives de connexion, cookies de session en HTTPS uniquement,
sauvegardes régulières de `eduvia.db`.

## Messages (bouton dans le menu, Préfet + Enseignant uniquement)

Ce n'est **pas une messagerie** : le Préfet publie des communications
générales (créer/modifier/supprimer), les enseignants les lisent, un
point c'est tout. Aucune fonctionnalité de réponse, commentaire ou
réaction n'existe dans le code — pas juste cachée côté enseignant, elle
n'a simplement jamais été construite.

## Règlement d'ordre intérieur (bouton dans le menu, visible à tous)

Fonctionnalité volontairement simple : **un seul fichier PDF**, remplacé
à chaque nouvel import (pas d'historique de versions).
- **Tout utilisateur connecté** peut consulter la page et télécharger
  le fichier actuel.
- **Seul le Préfet** voit le formulaire d'import et peut remplacer le
  fichier existant (contrôlé côté serveur, pas juste caché).

## Personnalisation des documents (menu "Organisation" > "Paramètres de l'école")

Le Préfet configure une seule fois :
- **Nom, adresse, téléphone, email** de l'école (affichés en en-tête)
- **Logo** (image PNG/JPG, affiché en haut du document)
- **Cachet** (image PNG/JPG, affiché à côté de la signature)
- **Nom et titre du signataire** (ex: "Mme Kabongo — Le Préfet des études")

Ces paramètres habillent automatiquement **tous les bulletins et reçus
générés**, sans rien reconfigurer document par document. Tant que rien
n'est configuré, des valeurs par défaut simples sont utilisées (le
système reste utilisable dès le premier jour).

Chaque paiement peut désormais avoir un **motif** (ex: "Minerval - 2ème
tranche"), affiché sur le reçu et dans l'historique.

## Frais scolaires et paiements (menu "Organisation" > "Frais scolaires")

- Le Préfet configure les **frais attendus par classe** (ex: Minerval,
  frais divers), sous forme de lignes avec un montant chacune.
- Le **montant attendu** d'un élève = somme des frais de sa classe.
- Chaque **paiement enregistré** (menu accessible depuis le dossier élève)
  génère automatiquement un **reçu PDF** téléchargeable.
- Le **solde = attendu − payé** est recalculé automatiquement à chaque
  paiement, jamais saisi manuellement, visible dans le dossier élève.
- Élèves et parents voient leur solde sur "Mon profil" — actuellement
  **toujours visible** pour ces rôles : le bascule "l'école choisit de
  les rendre visibles ou non" mentionné au prompt 6 n'est pas encore
  implémenté comme option de configuration séparée.

## Horaires (menu "Horaires" pour le Préfet, "Emploi du temps" pour les autres)

- Un créneau d'horaire s'appuie toujours sur une **attribution existante**
  (enseignant + classe + matière déjà validée dans "Notes > Attributions") :
  impossible de planifier un enseignant sur une classe qu'il n'enseigne pas.
- **Détection de conflit** : le Préfet ne peut pas créer un créneau qui
  chevauche un autre cours de la même classe, ni un créneau où le même
  enseignant serait déjà occupé ailleurs.
- Chacun ne voit que ce qui le concerne :
  - **Enseignant** → tous ses créneaux, toutes classes confondues
  - **Élève** → l'emploi du temps de sa seule classe
  - **Parent** → l'emploi du temps de chacun de ses enfants, séparément

## Notes et bulletins (menu "Notes")

- **Attributions** (Préfet) : autoriser un enseignant à noter une matière
  dans une classe précise. C'est ce qui détermine, côté serveur, où
  l'enseignant a le droit de saisir des notes — pas juste un bouton caché.
- **Saisir les notes** : l'enseignant choisit une de ses classes/matières
  attribuées et une période (1er/2ème/3ème Trimestre), puis note chaque
  élève sur 20.
- **Résultats de classe** : moyennes par élève, avec téléchargement direct
  du bulletin en PDF.
- Élèves et parents voient leurs notes/moyennes et peuvent télécharger
  leur bulletin PDF depuis "Mon profil".

## Présences (menu "Notes" > Présences)

- **Saisir les présences** : appel de classe par matière et par date,
  3 statuts (Présent/Absent/Retard), réservé aux classes/matières
  attribuées à l'enseignant (mêmes attributions que les notes).
- **Historique des présences** : consultable par le Préfet (toutes
  classes) et par l'enseignant (ses classes), avec filtre par dates.
- Le dossier élève affiche un résumé (nombre d'absences/retards).

## Dossier élève (bouton "Dossier" dans la liste des élèves)

Chaque élève a une fiche consolidée regroupant identité, classe/option/année
scolaire, parent/tuteur, et des emplacements réservés pour les résultats,
présences et paiements (à venir dans de prochains modules).

**Statuts possibles :** Actif, Transféré, Diplômé, Exclu, Archivé, Inactif.
Le Préfet peut changer le statut depuis le dossier. Dès qu'un élève n'est
plus "Actif" :
- son **historique scolaire est conservé** (jamais supprimé) ;
- son **compte de connexion, s'il en a un, est désactivé automatiquement**
  (il peut être réactivé manuellement plus tard si nécessaire).

L'historique scolaire (distinct du journal d'audit global) trace les
événements du parcours de l'élève : inscription, changements de statut, etc.

## Organisation scolaire (menu "Organisation", réservé au Préfet)

1. **Années scolaires** : créer une année (ex: "2026-2027") et l'activer.
   Une seule année est active à la fois.
2. **Options** : les filières de l'école (Scientifique, Commerciale...).
3. **Classes** : créées pour l'année scolaire active, avec un niveau
   (7ème CTEB à 6ème), un nom libre (ex: "3ème Scientifique A") et une
   option facultative. **Il faut activer une année scolaire avant de
   pouvoir créer des classes.**
4. **Matières** : liste simple des matières enseignées.

Le formulaire d'inscription d'un élève propose désormais uniquement les
classes réellement configurées par l'école (menu déroulant), au lieu
d'une liste fixe.

Menu "Enseignants" et "Parents" : raccourcis vers la liste des comptes
utilisateurs filtrée par rôle. Un compte enseignant peut avoir un
matricule et une spécialité.

## Comment lier un compte à un élève ou à des enfants

Lors de la création d'un compte (menu Utilisateurs > Créer un compte) :
- Rôle **Élève** → choisir la fiche élève associée dans la liste déroulante.
- Rôle **Parent/Tuteur** → sélectionner un ou plusieurs enfants (Ctrl/Cmd + clic).

Chaque élève/parent ne voit alors que ses propres informations : accéder à
la fiche d'un autre élève, ou à la liste complète, renvoie une erreur 403.

## Feuille de route (permissions par rôle)

| Permission | Préfet | Enseignant | Élève | Parent |
|---|---|---|---|---|
| Gérer les élèves / inscriptions | ✅ | ❌ (lecture seule*) | — | — |
| Gérer les comptes utilisateurs | ✅ | ❌ | ❌ | ❌ |
| Consulter son profil | ✅ | ✅ | ✅ | ✅ (ses enfants) |
| Gérer les années scolaires | ✅ | — | — | — |
| Gérer les classes / options | ✅ | — | — | — |
| Matières | ✅ | consulter les siennes | consulter | consulter |
| Emploi du temps | ✅ | consulter le sien | consulter | consulter |
| Notes / moyennes | ✅ (admin.) | enregistrer les siennes | consulter | consulter |
| Présences / absences / retards | ✅ | enregistrer pour ses classes | consulter | consulter |
| Bulletins | ✅ | — | consulter | consulter |
| Frais scolaires / paiements / soldes | ✅ | ❌ | — | consulter (si activé) |
| Documents de l'école | ✅ | — | — | — |
| Règlement d'ordre intérieur | ✅ | consulter | consulter | consulter |
| Messages généraux | ✅ (publier) | consulter | — | — |

\* **Limitation actuelle à corriger plus tard :** l'enseignant voit aujourd'hui
la liste de **tous** les élèves de l'école, alors qu'il ne devrait voir que
ceux de ses classes attribuées. Cette restriction nécessite le module
"Gestion des classes" + l'attribution enseignant↔classe, pas encore construits.

Tout ce qui est marqué "consulter" ci-dessus (matières, emploi du temps,
notes, bulletins, ROI, messages) n'est pas encore implémenté : seules les
permissions et la structure des comptes sont en place, prêtes à recevoir
ces modules.

## Historique des actions

Le Préfet peut consulter, dans le menu "Historique", la liste des actions
sensibles effectuées dans l'application (connexions, ajout/modification/
suppression d'élèves, création de comptes, activation/désactivation de
comptes...). Chaque entrée indique qui a fait quoi, et quand.

## Connexion

Au premier lancement, un compte administrateur est créé automatiquement :

- Email : `admin@eduvia.local`
- Mot de passe : `admin123`

**À changer dès que possible.** Ce compte (rôle Préfet/Administrateur) permet
ensuite de créer les autres comptes depuis le menu "Utilisateurs".

## Rôles et permissions

| Rôle | Élèves (voir) | Élèves (ajouter/modifier/supprimer) | Utilisateurs |
|---|---|---|---|
| Préfet / Administrateur | ✅ | ✅ | ✅ |
| Enseignant | ✅ | ❌ | ❌ |
| Élève | (à venir) | ❌ | ❌ |
| Parent / Tuteur | (à venir) | ❌ | ❌ |

Les permissions sont vérifiées **dans le code Python** (`decorateurs.py`),
pas seulement cachées dans les pages : un accès non autorisé reçoit une
vraie erreur 403, même en tapant l'adresse directement.

## Installation (à faire une seule fois)

1. Installer Python 3 si ce n'est pas déjà fait : https://www.python.org/downloads/
2. Ouvrir un terminal dans le dossier `eduvia/`
3. Installer Flask :

```
pip install -r requirements.txt
```

## Lancer l'application

```
python app.py
```

Puis ouvrir un navigateur à l'adresse : **http://127.0.0.1:5000**

La base de données (`eduvia.db`) sera créée automatiquement au premier lancement,
dans le même dossier. Aucune installation de serveur de base de données n'est nécessaire.

## Structure du projet

- `app.py` → les routes (pages) de l'application
- `database.py` → connexion et création de la base de données
- `models.py` → toutes les opérations sur les données des élèves
- `templates/` → les pages HTML
- `static/` → fichiers CSS

## Prochaines étapes prévues

1. ✅ Gestion des élèves
2. ⬜ Gestion des notes et bulletins
3. ⬜ Gestion des paiements/frais scolaires
4. ⬜ Comptes utilisateurs (admin, enseignant, comptable)
5. ⬜ Rapports et statistiques
