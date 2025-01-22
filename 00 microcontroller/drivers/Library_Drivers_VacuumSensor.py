# Library_Drivers_VacuumSensor.py
# 09. January 2025
# Jordon D Hemingway

'''
File to make a driver for reading Pfeiffer Pirani vacuum gauge (goes through an 
analog to digitcal converter)
'''

import struct
import time

from machine import I2C
from micropython import const

#set global voltage divider resistors (in connector gland)
_R1 = 5.6 #kO
_R2 = 3.3 #kO

#set global constants
_ADS1X15_PGA_RANGE = {
	23: 6.144, 
	1: 4.096, 
	2: 2.048, 
	4: 1.024, 
	8: 0.512, 
	16: 0.256
	}

#set global constants
_ADS1X15_POINTER_CONVERSION = const(0x00)
_ADS1X15_POINTER_CONFIG = const(0x01)
_ADS1X15_CONFIG_OS_SINGLE = const(0x8000)
_ADS1X15_CONFIG_MUX_OFFSET = const(12)
_ADS1X15_CONFIG_COMP_QUE_DISABLE = const(0x0003)
_ADS1X15_CONFIG_GAIN = {
	23: 0x0000,
	1: 0x0200,
	2: 0x0400,
	4: 0x0600,
	8: 0x0800,
	16: 0x0A00,
}

#data sample rates
_ADS1115_CONFIG_DR = {
	8: 0x0000,
	16: 0x0020,
	32: 0x0040,
	64: 0x0060,
	128: 0x0080,
	250: 0x00A0,
	475: 0x00C0,
	860: 0x00E0,
}

#set dafaults for this ADC
_DATA_RATE = 128
_SINGLE = 0x0100


class VacuumSensor:
	'''
	Makes a Pfeiffer Piranni vacuum sensor class instance by reading the output 
	of an Adafruit ADS1115 analog to digital converter.

	Channel 1 = vacuum
	'''

	def __init__(self, i2c: I2C, **kwargs):
		'''
		Initializes the class

		Parameters
		----------
		i2c : machine.I2C
			I2C instance pointing to the I2C connection

		name : str
			The name of the vacuum sensor

		adr : hex
			The I2C address to use for connection. Default should be 0x68 (0x48?)

		gain : int
			The signal gain to use. Can be: 2/3 (enter: 23), 1, 2, 4, 8, or 16. 
			Defaults to 1.
		'''

		#set attributes
		self.name = str(kwargs["name"])

		#make and initialize an ADS1115 class instance
		self.ads = ADS1115(i2c, **kwargs)

		#make analog in instances for each channel
		# vac = 2
		self.vacuumChannel = AnalogIn(self.ads, self.ads.P0)

	#function to get vacuum
	def getVacuum(self):
		'''
		Gets the current vacuum, in mbar
		'''
		
		#get voltage as float
		V = self.vacuumChannel.voltage

		#get V back to original value (used resistance voltage divider for ADC)
		U = V * ((_R1 + _R2)/_R2)

		#convert to pressure using log-linear scale in Pfeiffer manual (TPR 280)
		C = 5.5
		P = 10**(U - C)

		#print result
		print(P)


class AnalogIn:
	'''
	Class for reading the analog input values
	'''

	def __init__(self, ads: ADS1115, pin: int):
		'''
		Initializes the AnalogIn class

		Parameters
		----------
		ads : ADS1115
			The analog to digitcal converter class instance

		pin : int
			The pin to read
		'''

		#set attributes
		self._ads = ads
		self._pin = pin

	#function to get the value
	@property
	def value(self) -> int:
		'''
		Returns the value of an ADC pin as an integer

		Returns
		-------
		val : int
			The value of a given ADC pin (defined at initialization)
		'''

		val = self._ads.read(self._pin) << (16 - self._ads.bits)

		return val

	#function to get the voltage
	@property
	def voltage(self) -> float:
		'''
		Returns the voltage of a given ADC pin (defined at initialization)

		Returns
		-------
		V : float
			The voltage on the pin
		'''

		V = self.value * _ADS1X15_PGA_RANGE[self._ads.gain] / 32767

		return V


class ADS1115:
	'''
	Class for reading the analog to digital converter results
	'''

	def __init__(self, i2c: I2C, **kwargs):
		'''
		Initializes the class

		Parameters
		----------
		i2c : machine.I2C
			I2C instance pointing to the I2C connection

		adr : hex
			The I2C address to use for connection. Defaults to 0x48.

		gain : int
			The signal gain to use. Can be: 2/3, 1, 2, 4, 8, or 16. 
		'''

		#set attributes
		self.adr = int(kwargs["adr"], 0)
		self.i2c = i2c
		self.gain = int(kwargs["gain"])

		#set the pin integers
		self.P0 = 0
		self.P1 = 1
		self.P2 = 2
		self.P3 = 3

		#set the bits for ADS1115
		self.bits = 16
		
		#set the buffer
		self.buf = bytearray(3)
		self.singlebyte = bytearray(1)

	#function to take a reading
	def read(self, pin: int) -> int:
		'''
		Takes a reading on the given pin

		Parameters
		----------
		pin : int
			The pin to read, ranges from 0 to 3

		Returns
		-------
		val : int
			The resulting value
		'''

		#not differential, so add 0x04 (from adafruit library)
		pin = pin + 0x04

		#set configuration state (copying from adafruit library)
		config = _ADS1X15_CONFIG_OS_SINGLE
		config |= (pin & 0x07) << _ADS1X15_CONFIG_MUX_OFFSET
		config |= _ADS1X15_CONFIG_GAIN[self.gain]
		config |= _SINGLE
		config |= _ADS1115_CONFIG_DR[_DATA_RATE]
		config |= _ADS1X15_CONFIG_COMP_QUE_DISABLE

		#write to register and wait
		self._write_register(_ADS1X15_POINTER_CONFIG, config)
		
		#check if busy and, if so, wait
		while not self._read_register(_ADS1X15_POINTER_CONFIG) & 0X8000:
			pass

		#alternatively, just wait 0.015 seconds
		#time.sleep(0.015)

		#read back result
		res = self._read_register(_ADS1X15_POINTER_CONVERSION)

		#convert to voltage and return
		val = self._conversion_value(res)

		return val

	#helper function to read into the register
	def _read_register(self, reg: int) -> int:
		'''
		Reads into the device register

		Parameters
		----------
		reg : int
			The register to read into

		Returns
		-------
		val : int
			The readback value
		'''

		#set the byte
		self.singlebyte[0] = reg

		#write it to the thermocouple board
		self.i2c.writeto(self.adr, self.singlebyte)
		time.sleep(0.008)

		#read back result and return
		self.i2c.readfrom_into(self.adr, self.buf)

		return self.buf[0] << 8 | self.buf[1]

	#helper function to write to the register
	def _write_register(self, reg: int, value: int):
		'''
		Write 16 bit value to register

		Parameters
		----------
		reg : int
			The register to write to

		value : int
			The value to write
		'''

		#define the buf
		self.buf[0] = reg
		self.buf[1] = (value >> 8) & 0xFF
		self.buf[2] = value & 0xFF

		#then write
		self.i2c.writeto(self.adr, self.buf)


	#conversion function
	def _conversion_value(self, raw_adc: int) -> int:
		'''
		ADC board specific conversion value

		Parameters
		----------
		raw_adc : int
			The raw readback value

		Returns
		-------
		val : int
			The board-specific converted value
		'''
		raw_adc = raw_adc.to_bytes(2, "big")
		val = struct.unpack(">h", raw_adc)[0]
		return val

