import { ComponentChildren } from 'preact';

export function ResourceState({ loading, error, empty, children }: { loading: boolean; error: string | null; empty?: boolean; children: ComponentChildren }) {
  if (loading) {
    return (
      <div class="resource-state">
        <sl-spinner></sl-spinner>
        <span>Loading data…</span>
      </div>
    );
  }

  if (error) {
    return <sl-alert variant="danger" open>{error}</sl-alert>;
  }

  if (empty) {
    return <sl-alert variant="primary" open>No records yet.</sl-alert>;
  }

  return <>{children}</>;
}
