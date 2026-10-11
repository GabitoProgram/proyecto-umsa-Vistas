libfprint-2.so.2.0.0 — bundled copy of libfprint-2
==================================================

Source:    Debian 13 (trixie) package libfprint-2-2
           (https://packages.debian.org/trixie/libfprint-2-2)
Version:   1.94.9-1
License:   GNU LGPL-2.1-or-later
           (https://www.gnu.org/licenses/lgpl-2.1.html)
Upstream:  https://fprint.freedesktop.org/

This library is loaded dynamically by the application
(desktop/biometria/libfprint_backend.py). No part of the
application is statically linked against it; you may replace
this copy with your system's libfprint-2.so.2 if preferred
(the loader tries the system library first).

It enables support for fingerprint readers compatible with
libfprint, including the DigitalPersona U.are.U 4000/4000B/4500
(USB 05ba:0007/0008/000a).

Its runtime dependencies (libglib-2.0, libgusb, libgio,
libpixman, libcrypto, libgudev) are provided by the system.
