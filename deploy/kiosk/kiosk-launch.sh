#!/bin/bash
# Snoozolène — lancement du kiosque Chromium.
#
# Pourquoi ce script existe (incident de juillet 2026) :
# au redémarrage nocturne du PC, Chromium partait AVANT le réseau et/ou
# avant que le serveur ne soit prêt → page d'erreur figée (« écran blanc »),
# car un kiosque ne réessaie jamais de lui-même. Ici, on attend d'abord que
# le serveur réponde 200, et on ne lance le navigateur qu'ensuite.
#
# L'application elle-même est aussi résiliente (écran « Je me prépare… »
# + nouvelle tentative en boucle) : ces deux couches se complètent.
#
# Variables d'environnement :
#   SNOOZ_URL     URL de l'écran patient   (défaut : http://192.168.0.50:3000/display)
#   CHROMIUM_BIN  binaire du navigateur    (défaut : chromium)
set -u

SNOOZ_URL="${SNOOZ_URL:-http://192.168.0.50:3000/display}"
CHROMIUM_BIN="${CHROMIUM_BIN:-chromium}"

echo "[kiosk] attente du serveur sur $SNOOZ_URL …"
until curl -sf -o /dev/null --max-time 3 "$SNOOZ_URL"; do
    sleep 2
done
echo "[kiosk] serveur prêt — lancement de Chromium"

# Flags « zéro manipulation » — chacun répond à un incident constaté :
#   --kiosk                              plein écran, pas de barre d'adresse
#   --incognito                          profil jetable → jamais de popup
#                                        « Chrome ne s'est pas fermé
#                                        correctement » après un reboot brutal
#   --noerrdialogs --disable-infobars    aucune bulle d'erreur par-dessus l'écran
#   --disable-session-crashed-bubble     ceinture + bretelles avec --incognito
#   --password-store=basic               ne déclenche JAMAIS le trousseau de
#                                        clés (le « mot de passe au démarrage »)
#   --autoplay-policy=no-user-gesture-required   le réveil et la radio peuvent
#                                        sonner sans toucher l'écran
#   --use-fake-ui-for-media-stream       accepte caméra/micro automatiquement
#                                        (appels vidéo sans popup)
exec "$CHROMIUM_BIN" \
    --kiosk \
    --incognito \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --password-store=basic \
    --autoplay-policy=no-user-gesture-required \
    --use-fake-ui-for-media-stream \
    "$SNOOZ_URL"
