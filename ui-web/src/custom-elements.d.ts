declare namespace preact.JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}

declare global {
  interface Window {
    __JOB_AGGREGATOR_CONFIG__?: {
      jobApiBaseUrl?: string;
      candidateApiBaseUrl?: string;
      crawlerApiBaseUrl?: string;
      environment?: string;
    };
  }
}

export {};
