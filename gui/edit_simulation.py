from copy import deepcopy
from pprint import pprint, pformat
from PyQt5 import Qt, QtGui, QtWidgets, uic
import sys
import IAMS.helper as h
import json
from sim_tree import *

class edit_simulation_window(QtWidgets.QDialog):
    def __init__(self, parent=None, sim=None, sim_name = None ):
        super().__init__(parent)
        
        if sim is None:
            return

        uic.loadUi("edit_simulation.ui", self)

        if sim_name is not None:
            self.findChild(QtWidgets.QGroupBox, "gb_simulation_listing").setTitle("Simulation "+sim_name)
            self.setWindowTitle("Edit Simulation "+sim_name+"...")
        else:
            self.findChild(QtWidgets.QGroupBox, "gb_simulation_listing").setTitle("Unspecified Simulation")
            self.setWindowTitle("Add new Simulation...")

        ## Save original simulation and a working copy
        self.orig_sim = deepcopy(sim)
        self.sim = deepcopy(sim)


        self.findChild(QtWidgets.QPushButton, "button_add_parameter").clicked.connect(
            self.add_parameter
        )

        ## Load entries into simulation edit list
        for k,v in self.sim.items():
            self.add_sim_row(k,v)

    def add_sim_row(self, key, val):
        if isinstance(val, dict) and val.get("iterate_over", False): # Multiple Simulations
            self.add_parameter(True, str(key), str(val["value"]))
        else:
            self.add_parameter(False, str(key), str(val))

    def add_parameter(self, iterate_flag=None, name=None, value=None):
        ## Get layout to insert to
        gl = self.findChild(QtWidgets.QGridLayout, "gl_parameters")
        insert_row_number = gl.rowCount() ## Starts indexing at 0 -> hence inserting at rowCount goes one beyond

        # Construct widgets
        remove_button = QtWidgets.QToolButton()
        remove_button.setText("X")
        remove_button.clicked.connect(lambda _: self.remove_parameter_row(insert_row_number))
        iterate_hl_box = QtWidgets.QHBoxLayout()
        iterate_check_box = QtWidgets.QCheckBox()
        if iterate_flag is not None and iterate_flag:
            iterate_check_box.setChecked(True)
        iterate_check_box.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        iterate_hl_box.addWidget(iterate_check_box)
        name_line_edit = QtWidgets.QLineEdit(str(name) if name is not None else "")
        value_line_edit = QtWidgets.QLineEdit(str(value) if value is not None else "")

        # Add widgets to layout
        gl.addWidget(remove_button   , insert_row_number , 0)
        gl.addLayout(iterate_hl_box  , insert_row_number , 1)
        gl.addWidget(name_line_edit  , insert_row_number , 2)
        gl.addWidget(value_line_edit , insert_row_number , 3)
    def remove_parameter_row(self, i):
        gl = self.findChild(QtWidgets.QGridLayout, "gl_parameters")
        gl.itemAtPosition(i,0).widget().deleteLater()
        gl.itemAtPosition(i,1).takeAt(0).widget().deleteLater()
        gl.itemAtPosition(i,2).widget().deleteLater()
        gl.itemAtPosition(i,3).widget().deleteLater()
    def get_row_number_by_name(self, name):
        gl = self.findChild(QtWidgets.QGridLayout, "gl_parameters")
        for i in range(1,gl.rowCount()): ## Start at 1 because 0 is headers
            if name == gl.itemAtPosition(i, 2).widget().text():
                return i
        return None
        print('in get_row_by_name')
    def return_current_simulation(self):
        d = dict()
        gl = self.findChild(QtWidgets.QGridLayout, "gl_parameters")
        for i in range(1,gl.rowCount()): ## Start at 1 because 0 is headers
            key_slot = gl.itemAtPosition(i, 2)
            if key_slot is None: ## Deleted row -> doesn't contain any data -> can be skipped
                continue
            key = key_slot.widget().text()
            val = gl.itemAtPosition(i,3).widget().text()
            try:
                val = eval(val)
            except (NameError, SyntaxError): ## Understand val now as string because it cannot be evaluated as python code
                print(f'Understand {key} as string, rather than as to be evaluated!')
                val = str(val)
            iterate_over = gl.itemAtPosition(i,1).takeAt(0).widget().isChecked()
            if iterate_over and not hasattr(val, "__iter__"):
                iterate_over = False
                raise RuntimeWarning("Want to iterate over something that isn't iterable. Overwriting the iterate_over parameter!")
            if iterate_over:
                d[key] = {'iterate_over':True, 'value': val}
            else:
                d[key] = val
        return d

    @staticmethod ## Call signature: edit_simulation_window.get_edited_simulation(...)
    def get_edited_simulation(sim=None, sim_name = None, parent=None):
        dialog = edit_simulation_window(sim=sim, sim_name = sim_name, parent=parent)
        result = dialog.exec_()
        if result == QtWidgets.QDialog.Accepted:
            return_sim = dialog.return_current_simulation()
        else:
            return_sim = dialog.orig_sim
        return return_sim, result == QtWidgets.QDialog.Accepted
