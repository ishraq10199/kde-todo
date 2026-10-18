#!/bin/sh
# Installs kde-todo for the current user, running from this checkout:
#   ~/.local/bin/kde-todo, an app-menu entry, and autostart (in the tray).
# Usage: ./install.sh [--no-autostart]
set -eu

here=$(cd "$(dirname "$0")" && pwd)
bin="$HOME/.local/bin/kde-todo"
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
autostart="${XDG_CONFIG_HOME:-$HOME/.config}/autostart"

mkdir -p "$(dirname "$bin")" "$apps"
cat > "$bin" <<SH
#!/bin/sh
PYTHONPATH="$here\${PYTHONPATH:+:\$PYTHONPATH}" exec /usr/bin/python3 -m kde_todo "\$@"
SH
chmod +x "$bin"

sed "s|^Exec=.*|Exec=$bin gui|" "$here/kde_todo/data/org.kde.kdetodo.desktop" > "$apps/org.kde.kdetodo.desktop"

if [ "${1:-}" != "--no-autostart" ]; then
    mkdir -p "$autostart"
    sed "s|^Exec=.*|Exec=$bin gui --hidden|" "$here/kde_todo/data/org.kde.kdetodo.desktop" > "$autostart/org.kde.kdetodo.desktop"
fi

echo "Installed: $bin"
echo "Run 'kde-todo gui' or find kde-todo in the app menu."
