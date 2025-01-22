# Library_Drivers_LED.py
# 19. April 2022
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

'''
File to make a driver for turning on/off an LED light (pi pico testing!)
'''

from machine import Pin

class LED:
	'''
	Makes an LED class instance
	'''

	def __init__(self, **kwargs):
		'''
		Initialize the class

		Attributes
		----------
		name : str
			The name of the LED

		pin : int
			The pin number controlling the LED

		led : machine.Pin
			The status of the pin
		'''

		#set attributes
		self.name = kwargs["name"]
		self.pin = int(kwargs["pin"])

		#initialize the object
		self.led = Pin(self.pin, Pin.OUT)


	#define funciton to turn LED on
	def on(self):
		'''
		Turns LED on
		'''
		self.led.high()
		print("on: ", self.name)

	#define function to turn LED off
	def off(self):
		'''
		Turns LED off
		'''
		self.led.low()
		print("off: ", self.name)