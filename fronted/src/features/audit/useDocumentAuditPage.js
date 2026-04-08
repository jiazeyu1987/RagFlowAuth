import useDocumentAuditData from './useDocumentAuditData';
import useDocumentAuditVersions from './useDocumentAuditVersions';

export default function useDocumentAuditPage() {
  const dataState = useDocumentAuditData();
  const versionsState = useDocumentAuditVersions();

  return {
    ...dataState,
    ...versionsState,
  };
}
