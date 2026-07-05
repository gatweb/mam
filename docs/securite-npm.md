# Sécuriser l'accès distant avec Nginx Proxy Manager (NPM)

Objectif : protéger le dashboard exposé sur Internet **sans rien changer pour
la personne accompagnée**, qui utilise l'écran en local (kiosque sur
`http://IP-LOCALE:3000/display`, sans passer par le proxy).

La solution la plus simple et robuste : une **Access List** NPM (Basic Auth)
appliquée uniquement au Proxy Host public. L'accès local direct par IP ne
passe pas par NPM → **zéro impact sur l'écran kiosque**.

## 1. Créer l'Access List

Dans NPM → **Access Lists** → **Add Access List** :

- **Name** : `snoozolene-externe`
- Onglet **Details** :
  - **Satisfy Any** : ✅ **activé** (important — voir étape Autorisations)
- Onglet **Authorization** : ajouter un utilisateur
  - Username : `votre-login` / Password : *un mot de passe long et unique*
- Onglet **Access** : ajouter les règles
  - **Allow** : `192.168.0.0/24` *(votre réseau local — adaptez au vôtre)*
  - **Deny** : `all`

Avec *Satisfy Any*, une requête est acceptée si **l'une** des conditions est
remplie : venir du réseau local **ou** connaître le login/mot de passe.
Résultat :

| Accès | Effet |
|---|---|
| Écran kiosque (IP locale directe, sans NPM) | inchangé — ne voit jamais NPM |
| Vous, chez vous, via le domaine | pas de mot de passe (IP locale) |
| Vous, en vacances, via le domaine | login/mot de passe demandé **une fois** (le navigateur le retient) |
| N'importe qui d'autre sur Internet | 401 — bloqué |

## 2. Appliquer au Proxy Host

NPM → **Hosts → Proxy Hosts** → éditez le host public du dashboard →
onglet **Details** → **Access List** : sélectionnez `snoozolene-externe` → Save.

Vérifiez aussi sur ce host :
- **Websockets Support** : ✅ activé (obligatoire — le dashboard utilise `/ws`)
- **Block Common Exploits** : ✅ activé
- **SSL** : Force SSL + HTTP/2 activés

## 3. Si vous avez une IP fixe ou un VPN (option renforcée)

Si votre connexion en déplacement a une IP fixe (ou si vous passez par un VPN
type WireGuard/Tailscale vers la maison) :

- ajoutez `Allow <votre-ip-fixe>` dans l'Access List, ou
- **mieux** : supprimez carrément le Proxy Host public et accédez au dashboard
  via le VPN comme si vous étiez en local. C'est la solution la plus sûre :
  plus rien n'est exposé sur Internet.

## 4. Tester (à faire avant de partir !)

1. Depuis le réseau local : `https://votre-domaine.tld/admin` → doit s'ouvrir sans mot de passe.
2. Depuis la 4G du téléphone (Wi-Fi coupé) : même URL → doit demander le login.
3. Mauvais mot de passe → 401.
4. L'écran kiosque local : toujours fonctionnel, rien à faire.
5. Envoyez un message depuis l'admin en 4G → il doit apparaître sur l'écran
   (vérifie que les websockets passent avec l'Access List).

## Limites connues

- Basic Auth protège l'admin et l'API. Les notifications ntfy et les appels
  Jitsi ne passent pas par NPM et ne sont pas affectés.
- Si un jour vous partagez l'admin avec d'autres aidants, créez un utilisateur
  par personne dans l'Access List (révocable individuellement).
