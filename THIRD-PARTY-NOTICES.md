# Third-Party Notices

A-Sunday Conductor uses the following third-party open-source software.
This file is bundled with every distribution of the application.

## Serena — semantic code engine

- Project: https://github.com/oraios/serena
- License: MIT (full text below)
- Role: Serena is used as the internal semantic code engine behind the
  worker/connector instances that A-Sunday Conductor manages. All engine
  credit belongs to the Serena authors; the management UI, installer, and
  control plane are A-Sunday Conductor's own.

```
MIT License

Copyright (c) 2025 Oraios AI

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Libraries bundled inside the executables

The frozen Portable/Setup builds additionally embed these Python packages:

### Pillow — image processing (logo/portrait assets)

- Project: https://github.com/python-pillow/Pillow
- License: HPND / MIT-CMU (full text: https://raw.githubusercontent.com/python-pillow/Pillow/main/LICENSE)
- Role: loading and resizing the Sunday Family portrait and QR images.

### ModernGL — OpenGL wrapper (optional GPU logo renderer)

- Project: https://github.com/moderngl/moderngl
- License: MIT (full text: https://raw.githubusercontent.com/moderngl/moderngl/master/LICENSE)
- Role: GPU particle rendering for the header portrait; automatic Canvas fallback when unavailable.

### pyopengltk + PyOpenGL — Tk/OpenGL bridge

- Projects: https://github.com/jonwright/opengltk · https://github.com/mcfletch/pyopengl
- Licenses: MIT (opengltk) · MIT (PyOpenGL)
- Role: hosting the OpenGL logo inside the Tk window (Windows).

### PyInstaller — build tooling (not embedded at runtime)

- Project: https://github.com/pyinstaller/pyinstaller
- License: GPL with bootloader exception (full text: https://raw.githubusercontent.com/pyinstaller/pyinstaller/develop/COPYING.txt)
- Role: builds the Windows executables; not distributed inside them beyond its bootloader, per the exception.
