from .transfer_phase_1_3_ops import run_restore_phases_1_to_3
from .transfer_phase_4_5_ops import run_restore_phases_4_and_5


def run_restore_phases_1_to_5(self, *, log_to_file, messagebox, tempfile, tarfile, subprocess, time, os):
    run_restore_phases_1_to_3(
        self,
        log_to_file=log_to_file,
        messagebox=messagebox,
        tempfile=tempfile,
        tarfile=tarfile,
        subprocess=subprocess,
        time=time,
        os=os,
    )
    run_restore_phases_4_and_5(
        self,
        log_to_file=log_to_file,
        messagebox=messagebox,
        tempfile=tempfile,
        tarfile=tarfile,
        subprocess=subprocess,
        time=time,
        os=os,
    )
