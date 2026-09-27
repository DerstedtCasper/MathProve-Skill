# Upstream provenance and notices

## MathProve-Skill selected modified module

`skill/runtime/proof_factory_v8.py` is based on `e4aaf6abec8c05bc5186d635b06b56152442380b` / Git blob `6f362d40efd0cd2a183f2ceb70889b84d46f7f97`; the source was reconstructed from connector output and byte-checked against that blob before editing. The original project license follows; retain the original repository LICENSE when merging.

MIT License

Copyright (c) 2026 MathProve Contributors

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
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

## Separate CoMath patch

`review/patches/comath-statement-signature.patch` targets CoMath `e8e0182823b383cb228802c4d70f3309bf0a698c`, original `services/comathd/src/proof-kernel/lean/statement-signature.ts`, Git blob `7d5dab316a75180649016872f724a6718e618e70`. CoMath's package declares `PolyForm-Noncommercial-1.0.0`. This separate patch does not relicense CoMath or import its daemon into the MIT portable controller. Keep the upstream repository's own notices and license when applying it. The prompt supplements are newly authored method text with source-bound registry metadata, not copied CoMath runtime implementations.
