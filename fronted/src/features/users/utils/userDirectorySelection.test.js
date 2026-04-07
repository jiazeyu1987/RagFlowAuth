import { filterDepartmentsByCompany, shouldClearMismatchedDepartment } from './userDirectorySelection';

describe('userDirectorySelection', () => {
  const departments = [
    { id: 11, name: 'QA', company_id: 1 },
    { id: 21, name: 'Ops', company_id: 2 },
    { id: 31, name: 'Shared', company_id: null },
  ];

  it('returns all departments when no company is selected', () => {
    expect(filterDepartmentsByCompany({ companyId: '', departments })).toEqual(departments);
  });

  it('filters company-scoped departments while keeping shared departments visible', () => {
    expect(filterDepartmentsByCompany({ companyId: '1', departments })).toEqual([
      { id: 11, name: 'QA', company_id: 1 },
      { id: 31, name: 'Shared', company_id: null },
    ]);
  });

  it('returns false when no department is selected', () => {
    expect(
      shouldClearMismatchedDepartment({
        companyId: '1',
        departmentId: '',
        departments,
      })
    ).toBe(false);
  });

  it('returns false when the selected department cannot be found', () => {
    expect(
      shouldClearMismatchedDepartment({
        companyId: '1',
        departmentId: '999',
        departments,
      })
    ).toBe(false);
  });

  it('returns false when the selected department belongs to the same company', () => {
    expect(
      shouldClearMismatchedDepartment({
        companyId: '1',
        departmentId: '11',
        departments,
      })
    ).toBe(false);
  });

  it('returns true when the selected department belongs to another company', () => {
    expect(
      shouldClearMismatchedDepartment({
        companyId: '1',
        departmentId: '21',
        departments,
      })
    ).toBe(true);
  });

  it('returns false when the department has no bound company', () => {
    expect(
      shouldClearMismatchedDepartment({
        companyId: '1',
        departmentId: '31',
        departments,
      })
    ).toBe(false);
  });
});
