import React from 'react';
import { cardStyle, cellStyle, tableStyle, tableWrapperStyle } from '../pageStyles';

export default function TrainingRequirementsSection({
  text,
  requirements,
  getControlledActionLabel,
}) {
  return (
    <div style={cardStyle}>
      <h3 style={{ marginTop: 0 }}>{text.requirementSection}</h3>
      <div style={tableWrapperStyle}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={cellStyle}>{text.requirementCode}</th>
              <th style={cellStyle}>{text.controlledAction}</th>
              <th style={cellStyle}>{text.roleCode}</th>
              <th style={cellStyle}>{text.curriculumVersion}</th>
              <th style={cellStyle}>{text.recertificationInterval}</th>
              <th style={cellStyle}>{text.active}</th>
            </tr>
          </thead>
          <tbody>
            {requirements.length === 0 ? (
              <tr>
                <td style={cellStyle} colSpan={6}>
                  {text.noRequirements}
                </td>
              </tr>
            ) : requirements.map((item) => (
              <tr key={item.requirement_code}>
                <td style={cellStyle}>{item.requirement_code}</td>
                <td style={cellStyle}>{getControlledActionLabel(item.controlled_action)}</td>
                <td style={cellStyle}>{item.role_code}</td>
                <td style={cellStyle}>{item.curriculum_version}</td>
                <td style={cellStyle}>{item.recertification_interval_days}</td>
                <td style={cellStyle}>{item.active ? text.yes : text.no}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
