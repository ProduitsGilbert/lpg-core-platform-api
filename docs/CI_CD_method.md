

PRD – Modernisation Git + CI/CD + Déploiement Automatisé pour Projet API

1. Objectif

Moderniser un projet actuellement déployé manuellement en production en ajoutant :
	1.	Une organisation Git basée sur branches :
	•	main = toujours déployable
	•	dev = branche active pour développement
	•	branches feature/* = travail par sujet
	2.	Un pipeline CI/CD GitHub Actions :
	•	CI : tests + lint (facultatif au début)
	•	CD : build Docker + déploiement automatique uniquement quand main reçoit un push
	3.	Un système d’environnement clair :
	•	.env.dev
	•	.env.prod
	•	.env.example
	4.	Ne jamais casser la prod, tout en gardant une vitesse de développement rapide.

⸻

2. Portée

L’agent doit modifier ton repo pour intégrer :
	•	Les nouveaux fichiers Git :
	•	.github/workflows/ci.yml
	•	.github/workflows/cd.yml (si tu veux séparer)
	•	.env.example
	•	Le code pour charger les variables d’environnement correctement.
	•	La documentation minimale (README section “Workflow & Déploiement”).

L’agent ne doit pas :
	•	Modifier la logique métier de l’API.
	•	Introduire des dépendances inutiles.
	•	Changer le nom des containers ou du repo.
	•	Toucher au code front-end sauf si demandé explicitement.

⸻

3. Règles Git obligatoires

3.1 Branches à créer
	•	main
	•	dev

3.2 Règles de travail
	•	Tout développement se fait sur :
feature/nom-de-la-feature
	•	Une fois la feature terminée → PR vers dev
	•	Fusion vers main seulement lorsque l’intention est de déployer.

L’agent doit :
	•	Créer les branches si absentes.
	•	Mettre à jour le README pour décrire ce workflow.

⸻

4. CI – Tests & Validation

4.1 Ci.yml (déclenchement)

Déclencher CI sur :

on:
  pull_request:
    branches: [main, dev]
  push:
    branches: [dev]

4.2 Tâches CI
	•	Installer dépendances (pip install -r requirements.txt)
	•	lancer pytest (si ton projet n’a pas encore de tests, juste skip)
	•	Optionnel : exécuter ruff ou flake8

⸻

5. CD – Déploiement automatisé

5.1 Déclenchement

Déploiement uniquement quand il y a un push sur main.

on:
  push:
    branches: [main]

5.2 Actions
	1.	Build image Docker → taggée avec latest + le commit_sha
	2.	Push image vers ton registry Docker (Docker Hub ou ton serveur)
	3.	SSH vers ton serveur
	4.	Pull la nouvelle image
	5.	Redémarrer le conteneur via docker compose up -d

L’agent doit :
	•	Générer un fichier deploy.sh ou réutiliser ton compose existant.
	•	Créer une clé SSH GitHub Actions pour ton serveur (documentation à inclure dans README).
	•	Ajouter variables secrètes dans GitHub (à documenter, l’agent ne les créera pas).

⸻

6. Gestion des variables d’environnement

L’agent doit créer :

.env.example
.env.dev
.env.prod

Chacun contiendra :

APP_ENV=dev/prod
API_PORT=...
DB_CONN=...

Le code Python doit charger .env via dotenv.

⸻

7. Mise à jour du Dockerfile

Le Dockerfile doit être ajusté pour :
	•	être reproductible
	•	utiliser des layers propres
	•	accepter les fichiers .env

L’agent doit valider que ton Dockerfile fonctionne en CI.

⸻

8. Mise à jour du docker-compose

Deux fichiers :
	•	docker-compose.dev.yml
	•	docker-compose.prod.yml

Le front (page web) devra pointer vers api:port dans le réseau interne Docker.

⸻

9. Documentation

L’agent doit ajouter dans le README :
	•	Workflow Git
	•	Comment lancer l’environnement dev
	•	Comment fonctionne le déploiement automatique
	•	Structure des branches
	•	Comment ajouter une feature
	•	Comment rollback une prod

⸻

10. Ce que l’agent doit produire

En résumé, ton coding agent doit :
	1.	Créer les branches manquantes (dev, feature/setup-ci-cd)
	2.	Créer les workflows GitHub Actions :
	•	ci.yml
	•	cd.yml
	3.	Créer les fichiers d’environnement :
	•	.env.dev
	•	.env.prod
	•	.env.example
	4.	Adapter le code pour utiliser .env
	5.	Mettre à jour Dockerfile & docker-compose
	6.	Produire une documentation claire dans README
	7.	Préparer un script de déploiement SSH si nécessaire

L’agent doit effectuer ces modifications dans une PR unique nommée :

feature/ci-cd-setup

⸻

11. Contraintes pour l’agent
	•	Ne jamais toucher au code métier.
	•	Ne jamais changer la structure des API endpoints.
	•	Ne jamais modifier le front.
	•	Si un fichier risque de casser le build, l’agent doit proposer une version sécurisée.
	•	Toujours maintenir backward compatibility.
	•	Respecter la lisibilité et la simplicité (pas de pipeline sophistiqué inutile).

