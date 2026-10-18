#!/bin/sh
# Installs what kde-todo needs on Fedora KDE.
# (pip's PySide6 can't load the system's Kirigami).
# Usage: ./install-prerequisites.sh
set -eu

PACKAGES="
    python3-pyside6
    kf6-kirigami
    kf6-kirigami-addons
    kf6-qqc2-desktop-style
    python3-kf6-knotifications
    python3-kf6-kstatusnotifieritem
    python3-typer
    python3-rich
    python3-pydantic
    python3-filelock
    python3-platformdirs
    python3-dateparser
"

if ! command -v dnf >/dev/null 2>&1; then
    echo "This script is for Fedora (it needs dnf). Install these packages with your package manager:" >&2
    echo $PACKAGES >&2
    exit 1
fi

# shellcheck disable=SC2086  # the list is meant to split into words
missing=$(rpm -q $PACKAGES | sed -n 's/^package \(.*\) is not installed$/\1/p')
if [ -n "$missing" ]; then
    echo "Installing:" $missing
    # shellcheck disable=SC2086
    sudo dnf install $missing
else
    echo "All packages are already installed."
fi

# The mascot's speech bubble uses Departure Mono. It isn't packaged for Fedora, so the project
# carries a copy (SIL Open Font License, see kde_todo/data/fonts/LICENSE) to install for this user.
here=$(cd "$(dirname "$0")" && pwd)
fonts="${XDG_DATA_HOME:-$HOME/.local/share}/fonts"
if fc-list : family | grep -qx "Departure Mono"; then
    echo "Departure Mono font: already installed."
else
    mkdir -p "$fonts"
    cp "$here/kde_todo/data/fonts/DepartureMono-Regular.otf" "$fonts/"
    fc-cache "$fonts"
    echo "Departure Mono font: installed to $fonts"
fi

echo "Done. Next: ./install.sh"
