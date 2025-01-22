#TODO:
# *debug drawlines error when running on PC (SHOULD FIX WITH NEWEST PYQTGRAPH VERSION)
# *debug MFC error (DONE BUT NEED TO CHECK ON REAL SETUP) 
# *add wait time to ViciValve setter (readback error) (DONE BUT NEED TO CHECK ON REAL SETUP)

import numpy as np

import csv
import re
import serial
import time
import traceback
import sys
import os

from datetime import datetime
import time
from time import sleep

from typing import List

from PyQt5.uic import loadUi
from PyQt5.QtCore import (
	QTimer, 
	QObject, 
	QThreadPool,
	QRunnable, 
	pyqtSignal,
	pyqtSlot
	)

from PyQt5.QtGui import QIcon

#testing with pyqtgraph
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui
from pyqtgraph.Qt.QtWidgets import QMainWindow, QFileDialog, QToolBar, \
	QTableWidget, QTableWidgetItem, QMessageBox, QLineEdit, QDialogButtonBox, \
	QFormLayout, QDialog

# from pyqtgraph.Qt.QtWidgets import QTableWidget, QTableWidgetItem

#import file with icons
import qrc_icons

#make plot backgroudn gray
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

#need to do some path magic for executable to run properly
if getattr(sys, 'frozen', False):
    current_path = os.path.dirname(sys.executable)
else:
    current_path = str(os.path.dirname(__file__))

#make class for main widget
class WidgetMain(QMainWindow):
	'''
	Class for the main widget of the aTrois system command software
	For now, just testing things out
	'''

	def __init__(self, path):
		'''
		Initialize the class instance

		Parameters
		----------
		path : str
			String of path to the corresponding .ui file

		'''

		# READ-IN PARAMETERS #
		#--------------------#
		self.readIOStartup()

		#TESTING METHOD RUNNING THREADPOOL
		self.methodThreadpool = QThreadPool()
		self.methodThreadpool.setMaxThreadCount(1)

		#start the threadpool for real-time updates
		self.threadpool = QThreadPool()
		self.threadpool.setMaxThreadCount(1)

		#get time of initialization
		self._t0 = time.time()

		#initialize the superclass and load the .ui file
		super(WidgetMain, self).__init__()
		loadUi(path, self)

		#set attributes from .ui file

		#========#
		# DIALOG #
		#========#

		#clickable buttons
		self.clearButton.clicked.connect(self.clearDialog)
		self.disconnectButton.clicked.connect(self.disconnect)
		self.saveButton.clicked.connect(self.saveDialog)

		#connect either by hitting 'connect' or by pressing enter
		self.connectButton.clicked.connect(self.connect)
		self.portInput.returnPressed.connect(self.connect)

		#send command either by hitting 'send' or pressing enter
		self.sendButton.clicked.connect(self.sendCom)
		self.commandInput.returnPressed.connect(self.sendCom)

		# DIALOG INITIAL STATES #
		#-----------------------#
		self.connected = False
		self.running = False
		self.waiting = False
		self.devList = None #make none until connected

		#===============#
		# CONFIGURATION #
		#===============#

		# VALVES GROUP BOX #
		#------------------#
		#"set" buttons
		self.SetH2SwitchingValveButton.clicked.connect(self.setH2SwitchingValve)
		self.SetCOSwitchingValveButton.clicked.connect(self.setCOSwitchingValve)
		self.SetHFSwitchingValveButton.clicked.connect(self.setHFSwitchingValve)
		self.SetSelectorValveButton.clicked.connect(self.setSelectorValve)

		#clockwise checkbox for main selector
		self.selectorCWCheckbox.stateChanged.connect(self.setSelectorCCCW)

		#position labels (ensure larger font size)
		self.labelH2SwitchingValve.setFont(QtGui.QFont("Arial", 24))
		self.labelHFSwitchingValve.setFont(QtGui.QFont("Arial", 24))
		self.labelCOSwitchingValve.setFont(QtGui.QFont("Arial", 24))
		self.labelSelectorValve.setFont(QtGui.QFont("Arial", 24))
		
		# FLOW RATES GROUP BOX #
		#----------------------#
		#on/off valve checkboxes
		self.h2valveCheckbox.stateChanged.connect(self.h2OpenClose)
		self.hevalveCheckbox.stateChanged.connect(self.heOpenClose)
		self.covalveCheckbox.stateChanged.connect(self.coOpenClose)
		self.h2ovalveCheckbox.stateChanged.connect(self.h2oOpenClose)

		#"set" buttons
		self.SetHeFlowButton.clicked.connect(self.setHeFlow)
		self.SetH2FlowButton.clicked.connect(self.setH2Flow)
		self.SetCOFlowButton.clicked.connect(self.setCOFlow)

		#flow labels (ensure larger font size)
		self.labelH2Flow.setFont(QtGui.QFont("Arial", 24))
		self.labelHeFlow.setFont(QtGui.QFont("Arial", 24))
		self.labelCOFlow.setFont(QtGui.QFont("Arial", 24))
		self.labelH2OFlow.setFont(QtGui.QFont("Arial", 24))
		self.labelH2OTemp.setFont(QtGui.QFont("Arial", 24))
		self.labelCryoCoolerVacuum.setFont(QtGui.QFont("Arial", 24))

		# TEMPERATURES GROUP BOX #
		#------------------------#
		#"set" buttons
		self.SetT1TempButton.clicked.connect(self.setT1Temp)
		self.SetT2TempButton.clicked.connect(self.setT2Temp)
		self.SetTHFTempButton.clicked.connect(self.setTHFTemp)
		self.SetBoschOvenTempButton.clicked.connect(self.setBoschOvenTemp)
		self.SetCoF3OvenTempButton.clicked.connect(self.setCoF3OvenTemp)
		self.SetCryoCoolerTempButton.clicked.connect(self.setCryoCoolerTemp)

		#temp labels (ensure larger font size)
		self.labelT1Temp.setFont(QtGui.QFont("Arial", 24))
		self.labelT2Temp.setFont(QtGui.QFont("Arial", 24))
		self.labelTHFTemp.setFont(QtGui.QFont("Arial", 24))
		self.labelBoschOvenTemp.setFont(QtGui.QFont("Arial", 24))
		self.labelCoF3OvenTemp.setFont(QtGui.QFont("Arial", 24))
		self.labelCryoCoolerTemp.setFont(QtGui.QFont("Arial", 24))

		# CONFIGURATION INITIAL STATES #
		#------------------------------#
		#switching valves
		self._flagH2SwitchingPos = 1 #start in Pos 1
		self._flagCOSwitchingPos = 1 #start in Pos 1
		self._flagHFSwitchingPos = 1 #start in Pos 1
		self._flagSelectorPos = None #initiate but then set during goHome

		#on/off valves
		self._flagValveH2In = False #start with flow off
		self._flagValveHeIn = False #start with flow off
		self._flagValveCOIn = False #start with flow off
		self._flagValveH2OIn = False #start with flow off

		#selector valve
		self._flagSelectorCW = False #starts off in clockwise direction

		#cryocooler running and ready flags
		self._flagCryoCoolerRunning = False
		self._flagCryoCoolerReady = False

		#set the main tab default to "config"
		self.mainTabs.setCurrentIndex(0)

		#set the display flags to none
		
		#FLOW RATES
		self._currentCOFlow = None
		self._currentH2Flow = None
		self._currentHeFlow = None
		self._currentH2OFlow = None

		# TEMPERATURES
		self._currentT1Temp = None
		self._currentT2Temp = None
		self._currentTHFTemp = None
		self._currentBoschOvenTemp = None
		self._currentCoF3OvenTemp = None
		self._currentCryoCoolerTemp = None
		self._cryoCoolerSetTemp = None
		self._currentH2OTemp = None

		# PASSIVE SENSORS
		self._currentPressureSensorTemp = None
		self._currentPressureSensorPres = None
		self._currentTCDSignal = None
		self._currentCryoCoolerVacuum = None
		self._currentCryoCoolerPower = None

		# CONFIGURATION LOG TIMERS #
		#--------------------------#

		#set interval
		self.j = 2500 #2.5 seconds

		#initialize config timer (just one for all devices)
		self.configTimer = QTimer(self)
		self.configTimer.setInterval(self.j)
		self.configTimer.timeout.connect(self.updateConfig)

		#=================#
		# REAL-TIME PLOTS #
		#=================#

		# PLOT LOG BUTTONS #
		#------------------#

		self.startPlotButton.clicked.connect(self.startPlot)
		self.stopPlotButton.clicked.connect(self.stopPlot)
		self.clearPlotButton.clicked.connect(self.clearPlot)
		self.savePlotButton.clicked.connect(self.savePlot)

		# MAIN PLOTS WIDGET #
		#-------------------#

		#make plotting frame layout
		self.l = QtWidgets.QVBoxLayout()
		self.mainPlot.setLayout(self.l)

		#make plot for holding all real-time results
		self.plt = pg.PlotWidget(name = "mainPlots")
		self.plt.addLegend()
		self.l.addWidget(self.plt)

		#set Y label
		self.plt.setLabel('left', 'Signal', units = 'Units')
		self.plt.setYRange(-200,600)

		#set X label to be date-time
		axis = pg.DateAxisItem()
		self.plt.setAxisItems({'bottom':axis})
		self.plt.setLabel('bottom', 'date time')

		#adjust spacing
		self.l.setSpacing(0.)
		self.l.setContentsMargins(0., 0., 0., 0.)

		#add empty plots to fill later
		self.plotters = {
			'T1T': {'name': 'T_1 T (C)',					#temperatures
					'c': (39, 112, 0),
					'attr': '_currentT1Temp'
					},
			'T2T': {'name': 'T_2 T (C)',
					'c': (58, 163, 0),
					'attr': '_currentT2Temp'
					},
			'THFT': {'name': 'T_HF T (C)',
					'c': (84, 240, 0),
					'attr': '_currentTHFTemp'
					},
			'bpT': {'name': 'baseplate T (C)',
					'c': (131, 240, 72),
					'attr': '_currentCryoCoolerTemp'
					},
			'boT': {'name': 'Bosch oven T (C)',
					'c': (88, 0, 112),
					'attr': '_currentBoschOvenTemp'
					},
			'coT': {'name': 'CoF3 oven T (C)',
					'c': (129, 0, 163),
					'attr': '_currentCoF3OvenTemp'
					},
			'H2OT': {'name': 'H2O jacket T (C)',
					'c': (203, 72, 240),
					'attr': '_currentH2OTemp'
					},
			'psT': {'name': 'pressure sensor T (C)',
					'c': (188, 0, 240),
					'attr': '_currentPressureSensorTemp'
					},
			'HeFl': {'name': 'He flow rate (ccm)',			#flow rates
					'c': (11, 88, 212),
					'attr': '_currentHeFlow'
					},
			'H2Fl': {'name': 'H2 flow rate (ccm)',
					'c': (0, 152, 235),
					'attr': '_currentH2Flow'
					},
			'COFl': {'name': 'CO flow rate (ccm)',
					'c': (11, 195, 212),
					'attr': '_currentCOFlow'
					},
			'H2OFl': {'name': 'H2O jacket flow rate (ccm)',
					'c': (12, 246, 200),
					'attr': '_currentH2OFlow'
					},
			'selPos': {'name': 'selector valve position',	#valve positions
					'c': (0, 0, 0),
					'attr': '_flagSelectorPos'
					},
			'H2Pos': {'name': 'H2 valve position',
					'c': (75, 75, 75),
					'attr': '_flagH2SwitchingPos'
					},
			'HFPos': {'name': 'HF valve position',
					'c': (150, 150, 150),
					'attr': '_flagHFSwitchingPos'
					},
			'COPos': {'name': 'CO valve position',
					'c': (225, 225, 225),
					'attr': '_flagCOSwitchingPos'
					},
			'TCD': {'name': 'TCD signal (mV)',				#passive signals
					'c': (227, 40, 11),
					'attr': '_currentTCDSignal'
					},
			'psP': {'name': 'pressure sensor P (bar)', 
					'c': (237, 143, 12),
					'attr': '_currentPressureSensorPres'
					},
			'ccV': {'name': 'cryo cooler vacuum (mbar)',
					'c': (247, 203, 112),
					'attr': '_currentCryoCoolerVacuum'
					},
			'ccP': {'name': 'cryo cooler power (W)',
					'c': (230, 183, 12),
					'attr': '_currentCryoCoolerPower'
					}
		}

		#add empty plots to fill later
		for p in self.plotters:

			#make plot
			self.plotters[p]['instance'] = self.plt.plot(
				name = self.plotters[p]['name'],
				)

			#set color
			self.plotters[p]['instance'].setPen(
				color = self.plotters[p]['c'],
				width = 5,
				)

		# PLOTTER LOG TIMER #
		#-------------------#

		#set interval

		#initialize plotter timer (just one for all plots)
		self.plotTimer = QTimer(self)
		self.plotTimer.setInterval(self.j)
		self.plotTimer.timeout.connect(self.updatePlots)

		# PLOTTER DATA STORAGE #
		#----------------------#

		#make empty list for each plotter to add data into
		for p in self.plotters:

			#add empty list
			self.plotters[p]['data'] = np.array([])

		#also make empty list for timestamps
		self.plotTimeStamps = np.array([])

		# PLOT INITIAL STATES #
		#---------------------#
		self.plotting = False

		#===============#
		# METHOD EDITOR #
		#===============#

		# METHOD TABLE #
		#--------------#
		# self._triggerFile = os.path.join(current_path,'id_trigger_file.txt')
		# self._methodFolder = current_path
		self._saveTraces = False
		self._saveTracesPath = None
		self._currentSample = None
		self._currentMethod = None

		#set row and column counts
		self.methodTable.setRowCount(20)
		self.methodTable.setColumnCount(4)

		#set top row headers and make top row un-editable
		heads = [
			'Time (min)',
			'Device',
			'Event',
			'Notes',
			]

		for i, h in enumerate(heads):

			#make item and edit font
			item = QTableWidgetItem(h)
			item.setFont(QtGui.QFont("Arial", 18))

			#make uneditable
			item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEnabled)

			#add to table
			self.methodTable.setItem(0, i, item)

			#make colums default a bit wider
			self.methodTable.setColumnWidth(i, 125+50*i)

		# METHOD BUTTONS #
		#----------------#

		self.LoadMethodButton.clicked.connect(self.loadMethod)
		self.ClearMethodButton.clicked.connect(self.clearMethod)
		self.AddRowBelowButton.clicked.connect(self.addRowBelow)
		self.AddRowAboveButton.clicked.connect(self.addRowAbove)
		self.DeleteRowButton.clicked.connect(self.deleteRow)
		self.SaveMethodButton.clicked.connect(self.saveMethod)

		# TRIGGER WAIT LOG TIMERS #
		#-------------------------#

		#set interval
		self.k = 1000 #read file every 1 second

		#initialize trigger wait timer
		self.triggerTimer = QTimer(self)
		self.triggerTimer.setInterval(self.j)
		self.triggerTimer.timeout.connect(self.readTriggerFile)

		#==========#
		# MENU BAR #
		#==========#

		# ACTIONS #
		#---------#

		#file menu:
		#opens
		self.actionOpenMethod.triggered.connect(self.loadMethod)
		self.actionOpenTraces.triggered.connect(self.loadPlot)
		self.actionOpenDialog.triggered.connect(self.loadDialog)

		#saves
		self.actionSaveMethod.triggered.connect(self.saveMethod)
		self.actionSaveTraces.triggered.connect(self.savePlot)
		self.actionSaveDialog.triggered.connect(self.saveDialog)

		#edit menu:
		#edit method
		self.actionEditMethod.triggered.connect(self.editMethod)
		self.actionTriggerFile.triggered.connect(self.setTriggerFile)
		self.actionMethodFolder.triggered.connect(self.setMethodFolder)

		#run menu:
		self.actionCCInitialize.triggered.connect(self.initializeCC)
		self.actionCCShutDown.triggered.connect(self.shutDownCC)
		self.actionSetCCSafetyChecks.triggered.connect(self.setCCChecksWindow)
		self.actionStart.triggered.connect(self.startRun)
		self.actionStop.triggered.connect(self.stopRunByUser)
		self.actionTriggerStart.triggered.connect(self.startSequence)
		self.actionTriggerStop.triggered.connect(self.stopSequence)

		#=========#
		# TOOLBAR #
		#=========#

		# CREATE TOOLBAR #
		#----------------#

		self.mainToolbar = QToolBar('Actions')
		self.addToolBar(self.mainToolbar)

		# TOOLBAR BUTTONS #
		#-----------------#

		#set icons for each action
		self.actionStart.setIcon(QIcon(":run-start"))
		self.actionStop.setIcon(QIcon(":run-stop"))
		self.actionTriggerStart.setIcon(QIcon(":trigger-start"))
		self.actionTriggerStop.setIcon(QIcon(":trigger-stop"))
		self.actionCCInitialize.setIcon(QIcon(":cryocooler-start"))
		self.actionCCShutDown.setIcon(QIcon(":cryocooler-stop"))

		#add to toolbar
		self.mainToolbar.addAction(self.actionCCInitialize)
		self.mainToolbar.addAction(self.actionCCShutDown)
		self.mainToolbar.addAction(self.actionStart)
		self.mainToolbar.addAction(self.actionStop)
		self.mainToolbar.addAction(self.actionTriggerStart)
		self.mainToolbar.addAction(self.actionTriggerStop)

		# BASIC PARAMETERS #
		#------------------#

		#water flow settings for auto shutdown
		# self._minH2OFlow = 750 #ccm
		# self._maxH2OTemp = 25 #C
		# self._ccTempTol = 20 #C
		# self._maxCryoCoolerTemp = 30 #C (from Sunpower manual)

		# SAFETY CHECK TIMER #
		#--------------------#

		#initialize config timer (just one for all devices)
		self.safetyCheckTimer = QTimer(self)
		self.safetyCheckTimer.setInterval(2 * self.j) #make it a bit longer
		self.safetyCheckTimer.timeout.connect(self.safetyCheck)

		#============#
		# STATUS BAR #
		#============#

		self.statusBar().showMessage(
			'Current Status: Not Connected'
			)

	#~~~~~~~~~~~~~~~~~#
	# BASIC FUNCTIONS #
	#~~~~~~~~~~~~~~~~~#

	#safety box that prevents you from closing while connected
	def closeEvent(self, event):
		'''
		Check that it's good go close the software
		'''
		#save io_file output
		self.writeIOShutdown()
		
		# if connected, cannot close
		if self.connected:
			e = QMessageBox.information(self,'', "Cannot close program while connected to" \
				" devices. Please disconnect first!", buttons = QMessageBox.Ok)

			if e == QMessageBox.Ok:
				event.ignore()

	#function to print to dialog browser
	def print(self, text):
		'''
		Prints output to the readback browser

		Parameters
		----------
		text : str
			String of text to print
		'''

		#make sure it's not None (implying not connected)
		if text is not None:

			#get the existing text
			t = self.readbackBrowser.toPlainText()

			#add a timestamp
			now = datetime.now()
			s = now.strftime("%Y %m %d %H:%M:%S")
			
			#add to existing text
			t += "\n" + s + "\t" + text
			
			#send updated text to browser
			self.readbackBrowser.setPlainText(t)

	#function for communicating with raspberry pi
	def read_write(self, cmd, parse = 'print'):
		'''
		Basic method by which commands are sent to and read from the raspberry
		pi pico controller

		Parameters
		----------
		cmd: str
			String of the command text

		parse: string
			Tells the function how to parse the returned data; must be a string
			of an attribute of the main window. Defaults to print to browser.
		'''

		if self.connected:

			#convert parse string to attribute
			parseAttr = getattr(self, parse)

			#link the worker to the execute function
			w = Worker(self.executeReadWrite, cmd)
			w.signals.result.connect(parseAttr)

			#start the thread
			self.threadpool.start(w)

		else:
			self.print('Not connected')

	#read-write execution function to be called when making the worker
	def executeReadWrite(self, cmd):
		'''
		Executer function sent to the threadpool worker

		Parameters
		----------
		cmd: str
			String of the command text
		'''

		#encode the message and send it to the connection (write)
		mw = cmd + '\n'
		mw = mw.encode()
		self.connection.write(mw)

		#now get the returned message and return it
		mrt = self.connection.readline().decode("utf-8")
		mr = str(mrt)[0:-2] #remove final \n
		
		#return for setting readouts
		return mr

	#function for communicating with raspberry pi (when sending from dialog)
	# allows for reading multi-line commands
	def read_write_multiline(self, cmd, parse = 'print'):
		'''
		Method by which commands are sent to and read from the raspberry
		pi pico controller and multi-line commands are read

		Parameters
		----------
		cmd: str
			String of the command text

		parse: string
			Tells the function how to parse the returned data; must be a string
			of an attribute of the main window. Defaults to print to browser.
		'''

		if self.connected:

			#convert parse string to attribute
			parseAttr = getattr(self, parse)

			#link the worker to the execute function
			w = Worker(self.executeReadWriteMultiline, cmd)
			w.signals.result.connect(parseAttr)

			#start the thread
			self.threadpool.start(w)

		else:
			self.print('Not connected')

	#read-write execution function to be called when making the worker
	def executeReadWriteMultiline(self, cmd):
		'''
		Executer function sent to the threadpool worker

		Parameters
		----------
		cmd: str
			String of the command text
		'''

		#encode the message and send it to the connection (write)
		mw = cmd + '\n'
		mw = mw.encode()
		self.connection.write(mw)

		#now get the returned message and return it
		# read up to 1000 bytes
		mrt = self.connection.read(1000).decode("utf-8")
		mr = str(mrt)[0:-2] #remove final \n
		
		#return for setting readouts
		return mr

	#~~~~~~~~~~~~~~~~~~#
	# DIALOG FUNCTIONS #
	#~~~~~~~~~~~~~~~~~~#

	#function to clear 
	def clearDialog(self):
		'''
		Clears the readback browser
		'''
		self.readbackBrowser.clear()

	#function to connect to raspberry pi
	def connect(self):
		'''
		Connects to the raspberry pi pico on the given port
		'''

		#connect if not already
		if not self.connected:

			#get the port and print it to the browser
			port = self.portInput.text()

			#print that we're now connecting
			self.print('Connecting to port: {}'.format(port))

			#now try connecting
			try:
				self.connection = serial.Serial(
					port = port,
					baudrate = 9600, #value from Philip
					bytesize = 8, #value from Philip
					# timeout = 2, #value from Philip
					timeout = 0.25 #much shorter timeout
					)

				#print and change states if successful
				self.connected = True
				self.print('Successfully connected\n')

				#change status bar to not running
				self.statusBar().showMessage(
					'Current Status: Connected, not Running'
					)

				#get device list and store as attribute
				self.devList = self.getDevList()

				#move everything to home state on startup
				self.goHome()

				#start reading temps and flow rates to print to config panel
				self.configTimer.start()

				#start safety check timer
				self.safetyCheckTimer.start()

				#get initial cryo cooler set point (stored in controller)
				self.getCryoCoolerSetTemp()

			except Exception as e:

				#print the exception in the browser
				self.print("Couldn't connect. Raised: \n {}".format(str(e)))

		#otherwise state that we're already connected
		else:
			self.print('Already connected')

	#function to disconnect from raspberry pi
	def disconnect(self):
		'''
		Disconnect from the raspberry pi pico on the given port
		'''

		#disconnect if not already
		if self.connected:

			#get the port we're currently connected to
			comPort = self.connection.port

			#print that we're disconnecting
			self.print('Disconnecting from port: {}'.format(comPort))

			#now try disconnecting
			try:

				#stop timers, wait for threads to finish, and clear
				self.configTimer.stop()
				self.stopPlot()

				self.threadpool.clear()
				time.sleep(1.5*self.j/1000) #get to seconds

				#close the connection
				self.connection.close()

				#print and change states if successful
				self.connected = False
				self.print('Successfully disconnected')

				#change status bar to not connected
				self.statusBar().showMessage(
					'Current Status: Not Connected'
					)

				#blank-out config panel
				self.blankConfig()

			except Exception as e:

				#print the exception in the browser
				self.print("Couldn't disconnect. Raised exception: \n")
				self.print(e)

		#otherwise state that we're already disconnected
		else:
			self.print('Already disconnected') 

	#function to save dialog browser contents
	def saveDialog(self):
		'''
		Save the browser window to a .txt file 
		'''

		#bring up query for file name
		path = QFileDialog.getSaveFileName(self, 'Save File', '', 'TXT(*.txt)')

		#save the field if file name was not blank
		if path[0] != '':
			with open(path[0], 'w') as outfile:

				#save the data
				outfile.write(self.readbackBrowser.toPlainText())

	#function to load an existing dialog browser text
	def loadDialog(self):
		'''
		Loads some existing dialog text
		'''

		#bring up query for file name
		path = QFileDialog.getOpenFileName(self, 'Open File', '', 'TXT(*.txt)')

		if path[0] != '':
			with open(path[0], 'r') as infile:

				self.readbackBrowser.appendPlainText(infile.read())

	#function to send command to read/write function
	def sendCom(self):
		'''
		Send commands via the read_write function
		'''
		# self.read_write(self.commandInput.text())
		self.read_write_multiline(self.commandInput.text())

	#~~~~~~~~~~~~~~~~~~~~~~~~~#
	# CONFIGURATION FUNCTIONS #
	#~~~~~~~~~~~~~~~~~~~~~~~~~#

	# UPDATE FUNCTIONS #
	#------------------#

	#function to perform safety checks and do emergency shutdown if needed
	def safetyCheck(self):
		'''
		Performs safety checks and shuts down if needed
		'''

		# CRYO COOLER CHECKS #
		#--------------------#

		#if cryo cooler is running, perform safety checks
		if self._flagCryoCoolerRunning:

			#cryo cooler water jacket flow and temp
			if not self.ccSafetyCheck():

				#shut down cryo cooler and wait a second
				self.shutDownCC()
				sleep(1)

				#close the water flow valve if it's open
				if self._flagValveH2OIn:
					# self.h2ovalveCheckbox.setChecked(False)
					self.read_write('valveH2OIn close')

				#print result to dialog
				self.print('EMERGENCY CRYO COOLER SHUTDOWN! CLOSING H2O VALVE!')

			#if it passes checks, then get ready status
			else:
					self._flagCryoCoolerReady = self.ccStatus()

	#function to receive the new values and update display
	def updateConfig(self):
		'''
		Updates the real-time display values using workers in a threadpool
		'''

		#read_write and parse to update text

		# FLOW ON/OFF VALVES

		# He gas on/off valve
		self.read_write(
			'valveHeIn getPos',
			parse = 'updateCheckboxHeIn'
			)

		# H2 gas on/off valve
		self.read_write(
			'valveH2In getPos',
			parse = 'updateCheckboxH2In'
			)

		# CO gas on/off valve
		self.read_write(
			'valveCOIn getPos',
			parse = 'updateCheckboxCOIn'
			)

		# H2O jacket on/off valve
		self.read_write(
			'valveH2OIn getPos',
			parse = 'updateCheckboxH2OIn'
			)

		# SWITCHING VALVES

		# H2 switching (VICI) valve
		self.read_write(
			'valveSwitchingH2 getPos',
			parse = 'updateLabelH2Switching'
			)

		# HF switching (VICI) valve
		self.read_write(
			'valveSwitchingHF getPos',
			parse = 'updateLabelHFSwitching'
			)

		# CO switching (VICI) valve
		self.read_write(
			'valveSwitchingCO getPos',
			parse = 'updateLabelCOSwitching'
			)

		# SELECTOR VALVE
		self.read_write(
			'valveSelector getPos',
			parse = 'updateLabelSelectorValve'
			)

		# FLOW RATES

		#CO flow
		self.read_write(
			'mfcCOIn getFlow',
			parse = 'updateLabelCOFlow',
			)

		#H2 flow
		self.read_write(
			'mfcH2In getFlow',
			parse = 'updateLabelH2Flow'
			)

		#He flow
		self.read_write(
			'mfcHeIn getFlow',
			parse = 'updateLabelHeFlow'
			)

		#H2O flow
		self.read_write(
			'waterSensor h2oFlow',
			parse = 'updateLabelH2OFlow'
			)

		#H2O tmep
		self.read_write(
			'waterSensor h2oTemp',
			parse = 'updateLabelH2OTemp'
			)

		# TEMPERATURES

		#T1 temp
		self.read_write(
			'pidT1 getTemp',
			parse = 'updateLabelT1Temp'
			)

		#T2 temp
		self.read_write(
			'pidT2 getTemp',
			parse = 'updateLabelT2Temp'
			)

		#THF temp
		self.read_write(
			'pidTHF getTemp',
			parse = 'updateLabelTHFTemp'
			)

		#Bosch oven temp
		self.read_write(
			'pidBoschOven getTemp',
			parse = 'updateLabelBoschOvenTemp'
			)

		#CoF3 oven temp
		self.read_write(
			'pidCoF3Oven getTemp',
			parse = 'updateLabelCoF3OvenTemp'
			)

		#Cryocooler temp
		self.read_write(
			'cryoCooler getTemp',
			parse = 'updateLabelCryoCoolerTemp'
			)

		# PASSIVE SENSORS

		#Pressure sensor temperature
		self.read_write(
			'pressureSensorH2 getTemp',
			parse = 'updateLabelPressureSensorTemp',
			)

		#Pressure sensor pressure
		self.read_write(
			'pressureSensorH2 getPres',
			parse = 'updateLabelPressureSensorPres',
			)

		#TCD signal
		self.read_write(
			'tcdGC getSignal',
			parse = 'updateLabelTCDSignal',
			)

		#CryoCooler vacuum
		self.read_write(
			'vacuumSensor getVacuum',
			parse = 'updateLabelCryoCoolerVacuum'
			)

		#CryoCooler power
		self.read_write(
			'cryoCooler getPower',
			parse = 'updateLabelCryoCoolerPower'
			)

	#label update helper functions
	def updateCheckboxHeIn(self, p):
		'''
		Updates the He flow on/off checkbox label
		'''

		try:
			#read current state from device
			io = bool(int(p))

			#if readback and checkbox disagree, change checkbox state
			if self.hevalveCheckbox.isChecked() != io:

				#set flag to current state
				self._flagValveHeIn = io
				sleep(0.005) #wait a bit before going into trigger function

				#and change checkbox
				self.hevalveCheckbox.setChecked(io)

		#catch error if returns string
		except ValueError:
			pass

	def updateCheckboxH2In(self, p):
		'''
		Updates the H2 flow on/off checkbox label
		'''

		try:
			#read current state from device
			io = bool(int(p))

			#if readback and checkbox disagree, change checkbox state
			if self.h2valveCheckbox.isChecked() != io:

				#set flag to current state
				self._flagValveH2In = io
				sleep(0.005) #wait a bit before going into trigger function

				#and change checkbox
				self.h2valveCheckbox.setChecked(io)

		#catch error if returns string
		except ValueError:
			pass

	def updateCheckboxCOIn(self, p):
		'''
		Updates the CO flow on/off checkbox label
		'''

		try:
			#read current state from device
			io = bool(int(p))

			#if readback and checkbox disagree, change checkbox state
			if self.covalveCheckbox.isChecked() != io:

				#set flag to current state
				self._flagValveCOIn = io
				sleep(0.005) #wait a bit before going into trigger function

				#and change checkbox
				self.covalveCheckbox.setChecked(io)

		#catch error if returns string
		except ValueError:
			pass

	def updateCheckboxH2OIn(self, p):
		'''
		Updates the H2O flow on/off checkbox label
		'''

		try:
			#read current state from device
			io = bool(int(p))

			#if readback and checkbox disagree, change checkbox state
			if self.h2ovalveCheckbox.isChecked() != io:

				#set flag to current state
				self._flagValveH2OIn = io
				sleep(0.005) #wait a bit before going into trigger function

				#and change checkbox
				self.h2ovalveCheckbox.setChecked(io)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelH2Switching(self, p):
		'''
		Updates the H2 switching valve position label
		'''

		try:
			pos = int(p)+1 #change indexing
			self.labelH2SwitchingValve.setText(str(pos))
			self._flagH2SwitchingPos = pos

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelHFSwitching(self, p):
		'''
		Updates the HF switching valve position label
		'''

		try:
			pos = int(p)+1 #change indexing
			self.labelHFSwitchingValve.setText(str(pos))
			self._flagHFSwitchingPos = pos

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelCOSwitching(self, p):
		'''
		Updates the CO switching valve position label
		'''

		try:
			pos = int(p)+1 #change indexing
			self.labelCOSwitchingValve.setText(str(pos))
			self._flagCOSwitchingPos = pos

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelSelectorValve(self, p):
		'''
		Updates the selector valve position label
		'''

		try:
			#get last bit of string as int
			pos = int(p.split(' ')[-1])
			self.labelSelectorValve.setText(str(pos))
			self._flagSelectorPos = pos

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelCOFlow(self, q):
		'''
		Updates the CO Flow label
		'''

		try:
			self.labelCOFlow.setText('%.1f ccm' % float(q))
			self._currentCOFlow = float(q)

		#if returns string, try pausing then try again
		except ValueError:
			pass

	def updateLabelH2Flow(self, q):
		'''
		Updates the H2 Flow label
		'''
		try:
			self.labelH2Flow.setText('%.1f ccm' % float(q))
			self._currentH2Flow = float(q)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelHeFlow(self, q):
		'''
		Updates the He Flow label
		'''

		try:
			self.labelHeFlow.setText('%.1f ccm' % float(q))
			self._currentHeFlow = float(q)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelH2OFlow(self, q):
		'''
		Updates the H2O Flow label
		'''

		try:
			self.labelH2OFlow.setText('%.1f ccm' % float(q))
			self._currentH2OFlow = float(q)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelT1Temp(self, T):
		'''
		Updates the T1 temp label
		'''

		try:
			self.labelT1Temp.setText('%.1f C' % float(T))
			self._currentT1Temp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelT2Temp(self, T):
		'''
		Updates the T2 temp label
		'''

		try:
			self.labelT2Temp.setText('%.1f C' % float(T))
			self._currentT2Temp = float(T)
		
		#catch error if returns string
		except ValueError:
			pass

	def updateLabelTHFTemp(self, T):
		'''
		Updates the THF temp label
		'''

		try:
			self.labelTHFTemp.setText('%.1f C' % float(T))
			self._currentTHFTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelBoschOvenTemp(self, T):
		'''
		Updates the Bosch oven temp label
		'''

		try:
			self.labelBoschOvenTemp.setText('%.1f C' % float(T))
			self._currentBoschOvenTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelCoF3OvenTemp(self, T):
		'''
		Updates the CoF3 oven temp label
		'''

		try:
			self.labelCoF3OvenTemp.setText('%.1f C' % float(T))
			self._currentCoF3OvenTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelCryoCoolerTemp(self, T):
		'''
		Updates the Cryo cooler temp label
		'''

		try:
			self.labelCryoCoolerTemp.setText('%.1f C' % float(T))
			self._currentCryoCoolerTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelH2OTemp(self, T):
		'''
		Updates the H2O Temp label
		'''

		try:
			self.labelH2OTemp.setText('%.1f C' % float(T))
			self._currentH2OTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelCryoCoolerVacuum(self, P):
		'''
		Updates the current Pirani gauge value
		'''

		try:
			self.labelCryoCoolerVacuum.setText('%.1e mbar' % float(P))
			self._currentCryoCoolerVacuum = float(P)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelCryoCoolerPower(self, P):
		'''
		Updates the current cryo cooler power being used
		'''

		try:
			self._currentCryoCoolerPower = float(P)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelPressureSensorTemp(self, T):
		'''
		Updates the current pressure sensor temp value
		'''

		try:
			self._currentPressureSensorTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelPressureSensorPres(self, P):
		'''
		Updates the current pressure sensor pressure value
		'''

		try:
			self._currentPressureSensorPres = float(P)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelTCDSignal(self, S):
		'''
		Updates the current TCD signal value
		'''

		try:
			self._currentTCDSignal = float(S)

		#catch error if returns string
		except ValueError:
			pass


	# VALVE FUNCTIONS #
	#-----------------#

	#function to switch the H2 vici switching valve
	def setH2SwitchingValve(self):
		'''
		Sets Vici switching valve position for H2 Bosch oven

		Pos 1 = no voltage on pin
		Pos 2 = 24 V on pin
		'''
		
		#get current position
		cp = self._flagH2SwitchingPos

		#get set position from spinbox
		sp = self.H2SwitchingValveSpinBox.value()

		#send command to toggle
		if sp != cp and sp == 1:
			self.read_write('valveSwitchingH2 close')

		elif sp != cp and sp == 2:
			self.read_write('valveSwitchingH2 open')

		else:
			self.print('already at set position')

	#function to switch the HF waste vici switching valve
	def setHFSwitchingValve(self):
		'''
		Sets Vici switching valve position for HF waste
		
		Pos 1 = no voltage on pin
		Pos 2 = 24 V on pin
		'''
		
		#get current position
		cp = self._flagHFSwitchingPos

		#get set position from spinbox
		sp = self.HFSwitchingValveSpinBox.value()

		#send command to toggle
		if sp != cp and sp == 1:
			self.read_write('valveSwitchingHF close')

		elif sp != cp and sp == 2:
			self.read_write('valveSwitchingHF open')

		else:
			self.print('already at set position')

	#function to switch the CO sample loop vici switching valve
	def setCOSwitchingValve(self):
		'''
		Sets Vici switching valve for CO ref gas sample loop
		
		Pos 1 = no voltage on pin
		Pos 2 = 24 V on pin
		'''

		#get current position
		cp = self._flagCOSwitchingPos

		#get set position from spinbox
		sp = self.COSwitchingValveSpinBox.value()

		#send command to toggle
		if sp != cp and sp == 1:
			self.read_write('valveSwitchingCO close')

		elif sp != cp and sp == 2:
			self.read_write('valveSwitchingCO open')

		else:
			self.print('already at set position')

	#function to determine selector valve rotation direction
	def setSelectorCCCW(self):
		'''
		Sets the clockwise or counter-clockwise direction
		'''
		#toggle flagged state
		self._flagSelectorCW = not self._flagSelectorCW

	#function to switch the main vici selector valve
	def setSelectorValve(self):
		'''
		Sets Vici selector valve position
		'''

		#get current position
		cp = self._flagSelectorPos

		#get set position from spinbox
		sp = self.SelectorValveSpinBox.value()

		#get direction to move in
		if self._flagSelectorCW:
			d = 'CW'

		else:
			d = 'CC'

		#send command to move position
		if sp != cp:
			cmd = str(sp) + d

			self.read_write(f'valveSelector setPos {cmd}')

		else:
			self.print('already at set position')

		# #if connected:
		# if self.connected:

		# 	#toggle flagged state
		# 	self._flagSelectorPos = sp

		# 	#finally, update current position text
		# 	self.labelSelectorValve.setText(str(sp))

	#function to send selector valve home
	def setSelectorValveHome(self):
		'''
		Sends the Vici selector to the home position
		'''

		#if connected:
		if self.connected:

			#send command
			self.read_write(f'valveSelector setHome')

			# #toggle flagged state
			# self._flagSelectorPos = 1

			# #finally, update current position text
			# self.labelSelectorValve.setText(str(1))

	#function to get selector valve position
	def getSelectorValve(self):
		'''
		Gets current selector valve position
		'''
		return self._flagSelectorPos

	# FLOW RATE FUNCTIONS #
	#---------------------#

	#on/off valves:
	#function to open/close H2 on/off valve
	def h2OpenClose(self):
		'''
		Toggles H2 valve open/closed
		'''
		
		#if current and checkbox disagree, then send command to toggle
		if self._flagValveH2In != self.h2valveCheckbox.isChecked():

			#send command to toggle
			if self.h2valveCheckbox.isChecked():
				self.read_write('valveH2In open')
			else:
				self.read_write('valveH2In close')

			# and toggle flagged state
			self._flagValveH2In = self.h2valveCheckbox.isChecked()

	#function to open/close He on/off valve
	def heOpenClose(self):
		'''
		Toggles He valve open/closed
		'''
		
		#if current and checkbox disagree, then send command to toggle
		if self._flagValveHeIn != self.hevalveCheckbox.isChecked():

			#send command to toggle
			if self.hevalveCheckbox.isChecked():
				self.read_write('valveHeIn open')
			else:
				self.read_write('valveHeIn close')

			# and toggle flagged state
			self._flagValveHeIn = self.hevalveCheckbox.isChecked()

	#function to open/close CO on/off valve
	def coOpenClose(self):
		'''
		Toggles CO valve open/closed
		'''
		
		#if current and checkbox disagree, then send command to toggle
		if self._flagValveCOIn != self.covalveCheckbox.isChecked():

			#send command to toggle
			if self.covalveCheckbox.isChecked():
				self.read_write('valveCOIn open')
			else:
				self.read_write('valveCOIn close')

			# and toggle flagged state
			self._flagValveCOIn = self.covalveCheckbox.isChecked()

	#function to open/close H2O on/off valve
	def h2oOpenClose(self):
		'''
		Toggles H2O water jacket valve open/closed
		'''
		
		#if current and checkbox disagree, then send command to toggle
		if self._flagValveH2OIn != self.h2ovalveCheckbox.isChecked():

			#send command to toggle
			if self.h2ovalveCheckbox.isChecked():
				self.read_write('valveH2OIn open')
			else:
				self.read_write('valveH2OIn close')

			# and toggle flagged state
			self._flagValveH2OIn = self.h2ovalveCheckbox.isChecked()

	#flow setters:
	#function to set He flow rate
	def setHeFlow(self):
		'''
		Sets the flow rate of the He MFC
		'''
		
		#read value from spin box
		qccm = self.HeFlowSpinBox.value()

		#send command
		cmd = 'mfcHeIn setFlow ' + str(qccm)
		self.read_write(cmd)

	#function to set H2 flow rate
	def setH2Flow(self):
		'''
		Sets the flow rate of the H2 MFC
		'''
		#read value from spin box
		qccm = self.H2FlowSpinBox.value()

		#send command
		cmd = 'mfcH2In setFlow ' + str(qccm)
		self.read_write(cmd)

	#function to set CO flow rate
	def setCOFlow(self):
		'''
		Sets the flow rate of the CO MFC
		'''

		#read value from spin box
		qccm = self.COFlowSpinBox.value()

		#send command
		cmd = 'mfcCOIn setFlow ' + str(qccm)
		self.read_write(cmd)

	# TEMPERATURE FUNCTIONS #
	#-----------------------#

	#temp setters:
	#function to set trap T_1 temperature
	def setT1Temp(self):
		'''
		Sets the temperature for trap T1
		'''

		#read value from spin box
		qccm = self.T1TempSpinBox.value()

		#send command
		cmd = 'pidT1 setTemp ' + str(qccm)
		self.read_write(cmd)

	#function to set trap T_2 temperature
	def setT2Temp(self):
		'''
		Sets the temperature for trap T2
		'''

		#read value from spin box
		qccm = self.T2TempSpinBox.value()

		#send command
		cmd = 'pidT2 setTemp ' + str(qccm)
		self.read_write(cmd)

	#function to set trap T_HF temperature
	def setTHFTemp(self):
		'''
		Sets the temperature for trap THF
		'''

		#read value from spin box
		qccm = self.THFTempSpinBox.value()

		#send command
		cmd = 'pidTHF setTemp ' + str(qccm)
		self.read_write(cmd)

	#function to set Bosch oven temperature
	def setBoschOvenTemp(self):
		'''
		Sets the temperature for the Bosch oven
		'''
		
		#read value from spin box
		qccm = self.BoschOvenTempSpinBox.value()

		#send command
		cmd = 'pidBoschOven setTemp ' + str(qccm)
		self.read_write(cmd)

	#function to set CoF3 oven temperature
	def setCoF3OvenTemp(self):
		'''
		Sets the temperature for the CoF3 oven
		'''

		#read value from spin box
		qccm = self.CoF3OvenTempSpinBox.value()

		#send command
		cmd = 'pidCoF3Oven setTemp ' + str(qccm)
		self.read_write(cmd)

	#function to set CryoCooler baseplate temperature
	def setCryoCoolerTemp(self):
		'''
		Sets the temperature for the CryoCooler baseplate
		'''

		#read value from spin box
		cct = self.CryoCoolerTempSpinBox.value()

		#send command
		cmd = 'cryoCooler setTemp ' + str(cct)
		self.read_write(cmd)

		#read it back and update attribute
		self.getCryoCoolerSetTemp()

	#temp getter

	#function to get cryo cooler set temp and store as attribute
	def getCryoCoolerSetTemp(self):
		'''
		Gets the cryo cooler set temperature, in C, and updates attribute
		'''

		self.read_write(
			'cryoCooler getSetTemp',
			parse = 'updateCryoCoolerSetTemp',
			)

	#label update helper functions
	def updateCryoCoolerSetTemp(self, T):
		'''
		Updates the cryo cooler set temp attribute
		'''

		try:
			self._cryoCoolerSetTemp = float(T)

		#if returns string, try pausing then try again
		except ValueError:
			pass

	#~~~~~~~~~~~~~~~~~~~~#
	# PLOTTING FUNCTIONS #
	#~~~~~~~~~~~~~~~~~~~~#

	# PLOT LOGGER BUTTON FUNCTIONS #
	#------------------------------#

	#function to start plot logging
	def startPlot(self):
		'''
		Starts the plot logger
		'''
		
		if self.connected:
			if not self.plotting:

				#start plot timer
				self.plotTimer.start()
				self.plotting = True

			else:
				self.print("Already plotting")

		else:
			self.print("Not connected")

	#function to stop plot logging
	def stopPlot(self):
		'''
		Stops the plot logger
		'''

		if self.connected:
			if self.plotting:

				#stop plot timer
				self.plotTimer.stop()
				self.plotting = False

			else:
				self.print("Already not plotting")

		else:
			self.print("Not connected")

	#function to clear plot log
	def clearPlot(self):
		'''
		Clears the current plot log
		'''

		#make each plotter data into an empty list
		for p in self.plotters:

			#add empty list
			self.plotters[p]['data'] = np.array([])

		#make timestamp list empty also
		self.plotTimeStamps = np.array([])

		if self.connected:
			#then update the plots to be nothing
			self.updatePlots()

		else:
			self.print("Not connected")

	#function to save logged plot data
	def savePlot(self):
		'''
		Saves the plot log data
		'''

		#bring up query for file name
		path = QFileDialog.getSaveFileName(self, 'Save File', '', 'CSV(*.csv)')

		#save the field if file name was not blank
		if path[0] != '':
			with open(path[0], 'w', newline='') as outfile:

				#make a csv writer
				writer = csv.writer(outfile, delimiter=',')

				#make list of headers and of data to save
				headers = []
				data = []

				#first add timestamps to data and header
				headers.append('date_time')
				data.append(self.plotTimeStamps)

				#now loop through each ploter and get data and name; append
				for p in self.plotters:
					headers.append(self.plotters[p]['name'])
					data.append(self.plotters[p]['data'])

				#write headers to csv
				writer.writerow(headers)

				#finally, loop through each row and save
				for row in zip(*data):
					writer.writerow(row)

	#function to save logged plot data from a path string (for sequences)
	def savePlotFromString(self, path):
		'''
		Saves the plot log data from a path string
		'''

		#save the field if file name was not blank
		if path != '':
			with open(path, 'w', newline='') as outfile:

				#make a csv writer
				writer = csv.writer(outfile, delimiter=',')

				#make list of headers and of data to save
				headers = []
				data = []

				#first add timestamps to data and header
				headers.append('date_time')
				data.append(self.plotTimeStamps)

				#now loop through each ploter and get data and name; append
				for p in self.plotters:
					headers.append(self.plotters[p]['name'])
					data.append(self.plotters[p]['data'])

				#write headers to csv
				writer.writerow(headers)

				#finally, loop through each row and save
				for row in zip(*data):
					writer.writerow(row)

	#function to load existing plot data
	def loadPlot(self):
		'''
		Loads some existing traces
		'''
		pass

	# DATA GETTER FUNCTIONS #
	#-----------------------#

	#function to update plots
	def updatePlots(self):
		'''
		Updates all plots with new data
		'''

		#first, get timestamp
		t = np.append(self.plotTimeStamps, time.time())
		self.plotTimeStamps = t

		#next, get data for each connected plotter device
		# and append to data list
		for p in self.plotters:

			#get attribute values
			res = getattr(
				self,
				self.plotters[p]['attr']
				)

			#update data with new point
			d = np.append(self.plotters[p]['data'], res)
			self.plotters[p]['data'] = d

			#finally, update plots
			self.plotters[p]['instance'].setData(
				y = self.plotters[p]['data'], 
				x = self.plotTimeStamps
				)

	#~~~~~~~~~~~~~~~~~~#
	# METHOD FUNCTIONS #
	#~~~~~~~~~~~~~~~~~~#

	# METHOD BUTTON FUNCTIONS #
	#-------------------------#

	#function to load method
	def loadMethod(self):
		'''
		Loads a method file
		'''

		#bring up query for file name
		path = QFileDialog.getOpenFileName(self, 'Open File', '', 'CSV(*.csv)')

		#open the field if file name was not blank
		if path[0] != '':
			with open(path[0], 'r', newline='') as infile:

				#strip the table back to just the headers
				self.methodTable.setRowCount(1)
				self.methodTable.setColumnCount(4)

				#now loop through and add data
				for i, rowdata in enumerate(csv.reader(infile, delimiter=',')):

					#don't re-load the header row
					if i == 0:
						continue

					else:

						#now insert each row
						row = self.methodTable.rowCount()
						self.methodTable.insertRow(row)
						self.methodTable.setColumnCount(len(rowdata))

						#insert each item in a row columnwise
						for col, data in enumerate(rowdata):
							item = QTableWidgetItem(data)
							self.methodTable.setItem(row, col, item)

	#function to load method from input string
	def loadMethodFromString(self, mfs):
		'''
		Loads a method file from a string
		'''
		
		try:
			#open method file from string
			with open(mfs, 'r', newline='') as infile:

				#strip the table back to just the headers
				self.methodTable.setRowCount(1)
				self.methodTable.setColumnCount(4)

				#now loop through and add data
				for i, rowdata in enumerate(csv.reader(infile, delimiter=',')):

					#don't re-load the header row
					if i == 0:
						continue

					else:

						#now insert each row
						row = self.methodTable.rowCount()
						self.methodTable.insertRow(row)
						self.methodTable.setColumnCount(len(rowdata))

						#insert each item in a row columnwise
						for col, data in enumerate(rowdata):
							item = QTableWidgetItem(data)
							self.methodTable.setItem(row, col, item)

			success = True #return flag

		except FileNotFoundError:
			self.print('Method file not found!')
			self.print(f'Check method is in folder: {self._methodFolder}')

			#strip the table back to just the headers
			self.methodTable.setRowCount(1)
			self.methodTable.setColumnCount(4)

			success = False #return flag

		return success

	#function to clear method
	def clearMethod(self):
		'''
		Clears a method file
		'''

		#need to clear from row 1 on (i.e., leave headers)
		rs = self.methodTable.rowCount()

		#clears back to just the headres
		self.methodTable.setRowCount(1)

		# #now re-adds all the rows
		for i in range(rs-1):
		
			self.methodTable.insertRow(i+1)

	#function to add row below to method
	def addRowBelow(self):
		'''
		Adds row below selection
		'''
	
		try:	
			#get selected rows
			srs = self.methodTable.selectionModel().selectedRows()
			i = srs[-1].row()

			#now add below
			self.methodTable.insertRow(i+1)

		#pass if no rows highlighted
		except IndexError:
			pass

	#function to add row above to method
	def addRowAbove(self):
		'''
		Adds row above selection
		'''

		try:
			#get selected rows
			srs = self.methodTable.selectionModel().selectedRows()
			i = srs[0].row()

			#now add below
			self.methodTable.insertRow(i)

		#pass if no rows highlighted
		except IndexError:
			pass

	#function to delete selected row from method
	def deleteRow(self):
		'''
		Deletes selected row
		'''

		#get selected rows
		srs = self.methodTable.selectionModel().selectedRows()
		
		#now loop through and delete
		for ind in sorted(srs)[::-1]:
			i = ind.row()
			self.methodTable.removeRow(i)

	#function to save method
	def saveMethod(self):
		'''
		Saves the current table to a method file
		'''

		#bring up query for file name
		path = QFileDialog.getSaveFileName(self, 'Save File', '', 'CSV(*.csv)')

		#save the field if file name was not blank
		if path[0] != '':
			with open(path[0], 'w', newline='') as outfile:

				#make a csv writer
				writer = csv.writer(outfile, delimiter=',')

				#save the data
				# outfile.write(self.methodTable.toPlainText())

				#loop through each row and save
				for row in range(self.methodTable.rowCount()):
					
					rowdata = []
					
					for column in range(self.methodTable.columnCount()):
						
						#get the item in each cell
						item = self.methodTable.item(row, column)
						
						#append the data if there is some text
						if item is not None:
							rowdata.append(item.text())

						#otherwise append an empty cell
						else:
							rowdata.append('')
					
					writer.writerow(rowdata)

	#function to edit method (i.e., move to edit panel)
	def editMethod(self):
		'''
		Switches to the method edit panel
		'''
		self.mainTabs.setCurrentIndex(2)

	#~~~~~~~~~~~~~~~#
	# RUN FUNCTIONS #
	#~~~~~~~~~~~~~~~#

	#function to bring up window where user can input CC safety check values
	def setCCChecksWindow(self):
		'''
		allows user-defined CC safety checks
		'''

		#get list of relevant current values
		cvals = [
			self._minH2OFlow, 
			self._maxH2OTemp, 
			self._ccTempTol, 
			self._maxCryoCoolerTemp
			]

		#shorthand labels for error catching
		slabs = [
			'min. H2O flow',
			'max. H2O temp',
			'temp. tolerance',
			'max. baseplate temp.']
		
		#make the dialog box
		db = InputDialog(
			labels = [
				'Minimum H2O flow for cryo cooler safety shutoff (ccm):',
				'Maximum H2O temp. for cryo cooler safety shutoff (C):',
				'Temp. tolerance for cryo cooler ready state (C):',
				'Maximum cryo cooler baseplate temp for safety shutoff (C):'],
			currentvals = cvals)
		
		#if executed, update values
		newvals = []

		if db.exec_():

			#make sure values are floats and, if so, store in newvals list
			for i, val in enumerate(db.getInputs()):
				try:
					newvals.append(int(val))
				
				except ValueError:
					self.print(f'{slabs[i]} input must be a number. Retaining old value!')
					newvals.append(cvals[i])

			#now store to self
			self._minH2OFlow, self._maxH2OTemp, self._ccTempTol, \
			self._maxCryoCoolerTemp = newvals
		
	#function to initialize (cool-down) cryocooler
	def initializeCC(self):
		'''
		Initializes the cryo cooler sequence
		'''

		#performs safety check and prints error if any
		if not self.connected:
			self.print("Not Connected. Can't initialize cryo cooler.")

		else:
			if self.ccSafetyCheck(p = True):

				#initialize cryocooler
				self.read_write('cryoCooler startUp')

				#update run status
				self._flagCryoCoolerRunning = True			

	#function to shut down the cryo cooler
	def shutDownCC(self):
		'''
		Shuts down the cryo cooler
		'''

		#shut down cryocooler
		self.read_write('cryoCooler shutDown')

		#update run status
		self._flagCryoCoolerRunning = False

	#function to start a run
	def startRun(self):
		'''
		Starts a run
		'''
		
		# FIRST DO CHECKS #
		#-----------------#

		torun = True

		#check connected
		if not self.connected:

			#print and pass
			self.print("Not Connected. Can't start run.")
			torun = False

		#check method is loaded and makes sense
		elif not self.methodCheck():

			#print and pass
			self.print('Invalid method. Check method values before running.')
			torun = False

		#check cryocooler is ready (only for non-sequence runs)
		elif not self.waiting and not self._flagCryoCoolerReady:

			#ask user if they want to continue with run anyway
			# qm = QtGui.QMessageBox(self)
			qm = QMessageBox(self)
			
			ret = qm.question(
				self, 
				'', 
				'CryoCooler not yet at set temperature. Proceed anyway?',
				qm.Yes | qm.No
				)

			if ret == qm.Yes:
				self.print('Cryo cooler not ready; run started anyway')
				torun = True

			else:
				self.print('Cryo cooler not ready; run not started.')
				torun = False

		# START RUN #
		#-----------#

		#only if all checks pass, then start run:
		if torun:

			#start the plotter if it's not already going
			if not self.plotting:
				self.startPlot()

			if not self.waiting:

				#disable all dialog edit abilities while running:
				self.active(active = False)

				#clear dialog and plots
				self.clearDialog()
				self.clearPlot()

				#print the status
				self.print('RUNNING METHOD')
				self.print('------------------------------------------')

			else:

				#only clear plots if saving plots for each sample
				if self._saveTraces:
					self.clearPlot()

				#print the status
				self.print('RUNNING METHOD FROM ISODAT')
				self.print('------------------------------------------')

			self.statusBar().showMessage(
				'Current Status: Connected and Running'
				)

			#update status
			self.running = True

			#call the run method function to actually run the method
			self.runMethod()

	#function to stop a run when user clicks
	def stopRunByUser(self):
		'''
		Stops a run when user clicks to stop
		'''

		#make sure it's running first
		if self.running:

			#ask user to be sure
			# qm = QtGui.QMessageBox(self)
			qm = QMessageBox(self)
			
			ret = qm.question(
				self, 
				'', 
				'Are you sure you want to stop the run?',
				qm.Yes | qm.No
				)

			#stop run if yes
			if ret == qm.Yes:

				self.print('Run stopped by user')

				#clear any remaining queued tasks
				self.methodThreadpool.clear()

				#update running and waiting status
				self.running = False

				#do slightly different whether waiting for trigger or not
				if self.waiting:

					self.print('Returning to wait-for-trigger state!')
					self.print('IsoDat will not trigger. Stop/restart sequence!')

					#print the status
					self.statusBar().showMessage(
						'Current Status: Connected, waiting for Trigger'
						)

					#print failure to trigger file
					if self._triggerFile is not None:
						writeFileSection(self._triggerFile,'status','FAILURE')

					else:
						self.print('No trigger file chosen. Please select!')

				else:
					#reenable all dialog edit abilities after run:
					self.active(active = True)

					#print the status
					self.statusBar().showMessage(
						'Current Status: Connected, not Running'
						)

				#reset current sample and method to none
				self._currentSample = None
				self._currentMethod = None

		else:
			self.print('Not currently running')

	#function to stop a run when method finishes
	def stopRunNaturally(self):
		'''
		Stops a run when method finishes
		'''

		#make sure it's running first
		if self.running:

			#if run as part of sequence, need to go back to waiting state
			if self.waiting:

				#print some info
				self.print('RUN FROM ISODAT FINISHED NORMALLY')
				self.print('------------------------------------------')
				self.print('Returning to wait-for-trigger state!')

				#update running status
				self.running = False

				#print the status
				self.statusBar().showMessage(
					'Current Status: Connected, waiting for Trigger'
					)

				if self._triggerFile is not None:
					#print success to trigger file
					writeFileSection(self._triggerFile, 'status', 'SUCCESS')
				
				else:
					self.print('No trigger file chosen. Please select!')

			#if not run as part of sequence, finish as normal
			else:

				#print some info
				self.print('RUN FINISHED NORMALLY')
				self.print('------------------------------------------')

				#reenable all dialog edit abilities after run:
				self.active(active = True)

				#update running status
				self.running = False

				#print the status
				self.statusBar().showMessage(
					'Current Status: Connected, not Running'
					)

			#if saving traces, then do so now
			if self._saveTraces:

				#make full path, including sample name
				path = os.path.join(
					self._saveTracesPath,
					self._currentSample + '.csv')

				#save
				self.savePlotFromString(path)

			#reset current sample and method to none
			self._currentSample = None
			self._currentMethod = None

		else:
			self.print('Not currently running')

	#~~~~~~~~~~~~~~~~~~~~~~~~~~#
	# RUN BY TRIGGER FUNCTIONS #
	#~~~~~~~~~~~~~~~~~~~~~~~~~~#

	# TRIGGER MENU FUNCTIONS #
	#------------------------#

	#function to point to file for IsoDat trigger comms
	def setTriggerFile(self):
		'''
		lets the user set the trigger file (i.e., communication with Isodat)
		'''

		#first raise warning, saying only to change if you know what you're doing
		qm = QMessageBox(self)
		sns = qm.question(
			self, 
			'', 
			'Are you SURE you want to change trigger file? This may break IsoDat comms!!',
			qm.Yes | qm.No
			)

		if sns == qm.Yes:

			#then raise dialog allowing user to change
			path = QFileDialog.getOpenFileName(self, 'Open File', '', 'TXT(*.txt)')

			#open the field if file name was not blank
			if path[0] != '':
				self._triggerFile = path[0]
				self.print(f'Trigger file changed to "{self._triggerFile}"')

			else:
				self.print(f'No file chosen: retaining old trigger file' \
				 f' "{self._triggerFile}"')

		else:
			self.print(f'File not changed: retaining old trigger file' \
			f' "{self._triggerFile}"')

	#function to point to the directory containing all methods
	def setMethodFolder(self):
		'''
		points to directory containing methods called by Isodat
		'''

		#raise dialog to choose folder
		qm = QMessageBox(self)
		path = QFileDialog.getExistingDirectory(self,
			'Choose directory containing method files:',
			'',
			QFileDialog.ShowDirsOnly)

		#open the field if file name was not blank
		if path != '':
			self._methodFolder = path
			self.print(f'Method folder changed to "{self._methodFolder}"')

		else:
			self.print(f'No folder chosen: retaining old method folder' \
			 f' "{self._methodFolder}"')

	# TRIGGER RUN FUNCTIONS #
	#-----------------------#

	#function to wait for trigger from Isodat
	def startSequence(self):
		'''
		Continuously searches for IsoDat run signal to start run
		'''

		totrigger = True

		#check connected
		if not self.connected:

			#print and pass
			self.print("Not Connected. Can't start sequence.")
			totrigger = False

		elif self.waiting:

			#print and pass
			self.print("Already running sequence.")
			totrigger = False

		elif self._triggerFile is None:

			#print and pass
			self.print('No trigger file chosen. Please select!')
			totrigger = False

		else:
			#if connected, ask user if they want to save traces/dialogs
			qm = QMessageBox(self)
			sns = qm.question(
				self, 
				'', 
				'Would you like to save traces/dialogs for samples in this sequence?',
				qm.Yes | qm.No
				)

			if sns == qm.Yes:

				#now ask for path
				qm = QMessageBox(self)
				path = QFileDialog.getExistingDirectory(self,
					'Choose directory to save traces/dialogs:',
					'',
					QFileDialog.ShowDirsOnly)

				if path == '':
					#store state: don't trigger
					self._saveTraces = False
					self._saveTracesPath = None
					self.print("No directory chosen, sequence not started.")
					totrigger = False

				else:
					#store state: trigger, save traces to input directory
					self._saveTraces = True
					self._saveTracesPath = path
					totrigger = True					

			else:
				#store state: trigger, but don't save traces
				self._saveTraces = False
				self._saveTracesPath = None
				totrigger = True

		#if checks pass, start method
		if totrigger:

			#first reset trigger file to catch lingering fail from prev. sequence
			# default back to SUCCESS so Isodat will start first sample
			writeFileSection(self._triggerFile, 'status', 'SUCCESS')

			#clear dialog and plots
			self.clearDialog()
			self.clearPlot()

			#deactivate screen
			self.active(active = False)
			self.print('RUNNING ISODAT SEQUENCE')
			self.print('------------------------------------------')

			#print the status
			self.statusBar().showMessage(
				'Current Status: Connected, waiting for Trigger'
				)

			#update status
			self.waiting = True

			#start trigger wait timer
			self.triggerTimer.start()

	#function to stop waiting for trigger from Isodat
	def stopSequence(self):
		'''
		Stops waiting for IsoDat trigger sequence
		'''

		#make sure it's waiting for trigger first
		if self.waiting:

			#ask user to be sure
			qm = QMessageBox(self)
			
			ret = qm.question(
				self, 
				'', 
				'Are you sure you want to stop waiting for IsoDat trigger?',
				qm.Yes | qm.No
				)

			#stop run if yes
			if ret == qm.Yes:
				self.print('Wait-for-trigger stopped by user')

				#update running status
				self.waiting = False

				#stop trigger timer
				self.triggerTimer.stop()

				#if not still running a sample, reactivate
				if not self.running:

					#reenable all dialog edit abilities after run:
					self.active(active = True)

					#print the status
					self.statusBar().showMessage(
						'Current Status: Connected, not Running'
						)

		else:
			self.print('Not currently waiting for trigger')

	#function to continuously read trigger file
	def readTriggerFile(self):
		'''
		Function to read the trigger file and start run when needed
		'''

		#if not currently running method, look for trigger
		if not self.running and self._triggerFile is not None:

			try:

				#see if status is "RUN"
				if readFileSection(self._triggerFile, 'status') == 'RUN':

					#if so, get sample and method info
					sam = readFileSection(self._triggerFile, 'sample')
					met = readFileSection(self._triggerFile, 'method')

					#print status
					self.print(f'Recieved IsoDat trigger! Attempting to run:')
					self.print(f'sample: "{sam}", method: "{met}"')
					self.print(f'------------------------------------------')

					#try to load method
					mfs = os.path.join(self._methodFolder, met + '.csv')
					success = self.loadMethodFromString(mfs)

					#if successful, store, update file, and start run
					if success:
						#store the current sample and method names
						self._currentSample = sam
						self._currentMethod = met

						#start the run
						self.startRun()

						#update trigger file
						writeFileSection(self._triggerFile, 'status', 'WAIT')

					else:
						#do not start run
						self.print('Error loading method: skipping run')
						self.print('Returning to wait-for-trigger state!')
						self.print('IsoDat will not trigger. Stop/restart sequence!')

						#update trigger file
						writeFileSection(self._triggerFile, 'status', 'FAILURE')
			
			except:
				pass

	#==================#
	# HELPER FUNCTIONS #
	#==================#

	#function to send everything to home state
	def goHome(self):
		'''
		Moves to home state
		'''

		self.print('Setting everything to home position\n')

		# SWITCHING AND SELECTOR VALVES

		#set spin boxes
		self.SelectorValveSpinBox.setValue(1)
		self.COSwitchingValveSpinBox.setValue(1)
		self.H2SwitchingValveSpinBox.setValue(1)
		self.HFSwitchingValveSpinBox.setValue(1)

		#call set functions
		self.setSelectorValveHome()
		self.setCOSwitchingValve()
		self.setH2SwitchingValve()
		self.setHFSwitchingValve()

		# ON/OFF VALVES

		#close valves
		self.read_write('valveH2In close')
		self.read_write('valveHeIn close')
		self.read_write('valveCOIn close')
		self.read_write('valveH2OIn close')

	#function to activate or deactivate all push buttons
	def active(self, active = True):
		'''
		Tells the QWindow to activate or deactivate all push buttons

		Parameters
		----------
		qw : QMainWindow
			The main GUI window

		active : bool
			Either True for active or False for inactive
		'''

		self.connectButton.setEnabled(active)
		self.disconnectButton.setEnabled(active)
		self.sendButton.setEnabled(active)
		self.commandInput.setEnabled(active)
		self.saveButton.setEnabled(active)
		self.clearButton.setEnabled(active)

		#disable all configuration edit abilities while running:

		#temp buttons
		self.SetT1TempButton.setEnabled(active)
		self.SetT2TempButton.setEnabled(active)
		self.SetTHFTempButton.setEnabled(active)
		self.SetCryoCoolerTempButton.setEnabled(active)
		self.SetBoschOvenTempButton.setEnabled(active)
		self.SetCoF3OvenTempButton.setEnabled(active)

		#temp spin boxes
		self.T1TempSpinBox.setEnabled(active)
		self.T2TempSpinBox.setEnabled(active)
		self.THFTempSpinBox.setEnabled(active)
		self.CryoCoolerTempSpinBox.setEnabled(active)
		self.BoschOvenTempSpinBox.setEnabled(active)
		self.CoF3OvenTempSpinBox.setEnabled(active)

		#flow rate buttons
		self.SetCOFlowButton.setEnabled(active)
		self.SetH2FlowButton.setEnabled(active)
		self.SetHeFlowButton.setEnabled(active)

		#flow rate spin boxes
		self.COFlowSpinBox.setEnabled(active)
		self.H2FlowSpinBox.setEnabled(active)
		self.HeFlowSpinBox.setEnabled(active)

		#check boxes
		self.h2ovalveCheckbox.setEnabled(active)
		self.covalveCheckbox.setEnabled(active)
		self.h2valveCheckbox.setEnabled(active)
		self.hevalveCheckbox.setEnabled(active)

		#valve buttons
		self.SetSelectorValveButton.setEnabled(active)
		self.SetCOSwitchingValveButton.setEnabled(active)
		self.SetH2SwitchingValveButton.setEnabled(active)
		self.SetHFSwitchingValveButton.setEnabled(active)

		#valve spin boxes
		self.SelectorValveSpinBox.setEnabled(active)
		self.COSwitchingValveSpinBox.setEnabled(active)
		self.H2SwitchingValveSpinBox.setEnabled(active)
		self.HFSwitchingValveSpinBox.setEnabled(active)

		self.selectorCWCheckbox.setEnabled(active)

		#disable plotting edit abilities while running:

		#plot buttons
		self.startPlotButton.setEnabled(active)
		self.stopPlotButton.setEnabled(active)
		self.clearPlotButton.setEnabled(active)
		self.savePlotButton.setEnabled(active)

		#disable method edit abilities while running:

		#method buttons
		self.LoadMethodButton.setEnabled(active)
		self.ClearMethodButton.setEnabled(active)
		self.AddRowAboveButton.setEnabled(active)
		self.AddRowBelowButton.setEnabled(active)
		self.DeleteRowButton.setEnabled(active)
		self.SaveMethodButton.setEnabled(active)

	#function to put the config back to "N/A" when disconnected
	def blankConfig(self):
		'''
		Puts config panel back to N/A (call on disconnect)
		'''

		#temperatures
		self.labelT1Temp.setText('N/A C')
		self.labelT2Temp.setText('N/A C')
		self.labelTHFTemp.setText('N/A C')

		self.labelCryoCoolerTemp.setText('N/A C')
		self.labelBoschOvenTemp.setText('N/A C')
		self.labelCoF3OvenTemp.setText('N/A C')
		self.labelH2OTemp.setText('N/A C')

		#flow rates
		self.labelH2OFlow.setText('N/A ccm')
		self.labelCOFlow.setText('N/A ccm')
		self.labelH2Flow.setText('N/A ccm')
		self.labelHeFlow.setText('N/A ccm')

		self.labelCryoCoolerVacuum.setText('N/A mbar')

		#selector valves
		self.labelSelectorValve.setText('N/A')
		self.labelHFSwitchingValve.setText('N/A')
		self.labelCOSwitchingValve.setText('N/A')
		self.labelH2SwitchingValve.setText('N/A')

		#set current flags back to none
		#FLOW RATES
		self._currentCOFlow = None
		self._currentH2Flow = None
		self._currentHeFlow = None
		self._currentH2OFlow = None

		# TEMPERATURES
		self._currentT1Temp = None
		self._currentT2Temp = None
		self._currentTHFTemp = None
		self._currentBoschOvenTemp = None
		self._currentCoF3OvenTemp = None
		self._currentCryoCoolerTemp = None
		self._cryoCoolerSetTemp = None
		self._currentH2OTemp = None

		self._currentCryoCoolerVacuum = None
		self._currentCryoCoolerPower = None

	#function to perform cryo cooler safety check
	def ccSafetyCheck(self, p = False):
		'''
		Checks if the cryo cooler water jacket is functioning and that the
		baseplate is not above 30 C

		Parameters
		----------
		p : bool
			If true, prints the error to dialog. Defaults to ``False''.

		Returns
		-------
		chk : bool
			True if all checks are passed, false otherwise
		'''

		chk = True

		#valve
		if not self._flagValveH2OIn:
			
			chk = False

			if p:
				self.print(
					'water jacket valve not open!'
					)

		#flow rate
		elif self._currentH2OFlow < self._minH2OFlow:
			
			chk = False

			if p:
				self.print(
					'water jacket flow too low!'
					)
		
		#flow jacket temp
		elif self._currentH2OTemp > self._maxH2OTemp:
			
			chk = False

			if p:
				self.print(
					'water jacket temp too high!'
					)

		#baseplate temperature
		elif self._currentCryoCoolerTemp > self._maxCryoCoolerTemp:

			chk = False

			if p:
				self.print(
					'cryocooler baseplate is too warm!'
					)

		return chk

	#function to check cryo cooler status
	def ccStatus(self):
		'''
		Checks if the cryo cooler is at temp or not

		Returns
		-------
		ready : bool
			True if crycooler is at set temp (within bounds), false otherwise
		'''

		#default to false
		ready = False

		#get current temp
		cT = self._currentCryoCoolerTemp

		#get set temp
		sT = self._cryoCoolerSetTemp

		#check if cT within +/- bounds of set temp
		if (sT - self._ccTempTol) < cT < (sT + self._ccTempTol):
			ready = True

		return ready

	#function to check method makes sense
	def methodCheck(self):
		'''
		Checks that the inputted values in the method are reasonable

		Returns
		-------
		check : bool
			True if method makes sense, false otherwise
		'''

		check = True

		#loop through the table:
		nRow = self.methodTable.rowCount()

		for i in range(nRow):

			#skip header row
			if i == 0:
				continue

			#get data for this row
			try:
				t, dev, cmd = [self.methodTable.item(i,j).text() for j in range(3)]

			except AttributeError:
				# pass
				continue

			# TIME CHECK #
			#------------#

			#make sure first column is all floats or blank
			try:
				float(t)

			#skip if blank, raise error if non-floatable string
			except ValueError:
				
				#skip if blank (gets caught later, lets user leave empty rows)
				if t == '':
					pass
				
				else:
					#raise error, make check false, and end the loop
					self.print(
						f'Row {i+1}: time value must be a number, {t} was given'
						)
					
					check = False
					break

			# DEVICE CHECK #
			#--------------#

			#make sure device is in devicelist
			if dev not in self.devList.keys():

				self.print(
					f'Row {i+1}: unknown device {dev}; check device list'
					)

				check = False
				break

			# ATTR CHECK #
			#------------#

			#get method and value from command
			met = cmd.split()[0]

			if met not in self.devList[dev]:

				self.print(
					f'Row {i+1}: invalid method {met}; check {dev} help file'
					)

				check = False
				break

		# #for certain attributes, make sure they're in possible range
		# if selectorValve:
		# 	#make sure 1 <= pos <= 6

		# elif mfc:
		# 	#make sure 0 <= flow rate <= 150 ccm

		return check

	#function to actually run the method
	def runMethod(self):
		'''
		Runs the method that is currently loaded in the method editor.
		'''

		#first get TOTAL number of rows in table (including blanks)
		nRow = self.methodTable.rowCount()

		#make arrays to populate
		ts = [0] #start at 0
		cmds = ['pass'] #start with a pass command (for ordering purposes)

		#then loop through, extract t and command, and drop empty rows
		for i in range(nRow):

			#skip header row
			if i == 0:
				continue

			#get data for this row and append to command list
			try:

				#get values
				t, dev, cmd = [self.methodTable.item(i,j).text() for j in range(3)]

				#append time and command
				ts.append(float(t))
				cmds.append(str(dev) + ' ' + str(cmd))

			#skip if throws an error (i.e., if blank)
			except Exception:
				continue

		#get number of actual commands (can be less than nRow)
		nCmd = len(cmds)

		#make delta time array
		dt = [ts[i+1] - ts[i] for i in range(nCmd-1)]
		dt.append(1./60) #append a 1 second delay after final command

		#now loop through each command and execute
		for i in range(nCmd):

			#make a tuple of command and d time
			item = (cmds[i], dt[i])

			#make the worker
			w = Worker(self.executeMethodRow, item)

			#if it's the last row, then connect to stoprun method
			if i == (nCmd-1):

				#get parse method
				parse = getattr(self, 'stopRunNaturally')

				#connect
				w.signals.result.connect(parse)

			#now start the worker
			self.methodThreadpool.start(w)

	#function to execute command in a given method row
	def executeMethodRow(self, item):
		'''
		Executes the method specified in a given row by calling read_write

		Parameters
		----------
		item : tuple
			Tuple containing the command string and the time to wait after
			executing (in minutes)
		'''

		#extract info for parsing
		cmd = item[0]
		dt = item[1] * 60 #convert to seconds

		if cmd == 'pass':
			sleep(dt)

		else:
			self.read_write(cmd)
			sleep(dt)

	#function to read device list and return as dict
	def getDevList(self):
		'''
		Reads the device list string outputted by the Raspberry Pi and
		stores as an attribute. To be used for checking method. Makes a dict of 
		devices, with device names as keys and device methods as data.

		NOTE: Called without threading since this appears to crash the thread.
		This way, it just holds up the gui for ~2 seconds while connecting.
		'''

		#get device name strings as list
		devStr = self.executeReadWriteMultiline('deviceList')
		devNames = re.findall('\t(\w*)', devStr)

		#make empty dictionary
		devList = {}

		#loop through and store names as keys
		for n in devNames:

			#now read_write_multiline to get methods
			metStr = self.executeReadWriteMultiline(n)
			metNames = re.findall('\t(\w*)', metStr)

			devList[n] = metNames

		return devList

	#function to read i/o values on startup
	def readIOStartup(self):
		'''
		Reads the contents of the io_values file on program startup and stores
		This ensures, e.g., method directory does not need to be reset each time
		the software is re-opened.
		'''

		#get the file path
		io_file = os.path.join(current_path, 'io_values.txt')

		#open it and store each line to list
		with open(io_file, 'r', newline='') as f:
			lines = [line.rstrip() for line in f]

		#make into dict
		io_data = {l.split('=')[0]: l.split('=')[1] for l in lines}

		#now save to self
		for key in io_data:

			#need to evaluate None as nonetype and limits as ints
			try:
				setattr(self, key, eval(io_data[key]))

			#catch strings
			except SyntaxError:
				setattr(self, key, io_data[key])

	#function to write i/o values on shutdown
	def writeIOShutdown(self):
		'''
		Writes the current contents of the io_values to file on program shutdown
		to ensure, e.g, method directory does not need to be reset each time the
		software is re-opened.
		'''

		#get the file path
		io_file = os.path.join(current_path, 'io_values.txt')

		#open and read file keys
		with open(io_file, 'r', newline='') as f:
			lines = [line.rstrip() for line in f]

		#get dict keys
		keys = [l.split('=')[0] for l in lines]

		#make dictionary and get current values for each key
		io_data = {key: getattr(self, key) for key in keys}

		#now concatenate into list of strings
		lines = ['='.join([key, str(val)]) for key, val in io_data.items()]

		#finally, write each string to a line in the io_file
		with open(io_file, 'w', newline='') as f:
			f.write("\n".join(l for l in lines))

#===================#
# THREADING CLASSES #
#===================#

#class for making workers to thread
class Worker(QRunnable):
	'''
	Worker class for threading; inherited from QRunnable.
	'''

	def __init__(self, fn, *args, **kwargs):
		'''
		Initializes the class

		Parameters
		----------
		callback : function
			The function callback that is run by this worker thread. Supplied args
			and kwargs are passed to the runner function.

		args : list
			List of args to pass to runner function

		kwargs : dict
			Dict of kwargs to pass to runner function
		'''

		#init superclass
		super(Worker, self).__init__()

		#store constructor arguments
		self.fn = fn
		self.args = args
		self.kwargs = kwargs

		#store WorkerSignals object for passing back-and-forth to GUI
		self.signals = WorkerSignals()

		#add the function callback to kwargs
		# self.kwargs['updated_vals'] = self.signals.vals

	#make the runner function
	@pyqtSlot()
	def run(self):
		'''
		Initialise the runner function with passed args and kwargs.
		'''
		
		#try to run the function
		try:
			res = self.fn(*self.args, **self.kwargs)
		
		#catch any errors that may arise
		except:
			traceback.print_exc()
			exctype, value = sys.exc_info()[:2]
			
			#return any errors to the worker signals
			self.signals.error.emit((exctype, value, traceback.format_exc()))
		
		#return the result of the processing
		else:
			self.signals.result.emit(res)
		
		#emit no data when finished
		finally:
			self.signals.finished.emit()


#class for sending signals back-and-forth to main window
class WorkerSignals(QObject):
	'''
	Defines the signals available from a running worker thread. Supported 
	signals are:

	finished:
		No data (not used here)

	error:
		tuple (exctype, value, traceback.format_exc())

	result:
		object data returned from processing; can be anything

	vals:
		list of updated values to print to config table
	'''

	finished = pyqtSignal()
	error = pyqtSignal(tuple)
	result = pyqtSignal(object)


#class for bringing up a dialog box to take user-defined inputs
class InputDialog(QDialog):
	'''
	Input dialog class for taking multiple inputs at once. Inherited from
	Qdialog
	'''
	def __init__(self, labels:List[str], currentvals:List[float], parent = None):
		super().__init__(parent)

		#make the widget window
		bbox = QDialogButtonBox(
			QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
			self)
		layout = QFormLayout(self)
        
        #loop through inputs, set current vals as default text, and add to widget
		self.inputs = []
		for i, lab in enumerate(labels):
			
			#add to inputs
			self.inputs.append(QLineEdit(self))

			#set current (default) value
			self.inputs[-1].setText(str(currentvals[i]))
			
			#add to layout
			layout.addRow(lab, self.inputs[-1])

		layout.addWidget(bbox)

		bbox.accepted.connect(self.accept)
		bbox.rejected.connect(self.reject)

	def getInputs(self):
		return tuple(input.text() for input in self.inputs)

#======================#
# READ/WRITE FUNCTIONS #
#======================#

#function for reading a given "section" from a text file (Isodat nomenclature)
def readFileSection(file, section):
	'''
	Reads the "section" of the file and returns as string

	Parameters
	----------
	file : str
		String pointing to the file to read

	section : str
		The section to read, where file is structured as follows:

		[header]
		section1=value1
		section2=value2
		...etc.

	Returns
	-------
	value : None or str
		The value of the section, as a string. Returns None if section cannot
		be found in file
	'''

	#open the file
	with open(file, 'r', newline='') as f:

		#get all lines as a list
		lines = [line.rstrip() for line in f]

	#convert into a dict (ignoring first header line)
	data = {l.split('=')[0]: l.split('=')[1] for l in lines[1:]}

	#now get value, or none if section does not exist
	try:
		value = data[section]

	except KeyError:
		value = None

	return value

#function for writing a given "section" to a text file (Isodat nomenclature)
def writeFileSection(file, section, value):
	'''
	Writes the "section" of the file

	Parameters
	----------
	file : str
		String pointing to the file to read

	section : str
		The section to write to, where file is structured as follows:

		[header]
		section1=value1
		section2=value2
		...etc.

	value : str
		The value to store to section
	'''

	#open and read file keys
	with open(file, 'r', newline='') as f:
		lines = [line.rstrip() for line in f]

	#convert into a dict (ignoring first header line)
	data = {l.split('=')[0]: l.split('=')[1] for l in lines[1:]}

	#now store new value to section (can be new section)
	data[section] = value

	#now save as new lines
	newlines = ['='.join([key, str(val)]) for key, val in data.items()]

	#insert the header back inthe front
	newlines.insert(0,lines[0])

	#finally, write each string to a line in the io_file
	with open(file, 'w', newline='') as f:
		f.write("\n".join(l for l in newlines))
