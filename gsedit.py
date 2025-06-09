"""
 gsettings editor
"""

# import tkinter
import tkinter as tk
from tkinter import ttk
# GIO_VERSION = "2.0"
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio
from gi.repository import GLib


# gimodel from gisettings-ui project
import gimodel
from gimodel import *

class GSettingsEditor(tk.Toplevel):

    def __init__(self, parent):
        super().__init__(parent)
        self.gi_value: GiValue = None
        self.gi_key: GiKey = None
        self.parent = parent
        self.process_data(self.parent)
        self.do_layout(self.parent)        
        
    def destroy(self):
        self.after_cancel(self.place)
        super().destroy()
        
    def do_layout(self, parent):
        # Setup window
        self.overrideredirect(True)
        self.title("GNOME GSettings Editor")
        self.wm_title = "gsettings_ui"
        self.place()
        #self.resizable(False, False)

        # Add widgets
        
        self.info_frame = tk.Frame(self)
        self.label_info = tk.Label(self.info_frame, justify="left")
        self.label_info.configure(text=f"Schema: {self.gi_key.get_schema_name()}\nKey: {self.gi_key.get_key_name()}")
        default_value = self.gi_key.get_default_value()
        if default_value:
            self.label_info.configure(text=self.label_info["text"] + f"\nDefault: {get_defaultvalue(parent.tree, default_value, self.gi_value)}")
        self.label_info.pack(side=tk.LEFT, fill=tk.X)
        self.info_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        self.edit_frame = tk.Frame(self)
        self.edit_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)
        self.edit_label = tk.Label(self.edit_frame, justify="left", text=f"Value : {self.gi_value.get_vtype()}  ")
        self.edit_label.pack(side=tk.LEFT)
        range = self.gi_key.get_range()
        if self.gi_value.get_type() is bool:
            # ComboBox for booleans and ranges
            self.select_range = tk.StringVar()
            self.edit_value = ttk.Combobox(self.edit_frame, values=("True", "False"), textvariable=self.select_range, state="readonly")
            self.select_range.set(str(self.gi_value.get_value()))
        elif range and range[0] == 'enum':
            self.select_range = tk.StringVar()
            self.edit_value = ttk.Combobox(self.edit_frame, values = range[1], textvariable=self.select_range, state="readonly")
            self.select_range.set(str(self.gi_value.get_value()))
        else:
            self.edit_value = tk.Text(self.edit_frame, height=1)
            self.edit_value.insert(tk.END, str(self.gi_value.get_value()))
        self.edit_value.pack(side=tk.LEFT, fill=tk.X)
        self.ok_frame = tk.Frame(self, height=30)
        self.ok_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.button_ok = tk.Button(self.ok_frame, text="OK", command=self.accept_change)
        self.button_ok.pack(side=tk.RIGHT)
        self.button_cancel = tk.Button(self.ok_frame, text="Cancel", command=self.destroy)
        self.button_cancel.pack(side=tk.RIGHT)
        self.message_label = tk.Label(self)
        self.message_label.pack(side=tk.BOTTOM, fill=tk.X)
        
    def place(self):
        x =  self.parent.tree_frame.winfo_rootx()
        y =  self.parent.tree_frame.winfo_rooty()
        w =  self.parent.tree_frame.winfo_width() 
        h =  self.parent.tree_frame.winfo_height() 
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.after(100, self.place)

    def show(self):
        self.transient(self.parent)
        self.wait_visibility(self)
        self.grab_set()
        self.focus_set()
        self.wait_window(self)

    def process_data(self, parent):
        tree = parent.tree
        gi_dict = parent.gi_dict
        item = tree.focus()
        self.gi_key, self.gi_value = gi_dict.get_keyvalue(item)
                    
    def rebuild_item(self, item_id):
        tree : ttk.Treeview = self.parent.tree
        
        gi_dict : GiDict = self.parent.gi_dict
        gi_key, gi_value = gi_dict.get_keyvalue(item_id) 
        root = gi_value.get_key_id()
        data = self.gather_variant(tree, gi_dict, root)
        gi_variant = GlVariant.AssureVariant(gi_key.key_type,data)
        return gi_variant
    
    def gather_variant(self, tree:ttk.Treeview, gi_dict:GiDict, next, container=False):
        gi_key, gi_value = gi_dict.get_keyvalue(next)
        vt_str = gi_value.get_vtype()
        if not gi_value.is_compound():
            return gi_value.get_value()
        else:
            # Debug
            children = [c for c in tree.get_children(next)]
            data = [gi_dict[c] for c in children]
        
            if vt_str.startswith('a{'):
                dict = {}
                for c in tree.get_children(next):
                    key = tree.item(c, "text")
                    val = self.gather_variant(tree, gi_dict, c, True)
                    dict[key] = val
                v = dict if container else GlVariant(vt_str, dict)
                
            elif vt_str[0] in "a[(":
                #list = [self.gather_variant(tree, gi_dict, id) for id in tree.get_children(next)]
                list = []
                for c in tree.get_children(next):
                    val = self.gather_variant(tree, gi_dict, c, True)
                    list.append(val)
                v = list if container else GlVariant(vt_str, list)
                
            elif vt_str[0] in "v@":
                v = self.gather_variant(tree, gi_dict, tree.get_children(next)[0])
                
            elif vt_str[0] == 'm':
                # Nullale 
                children = tree.get_children(next)
                if len(children) == 0:
                    vt = GLib.VariantType(vt_str)
                    v = GLib.Variant.new_maybe(vt, None)
                else:
                    for node in children:
                        self.gather_variant(tree, gi_dict, node)
            else:
                # everything else
                val = gi_dict.get_value(next).get_value()
                v = val if container else GlVariant(vt_str, val)
                
            if gi_value.is_variant():
                v = GlVariant(vt_str, v)
            return v
        

    def accept_change(self):
        is_ok = True
        tree = self.parent.tree
        selected_item = tree.focus()
        if self.gi_value.get_value() == None:
            # ToDo: Create new value here.
            self.destroy()
            return
        if isinstance(self.edit_value, tk.Text):
            new_value = self.edit_value.get("1.0", "end-1c") 
        else:
            new_value = self.edit_value.get()
        try:
            tree.item(selected_item, values=new_value)
            self.gi_value.set_value(self.gi_value.get_type()(new_value))
            schema_name = self.gi_key.get_schema_name()
            key_name = self.gi_key.get_key_name()
            schema = self.parent.schema_source.lookup(schema_name, False)
            if(schema):
                variant = self.rebuild_item(selected_item)
                settings = Gio.Settings.new(schema_name)
                settings.set_value(key_name, variant)
        except Exception as e:
            error_msg = f"{e}";
            self.message_label.configure(text=e)
            is_ok = False
        if is_ok:
            self.destroy()


    def find_root(self, item):
        tree = self.parent.tree
        dict = self.parent.gi_dict
        while not isinstance(dict[item], GiKey):
            item = tree.parent(item)
        return item
    