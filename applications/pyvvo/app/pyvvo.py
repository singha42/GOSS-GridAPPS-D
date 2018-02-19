'''
This is the 'main' module for the application

Created on Jan 25, 2018

@author: thay838
'''
# TODO: probably need to set up pathing (add subdirectories to Python path)

# TODO: There's no reason the following steps should be done in series. We
# should spin up threads.

# For now, hard-code regulators and capacitors. We'll need to get this from
# the CIM later.
import pmaps.constants
reg = pmaps.constants.REG
cap = pmaps.constants.CAP

# TODO: Get data for load modeling, spin up load models

# TODO: Get .glm from platform service
# For now, 