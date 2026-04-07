import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import UserProfileFields from './UserProfileFields';

describe('UserProfileFields', () => {
  const inputStyle = {
    width: '100%',
    padding: '8px',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    boxSizing: 'border-box',
  };

  const labels = {
    fullName: '姓名',
    company: '公司',
    companyPlaceholder: '请选择公司',
    department: '部门',
    departmentPlaceholder: '请选择部门',
    userType: '用户类型',
    normalUser: '普通用户',
    subAdmin: '子管理员',
    ownerSubAdmin: '归属子管理员',
    ownerSubAdminPlaceholder: '请选择归属子管理员',
  };

  const testIds = {
    fullName: 'profile-full-name',
    company: 'profile-company',
    department: 'profile-department',
    userType: 'profile-user-type',
    userTypeReadonly: 'profile-user-type-readonly',
    manager: 'profile-manager',
  };

  const companies = [
    { id: 1, name: 'Acme' },
    { id: 2, name: 'Beta' },
  ];

  const departments = [
    { id: 11, company_id: 1, name: '研发一部' },
    { id: 22, company_id: 2, name: '研发二部' },
  ];

  const subAdminOptions = [{ value: 'u-sub', label: 'Alice' }];

  it('filters department options and forwards patch updates', () => {
    const onChangeValues = jest.fn();

    render(
      <UserProfileFields
        inputStyle={inputStyle}
        values={{
          full_name: 'Tom',
          company_id: '1',
          department_id: '11',
          user_type: 'normal',
          manager_user_id: 'u-sub',
        }}
        onChangeValues={onChangeValues}
        companies={companies}
        departments={departments}
        subAdminOptions={subAdminOptions}
        labels={labels}
        testIds={testIds}
        companyRequired
        departmentRequired
        managerRequired
        resetDepartmentOnCompanyChange
      />
    );

    expect(screen.getByRole('option', { name: '研发一部' })).toBeInTheDocument();
    expect(screen.queryByRole('option', { name: '研发二部' })).not.toBeInTheDocument();
    expect(screen.getByTestId('profile-manager')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('profile-full-name'), { target: { value: 'Tommy' } });
    fireEvent.change(screen.getByTestId('profile-company'), { target: { value: '2' } });
    fireEvent.change(screen.getByTestId('profile-user-type'), { target: { value: 'sub_admin' } });

    expect(onChangeValues).toHaveBeenNthCalledWith(1, { full_name: 'Tommy' });
    expect(onChangeValues).toHaveBeenNthCalledWith(2, { company_id: '2', department_id: '' });
    expect(onChangeValues).toHaveBeenNthCalledWith(3, { user_type: 'sub_admin' });
  });

  it('hides manager selection for sub admins', () => {
    render(
      <UserProfileFields
        inputStyle={inputStyle}
        values={{
          full_name: 'Tom',
          company_id: '1',
          department_id: '11',
          user_type: 'sub_admin',
          manager_user_id: '',
        }}
        onChangeValues={jest.fn()}
        companies={companies}
        departments={departments}
        subAdminOptions={subAdminOptions}
        labels={labels}
        testIds={testIds}
      />
    );

    expect(screen.queryByTestId('profile-manager')).not.toBeInTheDocument();
  });

  it('renders readonly user type when requested', () => {
    render(
      <UserProfileFields
        inputStyle={inputStyle}
        values={{
          full_name: 'Admin',
          company_id: '1',
          department_id: '11',
          user_type: 'normal',
          manager_user_id: '',
        }}
        onChangeValues={jest.fn()}
        companies={companies}
        departments={departments}
        subAdminOptions={subAdminOptions}
        labels={labels}
        testIds={testIds}
        readonlyUserType
        userTypeReadonlyLabel="管理员"
        showManager={false}
      />
    );

    expect(screen.queryByTestId('profile-user-type')).not.toBeInTheDocument();
    expect(screen.getByTestId('profile-user-type-readonly')).toHaveTextContent('管理员');
  });
});
