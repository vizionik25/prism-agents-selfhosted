## 2025-02-12 - Delete Action UX

**Learning:** Destructive actions without confirmation or loading state feedback can cause user anxiety and accidental data loss. Immediate visual feedback (like a loading spinner and disabling the button) reassures the user that the action was registered and is being processed.

**Action:** Whenever implementing a destructive action (like delete or remove), ensure it has a confirmation step, a loading state that prevents duplicate clicks, and clear visual feedback indicating the action is in progress.

## 2024-06-21 - Agent Creator Page Form Labels
**Learning:** React requires the use of `htmlFor` instead of `for` for linking `<label>` elements to input `id`s for accessibility, and Next.js projects strongly enforce this via linting. Custom `<Label>` components need to explicitly accept and pass down the `htmlFor` prop to ensure compatibility.
**Action:** When creating or modifying forms or custom form label components, always ensure they accept `htmlFor` and that associated input components have matching `id` attributes.

## 2025-02-12 - Accessible Chat Input Labels
**Learning:** Main chat inputs often lack an explicit visible label to maintain a clean UI, relying entirely on placeholder text, which can cause accessibility issues for screen readers. Form inputs must always have an associated label.
**Action:** When working on main search or chat inputs that do not feature visible labels, use a visually hidden `<label>` element (e.g., using Tailwind's `sr-only` class) properly linked to the input via `id` and `htmlFor` attributes to ensure full screen reader support.
