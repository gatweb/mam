# 🌙 Snoozolène

**Écran d'orientation et de réassurance pour les personnes accompagnées — Alzheimer, troubles cognitifs**

> Né d'un besoin réel, partagé librement.  
> Pour Agnès, et pour tous ceux qui traversent les mêmes nuits.

Snoozolène est une application web **locale, open source et sans abonnement** qui transforme une vieille tablette ou un écran branché à un PC en compagnon visuel rassurant pour votre proche. L'aidant la contrôle depuis son téléphone ou PC via un panneau d'administration simple — les changements apparaissent sur l'écran en moins d'une seconde.

---

## ✨ Fonctionnalités

| | |
|---|---|
| 🕐 | Heure, date et moment de la journée en grand |
| 🌤️ | Météo de la semaine (7 jours, Open-Meteo, sans compte) |
| 🍂 | Thèmes saisonniers automatiques (printemps / été / automne / hiver) |
| 📅 | Agenda du jour avec messages contextuels (avant / pendant / après) |
| 🔁 | Événements récurrents (quotidien, hebdomadaire, mensuel) |
| 🎂 | Anniversaires des proches avec bannière d'alerte 3 jours avant |
| 💬 | Message immédiat de l'aidant (apparaît sur l'écran en quelques secondes) |
| 📸 | Diaporama de photos famille avec légendes |
| 👨‍👩‍👧 | Proches avec photos, relation et message rassurant |
| 🏠 | Indicateur des personnes présentes aujourd'hui |
| 🌙 | Mode nuit automatique (heures configurables) |
| ⏰ | Réveil programmable avec flux radio (lecture directe dans le navigateur) |
| 🎵 | Lecture de musique / radio à la demande depuis l'admin |
| 📞 | Appels vidéo Jitsi (un clic côté aidant, plein écran côté patient) |
| 🏠 | Intégration Home Assistant (capteurs, présence, réveil sur media_player) |
| 🔔 | Notifications push via ntfy (écran déconnecté, rappel quotidien) |
| 📱 | PWA installable sur tablette (fonctionne hors ligne, anti-mise en veille) |
| 💾 | Sauvegarde et restauration en un clic |

---

## 📸 Aperçu

```
┌─────────────────────────────────────────────────┐
│  Lundi 30 juin 2026          🌤 23° / 18°  🌡 22° │
├─────────────────────────────────────────────────┤
│                                                 │
│   Bonjour Agnès, tu es chez toi.               │
│   Tu es en sécurité. ❤️                         │
│                                                 │
│   Gaëtan est avec toi aujourd'hui.             │
│                                                 │
│   📅 Aujourd'hui                                │
│      Kiné Marc à 10h30                          │
│                                                 │
│   👨 Gaëtan          👩 Sophie                  │
│   ton fils           ta fille                   │
│                                                 │
└─────────────────────────────────────────────────┘
```

*(Des captures d'écran réelles sont disponibles dans `/docs/screenshots/`)*

---

## 🚀 Démarrage rapide

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/)
- Un terminal (Linux, macOS ou WSL)

### Installation en une commande

```bash
git clone https://github.com/gatweb/mam.git
cd mam
bash install.sh
```

L'interface admin est disponible sur **http://localhost:3000/admin**  
L'écran patient sur **http://localhost:3000/display**

Des données de démonstration sont créées au premier démarrage pour faciliter la prise en main.

---

## 🖥️ Déploiement recommandé

### Proxmox LXC (serveur permanent)

La configuration idéale pour une installation qui tourne 24h/24 sans occuper un PC.

1. Créer un conteneur LXC **Ubuntu 22.04** — 512 Mo RAM, 8 Go disque, IP fixe
2. Dans le conteneur :
```bash
apt update && apt install -y curl git
curl -fsSL https://get.docker.com | sh
git clone https://github.com/gatweb/mam.git /opt/snoozolene
cd /opt/snoozolene && docker compose up -d --build
```

Accès depuis votre réseau local :
- **Admin** : `http://192.168.0.50:3000/admin`
- **Écran** : `http://192.168.0.50:3000/display`

### Vieux PC ou laptop en kiosque

Un laptop branché à un écran dans la chambre est parfait. Aucun matériel neuf à acheter.

```bash
# Lancer Chrome en mode kiosque au démarrage
chromium --kiosk --noerrdialogs --disable-infobars http://[ip-serveur]:3000/display
```

Pour éviter la mise en veille de l'écran, créer `/etc/xdg/autostart/snoozolene.desktop` :
```ini
[Desktop Entry]
Type=Application
Name=Snoozolène
Exec=chromium-browser --kiosk --noerrdialogs http://[ip-serveur]:3000/display
```

---

## 📱 Installer sur tablette (PWA)

### Android / Chrome
1. Ouvrir `http://[ip-serveur]:3000/display` dans Chrome
2. Menu ⋮ → **"Ajouter à l'écran d'accueil"**
3. L'app se lance en plein écran, sans barre de navigation

### iPad / Safari
1. Ouvrir l'URL dans Safari
2. Icône **Partager** → **"Sur l'écran d'accueil"**

> **Astuce** : L'écran ne se met plus en veille grâce au Screen Wake Lock. Sur Android, activez aussi *Options développeur → Écran actif en charge* pour les tablettes branchées en permanence.

---

## ⚙️ Configuration

### Panneau d'administration

| Section | Ce qu'on y fait |
|---------|----------------|
| ✉️ Messages | Envoyer un message immédiat à l'écran, gérer l'historique |
| 📅 Agenda | Ajouter des événements (ponctuels ou récurrents) |
| 💬 Questions | Gérer les Q/R affichées en rotation sur l'écran |
| 👨‍👩‍👧 Proches | Photos, relation, date de naissance, marquer comme "présent" |
| 📸 Photos | Album diaporama famille |
| ⏰ Réveil | Heure, jours, URL du flux radio |
| 🎵 Musique | Lancer / arrêter la radio à la demande |
| 🔔 Alertes | ntfy, rappel quotidien, heures du mode nuit |
| 🏠 Home Assistant | Capteurs à afficher, lecteur média, token d'accès |
| 🌍 Maison | Nom, message rassurant, coordonnées GPS pour la météo |

### Météo

Dans **Admin → Maison**, entrer les coordonnées GPS de votre domicile.  
Trouvez-les sur [maps.google.com](https://maps.google.com) → clic droit → *"C'est ici"*.

### Notifications push (ntfy)

1. Installer l'app **ntfy** sur votre téléphone ([ntfy.sh](https://ntfy.sh))
2. Créer un topic unique (ex: `snoozolene-dupont-2026`)
3. Renseigner dans **Admin → Alertes → Notifications**

Vous recevrez une alerte si l'écran se déconnecte, et un rappel quotidien facultatif pour ne pas oublier de mettre à jour le message du jour.

### Home Assistant (optionnel)

Dans **Admin → Home Assistant** :
1. URL de votre instance (ex: `http://192.168.0.100:8123`)
2. Long-Lived Access Token (Profil HA → Sécurité → tout en bas)
3. Rechercher vos entités et les ajouter à l'écran

Les capteurs s'affichent en haut ou en bas de l'écran (configurable). Le lecteur média peut être utilisé pour le réveil en parallèle de la lecture navigateur.

### Réveil et radio

Dans **Admin → Réveil** :
- Activer, choisir l'heure et les jours
- Coller l'URL d'un flux radio (ex: `https://radio.rtbf.be/viva-mo/mp3-160/me`)

La musique est jouée directement dans le navigateur de la tablette — aucune dépendance externe. L'overlay de réveil disparaît au toucher.

---

## 🏗️ Architecture

```
snoozolene/
├── backend/          # FastAPI + SQLite (SQLModel)
│   ├── main.py       # Routes API + WebSocket + APScheduler
│   ├── models.py     # Modèles de données
│   ├── notify.py     # Notifications ntfy
│   └── database.py   # Init SQLite + migrations
├── frontend/         # SvelteKit (Svelte 5 runes)
│   ├── src/routes/
│   │   ├── display/  # Écran patient (plein écran, PWA)
│   │   └── admin/    # Panneau aidant
│   └── static/       # PWA manifest, service worker, icônes
├── data/             # Volume Docker persistant (SQLite + photos)
└── docker-compose.yml
```

**Flux temps réel :** L'admin envoie une mise à jour → le backend broadcast via WebSocket → l'écran patient se rafraîchit en moins d'une seconde, sans rechargement de page.

**Ressources** : fonctionne sur 1% de CPU et 11% de RAM (Proxmox LXC 512 Mo). Convient à un Raspberry Pi ou un vieux PC.

---

## 🔭 Aller plus loin

### Assistant vocal local

> ⚠️ Nécessite un PC avec au moins 8 Go de RAM (GPU recommandé).

Il est possible d'ajouter un assistant vocal qui répond aux questions de votre proche à voix haute, sans envoyer de données sur Internet.

**Stack envisagée :**
- [Ollama](https://ollama.ai) + modèle `mistral` ou `llama3`
- [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) pour la transcription vocale
- [Piper TTS](https://github.com/rhasspy/piper) pour la synthèse vocale

Agnès dit *"Où est Gaëtan ?"* → Whisper transcrit → Ollama répond depuis les données Snoozolène → Piper lit la réponse à voix haute.

Cette fonctionnalité est sur la roadmap. Les contributions sont bienvenues !

### Intégration sonnette / caméra

Avec Home Assistant, vous pouvez déclencher une notification ntfy quand quelqu'un sonne, ou afficher un flux caméra sur l'écran via un appel vidéo automatique.

---

## 🤝 Contribuer

Toute contribution est la bienvenue : idées, corrections de bugs, traductions, nouvelles fonctionnalités.

1. Fork le dépôt
2. Créer une branche (`git checkout -b feature/ma-fonctionnalite`)
3. Committer vos changements
4. Ouvrir une Pull Request

---

## 📄 Licence

MIT — libre d'utilisation, de modification et de redistribution.

---

*Fait avec ❤️ pour Agnès, et pour tous ceux qui accompagnent leurs proches au quotidien.*
