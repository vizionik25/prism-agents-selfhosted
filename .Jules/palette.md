## 2025-02-12 - Delete Action UX

**Learning:** Destructive actions without confirmation or loading state feedback can cause user anxiety and accidental data loss. Immediate visual feedback (like a loading spinner and disabling the button) reassures the user that the action was registered and is being processed.

**Action:** Whenever implementing a destructive action (like delete or remove), ensure it has a confirmation step, a loading state that prevents duplicate clicks, and clear visual feedback indicating the action is in progress.

## 2024-06-21 - Agent Creator Page Form Labels
**Learning:** React requires the use of `htmlFor` instead of `for` for linking `<label>` elements to input `id`s for accessibility, and Next.js projects strongly enforce this via linting. Custom `<Label>` components need to explicitly accept and pass down the `htmlFor` prop to ensure compatibility.
**Action:** When creating or modifying forms or custom form label components, always ensure they accept `htmlFor` and that associated input components have matching `id` attributes.
