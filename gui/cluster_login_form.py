from copy import deepcopy
from pprint import pprint, pformat
from PyQt5 import Qt, QtGui, QtWidgets, uic
import sys
import IAMS.helper as h
import json
import os
import subprocess
import time
import pexpect
import tempfile
from IAMS.ssh_client import SSHClient, upload_directory
import paramiko


class cluster_login_form(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        uic.loadUi("cluster_login_form.ui", self)
        self.accepted = False

    def read_fields(self):
        return (
            self.findChild(QtWidgets.QLineEdit, "input_user").text(),
            self.findChild(QtWidgets.QLineEdit, "input_pass").text(),
            self.findChild(QtWidgets.QLineEdit, "input_mfa").text(),
        )

    @staticmethod  ## Call signature: edit_simulation_window.get_edited_simulation(...)
    def get_credentials(parent=None):
        dialog = cluster_login_form(parent=parent)
        result = dialog.exec_()
        if dialog.accepted:
            ret = dialog.read_fields()
        else:
            ret = (None, None)
        return ret, dialog.accepted

    def accept(self):
        self.accepted = True
        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    ssh = SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    for i in range(3):
        try:
            (user, password, mfa), res = cluster_login_form.get_credentials()
            if not res:
                continue
            ssh.totp = mfa
            #ssh.connect('localhost', port=22, username=user, password=password)
            ssh.duo_auth = True
            ssh.connect("login.hpc.caltech.edu", port=22, username=user, password=password)
            break
        except paramiko.AuthenticationException:
            print("Authentication didn't work! Retry")
    #upload_directory('./mv-folder', '/tmp/tmp/', ssh)
    cmds = [
        "ls -lh ~/",
    ]
    for cmd in cmds:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        output = stdout.readlines()
        print("> " + cmd)
        print("".join(output))
        print("\n")

    ssh.close()
