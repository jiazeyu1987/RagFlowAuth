import { act, renderHook, waitFor } from '@testing-library/react';
import { useCallback, useState } from 'react';
import { useManagedDepartmentReset } from './useManagedDepartmentReset';

const useManagedDepartmentResetHarness = ({ departments }) => {
  const [companyId, setCompanyId] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const resetDepartment = useCallback(() => {
    setDepartmentId('');
  }, []);

  useManagedDepartmentReset({
    companyId,
    departmentId,
    departments,
    resetDepartment,
  });

  return {
    companyId,
    departmentId,
    setCompanyId,
    setDepartmentId,
  };
};

describe('useManagedDepartmentReset', () => {
  it('clears the selected department when it no longer belongs to the chosen company', async () => {
    const { result } = renderHook(() =>
      useManagedDepartmentResetHarness({
        departments: [{ id: 11, company_id: 2, name: 'Ops' }],
      })
    );

    act(() => {
      result.current.setCompanyId('1');
      result.current.setDepartmentId('11');
    });

    await waitFor(() => expect(result.current.departmentId).toBe(''));
  });

  it('preserves the selected department when it still belongs to the chosen company', async () => {
    const { result } = renderHook(() =>
      useManagedDepartmentResetHarness({
        departments: [{ id: 11, company_id: 1, name: 'Ops' }],
      })
    );

    act(() => {
      result.current.setCompanyId('1');
      result.current.setDepartmentId('11');
    });

    await waitFor(() => expect(result.current.departmentId).toBe('11'));
  });
});
