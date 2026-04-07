import { useEffect } from 'react';
import { shouldClearMismatchedDepartment } from '../utils/userDirectorySelection';

export const useManagedDepartmentReset = ({
  companyId,
  departmentId,
  departments,
  resetDepartment,
}) => {
  useEffect(() => {
    if (
      shouldClearMismatchedDepartment({
        companyId,
        departmentId,
        departments,
      })
    ) {
      resetDepartment();
    }
  }, [companyId, departmentId, departments, resetDepartment]);
};
