export const DEFAULT_PAPER_SOURCES = {
  arxiv: { enabled: true, limit: 30 },
  pubmed: { enabled: false, limit: 30 },
  europe_pmc: { enabled: false, limit: 30 },
  openalex: { enabled: false, limit: 30 },
};

export const PAPER_LAST_CONFIG_KEY = 'paper_download_last_config_v1';

export const PAPER_LOCAL_KB_REF = '[鏈湴璁烘枃]';

export const PAPER_SOURCE_LABEL_MAP = {
  arxiv: 'arXiv',
  pubmed: 'PubMed',
  europe_pmc: 'Europe PMC',
  openalex: 'OpenAlex',
};

export const PAPER_BOX_STYLE = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '14px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};
