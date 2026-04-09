import React from 'react';

export default function OrganizationAssignmentFields({
  inputStyle,
  companyLabel,
  companyPlaceholder,
  companyValue,
  companyRequired = false,
  companyDisabled = false,
  companyTestId,
  companies,
  onChangeCompany,
  departmentLabel,
  departmentPlaceholder,
  departmentValue,
  departmentRequired = false,
  departmentDisabled = false,
  departmentTestId,
  departments,
  onChangeDepartment,
}) {
  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{companyLabel}</label>
        <select
          required={companyRequired}
          disabled={companyDisabled}
          value={companyValue || ''}
          onChange={onChangeCompany}
          data-testid={companyTestId}
          style={{ ...inputStyle, backgroundColor: companyDisabled ? '#f9fafb' : 'white' }}
        >
          <option value="" disabled>
            {companyPlaceholder}
          </option>
          {(Array.isArray(companies) ? companies : []).map((company) => (
            <option key={company.id} value={String(company.id)}>
              {company.name}
            </option>
          ))}
        </select>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{departmentLabel}</label>
        <select
          required={departmentRequired}
          disabled={departmentDisabled}
          value={departmentValue || ''}
          onChange={onChangeDepartment}
          data-testid={departmentTestId}
          style={{ ...inputStyle, backgroundColor: departmentDisabled ? '#f9fafb' : 'white' }}
        >
          <option value="" disabled>
            {departmentPlaceholder}
          </option>
          {(Array.isArray(departments) ? departments : []).map((department) => (
            <option key={department.id} value={String(department.id)}>
              {department.path_name || department.name}
            </option>
          ))}
        </select>
      </div>
    </>
  );
}
