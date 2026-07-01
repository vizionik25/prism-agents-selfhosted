## 2025-02-12 - Delete Action UX

**Learning:** Destructive actions without confirmation or loading state feedback can cause user anxiety and accidental data loss. Immediate visual feedback (like a loading spinner and disabling the button) reassures the user that the action was registered and is being processed.

**Action:** Whenever implementing a destructive action (like delete or remove), ensure it has a confirmation step, a loading state that prevents duplicate clicks, and clear visual feedback indicating the action is in progress.

## 2024-06-21 - Agent Creator Page Form Labels
**Learning:** React requires the use of `htmlFor` instead of `for` for linking `<label>` elements to input `id`s for accessibility, and Next.js projects strongly enforce this via linting. Custom `<Label>` components need to explicitly accept and pass down the `htmlFor` prop to ensure compatibility.
**Action:** When creating or modifying forms or custom form label components, always ensure they accept `htmlFor` and that associated input components have matching `id` attributes.

## 2026-07-01 - Input Field Accessibility Without Visible Labels

**Learning:** When adding input fields that require a clean UI (such as main chat inputs or search bars) where a visible label would clutter the design, relying solely on placeholder text is insufficient for accessibility. Screen readers need a programmatic association to understand the purpose of the input.

**Action:** Always pair form controls (like `Input` or `Textarea`) with an explicit `<label>` tag using `id` and `htmlFor`. For visually clean UIs, use a visually hidden label (e.g., using Tailwind's `sr-only` class) to ensure screen reader accessibility without affecting the visual design.
