import { isSessionActive } from '../download/downloadPageUtils';
import useDownloadPageController from '../download/useDownloadPageController';
import paperDownloadManager from './PaperDownloadManager';
import {
  DEFAULT_PAPER_SOURCES,
  PAPER_LAST_CONFIG_KEY,
  PAPER_LOCAL_KB_REF,
  PAPER_SOURCE_LABEL_MAP,
} from './paperDownloadPageUtils';

export default function usePaperDownloadPage() {
  return useDownloadPageController({
    manager: paperDownloadManager,
    storageKey: PAPER_LAST_CONFIG_KEY,
    localKbRef: PAPER_LOCAL_KB_REF,
    defaultSources: DEFAULT_PAPER_SOURCES,
    sourceLabelMap: PAPER_SOURCE_LABEL_MAP,
  });
}

export { isSessionActive };
