# Rapport de ColorStudioApp

Réalisé par : 
- **Blaszyk Constant**
- **Douilly Quentin**
- **Deldalle Corentin**

## 1. Migration vers Python 3.13

L'ensemble de la base de code a été migré pour être compatible avec **Python 3.13**. Cette mise à jour permet de bénéficier des dernières optimisations de l'interpréteur, des améliorations de typage et des nouvelles fonctionnalités du langage.

- **Avantages** : Meilleures performances globales, sécurité accrue et accès aux bibliothèques les plus récentes.
- **Actions réalisées** : Tests de compatibilité, mise à jour de la syntaxe si nécessaire et vérification des dépendances.

## 2. Passage à PyQt6

L'interface graphique, initialement basée sur une version antérieure (PyQt5), a été portée vers **PyQt6**.

- **Modifications majeures** :
  - Mise à jour des imports (`PyQt6.QtWidgets`, `PyQt6.QtCore`, `PyQt6.QtGui`).
  - Adaptation aux changements d'énumérations (ex: `Qt.AlignmentFlag.AlignCenter` au lieu de `Qt.AlignCenter`).
  - Utilisation des nouvelles méthodes recommandées par l'API PyQt6.
- **Résultat** : Une interface plus fluide et une meilleure intégration avec les systèmes d'exploitation modernes.

## 3. Suppression des Bibliothèques Obsolètes

Un nettoyage approfondi des dépendances a été effectué pour alléger le projet et réduire les risques de sécurité.

- **Retraits** : Identification et suppression des bibliothèques qui ne sont plus maintenues ou qui faisaient doublon avec des modules standards de Python 3.13.
- **Remplacement** : Utilisation de solutions intégrées ou plus modernes pour les fonctionnalités critiques (gestion d'images, calculs mathématiques).

## 4. Mise en Place d'une Architecture Logicielle Moderne

Le projet a été restructuré.

- **Modèle-Vue-Contrôleur (MVC)** : Séparation claire entre la logique métier, la gestion des données et l'interface utilisateur.
- **Modularité** : Découpage du code en modules (`colorstudio.model`, `colorstudio.utils`) pour faciliter la réutilisation et les tests.
- **Gestion des Dépendances** : Centralisation des requis techniques via un fichier `requirements.txt` propre.

