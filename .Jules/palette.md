## 2024-05-15 - Explicit Labels Over Placeholders
**Learning:** Found instances where forms (like the Create New Board modal) relied entirely on `placeholder` attributes instead of `<label>` tags. Placeholders disappear when users start typing and are not always announced correctly by screen readers, making forms less accessible and harder to use.
**Action:** Always pair form controls (`Input`, `Textarea`, etc.) with explicit `<label>` tags linked via `id` and `htmlFor`, even when using placeholders.
