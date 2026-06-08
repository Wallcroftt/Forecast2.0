# 🌤️ Infrastructure de Données Météo - Projet Forecast 2.0

## 📝 Contexte du Projet

Le projet Forecast 2.0 a été initié par l'entreprise GreenCoop dans le but d'améliorer significativement ses modèles de prévisions. La mission principale consiste à bâtir une infrastructure robuste pour collecter, nettoyer, unifier et stocker de grands volumes de données météorologiques dans le Cloud.

Ces données proviennent de plusieurs sources hétérogènes, notamment l'API InfoClimat et les relevés des stations Weather Underground (comme celles de La Madeleine et Ichtegem).

## 🛠️ Technologies Utilisées

* 
**Extraction de données :** Airbyte 


* 
**Stockage & Base de données :** Amazon S3 , MongoDB (NoSQL) 


* 
**Traitement & Conteneurisation :** Python (Script ETL) , Docker , AWS ECS 


* 
**Surveillance (Monitoring) :** Amazon CloudWatch 



## ⚙️ Architecture du Pipeline

Le flux de données est entièrement automatisé et sécurisé, fonctionnant avec une gestion des accès sans clé explicite (IAM). Il se décompose en quatre grandes étapes :

1. 
**Ingestion automatisée (Collecte) :** L'outil Airbyte se charge d'extraire régulièrement les données brutes depuis les différentes sources météorologiques et de les déposer dans un premier compartiment Amazon S3.


2. 
**Nettoyage et Unification (Transformation) :** Une tâche Docker hébergée sur AWS ECS déclenche un script Python dédié. Ce script récupère les fichiers récents, aplanit les données horaires issues d'InfoClimat et normalise les relevés des différentes stations Weather Underground. Un audit de qualité strict vérifie ensuite le typage des champs et isole automatiquement les valeurs aberrantes ou non recevables.


3. 
**Stockage final (Chargement) :** Une fois validées, les données sont sauvegardées au format JSON unifié sur Amazon S3 et chargées simultanément dans une base de données NoSQL MongoDB pour être facilement requêtables par les utilisateurs ou les modèles de prévision.


4. 
**Surveillance de l'infrastructure :** Une alarme CloudWatch mesure en continu la charge processeur (CPU) allouée au conteneur Docker. Si celle-ci dépasse le seuil critique de 80 %, une notification est immédiatement envoyée par courriel afin d'alerter l'équipe technique.



## 🚀 Résultats et Qualité des Données

* 
**Fiabilité :** Le processus de nettoyage et d'audit intégré garantit un excellent score de viabilité opérationnelle (mesure de la complétude et de l'intégrité des données) supérieur à 94 %.


* 
**Performances :** Les tests d'accessibilité réalisés sur la base finale MongoDB démontrent des temps de réponse optimaux, avec des requêtes complexes exécutées en moyenne en 0,009 seconde.