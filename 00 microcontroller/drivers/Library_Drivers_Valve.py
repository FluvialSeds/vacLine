# Library_Drivers_Valve.py
# 20. April 2022
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

'''
File to make a driver for turning on/off a 24V power switch on the LIP
pi pico controller board (nominally for pneumatic valves)
'''

from time import sleep
from machine import Pin

class Valve:
	'''
	Makes a Valve class instance
	'''

	def __init__(self, **kwargs):
		'''
		Initialize the class

		Attributes
		----------
		name : str
			The name of the Valve

		pin : int
			The pin number controlling the Valve

		valve : machine.Pin
			The status of the pin
		'''

		#set attributes
		self.name = kwargs["name"]
		self.pin = int(kwargs["pin"])
		self.valve = Pin(self.pin, Pin.OUT)


	#define funciton to open valve
	def open(self):
		'''
		Opens valve
		'''
		self.valve.high()
		print("open: ", self.name)

	#define function to close valve
	def close(self):
		'''
		Closes valve
		'''
		self.valve.low()
		print("close: ", self.name)

	#define function to get position
	def getPos(self):
		'''
		Gets the current position

		0 = closed
		1 = open
		'''

		sleep(0.001)

		print(self.valve.value())
