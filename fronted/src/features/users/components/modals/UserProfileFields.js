import React, { useMemo } from 'react';
import ManagerAssignmentField from './ManagerAssignmentField';
import OrganizationAssignmentFields from './OrganizationAssignmentFields';
import UserTypeField from './UserTypeField';
import { filterDepartmentsByCompany } from '../../utils/userDirectorySelection';

export default function UserProfileFields({
  inputStyle,
  values,
  onChangeValues,
  afterFullName = null,
  companies,
  departments,
  subAdminOptions,
  labels,
  testIds,
  companyRequired = false,
  departmentRequired = false,
  managerRequired = false,
  readonlyUserType = false,
  userTypeReadonlyLabel = '',
  showManager = true,
  userTypeBeforeOrganization = false,
  resetDepartmentOnCompanyChange = false,
}) {
  const visibleDepartments = useMemo(() => {
    return filterDepartmentsByCompany({
      companyId: values.company_id,
      departments,
    });
  }, [departments, values.company_id]);

  const isSubAdmin = String(values.user_type || 'normal') === 'sub_admin';

  const userTypeField = (
    <UserTypeField
      label={labels.userType}
      inputStyle={inputStyle}
      value={values.user_type}
      onChange={(event) => onChangeValues({ user_type: event.target.value })}
      testId={testIds.userType}
      normalLabel={labels.normalUser}
      subAdminLabel={labels.subAdmin}
      readonly={readonlyUserType}
      readonlyLabel={userTypeReadonlyLabel}
      readonlyTestId={testIds.userTypeReadonly}
    />
  );

  const organizationFields = (
    <OrganizationAssignmentFields
      inputStyle={inputStyle}
      companyLabel={labels.company}
      companyPlaceholder={labels.companyPlaceholder}
      companyValue={values.company_id}
      companyRequired={companyRequired}
      companyTestId={testIds.company}
      companies={companies}
      onChangeCompany={(event) =>
        onChangeValues(
          resetDepartmentOnCompanyChange
            ? { company_id: event.target.value, department_id: '' }
            : { company_id: event.target.value }
        )
      }
      departmentLabel={labels.department}
      departmentPlaceholder={labels.departmentPlaceholder}
      departmentValue={values.department_id}
      departmentRequired={departmentRequired}
      departmentTestId={testIds.department}
      departments={visibleDepartments}
      onChangeDepartment={(event) => onChangeValues({ department_id: event.target.value })}
    />
  );

  return (
    <>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{labels.fullName}</label>
        <input
          type="text"
          value={values.full_name || ''}
          onChange={(event) => onChangeValues({ full_name: event.target.value })}
          data-testid={testIds.fullName}
          style={inputStyle}
        />
      </div>

      {afterFullName}
      {userTypeBeforeOrganization ? userTypeField : organizationFields}
      {userTypeBeforeOrganization ? organizationFields : userTypeField}

      {showManager && !isSubAdmin ? (
        <ManagerAssignmentField
          inputStyle={inputStyle}
          label={labels.ownerSubAdmin}
          placeholder={labels.ownerSubAdminPlaceholder}
          value={values.manager_user_id}
          required={managerRequired}
          testId={testIds.manager}
          options={subAdminOptions}
          onChange={(event) => onChangeValues({ manager_user_id: event.target.value })}
        />
      ) : null}
    </>
  );
}
