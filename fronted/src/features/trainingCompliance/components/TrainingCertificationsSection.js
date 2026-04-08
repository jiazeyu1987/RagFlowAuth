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
} from '../pageStyles';

export default function TrainingCertificationsSection({
  text,
  requirements,
  certifications,
  certificationForm,
  certificationSelectedUser,
  certificationUserSearch,
  savingCertification,
  certificationStatusOptions,
  buildRequirementOptionLabel,
  getCertificationStatusLabel,
  buildDisplayUserLabel,
  buildUserLabel,
  formatTime,
  onCertificationFormFieldChange,
  onUserKeywordChange,
  onOpenUserSearch,
  onCloseUserSearch,
  onSelectUser,
  onSubmit,
}) {
  return (
    <>
      <section style={cardStyle} data-testid="training-certifications-tab-panel">
        <h3 style={{ marginTop: 0 }}>{text.certificationSection}</h3>
        <div style={sectionGridStyle}>
          <UserLookupField
            label={text.targetUser}
            placeholder={text.userSearchPlaceholder}
            selectedUser={certificationSelectedUser}
            searchState={certificationUserSearch}
            onInputChange={onUserKeywordChange}
            onFocus={onOpenUserSearch}
            onBlur={onCloseUserSearch}
            onSelectUser={onSelectUser}
            testIdPrefix="training-certification-user-search"
            text={text}
            buildUserLabel={buildUserLabel}
          />
          <label style={labelStyle}>
            <span>{text.trainingRequirement}</span>
            <select
              data-testid="training-certification-requirement"
              value={certificationForm.requirement_code}
              onChange={(event) =>
                onCertificationFormFieldChange('requirement_code', event.target.value)
              }
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
            <span>{text.certificationStatus}</span>
            <select
              data-testid="training-certification-status"
              value={certificationForm.certification_status}
              onChange={(event) =>
                onCertificationFormFieldChange('certification_status', event.target.value)
              }
              style={inputStyle}
            >
              {certificationStatusOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label style={labelStyle}>
            <span>{text.validUntil}</span>
            <input
              data-testid="training-certification-valid-until"
              type="datetime-local"
              value={certificationForm.valid_until}
              onChange={(event) =>
                onCertificationFormFieldChange('valid_until', event.target.value)
              }
              style={inputStyle}
            />
          </label>
          <label style={labelStyle}>
            <span>{text.notes}</span>
            <textarea
              data-testid="training-certification-notes"
              rows={3}
              value={certificationForm.certification_notes}
              onChange={(event) =>
                onCertificationFormFieldChange('certification_notes', event.target.value)
              }
              style={textareaStyle}
            />
          </label>
          <button
            type="button"
            data-testid="training-certification-submit"
            onClick={onSubmit}
            disabled={savingCertification}
            style={primaryButtonStyle}
          >
            {savingCertification ? text.saveCertificationPending : text.saveCertification}
          </button>
        </div>
      </section>

      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>{text.latestCertifications}</h3>
        <div style={tableWrapperStyle}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={cellStyle}>{text.targetUser}</th>
                <th style={cellStyle}>{text.requirementCode}</th>
                <th style={cellStyle}>{text.curriculumVersion}</th>
                <th style={cellStyle}>{text.certificationStatus}</th>
                <th style={cellStyle}>{text.validUntil}</th>
                <th style={cellStyle}>{text.grantedAt}</th>
              </tr>
            </thead>
            <tbody>
              {certifications.length === 0 ? (
                <tr>
                  <td style={cellStyle} colSpan={6}>
                    {text.noCertifications}
                  </td>
                </tr>
              ) : certifications.map((item) => (
                <tr key={item.certification_id}>
                  <td style={cellStyle}>{buildDisplayUserLabel(item.user_id)}</td>
                  <td style={cellStyle}>{item.requirement_code}</td>
                  <td style={cellStyle}>{item.curriculum_version}</td>
                  <td style={cellStyle}>
                    {getCertificationStatusLabel(item.certification_status)}
                  </td>
                  <td style={cellStyle}>{formatTime(item.valid_until_ms)}</td>
                  <td style={cellStyle}>{formatTime(item.granted_at_ms)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
