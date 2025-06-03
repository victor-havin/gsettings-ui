"""
Gi model.
This is the data model for Gio interface as seen by the UI module.
"""

class GiSchema:
    """
    Gio Schema
    A class to hold Gio schema data
    
    Note: This is mostly a placeholder for consistency. Currently I am not aware of any
    metadata accessible from schema. If there is or will be in the futture - this is the 
    place to add it.
    """
    def __init__(self, schema_id):
        self.schema_id = schema_id
        
    @classmethod
    def factory(cls, schema_id):
        return GiSchema(schema_id)
    
    def get_schema_id(self):
        return self.schema_id

class GiKey:
    """
    A class to hold data from Gio Key.
    It is used to store key data.
    """
    def __init__(self, schema_id, key):
        # Constructor for GiData
        self.schema_id = schema_id  # The ID of the GSettings schema
        self.key = key              # The key in the schema
        self.summary = None         # Summary of the schema key (if applicable)
        self.range = None           # Range of values for the schema key (if applicable)
        self.description = None     # Description of the schema key
        self.default_value = None   # Default value of the schema key
        self.value = None           # Current value of the schema key
    
    ## String representation methods
    def __repr__(self):
        return f"GiData(schema_id={self.schema_id}, key={self.key})"
    def __str__(self):
        return f"{self.schema_id}.{self.key}"
    def __eq__(self, other):
        if isinstance(other, GiKey):
            return self.schema_id == other.schema_id and self.key == other.key
        return False
    
    @classmethod
    def factory(cls, schema, key):
        gi_key = GiKey(schema.get_id(), key)
        # Check if the value is set
        schema_key = schema.get_key(key)
        if schema_key:
            # process the schema key
            # Get metadata like description, default value, constraints, etc.
            description = schema_key.get_description()
            default_value = schema_key.get_default_value().unpack()
            value_range = schema_key.get_range()
            summary = schema_key.get_summary()
            if description:
                gi_key.set_description(description) 
            if default_value:
                gi_key.set_default_value(default_value)
            if value_range:
                gi_key.set_range(value_range)
            if summary:
                gi_key.set_summary(summary)
        return gi_key
        
    def set_schema_id(self, schema_id):
        #Set the schema ID of the data.
        self.schema_id = schema_id
    def get_schema_id(self):
        #Get the schema ID of the data.
        return self.schema_id 
    def set_summary(self, summary):
        #Set the summary of the schema key.
        self.summary = summary  
    def get_summary(self):
        #Get the summary of the schema key.
        return self.summary 
    def set_range(self, range):
        #Set the range of the schema key.
        self.range = range  
    def get_range(self):
        #Get the range of the schema key.
        return self.range
    def set_key(self, key):
        #Set the key of the schema.
        self.key = key
    def get_key(self):
        #Get the key of the schema.
        return self.key
    def set_description(self, description):
        #Set the description of the schema key.
        self.description = description
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
    
class GiValue:
    """
    GiValue holds value, type and the owning key.
    """
    
    def __init__(self, key, value, type):
        self.key = key
        self.value = value
        self.type = type
        self.compound = False
        
    @classmethod
    def factory(cls, key, value, type):
        gi_value = GiValue(key, value, type)
        gi_value.compound = gi_value.type not in [int, float, str, bool]
        return gi_value

    def get_key(self):
        return self.key
    
    def get_value(self):
        return self.value
    
    def get_type(self):
        return self.type
    
    def is_compound(self):
        return self.compound