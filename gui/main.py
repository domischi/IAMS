from pprint import pprint, pformat
from PyQt5 import Qt, QtGui, QtWidgets, uic
import sys
import IAMS.helper as h
import json
from sim_tree import *


class sim_list_item(
    Qt.QStandardItem
):  ## Either a simulation, or a grid-search simulation
    def __init__(self, txt, sim):
        super().__init__()
        self.setEditable(False)
        self.setText(txt)
        if type(sim) == list:
            self.sim = None
        elif type(sim) == dict:
            self.sim = sim  # TODO currently there is no way of assesing this data
        else:
            raise RuntimeError


class main_window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)
        self.show()
        self.sim_tree = sim_tree_node()
        self.findChild(QtWidgets.QPushButton, "button_add_sims").clicked.connect(
            self.add_simulations
        )
        self.findChild(QtWidgets.QPushButton, "button_run_sims").clicked.connect(
            self.run_simulations
        )
        self.findChild(QtWidgets.QPushButton, "button_edit_sims").clicked.connect(
            self.edit_simulations
        )
        self.findChild(QtWidgets.QLabel, "SelectedSimInfo")
        self.actionOpen.triggered.connect(self.load_simulations)
        self.actionSave.triggered.connect(self.save_simulations)
        self.actionSave_As.triggered.connect(self.save_simulations_as)
        self.actionExit.triggered.connect(self.exit)

        self.simulation_list_tree_view = self.findChild(
            QtWidgets.QTreeView, "SimulationTreeView"
        )
        self.simulation_list_tree_view.setHeaderHidden(True)
        self.simulation_list_tree_view.clicked.connect(self.update_sim_details)

        self.last_saved_to = None
        self.unsaved_changes = False
        self.load_file("queue.json")
        self.selected_sim_name = None

    def save_simulations(self):
        if self.last_saved_to is not None:
            self.save_to_file(self.last_saved_to)
        else:
            self.save_simulations_as()

    def save_simulations_as(self):
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("json")
        filedialog.setNameFilter("Simulation File (*.json);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        selected = filedialog.exec()
        if selected:
            filename = filedialog.selectedFiles()[0]
        else:
            return
        if filename == "":
            logger.debug("No file name selected.")
            return
        self.save_to_file(filename)

    def save_to_file(self, path):
        self.last_saved_to = path
        self.unsaved_changes = False
        self.sim_tree.save_json_of_children(path)

    def load_simulations(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Simulation...",
            "",
            "Simulation Files (*.json);;All Files (*)",
            options=options,
        )
        if fileName and fileName.endswith(".json"):
            self.load_file(fileName)

    def load_file(self, filename):
        with open(filename, "r") as f:
            l = json.load(f)
        if type(l) == list:
            self.sim_tree.load_json_into_node("queue-orig.json")
            self.rebuild_sim_tree()
        else:
            logger.error(
                "Tried to load a simulation lists file that isn't a list. Ignoring it..."
            )

    def rebuild_sim_tree(self):
        tm = self.sim_tree.get_pyqt_tree_model()
        self.simulation_list_tree_view.setModel(tm)
        self.simulation_list_tree_view.expandAll()

    def update_sim_details(self):
        clicked_sim_name = self.simulation_list_tree_view.selectedIndexes()[0].data()
        self.selected_sim_name = clicked_sim_name
        sim_data = self.sim_tree.get_data_by_name(clicked_sim_name)
        txt = "(No valid selection)"
        if isinstance(sim_data, list):
            txt = "(Multiple experiments in this list, no clear common denominator)"
        elif isinstance(sim_data, dict):
            txt = pformat(sim_data)
        else:
            raise RuntimeWarning(f"Didn't understand {type(sim_data)} to display")
        self.findChild(QtWidgets.QLabel, "SelectedSimInfo").setText(txt)

    def run_simulations(self):
        print("in run_simulations")

    def edit_simulations(self):
        print("in edit_simulations")

    def add_simulations(self):
        print("in add_simulations")

    def exit(self):
        print("in exit")
        self.close()


def expand_node(s, node, modifier=""):
    if type(s) == dict:
        node.appendRow(sim_list_item(f"Sim {modifier[:-1]}", s))
    if type(s) == list:
        if len(s) == 1:
            expand_node(s[0], node, modifier=modifier)
        else:
            node2 = sim_list_item(f"Sims {modifier[:-1]}", s)
            for i, ss in enumerate(s):
                expand_node(ss, node2, modifier=modifier + f"{i+1}.")
            node.appendRow(node2)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = main_window()
    sys.exit(app.exec_())
