# Library_Drivers_MFC.py
# 09. January 2025
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

'''
File to make a driver for getting and setting flow of Axetris 2022 MFC.
'''

from time import sleep, ticks_ms, ticks_diff
from machine import Pin, UART

class MFC:
	'''
	Makes an MFC class instance
	'''

	def __init__(self, **kwargs):
		'''
		Initialize the class

		Attributes
		----------
		name : str
			The name of the MFC controller

		bus : int
			The bus channel to use

		baud : int
			The baud rate of the cryo cooler

		pinRx : int
			The receive pin number

		pinTx : int
			The transmit pin number

		maxFlow : int
			The maximum flow rate, in sccm. This is device-specific and
			determined at the time of purchase.

		'''

		#set attributes
		self.name = kwargs["name"]
		self.bus = int(kwargs["bus"])
		self.baud = int(kwargs["baud"])
		self.pinRx = int(kwargs["pinRx"])
		self.pinTx = int(kwargs["pinTx"])
		self.maxFlow = int(kwargs["maxFlow"])
		
		#initialize the uart bus
		self.initUart()

	#define funciton to get temperature
	def getTemp(self):
		'''
		Get the current temperature from MFC thermocouple
		'''
		
		#initialize the uart bus
		# self.initUart()

		#define command
		# from Axetris data sheet:
		#	0x61 = read variable
		#	0x0F = ADC_temp
		cmd = [0x61, 0x0F]

		#calculate checksum by adding up all the values inside the command array
		chksum = sum(cmd)

		#add checksum to the command array
		cmd.extend([chksum % 256])

		#now send command to read temp
		self.myUart.write(bytearray(cmd))

		#----------------------------------------------------------------------#
		# USE STATIC RESPONSE

		#statically wait for response and read
		sleep(0.02) #20 milliseconds

		i1 = self.myUart.read()

		sleep(0.02) #another 20 milliseconds
		#----------------------------------------------------------------------#

		#convert output hex to int
		k = (i1[1]*256 + i1[2])

		#calculate temp value in Celsius using Axetris data sheet (Sec. 7.4)
		c1 = 65535
		c2 = 1./6
		c3 = 0.01

		T_C = (k/c1 - c2)/c3

		#print output to browser window
		# print(self.name,'temp.:',T_C,'deg. C')
		print(T_C)

	#define function to get flow rate
	def getFlow(self):
		'''
		Get the current flow rate from the MFC, in sccm
		'''

		#initialize the uart bus
		# self.initUart()

		#define command
		# from Axetris data sheet:
		#	0x31 = read flow rate
		cmd = [0x31]

		#now send command to read flow
		self.myUart.write(bytearray(cmd))

		#----------------------------------------------------------------------#
		# USE STATIC RESPONSE

		#statically wait for response and read
		sleep(0.02) #20 milliseconds

		i1 = self.myUart.read()

		sleep(0.02) #another 20 milliseconds
		#----------------------------------------------------------------------#

		#convert output hex to int
		k = (i1[1]*256 + i1[2])

		#calculate flow value in sccm using Axetris data sheet (Sec. 7.1)
		c1 = 10000
		c2 = self.maxFlow #this is MFC-specific
		
		Q_sccm = (k/c1)*c2

		#print output to browser window
		# print(self.name,'flow:',Q_sccm,'sccm')
		print(Q_sccm)

	#define function to get serial number
	def getSerialNumber(self):
		'''
		Get the serial number of this MFC
		'''

		#initialize the uart bus
		# self.initUart()

		#define command
		# from Axetris data sheet:
		#	0x61 = read variable
		#	0x00 = serial number
		cmd = [0x61, 0x00]

		#calculate checksum by adding up all the values inside the command array
		chksum = sum(cmd)

		#add checksum to the command array
		cmd.extend([chksum % 256])

		#now send command to read serial number
		self.myUart.write(bytearray(cmd))

		#----------------------------------------------------------------------#
		# USE STATIC RESPONSE

		#statically wait for response and read
		sleep(0.02) #50 milliseconds

		i1 = self.myUart.read()

		sleep(0.02) #another 20 milliseconds
		#----------------------------------------------------------------------#

		#convert output hex to int
		k = (i1[1]*256 + i1[2])

		#print output to browser window
		print(self.name,'Serial Number:',k)

	#define function to set flow rate
	def setFlow(self, flow: float):
		'''
		Set the MFC flow rate, in ccm
		'''
		
		#initialize the uart bus
		# self.initUart()

		#get write command in the correct form

		#calculate flow value in sccm using Axetris data sheet (Sec. 7.2)
		c1 = 65535
		c2 = self.maxFlow #this is MFC-specific

		stp = int((float(flow) / c2) * c1)
		val = stp.to_bytes(2, "big")

		#define command
		# from Axetris data sheet:
		#	0x62 = write variable
		#	0x14 = set mass flow
		cmd = [0x62, 0x14]
		cmd.extend(val) #add inputted value to command

		#calculate checksum by adding up all the values inside the command array
		chksum = sum(cmd)

		#add checksum to the command array
		cmd.extend([chksum % 256])

		#now send command to set flow
		self.myUart.write(bytearray(cmd))

		#----------------------------------------------------------------------#
		# USE STATIC RESPONSE

		#statically wait for response and read
		sleep(0.02) #50 milliseconds

		i1 = self.myUart.read()

		sleep(0.02) #another 20 milliseconds
		#----------------------------------------------------------------------#

		#now check if the sent back request, indicating success
		if i1 is not None and i1[0] == (0x62):

			#decode outputted value
			# Qset_sccm = str(i1.decode())
			print(self.name,'flow set to: %.1f sccm' % float(flow))

		else:

			#print failure message
			print(self.name,'flow set attempt failed')

	#define function to re-init the uart bus
	def initUart(self):
		'''
		Initializes the UART bus.
		'''

		#init uart
		self.myUart = UART(
			self.bus, #given ID value
			baudrate = self.baud, #from Axetris data sheet
			tx = Pin(self.pinTx), #UART multi Tx (on LIP board from Philip)
			rx = Pin(self.pinRx), #UART multi Rx (on LIP board from Philip)
			bits = 8, #8 bits per character( from Axetris data sheet)
			parity = 1, #parity bit odd (from Axetris data sheet)
			stop = 1, #number of stop bits (from Axetris data sheet)
			)

