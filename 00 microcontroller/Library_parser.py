# Library_parser.py
# 09. January 2025
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

'''
File to parse a bunch of tasks and messages
'''

#parser function
def parser(messageList, deviceList):
	'''
	Function to parse messages and pass them to connected devices

	Parameters
	----------
	messageList : list
		List of possible messages to send

	deviceList : list
		List of connected devices
	'''

	#start with empty list
	commandlist = []

	#loop through each message
	for message in messageList:

		#commands are space delimited; needs to split
		commands = message.split(" ", 2)

		#print help if needed (message below)
		if commands[0] == "help":
			print(helpmessage)

		#print device list if needed (message below)
		elif commands[0] == "deviceList":
			print(deviceListmessage)

			#loops through and prints each device name
			for device in deviceList.keys():
				print(f"-\t{device}")

		#otherwise, find the right device for the command
		elif commands[0] in deviceList.keys():

			#get the intsance of that device
			obj = deviceList[commands[0]]["Instance"]

			#get a list of attributes of that class instance
			# (ignoring doubleunder attributes)
			methods = [attribute for attribute in dir(obj)
					   if callable(getattr(obj, attribute))
					   and attribute.startswith('__') is False
					   ]
			
			#print list of possible commands for this particular device
			if len(commands) < 2 or commands[1] == "help":
				
				print(f'\nList of methods of {commands[0]}:')
				
				#loop through each method and print
				for method in methods:
					print(f"-\t{method}")

			#execute command if it's in the class instance attribute list
			elif commands[1] in methods:

				#add to command list
				com = {"Device": commands[0], "Method": commands[1]}

				#including kwargs if needed
				if len(commands) == 3: com["kwargs"] = commands[2]
				
				commandlist.append(com)

			#if device is correct, but method is wrong, print error:
			else:
				print(f'ERROR: Unknown method {commands[1]}. Type "{commands[0]}' \
					' help" for more information.')
		
		#finally if device is unknown, print error
		else:
			print(f'ERROR: Unknown device {commands[0]}. ' \
				' Type "help" for more information.')

	return commandlist


helpmessage = ('Welcome to the vacuum line double-trap software!\n'
			   '1. List of commands\n' 
			   '\t- help (gives this documentation)\n'
			   '\t- deviceList (lists all the devices)\n'
			   # '\t- TaskManager\n'
			   '\t- device (gives method parameters for device)\n\n'
			   '2. Examples\n'
			   '2.1 \tTurn on the onboard LED (simple "hello world" test)\n'
			   '\tonboardLED on\n'
			   '\tThis turns on the onboard LED on the Raspberry Pi Pico.'
			   )

deviceListmessage = ('\nList of active devices.\n'
					 'To modify this list, change "Library_deviceList.json"\n'
					 )