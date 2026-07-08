import { ComponentChildren } from 'preact';

export function SectionCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ComponentChildren }) {
  return (
    <sl-card class="section-card">
      <div slot="header" class="section-header">
        <div>
          <strong>{title}</strong>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      </div>
      {children}
    </sl-card>
  );
}
