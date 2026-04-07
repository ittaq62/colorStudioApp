# Migration technique — ColorStudio

## Mise à jour vers Python 3.13 et PyQt6

-> migration de l'ensemble du projet vers Python 3.13 car dernière version dispo sur la machine (avec `python3 --version`)
-> remplacement de tous les imports `PyQt5` par `PyQt6` (`Qt.Orientation.Horizontal`, `QImage.Format.Format_RGB888`)
-> suppression du widget `QGLWidget` (supprimé dans Qt6) pour `QOpenGLWidget`
-> mise à jour de l'API `moderngl`  
-> remplacement de `easygui` par `QFileDialog` natif PyQt6. L'appel `app.exec_()`
-> reformatage du code avec une indentation

## Nettoyage et suppression des imports inutilisés

-> suppression de tous les imports obsolètes et inutilisés
----> dans `colorStudioController.py` : `imageio`, `moderngl`, `numpy` et `skimage`
----> dans `colorStudioUIBuilder.py` : `sys`, `imageio`, `moderngl` et `numpy`
----> dans `colorStudioWidget.py` où `imageio` était importé sans jamais être appelé.
