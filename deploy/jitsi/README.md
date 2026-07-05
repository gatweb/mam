# Jitsi Meet auto-hébergé (appels sans manipulation)

Serveur Jitsi privé, **sans lobby, sans compte, sans mot de passe** — pour que
l'écran patient rejoigne l'appel 100 % automatiquement.

## Installation (LXC/VM Docker, 2 Go RAM)

```bash
cd deploy/jitsi
cp .env.example .env
nano .env    # PUBLIC_URL + JVB_ADVERTISE_IPS + secrets (voir commentaires)
docker compose up -d
```

## Réseau

| Flux | Port | Direction |
|---|---|---|
| Interface web (via NPM) | 8100 (HTTP interne) | NPM → serveur Jitsi |
| Média audio/vidéo | **10000/UDP** | Internet → serveur Jitsi (ouvrir/NAT sur la box) |

### Proxy Host NPM

- Domain : `meet.votre-domaine.tld`
- Forward : `http://IP-DU-SERVEUR-JITSI:8100`
- **Websockets Support : ✅ obligatoire**
- SSL : certificat Let's Encrypt, Force SSL
- ⚠️ **Pas d'Access List sur ce host** : l'écran patient et vous devez pouvoir
  rejoindre sans mot de passe. La sécurité vient des noms de salons aléatoires.

Sur la box/routeur : rediriger `10000/UDP` vers le serveur Jitsi. Sans cette
redirection, l'appel se connecte mais **ni image ni son** dès qu'on n'est pas
sur le réseau local.

## Configurer Snoozolène

Admin → **Alertes → 📞 Appels vidéo** → URL du serveur Jitsi :
`https://meet.votre-domaine.tld` → Enregistrer.

## Vérifier

1. `https://meet.votre-domaine.tld/test123` depuis deux appareils (dont un en
   4G) : les deux doivent entrer directement, sans lobby, et se voir/entendre.
2. Puis test complet depuis l'admin Snoozolène (voir `docs/appels-video.md`).
