import { ComponentChildren } from 'preact';
import { Link, useLocation } from 'wouter-preact';
import { getRuntimeConfig } from 'src/lib/config';

const navGroups = [
  {
    label: 'Overview',
    links: [{ href: '/', label: 'Home' }],
  },
  {
    label: 'Candidate',
    links: [
      { href: '/candidate/upload', label: 'Upload CV' },
      { href: '/candidate/lookup', label: 'Candidate Lookup' },
      { href: '/jobs', label: 'Browse Jobs' },
    ],
  },
  {
    label: 'Admin',
    links: [
      { href: '/admin/jobs', label: 'Jobs' },
      { href: '/admin/raw-jobs', label: 'Raw Jobs' },
      { href: '/admin/candidates', label: 'Candidates' },
      { href: '/admin/tasks', label: 'Tasks' },
    ],
  },
];

export function AppShell({ children }: { children: ComponentChildren }) {
  const [location] = useLocation();
  const config = getRuntimeConfig();

  return (
    <div class="layout-shell">
      <aside class="sidebar-panel">
        <div class="brand-block">
          <div>
            <p class="eyebrow">Job Aggregator</p>
            <h1>UI Console</h1>
          </div>
          <sl-badge variant="primary" pill>
            {config.environment}
          </sl-badge>
        </div>
        {navGroups.map((group) => (
          <div class="nav-group" key={group.label}>
            <p class="nav-label">{group.label}</p>
            {group.links.map((link) => (
              <Link
                key={link.href}
                class={`nav-link ${location === link.href ? 'is-active' : ''}`}
                href={link.href}
              >
                {link.label}
              </Link>
            ))}
          </div>
        ))}
      </aside>
      <main class="content-panel">
        <header class="content-header">
          <div>
            <p class="eyebrow">Thin frontend</p>
            <h2>Candidate and admin workflows</h2>
          </div>
          <div class="endpoint-chips">
            <sl-badge pill>{config.jobApiBaseUrl}</sl-badge>
            <sl-badge pill>{config.candidateApiBaseUrl}</sl-badge>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}
