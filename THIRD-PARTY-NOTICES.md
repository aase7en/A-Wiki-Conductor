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

### TkinterWeb + Tkhtml — embedded Guide renderer

- TkinterWeb 4.25.3 — https://github.com/Andereoo/TkinterWeb
- tkinterweb-tkhtml 2.1.1
- tkinterweb-tkhtml-extras 1.3.1
- License: MIT
- Role: local/offline HTML/CSS rendering for the in-app beginner Guide. JavaScript and remote images/resources are disabled by A-Sunday Conductor.

MIT License

Copyright (c) 2021-2025 Andrew Clarke
Copyright (c) 2025 Andrew Clarke (tkhtml runtime packages)

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

### Python-Markdown — Markdown to HTML transformation

- Project: https://github.com/Python-Markdown/markdown
- Version tested for v0.7.0: 3.10.3
- License: BSD-3-Clause
- Role: transforms the existing Markdown user-guide SSoT into bounded local HTML sections in memory.

BSD 3-Clause License

Copyright 2007, 2008 The Python Markdown Project (v. 1.7 and later)
Copyright 2004, 2005, 2006 Yuri Takhteyev (v. 0.2-1.6b)
Copyright 2004 Manfred Stienstra (the original version)

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
