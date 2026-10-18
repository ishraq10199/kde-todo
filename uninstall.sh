#!/bin/sh
# Removes what install.sh and the app set up for the current user: the kde-todo command, the app-menu
# entry, autostart and the notification config.
# Prerequisites (Fedora packages, the Departure Mono font) and your todo records are kept.
# Usage: ./uninstall.sh [--remove-data]   (--remove-data also deletes your records, after asking)
set -eu

data_home="${XDG_DATA_HOME:-$HOME/.local/share}"
config_home="${XDG_CONFIG_HOME:-$HOME/.config}"
records="${KDE_TODO_DATA_DIR:-$data_home/kde-todo}"
bin="$HOME/.local/bin/kde-todo"

remove() {
    if [ -e "$1" ]; then
        rm -f "$1"
        echo "Removed $1"
    fi
}

# Stop a running copy, so it doesn't keep showing in the tray.
if pgrep -f "kde_todo gui" >/dev/null 2>&1; then
    pkill -f "kde_todo gui" || true
    echo "Stopped the running kde-todo."
fi

# Only remove the command if it's the wrapper install.sh wrote.
if [ -f "$bin" ] && grep -q -- "-m kde_todo" "$bin"; then
    remove "$bin"
elif [ -e "$bin" ]; then
    echo "Left $bin alone: it isn't the kde-todo wrapper."
fi

remove "$data_home/applications/org.kde.kdetodo.desktop"
remove "$config_home/autostart/org.kde.kdetodo.desktop"
remove "$data_home/knotifications6/kde-todo.notifyrc"
remove "$config_home/kde-todo.notifyrc"  # your notification choices from System Settings, if any

if [ "${1:-}" = "--remove-data" ]; then
    if [ -d "$records" ]; then
        days=$(find "$records/days" -name '*.json' 2>/dev/null | wc -l)
        echo "This deletes all your kde-todo records ($days days, plus the stash and settings) in:"
        echo "  $records"
        printf "Type 'delete' to confirm: "
        read -r answer || answer=""
        if [ "$answer" = "delete" ]; then
            rm -rf "$records"
            echo "Removed $records"
        else
            echo "Kept your records."
        fi
    fi
elif [ -d "$records" ]; then
    echo "Kept your records in $records (run with --remove-data to delete them too)."
fi

echo "kde-todo is uninstalled. Prerequisites (Fedora packages, the Departure Mono font) were left in place."
