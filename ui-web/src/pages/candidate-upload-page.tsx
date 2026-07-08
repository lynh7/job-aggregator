// @ts-nocheck
import { useState } from 'preact/hooks';
import { SectionCard } from 'src/components/section-card';
import { getRuntimeConfig } from 'src/lib/config';
import { CandidateCreateResponse } from 'src/lib/types';

export function CandidateUploadPage() {
  const config = getRuntimeConfig();
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: Event) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const data = new FormData(form);
    setSubmitting(true);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch(`${config.candidateApiBaseUrl}/candidates`, {
        method: 'POST',
        body: data,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }
      const payload = (await response.json()) as CandidateCreateResponse;
      setMessage(`Candidate ${payload.candidate_id} accepted. Task ${payload.task_id} queued.`);
      form.reset();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Upload failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <SectionCard title="Upload Candidate CV" subtitle="Public candidate intake without login for now">
      <form class="stack-form" onSubmit={handleSubmit}>
        <label>
          Full name
          <input class="text-input" name="full_name" placeholder="Jane Doe" />
        </label>
        <label>
          Email
          <input class="text-input" name="email" type="email" placeholder="jane@example.com" />
        </label>
        <label>
          Phone
          <input class="text-input" name="phone" placeholder="+84..." />
        </label>
        <label>
          Location
          <input class="text-input" name="location" placeholder="Ho Chi Minh City" />
        </label>
        <label>
          CV file
          <input class="text-input" name="file" type="file" required />
        </label>
        <div class="toolbar-row">
          <button class="primary-button" type="submit" disabled={submitting}>
            {submitting ? 'Submitting…' : 'Submit CV'}
          </button>
        </div>
      </form>
      {message ? <sl-alert variant="success" open>{message}</sl-alert> : null}
      {error ? <sl-alert variant="danger" open>{error}</sl-alert> : null}
    </SectionCard>
  );
}
