## 2025-02-12 - Delete Action UX

**Learning:** Destructive actions without confirmation or loading state feedback can cause user anxiety and accidental data loss. Immediate visual feedback (like a loading spinner and disabling the button) reassures the user that the action was registered and is being processed.

**Action:** Whenever implementing a destructive action (like delete or remove), ensure it has a confirmation step, a loading state that prevents duplicate clicks, and clear visual feedback indicating the action is in progress.
