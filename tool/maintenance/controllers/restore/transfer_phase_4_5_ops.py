from .transfer_phase_4_images_ops import run_restore_phase_4_images
from .transfer_phase_5_volumes_ops import run_restore_phase_5_volumes


def run_restore_phases_4_and_5(self, *, log_to_file, messagebox, tempfile, tarfile, subprocess, time, os):
    run_restore_phase_4_images(
        self,
        log_to_file=log_to_file,
        messagebox=messagebox,
        tempfile=tempfile,
        tarfile=tarfile,
        subprocess=subprocess,
        time=time,
        os=os,
    )
    run_restore_phase_5_volumes(
        self,
        log_to_file=log_to_file,
        messagebox=messagebox,
        tempfile=tempfile,
        tarfile=tarfile,
        subprocess=subprocess,
        time=time,
        os=os,
    )
