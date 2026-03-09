export const ROOT = '';

export const DATASET_CREATE_ALLOWED_KEYS = ['description', 'chunk_method', 'embedding_model', 'avatar'];

export const DATASET_UPDATE_ALLOWED_KEYS = ['name', ...DATASET_CREATE_ALLOWED_KEYS, 'pagerank'];
