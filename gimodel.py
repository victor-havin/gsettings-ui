"""
Gi model.
This is the data model for Gio interface as seen by the UI module.
"""
import gi
gi.require_version("Gio", "2.0")
from gi.repository import GLib

class GlVariant(GLib.Variant):
    """
    GlVariant
    Basic Types
    "b" → Boolean
    "y" → Byte (unsigned 8-bit integer)
    "n" → Int16
    "q" → UInt16
    "i" → Int32
    "u" → UInt32
    "x" → Int64
    "t" → UInt64
    "d" → Double (floating-point)
    "s" → String
    "o" → Object path
    "g" → Signature
    "v" → Variant (can hold any type)
    "@" -> Also variant in some cases
    Container Types
    "mT" → Maybe type (nullable)
    "aT" → Array of type T
    "(T1T2...Tn)" → Tuple containing multiple types
    "{KT}" → Dictionary entry (key-value pair)
    """

    base_type_sig : str = "bynqiuxtdsog"
    composite_type_sig : str = "mav@({"

    @staticmethod
    def AssureVariant(vt_str, input):
        if isinstance(input, GLib.Variant):
            return input
        else:
            return GlVariant(vt_str, input)
        
    @staticmethod    
    def unpack_preserve_variants(variant):
        if not isinstance(variant, GLib.Variant):
            return variant  # Return non-variant values as-is

        type_str = variant.get_type_string()

        if type_str == 'v':  # Preserve inner variants
            return variant  

        elif type_str.startswith('a{'):  # Dictionary case (array of key-value pairs)
            preserved_dict = {}
            for i in range(variant.n_children()):  # Iterate through dictionary entries
                entry = variant.get_child_value(i)
                key = entry.get_child_value(0).unpack()
                value = GlVariant.unpack_preserve_variants(entry.get_child_value(1))
                preserved_dict[key] = value
            return preserved_dict  # Properly preserves nested variants

        elif type_str.startswith('a'):  # Generic array handling
            return [GlVariant.unpack_preserve_variants(variant.get_child_value(i)) for i in range(variant.n_children())]

        elif variant.is_container():  # Tuples (structured types)
            return tuple(GlVariant.unpack_preserve_variants(variant.get_child_value(i)) for i in range(variant.n_children()))

        else:  # Unpack primitive values
            return variant.unpack()

class GiSchema:
    """
    Gio Schema
    A class to hold Gio schema data
    
    Note: This is mostly a placeholder for consistency. Currently I am not aware of any
    metadata accessible from schema. If there is or will be in the futture - this is the 
    place to add it.
    """
    def __init__(self, name):
        self.name = name
        
    @classmethod
    def factory(cls, schema_name):
        return GiSchema(schema_name)
    
    def get_name(self):
        return self.name


class GiKey:
    """
    A class to hold data from Gio Key.
    It is used to store key data.
    """
    def __init__(self, schema_name, key_name, key_id):
        # Constructor for GiData
        self.schema_name = schema_name  # The ID of the GSettings schema
        self.key_name = key_name        # The key in the schema
        self.key_id = key_id            # The key id 
        self.key_type = None            # Key type in GVariant type string format
        self.summary = None             # Summary of the schema key (if applicable)
        self.range = None               # Range of values for the schema key (if applicable)
        self.description = None         # Description of the schema key
        self.default_value = None       # Default value of the schema key
        self.value = None               # Current value of the schema key
    
    ## String representation methods
    def __repr__(self):
        return f"GiKey(schema_id={self.schema_id}, key={self.key})"
    def __str__(self):
        return f"{self.schema_id}.{self.key}"
    def __eq__(self, other):
        if isinstance(other, GiKey):
            return self.schema_id == other.schema_id and self.key == other.key
        return False
    
    @classmethod
    def factory(cls, schema, key_name, key_id):
        gi_key = GiKey(schema.get_id(), key_name, key_id)
        # Check if the value is set
        schema_key = schema.get_key(key_name)
        if schema_key:
            # process the schema key
            # Get metadata like description, default value, constraints, etc.
            description = schema_key.get_description()
            key_type = schema_key.get_value_type().dup_string()
            default_value = schema_key.get_default_value().unpack()
            value_range = schema_key.get_range()
            summary = schema_key.get_summary()
            if description:
                gi_key.description = description
            if default_value:
                gi_key.default_value = default_value
            if key_type:
                gi_key.key_type = key_type
            if value_range:
                gi_key.range = value_range.unpack()
            if summary:
                gi_key.summary = summary
        return gi_key
        
    def get_schema_name(self):
        #Get the schema ID of the data.
        return self.schema_name
    def get_summary(self):
        #Get the summary of the schema key.
        return self.summary 
    def get_range(self):
        #Get the range of the schema key.
        return self.range
    def get_key_name(self):
        #Get the key id.
        return self.key_name
    def get_description(self):
        #Get the description of the schema key.
        return self.description
    def set_default_value(self, default_value):
        #Set the default value of the schema key.
        self.default_value = default_value
    def get_default_value(self):
        #Get the default value of the schema key.
        return self.default_value
    def set_value(self, value):
        self.value = value
    def get_value(self):
        return self.value
    def get_key_type(self):
        return self.key_type
    def get_key_id(self):
        return self.key_id

class GiValue:
    """
    GiValue holds value, type and the owning key.
    """
    
    def __init__(self, key, value, vtype):
        self.key = key
        self.key_id = key.get_key_id()
        self.value = value
        self.vtype = vtype
        self.variant = False
        self.compound = False
        
    @classmethod
    def factory(cls, key, value, type):
        gi_value = GiValue(key, value, type)
        gi_value.compound = type not in GlVariant.base_type_sig
        return gi_value

    def get_key(self):
        return self.key
    
    def get_key_id(self):
        return self.key.get_key_id()
    
    def set_value(self, value):
        if self.vtype == 'b' and isinstance(value,str):
            self.value = True if value == 'True' else False
        else:
            self.value = value
        
    def get_value(self):
        return self.value
    
    def get_type(self):
        return type(self.value)
    
    def get_vtype(self):
        return self.vtype
    
    def is_compound(self):
        return self.compound
    
    def is_variant(self):
        return self.variant
    
    def set_variant(self, is_variant):
        self.variant = is_variant

class GiDict(dict):
    """ 
    GiDict class
    Represents GI dictionary object.
    Holds keys and values for a schema source
    """    
    # Get Data (key or value)
    def get_data(self, id):
        gi_data = self.get(id, None)
        if not gi_data:
            raise TypeError(f"No data at {id}")
        return gi_data
    
    # Get schema
    def get_schema(self, id):
        gi_schema = self.get(id, None)
        if not gi_schema or not isinstance(gi_schema, GiSchema):
            raise TypeError(f"No schema at {id}")
        return gi_schema
    
    # Get Key
    def get_key(self, id):
        gi_key = self.get(id, None)
        if not gi_key or not isinstance(gi_key, GiKey):
            raise TypeError(f"No key at {id}")
        return gi_key
    
    # Get Value
    def get_value(self, id):
        gi_value = self.get(id, None)
        if not gi_value or not isinstance(gi_value, GiValue):
            raise TypeError(f"No value at {id}")
        return gi_value
        
    # Get  Key-Value pair
    def get_keyvalue(self, id):
        gi_data = self.get_data(id)
        if isinstance(gi_data, GiKey):
            gi_key = gi_data
            gi_value = gi_key.get_value()
        elif isinstance(gi_data, GiValue):
            gi_value = gi_data
            gi_key = gi_value.get_key()
        else:
            raise TypeError(f"No key or value at {id}")
        return (gi_key, gi_value)

""" 
common helpers
"""
def get_defaultvalue(tree, default_value, value):
    if type(default_value) in [list, tuple]:
    # if default is compond and value is not - select the matchiing one
        if not value.is_compound():
            selected_item = tree.focus()
            parent = tree.parent(selected_item)
            index = tree.get_children(parent).index(selected_item)
            selected_value = default_value[index]
            return selected_value
    return default_value
                        
