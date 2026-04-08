import React from 'react';
import ApprovalMemberUserLookup from './ApprovalMemberUserLookup';
import {
  WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
  WORKFLOW_MEMBER_TYPE_USER,
  buildMemberSearchKey,
  createUserSearchState,
  specialRoleLabel,
} from '../approvalConfigHelpers';
import { buttonStyle, cardStyle, primaryButtonStyle } from '../pageStyles';

export default function ApprovalConfigWorkflowEditor({
  currentDraft,
  currentOperationType,
  drafts,
  savingKey,
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
}) {
  if (!currentDraft) {
    return <div style={cardStyle}>暂无审批场景</div>;
  }

  return (
    <section
      key={currentDraft.operation_type}
      style={cardStyle}
      data-testid={`approval-config-card-${currentDraft.operation_type}`}
    >
      <div style={{ display: 'grid', gap: '14px' }}>
        <label style={{ display: 'grid', gap: '6px' }}>
          <span style={{ fontWeight: 600, color: '#111827' }}>审批场景</span>
          <select
            value={currentOperationType}
            onChange={(event) => setCurrentOperationType(event.target.value)}
            data-testid="approval-config-operation-select"
            style={{
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '10px',
            }}
          >
            {drafts.map((draft) => (
              <option key={draft.operation_type} value={draft.operation_type}>
                {draft.operation_label}
              </option>
            ))}
          </select>
        </label>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: '12px',
            flexWrap: 'wrap',
          }}
        >
          <div>
            <div style={{ fontWeight: 700, color: '#111827' }}>{currentDraft.operation_label}</div>
            <div style={{ color: '#6b7280', marginTop: '4px' }}>{currentDraft.operation_type}</div>
          </div>
          <button
            type="button"
            data-testid={`approval-config-save-${currentDraft.operation_type}`}
            onClick={handleSave}
            disabled={savingKey === currentDraft.operation_type}
            style={primaryButtonStyle}
          >
            {savingKey === currentDraft.operation_type ? '保存中...' : '保存'}
          </button>
        </div>

        <label style={{ display: 'grid', gap: '6px' }}>
          <span style={{ fontWeight: 600, color: '#111827' }}>工作流名称</span>
          <input
            type="text"
            value={currentDraft.name}
            data-testid={`approval-config-name-${currentDraft.operation_type}`}
            onChange={(event) => setCurrentDraftName(event.target.value)}
            style={{
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '10px',
            }}
          />
        </label>

        {(currentDraft.steps || []).map((step, stepIndex) => (
          <div
            key={`${currentDraft.operation_type}-${step.step_no}`}
            style={{
              border: '1px solid #e5e7eb',
              borderRadius: '12px',
              padding: '12px',
            }}
            data-testid={`approval-config-step-${currentDraft.operation_type}-${stepIndex}`}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: '12px',
                alignItems: 'center',
                flexWrap: 'wrap',
              }}
            >
              <strong>{`第 ${stepIndex + 1} 层`}</strong>
              <button
                type="button"
                onClick={() => removeStep(stepIndex)}
                disabled={(currentDraft.steps || []).length <= 1}
                style={buttonStyle}
              >
                删除本层
              </button>
            </div>

            <div style={{ marginTop: '12px', display: 'grid', gap: '12px' }}>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span style={{ fontWeight: 600, color: '#111827' }}>层名称</span>
                <input
                  type="text"
                  value={step.step_name}
                  data-testid={`approval-config-step-name-${currentDraft.operation_type}-${stepIndex}`}
                  onChange={(event) =>
                    updateStepField(stepIndex, 'step_name', event.target.value)
                  }
                  style={{
                    padding: '10px 12px',
                    border: '1px solid #d1d5db',
                    borderRadius: '10px',
                  }}
                />
              </label>

              <div style={{ display: 'grid', gap: '10px' }}>
                <div style={{ fontWeight: 600, color: '#111827' }}>审批成员</div>
                {(step.members || []).map((member, memberIndex) => {
                  const searchKey = buildMemberSearchKey(
                    currentDraft.operation_type,
                    stepIndex,
                    memberIndex
                  );

                  return (
                    <div
                      key={`${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '180px minmax(0, 1fr) auto',
                        gap: '10px',
                        alignItems: 'center',
                      }}
                      data-testid={`approval-config-member-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                    >
                      <select
                        value={member.member_type}
                        data-testid={`approval-config-member-type-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                        onChange={(event) =>
                          updateMemberField(
                            stepIndex,
                            memberIndex,
                            'member_type',
                            event.target.value
                          )
                        }
                        style={{
                          padding: '10px 12px',
                          border: '1px solid #d1d5db',
                          borderRadius: '10px',
                        }}
                      >
                        <option value={WORKFLOW_MEMBER_TYPE_USER}>固定用户</option>
                        <option value={WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE}>直属主管</option>
                      </select>

                      {member.member_type === WORKFLOW_MEMBER_TYPE_USER ? (
                        <ApprovalMemberUserLookup
                          searchKey={searchKey}
                          selectedUser={getSelectedUser(member.member_ref)}
                          searchState={
                            getMemberSearchState(
                              currentDraft.operation_type,
                              stepIndex,
                              memberIndex
                            ) || createUserSearchState()
                          }
                          onSearchStateChange={updateMemberSearchState}
                          onInputChange={(value) =>
                            handleMemberUserKeywordChange(
                              currentDraft.operation_type,
                              stepIndex,
                              memberIndex,
                              value
                            )
                          }
                          onSelectUser={(selectedUser) =>
                            handleSelectMemberUser(
                              currentDraft.operation_type,
                              stepIndex,
                              memberIndex,
                              selectedUser
                            )
                          }
                          searchUsers={searchUsers}
                          testIdPrefix={`approval-config-member-ref-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                        />
                      ) : (
                        <div
                          data-testid={`approval-config-member-role-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                          style={{
                            padding: '10px 12px',
                            border: '1px solid #d1d5db',
                            borderRadius: '10px',
                            background: '#f9fafb',
                            color: '#374151',
                          }}
                        >
                          {specialRoleLabel(member.member_ref)}
                        </div>
                      )}

                      <button
                        type="button"
                        onClick={() => removeMember(stepIndex, memberIndex)}
                        style={buttonStyle}
                      >
                        删除成员
                      </button>
                    </div>
                  );
                })}

                <div>
                  <button
                    type="button"
                    data-testid={`approval-config-add-member-${currentDraft.operation_type}-${stepIndex}`}
                    onClick={() => addMember(stepIndex)}
                    style={buttonStyle}
                  >
                    增加成员
                  </button>
                </div>
              </div>
            </div>
          </div>
        ))}

        <div>
          <button
            type="button"
            data-testid={`approval-config-add-step-${currentDraft.operation_type}`}
            onClick={addStep}
            style={buttonStyle}
          >
            增加一层
          </button>
        </div>
      </div>
    </section>
  );
}
