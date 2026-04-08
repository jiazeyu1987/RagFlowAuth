import React from 'react';
import UserLookupField from './UserLookupField';
import {
  cardStyle,
  cellStyle,
  inputStyle,
  labelStyle,
  primaryButtonStyle,
  sectionGridStyle,
  tableStyle,
  tableWrapperStyle,
  textareaStyle,
  twoColumnGridStyle,
} from '../pageStyles';

export default function TrainingRecordsSection({
  text,
  requirements,
  records,
  recordForm,
  recordSelectedUser,
  recordUserSearch,
  savingRecord,
  trainingOutcomeOptions,
  effectivenessOptions,
  buildRequirementOptionLabel,
  getTrainingOutcomeLabel,
  getEffectivenessLabel,
  buildDisplayUserLabel,
  buildUserLabel,
  formatTime,
  onRequirementChange,
  onRecordFormFieldChange,
  onUserKeywordChange,
  onOpenUserSearch,
  onCloseUserSearch,
  onSelectUser,
  onSubmit,
}) {
  return (
    <>
      <section style={cardStyle} data-testid="training-records-tab-panel">
        <h3 style={{ marginTop: 0 }}>{text.recordSection}</h3>
        <div style={sectionGridStyle}>
          <UserLookupField
            label={text.targetUser}
            placeholder={text.userSearchPlaceholder}
            selectedUser={recordSelectedUser}
            searchState={recordUserSearch}
            onInputChange={onUserKeywordChange}
            onFocus={onOpenUserSearch}
            onBlur={onCloseUserSearch}
            onSelectUser={onSelectUser}
            testIdPrefix="training-record-user-search"
            text={text}
            buildUserLabel={buildUserLabel}
          />
          <label style={labelStyle}>
            <span>{text.trainingRequirement}</span>
            <select
              data-testid="training-record-requirement"
              value={recordForm.requirement_code}
              onChange={(event) => onRequirementChange(event.target.value)}
              style={inputStyle}
            >
              {requirements.length === 0 ? (
                <option value="">{text.noRequirements}</option>
              ) : requirements.map((item) => (
                <option key={item.requirement_code} value={item.requirement_code}>
                  {buildRequirementOptionLabel(item)}
                </option>
              ))}
            </select>
          </label>
          <label style={labelStyle}>
            <span>{text.completedAt}</span>
            <input
              data-testid="training-record-completed-at"
              type="datetime-local"
              value={recordForm.completed_at}
              onChange={(event) => onRecordFormFieldChange('completed_at', event.target.value)}
              style={inputStyle}
            />
          </label>
          <div style={twoColumnGridStyle}>
            <label style={labelStyle}>
              <span>{text.trainingOutcome}</span>
              <select
                data-testid="training-record-outcome"
                value={recordForm.training_outcome}
                onChange={(event) =>
                  onRecordFormFieldChange('training_outcome', event.target.value)
                }
                style={inputStyle}
              >
                {trainingOutcomeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label style={labelStyle}>
              <span>{text.effectivenessStatus}</span>
              <select
                data-testid="training-record-effectiveness"
                value={recordForm.effectiveness_status}
                onChange={(event) =>
                  onRecordFormFieldChange('effectiveness_status', event.target.value)
                }
                style={inputStyle}
              >
                {effectivenessOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label style={labelStyle}>
            <span>{text.effectivenessSummary}</span>
            <textarea
              data-testid="training-record-summary"
              rows={3}
              value={recordForm.effectiveness_summary}
              onChange={(event) =>
                onRecordFormFieldChange('effectiveness_summary', event.target.value)
              }
              style={textareaStyle}
            />
          </label>
          <label style={labelStyle}>
            <span>{text.notes}</span>
            <textarea
              data-testid="training-record-notes"
              rows={3}
              value={recordForm.training_notes}
              onChange={(event) => onRecordFormFieldChange('training_notes', event.target.value)}
              style={textareaStyle}
            />
          </label>
          <button
            type="button"
            data-testid="training-record-submit"
            onClick={onSubmit}
            disabled={savingRecord}
            style={primaryButtonStyle}
          >
            {savingRecord ? text.saveRecordPending : text.saveRecord}
          </button>
        </div>
      </section>

      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>{text.latestRecords}</h3>
        <div style={tableWrapperStyle}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={cellStyle}>{text.targetUser}</th>
                <th style={cellStyle}>{text.requirementCode}</th>
                <th style={cellStyle}>{text.curriculumVersion}</th>
                <th style={cellStyle}>{text.trainingOutcome}</th>
                <th style={cellStyle}>{text.effectivenessStatus}</th>
                <th style={cellStyle}>{text.completedAt}</th>
              </tr>
            </thead>
            <tbody>
              {records.length === 0 ? (
                <tr>
                  <td style={cellStyle} colSpan={6}>
                    {text.noRecords}
                  </td>
                </tr>
              ) : records.map((item) => (
                <tr key={item.record_id}>
                  <td style={cellStyle}>{buildDisplayUserLabel(item.user_id)}</td>
                  <td style={cellStyle}>{item.requirement_code}</td>
                  <td style={cellStyle}>{item.curriculum_version}</td>
                  <td style={cellStyle}>{getTrainingOutcomeLabel(item.training_outcome)}</td>
                  <td style={cellStyle}>{getEffectivenessLabel(item.effectiveness_status)}</td>
                  <td style={cellStyle}>{formatTime(item.completed_at_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
