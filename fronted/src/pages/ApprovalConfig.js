import React from 'react';
import ApprovalConfigWorkflowEditor from '../features/operationApproval/components/ApprovalConfigWorkflowEditor';
import { cardStyle } from '../features/operationApproval/pageStyles';
import useApprovalConfigPage from '../features/operationApproval/useApprovalConfigPage';

export default function ApprovalConfig() {
  const {
    loading,
    savingKey,
    error,
    saveMessage,
    drafts,
    currentOperationType,
    currentDraft,
    searchUsers,
    updateMemberSearchState,
    setCurrentOperationType,
    setCurrentDraftName,
    addStep,
    removeStep,
    updateStepField,
    addMember,
    removeMember,
    updateMemberField,
    handleMemberUserKeywordChange,
    handleSelectMemberUser,
    handleSave,
    getSelectedUser,
    getMemberSearchState,
  } = useApprovalConfigPage();

  return (
    <div style={{ display: 'grid', gap: '16px' }} data-testid="approval-config-page">
      {error ? (
        <div
          data-testid="approval-config-error"
          style={{
            ...cardStyle,
            borderColor: '#fecaca',
            background: '#fef2f2',
            color: '#991b1b',
          }}
        >
          {error}
        </div>
      ) : null}

      {saveMessage ? (
        <div
          data-testid="approval-config-success"
          style={{
            ...cardStyle,
            borderColor: '#bbf7d0',
            background: '#f0fdf4',
            color: '#166534',
          }}
        >
          {saveMessage}
        </div>
      ) : null}

      {loading ? (
        <div style={cardStyle}>正在加载审批配置...</div>
      ) : (
        <ApprovalConfigWorkflowEditor
          currentDraft={currentDraft}
          currentOperationType={currentOperationType}
          drafts={drafts}
          savingKey={savingKey}
          searchUsers={searchUsers}
          updateMemberSearchState={updateMemberSearchState}
          setCurrentOperationType={setCurrentOperationType}
          setCurrentDraftName={setCurrentDraftName}
          addStep={addStep}
          removeStep={removeStep}
          updateStepField={updateStepField}
          addMember={addMember}
          removeMember={removeMember}
          updateMemberField={updateMemberField}
          handleMemberUserKeywordChange={handleMemberUserKeywordChange}
          handleSelectMemberUser={handleSelectMemberUser}
          handleSave={handleSave}
          getSelectedUser={getSelectedUser}
          getMemberSearchState={getMemberSearchState}
        />
      )}
    </div>
  );
}
