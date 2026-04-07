from .transfer_phase_6_start_ragflow_ops import start_ragflow_containers
from .transfer_phase_6_start_ragflowauth_ops import start_ragflowauth_containers


def start_restore_phase_6(self):
    ragflowauth_reason = start_ragflowauth_containers(self)
    start_ragflow_containers(self)
    return ragflowauth_reason
