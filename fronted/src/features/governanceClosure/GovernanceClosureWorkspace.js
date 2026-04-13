import React, { useCallback, useEffect, useState } from 'react';
import governanceClosureApi from './api';

const panelStyle = {
  background: '#ffffff',
  border: '1px solid #d7dde5',
  borderRadius: 8,
  padding: 16,
  boxShadow: '0 8px 20px rgba(15, 23, 42, 0.05)',
};

const inputStyle = {
  width: '100%',
  padding: 10,
  borderRadius: 6,
  border: '1px solid #c7d2de',
  boxSizing: 'border-box',
};

const buttonStyle = {
  padding: '8px 12px',
  borderRadius: 6,
  border: '1px solid #94a3b8',
  background: '#f8fafc',
  cursor: 'pointer',
};

const primaryButtonStyle = {
  ...buttonStyle,
  border: '1px solid #0f766e',
  background: '#0f766e',
  color: '#ffffff',
};

const sectionHeaderStyle = {
  margin: 0,
  color: '#0f172a',
};

const initialComplaintForm = {
  complaint_code: '',
  source_channel: 'customer',
  severity_level: 'major',
  subject: '',
  description: '',
  reported_by_user_id: '',
  owner_user_id: '',
};

const initialCapaForm = {
  capa_code: '',
  complaint_id: '',
  action_title: '',
  root_cause_summary: '',
  correction_plan: '',
  preventive_plan: '',
  owner_user_id: '',
  due_date: '',
};

const initialInternalAuditForm = {
  audit_code: '',
  scope_summary: '',
  lead_auditor_user_id: '',
  planned_at_ms: '',
};

const initialManagementReviewForm = {
  review_code: '',
  meeting_at_ms: '',
  chair_user_id: '',
  input_summary: '',
};

export default function GovernanceClosureWorkspace() {
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [complaints, setComplaints] = useState([]);
  const [capas, setCapas] = useState([]);
  const [internalAudits, setInternalAudits] = useState([]);
  const [managementReviews, setManagementReviews] = useState([]);
  const [complaintForm, setComplaintForm] = useState(initialComplaintForm);
  const [capaForm, setCapaForm] = useState(initialCapaForm);
  const [internalAuditForm, setInternalAuditForm] = useState(initialInternalAuditForm);
  const [managementReviewForm, setManagementReviewForm] = useState(initialManagementReviewForm);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [complaintItems, capaItems, auditItems, reviewItems] = await Promise.all([
        governanceClosureApi.listComplaints({ limit: 20 }),
        governanceClosureApi.listCapas({ limit: 20 }),
        governanceClosureApi.listInternalAudits({ limit: 20 }),
        governanceClosureApi.listManagementReviews({ limit: 20 }),
      ]);
      setComplaints(complaintItems);
      setCapas(capaItems);
      setInternalAudits(auditItems);
      setManagementReviews(reviewItems);
    } catch (requestError) {
      setError(requestError.message || 'Failed to load governance closure data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const runAction = useCallback(async (runner, successMessage) => {
    setWorking(true);
    setError('');
    setSuccess('');
    try {
      await runner();
      setSuccess(successMessage);
      await loadAll();
    } catch (actionError) {
      setError(actionError.message || 'Action failed');
    } finally {
      setWorking(false);
    }
  }, [loadAll]);

  return (
    <div style={{ display: 'grid', gap: 14 }} data-testid="governance-closure-workspace">
      {error ? (
        <section style={{ ...panelStyle, color: '#9f1239' }} data-testid="governance-closure-error">
          {error}
        </section>
      ) : null}
      {success ? (
        <section style={{ ...panelStyle, color: '#166534' }} data-testid="governance-closure-success">
          {success}
        </section>
      ) : null}

      <section style={panelStyle}>
        <h4 style={sectionHeaderStyle}>Complaint Cases</h4>
        <p style={{ color: '#475569', marginTop: 8 }}>ComplaintCase owner scope for WS08.</p>
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <input
            style={inputStyle}
            placeholder="Complaint code"
            value={complaintForm.complaint_code}
            onChange={(event) => setComplaintForm((prev) => ({ ...prev, complaint_code: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Subject"
            value={complaintForm.subject}
            onChange={(event) => setComplaintForm((prev) => ({ ...prev, subject: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Description"
            value={complaintForm.description}
            onChange={(event) => setComplaintForm((prev) => ({ ...prev, description: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Reported by user_id"
            value={complaintForm.reported_by_user_id}
            onChange={(event) => setComplaintForm((prev) => ({ ...prev, reported_by_user_id: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Owner user_id"
            value={complaintForm.owner_user_id}
            onChange={(event) => setComplaintForm((prev) => ({ ...prev, owner_user_id: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Severity (minor|major|critical)"
            value={complaintForm.severity_level}
            onChange={(event) => setComplaintForm((prev) => ({ ...prev, severity_level: event.target.value }))}
          />
        </div>
        <button
          type="button"
          style={{ ...primaryButtonStyle, marginTop: 10 }}
          disabled={working}
          onClick={() => runAction(async () => {
            await governanceClosureApi.createComplaint({
              complaint_code: complaintForm.complaint_code.trim(),
              source_channel: complaintForm.source_channel,
              severity_level: complaintForm.severity_level.trim(),
              subject: complaintForm.subject.trim(),
              description: complaintForm.description.trim(),
              reported_by_user_id: complaintForm.reported_by_user_id.trim(),
              owner_user_id: complaintForm.owner_user_id.trim(),
            });
            setComplaintForm(initialComplaintForm);
          }, 'Complaint case created')}
        >
          Create complaint
        </button>
        <div style={{ marginTop: 12, color: '#475569' }}>
          {loading ? 'Loading...' : `${complaints.length} complaint cases`}
        </div>
      </section>

      <section style={panelStyle}>
        <h4 style={sectionHeaderStyle}>CAPA Actions</h4>
        <p style={{ color: '#475569', marginTop: 8 }}>CapaAction owner scope for WS08.</p>
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <input
            style={inputStyle}
            placeholder="CAPA code"
            value={capaForm.capa_code}
            onChange={(event) => setCapaForm((prev) => ({ ...prev, capa_code: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Linked complaint_id (optional)"
            value={capaForm.complaint_id}
            onChange={(event) => setCapaForm((prev) => ({ ...prev, complaint_id: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Title"
            value={capaForm.action_title}
            onChange={(event) => setCapaForm((prev) => ({ ...prev, action_title: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Owner user_id"
            value={capaForm.owner_user_id}
            onChange={(event) => setCapaForm((prev) => ({ ...prev, owner_user_id: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Due date (YYYY-MM-DD)"
            value={capaForm.due_date}
            onChange={(event) => setCapaForm((prev) => ({ ...prev, due_date: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Root cause"
            value={capaForm.root_cause_summary}
            onChange={(event) => setCapaForm((prev) => ({ ...prev, root_cause_summary: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Correction plan"
            value={capaForm.correction_plan}
            onChange={(event) => setCapaForm((prev) => ({ ...prev, correction_plan: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Preventive plan"
            value={capaForm.preventive_plan}
            onChange={(event) => setCapaForm((prev) => ({ ...prev, preventive_plan: event.target.value }))}
          />
        </div>
        <button
          type="button"
          style={{ ...primaryButtonStyle, marginTop: 10 }}
          disabled={working}
          onClick={() => runAction(async () => {
            await governanceClosureApi.createCapa({
              capa_code: capaForm.capa_code.trim(),
              complaint_id: capaForm.complaint_id.trim() || null,
              action_title: capaForm.action_title.trim(),
              root_cause_summary: capaForm.root_cause_summary.trim(),
              correction_plan: capaForm.correction_plan.trim(),
              preventive_plan: capaForm.preventive_plan.trim(),
              owner_user_id: capaForm.owner_user_id.trim(),
              due_date: capaForm.due_date.trim(),
            });
            setCapaForm(initialCapaForm);
          }, 'CAPA action created')}
        >
          Create CAPA
        </button>
        <div style={{ marginTop: 12, color: '#475569' }}>
          {loading ? 'Loading...' : `${capas.length} CAPA actions`}
        </div>
      </section>

      <section style={panelStyle}>
        <h4 style={sectionHeaderStyle}>Internal Audit Records</h4>
        <p style={{ color: '#475569', marginTop: 8 }}>InternalAuditRecord owner scope for WS08.</p>
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <input
            style={inputStyle}
            placeholder="Audit code"
            value={internalAuditForm.audit_code}
            onChange={(event) => setInternalAuditForm((prev) => ({ ...prev, audit_code: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Lead auditor user_id"
            value={internalAuditForm.lead_auditor_user_id}
            onChange={(event) => setInternalAuditForm((prev) => ({ ...prev, lead_auditor_user_id: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Scope summary"
            value={internalAuditForm.scope_summary}
            onChange={(event) => setInternalAuditForm((prev) => ({ ...prev, scope_summary: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Planned at ms"
            value={internalAuditForm.planned_at_ms}
            onChange={(event) => setInternalAuditForm((prev) => ({ ...prev, planned_at_ms: event.target.value }))}
          />
        </div>
        <button
          type="button"
          style={{ ...primaryButtonStyle, marginTop: 10 }}
          disabled={working}
          onClick={() => runAction(async () => {
            await governanceClosureApi.createInternalAudit({
              audit_code: internalAuditForm.audit_code.trim(),
              scope_summary: internalAuditForm.scope_summary.trim(),
              lead_auditor_user_id: internalAuditForm.lead_auditor_user_id.trim(),
              planned_at_ms: Number(internalAuditForm.planned_at_ms),
            });
            setInternalAuditForm(initialInternalAuditForm);
          }, 'Internal audit record created')}
        >
          Create internal audit
        </button>
        <div style={{ marginTop: 12, color: '#475569' }}>
          {loading ? 'Loading...' : `${internalAudits.length} internal audit records`}
        </div>
      </section>

      <section style={panelStyle}>
        <h4 style={sectionHeaderStyle}>Management Review Records</h4>
        <p style={{ color: '#475569', marginTop: 8 }}>ManagementReviewRecord owner scope for WS08.</p>
        <div style={{ display: 'grid', gap: 8, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <input
            style={inputStyle}
            placeholder="Review code"
            value={managementReviewForm.review_code}
            onChange={(event) => setManagementReviewForm((prev) => ({ ...prev, review_code: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Meeting at ms"
            value={managementReviewForm.meeting_at_ms}
            onChange={(event) => setManagementReviewForm((prev) => ({ ...prev, meeting_at_ms: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Chair user_id"
            value={managementReviewForm.chair_user_id}
            onChange={(event) => setManagementReviewForm((prev) => ({ ...prev, chair_user_id: event.target.value }))}
          />
          <input
            style={inputStyle}
            placeholder="Input summary"
            value={managementReviewForm.input_summary}
            onChange={(event) => setManagementReviewForm((prev) => ({ ...prev, input_summary: event.target.value }))}
          />
        </div>
        <button
          type="button"
          style={{ ...primaryButtonStyle, marginTop: 10 }}
          disabled={working}
          onClick={() => runAction(async () => {
            await governanceClosureApi.createManagementReview({
              review_code: managementReviewForm.review_code.trim(),
              meeting_at_ms: Number(managementReviewForm.meeting_at_ms),
              chair_user_id: managementReviewForm.chair_user_id.trim(),
              input_summary: managementReviewForm.input_summary.trim(),
            });
            setManagementReviewForm(initialManagementReviewForm);
          }, 'Management review record created')}
        >
          Create management review
        </button>
        <div style={{ marginTop: 12, color: '#475569' }}>
          {loading ? 'Loading...' : `${managementReviews.length} management review records`}
        </div>
      </section>
    </div>
  );
}
