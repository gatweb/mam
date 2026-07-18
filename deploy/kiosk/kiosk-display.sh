#!/bin/bash
# Snoozolène — configuration de l'écran du kiosque avant le lancement de
# Chromium : le GRAND ÉCRAN externe devient l'écran principal et l'écran
# interne du laptop est éteint (sinon GNOME y envoie les fenêtres plein
# écran et le grand écran reste sur un bureau vide).
#
# Appelé automatiquement par snoozolene-kiosk.service (ExecStartPre).
# Variables d'environnement :
#   KIOSK_KEEP_INTERNAL=1   garder l'écran interne allumé (mode étendu)
set -u

export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"

# Attendre que le serveur X réponde (le service part tôt dans la session)
for _ in $(seq 1 30); do
    xrandr --query >/dev/null 2>&1 && break
    sleep 1
done

# Panneau interne (eDP/LVDS) vs sortie externe (HDMI/DP/VGA…)
INTERNAL="$(xrandr --query | awk '/ connected/{print $1}' | grep -E '^(eDP|LVDS)' | head -1)"
EXTERNAL="$(xrandr --query | awk '/ connected/{print $1}' | grep -vE '^(eDP|LVDS)' | head -1)"

if [ -z "$EXTERNAL" ]; then
    echo "[kiosk] pas d'écran externe détecté — configuration inchangée"
    exit 0
fi

echo "[kiosk] écran externe $EXTERNAL → principal"
ARGS="--output $EXTERNAL --primary --auto"
if [ -n "$INTERNAL" ] && [ "${KIOSK_KEEP_INTERNAL:-0}" != "1" ]; then
    echo "[kiosk] écran interne $INTERNAL → éteint"
    ARGS="$ARGS --output $INTERNAL --off"
fi
xrandr $ARGS

# Jamais de veille ni d'écran noir : un kiosque éteint ressemble à une panne.
# (La page acquiert aussi un wake lock dans Chrome — ceinture + bretelles.)
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true
gsettings set org.gnome.desktop.session idle-delay 0 2>/dev/null || true
