from __future__ import annotations

from .models import Company, Department, Employee


def build_org_tree(
    *,
    companies: list[Company],
    departments: list[Department],
    employees: list[Employee],
) -> list[dict]:
    company_by_id = {item.company_id: item for item in companies}
    department_by_id = {item.department_id: item for item in departments}
    children_by_parent: dict[int, list[dict]] = {}
    roots_by_company: dict[int, list[dict]] = {}
    people_by_department: dict[int, list[dict]] = {}
    people_by_company: dict[int, list[dict]] = {}

    for department in departments:
        node = build_department_node(department)
        if department.parent_department_id is None:
            roots_by_company.setdefault(int(department.company_id or 0), []).append(node)
        else:
            children_by_parent.setdefault(department.parent_department_id, []).append(node)

    for employee in employees:
        company = company_by_id.get(int(employee.company_id or 0))
        if company is None:
            raise RuntimeError(f"org_employee_company_missing:{employee.employee_user_id}")
        department = None
        if employee.department_id is not None:
            department = department_by_id.get(employee.department_id)
            if department is None:
                raise RuntimeError(f"org_employee_department_missing:{employee.employee_user_id}")
        node = build_employee_node(employee, company=company, department=department)
        if employee.department_id is None:
            people_by_company.setdefault(company.company_id, []).append(node)
        else:
            people_by_department.setdefault(employee.department_id, []).append(node)

    def attach_children(nodes: list[dict]) -> list[dict]:
        attached: list[dict] = []
        for node in nodes:
            child_nodes = children_by_parent.get(node["id"], [])
            node["children"] = attach_children(child_nodes) + people_by_department.get(node["id"], [])
            attached.append(node)
        return attached

    tree: list[dict] = []
    for company in companies:
        root_children = roots_by_company.get(company.company_id, [])
        tree.append(
            {
                "id": company.company_id,
                "node_type": "company",
                "name": company.name,
                "path_name": company.name,
                "source_key": company.source_key,
                "company_id": company.company_id,
                "department_id": None,
                "parent_department_id": None,
                "level_no": 1,
                "source_department_id": None,
                "employee_user_id": None,
                "email": None,
                "employee_no": None,
                "department_manager_name": None,
                "is_department_manager": False,
                "created_at_ms": company.created_at_ms,
                "updated_at_ms": company.updated_at_ms,
                "children": attach_children(root_children) + people_by_company.get(company.company_id, []),
            }
        )
    return tree


def build_department_node(department: Department) -> dict:
    return {
        "id": department.department_id,
        "node_type": "department",
        "name": department.name,
        "path_name": department.path_name,
        "source_key": department.source_key,
        "company_id": department.company_id,
        "department_id": department.department_id,
        "parent_department_id": department.parent_department_id,
        "level_no": department.level_no,
        "source_department_id": department.source_department_id,
        "employee_user_id": None,
        "email": None,
        "employee_no": None,
        "department_manager_name": None,
        "is_department_manager": False,
        "created_at_ms": department.created_at_ms,
        "updated_at_ms": department.updated_at_ms,
        "children": [],
    }


def build_employee_node(
    employee: Employee,
    *,
    company: Company,
    department: Department | None,
) -> dict:
    parent_path = department.path_name if department is not None else company.name
    return {
        "id": employee.employee_id,
        "node_type": "person",
        "name": employee.name,
        "path_name": f"{parent_path} / {employee.name}",
        "source_key": employee.source_key,
        "company_id": employee.company_id,
        "department_id": employee.department_id,
        "parent_department_id": employee.department_id,
        "level_no": (department.level_no + 1) if department is not None else 2,
        "source_department_id": None,
        "employee_user_id": employee.employee_user_id,
        "email": employee.email,
        "employee_no": employee.employee_no,
        "department_manager_name": employee.department_manager_name,
        "is_department_manager": employee.is_department_manager,
        "created_at_ms": employee.created_at_ms,
        "updated_at_ms": employee.updated_at_ms,
        "children": [],
    }
