# kde-todo

Time-blocked daily todos for KDE Plasma, made for personal use only.

## Setup (fresh Fedora KDE)

<!-- markdownlint-disable MD013 -->

```sh
./install-prerequisites.sh   # installs the Fedora packages below (asks first) and the bubble font
./install.sh                 # adds ~/.local/bin/kde-todo, app-menu entry, autostart (--no-autostart to skip)
```

<!-- markdownlint-enable MD013 -->

The packages, if you'd rather install them yourself:

<!-- markdownlint-disable MD013 -->

```sh
sudo dnf install python3-pyside6 kf6-kirigami kf6-kirigami-addons kf6-qqc2-desktop-style \
    python3-kf6-knotifications python3-kf6-kstatusnotifieritem \
    python3-typer python3-rich python3-pydantic python3-filelock python3-platformdirs python3-dateparser
```

<!-- markdownlint-enable MD013 -->

Don't install PySide6 with pip; it can't load the system's Kirigami.

The mascot's speech bubble uses the [Departure Mono](https://departuremono.com)
font. A copy (v1.500, SIL Open Font License) is in `kde_todo/data/fonts/`, and
`install-prerequisites.sh` installs it for your user if it isn't installed
already.

## Run

<!-- markdownlint-disable MD013 -->

```sh
kde-todo gui            # open the app (it then lives in the tray)
kde-todo --help         # CLI
python3 -m unittest     # tests
```

<!-- markdownlint-enable MD013 -->

Records live in `~/.local/share/kde-todo/` (override with `KDE_TODO_DATA_DIR`).

## Uninstall

<!-- markdownlint-disable MD013 -->

```sh
./uninstall.sh                 # removes the command, app-menu entry, autostart and notification config
./uninstall.sh --remove-data   # also deletes your records (asks you to type "delete" first)
```

<!-- markdownlint-enable MD013 -->

Prerequisites (the Fedora packages and the Departure Mono font) are left
installed.

## LLM Usage Disclosure

> [!NOTE]
> This project was made with assistance from an LLM, for personal use.

## License

MIT, see [LICENSE](LICENSE). The bundled Departure Mono font is under the SIL
Open Font License, see
[kde_todo/data/fonts/LICENSE](kde_todo/data/fonts/LICENSE).
