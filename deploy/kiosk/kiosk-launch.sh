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
#   CHROMIUM_BIN  binaire du navigateur    (défaut : auto-détecté)
set -u

SNOOZ_URL="${SNOOZ_URL:-http://192.168.0.50:3000/display}"

# Profil DÉDIÉ au kiosque. Indispensable : sans lui, si un autre Chromium
# tourne déjà (navigateur de la session, ancien autostart…), le nôtre lui
# délègue l'URL et se termine aussitôt avec code 0 → systemd le relance en
# boucle (incident du 17 juillet 2026 : service « Succeeded » après 9 s).
PROFILE_DIR="$HOME/.config/snoozolene-kiosk"

# Auto-détection du binaire (Zorin/Ubuntu : chromium-browser, snap/Arch :
# chromium, sinon Chrome).
if [ -z "${CHROMIUM_BIN:-}" ]; then
    for bin in chromium chromium-browser google-chrome google-chrome-stable; do
        command -v "$bin" > /dev/null && CHROMIUM_BIN="$bin" && break
    done
fi
if [ -z "${CHROMIUM_BIN:-}" ]; then
    echo "[kiosk] ERREUR : aucun navigateur Chromium/Chrome trouvé" >&2
    exit 1
fi

# 1. Attendre la session graphique (X11). L'ordonnancement systemd ne suffit
#    pas sur tous les environnements de bureau — on vérifie nous-mêmes.
#    (Wayland : pas de xset — on saute l'attente si WAYLAND_DISPLAY est défini.)
if [ -z "${WAYLAND_DISPLAY:-}" ]; then
    echo "[kiosk] attente de la session graphique (DISPLAY=${DISPLAY:-:0}) …"
    until xset q > /dev/null 2>&1; do sleep 2; done
fi

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
#                                        à un autre Chromium déjà ouvert
#   --kiosk                              plein écran, pas de barre d'adresse
#   --incognito                          pas de restauration de session → pas de
#                                        popup « Chrome ne s'est pas fermé
#                                        correctement » après un reboot brutal
#   --no-first-run                       pas d'assistant de bienvenue sur ce
#                                        profil neuf
#   --noerrdialogs --disable-infobars    aucune bulle d'erreur par-dessus l'écran
#   --disable-session-crashed-bubble     ceinture + bretelles avec --incognito
#   --password-store=basic               ne déclenche JAMAIS le trousseau de
#                                        clés (le « mot de passe au démarrage »)
#   --autoplay-policy=no-user-gesture-required   le réveil et la radio peuvent
#                                        sonner sans toucher l'écran
#   --use-fake-ui-for-media-stream       accepte caméra/micro automatiquement
#                                        (appels vidéo sans popup)
exec "$CHROMIUM_BIN" \
    --user-data-dir="$PROFILE_DIR" \
    --kiosk \
    --incognito \
    --no-first-run \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --password-store=basic \
    --autoplay-policy=no-user-gesture-required \
    --use-fake-ui-for-media-stream \
    "$SNOOZ_URL"
