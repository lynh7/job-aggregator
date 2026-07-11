// @ts-nocheck
import { useMemo, useState } from 'preact/hooks';
import { SectionCard } from 'src/components/section-card';
import { getRuntimeConfig } from 'src/lib/config';
import { postJson } from 'src/lib/http';
import { CrawlResponse } from 'src/lib/types';

const providerOptions = [
  { value: 'topcv', label: 'TopCV' },
  { value: 'itviec', label: 'ITViec' },
  { value: 'mock', label: 'Mock' },
];

function parseKeywords(input: string): string[] {
  return input
    .split(',')
    .map((value) => value.trim())
    .filter(Boolean);
}

export function AdminCrawlPage() {
  const config = getRuntimeConfig();
  const [keywords, setKeywords] = useState('data engineer, backend');
  const [location, setLocation] = useState('');
  const [limitPerProvider, setLimitPerProvider] = useState('10');
  const [exportEnabled, setExportEnabled] = useState(true);
  const [providers, setProviders] = useState<string[]>(['topcv', 'itviec']);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CrawlResponse | null>(null);

  const parsedKeywords = useMemo(() => parseKeywords(keywords), [keywords]);

  function toggleProvider(provider: string) {
    setProviders((current) => current.includes(provider)
      ? current.filter((value) => value !== provider)
      : [...current, provider]);
  }

  async function handleSubmit(event: Event) {
    event.preventDefault();

    if (parsedKeywords.length === 0) {
      setError('Enter at least one keyword.');
      return;
    }

    if (providers.length === 0) {
      setError('Select at least one provider.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await postJson<CrawlResponse>(`${config.crawlerApiBaseUrl}/crawl`, {
        keywords: parsedKeywords,
        providers,
        location: location.trim() || null,
        limit_per_provider: Number(limitPerProvider) || 10,
        export: exportEnabled,
      });
      setResult(response);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Crawl request failed.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div class="page-grid">
      <SectionCard title="Admin Crawl Trigger" subtitle="Run a multi-provider crawl through crawler-api and ingest into the core API">
        <form class="stack-form" onSubmit={handleSubmit}>
          <label>
            Keywords
            <input
              class="text-input"
              placeholder="data engineer, platform engineer"
              value={keywords}
              onInput={(event) => setKeywords((event.currentTarget as HTMLInputElement).value)}
            />
            <span class="muted">Comma-separated. Browser only sends intent; crawl logic stays in the backend.</span>
          </label>

          <div class="inline-field-grid">
            <label>
              Location
              <input
                class="text-input"
                placeholder="Ho Chi Minh City"
                value={location}
                onInput={(event) => setLocation((event.currentTarget as HTMLInputElement).value)}
              />
            </label>
            <label>
              Limit per provider
              <input
                class="text-input"
                type="number"
                min="1"
                max="100"
                value={limitPerProvider}
                onInput={(event) => setLimitPerProvider((event.currentTarget as HTMLInputElement).value)}
              />
            </label>
          </div>

          <div>
            <p class="field-label">Providers</p>
            <div class="checkbox-grid">
              {providerOptions.map((provider) => (
                <label class="check-option" key={provider.value}>
                  <input
                    type="checkbox"
                    checked={providers.includes(provider.value)}
                    onChange={() => toggleProvider(provider.value)}
                  />
                  <span>{provider.label}</span>
                </label>
              ))}
            </div>
          </div>

          <label class="check-option">
            <input
              type="checkbox"
              checked={exportEnabled}
              onChange={(event) => setExportEnabled((event.currentTarget as HTMLInputElement).checked)}
            />
            <span>Generate JSON and XLSX export artifacts when available</span>
          </label>

          <div class="toolbar-row">
            <button type="submit" class="primary-button" disabled={submitting}>
              {submitting ? 'Triggering crawl…' : 'Trigger Crawl'}
            </button>
            <span class="muted monospace">{config.crawlerApiBaseUrl}/crawl</span>
          </div>
        </form>

        {error ? <sl-alert variant="danger" open>{error}</sl-alert> : null}
      </SectionCard>

      <SectionCard title="Request Preview" subtitle="Current backend payload assembled by the UI">
        <pre>{JSON.stringify({
          keywords: parsedKeywords,
          providers,
          location: location.trim() || null,
          limit_per_provider: Number(limitPerProvider) || 10,
          export: exportEnabled,
        }, null, 2)}</pre>
      </SectionCard>

      <SectionCard title="Latest Crawl Result" subtitle="Response from crawler-api after ingest to job-api">
        {result ? (
          <div class="result-grid">
            <div class="result-stat">
              <span class="stat-label">Fetched</span>
              <strong class="stat-value">{result.fetched}</strong>
            </div>
            <div class="result-stat">
              <span class="stat-label">Stored</span>
              <strong class="stat-value">{result.stored}</strong>
            </div>
            <div class="result-stat">
              <span class="stat-label">Duplicates Filtered</span>
              <strong class="stat-value">{result.duplicates_filtered}</strong>
            </div>
            <div class="result-stat">
              <span class="stat-label">Providers</span>
              <strong>{result.providers.join(', ') || '—'}</strong>
            </div>
            <div class="result-stat">
              <span class="stat-label">JSON Export</span>
              <strong>{result.json_export ?? '—'}</strong>
            </div>
            <div class="result-stat">
              <span class="stat-label">XLSX Export</span>
              <strong>{result.xlsx_export ?? '—'}</strong>
            </div>
          </div>
        ) : (
          <sl-alert variant="primary" open>No crawl submitted yet in this browser session.</sl-alert>
        )}
      </SectionCard>
    </div>
  );
}
