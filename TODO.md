# TODO / Backlog

## À faire au retour (non traité volontairement dans cette session)

- [ ] **Cron de redémarrage automatique** de l'ordinateur kiosque + vérification
      du script de démarrage (autostart Chromium avec les bons flags — voir
      `docs/appels-video.md` pour les flags requis : `--autoplay-policy`,
      `--use-fake-ui-for-media-stream`).
- [ ] **Messages vocaux** : laisser/recevoir des messages vocaux automatiquement.
      Lien avec l'existant : le canal WebSocket (`_broadcast`) et la lecture
      audio navigateur du display (fonction `playAudio`) peuvent être réutilisés
      tels quels pour diffuser un message vocal uploadé depuis l'admin.

## Détection de chute

- [ ] Vérifier dans HA si le FP2 actuel expose une entité de chute
      (voir `docs/detection-chute.md` §2) ; sinon choisir : second FP2 plafond,
      bouton d'urgence Zigbee, ou heuristique « occupation > 30 min ».

## Avant open-source (repo public)

- [ ] Décider du sort des prénoms réels dans le seed (`backend/main.py`,
      `_seed_if_empty`) et le README — les remplacer par des prénoms fictifs ?
- [ ] L'historique git du repo privé contient le domaine personnel dans un
      message de commit — ne pas transférer cet historique tel quel au repo public.
- [ ] Restreindre CORS (`allow_origins=["*"]`) une fois l'architecture des
      origines stabilisée.
