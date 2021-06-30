import json
import numpy as np
from copy import deepcopy
from pprint import pprint
from PyQt5 import Qt, QtGui, QtWidgets, uic
from IAMS.helper import write_queued_experiments


class sim_tree_node_PyQt(Qt.QStandardItem):
    def __init__(self, txt):
        super().__init__()
        self.setEditable(False)
        self.setText(txt)


class sim_tree_node:
    def __init__(self, list_or_dict=None, parent=None, index=None):
        self.parent = parent
        self.children = []
        self.name = (
            (self.parent.name if self.parent is not None else "")
            + ("." if self.parent is not None and self.parent.name != "" else "")
            + (str(index) if index is not None else "")
        )

        if list_or_dict is None:
            self.data = None
            self.is_multiple_simulations = False
        elif isinstance(list_or_dict, dict):
            self.data = deepcopy(list_or_dict)
            self.is_multiple_simulations = self.contains_iterate_over()
            if self.is_multiple_simulations:
                self.expand_data()
        elif isinstance(list_or_dict, list):
            self.children = [
                sim_tree_node(e, self, index=i + 1) for i, e in enumerate(list_or_dict)
            ]
            self.data = deepcopy(list_or_dict)
            self.is_multiple_simulations = True
        else:
            raise RuntimeError(
                f"Tried to construct a sim_tree_node with input type {type(list_or_dict)=}"
            )

    def contains_iterate_over(self):
        assert isinstance(self.data, dict)
        for k, v in self.data.items():
            if isinstance(v, dict) and v.get("iterate_over", False):
                return True
        return False

    def expand_data(self):
        iterate_over_key = None
        for k, v in self.data.items():
            if isinstance(v, dict) and v.get("iterate_over", False):
                iterate_over_key = k
                break
        assert iterate_over_key is not None
        for i, val in enumerate(self.data[iterate_over_key]["value"]):
            sim_dir = deepcopy(self.data)
            sim_dir[iterate_over_key] = val
            self.children.append(sim_tree_node(sim_dir, parent=self, index=i + 1))

    def load_json_into_node(self, json_path):
        assert json_path.endswith(".json")
        with open(json_path, "r") as f:
            l = json.load(f)
        new_tree = sim_tree_node(l, parent=None)  ## Instantiate root node
        self.__dict__.update(
            new_tree.__dict__
        )  ## This is a massive cheat, but apparently works to replace the current self with a new self

    def save_json_of_children(self, json_path, flatten=True):
        if self.is_multiple_simulations and not flatten:
            raise RuntimeError("Cannot store json of non-flattened simulations")
        l = self.flattened_simulations()
        write_queued_experiments(l, json_path)

    def flattened_simulations(self):
        l = []
        if self.is_multiple_simulations:
            l.extend([s for c in self.children for s in c.flattened_simulations()])
            return l
        else:
            return [self.data]

    def get_data_by_name(self, name):
        if name == self.name:
            return self.data
        else:
            for c in self.children:
                data = c.get_data_by_name(name)
                if data is not None:
                    return data
        return None
    def replace_sim_by_name(self, name, new_sim):
        if name == self.name:
            new_tree = sim_tree_node(new_sim, parent=self.parent)
            self.__dict__.update( new_tree.__dict__)  ## Overwrite oneself with new simulation
            self.name = name ## Because name get's overwritten with something unintelligible by the line above
        else:
            for c in self.children:
                c.replace_sim_by_name(name, new_sim)
    def insert_below_name(self, name, new_sim):
        if name is None: ## Handle insert on root level
            name=""
        if name == self.name:
            new_tree = sim_tree_node(new_sim, parent=self, index = len(self.children)+1) ## TODO with better naming convention -> fix this as it could lead to double usage of same name when items are added and deleted
            self.children.append(new_tree)
        else:
            for c in self.children:
                c.insert_below_name(name, new_sim)

    def __str__(self):
        s = "Sim"
        if self.is_multiple_simulations:
            s += "s"
        s += " "
        s += self.name
        return s

    def get_sub_trees(self):
        node = sim_tree_node_PyQt(self.name)
        for c in self.children:
            node.appendRow(c.get_sub_trees())
        return node

    def get_pyqt_tree_model(self):
        treeModel = Qt.QStandardItemModel()
        rootNode = treeModel.invisibleRootItem()
        rootNode.appendRow(self.get_sub_trees())
        return treeModel


if __name__ == "__main__":
    s = sim_tree_node()  ## Root node
    s.load_json_into_node("queue-orig.json")
    tm = s.get_pyqt_tree_model()
