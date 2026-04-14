import React from 'react';
import UserManagementContent from '../features/users/components/UserManagementContent';
import UserManagementModals from '../features/users/components/UserManagementModals';
import useUserManagementPage from '../features/users/useUserManagementPage';
import {
  buildUserManagementContentProps,
  buildUserManagementModalProps,
} from '../features/users/utils/userManagementPageSections';

const UserManagement = () => {
  const page = useUserManagementPage();

  if (page.loading) return <div>加载中...</div>;
  if (page.error) return <div>错误: {page.error}</div>;

  return (
    <div>
      <UserManagementContent {...buildUserManagementContentProps(page)} />
      <UserManagementModals {...buildUserManagementModalProps(page)} />
    </div>
  );
};

export default UserManagement;

