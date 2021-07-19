from pprint import pprint, pformat
from PyQt5 import Qt, QtGui, QtWidgets, uic, QtCore
import sys
import IAMS.helper as h
import IAMS.runners.runner_helper as rh
import json
from sim_tree import *
from edit_simulation import edit_simulation_window
from run_simulation import run_simulation_window

DEFAULT_SIM_DICT = dict()


class main_window(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("main.ui", self)
        self.show()
        self.sim_tree = sim_tree_node()
        self.findChild(QtWidgets.QPushButton, "button_remove_sims").clicked.connect(
            self.remove_simulations
        )
        self.findChild(QtWidgets.QPushButton, "button_add_sims").clicked.connect(
            self.add_simulations
        )
        self.findChild(QtWidgets.QPushButton, "button_run_sims").clicked.connect(
            self.run_simulations
        )
        self.findChild(QtWidgets.QPushButton, "button_edit_sims").clicked.connect(
            self.edit_simulations
        )
        self.actionOpen.triggered.connect(self.load_simulations)
        self.actionSave.triggered.connect(self.save_simulations)
        self.actionSave_As.triggered.connect(self.save_simulations_as)
        self.actionSave_Queue_File.triggered.connect(self.save_flattened_simulations_as)
        self.actionExit.triggered.connect(self.exit)

        self.simulation_list_tree_view = self.findChild(
            QtWidgets.QTreeView, "SimulationTreeView"
        )
        self.simulation_list_tree_view.setHeaderHidden(True)

        self.last_saved_to = None
        self.selected_sim_name = None
        self.unsaved_changes = False
        self.standard_window_title = self.windowTitle()

        ## Define keyboard shortcuts
        # Remove simulations
        QtWidgets.QShortcut("Del", self).activated.connect(self.remove_simulations)
        QtWidgets.QShortcut("Backspace", self).activated.connect(self.remove_simulations)
        QtWidgets.QShortcut("-", self).activated.connect(self.remove_simulations)
        # Add simulations
        QtWidgets.QShortcut("+", self).activated.connect(self.add_simulations)
        # Save flattened simulations
        self.actionSave_Queue_File.setShortcut("Ctrl+Shift+S")
        # Save simulation tree
        self.actionSave.setShortcut("Ctrl+S")
        # Open simulation tree
        self.actionOpen.setShortcut("Ctrl+O")

        load_file_candidate = sys.argv[-1]
        if len(sys.argv) > 1 and (
            load_file_candidate.endswith(".json")
            or load_file_candidate.endswith(".simtree")
        ):
            self.load_file(load_file_candidate)
        else:
            self.load_simulations()

    def set_unsaved_changes(self, flag=True):
        if flag:
            self.unsaved_changes = True
            self.setWindowTitle(self.standard_window_title + "*")
        else:
            self.unsaved_changes = False
            self.setWindowTitle(self.standard_window_title)

    def save_simulations(self):
        if self.last_saved_to is not None:
            self.save_to_file(self.last_saved_to)
        else:
            self.save_simulations_as()

    def save_simulations_as(self):
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("simtree")
        filedialog.setNameFilter("Simulation Tree File (*.simtree);;All files (*.*)")
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
        self.set_unsaved_changes(False)
        self.sim_tree.save_sim_tree_to_json(path)

    def save_flattened_simulations_as(self):
        filedialog = QtWidgets.QFileDialog(self)
        filedialog.setDefaultSuffix("json")
        filedialog.setNameFilter("Queue File (*.json);;All files (*.*)")
        filedialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
        selected = filedialog.exec()
        if selected:
            filename = filedialog.selectedFiles()[0]
        else:
            return
        if filename == "":
            logger.debug("No file name selected.")
            return
        self.save_flattened_simulations_to_file(filename)

    def save_flattened_simulations_to_file(self, path):
        self.sim_tree.save_flattened_json_of_children(path)

    def load_simulations(self):
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Load Simulation...",
            "",
            "Simulation Tree (*.simtree);;Simulation Files (*.json);;All Files (*)",
            options=options,
        )
        if fileName:
            self.load_file(fileName)

    def load_file(self, filename):
        if self.unsaved_changes:
            qm = QtWidgets.QMessageBox
            ret = qm.warning(
                self,
                "Unsaved changes",
                "There are unsaved changes. Are you sure you want to load a new file?",
                qm.Yes | qm.No,
            )
            if ret != qm.Yes:
                return
        if filename.endswith(".json"):
           ## Assume regular queue file, as generated by a script
            with open(filename, "r") as f:
                l = json.load(f)
            if type(l) == list:
                self.sim_tree.load_json_into_node(filename)
                self.rebuild_sim_tree()
            else:
                logger.error(
                    "Tried to load a simulation lists file that isn't a list. Ignoring it..."
                )
        elif filename.endswith(".simtree"):
            ## Assume a simtree generated by the gui
            self.sim_tree.load_sim_tree_from_json(filename)
            self.rebuild_sim_tree()
            self.last_saved_to = filename
        else:
            raise RuntimeWarning(
                f"Didn't understand filetype of {filename} to load into program..."
            )

        self.SIM_TYPE = rh.get_simtype_from_simlist(self.sim_tree.flattened_simulations())
        self.findChild(QtWidgets.QGroupBox, "selected_sim_gb").setTitle(f"Selected {self.SIM_TYPE} Simulation")
        if self.SIM_TYPE.lower() == 'Springbox'.lower():
            # Groups and their order to display simulation
            self.sim_view_group_names = [
                "Time Integration Parameters",
                "Geometry Parameters",
                "Particle Parameters",
                "Interaction Parameters",
                "Data Storage Parameters",
                "Other Parameters",
                    ]
        elif self.SIM_TYPE.lower() == 'ANFDM'.lower():
            # Groups and their order to display simulation
            self.sim_view_group_names = [
                "Time Integration Parameters",
                "Geometry Parameters",
                "Network Physics Parameters",
                "Data Storage Parameters",
                "Other Parameters",
                    ]
        else:
            self.sim_view_group_names = [
                "Other Parameters",
                    ]

    def rebuild_sim_tree(self):
        tm = self.sim_tree.get_pyqt_tree_model()
        self.simulation_list_tree_view.setModel(tm)
        self.simulation_list_tree_view.expandAll()
        # These connections have to be redone after every change in the tree, and only after the tree has been loaded
        self.simulation_list_tree_view.selectionModel().selectionChanged.connect(
            self.update_sim_details
        )
        self.simulation_list_tree_view.activated.connect(self.edit_simulations)

    def update_selection(self, sim_name):
        qmodelindex_of_sim = (
            self.simulation_list_tree_view.model()
            .findItems(sim_name, QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)[0]
            .index()
        )
        self.simulation_list_tree_view.setCurrentIndex(qmodelindex_of_sim)

    ## Returns the Index corresponding to the correct group
    def get_group_association(self, s):
        if self.SIM_TYPE.lower()=='Springbox'.lower():
            return self.get_group_association_springbox(s)
        elif self.SIM_TYPE.lower()=='anfdm'.lower():
            return self.get_group_association_anfdm(s)
        else:
            return self.get_group_association_generic(s)
    def get_group_association_generic(self, s):
        return -1 ## Get sorted into other
    def get_group_association_springbox(self, s):
        ## Time parameters
        if s in ['T', 'dt']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'time' in s.lower())
        ## Geometry parameters
        if s in ['L', 'window_velocity', 'vx', 'x_0_circ', 'activation_fn_type', 'activation_circle_radius', 'v_circ']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'geom' in s.lower())
        ## Interaction parameters
        if s in ['activation_decay_rate', 'spring_cutoff','spring_lower_cutoff', 'spring_k', 'spring_k_rep', 'spring_r0', 'LJ_cutoff', 'LJ_eps', 'LJ_r0']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'interaction' in s.lower())
        ## Data storage parameters
        if s in ['SAVEFIG', 'savefreq_fig', 'savefreq_data_dump']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'data' in s.lower())
        ## Particles
        if s in ['n_part', 'const_particle_density', 'particle_density', 'm_init']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'particle' in s.lower())

        return -1 ## Get sorted into other
    def get_group_association_anfdm(self, s):
        ## Time parameters
        if s in ['T_tot', 'dt']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'time' in s.lower())
        ## Geometry parameters
        if s in ['Global_Geometry', 'AR_fr', 'AR_xy', 'UnitCell_Geo', 'lattice_dsrdr', 'lattice_shape', 'rounded', 'round_coeff']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'geom' in s.lower())
        ## Network Physics Parameters,
        if s in ['gamma', 'mass', 'illum_ratio', 'rhof', 'rhoi', 'rhoPower', 's0', 'tau_s']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'network' in s.lower())
        ## Data storage parameters
        if s in ['show_plots', 'plot_density_map', 'plot_full_positions', 'plot_velocity_map', 'plot_velocity_plot', 'dump_type', 'N_frame']:
            return next(i for i, s in enumerate(self.sim_view_group_names) if 'data' in s.lower())
        return -1 ## Get sorted into other

    ## Construct the simulation view for the main window
    def get_sim_view(self):
        sim_data = self.sim_tree.get_data_by_name(self.selected_sim_name)

        txt = "(No valid selection)"
        if isinstance(sim_data, list):
            qlabel = QtWidgets.QLabel("(Multiple experiments in this list, no clear common denominator)")
            return [qlabel]
        elif isinstance(sim_data, dict):
            ## Get the big layout sorted
            gbs = [QtWidgets.QGroupBox(n) for n in self.sim_view_group_names]
            vertical_spacer = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding) 

            ## Introduce the local layouts
            layouts = [QtWidgets.QGridLayout() for _ in range(len(gbs))]
            for gb, l in zip(gbs,layouts):
                gb.setLayout(l)

            ## Add items to the layouts
            for k, v in sim_data.items():
                if isinstance(v, dict) and v.get("iterate_over", False):
                    key = QtWidgets.QLabel(str(k))
                    val = QtWidgets.QLabel("Iterating over: "+str(v["value"]))
                    font = QtGui.QFont()
                    font.setBold(True)
                    key.setFont(font)
                    val.setFont(font)
                else:
                    key = QtWidgets.QLabel(str(k))
                    val = QtWidgets.QLabel(str(v))
                insert_group_index = self.get_group_association(k)
                c = layouts[insert_group_index].rowCount()
                layouts[insert_group_index].addWidget(key, c, 0)
                layouts[insert_group_index].addWidget(val, c, 1)

            return [*gbs, vertical_spacer]
        else:
            raise RuntimeWarning(f"Didn't understand {type(sim_data)} to display")
            qlabel = QtWidgets.QLabel("(No valid selection)")
            return [qlabel]


    def update_sim_details(self):
        ## Update selected sim
        try:
            clicked_sim_name = self.simulation_list_tree_view.selectedIndexes()[0].data()
        except:
            print("Didn't find a clicked sim name, ignoring it")
            return
        self.selected_sim_name = clicked_sim_name

        ## Get new widgets
        widgets = self.get_sim_view()

        ## Get the widgets that we want to address
        sim_gb = self.findChild(QtWidgets.QGroupBox, "selected_sim_gb")
        sim_view_layout = self.findChild(QtWidgets.QVBoxLayout, "sim_view_layout")

        ## Clear out view
        for i in reversed(range(sim_view_layout.count())): 
            sim_view_layout.removeWidget(sim_view_layout.itemAt(i).widget())
        
        ## Add new widgets
        for w in widgets:
            if isinstance(w, QtWidgets.QSpacerItem):
                sim_view_layout.addItem(w)
            else:
                sim_view_layout.addWidget(w)

    def run_simulations(self):
        if self.unsaved_changes:
            self.save_simulations()
        sim_status = run_simulation_window(sims=self.sim_tree)

    def edit_simulations(self):
        data_now = self.sim_tree.get_data_by_name(self.selected_sim_name)
        if isinstance(data_now, dict):  ## Can only edit structured simulations
            edited_sim, changed = edit_simulation_window.get_edited_simulation(
                data_now, self.selected_sim_name
            )
            if changed:
                self.sim_tree.replace_sim_by_name(self.selected_sim_name, edited_sim)
                if any(
                    [
                        isinstance(val, dict) and val.get("iterate_over", False)
                        for val in edited_sim.values()
                    ]
                ):
                    self.rebuild_sim_tree()
                self.set_unsaved_changes(True)
        self.update_sim_details()

    def add_simulations(self):
        if self.selected_sim_name is None or self.selected_sim_name == "" or self.selected_sim_name == SIM_TREE_ROOT_NAME:
            data_now = DEFAULT_SIM_DICT
        else:
            data_now = self.sim_tree.get_data_by_name(
                self.selected_sim_name
            )  ## Use currently selected simulation as starting point
        new_sim, non_empty = edit_simulation_window.get_edited_simulation(sim=data_now)
        if non_empty:
            new_name = self.sim_tree.insert_at_name(self.selected_sim_name, new_sim)
            self.rebuild_sim_tree()
            self.update_selection(new_name)  ## selects new element in treeview and should also update sim details
            self.set_unsaved_changes(True)

    def remove_simulations(self):
        if self.selected_sim_name is not None:
            self.sim_tree.remove_sim_by_name(self.selected_sim_name)
            self.rebuild_sim_tree()
            self.set_unsaved_changes(True)

    # Require overwrite in order to ensure program terminates via exit (asking user for confirmation of save)
    def closeEvent(self, evt):  
        self.exit()

    def exit(self):
        if self.unsaved_changes:
            qm = QtWidgets.QMessageBox
            ret = qm.warning(
                self,
                "Unsaved changes",
                "Unsaved Changes! Do you want to save now?",
                qm.Yes | qm.No,
            )
            if ret == qm.Yes:
                self.save_simulations()
                qm.information(
                    self, "Saved!", f"Saved changes to '{self.last_saved_to}'", qm.Ok
                )

        self.close()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = main_window()
    sys.exit(app.exec_())
