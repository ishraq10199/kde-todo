# kde-todo

[![License: MIT][badge-license]][license]
[![Python 3.12+][badge-python]][python]
[![KDE Plasma 6][badge-plasma]][plasma]
[![Fedora][badge-fedora]][fedora]
[![Qt 6 / PySide6][badge-qt]][pyside]
[![Kirigami][badge-kirigami]][kirigami]

Time-blocked daily todos for KDE Plasma, made for personal use only.

<!-- markdownlint-disable MD033 -->

<p align="center">
  <img src="bubble_gifs/Mochi/working_4_i-ll-guard-the-snacks-while-you-work.gif"
    alt="Mochi, the default mascot, keeping you company while you work">
  <br>
  Mochi cheers you on while you work.
</p>

<!-- markdownlint-enable MD033 -->

[badge-license]: https://img.shields.io/badge/license-MIT-blue
[badge-python]: https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white
[badge-plasma]: https://img.shields.io/badge/KDE%20Plasma-6-1D99F3?logo=kde&logoColor=white
[badge-fedora]: https://img.shields.io/badge/Fedora-supported-51A2DA?logo=fedora&logoColor=white
[badge-qt]: https://img.shields.io/badge/Qt%206-PySide6-41CD52?logo=qt&logoColor=white
[badge-kirigami]: https://img.shields.io/badge/UI-Kirigami-1D99F3?logo=kde&logoColor=white
[license]: LICENSE
[python]: https://www.python.org
[plasma]: https://kde.org/plasma-desktop
[fedora]: https://fedoraproject.org/kde
[pyside]: https://doc.qt.io/qtforpython-6
[kirigami]: https://develop.kde.org/frameworks/kirigami

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
