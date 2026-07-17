# Appels vidéo « zéro manipulation »

Le but : l'aidant appuie sur 📞 dans l'admin → l'écran de la personne
accompagnée bascule **tout seul** en plein écran d'appel, caméra et micro
actifs. Elle n'a **rien** à toucher : pas de mot de passe, pas de lobby,
pas de bouton « Rejoindre ».

## Pourquoi ça bloquait

1. **meet.jit.si a changé les règles** : depuis fin 2023, tout salon créé sur
   le serveur public exige qu'un **modérateur authentifié** (compte Google,
   GitHub ou Facebook) démarre la réunion. Tant que personne d'authentifié
   n'est là, les invités voient « En attente de l'organisateur… ».
2. L'ancien paramètre `prejoinPageEnabled` est **déprécié** : sur les versions
   récentes de Jitsi il est ignoré → l'écran « Rejoindre la réunion » apparaît.
   Le code utilise maintenant `config.prejoinConfig.enabled=false` (avec
   l'ancien paramètre conservé pour compatibilité).

## Option A (recommandée) — Jitsi auto-hébergé, sans lobby ni compte

Vous contrôlez tout : pas de lobby, pas d'authentification, pas de limite.
Un conteneur LXC/VM Docker sur votre Proxmox suffit (2 Go RAM recommandés).

```bash
cd deploy/jitsi
cp .env.example .env
# éditez .env : domaine, adresse IP publique/locale
docker compose up -d
```

Puis dans **Admin → Alertes → Appels vidéo**, remplacez l'URL par celle de
votre serveur (ex : `https://meet.votre-domaine.tld`).

Voir `deploy/jitsi/README.md` pour la configuration NPM (ports UDP 10000
à ouvrir/rediriger, websockets, etc.).

## Option B — rester sur meet.jit.si

Ça fonctionne, avec une contrainte : **vous** (l'appelant) devez être connecté
à un compte (Google/GitHub) dans votre navigateur sur meet.jit.si. Vous êtes
alors modérateur : dès que vous rejoignez, l'écran de votre proche entre
automatiquement dans l'appel. De son côté, aucune manipulation — mais elle
verra « en attente de l'organisateur » pendant les secondes où vous n'avez pas
encore rejoint.

À tester en conditions réelles avant de compter dessus : le comportement de
meet.jit.si peut évoluer sans préavis. C'est précisément pour ça que
l'auto-hébergement (option A) est recommandé.

## Côté kiosque : autoriser caméra/micro sans question

Chromium demande normalement l'autorisation caméra/micro — une question à
laquelle la personne ne doit jamais avoir à répondre. Le lancement complet
du kiosque (tous les flags, attente du serveur, redémarrage auto) est
fourni clé en main dans **`deploy/kiosk/`** — suivez son README.

Flags essentiels pour les appels et le réveil :

- `--use-fake-ui-for-media-stream` : accepte automatiquement caméra + micro
  (pas de popup). Alternative plus fine : dans Chromium, ouvrir une fois le
  site et choisir « Toujours autoriser ».
- `--autoplay-policy=no-user-gesture-required` : indispensable aussi pour que
  le **son du réveil et la radio** démarrent sans toucher l'écran.

## Checklist de test réel (5 minutes)

1. Admin → Proches → 📞 sur votre fiche : votre navigateur ouvre le salon.
2. L'écran patient passe en plein écran d'appel **sans aucune action**.
3. Vous vous voyez/entendez dans les deux sens.
4. Admin → « Raccrocher » (fin d'appel) → l'écran revient au dashboard.
5. Refaites le test **depuis la 4G** (hors du réseau local) : c'est le cas
   réel des vacances.

## Diagnostic « les appels ne passent pas » (ordre des causes les plus probables)

Avant tout, ouvrez **Admin → Alertes → 🩺 État du système** : la ligne
« Serveur d'appels (Jitsi) » doit être 🟢 avec votre URL auto-hébergée.

1. **`jitsi_url` restée sur meet.jit.si** dans l'admin → appels bloqués
   « en attente de l'organisateur ». Vérifiez l'URL affichée dans la carte
   santé (10 secondes).
2. **`JVB_ADVERTISE_IPS` incorrect** dans le `.env` du serveur Jitsi : il doit
   contenir l'IP **locale du LXC Jitsi** et l'**IP publique de la box**.
   Symptôme exact : la connexion s'établit mais **ni image ni son**.
   Vérifier :
   `grep JVB_ADVERTISE_IPS deploy/jitsi/.env`, corriger, puis
   `docker compose up -d` dans ce dossier.
3. **NAT port 10000/UDP** non redirigé vers le LXC Jitsi (ou hairpin NAT
   absent pour les tests depuis le LAN). Test : `docker compose logs jvb`
   sur le LXC pendant un appel 4G — si aucune ligne n'arrive, le flux vidéo
   n'atteint jamais le serveur.
4. **Kiosque sans `--use-fake-ui-for-media-stream`** : la popup caméra bloque
   l'entrée en conférence. Réglé une fois pour toutes par `deploy/kiosk/`.
5. **IP publique de la box changeante** (DHCP opérateur) : `JVB_ADVERTISE_IPS`
   devient faux silencieusement. Si l'IP n'est pas fixe, prévoir un DynDNS +
   un script qui met à jour le `.env` (ou demander une IP fixe à l'opérateur).

Test décisif final : `https://meet.votre-domaine/test123` depuis un
téléphone **en 4G** + un PC local : image + son dans les deux sens.
