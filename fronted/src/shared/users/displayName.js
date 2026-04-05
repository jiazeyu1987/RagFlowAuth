export const getDisplayName = (item, fallback = '-') => {
  if (!item) return fallback;
  const values = [
    item.full_name,
    item.display_name,
    item.signed_by_full_name,
    item.applicant_full_name,
    item.approver_full_name,
    item.actor_full_name,
    item.reviewed_by_name,
    item.uploaded_by_name,
    item.deleted_by_name,
    item.downloaded_by_name,
    item.original_uploader_name,
    item.original_reviewer_name,
    item.retired_by_name,
    item.recipient_full_name,
    item.employee_name,
    item.name,
    item.username,
    item.signed_by_username,
    item.applicant_username,
    item.approver_username,
    item.actor_username,
    item.recipient_username,
  ];
  for (const value of values) {
    const text = String(value || '').trim();
    if (text) return text;
  }
  return fallback;
};
