# Détection de chute (Aqara FP2) → appel vidéo automatique

Quand une chute est détectée, Snoozolène peut :
1. ouvrir **automatiquement un appel vidéo plein écran** sur l'écran de la
   personne (elle n'a rien à faire — vous la voyez et lui parlez) ;
2. envoyer une **notification ntfy urgente** sur votre téléphone — un appui
   sur la notification vous fait rejoindre l'appel.

## 1. Côté Snoozolène

1. **Admin → Alertes → 🚨 Alerte chute** → « Générer » → copiez le jeton.
2. Testez avec le bouton « 🚨 Tester l'alerte » : l'écran doit basculer en
   appel et votre téléphone doit sonner (priorité urgente ntfy).

L'endpoint appelé est :

```
POST http://IP-SNOOZOLENE:8000/api/alert/fall
Content-Type: application/json

{"token": "LE-JETON", "source": "salle de bain"}
```

## 2. Côté Home Assistant

### ⚠️ D'abord, vérifier ce que votre FP2 sait faire

Le FP2 a **deux modes exclusifs**, configurés dans l'app Aqara :

| Mode | Ce qu'il expose | Peut détecter une chute ? |
|---|---|---|
| **Présence par zones** (montage mural) | capteurs de présence par zone | ❌ non |
| **Détection de chute** (montage **au plafond**, 2,5–3 m) | capteur « fall detection » | ✅ oui |

Un même FP2 **ne fait pas les deux à la fois**. Si le vôtre est monté au mur
pour la présence salle de bain, il faut soit un **second FP2 au plafond** en
mode chute, soit basculer celui-ci (et perdre l'affichage libre/occupée).

La configuration du mode se fait **uniquement dans l'app Aqara** ; l'entité
apparaît ensuite dans HA via l'intégration HomeKit Controller (ou Matter),
généralement comme `binary_sensor.*fall*` ou un capteur d'« occupation »
dédié à la chute. Cherchez « fall » dans **Outils de dev → États**.

### Automatisation (configuration.yaml + UI)

`configuration.yaml` :

```yaml
rest_command:
  snoozolene_alerte_chute:
    url: "http://IP-SNOOZOLENE:8000/api/alert/fall"
    method: POST
    content_type: "application/json"
    payload: >-
      {"token": "LE-JETON", "source": "salle de bain"}
```

Automatisation (UI ou YAML) :

```yaml
alias: "Chute salle de bain → appel Snoozolène"
triggers:
  - trigger: state
    entity_id: binary_sensor.fp2_salle_de_bain_fall  # ← adaptez à votre entité
    to: "on"
    for: "00:00:05"        # 5 s de confirmation pour limiter les faux positifs
actions:
  - action: rest_command.snoozolene_alerte_chute
mode: single
```

Redémarrez HA, provoquez l'état (Outils de dev → États → forcez le capteur
à `on`) et vérifiez que l'écran bascule en appel.

## 3. Ce qui reste à faire si le FP2 n'expose pas la chute

Si après vérification votre FP2 (mode/montage actuel) n'expose pas d'entité
de chute dans HA, il manque uniquement le **déclencheur physique**. Tout le
reste (endpoint, jeton, appel auto, notification) est en place et testable
avec le bouton « Tester l'alerte ». Options au retour de vacances :

1. Second FP2 au plafond de la salle de bain en mode chute (~60 €) — la
   solution propre.
2. Bouton d'appel d'urgence Zigbee (ex : Aqara Wireless Mini Switch) collé
   au mur à hauteur de main : automatisation identique, `trigger` sur le
   bouton. Très fiable, utilisable dès maintenant.
3. Heuristique « présence anormalement longue » : si la salle de bain reste
   `occupée` plus de N minutes, envoyer l'alerte. Faux positifs possibles,
   mais filet de sécurité utile — c'est la même automatisation avec
   `for: "00:30:00"` sur le capteur de présence existant.

L'option 3 est activable dès aujourd'hui sans matériel neuf, en complément.
