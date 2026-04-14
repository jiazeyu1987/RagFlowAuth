import React from 'react';
import GovernanceClosureWorkspace from '../features/governanceClosure/GovernanceClosureWorkspace';

const panelStyle = {
  background: '#ffffff',
  border: '1px solid #dbe2ea',
  borderRadius: '16px',
  padding: '18px',
  boxShadow: '0 10px 30px rgba(15, 23, 42, 0.06)',
};

export default function QualitySystemGovernanceClosure() {
  return (
    <div
      data-testid="quality-system-governance-closure-page"
      style={{ display: 'grid', gap: 16, padding: 20, background: '#f8fafc' }}
    >
      <section style={panelStyle}>
        <h2 style={{ margin: 0 }}>投诉与治理闭环</h2>
        <p style={{ margin: '10px 0 0', color: '#475569', lineHeight: 1.6 }}>
          投诉、CAPA、内审与管理评审等治理闭环工作区（管理入口）。
        </p>
      </section>

      <GovernanceClosureWorkspace />
    </div>
  );
}

