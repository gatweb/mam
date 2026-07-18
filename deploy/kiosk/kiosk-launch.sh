#!/bin/bash
# Snoozolène — lancement du kiosque Chromium.
#
# Pourquoi ce script existe (incident de juillet 2026) :
# au redémarrage nocturne du PC, Chromium partait AVANT le réseau et/ou
# avant que le serveur ne soit prêt → page d'erreur figée (« écran blanc »),
# car un kiosque ne réessaie jamais de lui-même. Ici, on attend d'abord que
# la session graphique ET le serveur soient prêts, et on ne lance le
# navigateur qu'ensuite.
#
# L'application elle-même est aussi résiliente (écran « Je me prépare… »
# + nouvelle tentative en boucle) : ces deux couches se complètent.
#
# Variables d'environnement :
#   SNOOZ_URL     URL de l'écran patient   (défaut : http://192.168.0.50:3000/display)
#   CHROMIUM_BIN  binaire du navigateur    (défaut : auto-détecté ; Chrome .deb
#                 recommandé — le snap chromium casse WebRTC, voir README)
set -u

SNOOZ_URL="${SNOOZ_URL:-http://192.168.0.50:3000/display}"

# Profil DÉDIÉ au kiosque. Indispensable : sans lui, si un autre Chrome/Chromium
# tourne déjà (navigateur de la session, ancien autostart…), le nôtre lui
# délègue l'URL et se termine aussitôt avec code 0 → systemd le relance en
# boucle (incident du 17 juillet 2026 : service « Succeeded » après 9 s).
PROFILE_DIR="$HOME/.config/snoozolene-kiosk"

# Origine (protocole://hôte:port) de l'écran. INDISPENSABLE en HTTP local :
# Chrome exige un contexte sécurisé pour getUserMedia, y compris dans une
# iframe HTTPS si la page mère est en HTTP — sans ce flag, Jitsi est redirigé
# vers sa page « WebRTC is not available in your browser » et les appels
# vidéo ne peuvent JAMAIS aboutir (cause racine de l'incident de juillet 2026,
# reproduite et validée le 18 juillet). Inoffensif si l'URL est déjà en HTTPS.
SNOOZ_ORIGIN="$(printf '%s' "$SNOOZ_URL" | sed 's|\(https\{0,1\}://[^/]*\).*|\1|')"

# Auto-détection du binaire. Ordre : Chrome .deb d'abord (WebRTC complet,
# pas de confinement snap), puis chromium-browser/chromium.
if [ -z "${CHROMIUM_BIN:-}" ]; then
    for bin in google-chrome-stable google-chrome chromium-browser chromium; do
        command -v "$bin" > /dev/null && CHROMIUM_BIN="$bin" && break
    done
fi
if [ -z "${CHROMIUM_BIN:-}" ]; then
    echo "[kiosk] ERREUR : aucun navigateur Chrome/Chromium trouvé" >&2
    exit 1
fi

# 1. Attendre la session graphique : d'abord X (xset), puis le gestionnaire
#    de fenêtres. Si Chromium se lance avant gnome-shell, la fenêtre kiosque
#    n'est pas gérée et reste GRISE figée (constaté sur le terrain : 1er
#    lancement gris, le 2e — après redémarrage du service — parfait).
#    (Wayland : pas de xset — on saute si WAYLAND_DISPLAY est défini.)
# Attente BORNÉE (2 min max) et seulement si xset existe : si l'outil manque
# ou que X ne vient pas, on tente quand même — l'app a son propre écran
# d'attente, et systemd relancera. Un kiosque ne doit jamais bloquer sans fin.
if [ -z "${WAYLAND_DISPLAY:-}" ] && command -v xset > /dev/null; then
    echo "[kiosk] attente de la session graphique (DISPLAY=${DISPLAY:-:0}) …"
    for _ in $(seq 1 60); do
        xset q > /dev/null 2>&1 && break
        sleep 2
    done
fi
echo "[kiosk] attente du gestionnaire de fenêtres…"
for _ in $(seq 1 60); do
    if pgrep -x gnome-shell >/dev/null 2>&1 || pgrep -x mutter >/dev/null 2>&1 \
       || pgrep -x kwin_x11 >/dev/null 2>&1 || pgrep -x openbox >/dev/null 2>&1 \
       || pgrep -x xfwm4 >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
sleep 3   # laisser le compositeur se stabiliser

# 2. Attendre que le serveur Snoozolène réponde.
echo "[kiosk] attente du serveur sur $SNOOZ_URL …"
until curl -sf -o /dev/null --max-time 3 "$SNOOZ_URL"; do
    sleep 2
done

# 3. Fermer une éventuelle instance kiosque précédente (sinon : délégation
#    → sortie immédiate → boucle systemd, cf. commentaire PROFILE_DIR).
if pkill -f -- "--user-data-dir=$PROFILE_DIR" 2> /dev/null; then
    echo "[kiosk] ancienne instance kiosque fermée"
    sleep 2
fi

echo "[kiosk] lancement de $CHROMIUM_BIN"

# Flags « zéro manipulation » — chacun répond à un incident constaté :
#   --user-data-dir                      profil séparé → jamais de délégation
#                                        à un autre Chrome/Chromium déjà ouvert
#   --kiosk                              plein écran, pas de barre d'adresse
#   --incognito                          pas de restauration de session → pas de
#                                        popup « Chrome ne s'est pas fermé
#                                        correctement » après un reboot brutal
#   --no-first-run --no-default-browser-check   pas d'assistant de premier
#                                        démarrage ni « navigateur par défaut ? »
#                                        (indispensable avec un Chrome .deb neuf)
#   --noerrdialogs --disable-infobars    aucune bulle d'erreur par-dessus l'écran
#   --disable-session-crashed-bubble     ceinture + bretelles avec --incognito
#   --password-store=basic               ne déclenche JAMAIS le trousseau de
#                                        clés (le « mot de passe au démarrage »)
#   --autoplay-policy=no-user-gesture-required   le réveil et la radio peuvent
#                                        sonner sans toucher l'écran
#   --use-fake-ui-for-media-stream       accepte caméra/micro automatiquement
#                                        (appels vidéo sans popup)
#   --unsafely-treat-insecure-origin-as-secure   rend getUserMedia (donc les
#                                        appels Jitsi) possible bien que la
#                                        page mère soit en HTTP local
exec "$CHROMIUM_BIN" \
    --user-data-dir="$PROFILE_DIR" \
    --kiosk \
    --incognito \
    --no-first-run \
    --no-default-browser-check \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --password-store=basic \
    --autoplay-policy=no-user-gesture-required \
    --use-fake-ui-for-media-stream \
    --unsafely-treat-insecure-origin-as-secure="$SNOOZ_ORIGIN" \
    "$SNOOZ_URL"
