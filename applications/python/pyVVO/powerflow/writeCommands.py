"""
Module to write setpoint commands to a GridLAB-D model (.glm)

NOTE: This module is in 'prototype' mode. As such, it certainly isn't
optimally efficient.

Created on Jul 27, 2017

@author: thay838

"""

import re

def readModel(modelIn):
    '''Simple function to read file as string'''
    with open(modelIn, 'r') as f:
        s = f.read()
    return s

class writeCommands:
    """"Class for reading GridLAB-D model and changing setpoints in voltage
        regulating equipment (OLTC, caps, etc.)
    """
    # Define some constants for GridLAB-D model parsing.
    REGOBJ_REGEX = re.compile(r'\bobject\b\s\bregulator\b')
    REGCONF_REGEX = re.compile(r'\bobject\b\s\bregulator_configuration\b')
    CAP_REGEX = re.compile(r'\bobject\b\s\bcapacitor\b')
    
    def __init__(self, strModel, pathModelOut, pathModelIn=''):
        """"Initialize class with input/output GridLAB-D models
        
        strModel should be a string representing a GridLAB-D model.
            Can be obtained by calling readModel function in this module.
            It will be modified to send new commands.
            
        pathModelOut is the path to the new output model.
        """

        # Set properties.
        self.strModel = strModel
        self.pathModelIn = pathModelIn
        self.pathModelOut = pathModelOut
        
    def writeModel(self):
        """"Simple method to write strModel to file"""
        
        with open(self.pathModelOut, 'w') as f:
            f.write(self.strModel)
    
    def commandRegulators(self, regulators):
        """"Function to change tap positions on a given regulator.
        
        This is performed by finding its configuration and changing 'tap_pos.'
        
        INPUT: Dictionary of dictionaries. Top level keys are regulator
            names. Each subdict can have up to two keys: 'regulator' and 
            'configuration.' Within the 'regulator' or 'configuration' dicts,
            keys are properties to change (e.g. tap_A or Control) mappped to
            the new desired value (e.g. 2 or MANUAL)
            
        Example regulators input:
        regulators={'R2-12-47-2_reg_1': {
                        'regulator': {
                            'tap_A':1,
                            'tap_B':2,
                            'tap_C':3
                        },
                        'configuration': {
                            'Control': 'MANUAL'
                        }
                    },
                    'R2-12-47-2_reg_2': {
                        'regulator': {
                            'tap_A':4,
                            'tap_B':5,
                            'tap_C':6
                        },
                        'configuration': {
                            'Control': 'MANUAL'
                        }
                    }
        }
        
        OUTPUT: The GridLAB-D model in self.strModel is modified
        """
        # First, find all regulators
        regMatch = writeCommands.REGOBJ_REGEX.search(self.strModel)
        
        # Loop through regulators to find names and configs.
        # Note that this could be more efficient, but oh well.
        regDict = dict()
        while regMatch is not None:
            # Extract the object:
            reg = self.extractObject(regMatch)
            
            # Extract name and configuration properties and assign to dict
            d = writeCommands.extractProperties(reg['obj'],
                                                ['name', 'configuration'])
            name = d['name']['prop']
            regDict[name] = d
            
            # If this regulator is in our input dictionary, alter properties
            if (name in regulators) and ('regulator' in regulators[name]):
                
                # Modify the properties of the regulator
                reg['obj'] = writeCommands.modObjProps(reg['obj'], 
                                                       regulators[name]['regulator'])
                
                # Replace regulator with new modified regulator
                self.replaceObject(reg)
            
            # Find the next regulator using index offset
            regEndInd = reg['start'] + len(reg['obj'])
            regMatch = writeCommands.REGOBJ_REGEX.search(self.strModel,
                                                              regEndInd)
            
            
            
        # Find the configurations for the requested regulators and put in list.
        # NOTE: confList and regList MUST be one to one.
        confList = []
        regList = []
        for regName, commandDict in regulators.items():
            # If we didn't find it, raise an exception
            if regName not in regDict:
                raise ObjNotFoundError(obj=regName, model=self.pathModelIn)
            
            # If we're commanding the configuration, add it to the list.
            if 'configuration' in commandDict:
                # Extract name of the configuration, put in list
                confList.append(regDict[regName]['configuration']['prop'])
                # Put the regulator in the list
                regList.append(regName)
        
        # Next, loop through and command regulator configurations. Since we'll
        # be modifying the model as we go, we shouldn't use the 'finditer' 
        # method.
        regConfMatch = writeCommands.REGCONF_REGEX.search(self.strModel)
        
        while regConfMatch is not None:
            # Extract the object
            regConf = self.extractObject(regConfMatch)
            
            # Extract the name
            d = writeCommands.extractProperties(regConf['obj'], ['name'])
            
            # If the regulator is in our configuration list, alter config.
            if d['name']['prop'] in confList:
                # Get the name of the regulator to command
                regInd = confList.index(d['name']['prop'])
                regName = regList[regInd]
                
                # Modify the configuration
                regConf['obj'] = writeCommands.modObjProps(regConf['obj'],
                                                           regulators[regName]['configuration'])
                    
                # Regulator configuration has been updated, now update model
                self.replaceObject(regConf)
            
            # Find the next regulator configuration, using index offset
            regEndInd = regConf['start'] + len(regConf['obj'])
            regConfMatch = writeCommands.REGCONF_REGEX.search(self.strModel,
                                                              regEndInd)
        
    def commandCapacitors(self, capacitors):
        """"Function to change state of capacitors.
        
        INPUT: Dictionary of dictionaries. Top level keys are capacitor
            names. Each subdict's keys are properties to change (e.g. 
            switchA) mappped to the new desired value (e.g. OPEN)
        
        Example capacitors input:
        capacitors={'R2-12-47-2_cap_1': {
                        'switchA':'OPEN',
                        'switchB':'CLOSED',
                        'control': 'MANUAL'
                    },
                    'R2-12-47-2_cap_4': {
                        'switchA':'CLOSED',
                        'switchB':'CLOSED',
                        'switchC': 'OPEN',
                        'control': 'MANUAL'
                    }
        }
        
            
        OUTPUT: The GridLAB-D model in self.strModel is modified
        """
        # Find the first capacitor
        capMatch = writeCommands.CAP_REGEX.search(self.strModel)
        
        # Loop through the capacitors
        while capMatch is not None:
            # Extract the object
            cap = self.extractObject(capMatch)
            
            # Extract its name
            capName = writeCommands.extractProperties(cap['obj'], ['name'])
            n = capName['name']['prop']
            
            # If the capacitor is in the list to command, do so
            if n in capacitors:
                # Modify the capacitor object to implement commands
                cap['obj'] = writeCommands.modObjProps(cap['obj'], 
                                                       capacitors[n])
                                 
                # Splice new capacitor object into model
                self.replaceObject(cap)
                                
            # Find the next capacitor, using index offset
            capEndInd = cap['start'] + len(cap['obj'])
            capMatch = writeCommands.CAP_REGEX.search(self.strModel, capEndInd)
            
    def replaceObject(self, objDict):
        """Function to replace object in the model string with a modified
        one.
        
        INPUTS: objDict: object dictionary in the format returned by 
            writeCommands.extractObject
            
        OUTPUS: directly modifies self.strModel to replace object with new one
        """
        self.strModel = (self.strModel[0:objDict['start']] + objDict['obj']
                         + self.strModel[objDict['end']:])
                                
    @staticmethod
    def modObjProps(objStr, propDict):
        """"Function to modify an object's properties"""
        
        # Loop through the properties and modify/create them
        for prop, value in propDict.items():
            try:
                propVal = writeCommands.extractProperties(objStr, [prop])
            except PropNotInObjError:
                # If the property doesn't exist, append it to end of object
                
                # Determine if linesep is necessary before appended line
                if objStr[-2] == '\n':
                    preSep = ''
                else:
                    preSep = '\n'
                    
                objStr = (objStr[0:-1] + preSep + prop + " " + str(value)
                          + ";" + objStr[-1])
            else:
                # Replace previous property value with this one
                objStr = (objStr[0:propVal[prop]['start']] + str(value)
                          + objStr[propVal[prop]['end']:])
                         
        # Return the modified object
        return objStr
                
    def extractObject(self, regMatch):
        """"Function to a GridLAB-D object from the larger model as a string.
        
        regMatch is a match object returned from the re package after calling
            re.search or one member of re.finditer.
        
        OUTPUT:
        dict with three fields: 'start,' 'end,' and 'obj'
            start indicates the starting index of the object in the full model
            end indicates the ending index of the object in the full model
            
        """
        
        # Extract the starting index of the regular expression match.
        startInd =  regMatch.span()[0]
        # Initialize the ending index (to be incremented in loop).
        endInd = startInd
        # Initialize counter for braces (to avoid problems with nested objects)
        braceCount = 0
        
        for c in self.strModel[startInd:]:
            # Increment the index
            endInd += 1
            
            # To avoid troubles with nested objects, keep track of braces
            if c == '{':
                braceCount += 1
            elif c == '}':
                braceCount -= 1
                
            # Break loop if c is a closing curly brace. Since the index is
            # incremented first, we ensure the closing bracket is included.
            if c == '}' and braceCount == 0:
                break
            
        # We now know the range of this object. Extract it.
        objStr = self.strModel[startInd:endInd]
        out = {'start':startInd, 'end':endInd, 'obj':objStr}
        return out
    
    @staticmethod
    def extractProperties(objString, props):
        """"Function to extract properties from a string of an object.
        
        INPUTS:
            objString: string representing object
            props: list of desired properties to extract
            
        OUTPUT: 
            dict mapping props to extracted values
        """
        # Initialize return
        outDict = dict()
        
        # Loop over the properties
        for p in props:
            # Create regular expression to extract the property after the 
            # property name and before the semi-colon.
            exp = r'(?<=\b' + p + r'\b\s)(.*?)(?=;)'
            prop = re.search(exp, objString)
            
            # If the property was not found, raise an exception.
            # TODO: make exception better
            if not prop:
                raise PropNotInObjError(obj = objString, prop = p)
            
            # Get property value and assign to output dictionary
            propStr = prop.group().strip()
            outDict[p] = {'prop': propStr, 'start': prop.span()[0],
                          'end': prop.span()[1]} 
            
        return outDict

class Error(Exception):
    """"Base class for exceptions in this module"""
    pass

class ObjNotFoundError(Error):
    """"Exception raised if requested object doesn't exist in model
    
    Attributes:
        obj: requested object
        model: model file in question
        message: simple message
    """
    def __init__(self, obj, model):
        self.obj = obj
        self.model = model
        self.message = "The object '" + obj + "' doesn't exist in " + model
        
    def __str__(self):
        return(repr(self.message))
        
class PropNotInObjError(Error):
    """"Exception raised if an object doesn't have the property required
    
    Attributes:
        obj: object in which a property is being looked for in
        prop: property being searched for in an object
        model: model file being searched
        message: simple message
    """
    def __init__(self, obj, prop, model=''):
        self.obj = obj
        self.prop = prop
        self.model = model
        self.message = ("The property '" + prop + "' doesn't exist in "
                        + "the object '" + obj + "' in the model " + model)
            
    def __str__(self):
        return(repr(self.message))

inPath = 'C:/Users/thay838/Desktop/R2-12.47-2.glm'
strModel = readModel(inPath)
obj = writeCommands(strModel=strModel, pathModelIn=inPath, pathModelOut='C:/Users/thay838/Desktop/R2-12.47-2-copy.glm')
obj.commandRegulators(regulators={'R2-12-47-2_reg_1': {'regulator': {'tap_A':1, 'tap_B':2, 'tap_C':3}, 'configuration': {'Control': 'MANUAL'}}, 'R2-12-47-2_reg_2': {'regulator': {'tap_A':4, 'tap_B':5, 'tap_C':6}, 'configuration': {'Control': 'MANUAL'}}})
obj.commandCapacitors(capacitors={'R2-12-47-2_cap_1': {'switchA':'OPEN', 'switchB':'CLOSED', 'control': 'MANUAL'}, 'R2-12-47-2_cap_4': {'switchA':'CLOSED', 'switchB':'CLOSED', 'switchC': 'OPEN', 'control': 'MANUAL'}})
obj.writeModel()