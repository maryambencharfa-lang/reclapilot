# ReclaPilot dynamique

Cette version utilise une base SQLite.

## Fonctionnement

1. La page Nouvelle réclamation enregistre une ligne dans la base.
2. La page Liste des réclamations lit cette base.
3. Le Dashboard calcule automatiquement les KPI et graphiques depuis la même base.
4. Le statut peut être modifié depuis la liste.

## Lancement

```cmd
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Connexion :

- Identifiant : admin
- Mot de passe : 1234
