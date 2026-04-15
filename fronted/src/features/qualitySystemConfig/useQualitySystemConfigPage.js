import { useCallback, useEffect, useMemo, useState } from 'react';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';
import qualitySystemConfigApi from './api';

const TABS = Object.freeze({
  positions: 'positions',
  categories: 'categories',
});

const buildAssignmentDrafts = (positions) => {
  const drafts = {};
  (positions || []).forEach((position) => {
    drafts[position.id] = Array.isArray(position.assigned_users) ? position.assigned_users : [];
  });
  return drafts;
};

const normalizeIds = (items) =>
  (items || [])
    .map((item) => String(item?.user_id || '').trim())
    .filter(Boolean)
    .sort();

const sameAssignments = (left, right) => {
  const leftIds = normalizeIds(left);
  const rightIds = normalizeIds(right);
  if (leftIds.length !== rightIds.length) return false;
  return leftIds.every((value, index) => value === rightIds[index]);
};

export default function useQualitySystemConfigPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [activeTab, setActiveTab] = useState(TABS.positions);
  const [positions, setPositions] = useState([]);
  const [fileCategories, setFileCategories] = useState([]);
  const [assignmentDrafts, setAssignmentDrafts] = useState({});
  const [savingAssignments, setSavingAssignments] = useState({});
  const [categoryName, setCategoryName] = useState('');
  const [categorySubmitting, setCategorySubmitting] = useState(false);
  const [deactivatingCategoryId, setDeactivatingCategoryId] = useState(null);

  const loadConfig = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await qualitySystemConfigApi.getConfig();
      const nextPositions = Array.isArray(payload?.positions) ? payload.positions : [];
      const nextCategories = Array.isArray(payload?.file_categories) ? payload.file_categories : [];
      setPositions(nextPositions);
      setFileCategories(nextCategories);
      setAssignmentDrafts(buildAssignmentDrafts(nextPositions));
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, 'Failed to load quality system configuration.'));
      setPositions([]);
      setFileCategories([]);
      setAssignmentDrafts({});
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const updatePositionDraft = useCallback((positionId, users) => {
    setAssignmentDrafts((previous) => ({
      ...previous,
      [positionId]: Array.isArray(users) ? users : [],
    }));
  }, []);

  const saveAssignments = useCallback(async (positionId, changeReason) => {
    const reason = String(changeReason || '').trim();
    if (!reason) {
      setError('Please provide a change reason.');
      return false;
    }
    const nextUsers = Array.isArray(assignmentDrafts[positionId]) ? assignmentDrafts[positionId] : [];
    setSavingAssignments((previous) => ({ ...previous, [positionId]: true }));
    setError('');
    setNotice('');
    try {
      const updated = await qualitySystemConfigApi.updateAssignments(positionId, {
        user_ids: nextUsers.map((item) => item.user_id),
        change_reason: reason,
      });
      setPositions((previous) =>
        previous.map((position) => (position.id === positionId ? updated : position))
      );
      setAssignmentDrafts((previous) => ({
        ...previous,
        [positionId]: Array.isArray(updated?.assigned_users) ? updated.assigned_users : [],
      }));
      setNotice('Position assignments saved.');
      return true;
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, 'Failed to save position assignments.'));
      return false;
    } finally {
      setSavingAssignments((previous) => ({ ...previous, [positionId]: false }));
    }
  }, [assignmentDrafts]);

  const createCategory = useCallback(async (changeReason) => {
    const name = String(categoryName || '').trim();
    const reason = String(changeReason || '').trim();
    if (!name) {
      setError('Please provide a file category name.');
      return false;
    }
    if (!reason) {
      setError('Please provide a change reason.');
      return false;
    }
    setCategorySubmitting(true);
    setError('');
    setNotice('');
    try {
      const created = await qualitySystemConfigApi.createFileCategory({
        name,
        change_reason: reason,
      });
      setFileCategories((previous) => [...previous, created]);
      setCategoryName('');
      setNotice('File category saved.');
      return true;
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, 'Failed to save file category.'));
      return false;
    } finally {
      setCategorySubmitting(false);
    }
  }, [categoryName]);

  const deactivateCategory = useCallback(async (categoryId, changeReason) => {
    const reason = String(changeReason || '').trim();
    if (!reason) {
      setError('Please provide a change reason.');
      return false;
    }
    setDeactivatingCategoryId(categoryId);
    setError('');
    setNotice('');
    try {
      await qualitySystemConfigApi.deactivateFileCategory(categoryId, {
        change_reason: reason,
      });
      setFileCategories((previous) => previous.filter((item) => item.id !== categoryId));
      setNotice('File category removed.');
      return true;
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, 'Failed to remove file category.'));
      return false;
    } finally {
      setDeactivatingCategoryId(null);
    }
  }, []);

  const positionsWithDrafts = useMemo(
    () =>
      positions.map((position) => ({
        ...position,
        draft_assigned_users: assignmentDrafts[position.id] || [],
        is_dirty: !sameAssignments(position.assigned_users, assignmentDrafts[position.id] || []),
      })),
    [assignmentDrafts, positions]
  );

  return {
    loading,
    error,
    notice,
    activeTab,
    tabs: TABS,
    positions: positionsWithDrafts,
    fileCategories,
    categoryName,
    categorySubmitting,
    deactivatingCategoryId,
    savingAssignments,
    setActiveTab,
    setCategoryName,
    updatePositionDraft,
    saveAssignments,
    createCategory,
    deactivateCategory,
    searchUsers: qualitySystemConfigApi.searchUsers,
    reload: loadConfig,
  };
}
