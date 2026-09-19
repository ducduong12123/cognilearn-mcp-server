# Third-party notices

## LangExtract (`src/langextract/`)

`src/langextract/` is a vendored copy of [LangExtract](https://github.com/google/langextract),
Copyright 2025 Google LLC, licensed under the Apache License, Version 2.0. It is used only by the
question-bank tagging script (`src/script/tag_questions.py`) to build structured extraction
prompts. The original license headers are preserved in each file; the full license text is at
<http://www.apache.org/licenses/LICENSE-2.0>.

No modifications to the library are intended; it will be replaced by the `langextract` package
from PyPI.
