# Sauvegardes

Deux niveaux de protection, complémentaires :

## 1. Sauvegarde automatique nocturne (intégrée, rien à faire)

Chaque nuit à **3 h 30**, le backend crée un ZIP complet (base de données +
photos + sons) dans `data/backups/` et garde les **7 derniers**. En cas
d'échec, vous recevez une notification ntfy prioritaire.

Réglable via variables d'environnement du conteneur backend
(`docker-compose.yml`) :

| Variable | Défaut | Rôle |
|---|---|---|
| `BACKUP_TIME` | `03:30` | heure de la sauvegarde |
| `BACKUP_KEEP` | `7` | nombre de ZIP conservés |
| `BACKUP_DIR` | `/data/backups` | dossier de destination (dans le volume) |

⚠️ Ces ZIP sont sur le **même disque** que l'application : ils protègent d'une
fausse manipulation ou d'une base corrompue, pas d'une panne de la machine.
D'où le niveau 2.

## 2. Copie hors machine (fortement recommandé)

Depuis **n'importe quelle autre machine** (autre nœud Proxmox, NAS, PC), l'API
fournit le ZIP complet à la demande — un cron suffit :

```bash
# crontab -e sur l'autre machine (ex: un autre nœud Proxmox)
# Tous les jours à 4 h 30, garder 30 jours
30 4 * * * curl -sf -o /mnt/backups/snoozolene-$(date +\%F).zip http://IP-SNOOZOLENE:8000/api/backup && find /mnt/backups -name 'snoozolene-*.zip' -mtime +30 -delete
```

Alternative sans API : copier directement le dossier `data/backups/` de l'hôte
(rsync, sauvegarde Proxmox du LXC, etc.). La sauvegarde native Proxmox
(vzdump) du conteneur LXC entier est aussi une excellente ceinture-bretelles.

## 3. Restaurer

- **Via l'admin** : Admin → Maison → 💾 Importer une sauvegarde (.zip) —
  remplace la base et les médias, l'écran se rafraîchit tout seul.
- **À la main** (machine neuve) : `git clone` + `docker compose up -d`, puis
  importer le ZIP via l'admin. C'est tout — aucune autre donnée n'existe hors
  de `data/`.

**Testez une restauration une fois** (sur une instance jetable) : une
sauvegarde jamais restaurée n'est pas une sauvegarde.
