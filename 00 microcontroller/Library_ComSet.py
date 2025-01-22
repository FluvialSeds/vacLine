# Library_ComSet.py
# 09. January 2025
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

'''
File to read the list of devices being controlled by the pi pico and get their
settings
'''

from Library_file import read_file
from machine import Pin, I2C

#set relative path to json files
jsonpth = 'json_files/'

#set relative path to driver files
drvpth = 'drivers.'

#get list of devices
deviceList = read_file(
	file_name = jsonpth + 'Library_deviceList.json'
	)

#make the I2C connection for all I2C-based devices

#get the I2C info from (pins and frequency)
i2cInfo = read_file(
	file_name = jsonpth + "Library_I2C.json"
	)

#make the connection
i2c = I2C(
	i2cInfo["bus"],
	sda = Pin(i2cInfo["sdaPin"]),
	scl = Pin(i2cInfo["sclPin"]),
	freq = i2cInfo["freq"]
	)

#dynamically import and initialize drivers for each device
for device in deviceList.values():
	
	#import module containing that driver code
	module = __import__(
		drvpth + f"Library_Drivers_{device['Driver']}",
		globals(),
		locals(),
		[f"{device['Driver']}"]
		)
	
	#check if it's an I2C device or not
	if "adr" in device["Parameter"]:

		#make the instance using the i2c-specific constructor
		device["Instance"] = getattr(
			module, 
			f"{device['Driver']}"
			)(i2c, **device["Parameter"])

	else:

		#make the instance using the non-i2c constructor
		device["Instance"] = getattr(
			module, 
			f"{device['Driver']}"
			)(**device["Parameter"])

#get list of settings
settings = read_file(
	file_name = jsonpth + 'Library_settings.json'
	)