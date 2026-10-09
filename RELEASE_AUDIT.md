# Release v1.0.0 – License audit / Lizenzprüfung

**Status: BLOCKED / NICHT ZUR ÖFFENTLICHEN VERÖFFENTLICHUNG FREIGEGEBEN**

## Confirmed / Bestätigt

- Windows portable ZIP opens without archive corruption; NIIMBOT B1 printing and BamBuddy spool retrieval were successfully tested by the developer.
- Main executable SHA-256: `83286c082a64515a1f8c203be987bda808ab3b956bf0ec00ee83bac24fdc62b6`
- Bundled: Python 3.14 runtime, OpenSSL 3 libraries, Tcl/Tk 9 library, WinRT Bluetooth extensions, Pillow and Python dependencies.
- Existing full license files are bundled for bleak, keyring, niimbot-b1, and vendored importlib_metadata. The project MIT license is bundled.

## Still required / Noch offen

- Obtain and include the **exact license/copyright notices for the actual versions and binary distributions** of CPython 3.14, Tcl/Tk 9, OpenSSL 3, Pillow and any bundled native libraries.
- Review license notices for qrcode, requests, certifi, charset-normalizer, idna, urllib3, WinRT, jaraco, and any other bundled dependencies, including vendored components.
- Confirm which components are redistributed by the PyInstaller bundle and include all required notices; check Python/Tcl/Tk/OpenSSL and Microsoft runtime redistribution conditions.
- Rebuild release ZIP with verified notices, test on Windows, then publish `v1.0.0` with Windows 10/11 64-bit, NIIMBOT B1, tested 40 × 30 mm label size.

This checklist is not a legal opinion. Do not publish the current RC as a final public release.

Diese Checkliste ist keine Rechtsberatung. Die aktuelle RC-ZIP noch nicht als endgültiges öffentliches Release veröffentlichen.
