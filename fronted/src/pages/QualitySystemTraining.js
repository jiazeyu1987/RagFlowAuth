import React from 'react';
import TrainingAckWorkspace from '../features/qualitySystem/training/TrainingAckWorkspace';

const panelStyle = {
  background: '#ffffff',
  border: '1px solid #dbe2ea',
  borderRadius: '16px',
  padding: '18px',
  boxShadow: '0 10px 30px rgba(15, 23, 42, 0.06)',
};

export default function QualitySystemTraining() {
  return (
    <div
      data-testid="quality-system-training-page"
      style={{ display: 'grid', gap: 16, padding: 20, background: '#f8fafc' }}
    >
      <section style={panelStyle}>
        <h2 style={{ margin: 0 }}>培训与知晓</h2>
        <p style={{ margin: '10px 0 0', color: '#475569', lineHeight: 1.6 }}>
          该工作区基于质量 capability 控制培训分派、知晓确认与疑问闭环。
        </p>
      </section>

      <TrainingAckWorkspace />
    </div>
  );
}

