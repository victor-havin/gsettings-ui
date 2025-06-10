"""
gsettings-ui
A simple GUI application for exploring GNOME settings schemas.

This tool displays GNOME settings in a structured tree of schemas and keys, 
allowing users to browse default schemas or open relocatable schemas from 
a specified path. 

The search box in the button bar provides incremental search functionality, 
filtering schemas and keys as the search string is entered.

Overall, the schema browsing experience is similar to the functionality 
offered by the GNOME `gsettings` tool, but with a graphical interface.

Implemented in Python 3.
- Uses `tkinter` (included with Python 3).
- Uses `gi` (installable via `pip` or `apt-get`).

On externally managed systems install dependencies with apt:
```bash
sudo apt install python3-tkinter python3-gi

To start the application:
```bash
python3 gsettings-ui.py
"""

""" Import section """
# import from Python
from os import path
from enum import Enum

# GIO_VERSION = "2.0"
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio

# tkinter
import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import tkinter.font as tkFont

# gimodel from gisettings-ui project
import gimodel
from gimodel import *

import gsedit
from gsedit import GSettingsEditor

""" Implementation starts here """
class SearchResults(list):
    """
    A class to hold search results.
    It extends the built-in list to provide additional functionality if needed.
    """
    def __init__(self, *args, **kwargs):
        # Costructor for SearchResults
        self.current_index: int = 0  # Current index in the search results
        super().__init__(*args, **kwargs)
    def next(self):
        #Get the next search result.
        if self.current_index < len(self) - 1:
            self.current_index += 1
        return self[self.current_index] if self else None
    def previous(self):
        #Get the previous search result.
        if self.current_index > 0:
            self.current_index -= 1
        return self[self.current_index] if self else None
    def current(self):
        #Get the current search result.
        return self[self.current_index] if self else None
    def reset(self):
        #Reset the search results.
        self.current_index = 0
        self[:] = []  # Clear the list

class GSettingsViewer(tk.Tk):
    """
    A class to create a GUI application for viewing GNOME GSettings schemas.
    It inherits from tk.Tk and uses Gio to access GSettings schemas.
    It provides a treeview to display schemas and their keys, and a text pane to show details.
    """
    class NodeType(Enum):
        """
        An enumeration for node types in the treeview.
        It can be used to differentiate between schema, key, and value nodes.
        """
        SCHEMA = 1
        KEY = 2
        VALUE = 3
        COMPOUND = 4

    """ Special functions """
    ## Class constructor
    ## Initializes the main window, sets up the layout, and loads GSettings schemas.    
    def __init__(self):
        super().__init__()
        # Constants
        self.MAX_ASCII : int = 256          # Max ASCII key code
        self. SEARCH_DELAY :int = 300       # At least SEARCH_DELAY between searches
        self.mydir = path.dirname(__file__)
        self.schema_source = None
        self.schema_types = ("Installed", "Relocatable") 
        self.schema_type = tk.StringVar()
        self.location = None
        # Search results
        self.search_results : SearchResults = SearchResults()
        self.after_id = 0  # ID for the after method used in search
        # Gi data dictionary
        self.gi_dict : GiDict = GiDict()
        # Editor
        self.gsedit = None
        # Do UI layout
        self.do_layout()        
        # Load schemas
        self.load_schemas(self.schema_type.get())
        
    """ UI Layout """

    ## Do layout
    ## This function sets up the layout of the main window, including the toolbar, treeview,
    ## text pane, and status bar.
    ## It also binds events for resizing the toolbar and handling selections in the treeview.
    def do_layout(self):
        self.LoadIcons()
        # Set main window props
        self.title("GNOME GSettings Viewer")
        self.wm_title = "gsettings_ui"
        self.geometry("600x480")
        self.resizable(True, True)
        self.ico_empty = tk.PhotoImage(width=16,height=16)
         # Toolbar for actions
        self.toolbar = ttk.Frame(self, height=30)  # Fixed height for the toolbar
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        self.toolbar.pack_propagate(False) 
        self.toolbar.bind("<Configure>", self.redo_toolbar_layout)  # Bind resize event to redo layout
        # Status bar for messages
        self.status_bar = tk.Label(self, bd=1, relief=tk.SUNKEN, anchor=tk.W, text="")
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, expand=False)
        # Add a path editor to the toolbar
        self.path_entry = tk.Entry(self.toolbar, width=30)
        self.path_entry.pack(side=tk.LEFT, padx=5, pady=5)
        self.path_entry.bind("<Return>", lambda event: self.load_schemas(self.schema_type.get(), self.path_entry.get()))
        # Add Browse buttton to the toolbar
        self.browse_button = tk.Button(self.toolbar, image=self.ico_folder, command=self.open_location)
        self.browse_button.pack(side=tk.LEFT, padx=5, pady=5)
        #add default button to the toolbar
        self.default_button = tk.Button(self.toolbar, image=self.ico_check, command=self.load_default)
        self.default_button.pack(side=tk.LEFT, padx=5, pady=5)
        # Add separator to the toolbar
        self.toolbar_separator = ttk.Separator(self.toolbar, orient=tk.VERTICAL)
        self.toolbar_separator.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)

        # Add result label to the toolbar
        self.search_icon = tk.Label(self.toolbar, image=self.ico_glass)
        self.search_icon.pack(side=tk.LEFT, padx=5, pady=5)
        # Add search entry to the toolbar
        self.search_text = tk.Entry(self.toolbar, width=20)
        self.search_text.pack(side=tk.LEFT, padx=5, pady=5)
        self.search_text.bind("<KeyRelease>", self.search_handle)  # Bind key release to search
        # Add next and previous buttons to the toolbar
        self.search_prev_button = tk.Button(self.toolbar, image=self.ico_up, command=self.search_prev)
        self.search_prev_button.pack(side=tk.LEFT, padx=1, pady=5)
        self.search_next_button = tk.Button(self.toolbar, image=self.ico_down, command=self.search_next)
        self.search_next_button.pack(side=tk.LEFT, padx=1, pady=5)
        # Add search [current/total] label to toolbar
        self.search_label = tk.Label(self.toolbar, text="[0/0]")
        self.search_label.pack(side=tk.LEFT, padx=5, pady=5)

        # second toolbar
        self.toolbar2 = tk.Frame(self, height=30)
        self.toolbar2.pack(side=tk.TOP, fill=tk.X)
        self.type_selector = ttk.Combobox(self.toolbar2, width=10, values=self.schema_types, textvariable=self.schema_type, state="readonly")
        self.schema_type.set(self.schema_types[0])
        self.type_selector.pack(side=tk.LEFT, padx=5, pady=5)
        self.type_selector.bind("<<ComboboxSelected>>", self.schema_type_handle)
          
        # Paned window for layout
        self.paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        # Treeview frame
        self.tree_frame = ttk.Frame(self.paned_window)
        self.tree_frame.bind("<Configure>", self.tree_frame_handle)
        self.tree_frame.pack(fill=tk.BOTH, expand=True)
        # Treeview for schemas
        self.tree = ttk.Treeview(self.tree_frame, columns=("Value", ), show="tree headings")
        self.tree.heading("Value", text="Value")
        self.tree.column("Value", width=250)
        self.tree.bind("<<TreeviewSelect>>", self.selection_handle)
        # Add a vertical scrollbar to the treeview
        self.tree_scrollbar = tk.Scrollbar(self.tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y) 
        self.tree.configure(yscrollcommand=self.tree_scrollbar.set)
        self.tree.pack(fill=tk.BOTH, padx=1, pady=1, expand=True)
        self.tree.bind("<Double-1>", self.edit_handle)
        self.tree.bind("<KeyRelease>", self.edit_handle)
        # Text frame for schema details
        self.text_frame = ttk.Frame(self.paned_window)
        self.text_frame.pack(fill=tk.BOTH, expand=True)

        # Text pane for schema details
        self.text = tk.Text(self.text_frame, wrap="word", height=10, width=40)
        # Add tags for text formatting
        self.text.tag_configure("bold_blue", foreground="blue", font=("Arial", 10, "bold"))
        self.text.tag_configure("underline_blue", foreground="blue", font=("Arial", 10, "underline italic"))
        self.text.tag_configure("regular", foreground="black", font=("Arial", 10, "normal"))
        self.text.config(state=tk.DISABLED)  # Make text pane read-only initially
         # Add a vertical scrollbar to the text pane
        self.text_scrollbar = tk.Scrollbar(self.text_frame, orient=tk.VERTICAL, command=self.text.yview)
        self.text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.configure(yscrollcommand=self.text_scrollbar.set)
        self.text.pack(fill=tk.BOTH, expand=True)
        # Bind copy and paste actions to the text pane
        self.text.bind("<Control-c>", self.copy_text)

        # Add views to the paned window
        self.paned_window.add(self.tree_frame, weight=1)
        self.paned_window.add(self.text_frame, weight=2)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        self.iconphoto(True, self.ico_check) # Set main window icon
        self.update_idletasks()  # Ensure the layout is updated
        self.minsize(400, 400)  # Set minimum size for the main window
        self.search_text.focus_set()  # Set focus to the search entry
        # Load Icons
 
    # Load icons from default location
    def LoadIcons(self):
        #toolbar icons
        try:
            self.ico_folder = tk.PhotoImage(file=f"{self.mydir}/icons/ico_folder.png")
            self.ico_check  = tk.PhotoImage(file=f"{self.mydir}/icons/ico_check.png")
            self.ico_glass = tk.PhotoImage(file=f"{self.mydir}/icons/ico_glass.png")
            self.ico_up = tk.PhotoImage(file=f"{self.mydir}/icons/ico_up.png")
            self.ico_down = tk.PhotoImage(file=f"{self.mydir}/icons/ico_down.png")
        except tk.TclError:
            # Fallback icons if the specified icons are not found
            self.ico_folder = self.ico_empty
            self.ico_check =  self.ico_empty
            self.ico_glass =  self.ico_empty
            self.ico_up =  self.ico_empty
            self.ico_down =  self.ico_empty
        # TreeView icons
        try:
            self.ico_schema = tk.PhotoImage(file=f"{self.mydir}/icons/ico_schema.png")
            self.ico_key = tk.PhotoImage(file=f"{self.mydir}/icons/ico_key.png")
            self.ico_value = tk.PhotoImage(file=f"{self.mydir}/icons/ico_check.png")
            self.ico_data = tk.PhotoImage(file=f"{self.mydir}/icons/ico_value.png")
        except tk.TclError:
            # Fallback icons if the specified icons are not found
            self.ico_schema =  self.ico_empty
            self.ico_key =  self.ico_empty
            self.ico_value =  self.ico_empty
            self.ico_data =  self.ico_empty
        #icon dictionary
        self.icons_dict = {
            self.NodeType.SCHEMA:   self.ico_schema,
            self.NodeType.KEY:      self.ico_key,
            self.NodeType.COMPOUND:  self.ico_folder,   #ToDo: compound key
            self.NodeType.VALUE:    self.ico_data
        }

    """ GIO Operations """
           
    ## Load schemas
    ## This function loads the GSettings schemas from the system and populates the treeview with them.
    def load_schemas(self, schema_type, location=None):
        
        try:
            default_source = None
            # Clear the treeview
            self.tree.delete(*self.tree.get_children())
            self.gi_dict.clear()  # Clear the GiData dictionary
            default_source = Gio.SettingsSchemaSource.get_default()
            if location == None:
                self.schema_source = default_source
                installed,relocatable = self.schema_source.list_schemas(False)
            else:
                # Load schemas from the specified location
                self.schema_source = Gio.SettingsSchemaSource.new_from_directory(location, Gio.SettingsSchemaSource.get_default(), True)
                installed, relocatable  = self.schema_source.list_schemas(False)
            schemas = installed if schema_type == 'Installed' else relocatable
            self.status_bar.config(text=f"{schema_type} Schema Source {location if location else ''}")
                
            if not schemas:
                self.status_bar.config(text="No schemas found.")
                return

            # Insert schemas into the treeview
            for schema_id in schemas:
                schema = self.schema_source.lookup(schema_id, False)
                split_id = schema_id.split('.')
                parent = ""
                # Build the tree for grouping
                # It will split the schema name into separate tree items for better navigation
                for i, part in enumerate(split_id):
                    node_id = ".".join(split_id[:i+1])
                    if not self.tree.exists(node_id):
                        node = self.tree.insert(parent, "end", node_id, text=part, values=(), tags=("type", self.NodeType.SCHEMA), image=self.ico_schema)
                        self.gi_dict[node] = GiSchema.factory(node_id)
                    parent = node_id
                # For relocatable without location and installed with location
                # we can only list schema names - no data
                
                if schema_type == "Relocatable" and not location:
                    # Can't open relocatable schemas without location
                    self.tree.item(node, values=("Relocatable",))
                    continue
                # At this point parent is the full schema_id node
                # Now parse the settings
                settings = None
                if schema:
                    installed = default_source.lookup(schema.get_id(), False)
                    if (not installed):
                        # Schema not installed
                        self.tree.item(node, values=("Not installed",))
                        continue
                    #if(not source.get_path()):
                    #    continue
                    if(location):
                        # Check location
                        path = schema.get_path()
                        if(path and path != location):
                            self.tree.item(node, values=("Wrong location",))
                            continue
                        settings = Gio.Settings.new_with_path(schema.get_id(), location)
                    else:
                        settings = Gio.Settings.new(schema.get_id())
                    if settings is None:
                        # No settings in schema
                        # This is odd.
                        continue
                    # Process keys
                    for key in schema.list_keys():
                        val = settings.get_value(key)
                        data = val.unpack()
                        self.parse_key(parent, None, key, val, schema)
                            
        except Exception as e:
            self.status_bar.config(text=f"Error loading schemas: {e}")

    def parse_key(self, parent, key_id, name, data, schema, variant=False):
        # variant type
        root_key = None
        nullable = False
        tv = data.get_type_string() if data != None else "?"
        is_variant = tv in "v@"
        gi_dict = self.gi_dict

        # Unpack variant
        if data != None:
            unpacked = data.unpack() if tv[0] in GlVariant.base_type_sig else None
            # Insert new node into tree
            if tv[0] in GlVariant.base_type_sig:
                if(key_id is None):
                    current = self.insert(parent, name, unpacked, self.NodeType.KEY)
                else:
                    current = self.insert(parent, name, unpacked, self.NodeType.VALUE)
                gi_dict.add_gidata(current, key_id, schema, name, data, variant)
            else:
                # Do not insert variant types into tree. Instead mark data as variant.
                node_type = self.NodeType.COMPOUND if key_id else self.NodeType.KEY
                if not is_variant or (is_variant and key_id == None):
                    current = self.insert(parent, name, tv, node_type)
                    gi_dict.add_gidata(current, key_id, schema, name, data, variant)
                if is_variant and key_id != None:
                    current = parent 
                    
            # Handle different types of values
            root_key = current if key_id == None else key_id
            if tv[0] in "a([":
                # List types: show key, children as values
                for i in range(data.n_children()):  # Iterate over array elements
                    if tv.startswith("a{"):
                        # dictionary
                        d = data.get_child_value(i)
                        k = d.get_child_value(0)
                        v = d.get_child_value(1)
                        self.parse_key(current, root_key, k.unpack(), v, schema)
                    else:          
                        # list/array/tuple         
                        d = data.get_child_value(i)
                        self.parse_key(current, root_key, str(i), d, schema)
            elif is_variant:
                for i in range(data.n_children()):
                    d = data.get_child_value(i)
                    self.parse_key(current, root_key, name, d, schema, variant=True)
            elif tv[0] == "m":
                nullable = True
                for i in range(data.n_children()):
                    d = data.get_child_value(i)
                    self.parse_key(current, root_key, str(i), d, schema)
            else:
                if not tv[0] in GlVariant.base_type_sig:
                    print(f"-->Debug: Unknown variant type {tv}")
        else:
            # If the value is not set, just insert the key
            current = self.insert(parent, name, "", self.NodeType.KEY)
            gi_dict.add_gidata(current, key_id, schema, name, data, variant)

        return current
     
    """ Event handlers"""
    ## Redo toolbar layout
    ## This function is called when the toolbar is resized.
    def redo_toolbar_layout(self, event):
        if event:
            # If an event is passed, adjust the layout based on the new size
            
            # Measure font
            font = tkFont.Font(font=self.path_entry["font"])
            char_width = font.measure('0') or 10
            # Reserve space for other widgets
            # ToDo: May be calculate reserves from sizes of other widgets
            # (It can make it harder to maintain though)
            path_reserve = 100
            search_reserve = 160
            # Reserve space for buttons and labels
            # Divide it roughly in half between path and search
            # ToDo: Maybe add a slider bar in the future.
            path_text_chars = int(((event.width/2) - path_reserve)/char_width)
            path_text_chars = max(10, path_text_chars)
            self.path_entry.config(width=path_text_chars)
            search_text_chars = int((event.width/2 - search_reserve)/char_width)
            self.search_text.config(width=max(10,search_text_chars))
 
    ## Schema type handle
    def schema_type_handle(self, event):
        schema_type = self.schema_type.get()
        location = self.path_entry.get()
        location = location if location != '' else None
        self.load_schemas(schema_type, location)
 
    ## Selection Handle
    ## This function is called when a selection is made in the treeview.
    ## It updates the caption of the treeview and populates the table with the selected schema's details.
    def selection_handle(self, event):
        selected_item = self.tree.focus()
        # Check for the search context
        if len(self.search_results) > 0:
            search_item = self.search_results.current()
            if not selected_item == search_item:
                # Reset search results if selection changes
                self.search_results.reset()  
                self.search_label.config(text=f"[0/0]")
                self.search_text.delete(0, tk.END)  # Clear search text
        # Update the caption of the treeview
        full_path = self.get_full_path(self.tree, selected_item)
        item_id = self.tree.item(selected_item, "text")
        self.tree.heading("#0", text=full_path, anchor="w")
        # Update the text pane with details of the selected item
        self.update_text_pane(selected_item)

    # Sync editor to the tree frame
    def tree_frame_handle(self, event):
        if self.gsedit:
            self.gsedit.place()
    
    # Start the editor
    def edit_handle(self, event):
        if event.type is tk.EventType.KeyRelease and event.keysym != 'Return':
            return
        selected_item = self.tree.focus()
        gi_data = self.gi_dict.get(selected_item, None)
        if isinstance(gi_data, GiSchema):
            # Can't edit schemas
            return
        children = self.tree.get_children(selected_item)
        if(len(children) == 0):
            # It is a leaf node. Edit.
            self.gsedit = GSettingsEditor(self)
            self.gsedit.show()
            self.gsedit = None

    ## Search handle
    def search_handle(self, event):
        # If the key is a special key, handle it separately
        # For example, Up and Down keys for navigation
        if event.keysym_num > self.MAX_ASCII:
            if event.keysym in ("Up", "KP_Up"):
                self.search_prev()
                return
            elif event.keysym in ("Down", "KP_Down"):
                self.search_next()
                return
            elif not event.keysym in ["Delete", "BackSpace", "KP_Delete", "KP_BackSpace"]:
                return
        # For all other keys do search    
        # Use delay not to waste time on extra searches for 
        # rapid key sequences
        if self.after_id:
            # Cancel the previous search 
            self.after_cancel(self.after_id)  
        # Set a threshold for the search delay
        self.after_id = self.after(self.SEARCH_DELAY, self.search)  # Perform search after delay

    ## Top level search function
    def search(self):
        self.search_results.reset()  # Reset search results
        self.search_label.config(text=f"0 / 0")
        search_text = self.search_text.get() #.strip()
        if search_text:
            self.do_search(search_text, "")
        if len(self.search_results) > 0:
            self.search_label.config(text=f"[1/{len(self.search_results)}]")
            first_result = self.search_results[0]
            self.select_and_focus(first_result)
       
    ## Do search
    ## This function performs a recursive search in the treeview for the given search text.
    def do_search(self, search_text, root):
        for item_id in self.tree.get_children(root):
            if type(self.gi_dict[item_id]) in [GiSchema, GiKey]:
                # For now only search schemas and keys
                # ToDo: Search Data option?
                text = self.tree.item(item_id, "text")            
                if search_text.lower() in text.lower():
                    self.search_results.append(item_id)
                else:
                    self.do_search(search_text, item_id)
                
    ## Search previous result
    def search_prev(self):
        if len(self.search_results) > 0:
            current = self.search_results.previous()
            if current:
                self.select_and_focus(current)
                self.search_label.config(text=f"[{self.search_results.current_index+1}/{len(self.search_results)}]")

    ## Search next result
    def search_next(self):
        if len(self.search_results) > 0:
            if self.search_results.current_index == len(self.search_results) - 1:
                return  # No more results to show
            # Get the next item in the search results
            current = self.search_results.next()
            if current:
                self.select_and_focus(current)
                self.tree.yview_scroll(1, "units")  # Scroll to the item
                self.search_label.config(text=f"[{self.search_results.current_index+1}/{len(self.search_results)}]")

    ## Copy text handle
    def copy_text(self, event):
        self.text.event_generate("<<Copy>>")
        
    ## Load default
    ## This function loads the default GSettings schema location and populates the treeview with schemas.
    def load_default(self):
        # Clear path text
        self.path_entry.delete(0, tk.END)
        #set type to Installed
        self.schema_type.set(self.schema_types[0])
        # Load schemas from the default location
        self.load_schemas(self.schema_type.get())
 
    ## Open schema location
    ## This function is called when the Open button is clicked.
    ## It opens a file dialog to select a GSettings schema location and loads the schemas from that location.
    def open_location(self):
        # Open a file dialog to select a GSettings schema location
        location = tk.filedialog.askdirectory(title="Select Schema Location", initialdir=self.path_entry.get())
        # Validate the location
        # ToDo: 
        # 1. More rigorous validation
        # 2. Check if the location exists
        if location:
            if(location[-1] != '/'):
                location += '/'
            if not Gio.File.new_for_path(location).query_exists(None):
                self.status_bar.config(text=f"Path {location} does not exist.")
                return
        # Remember location
        self.location = location
        # Set type to "Relocatable"
        self.schema_type.set(self.schema_types[1])
        
        if self.location:
            self.path_entry.delete(0, tk.END)  # Clear the path text entry
            self.path_entry.insert(0, self.location)  # Insert the selected path
            # Load schemas from the selected location
            self.load_schemas(self.schema_type.get(), self.location)

    """ Helper functions """
    
    ## Get full path
    ## Helper function for getting the full path of a selected item in the treeview.    
    def get_full_path(self, tree, item):
        path = []
        while item:
            path.append(tree.item(item, "text"))
            item = tree.parent(item)
        return ".".join(reversed(path))

    ## Select and focus
    ## This function selects and focuses the given item in the treeview.
    def select_and_focus(self, item):
        """Select and focus the given item in the treeview."""
        self.tree.update_idletasks()  # Ensure the treeview is updated
        self.tree.see(item)
        self.tree.selection_set(item)
        self.tree.focus(item)
       
    ## Insert
    ## This function inserts a new item into the treeview with the given key, value, type, and image.
    ## It returns the ID of the newly inserted item.
    def insert(self, parent, key, val, type):
        values = (str(val),)
        image = self.icons_dict.get(type, self.ico_empty)
        return self.tree.insert(parent, "end", text=key, values=values, image=image)

    ## Update text pane
    ## This function updates the text pane with details of the selected item in the treeview.
    def update_text_pane(self, selected_item):
        gi_dict = self.gi_dict
        gi_data = gi_dict.get_data(selected_item)
        if isinstance(gi_data, GiSchema):
            gi_key, gi_value = (None, None)
        else:
            gi_key, gi_value = self.gi_dict.get_keyvalue(selected_item)
                
        # Set up the text pane
        self.text.config(state=tk.NORMAL)
        self.text.delete(1.0, tk.END)
        # Insert the full path in the text pane
        full_path = self.get_full_path(self.tree, selected_item)
        self.text.insert(tk.END, full_path + "\n\n", "underline_blue")
        # Show the description and value
        values = self.tree.item(selected_item, "values")
        text = self.tree.item(selected_item, "text")
        
        if gi_key:
            # If GiData is available, show its schema ID
            self.text.insert(tk.END, "Schema ID: ", "bold_blue")
            self.text.insert(tk.END, f"{gi_key.get_schema_name()}\n")
            # If key is present, show it
            if gi_key.get_key_name():
                self.text.insert(tk.END, "Key: ", "bold_blue")
                self.text.insert(tk.END, f"{gi_key.get_key_name()}")
                # If summary is present, show it 
                if gi_key.get_summary():
                    self.text.insert(tk.END, f"\t({gi_key.get_summary()})\n")
                self.text.insert(tk.END, "\n")
            #if key type present, show it
            if gi_key.get_key_type():
                self.text.insert(tk.END, "\nKey type: ", "bold_blue")
                self.text.insert(tk.END, f"{gi_key.get_key_type()}\n", "bold_blue")
            # If description is present, show it
            if gi_key.get_description():
                self.text.insert(tk.END, "Description: ", "bold_blue")
                self.text.insert(tk.END, f"\n{gi_key.get_description()}\n")
        if gi_value:
            # Show the value if present
            self.text.insert(tk.END, f"Value: {gi_value.get_vtype()} ", "bold_blue")
            if gi_value.is_compound():
                self.text.insert(tk.END, "\n<<Compound>>\n")
            else:
                self.text.insert(tk.END, f"\n{gi_value.get_value()}\n") 
        if gi_key:
            # If default value if present
            default_value = gi_key.get_default_value()
            if default_value:
                default_value =  get_defaultvalue(self.tree, default_value, gi_value)
                self.text.insert(tk.END, f"Default Value: ", "bold_blue")
                self.text.insert(tk.END, f"\n{default_value}\n")
            # If range is present, show it
            if gi_key.get_range():
                t,v = gi_key.get_range()
                if len(v) > 0:
                    self.text.insert(tk.END, "Range: ", "bold_blue")
                    self.text.insert(tk.END, f"\n{t} : {v}")
        # Lock the text pane
        self.text.config(state=tk.DISABLED)
    
 
""" Main function """
## This function creates an instance of the GSettingsViewer class and starts the Tkinter main loop.
if __name__ == "__main__":
    try:
        app = GSettingsViewer()
        app.mainloop()
    except Exception as e:
        print(f"An error occurred: {e}")
