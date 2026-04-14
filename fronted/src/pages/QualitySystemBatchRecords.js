import React from 'react';
import BatchRecordsWorkspace from '../features/batchRecords/BatchRecordsWorkspace';

const panelStyle = {
  background: '#ffffff',
  border: '1px solid #dbe2ea',
  borderRadius: '16px',
  padding: '18px',
  boxShadow: '0 10px 30px rgba(15, 23, 42, 0.06)',
};

export default function QualitySystemBatchRecords() {
  return (
    <div
      data-testid="quality-system-batch-records-page"
      style={{ display: 'grid', gap: 16, padding: 20, background: '#f8fafc' }}
    >
      <section style={panelStyle}>
        <h2 style={{ margin: 0 }}>批记录与签名</h2>
        <p style={{ margin: '10px 0 0', color: '#475569', lineHeight: 1.6 }}>
          该工作区提供批记录模板、执行实例、步骤写入、电子签名、复核与导出能力，并写入审计日志。
        </p>
      </section>

      <BatchRecordsWorkspace />
    </div>
  );
}
