'''
micropython modbus package based on a stripped-down version of the Pycom
umodbus package

24. May 2022
Jordon D Hemingway
'''

from machine import Pin, UART
import struct
import time

from . import const

#make the modbus RTU serial class
class ModbusRTU(object):
	'''
	Makes a modbus RTU serial communcation object
	'''

	def __init__(
		self,
		bus: int,
		rx: Pin = None,
		tx: Pin = None,
		baudrate: int = 9600,
		bits: int = 8,
		stop: int = 8,
		parity: int = None,
		):
		'''
		Initializes the class
		
		Attributes
		----------
		bus : int
			The UART bus to use for communication

		rx : Pin
			The UART Rx pin

		tx : Pin
			The UART Tx pin

		baudrate : int
			The baud rate to use, defaults to 9600

		bits : int
			The number of bits per data byte, defaults to 8

		stop : int
			The number of stop bits, defaults to 1

		parity : None or int
			The parity to use, defaults to None
		'''

		#initialize the uart bus connection
		self._uart = UART(
			bus,
			tx = tx,
			rx = rx,
			baudrate = baudrate,
			bits = bits,
			stop = stop,
			parity = parity,
			)

	#define function to read coils
	def read_coils(
		self, 
		slave_id: int, 
		starting_addr: int, 
		count: int) -> list:
		'''
		Reads coils from the given slave device

		Parameters
		----------
		slave_id : int
			The ID value of the slave device

		starting_addr : int
			The initial coil address

		count : int
			The number of coils to read

		Returns
		-------
		coil_value : list
			List of current values in the coils
		'''

		#first check coil count is okay
		if not (1 <= count <= 2000):
			raise ValueError('invalid number of coils')

		#the get modbus_pdu
		modbus_pdu = struct.pack(
			'>BHH', 
			const.READ_COILS, 
			starting_addr, 
			count
			)

		#get response data
		resp_data = self._send_receive(modbus_pdu, slave_id, True)

		#convert byte to boolean string
		coil_value = self._bytes_to_bool(resp_data)

		#since this is an entire byte, need to drop final bits if input
		# bit length does not fill final byte
		full_bits = 8 * (count // 8)
		hanging_bits = count % 8

		#drop empty bits and return
		res = coil_value[:full_bits + hanging_bits]

		return res

	#define function to read discrete inputs (read-only coils)
	def read_discrete_inputs(
		self, 
		slave_id: int, 
		starting_addr: int, 
		count: int) -> list:
		'''
		Reads discrete inputs from the given slave device

		Parameters
		----------
		slave_id : int
			The ID value of the slave device

		starting_addr : int
			The initial discrete input address

		count : int
			The number of discrete inputs to read

		Returns
		-------
		discin_value : list
			List of current values in the discrete inputs
		'''
		#first check discrete input count is okay
		if not (1 <= count <= 2000):
			raise ValueError('invalid number of discrete inputs')

		#the get modbus_pdu
		modbus_pdu = struct.pack(
			'>BHH', 
			const.READ_DISCRETE_INPUTS, 
			starting_addr, 
			count
			)

		#get response data
		resp_data = self._send_receive(modbus_pdu, slave_id, True)

		#finally get the status
		discin_value = self._bytes_to_bool(resp_data)

		#since this is an entire byte, need to drop final bits if input
		# bit length does not fill final byte
		full_bits = 8 * (count // 8)
		hanging_bits = count % 8

		#drop empty bits and return
		res = discin_value[:full_bits + hanging_bits]

		return res

	#define function to read input registers
	def read_input_registers(
		self, 
		slave_id: int, 
		starting_addr: int, 
		count: int,
		signed: bool = True) -> list:
		'''
		Reads the given input registers from the slave device

		Parameters
		----------
		slave_id : int
			The ID value of the slave device

		starting_addr : int
			The initial register address

		count : int
			The number of registers to read

		signed : bool
			Whether or not the register values are signed (pos./neg.)

		Returns
		-------
		ireg_value : list
			List of current values in the registers
		'''

		#first check register count is okay
		if not (1 <= count <= 125):
			raise ValueError('invalid number of input registers')

		#get the modbus pdu
		modbus_pdu = struct.pack(
			'>BHH', 
			const.READ_INPUT_REGISTERS,
			starting_addr,
			count
			)

		#get response data
		resp_data = self._send_receive(modbus_pdu, slave_id, True)

		#finally, get the values
		ireg_value = self._to_short(resp_data, signed = signed)

		return ireg_value

	#define function to read holding resgisters
	def read_holding_registers(
		self, 
		slave_id: int, 
		starting_addr: int, 
		count: int,
		signed: bool = True) -> list:
		'''
		Reads the given holding registers from the slave device

		Parameters
		----------
		slave_id : int
			The ID value of the slave device

		starting_addr : int
			The initial register address

		count : int
			The number of registers to read

		signed : bool
			Whether or not the register values are signed (pos./neg.)

		Returns
		-------
		hreg_value : list
			List of current values in the registers
		'''

		#first check register count is okay
		if not (1 <= count <= 125):
			raise ValueError('invalid number of holding registers')

		#get the modbus pdu
		modbus_pdu = struct.pack(
			'>BHH', 
			const.READ_HOLDING_REGISTERS,
			starting_addr,
			count
			)

		#get response data
		resp_data = self._send_receive(modbus_pdu, slave_id, True)

		#finally, get the values
		hreg_value = self._to_short(resp_data, signed = signed)

		return hreg_value

	#define function to write single coil
	def write_single_coil(
		self, 
		slave_id: int, 
		output_addr: int, 
		output_value: bool) -> bool:
		'''
		Writes data to a single coil on the given slave device

		Parameters
		----------
		slave_id : int
			The ID value of the slave device

		output_addr : int
			The coil address to write to

		output_value : bool
			The value to write; must be False (0) or True (1)

		Returns
		-------
		success : bool
			Tells whether or not the writing was successful
		'''

		#check if value is okay and get to hex
		if output_value is False:
			val = 0x0000

		elif output_value is True:
			val = 0xFF00

		else:
			raise ValueError('illegal coil value')

		#get the modbus pdu
		modbus_pdu = struct.pack(
			'>BHH',
			const.WRITE_SINGLE_COIL, 
			output_addr, 
			val
			)

		#get response data
		resp_data = self._send_receive(modbus_pdu, slave_id, False)

		#confirm response data checks out
		op_status = self._validate_resp_data(
			resp_data,
			const.WRITE_SINGLE_COIL,
			output_addr,
			value = val,
			count = None,
			signed = False
			)

		return op_status

	#define function to write single holding register
	def write_single_register(
		self, 
		slave_id: int, 
		output_addr: int, 
		output_value: int,
		signed: bool = True) -> bool:
		'''
		Writes data to a single register on the given slave device

		Parameters
		----------
		slave_id : int
			The ID value of the slave device

		output_addr : int
			The register address to write to

		output_value : int
			The value to write

		signed : bool
			Tells whether the data written is signed or not (pos./neg.).
			Defaults to True.

		Returns
		-------
		success : bool
			Tells whether or not the writing was successful
		'''

		#get right format
		fmt = 'h' if signed else 'H'

		#get the modbus pdu
		modbus_pdu = struct.pack(
			'>BH'+fmt,
			const.WRITE_SINGLE_REGISTER, 
			output_addr, 
			output_value
			)

		#get response data
		resp_data = self._send_receive(modbus_pdu, slave_id, False)

		#confirm response data checks out
		op_status = self._validate_resp_data(
			resp_data,
			const.WRITE_SINGLE_REGISTER,
			output_addr,
			value = output_value,
			count = None,
			signed = signed
			)

		return op_status

	#define function to write multiple coils
	def write_multiple_coils(
		self, 
		slave_id: int, 
		starting_addr: int, 
		output_values: list) -> bool:
		'''
		Writes data to a multiple coils on the given slave device

		Parameters
		----------
		slave_id : int
			The ID value of the slave device

		output_addr : int
			The starting coil address to write to

		output_value : int
			The values to write; must be a list of 0s or 1s

		Returns
		-------
		success : bool
			Tells whether or not the writing was successful
		'''

		#section the list byte-wise
		sectioned_list = [output_values[i:i+8] for i in \
			range(0, len(output_values), 8)]

		#make empty list of values to write to slave
		write_vals = []

		#loop through each byte, do some byte logic, and add to list
		for index, byte in enumerate(sectioned_list):
			
			w = sum(v << i for i, v in enumerate(byte))
			write_vals.append(w)

		#get the right packing format
		fmt = 'B' * len(write_vals)

		#now get the modbus pdu
		modbus_pdu = struct.pack(
			'>BHHB'+fmt,
			const.WRITE_MULTIPLE_COILS,
			starting_addr,
			len(output_values), 
			((len(output_values) - 1) // 8) + 1,
			*write_vals)

		#get response data
		resp_data = self._send_receive(modbus_pdu, slave_id, False)

		#confirm response data checks out
		op_status = self._validate_resp_data(
			resp_data,
			const.WRITE_MULTIPLE_COILS,
			starting_addr,
			value = None,
			count = len(output_values),
			signed = False
			)

		return op_status

	#define function to write multiple holding registers
	def write_multiple_registers(
		self, 
		slave_id: int, 
		starting_addr: int, 
		output_values: list,
		signed: bool = True) -> bool:
		'''
		Writes data to a multiple holding registers on the given slave device

		Parameters
		----------
		slave_id : int
			The ID value of the slave device

		output_addr : int
			The starting register address to write to

		output_value : int
			The values to write

		signed : bool
			Tells whether the data written is signed or not (pos./neg.).
			Defaults to True.

		Returns
		-------
		success : bool
			Tells whether or not the writing was successful
		'''

		#get the count
		count = len(output_values)

		#first check register count is okay
		if not (1 <= count <= 123):
			raise ValueError('invalid number of registers')

		#get the packing format
		fmt = ('h' if signed else 'H') * count

		#now get the modbus pdu
		modbus_pdu = struct.pack(
			'>BHHB'+fmt,
			const.WRITE_MULTIPLE_REGISTERS,
			starting_addr,
			count, 
			count * 2,
			*output_values)
		
		#get response data
		resp_data = self._send_receive(modbus_pdu, slave_id, False)

		#confirm response data checks out
		op_status = self._validate_resp_data(
			resp_data,
			const.WRITE_MULTIPLE_REGISTERS,
			starting_addr,
			value = None,
			count = len(output_values),
			signed = signed
			)

		return op_status

	#------------------#
	# HELPER FUNCTIONS #
	#------------------#

	#function for converting byte list to boolean list
	def _bytes_to_bool(self, byte_list: list) -> list:
		'''
		Converts list of bytes to list of booleans

		Parameters
		----------
		byte_list : list
			List of bytes to convert

		Returns
		-------
		bool_list : list
			List of booleans
		'''

		bool_list = []

		#loop through and convert
		for index, byte in enumerate(byte_list):

			bool_list.extend([bool(byte & (1 << n)) for n in range(8)])

		return bool_list

	#function to convert data to crc16 format
	def _calculate_crc16(self, data: bytearray) -> bytearray:
		'''
		Converts data to crc16 format

		Parameters
		----------
		data : bytearray
			Array of data bytes

		Returns
		-------
		crc : bytearray
			Bytearray of crc16 formatted data
		'''

		crc = 0xFFFF

		#loop through and convert
		for char in data:
			crc = (crc >> 8) ^ const.CRC16_TABLE[((crc) ^ char) & 0xFF]

		crc16 = struct.pack('<H', crc)

		return crc16

	#function to decide whether or not to exit read loop
	def _exit_read(self, resp: bytearray) -> bool:
		'''
		Tells the program whether or not to exit a read loop

		Parameters
		----------
		resp : bytearray
			Array of response bytes

		Returns
		-------
		exit : bool
			Yes or no to exit
		'''

		if resp[1] >= const.ERROR_BIAS:
			if len(resp) < const.ERROR_RESP_LEN:
				return False
		
		elif (const.READ_COILS <= resp[1] <= const.READ_INPUT_REGISTERS):
			expected_len = const.RESPONSE_HDR_LENGTH + 1 + resp[2] + const.CRC_LENGTH
			if len(resp) < expected_len:
				return False
		
		elif len(resp) < const.FIXED_RESP_LEN:
			return False

		return True

	#function to read from uart
	def _uart_read(self) -> bytearray:
		'''
		Reads from the uart bus

		Returns
		-------
		resp : bytearray
			Array of bytes read from the slave
		'''

		#pre-define
		resp = bytearray()

		#loop through and read
		for x in range(1, 40):

			#append if anything to read
			if self._uart.any():
				resp.extend(self._uart.read())

				# variable length function codes may require multiple reads
				if self._exit_read(resp):
					break

			#sleep before next iteration
			time.sleep(0.05)

		return resp

	#function to send data to the slave device
	def _send(self, modbus_pdu: bytes, slave_id: int):
		'''
		Sends data to the slave device

		Parameters
		----------
		modbus_pdu : bytes
			The bytes object of the data to send

		slave_id : int
			The ID value of the slave device
		'''
		
		#define byte array
		serial_pdu = bytearray()
		serial_pdu.append(slave_id)
		serial_pdu.extend(modbus_pdu)

		#calculate the crc
		crc = self._calculate_crc16(serial_pdu)
		serial_pdu.extend(crc)

		#now write to uart
		self._uart.write(serial_pdu)

	#define send-receive helper function
	def _send_receive(
		self, 
		modbus_pdu: bytes, 
		slave_id: int, 
		ct: bool) -> bytearray:
		'''
		Sends and receives data to the slave device

		Parameters
		----------
		modbus_pdu : bytes
			The bytes object of the data to send

		slave_id : int
			The ID value of the slave device

		ct : bool
			Tells the function whether or not to count (what?)

		Returns
		-------
		res : bytearray
			Bytearray of resulting data
		'''
		
		#flush the Rx FIFO
		self._uart.read()

		#send data
		self._send(modbus_pdu, slave_id)

		#readback data
		res = self._validate_resp_hdr(
			self._uart_read(),
			slave_id,
			modbus_pdu[0],
			ct
			)

		return res

	#function to get short byte array
	def _to_short(self, byte_array: bytearray, signed: bool = True) -> list:
		'''
		Unpacks the data according to the format >h or >H

		Parameters
		----------
		byte_array : bytearray
			The data to unpack

		signed : bool
			Tells whether to unpack signed or unsigned data

		Returns
		-------
		res : list
			Unpacked data as list
		'''

		#get length of response
		resp_quant = int(len(byte_array) / 2)

		fmt = '>' + (('h' if signed else 'H') * resp_quant)
		res = struct.unpack(fmt, byte_array)

		return list(res)

	#function to validate write and read response agree
	def _validate_resp_data(
		self,
		data: bytearray,
		function_code: hex,
		addr: int,
		value: int = None,
		count: int = None,
		signed: bool = True
		) -> bool:
		'''
		Validates that the write and readback data match; used when writing to
		coils and registers

		Parameters
		----------
		data : bytearray
			Bytearray of the data written to the slave device

		function_code : hex
			The hex value of the function, either write to single/multiple coils
			or write to single/multiple registers.

		addr : int
			The coil/register address where data is to be written

		value : int or None
			For individual coil/register, the value to write.
			For multiple coil/register, should be None (not called).

		count : int or None
			For individual coil/register, should be none (not called).
			For multiple coil/register, the number of coils/registers written.

		signed : bool
			Tells whether to unpack signed or unsigned data (pos./neg.)

		Returns
		-------
		op_status : bool
			Tells whether or not the data match up
		'''

		#check if write single coil/register, do stuff:
		if function_code in \
			[const.WRITE_SINGLE_COIL, const.WRITE_SINGLE_REGISTER]:

			#get unpacking format
			fmt = '>H' + ('h' if signed else 'H')

			#get the response address and value
			resp_addr, resp_value = struct.unpack(fmt, data)

			#check they match the inputs
			if (addr == resp_addr) and (value == resp_value):
				return True

		#check if write multiple coil/register, do stuff:
		elif function_code in \
			[const.WRITE_MULTIPLE_COILS, const.WRITE_MULTIPLE_REGISTERS]:
			
			#get the response starting address and quantity
			resp_addr, resp_qty = struct.unpack('>HH', data)

			if (addr == resp_addr) and (count == resp_qty):
				return True

		return False

	#function to validate response
	def _validate_resp_hdr(
		self, 
		resp: bytearray, 
		slave_id: int, 
		func_code: bytes, 
		ct: bool) -> bytearray:
		'''
		Validate the response

		Parameters
		----------
		resp : bytearray
			The inputted bytearray of response data

		slave_id : int
			The ID value of the slave device

		func_code : bytes
			Byte containing the function code

		ct : bool
			Tells the function whether or not to count (what?)

		Returns
		-------
		res : bytearray
			The validated response
		'''

		#check if response. If not, raise error
		if len(resp) == 0:
			raise OSError('no data received from slave')

		#if so, get expected value
		resp_crc = resp[-const.CRC_LENGTH:]
		exp_crc = self._calculate_crc16(
			resp[0:len(resp) - const.CRC_LENGTH]
			)

		#check if response matches
		if ((resp_crc[0] is not exp_crc[0]) or (resp_crc[1] is not exp_crc[1])):
			raise OSError('invalid response CRC')

		#check if slave id matches
		if (resp[0] != slave_id):
			raise ValueError('wrong slave address')

		#check if slave returned error
		if (resp[1] == (func_code + const.ERROR_BIAS)):
			raise ValueError('slave returned exception code: {:d}'.
							 format(resp[2]))

		#get hdr length byte
		hdr_length = (const.RESPONSE_HDR_LENGTH + 1) if ct \
			else const.RESPONSE_HDR_LENGTH

		#finally, calculate result and return
		res = resp[hdr_length:len(resp) - const.CRC_LENGTH]
		
		return res
