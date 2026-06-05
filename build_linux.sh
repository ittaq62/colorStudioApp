#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# Build du binaire Linux + integration desktop.
#
# Prerequis :
#   sudo apt install python3.12 python3-pip python3-venv libxcb-cursor0 libegl1
#   pip install -r requirements-dev.txt
#
# Usage :
#   ./build_linux.sh              # build + install local en .local
#   ./build_linux.sh --no-install # juste le build, pas d'integration desktop
# -----------------------------------------------------------------------------

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

INSTALL=true
if [ "$1" = "--no-install" ]; then
    INSTALL=false
fi

# 1) regen des icones
echo ">>> regeneration des icones SVG + app.ico + app.png..."
python3 generate_icons.py

# 2) nettoyage des builds precedents
echo ">>> nettoyage de build/ et dist/..."
rm -rf build dist

# 3) PyInstaller
echo ">>> build PyInstaller..."
python3 -m PyInstaller colorstudio.spec --clean

OUT="dist/colorstudio/colorstudio"
if [ ! -f "$OUT" ]; then
    echo ">>> ECHEC : binaire attendu introuvable a $OUT"
    exit 1
fi

SIZE_MB=$(du -m "$OUT" | cut -f1)
echo ">>> Build OK : $OUT ($SIZE_MB Mo)"

# 4) integration desktop locale (facultative)
if [ "$INSTALL" = "true" ]; then
    echo ""
    echo ">>> Integration desktop locale dans ~/.local..."
    APP_DIR="$HOME/.local/share/colorstudio"
    BIN_DIR="$HOME/.local/bin"
    ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
    DESKTOP_DIR="$HOME/.local/share/applications"

    mkdir -p "$APP_DIR" "$BIN_DIR" "$ICON_DIR" "$DESKTOP_DIR"

    # copie du bundle complet
    cp -r dist/colorstudio/* "$APP_DIR/"

    # symlink dans ~/.local/bin
    ln -sf "$APP_DIR/colorstudio" "$BIN_DIR/colorstudio"

    # icone
    cp colorstudio/icons/app.png "$ICON_DIR/colorstudio.png"

    # .desktop file (adapte le chemin Exec)
    sed "s|^Exec=.*|Exec=$BIN_DIR/colorstudio %f|" packaging/colorstudio.desktop > "$DESKTOP_DIR/colorstudio.desktop"
    chmod +x "$DESKTOP_DIR/colorstudio.desktop"

    # rafraichit la base desktop
    if command -v update-desktop-database &> /dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi

    echo ""
    echo ">>> Integration terminee."
    echo "    Binaire : $BIN_DIR/colorstudio"
    echo "    .desktop : $DESKTOP_DIR/colorstudio.desktop"
    echo "    Icone : $ICON_DIR/colorstudio.png"
    echo ""
    echo "Lancer avec :"
    echo "  colorstudio                        # depuis le shell (PATH ~/.local/bin)"
    echo "  colorstudio xml-hdr-demo.json      # avec un fichier de scene"
    echo "  ou via le menu d'applications du DE (apres une deconnexion/reconnexion)"
fi
