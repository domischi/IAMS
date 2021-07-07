from copy import deepcopy
from pprint import pprint, pformat
from PyQt5 import Qt, QtGui, QtWidgets, uic
import sys
import os
import time
import multiprocessing
import IAMS.helper as h
import json
from sim_tree import *
import paramiko
from IAMS.ssh_client import SSHClient, upload_directory, create_scratch_link
from IAMS.runners.SpringBoxRunner import run_all_dask_local, generate_cluster_submission
from cluster_login_form import cluster_login_form

def _execute_local(sim_list, nthreads):
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    if os.fork() != 0:
        return
    run_all_dask_local(sim_list, nthreads) 

class run_simulation_window(QtWidgets.QDialog):
    def __init__(self, parent=None, sims=None):
        super().__init__(parent)
        uic.loadUi("run_simulation.ui", self)
        self.findChild(QtWidgets.QPushButton, "button_run_local").clicked.connect(self.run_local)
        self.findChild(QtWidgets.QPushButton, "button_run_cluster").clicked.connect(self.run_cluster)
        self.findChild(QtWidgets.QPushButton, "button_run_aws").clicked.connect(self.run_aws)
        self.findChild(QtWidgets.QPushButton, "button_cancel").clicked.connect(self.cancel)
        self.sim_list = sims.flattened_simulations()
        self.findChild(QtWidgets.QLineEdit,"input_local_workers").setText(str(multiprocessing.cpu_count()))
        self.findChild(QtWidgets.QLineEdit,"input_local_workers").returnPressed.connect(self.run_local)
        self.findChild(QtWidgets.QLineEdit,"input_slurm_time").returnPressed.connect(self.run_cluster)
        self.exec()

    def run_local(self):
        nthreads=self.findChild(QtWidgets.QLineEdit,"input_local_workers").text()
        try:
            nthreads=int(nthreads)
        except ValueError:
            QtWidgets.QMessageBox.information(self, "Error!", f"Cannot understand {nthreads} as a number of workers. Has to be an integer!", QtWidgets.QMessageBox.Ok)
            return
        if nthreads<=0:
            QtWidgets.QMessageBox.information(self, "Error!", f"Number of workers has to be positive", QtWidgets.QMessageBox.Ok)
            return
        p = multiprocessing.Process(target=_execute_local, args=(self.sim_list, nthreads))
        p.start()
        p.join()
        QtWidgets.QMessageBox.information(self, "Started simulations", f"Successfully started local simulations with {nthreads} threads.", QtWidgets.QMessageBox.Ok)
        self.close()
    def run_cluster(self, *args, create_scratch_if_not_exits=True):
        slurm_time=self.findChild(QtWidgets.QLineEdit,"input_slurm_time").text()
        if not h.is_valid_slurm_time(slurm_time):
            QtWidgets.QMessageBox.information(self, "Error!", f"Not a valid specification for slurm time: {slurm_time}", QtWidgets.QMessageBox.Ok)
            return

        ssh = SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        for i in range(3): ## do a number of retries
            try:
                (user, password, mfa), res = cluster_login_form.get_credentials()
                if not res:
                    continue
                ssh.totp = mfa
                #ssh.connect('localhost', port=22, username=user, password=password)
                ssh.duo_auth = True
                ssh.connect('login.hpc.caltech.edu', port=22, username=user, password=password)
                break
            except paramiko.AuthenticationException:
                print("Authentication didn't work! Retry")

        ## Assure that we have the scratch link on the cluster ready for us to work with
        remote_file_path = '~/scratch/'
        if create_scratch_if_not_exits:
            remote_file_path = create_scratch_link(ssh)
        
        ## Generate files locally required for the simulation
        u = generate_cluster_submission(self.sim_list, user, slurm_time)

        ## Upload all files (using tar locally, upload via sftp, untar on cluster)
        upload_directory(f'./{u}', remote_file_path, ssh)

        ## Remove local files no longer requires
        os.system(f'rm -r {u}')

        ## Submit job
        cmds = [
                f'cd {remote_file_path}/{u}; sbatch submit.sh',
                ]
        for cmd in cmds:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            output = stdout.readlines()
            print('> '+cmd)
            print(''.join(output))

        ## Close ssh tunnel
        ssh.close()
        ## Close window
        self.close()

    def run_aws(self):
        print('aws')
        self.close()
    def cancel(self):
        print('cancel')
        self.close()
