# Library_Drivers_MFC.py
# 25. April 2022
# Jordon D Hemingway

'''
File to make a driver for reading LIP custom-built TCD.
'''

class TCD:
	'''
	Makes a TCD class instance
	'''
	
	def __init__(self, i2c: I2C, **kwargs):
		'''
		Initializes the class
		
		Attributes
		----------
		i2c : machine.I2C
			I2C instance pointing to the I2C connection

		name : str
			The name of the TCD

		adr : hex
			The I2C address to use for connection. Defaults to 0x69.
		
		bits : int
			Number of bits for communication with MCP3422 ADC. Can be 12,
			14, 16, or 18. Defaults to 18.
		
		channel : int
			Channel for communicating with MCP3422 ADC. Can be 1 or 2.
			Defaults to 1.
		
		gain : int
			The signal gain to use. Can be: 1, 2, 4, or 8. Defaults to 1.
		'''
		
		#set attributes
		self.name = str(kwargs["name"])
		self.adr = int(kwargs["adr"], 0)
		self.i2c = i2c
		self.bits = int(kwargs["bits"])
		self.channel = int(kwargs["channel"])
		self.gain = int(kwargs["gain"])
		
		#define dicts for sending commands
		#As defined in circuitpython code from Lukas, values defined
		# in MCP3422 ADC documentation
		self._bits_dict = {
			12: 0b00,
			14: 0b01,
			16: 0b10,
			18: 0b11,
			}
		
		self._channel_dict = {
			1: 0b00,
			2: 0b01,
			}
		
		self._gain_dict = {
			1: 0b00,
			2: 0b01,
			4: 0b10,
			8: 0b11,
			}
		
		#this is a command with some bitwise operators that came from
		# Lukas's code, but I'm not entirely sure what it means
		val = 0b1 << 7 | self._channel_dict[self.channel] << 5 | \
				0b1 << 4 | self._bits_dict[self.bits] << 2 | \
					self._gain_dict[self.gain]
		
		#now write this to the ADC
		self.i2c.writeto(self.adr, bytes([val]))
	
	#define function to read output
	def getSignal(self):
		'''
		Reads TCD signal and prints the result, in microvolts.
		'''
		
		#first define the size of the bytearray to write to (depends on bits)
		if self.bits > 15:
			res = bytearray(3)
		
		else:
			res = bytearray(2)
		
		#read current value and write into res
		self.i2c.readfrom_into(self.adr, res)
		
		#now parse result (depends on bits)
		# This was taken from Lukas' code, assumign it's written in the MCP3442 
		# ADC manual
		
		# for the case of 18 bits:
		if self.bits == 18:
			
			x = (res[0]&0b1) << 16 | res[1] << 8 | res[2]
			
			#switch signs if needed
			if res[0]&0b10 == 1:
				x = -1*x
			
			sig_uv = x*15.625
		
		# for the case of 16 bits:
		elif self.bits == 16:
			
			x = (res[0]&0b1111111) << 8 | res[1]
			
			#switch signs if needed
			if res[0]&0b10000000 == 1:
				x = -1*x
			
			sig_uv = x*62.5
		
		# for the case of 14 bits:
		elif self.bits == 14:
			
			x = (res[0]&0b11111) << 8 | res[1]
			
			#switch signs if needed
			if res[0]&0b100000 == 1:
				x = -1*x
			
			sig_uv = x*62.5
		
		# for the case of 12 bits:
		elif self.bits == 12:

			x = (res[0]&0b111) << 8 | res[1]
			
			#switch signs if needed
			if res[0]&0b1000 == 1:
				x = -1*x
			
			sig_uv = x*1000

		else:
			raise ValueError('Invalid bits: {self.bits}. Must be 12, 14, 16, 18')
		
		print(sig_uv)

