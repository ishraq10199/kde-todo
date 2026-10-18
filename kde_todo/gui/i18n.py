"""Replacement for KLocalizedContext, since KI18n has no Python bindings on Fedora.

Kirigami Addons calls i18nc(), i18nd() and i18ndc() from QML. These only fill in
%1, %2, ... and don't translate.
"""

import re

from PySide6.QtCore import QObject, Slot


def _fill(text, args):
    return re.sub(r"%(\d)", lambda m: str(args[int(m[1]) - 1]) if int(m[1]) <= len(args) else m[0], text)


def _overloads(fixed):
    """Slot overloads: `fixed` string params followed by 0-3 extra args."""
    def wrap(fn):
        for extra in range(3, -1, -1):
            fn = Slot(*[str] * fixed, *["QVariant"] * extra, result=str)(fn)
        return fn
    return wrap


class LocalizedContext(QObject):
    @_overloads(2)
    def i18nc(self, context, text, *args): return _fill(text, args)

    @_overloads(2)
    def i18nd(self, domain, text, *args): return _fill(text, args)

    @_overloads(3)
    def i18ndc(self, domain, context, text, *args): return _fill(text, args)
