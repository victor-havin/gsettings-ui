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

class GSettingsEditor(ttk.Frame):
    """
    GSettingsEditor dialog.
    It gets created on top of the tree view frame and
    does the key data editing.
    """

    # Constructor
    def __init__(self, parent):
        super().__init__(parent)
        self.gi_value: GiValue = None
        self.gi_key: GiKey = None
        self.root = parent.winfo_toplevel()
        self.process_data(self.root)
        self.do_layout(parent)      
        self.place()  
        self.place_after_id = None
    
    # Destructor
    def destroy(self):
        if self.place_after_id:
            self.after_cancel(self.place_after_id)
        super().destroy()

    # Layout manager
    def do_layout(self, parent):
        # Add widgets

        self.bind_all("<Key>", self.key_handle)
        self.info_frame = ttk.Frame(self)
        self.label_info = tk.Label(self.info_frame, justify="left")
        self.label_info.configure(text=f"Schema: {self.gi_key.get_schema_name()}\nKey: {self.gi_key.get_key_name()}")
        default_value = self.gi_key.get_default_value()
        if default_value:
            self.label_info.configure(text=self.label_info["text"] + f"\nDefault: {get_defaultvalue(self.root.tree, default_value, self.gi_value)}")
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
            self.edit_value = tk.Entry(self.edit_frame, width=60)
            self.edit_value.insert(tk.END, str(self.gi_value.get_value()))
        self.edit_value.pack(side=tk.LEFT, fill=tk.X)
        self.edit_value.focus_set()
        self.edit_value.bind("<Escape>", self.reject_change)
        self.ok_frame = tk.Frame(self, height=30)
        self.ok_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.button_ok = tk.Button(self.ok_frame, text="OK", command=self.accept_change)
        self.button_ok.pack(side=tk.RIGHT)
        self.button_cancel = tk.Button(self.ok_frame, text="Cancel", command=self.reject_change)
        self.button_cancel.pack(side=tk.RIGHT)
        self.message_label = tk.Label(self)
        self.message_label.pack(side=tk.BOTTOM, fill=tk.X)

    def key_handle(self, event):
        if isinstance(event.widget, ttk.Treeview):
            return
        if event.keysym == 'Return':
            if event.widget is self.button_cancel:
                self.reject_change()
            else:
                self.accept_change()
        elif event.keysym == 'Escape':
            self.reject_change()
   
    # Get data from the parent
    def process_data(self, root):
        tree = root.tree
        gi_dict = root.gi_dict
        item = tree.focus()
        self.gi_key, self.gi_value = gi_dict.get_keyvalue(item)
                    
    # Rebuild tree item
    # Very cool algorithm that gathers a variant from the 
    # key subtree.
    def rebuild_item(self, item_id):
        tree : ttk.Treeview = self.root.tree
        
        gi_dict : GiDict = self.root.gi_dict
        gi_key, gi_value = gi_dict.get_keyvalue(item_id) 
        root = gi_value.get_key_id()
        data = self.gather_variant(tree, gi_dict, root)
        gi_variant = GlVariant.AssureVariant(gi_key.key_type,data)
        return gi_variant
    
    # Recursive variant gathereing
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
        
    # Accept change
    def accept_change(self):
        is_ok = True
        tree = self.root.tree
        location = self.root.location
        selected_item = tree.focus()
        if self.gi_value.get_value() == None:
            # ToDo: Create new value here.
            self.create_value(selected_item)
        new_value = self.edit_value.get()
        try:
            tree.item(selected_item, values=new_value)
            if self.gi_value.get_type() == bool and new_value == 'False':
                new_value = False
            self.gi_value.set_value(self.gi_value.get_type()(new_value))
            schema_name = self.gi_key.get_schema_name()
            key_name = self.gi_key.get_key_name()
            schema = self.root.schema_source.lookup(schema_name, False)
            if(schema):
                variant = self.rebuild_item(selected_item)
                if location:
                    settings = Gio.Settings.new_with_path(schema_name, location)
                else:
                    settings = Gio.Settings.new(schema_name)
                settings.set_value(key_name, variant)
        except Exception as e:
            error_msg = f"{e}";
            self.message_label.configure(text=e)
            is_ok = False
        if is_ok:
            self.destroy()
        return "break"
            
    def reject_change(self, even=None):
        self.destroy()
        return "break"

    def create_value(self, item):
        tree = self.root.tree
        gi_dict = self.root.gi_dict
        key,val = gi_dict.get_keyvalue(item)
        vt_str = key.get_type()
        if(vt_str in GlVariant.base_type_sig):
            data = GlVariant.new_data(vt_str)
            val = GiValue.factory(key, data, vt_str)
            key.set_value(val)
        
            
    # Find root key for a data item
    def find_root(self, item):
        tree = self.root.tree
        dict = self.root.gi_dict
        while not isinstance(dict[item], GiKey):
            item = tree.parent(item)
        return item
