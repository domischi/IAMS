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
from IAMS.runners.SpringBoxRunner import run_all_dask_local

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
    def run_cluster(self):
        print('cluster')
        self.close()
    def run_aws(self):
        print('aws')
        self.close()
    def cancel(self):
        print('cancel')
        self.close()
