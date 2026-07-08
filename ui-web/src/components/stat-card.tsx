export function StatCard({ label, value, hint }: { label: string; value: string | number; hint: string }) {
  return (
    <sl-card class="stat-card">
      <p class="stat-label">{label}</p>
      <strong class="stat-value">{value}</strong>
      <p class="stat-hint">{hint}</p>
    </sl-card>
  );
}
