'''
micropython modbus package based on a stripped-down version of the Pycom
umodbus package

25. May 2022
Jordon D Hemingway
'''

#get version and author
__version__ = '0.0.1'
__author__ = 'Jordon D. Hemingway'

#import classes
from . serial import ModbusRTU