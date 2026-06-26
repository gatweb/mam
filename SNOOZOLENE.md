# Snoozolène — Dossier de conception fusionné

> *"Maman, tu es chez Gaëtan. Tu es en sécurité. Aujourd'hui, tu n'as rien à préparer."*
>
> Si Snoozolène affiche cela clairement, sans bug, sans abonnement, et que l'aidant peut le modifier
> en 10 secondes depuis son téléphone — le projet est déjà extrêmement utile.

---

## Ce qu'est Snoozolène

Un **écran de repères familiaux**, toujours visible, piloté à distance par les aidants,
local-first, open source, conçu pour les personnes désorientées (Alzheimer, démence).

**Ce que ce n'est pas :**
- Pas un dispositif médical
- Pas un chatbot libre qui invente des réponses
- Pas un système de surveillance totale
- Pas une usine domotique

**Principe central :** la personne malade ne doit rien apprendre. Elle lève les yeux, elle lit, elle est rassurée.

---

## Pourquoi ce projet a sa place

Les solutions existantes (RecallCue, Calendar Clock, Idem, Memoryboard, GrandPad…) proposent
de bonnes idées mais **aucune ne réunit** :

- (a) Gratuit + open source
- (b) Tout-en-un : orientation + agenda + photos + vidéo + sécurité
- (c) Tourne sur vieux PC / mini-PC / NUC
- (d) Entièrement local, sans cloud obligatoire, respectueux de la vie privée
- (e) Personnalisation profonde des messages émotionnels

C'est le créneau de Snoozolène.

---

## Les 5 piliers de l'écran

1. **Où suis-je ?** — "Tu es chez Gaëtan, ton fils."
2. **Quel jour et quelle heure ?** — Date complète, heure, moment de la journée
3. **Que se passe-t-il aujourd'hui ?** — Agenda narratif, pas une liste froide
4. **Qui est avec moi / qui vient ?** — Photos avec prénoms et lien familial
5. **Tout va bien, je suis en sécurité.** — Message rassurant permanent

---

## UX : règles absolues pour Alzheimer

### Ce qu'on affiche

```
VENDREDI 26 JUIN 2026
10 h 15 — MATIN

Tu es chez Gaëtan, ton fils.
Tu es en sécurité.

Aujourd'hui :
Tu restes à la maison.
Le kiné vient à 14 h.
Gaëtan rentre vers 18 h.

Photo : Gaëtan — ton fils
```

### Règles typographiques
- Police très grande (48–72 px minimum), sans-serif (Inter, Roboto)
- Contraste fort (fond sombre, texte blanc/jaune)
- Pas d'abréviations : "vendredi" pas "ven.", "après-midi" pas "PM"
- Date complète : "vendredi 26 juin 2026"
- Pas de menus, pas d'icônes seules, pas d'animations rapides
- Les zones restent toujours au même endroit (stabilité visuelle)

### Ton des messages

| À éviter | À préférer |
|---|---|
| "Tu as oublié…" | "Tu es chez Gaëtan." |
| "Je te l'ai déjà dit…" | "Tu es en sécurité." |
| "Tu dois…" | "On s'occupe de toi." |
| "Attention !" | "Tu n'as rien à préparer." |

---

## Modes d'affichage

### Mode matin
```
Bonjour.
Nous sommes vendredi matin.
Tu es chez Gaëtan.
Le petit-déjeuner est prêt dans la cuisine.
```

### Mode après-midi
```
C'est l'après-midi.
Le kiné vient à 14 h.
Après, tu pourras te reposer.
```

### Mode soir / sundowning (17h–21h)
Couleurs plus chaudes, moins d'informations, photos familières, message très rassurant :
```
Bonsoir.
La journée est terminée.
Tu es chez Gaëtan.
Tout est fermé, tout va bien.
Tu peux te reposer.
```

### Mode nuit (critique pour éviter les errances nocturnes)
Fond très sombre, texte épuré :
```
IL EST NUIT — 3 h 12
Nous sommes dans la nuit de vendredi à samedi.
Tout va bien.
Tu es chez Gaëtan.
Tu peux te recoucher.
```

---

## Fonctionnalités clés

### A. Agenda narratif (pas un calendrier froid)
L'aidant saisit "Kiné 14h", la personne voit selon l'heure :
- Le matin → "Cet après-midi, le kiné vient"
- À 13h45 → "Le kiné arrive bientôt"
- Après → "Le kiné est passé. Tout va bien."

Chaque événement a : titre, heure, qui accompagne, message rassurant avant/pendant/après.

### B. Cartes de réassurance Q/R
Réponses personnalisées aux questions répétées, défilant lentement (toutes les 2–5 min) :

- "Est-ce que je rentre chez moi ?" → "Tu es chez Gaëtan pour être accompagnée. Tu es en sécurité."
- "Quand revient ma sœur ?" → "Sophie vient dimanche après-midi."
- "Où est ma chambre ?" → "Ta chambre est la deuxième porte à droite."
- "Pourquoi je suis ici ?" → "Tu es ici pour être entourée et rassurée. Gaëtan s'occupe de toi."

**Règle : ne jamais mentir.** Ne pas écrire "tu rentres demain" si ce n'est pas certain.

### C. Boucle d'apaisement déclenchée par récurrence
Si la même question revient (détectée par micro ou bouton aidant), l'écran rejoue automatiquement
une vidéo rassurante du proche concerné. Ex. : "quand revient ma sœur ?" → vidéo de Sophie disant
"je viens dimanche, je pense à toi".

### D. Photos des proches avec rôle familial
Pas juste une photo avec un prénom. Pour chaque proche :
- Prénom en grand
- Lien familial ("ton fils", "ta sœur")
- Phrase rassurante
- Fréquence de visite

### E. Messages vidéo courts (20–30 secondes)
Enregistrés par les proches, déclenchés automatiquement :
- Matin, après déjeuner, fin d'après-midi, coucher
- "Bonjour maman, c'est Gaëtan. Je suis au travail. Je rentre ce soir à 18h. Je t'aime."

### F. Bouton aidant "message immédiat"
Depuis son téléphone, en 5 secondes :
```
Je suis allé faire les courses.
Je reviens vers 17 h.
Tout va bien.
— Gaëtan
```
Ce message apparaît immédiatement à l'écran.

### G. Fiche papier de secours (PDF imprimable)
En cas de panne : adresse, qui habite ici, numéros d'urgence, message rassurant, photos.

---

## Architecture technique

```
Smartphone / PC aidant
        |
        | navigateur (PWA Admin)
        |
+-------v-----------------------------------------+
|  Mini-PC / vieux PC / Intel NUC  (Linux 24/7)   |
|                                                  |
|  Application Snoozolène Core (FastAPI)           |
|  - API REST + WebSocket                          |
|  - Planificateur (agenda, modes jour/nuit)       |
|  - Base SQLite                                   |
|  - Stockage médias (photos, vidéos)              |
|  - Sauvegarde automatique                        |
|                                                  |
|  Optionnel plus tard :                           |
|  - Voix (Whisper + LLM Ollama + Piper TTS)      |
|  - Capteurs (via MQTT / Home Assistant)          |
|  - Vidéo (WebRTC + coturn)                       |
+------------------^-------------------------------+
                   |
                   | WebSocket local
                   |
        TV / écran / tablette
        (Chromium kiosk, plein écran)
```

**Principes :**
- **Local-first** : tout fonctionne sans Internet (heure, messages, photos, rappels)
- **Offline-first** : si le Wi-Fi tombe, l'écran continue avec le dernier état connu
- **Découplage** : l'écran est "bête" (affichage seul), la logique est sur le hub → plusieurs écrans synchronisés (salon + chambre)
- **Cloud optionnel** : uniquement pour relier l'aidant distant (relai WebRTC chiffré, jamais stockage de données)

---

## Stack technique recommandée

| Couche | Choix | Pourquoi |
|---|---|---|
| OS | Debian / Ubuntu LTS | Stable, gratuit, vieux PC/NUC |
| Écran patient | PWA plein écran, Chromium kiosk | TV, tablette, PC — un seul code |
| Frontend | SvelteKit + TypeScript | Léger, rapide, excellent pour PWA |
| Backend | Python + FastAPI | Simple, async, WebSocket, bon écosystème |
| Base de données | SQLite (mode WAL) | Zéro administration, sauvegarde = copie d'un fichier |
| Médias | Stockage local + FFmpeg | Compression images, transcodage vidéo |
| Météo | Open-Meteo | Gratuit, sans clé API |
| Notifications aidant | ntfy ou Gotify | Auto-hébergés, open source |
| Déploiement | Docker Compose | Installation en 1 commande |
| Licence | AGPLv3 | Les forks restent open source |
| Vidéo (plus tard) | WebRTC + LiveKit + coturn | Standard ouvert, auto-décroché |
| Voix (plus tard) | Whisper.cpp + Ollama + Piper | 100% local, privé, français |
| Capteurs (plus tard) | Home Assistant + MQTT | Des centaines de capteurs compatibles |

---

## Modèle de données

```
care_recipient      → la personne accompagnée (prénom, photo, message rassurant)
household           → le domicile (nom "chez Gaëtan", adresse, photo maison)
people              → les proches (prénom, lien, photo, message, prochaine visite)
events              → agenda (titre, heure, récurrence, messages avant/pendant/après)
reminders           → rappels simples (boire, manger, médicament)
faq                 → cartes Q/R (question, réponse, photo associée, heures d'affichage)
media               → photos et vidéos
display_settings    → thème, mode nuit, luminosité
screen_status       → l'écran est-il connecté ?
audit_log           → qui a modifié quoi, quand
```

---

## Éthique, sécurité, vie privée

- Données stockées **localement par défaut**, pas de télémétrie
- Export complet des données, suppression facile
- Sauvegarde chiffrable
- Comptes aidants protégés, journal des connexions
- Pas de caméra activée sans indication visible
- **L'application ne doit pas afficher les mots "Alzheimer" ou "démence"** sur l'écran patient

### Règle IA (essentielle)
L'assistant vocal ne génère **jamais librement**. Il puise uniquement dans les Q/R validées par l'aidant (RAG).
S'il ne sait pas, il répond : *"Je ne sais pas. Je vais prévenir Gaëtan."*

---

## Feuille de route

### Phase 0 — Cadrage (1–2 semaines)
- Observer les vraies questions répétitives
- Tester les maquettes à distance de lecture réelle
- Définir les 20 messages de base
- Choisir le matériel cible

### Phase 1 — MVP local (4–6 semaines) ← **commencer ici**
- Horloge, date, moment de la journée
- "Tu es chez Gaëtan" permanent
- Photos des proches avec lien familial
- Agenda du jour (narratif)
- Cartes Q/R défilantes
- Interface aidant locale (smartphone/PC sur le même Wi-Fi)
- Mode nuit
- Mode kiosk + démarrage automatique
- Sauvegarde locale

**Pas de** : visio, IA, capteurs, cloud, reconnaissance vocale.

### Phase 2 — Aidant confortable (1–2 mois)
- Messages immédiats depuis le téléphone
- Événements récurrents
- Vidéos courtes des proches
- Mode sundowning avancé
- Export PDF fiche de secours
- Notifications aidant (ntfy)
- Multi-aidants

### Phase 3 — Accès distant optionnel (1–2 mois)
- Accès via VPN WireGuard / Tailscale
- Journal d'activité
- Statut de l'écran à distance

### Phase 4 — Communication familiale (2–3 mois)
- Messages vidéo programmés
- Appels vidéo WebRTC auto-décroché
- Contacts autorisés uniquement
- Affichage "C'est Sophie, ta sœur" pendant l'appel

### Phase 5 — Sécurité douce (3–6 mois)
- Intégration Home Assistant
- Détection non-levée
- Capteur de porte, présence, lit
- Bouton urgence
- Radar mmWave pour chute (indicatif)

### Phase 6 — Assistant vocal local (6–12 mois)
- Reconnaissance vocale locale (Whisper.cpp)
- Réponses uniquement sur base validée (RAG)
- Synthèse vocale (Piper, supporte le français)
- Journal des questions non comprises → suggestions à l'aidant

---

## MVP concret à construire maintenant

### Écran (ce que voit la personne malade)
```
VENDREDI 26 JUIN 2026
14 h 32 — APRÈS-MIDI

Tu es chez Gaëtan.
Tu es en sécurité.

Aujourd'hui :
• Le kiné vient à 14 h.
• Gaëtan rentre vers 18 h.
• Marie appellera dimanche.

[Photo de Gaëtan — ton fils]

Tout va bien. Tu dors ici cette nuit.
Ta chambre est prête.
```

### Interface aidant (depuis le téléphone)
- Modifier le message principal
- Ajouter un rendez-vous
- Ajouter une photo
- Créer une carte Q/R
- Prévisualiser l'écran
- Voir si l'écran est connecté

### Technique
- Une seule machine, pas de cloud, pas de compte externe
- Docker Compose pour l'installation
- SQLite
- Chromium en mode kiosk
- Sauvegarde exportable

---

## Exemple de configuration MVP

```yaml
personne:
  prenom: "Martine"

domicile:
  nom: "chez Gaëtan"
  ville: "Lyon"
  message: "Tu es chez Gaëtan, ton fils. Tu es en sécurité."

aidants:
  - nom: "Gaëtan"
    relation: "ton fils"
    photo: "gaetan.jpg"
    message: "Je suis dans la maison ou au travail. Je reviens toujours."

routine:
  lundi:
    matin: "Tu restes à la maison."
    apres_midi: "Promenade si tu en as envie."
  mardi:
    matin: "Tu vas au centre à 9 h 30."
    apres_midi: "Tu rentres après le goûter."

questions:
  - q: "Est-ce que je rentre chez moi ?"
    r: "Tu es chez Gaëtan pour être accompagnée. Tu es en sécurité."
  - q: "Quand revient ma sœur ?"
    r: "Sophie vient dimanche après-midi."
  - q: "Que vais-je faire aujourd'hui ?"
    r: "Aujourd'hui tu restes à la maison. Il n'y a rien à préparer."
```

---

## Vision ultime

Un **écosystème familial de réassurance**, jamais une IA qui remplace la famille.

- Multi-écrans synchronisés (salon, chambre, cuisine)
- Assistant vocal borné dans la langue maternelle
- Sécurité multi-capteurs sans caméra de surveillance
- Cercle de soin collaboratif (plusieurs proches, auxiliaires de vie)
- Journal de santé exportable pour le neurologue
- Bibliothèque communautaire de scénarios d'apaisement
- Thérapie de réminiscence : photos d'époque, musiques de jeunesse aux moments d'agitation
- Adaptation au stade de la maladie (mode léger / modéré / avancé)

---

## Recommandation médicale et humaine

> La répétition n'est pas seulement un problème de mémoire.
> C'est souvent une expression d'anxiété.
> Il faut répondre au besoin émotionnel : "Je suis en sécurité ? Quelqu'un s'occupe de moi ?"

- Ne jamais corriger ou confronter la personne à ses oublis
- Ne jamais surcharger l'écran
- Les photos et voix familières peuvent être très rassurantes
- Le soir est souvent plus difficile → mode sundowning dédié
- Les rappels de médicaments ne sont pas une preuve de prise
- Les capteurs ne remplacent pas la présence humaine
- **L'application préserve la dignité** : jamais "Alzheimer" ou "démence" à l'écran

---

*Le cœur du projet n'est pas la technologie. C'est une interface de réassurance.*
*Moins d'intelligence artificielle au départ, plus d'intelligence humaine bien affichée.*
