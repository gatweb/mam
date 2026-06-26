# 🌙 Snoozolène

**Écran d'orientation et de réassurance pour les personnes accompagnées (Alzheimer, troubles cognitifs)**

> Né d'un besoin réel, partagé librement. Pour Martine, et pour tous ceux qui traversent les mêmes nuits.

Snoozolène est une application web **locale, open source et sans abonnement** qui transforme une vieille tablette ou un écran branché à un PC en compagnon visuel rassurant pour votre proche. L'aidant la contrôle depuis son téléphone ou PC via un panneau d'administration simple.

---

## ✨ Fonctionnalités

| | |
|---|---|
| 🕐 | Heure, date et moment de la journée en grand |
| 🌤️ | Météo de la semaine (7 jours, Open-Meteo, sans compte) |
| 📅 | Agenda du jour avec messages contextuels (avant / pendant / après) |
| 🔁 | Événements récurrents (quotidien, hebdo, mensuel) |
| 💬 | Message immédiat de l'aidant (apparaît en quelques secondes) |
| 📸 | Diaporama de photos famille avec légendes |
| 👨‍👩‍👧 | Proches avec photos, relation et message rassurant |
| 🌙 | Mode nuit automatique (heures configurables) |
| 📞 | Appels vidéo Jitsi (un clic côté aidant, plein écran côté patient) |
| 🏠 | Intégration Home Assistant (capteurs, présence…) |
| 🔔 | Notifications push via ntfy (écran déconnecté, rappel quotidien) |
| 📱 | PWA installable sur tablette (fonctionne hors ligne) |

---

## 🚀 Démarrage rapide

### Prérequis

- [Docker](https://docs.docker.com/get-docker/) + [Docker Compose](https://docs.docker.com/compose/install/)
- Un terminal

### Installation en une commande

```bash
git clone https://github.com/gatweb/mam.git
cd mam
bash install.sh
```

L'interface admin est disponible sur **http://localhost:3000/admin**  
L'écran patient sur **http://localhost:3000/display**

---

## 🖥️ Déploiement sur Proxmox (recommandé)

La meilleure configuration pour un usage permanent : un conteneur LXC léger sur votre cluster Proxmox.

### 1. Créer le conteneur LXC

Dans l'interface Proxmox :
- Template : **Ubuntu 22.04**
- RAM : **512 Mo** minimum (1 Go recommandé)
- Disque : **8 Go** minimum
- Réseau : IP fixe sur votre LAN (ex: `192.168.0.50`)

### 2. Installer Docker dans le LXC

```bash
# Dans le conteneur
apt update && apt install -y curl git
curl -fsSL https://get.docker.com | sh
```

### 3. Déployer Snoozolène

```bash
git clone https://github.com/gatweb/mam.git /opt/snoozolene
cd /opt/snoozolene
docker compose up -d --build
```

### 4. Démarrage automatique

```bash
# Le service redémarre automatiquement avec Docker
docker compose up -d --restart unless-stopped
```

Accès depuis votre réseau local :
- **Admin** : `http://192.168.0.50:3000/admin`
- **Écran** : `http://192.168.0.50:3000/display`

---

## 📱 Installer sur la tablette (PWA)

### Android / Chrome
1. Ouvrir `http://[ip-serveur]:3000/display` dans Chrome
2. Menu ⋮ → **"Ajouter à l'écran d'accueil"** (ou icône ⊕ dans la barre)
3. L'app se lance en plein écran, sans barre de navigation

### iPad / iPhone / Safari
1. Ouvrir `http://[ip-serveur]:3000/display` dans Safari
2. Icône **Partager** → **"Sur l'écran d'accueil"**
3. Confirmer → icône Snoozolène sur l'accueil

> **Astuce** : La tablette ne se mettra plus en veille grâce au Screen Wake Lock. Pour forcer l'écran allumé sur Android, activez aussi *Paramètres → Options développeur → Écran actif en charge*.

---

## 💻 Vieux PC ou laptop en kiosque

Un vieux laptop Ubuntu branché à un écran dans la chambre est idéal.

```bash
# Installer Chromium
apt install -y chromium-browser

# Lancer en mode kiosque au démarrage
# Ajouter dans /etc/xdg/autostart/snoozolene.desktop :
cat > /etc/xdg/autostart/snoozolene.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Snoozolène
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble http://192.168.0.50:3000/display
EOF
```

Pour empêcher la mise en veille de l'écran :
```bash
# Dans /etc/X11/xorg.conf.d/10-noblank.conf
Section "ServerFlags"
  Option "BlankTime"   "0"
  Option "StandbyTime" "0"
  Option "SuspendTime" "0"
  Option "OffTime"     "0"
EndSection
```

---

## ⚙️ Configuration

### Premier démarrage

Des données de démonstration sont créées automatiquement (Martine, Gaëtan, Sophie, événements et questions types). Vous pouvez les remplacer depuis **Admin → Maison → Remettre les données de démo**.

### Panneau d'administration

| Onglet | Ce qu'on y fait |
|--------|----------------|
| ✉️ Message | Envoyer un message immédiat à l'écran |
| 📅 Agenda | Ajouter des événements (récurrents ou ponctuels) |
| 💬 Questions | Gérer les Q/R affichées en rotation |
| 👨‍👩‍👧 Proches | Photos, relations, activer les appels vidéo |
| 📸 Photos | Album diaporama famille |
| 🔔 Alertes | ntfy, rappel quotidien, heures mode nuit, Home Assistant |
| 🏠 Maison | Nom, message rassurant, coordonnées GPS pour la météo |

### Météo

Dans **Admin → Maison → Météo**, entrer les coordonnées GPS de votre domicile.  
Trouvez-les sur [maps.google.com](https://maps.google.com) → clic droit sur votre adresse.

### Notifications (ntfy)

1. Installer l'app **ntfy** sur votre téléphone ([ntfy.sh](https://ntfy.sh))
2. Créer un topic unique (ex: `snoozolene-dupont-2026`)
3. Renseigner dans **Admin → Alertes → Notifications**

Vous recevrez une alerte si l'écran se déconnecte, et un rappel quotidien facultatif.

### Home Assistant

Dans **Admin → Alertes → Home Assistant** :
1. URL de votre instance (ex: `http://192.168.0.100:8123`)
2. Long-Lived Access Token (Profil HA → Sécurité → tout en bas)
3. Rechercher vos entités et les ajouter à l'écran

### Appels vidéo

Dans **Admin → Proches**, activer le bouton 🎥 pour chaque proche autorisé.  
Un clic sur 📞 lance un appel Jitsi Meet : l'écran de Martine bascule automatiquement en plein écran vidéo. Elle n'a rien à faire.

---

## 🔧 Variables d'environnement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `PUBLIC_API_URL` | `http://localhost:8000` | URL du backend (à changer si accès distant) |
| `MEDIA_DIR` | `/data/media` | Dossier de stockage des photos |

---

## 🤝 Contribuer

Toute contribution est la bienvenue ! Idées, corrections, traductions…

1. Fork le dépôt
2. Créer une branche (`git checkout -b feature/ma-fonctionnalite`)
3. Committer vos changements
4. Ouvrir une Pull Request

---

## 🔭 Aller plus loin

### Assistant vocal local (avec Ollama)

> ⚠️ Nécessite un PC avec au moins **8 Go de RAM** et de préférence un GPU.

Il est possible d'ajouter un assistant vocal qui répond aux questions de votre proche à voix haute, sans envoyer de données sur Internet.

**Stack recommandée :**
- [Ollama](https://ollama.ai) + modèle `mistral` ou `llama3`
- [Whisper.cpp](https://github.com/ggerganov/whisper.cpp) pour la transcription vocale
- Un micro USB dans la chambre

L'idée : Martine dit "Où est Gaëtan ?" → Whisper transcrit → Ollama génère une réponse depuis les données Snoozolène → synthèse vocale (piper-tts) → réponse audio.

Cette fonctionnalité est sur la roadmap. Les contributions sont bienvenues !

### Intégration sonnette / caméra

Avec Home Assistant, vous pouvez déclencher une notification ntfy quand quelqu'un sonne, ou afficher un flux caméra sur l'écran via un appel vidéo automatique.

---

## 🏗️ Architecture

```
snoozolene/
├── backend/          # FastAPI + SQLite (SQLModel)
│   ├── main.py       # Routes API + WebSocket + scheduler
│   ├── models.py     # Modèles de données
│   ├── notify.py     # Notifications ntfy
│   └── database.py   # Init SQLite
├── frontend/         # SvelteKit (Svelte 5 runes)
│   ├── src/routes/
│   │   ├── display/  # Écran patient (plein écran, PWA)
│   │   └── admin/    # Panneau aidant
│   └── static/       # PWA manifest, service worker, icônes
├── data/             # Volume Docker (SQLite + photos)
└── docker-compose.yml
```

**Flux temps réel :** L'admin envoie une mise à jour → le backend broadcast via WebSocket → l'écran patient se rafraîchit en moins d'une seconde.

---

## 📄 Licence

MIT — libre d'utilisation, de modification et de redistribution.

---

*Fait avec ❤️ pour Martine, et pour tous ceux qui accompagnent leurs proches au quotidien.*
