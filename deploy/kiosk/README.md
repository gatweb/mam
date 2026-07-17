# Kiosque Snoozolène — démarrage automatique sans écran blanc

Ce dossier corrige l'incident de juillet 2026 : après le redémarrage
nocturne du PC, Chromium s'ouvrait sur une **page blanche** (le navigateur
partait avant le réseau/le serveur et ne réessayait jamais) et un **mot de
passe** était parfois demandé (trousseau de clés ou écran de connexion).

Le correctif tient en 3 couches :

1. **Autologin** : la session s'ouvre toute seule → pas d'écran de connexion.
2. **Ce service** : attend que le serveur réponde 200 avant de lancer
   Chromium, avec les flags « zéro manipulation », et le relance s'il meurt.
3. **L'application** : si le premier chargement échoue quand même, l'écran
   affiche « Je me prépare… » et réessaie en boucle (livré avec le frontend,
   rien à installer).

## Installation (une fois, sur le PC kiosque)

```bash
# 1. Copier les fichiers
mkdir -p ~/.local/bin ~/.config/systemd/user
cp kiosk-launch.sh ~/.local/bin/snoozolene-kiosk.sh
chmod +x ~/.local/bin/snoozolene-kiosk.sh
cp snoozolene-kiosk.service ~/.config/systemd/user/

# 2. Adapter l'URL du serveur dans le service
#    (remplacer 192.168.0.50 par l'IP de votre serveur Snoozolène)
nano ~/.config/systemd/user/snoozolene-kiosk.service

# 3. Activer et démarrer
systemctl --user daemon-reload
systemctl --user enable --now snoozolene-kiosk.service

# 4. Voir les logs (utile en cas de problème)
journalctl --user -u snoozolene-kiosk.service -f
```

⚠️ Ne PAS activer `loginctl enable-linger` : le service a besoin de la
session graphique ouverte (étape autologin ci-dessous) ; linger le ferait
partir trop tôt, sans écran.

## Autologin — plus d'écran de connexion

### Ubuntu/GNOME avec GDM

Éditer `/etc/gdm3/custom.conf` (ou `/etc/gdm/custom.conf` sur certaines
versions) :

```ini
[daemon]
AutomaticLoginEnable = true
AutomaticLogin = agnes        # ← le nom d'utilisateur de la session kiosque
```

### LightDM (Xubuntu, Lubuntu…)

Éditer `/etc/lightdm/lightdm.conf` :

```ini
[Seat:*]
autologin-user=agnes          # ← le nom d'utilisateur de la session kiosque
autologin-user-timeout=0
```

Puis redémarrer : la session doit s'ouvrir sans rien demander.

## Le « mot de passe au démarrage » (trousseau de clés)

C'était Chromium qui déclenchait le déverrouillage du trousseau GNOME après
l'autologin. Le flag `--password-store=basic` (déjà dans le script) le
supprime définitivement : Chromium n'utilise plus le trousseau. Aucune autre
action nécessaire — en particulier, ne laissez jamais Agnès taper quoi que
ce soit : si une demande de mot de passe réapparaît, c'est un bug à signaler.

## Wayland (si la session n'est pas X11)

Le service suppose une session X11 (`DISPLAY=:0`). Pour vérifier :

```bash
echo $XDG_SESSION_TYPE     # « x11 » → rien à faire ; « wayland » → lire la suite
```

Sous Wayland : retirer les deux lignes `Environment=DISPLAY/XAUTHORITY` du
service et ajouter `--ozone-platform=wayland` aux flags Chromium dans
`snoozolene-kiosk.sh`.

## Redémarrage nocturne (le cron de 2 h)

Le couple autologin + service rend le redémarrage quotidien sûr. Pour le
programmer (recommandé : un PC qui tourne des mois sans reboot finit par
tousser) :

```bash
sudo crontab -e
# Ajouter :
0 2 * * * /sbin/reboot
```

Au retour, l'écran se rallume tout seul sur le tableau de bord, et l'aidant
reçoit une notification « 🖥️ Écran en ligne » (heartbeat de démarrage du
backend) puis « ✅ Écran reconnecté » si la coupure a duré plus d'une minute.

## Vérification après installation

1. `systemctl --user status snoozolene-kiosk.service` → *active (running)*.
2. Éteindre le serveur Snoozolène puis redémarrer le PC : Chromium ne doit
   PAS apparaître tant que le serveur est éteint ; il se lance tout seul
   quand le serveur revient (c'est la boucle d'attente du script).
3. Serveur allumé, `sudo reboot` : l'écran doit revenir sur le tableau de
   bord sans aucune intervention, en moins de 2 minutes.
