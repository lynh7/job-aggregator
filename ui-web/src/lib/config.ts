export type RuntimeConfig = {
  jobApiBaseUrl: string;
  candidateApiBaseUrl: string;
  crawlerApiBaseUrl: string;
  environment: string;
};

const defaultConfig: RuntimeConfig = {
  jobApiBaseUrl: '/job-api/api/v1',
  candidateApiBaseUrl: '/candidate-api/api/v1',
  crawlerApiBaseUrl: '/crawler-api/api/v1',
  environment: 'local',
};

export function getRuntimeConfig(): RuntimeConfig {
  const fromWindow = window.__JOB_AGGREGATOR_CONFIG__ ?? {};
  return {
    jobApiBaseUrl: fromWindow.jobApiBaseUrl ?? defaultConfig.jobApiBaseUrl,
    candidateApiBaseUrl: fromWindow.candidateApiBaseUrl ?? defaultConfig.candidateApiBaseUrl,
    crawlerApiBaseUrl: fromWindow.crawlerApiBaseUrl ?? defaultConfig.crawlerApiBaseUrl,
    environment: fromWindow.environment ?? defaultConfig.environment,
  };
}
