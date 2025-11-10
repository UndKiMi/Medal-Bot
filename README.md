# 🤖 Survey Bot - Automated Survey Completion Tool

> Bot automatique pour remplir des questionnaires de satisfaction en ligne

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Chrome](https://img.shields.io/badge/Chrome-Required-green.svg)](https://www.google.com/chrome/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 C'est quoi ce bot ?

Un programme qui remplit **automatiquement** des questionnaires de satisfaction pour vous. Il simule un vrai humain pour ne pas être détecté.

**🔗 URL du questionnaire :** Configurable dans le fichier `.env`

---

## ✨ Qu'est-ce qu'il fait ?

- ✅ **Remplit automatiquement** les questionnaires avec les meilleures notes
- 🖥️ **Interface graphique simple** - Pas besoin de toucher au code !
- 📊 **Statistiques en direct** - Voir combien de questionnaires ont été remplis
- 🤖 **Simule un humain** - Frappe avec des erreurs, bouge la souris, fait des pauses
- 🛡️ **Anti-détection avancée** - Simulation humaine réaliste
- ⏰ **Planification intelligente** - Fonctionne uniquement pendant les heures d'ouverture (11h30-21h38)
- 📈 **6 questionnaires par jour** - Répartis automatiquement sur la journée

---

## 🚀 Installation

### Étape 1️⃣ : Télécharger le bot

1. Cliquez sur le bouton vert **"Code"** en haut de la page
2. Cliquez sur **"Download ZIP"**
3. Décompressez le fichier ZIP sur votre bureau

### Étape 2️⃣ : Installer Python

1. Allez sur https://www.python.org/downloads/
2. Téléchargez **Python 3.12** (ou plus récent)
3. **IMPORTANT** : Cochez la case **"Add Python to PATH"** pendant l'installation
4. Cliquez sur **"Install Now"**

### Étape 3️⃣ : Installer Chrome

Si vous n'avez pas Google Chrome :
1. Allez sur https://www.google.com/chrome/
2. Téléchargez et installez Chrome

### Étape 4️⃣ : Installer les dépendances

1. Ouvrez le dossier **Survey-Bot**
2. **Double-cliquez** sur le fichier `install_dependencies.bat`
3. Attendez que l'installation se termine (ça peut prendre 2-3 minutes)

---

## 🎮 Utilisation

### 🖥️ Méthode 1 : Utiliser l'exécutable

1. Allez dans le dossier **`dist/`**
2. **Double-cliquez** sur **`SurveyBot.exe`**
3. L'interface s'ouvre automatiquement
4. Cliquez sur **"▶️ LANCER LE BOT"**
5. C'est tout ! Le bot fait le reste 🎉

### 🐍 Méthode 2 : Lancer avec Python

1. **Double-cliquez** sur `start_gui.bat`
2. L'interface s'ouvre
3. Cliquez sur **"▶️ LANCER LE BOT"**

---

## 📱 Interface Graphique - Mode d'emploi

![Interface du Bot](https://i.imgur.com/cXNropP.png)


### 🎮 Boutons expliqués

- **▶️ LANCER LE BOT** : Démarre le bot (il remplit les questionnaires automatiquement)
- **⏹️ STOPPER LE BOT** : Arrête le bot proprement
- **🗑️ EFFACER LES LOGS** : Nettoie la console

---

## 🐛 Prérequis

| Logiciel | Version | Où le télécharger |
|----------|---------|-------------------|
| 🐍 Python | 3.8+ | https://www.python.org/downloads/ |
| 🌐 Chrome | Récent | https://www.google.com/chrome/ |
| 📡 Internet | Stable | Votre connexion habituelle |

---

## 📁 Structure du Projet

```
Survey-Bot/
├── 📁 dist/
│   └── SurveyBot.exe         ⭐ FICHIER PRINCIPAL - Double-cliquez ici !
├── 📁 AVIS/                  📝 Fichiers d'avis (commentaires automatiques)
│   ├── avis_drive.txt
│   ├── avis_comptoir.txt
│   └── ...
├── 📁 bot/                   🤖 Code source du bot
│   ├── automation.py         🎯 Logique principale
│   ├── scheduler.py          ⏰ Planification intelligente
│   └── utils/                🛠️ Outils
├── gui.py                    🖥️ Interface graphique
├── .env                      🔧 Configuration personnalisée
├── .env.example              📋 Modèle de configuration
├── config.yaml               ⚙️ Configuration (legacy)
├── start_gui.bat             🚀 Lanceur rapide
└── README.md                 📖 Ce fichier
```

---

## ⚙️ Configuration

### 🔧 Configuration via fichier .env

Le bot utilise un fichier `.env` pour toutes les configurations modifiables. Pour personnaliser :

1. Ouvrez le fichier `.env` à la racine du projet
2. Modifiez les valeurs selon vos besoins :

```env
LOCATION_CODE=XXXX
SURVEY_URL=https://example.com/survey

CHROME_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64)...
CHROME_WINDOW_SIZE=1920,1080
CHROME_LANGUAGES=fr-FR,fr

TIMING_SHORT_WAIT_MIN=1
TIMING_SHORT_WAIT_MAX=3
TIMING_MEDIUM_WAIT_MIN=3
TIMING_MEDIUM_WAIT_MAX=7
```

**Variables importantes :**
- `LOCATION_CODE` : Code de l'établissement (4 chiffres)
- `SURVEY_URL` : URL du questionnaire
- `TIMING_*` : Délais d'attente pour simuler un comportement humain

### Modifier les horaires

Ouvrez `bot/scheduler.py` et changez :
```python
BOT_START_TIME = time(11, 30)
BOT_END_TIME = time(21, 38)
DAILY_QUESTIONNAIRES = 6
```

---

## 🎯 Comment ça marche ?

### 1️⃣ Planification Intelligente
- Le bot démarre automatiquement à **11h30**
- Il s'arrête automatiquement à **21h38**
- Il répartit **6 questionnaires** sur la journée
- Il attend entre **1h et 2h** entre chaque questionnaire

### 2️⃣ Simulation Humaine
- ⌨️ **Frappe avec erreurs** : 2% de fautes de frappe + corrections
- 🖱️ **Mouvements de souris** : Déplacements aléatoires et naturels
- ⏱️ **Timings réalistes** : Pauses de 2-5 secondes entre chaque action
- 📜 **Scroll progressif** : Défilement smooth comme un humain

### 3️⃣ Anti-Détection
- 🛡️ **Masquage WebDriver** : Le site ne détecte pas que c'est un bot
- 🎭 **Empreinte navigateur** : Simule un vrai utilisateur Chrome
- 🔄 **Variation des réponses** : 85% excellent, 10% bon, 5% moyen
- 🕐 **Heures de visite réalistes** : Génère des heures crédibles

---

## 📊 Statistiques Sauvegardées

Le bot sauvegarde automatiquement dans `bot_stats.json` :
- ✅ Nombre total de questionnaires
- 📈 Taux de succès/échec
- 📋 Compteurs par catégorie
- 🕐 Historique des 50 derniers questionnaires

---

## 🔧 Commandes Avancées

### Lancer en mode debug
```bash
python gui.py --debug
```

### Compiler un nouvel exécutable
```bash
python -m PyInstaller build_exe.spec
```

### Tester le scheduler
```bash
python test_scheduler.py
```

---

## 📝 Logs & Débogage

Les logs sont enregistrés dans `logs/bot.log` :
```
[14:25:30] 🚀 Démarrage du bot...
[14:25:32] 🌐 Initialisation du navigateur...
[14:25:35] ✅ Navigateur initialisé avec succès
[14:25:40] 🤖 Exécution du questionnaire...
[14:26:15] ✅ Questionnaire #1 terminé avec succès!
```

---

## 🎓 Parcours Supportés

Le bot gère automatiquement **6 types de commandes** :

| Type | Étapes supplémentaires | Difficulté |
|------|------------------------|------------|
| 🍔 **Borne** | Type + Lieu (2 étapes) | ⭐⭐⭐ |
| 🧑‍💼 **Comptoir** | Type + Lieu (2 étapes) | ⭐⭐⭐ |
| 📱 **Click & Collect App** | Lieu (1 étape) | ⭐⭐⭐ |
| 💻 **Click & Collect Site** | Lieu (1 étape) | ⭐⭐⭐ |
| 🚗 **Drive** | Type + Lieu | ⭐⭐⭐ |
| 🏠 **Livraison** | Pas de service LAD | 0 |

---

## 🛡️ Technologie Anti-Détection

### Comment le bot évite d'être détecté ?

#### 🎭 Masquage WebDriver
```javascript
// Le bot masque toutes les traces d'automatisation
navigator.webdriver = undefined  // ✅ Invisible
window.chrome.runtime = {}       // ✅ Simule un vrai Chrome
```

#### ⏱️ Timings Humains
- **Frappe** : 2-5 secondes par champ (avec erreurs 2%)
- **Clics** : Hésitation de 0.1-0.3 secondes
- **Scroll** : Défilement progressif et smooth
- **Pauses** : Micro-pauses aléatoires (10% du temps)

#### 🎯 Variation des Réponses
- 100% → Note **Excellent** (5/5)
- Toujours des avis très positifs
- Aucun avis moyen ou négatif

#### 🕐 Heures de Visite Réalistes
Le bot génère des heures de visite crédibles :
- Entre 11h30 et l'heure actuelle
- Maximum 5 minutes dans le passé
- Jamais dans le futur

---

## 🚨 Détections Contournées

| Système de détection | Status |
|---------------------|--------|
| ✅ AppDynamics RUM | Contourné |
| ✅ Grafana RUM Gateway | Contourné |
| ✅ Session Tracking | Contourné |
| ✅ Canvas Fingerprinting | Contourné |
| ✅ WebDriver Detection | Contourné |
| ✅ Timing Analysis | Contourné |

---

## 💡 Conseils d'Utilisation

### ✅ À FAIRE
- ✅ Lancer le bot pendant les heures d'ouverture (11h30-21h38)
- ✅ Laisser le bot tourner en arrière-plan
- ✅ Vérifier les statistiques régulièrement
- ✅ Garder Chrome à jour

### ❌ À NE PAS FAIRE
- ❌ Lancer plusieurs instances du bot en même temps
- ❌ Modifier les fichiers pendant que le bot tourne
- ❌ Fermer Chrome manuellement pendant l'exécution
- ❌ Utiliser votre ordinateur pour d'autres tâches intensives

---

## 🎓 FAQ

### ❓ Le bot est-il détectable ?
**Non.** Le bot utilise les technologies les plus avancées pour simuler un humain.

### ❓ Combien de questionnaires par jour ?
**6 questionnaires** répartis automatiquement entre 11h30 et 21h38.

### ❓ Puis-je utiliser mon ordinateur pendant que le bot tourne ?
**Oui**, mais évitez les tâches intensives. Le bot tourne en arrière-plan.

### ❓ Le bot fonctionne-t-il la nuit ?
**Non.** Le bot s'arrête automatiquement à 21h38 et redémarre à 11h30 le lendemain.

### ❓ Puis-je changer le nombre de questionnaires ?
**Oui.** Modifiez `DAILY_QUESTIONNAIRES` dans `bot/scheduler.py`.

### ❓ Le bot peut-il remplir d'autres questionnaires ?
**Oui.** Configurez l'URL du questionnaire dans le fichier `.env`.

---

## 🔒 Sécurité & Confidentialité

- 🔐 **Aucune donnée envoyée** : Le bot fonctionne 100% en local
- 🛡️ **Pas de télémétrie** : Aucune information n'est collectée
- 🔒 **Code open-source** : Vous pouvez vérifier le code vous-même
- 💾 **Données locales** : Tout est sauvegardé sur votre PC

---

## 📜 Avertissement

### ⚠️ Avertissement Légal
Ce bot est fourni **à des fins éducatives uniquement**. 

**L'auteur n'est pas responsable de :**
- ❌ L'utilisation frauduleuse du bot
- ❌ Les violations des conditions d'utilisation des plateformes
- ❌ Les conséquences légales de son utilisation

**Utilisez ce bot à vos propres risques.**

---

## 🎉 Remerciements

Merci d'utiliser Survey Bot ! Si ce projet vous a aidé, n'hésitez pas à :
- ⭐ Mettre une étoile sur GitHub
- 💬 Laisser un commentaire

---

<div align="center">

**Made with ❤️ by KiMi**

🤖 **Combien de temps le niveau ?!**

</div>
