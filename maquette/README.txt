Maquette DevArchive — Frontend uniquement
=========================================

Ce dossier contient des copies des pages du projet en HTML/CSS/JS statiques,
sans Django ni backend. Utile pour prévisualiser le design ou partager la maquette.

Fichiers :
  - index.html       : page d'accueil publique (landing)
  - connexion.html   : page de connexion
  - inscription.html : page d'inscription (étudiant)
  - etudiant.html    : tableau de bord étudiant (sujets visités, recherche d'examens, historique)
  - personnel.html   : espace personnel enseignant (tableau de bord des archives)
  - administrateur.html : tableau de bord administrateur (utilisateurs, modération, facultés)

Utilisation :
  Ouvrir directement les fichiers dans un navigateur (double-clic ou glisser-déposer).
  Les liens entre pages fonctionnent (connexion <-> inscription, déconnexion -> connexion).
  Les formulaires ne sont pas envoyés (message "Maquette : pas d'envoi" ou comportement local).

Note : Sur la page personnel, les archives sont stockées dans le localStorage du navigateur
       (ajout / modification / suppression fonctionnent en local).
