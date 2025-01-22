# Library_Drivers_PID.py
# 26. May 2022
# Jordon D Hemingway

'''
File to make a driver for controlling Autonics PID controller
'''

from time import sleep
from machine import Pin
from umodbus import ModbusRTU

#set global constants (i.e., coil and register values)

#status coils
_COIL_RUN_STOP = 0
_COIL_AUTO_TUNE = 1
_COIL_PER_CH = 2

#input registers
_IREG_HARDWARE_VERSION = 102
_IREG_SOFTWARE_VERSION = 103

_IREG_CURRENT_TEMP = 1000
_IREG_DECIMAL = 1001
_IREG_TEMP_UNIT = 1002
_IREG_CURRENT_SET_TEMP = 1003
_IREG_HEATING_MV = 1004
_IREG_COOLING_MV = 1005
_IREG_PER_CH = 6

#holding registers

#MONITORING GROUP
_HREG_CURRENT_SET_TEMP = 0
_HREG_HEATING_MV = 1
_HREG_COOLING_MV = 2
_HREG_AUTO_MANUAL = 3

#CONTROL OPERATION GROUP
_HREG_RUN_STOP = 50
_HREG_MULTISV_NUM = 51
_HREG_SV0 = 52
_HREG_SV1 = 53
_HREG_SV2 = 54
_HREG_SV3 = 55

_HREG_AUTO_TUNE = 100
_HREG_HEAT_PROP_BAND = 101
_HREG_COOL_PROP_BAND = 102
_HREG_HEAT_INT_TIME = 103
_HREG_COOL_INT_TIME = 104
_HREG_HEAT_DEV_TIME = 105
_HREG_COOL_DEV_TIME = 106

_HREG_DEAD_OVERLAP_BAND = 107
_HREG_MANUAL_RESET = 108
_HREG_HEAT_HYST = 109
_HREG_HEAT_OFFSET = 110
_HREG_COOL_HYST = 111
_HREG_COOL_OFFSET = 112

_HREG_MV_LOW_LIMIT = 113
_HREG_MV_HIGH_LIMIT = 114

_HREG_RAMP_UP_RATE = 115
_HREG_RAMP_DOWN_RATE = 116
_HREG_RAMP_TIME_UNIT = 117

#INITIAL SETTING GROUP
_HREG_INPUT_TYPE = 150
_HREG_TEMP_UNIT = 151
_HREG_TEMP_BIAS = 152
_HREG_DIGITAL_FILTER = 153
_HREG_SV_LOW_LIMIT = 154
_HREG_SV_HIGH_LIMIT = 155

_HREG_OP_TYPE = 156
_HREG_CONTROL_METHOD = 157
_HREG_AUTO_TUNE_MODE = 158

_HREG_HEAT_CONTROL_TIME = 159
_HREG_COOL_CONTROL_TIME = 160

#CONTROL SETTING GROUP
_HREG_MULTI_SV = 200
_HREG_INIT_MANUAL_MV = 201
_HREG_PRESET_MANUAL_MV = 202
_HREG_SENSOR_ERROR_MV = 203
_HREG_STOP_MV = 204
_HREG_STOP_ALARM = 205

_HREG_PER_CH = 1000

#COMMUNICTION SETTING GROUP
_HREG_BAUDRATE = 300
_HREG_PARITY = 301
_HREG_STOP = 302
_HREG_RESP_WAIT_TIME = 303
_HREG_COMM_WRITE = 304
_HREG_PARAM_INIT = 305

#SKIPPING ALARM SETTING GROUP SINCE NOT USED HERE

#SENSOR TYPE LOOKUP TABLE
_SENSOR_TYPES = {
	'K':{False: 0, True: 1},
	'J':{False: 2, True: 3},
	'E':{False: 4, True: 5},
	'T':{False: 6, True: 7},
	'B':{False: 8, True: 8},
	'R':{False: 9, True: 9},
	'S':{False: 10},
	'N':{False: 11},
	'C':{False: 12},
	'G':{False: 13},
	'L':{False: 14, True: 15},
	'U':{False: 16, True: 17},
	'PlII':{False: 18},
	'JPt100':{False: 19, True: 20},
	'DPt100':{False: 21, True: 22},
	}

dict(zip(
	['K','J','E','T','B','R','S','N','C','G','L','U','PlII','JPt100','DPt100'],
	range(0,22,2)
	))

class PID:
	'''
	Makes a PID class instance (controls a single channel)
	'''

	def __init__(
		self, 
		decimal: bool = True, 
		tUnit: str = 'min',
		TUnit: str = 'C',
		**kwargs):
		'''
		Initialize the class

		Attributes
		----------
		name : str
			The name of the PID controller

		bus : int
			The bus channel to use

		id : str
			The RS-485 ID value

		baud : int
			The baud rate of the PID controller

		pinRx : int
			The receive pin number

		pinTx : int
			The transmit pin number

		ch : int
			The channel number of the given PID controller (1-4)

		type : float
			The thermocouple type, typically "K" or "E" here

		decimal : bool
			Tells the function whether or not to report 10ths of degrees.
			Defaults to True.

		tUnit : str
			The time units to use, either "sec", "min", or "hour". Defaults to
			"min".

		TUnit : str
			The temperature units to use, either "C" or "F". Defaults to "C".
		'''

		#set attributes
		self.name = kwargs["name"]
		self.id = int(kwargs["id"])
		self.bus = int(kwargs["bus"])
		self.baud = int(kwargs["baud"])
		self.pinRx = int(kwargs["pinRx"])
		self.pinTx = int(kwargs["pinTx"])
		self.ch = int(kwargs["ch"])
		self.type = str(kwargs["type"])
		
		#attributes for storing units
		self.decimal = decimal
		self.tUnit = tUnit
		self.TUnit = TUnit

		#save ModbusRTU attribute
		self.myModbus = ModbusRTU(
			self.bus, #given ID value
			baudrate = self.baud, #should be 9600, from Autonics manual
			tx = Pin(self.pinTx), #UART0 Tx (on LIP board from Philip)
			rx = Pin(self.pinRx), #UART0 Rx (on LIP board from Philip)
			bits = 8, #8 bits per character(from Autonics manual)
			parity = None, #no partiy (from Autonics manual)
			stop = 2, #number of stop bits (from Autonics manual)
			)

		#flag initial run status
		self.__flagRunning = not self.myModbus.read_coils(
			self.id,
			_COIL_RUN_STOP + _COIL_PER_CH * (self.ch - 1),
			1
			)[0]

		#setup units
		self._setup_units()

		#initialize sensor type
		self._set_sensor()

	#define function to autotune
	def autoTune(self):
		'''
		Autotunes PID controller
		'''
		
		#if running, raise error
		if not self.__flagRunning:
			raise AttributeError(
				f'{self.name} must be running to auto tune; start run first!'
				)

		#get the coil address
		addr = _COIL_AUTO_TUNE + _COIL_PER_CH * (self.ch - 1)

		#write to coil to start autotuning
		success = self.myModbus.write_single_coil(self.id, addr, True)

		#raise error if failed
		if not success:
			raise ValueError(f'{self.name} write to coil failed')

		else:
			#print running message
			print(self.name, 'autotune initiated; wait for completion')

		#now wait for autotune to finish
		# THIS WHILE LOOP HOLDS UP EVERYTHING ELSE! REMOVING!
		
		# while True:

		# 	#if no longer autotuning, print and break
		# 	if not self.myModbus.read_coils(self.id, addr, 1)[0]:

		# 		#print output
		# 		print(self.name, 'autotune completed')
		# 		break

		# 	#pause for a while before reading again
		# 	sleep(1)

	#define function to stop the autotune
	def stopAutoTune(self):
		'''
		Stops auto tuning; mostly for testing purposes
		'''

		#if running, raise error
		if not self.__flagRunning:
			raise AttributeError(
				f'{self.name} is not running, cannot be autotuning'
				)

		#get the coil address
		addr = _COIL_AUTO_TUNE + _COIL_PER_CH * (self.ch - 1)

		#if autotuning, stop the autotune
		if self.myModbus.read_coils(self.id, addr, 1)[0]:

			#write to coil to stop autotuning
			success = self.myModbus.write_single_coil(self.id, addr, False)

			#raise error if failed
			if not success:
				raise ValueError(f'{self.name} write to coil failed')

			else:
				#print running message
				print(self.name, 'autotune stopped')

		#otherwise, print that it's already not autotuning
		else:

			print(self.name, 'already was not autotuning')

	#define function to get current temperature
	def getTemp(self):
		'''
		Gets the current temperature, in whatever units are stored in the PID
		'''

		#get the register address
		addr = _IREG_CURRENT_TEMP + _IREG_PER_CH * (self.ch - 1)

		#read the register
		T = self.myModbus.read_input_registers(
			self.id, 
			addr, 
			1, 
			signed = True
			)[0]

		#sleep a few ms
		sleep(0.005)

		#if decimals, divide by 10
		if self.decimal:
			T /= 10

		print(T)

	#define a function to get the setpoint temperature
	def getSetTemp(self):
		'''
		Gets the setpint temperature, in whatever units are stored in the PID
		'''

		#get the register address
		addr = _IREG_CURRENT_SET_TEMP + _IREG_PER_CH * (self.ch - 1)

		#read the register
		T = self.myModbus.read_input_registers(
			self.id, 
			addr, 
			1, 
			signed = True
			)[0]

		#sleep a few ms
		sleep(0.005)

		#if decimals, divide by 10
		if self.decimal:
			T /= 10

		print(self.name, 'setpoint T:', T, self.TUnit)

	#define function to set temperature
	def setTemp(self, T: int):
		'''
		Sets the setpiont temperature, in whatever units are stored in the PID 
		controller

		Parameters
		----------
		T : int or float
			The temperature to set the setpoint to, in whatever units are stored
			in the PID controller. If not decimal, rounds to nearest integer T.
		'''

		#get the right address
		addr = _HREG_CURRENT_SET_TEMP + _HREG_PER_CH * (self.ch - 1)

		#get the value in right format
		if self.decimal:
			value = int(T)*10

		else:
			value = int(T)

		#write to register to set setpoint T
		success = self.myModbus.write_single_register(
			self.id, 
			addr, 
			value,
			signed = True)
		
		#sleep a few ms
		sleep(0.005)

		#raise error if failed
		if not success:
			raise ValueError(f'{self.name} write to register failed')

		else:
			#print success message
			print(self.name, 'setpoint T set to:', T, self.TUnit)

	#define function to get ramp rate
	def getRampRate(self):
		'''
		Gets the ramp rate, in whatever units are stored in the PID controller
		'''

		#get the register address
		addr = _HREG_RAMP_UP_RATE + _HREG_PER_CH * (self.ch - 1)

		#read the register
		R = self.myModbus.read_holding_registers(
			self.id, 
			addr, 
			1, 
			signed = True
			)[0]

		#sleep a few ms
		sleep(0.005)

		#if decimals, divide by 10 (I THINK I NEED TO DO THIS??)
		if self.decimal:
			R /= 10

		print(self.name, 'ramp rate:', R, self.TUnit, 'per', self.tUnit)

	#define function to set ramp rate
	def setRampRate(self, R: int):
		'''
		Sets the ramp rate according to the stored temperature and time units

		Parameters
		----------
		R : int or float
			The ramp rate to set, using time and temperature units stored in the
			PID object. 
		'''

		#get the right address
		addr = _HREG_RAMP_UP_RATE + _HREG_PER_CH * (self.ch - 1)

		#get the value in right format (I THINK I NEED TO DO THIS??)
		if self.decimal:
			value = int(R)*10

		else:
			value = int(R)

		#write to register to set setpoint T
		success = self.myModbus.write_single_register(
			self.id, 
			addr, 
			value,
			signed = True)

		#sleep a few ms
		sleep(0.005)

		#raise error if failed
		if not success:
			raise ValueError(f'{self.name} write to register failed')

		else:
			#print success message
			print(
				self.name, 'ramp rate set to:', R, self.TUnit, 'per', self.tUnit
				)

	#function to start run
	def startRun(self):
		'''
		Sets the PID controller to start a run. When started, it will begin to
		approach the setpoint temperature at the given ramp rate, both of which
		are set in the object.
		'''

		#get the coil number
		addr = _COIL_RUN_STOP + _COIL_PER_CH * (self.ch - 1)

		#if not running, start run
		if not self.__flagRunning:

			#write to coil to start run
			success = self.myModbus.write_single_coil(
				self.id,
				addr,
				False #false for run, true for stop (seems backwards...)
				)

			#raise error if failed
			if not success:
				raise ValueError(
					f'{self.name} write to coil failed'
					)

			else:

				#print running message
				print(self.name, 'run initiated')

				#update running flag
				self.__flagRunning = True

		else:

			#print already running message
			print(self.name, 'already running')

	#function to stop a run
	def stopRun(self):
		'''
		Stops the PID controller run
		'''

		#get the coil number
		addr = _COIL_RUN_STOP + _COIL_PER_CH * (self.ch - 1)

		#if running, stop run
		if self.__flagRunning:

			#write to coil to start run
			success = self.myModbus.write_single_coil(
				self.id,
				addr,
				True #false for run, true for stop (seems backwards...)
				)

			#raise error if failed
			if not success:
				raise ValueError(
					f'{self.name} write to coil failed'
					)

			else:

				#print running message
				print(self.name, 'run stopped')

				#update running flag
				self.__flagRunning = False

		else:

			#print already running message
			print(self.name, 'already not running')

	#function to get model name and hardware version
	def getVersion(self):
		'''
		Gets the hardware and software version numbers

		Returns
		-------
		versions : list
			List of version numbers, [hardware, software]
		'''

		#read the input registers
		versions = self.myModbus.read_input_registers(
			self.id,
			_IREG_HARDWARE_VERSION,
			2,
			signed = True
			)

		print(self.name,'Hardware and software versions:',versions)

	#function to set thing sup and make sure units are correct
	def _setup_units(self):
		'''
		Sets up the time and temperature units for the PID controller
		'''

		#make sure attributes are correct, and get appropriate register value

		#time units
		if self.tUnit in ['s','sec','S','Sec','seconds','Seconds']:
			tRegVal = 0

		elif self.tUnit in ['m','min','M','Min','minutes','Minutes']:
			tRegVal = 1

		elif self.tUnit in ['h','hr','H','Hr','hours','Hours']:
			tRegVal = 2

		else:
			raise ValueError(
				f'{self.name} time unit must be "sec", "min", or "hour"'
				)

		#temp units
		if self.TUnit in ['c','C','celsius','Celsius']:
			TRegVal = 0

		elif self.TUnit in ['F','f','fahrenheit','Fahrenheit']:
			TRegVal = 1

		else:
			raise ValueError(
				f'{self.name} temp unit must be "C" or "F"'
				)

		#get the corresponding register numbers
		tRegAddr = _HREG_RAMP_TIME_UNIT + _HREG_PER_CH * (self.ch - 1)
		TRegAddr = _HREG_TEMP_UNIT + _HREG_PER_CH * (self.ch - 1)

		#now write the holding registers
		for addr, value in zip([tRegAddr, TRegAddr],[tRegVal, TRegVal]):

			success = self.myModbus.write_single_register(
				self.id,
				addr,
				value,
				signed = False
				)

			#raise error if failed
			if not success:
				raise ValueError(
					f'{self.name} write to register failed'
					)

	#function to set sensor type
	def _set_sensor(self):
		'''
		Sets the sensor type (thermocouple or pT100) and sig figs
		'''

		#make sure sensor type is allowed
		if self.type not in _SENSOR_TYPES.keys():
			raise ValueError(
				f'{self.name} type must be in {list(_SENSOR_TYPES.keys())}'
				)

		#get register value from lookup table
		try:
			value = _SENSOR_TYPES[self.type][self.decimal]

		except KeyError:
			raise ValueError(
				f'{self.name} type {self.type} cannot print degree decimals'
				)

		#write value to register and check read-back
		addr = _HREG_INPUT_TYPE + _HREG_PER_CH * (self.ch - 1)

		success = self.myModbus.write_single_register(
			self.id,
			addr,
			value,
			signed = False
			)

		#raise error if failed
		if not success:
			raise ValueError(
				f'{self.name} write to register failed'
				)
