import json
import numpy as np
from copy import deepcopy
from pprint import pprint
from PyQt5 import Qt, QtGui, QtWidgets, uic
from IAMS.helper import write_queued_experiments

SIM_TREE_ROOT_NAME = "Simulations"

class sim_tree_node_PyQt(Qt.QStandardItem):
    def __init__(self, txt):
        super().__init__()
        self.setEditable(False)
        self.setText(txt)


class sim_tree_node_encoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "reprJSON"):  ## Handle sim tree
            return o.reprJSON()
        elif isinstance(o, np.ndarray):  ## Handle sim tree
            return o.tolist()
        else:
            return json.JSONEncoder.default(self, o)


class sim_tree_node:
    def __init__(self, list_or_dict=None, parent=None, index=None, nameHint=None):
        self.parent = parent
        self.children = []
        self.nameHint = nameHint
        if nameHint is None:
            self.name = (
                (self.parent.name if self.parent is not None else "")
                + ("." if self.parent is not None and self.parent.name != "" else "")
                + (str(index) if index is not None else "")
            )
        else:
            self.name = self.nameHint
        if self.name == "":  ## Root list
            self.name = SIM_TREE_ROOT_NAME

        if list_or_dict is None:
            self.data = None
            self.is_multiple_simulations = False
        elif isinstance(list_or_dict, dict):
            self.data = deepcopy(list_or_dict)
            self.is_multiple_simulations = self.contains_iterate_over()
            if self.is_multiple_simulations:
                self.name += " " + self.expand_data()
        elif isinstance(list_or_dict, list):
            self.children = [
                sim_tree_node(e, self, index=i + 1, nameHint=f"{i+1}")
                for i, e in enumerate(list_or_dict)
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
        for k, v in self.data.items():
            ## Handle non-iterate over dicts
            if isinstance(v, dict) and not v.get("iterate_over", False): 
                self.data[k] = v["value"]
        iterate_over_key = None
        for k, v in self.data.items():
            if isinstance(v, dict) and v.get("iterate_over", False):
                iterate_over_key = k
                break
        assert iterate_over_key is not None
        for i, val in enumerate(self.data[iterate_over_key]["value"]):
            sim_dir = deepcopy(self.data)
            sim_dir[iterate_over_key] = val
            if self.nameHint is not None:
                name_hint = f"{self.nameHint}, {iterate_over_key}={val}"
            else:
                name_hint = f"{iterate_over_key}={val}"
            self.children.append(
                sim_tree_node(sim_dir, parent=self, index=i + 1, nameHint=name_hint)
            )

        min_val = min(self.data[iterate_over_key]["value"])
        max_val = max(self.data[iterate_over_key]["value"])
        s = iterate_over_key + f" [{min_val}, {max_val}]"
        return s

    def load_json_into_node(self, json_path):  ## Assumes a script generated queue file
        assert json_path.endswith(".json")
        with open(json_path, "r") as f:
            l = json.load(f)
        new_tree = sim_tree_node(l, parent=None)  ## Instantiate root node
        self.__dict__.update(
            new_tree.__dict__
        )  ## This is a massive cheat, but apparently works to replace the current self with a new self

    def reprJSON(self):
        return {
            "parent"                  : None,  # Has to be redone in loading
            "data"                    : self.data,
            "name"                    : self.name,
            "is_multiple_simulations" : self.is_multiple_simulations,
            "children"                : [c.reprJSON() for c in self.children],
            "nameHint"                : self.nameHint,
        }

    def save_sim_tree_to_json(self, sim_tree_dump_path):
        d = self.__dict__
        with open(sim_tree_dump_path, "w") as f:
            json.dump(d, f, indent=4, cls=sim_tree_node_encoder)

    def load_from_dict(self, d, parent=None):
        self.parent = parent
        self.data = d["data"]
        self.name = d.get("name", "")
        self.nameHint = d["nameHint"]
        self.is_multiple_simulations = d["is_multiple_simulations"]
        self.children = [
            sim_tree_node().load_from_dict(dd, parent=self) for dd in d["children"]
        ]
        return self

    def load_sim_tree_from_json(self, sim_tree_dump_path):
        assert sim_tree_dump_path.endswith(".simtree")
        with open(sim_tree_dump_path, "r") as f:
            d = json.load(f)
        self.load_from_dict(d)

    def save_flattened_json_of_children(self, json_path):
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
            new_tree = sim_tree_node(new_sim, parent=self.parent, nameHint=self.nameHint)
            ## Overwrite oneself with new simulation
            self.__dict__.update(new_tree.__dict__) 
        else:
            for c in self.children:
                c.replace_sim_by_name(name, new_sim)

    def remove_sim_by_name(self, name):
        self.children = [c for c in self.children if c.name != name]
        for c in self.children:
            c.remove_sim_by_name(name)

    def get_all_names(self):
        ret = [self.name]
        ret.extend([c.get_all_names() for c in self.children])
        return ret
    
    def get_full_name_hint_from_dict(self, d):
        assert isinstance(d, dict)
        s = ""
        for k, v in d.items():
            if not (isinstance(v, dict) and v.get("iterate_over", False)):
                s += f"{k}={v}, "
        for k, v in d.items():
            if isinstance(v, dict) and v.get("iterate_over", False):
                min_val = min(v["value"])
                max_val = max(v["value"])
                s += f"{k} [{min_val}, {max_val}], "
        s=s[:-2]
        if s in (self.parent.get_all_names() if self.parent is not None else self.get_all_names()):
            s+=' (new)'
        return s

    def insert_at_name(self, name, new_sim):
        if name is None or name == SIM_TREE_ROOT_NAME:  ## Handle insert on root level
            new_tree = sim_tree_node(
                new_sim,
                parent=self.parent,
                index=len(self.children) + 1,
                nameHint=self.get_full_name_hint_from_dict(new_sim),
            )
            self.children.append(new_tree)
            return new_tree.name

        if name == self.name:
            name_hint = self.get_full_name_hint_from_dict(new_sim)
            new_tree = sim_tree_node(
                new_sim,
                parent=self.parent,
                index=len(self.children) + 1,
                nameHint=name_hint,
            )
            self.parent.children.append(new_tree)
            return new_tree.name
        else:
            for c in self.children:
                ret_val = c.insert_at_name(name, new_sim)
                if ret_val is not None:
                    return ret_val

    def insert_below_name(self, name, new_sim):
        if name is None:  ## Handle insert on root level
            name = ""
        if name == self.name:
            new_tree = sim_tree_node(
                new_sim,
                parent=self,
                index=len(self.children) + 1,
                nameHint=self.nameHint,
            )
            self.children.append(new_tree)
            return new_tree.name
        else:
            for c in self.children:
                ret_val = c.insert_below_name(name, new_sim)
                if ret_val is not None:
                    return ret_val

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
