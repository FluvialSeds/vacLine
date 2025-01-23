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
		self.devList = None #make none until connected

		#===============#
		# CONFIGURATION #
		#===============#

		# DT INTERFACE GROUP BOX #
		#------------------------#
		#DT toggle
		self.toggleTrapButton.clicked.connect(self.toggleTrap)
		
		#DT temps
		self.dtLeftCheckBox.stateChanged.connect(self.heatDTLeft)
		self.dtRightCheckBox.stateChanged.connect(self.heatDTRight)

		#Flow and water trap
		self.HeFlowCheckBox.stateChanged.connect(self.heOpenClose)
		self.wt2HeatCheckBox.stateChanged.connect(self.heatWT2)
		self.setHeFlowButton.clicked.connect(self.setHeFlow)

		# VACUUM LINE GROUP BOX #
		#-----------------------#
		#CF and water trap temps
		self.wt1HeatCheckBox.stateChanged.connect(self.heatWT1)
		self.cfHeatCheckBox.stateChanged.connect(self.heatCF)

		# CONFIGURATION INITIAL STATES #	
		#------------------------------#
		#DT state
		self._flagDTSwitchingPos = 1 #start is pos 1 (trapping T1)

		#on/off valves
		self._flagValveHeIn = False #start with flow off

		#heating states
		self._flagHeatingDTL = False #state with no heating
		self._flagHeatingDTR = False #state with no heating
		self._flagHeatingCF = False #state with no heating
		self._flagHeatingWT1 = False #state with no heating
		self._flagHeatingWT2 = False #state with no heating

		#set the display flags to none
		#TEMPS
		self._currentDTLTemp = None
		self._currentDTRTemp = None
		self._currentCFTemp = None
		self._currentWT1Temp = None
		self._currentWT2Temp = None

		#FLOW RATES
		self._currentHeFlow = None

		# PASSIVE SENSORS
		self._currentTCDSignal = None
		self._currentVacGaugeSignal = None

		#set the main tab default to "command line"
		self.mainTabs.setCurrentIndex(0)

		# CONFIGURATION LOG TIMERS #
		#--------------------------#

		#set interval
		self.j = 1000 #1 second

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
		# self.l.setSpacing(0.)
		# self.l.setContentsMargins(0., 0., 0., 0.)

		self.l.setSpacing(0)
		self.l.setContentsMargins(0, 0, 0, 0)


		#add empty plots to fill later
		self.plotters = {
			'DTLT': {'name': 'DT_Left T (C)',					#temperatures
					'c': (39, 112, 0),
					'attr': '_currentDTLTemp'
					},
			'DTRT': {'name': 'DT_Right T (C)',
					'c': (58, 163, 0),
					'attr': '_currentDTRTemp'
					},
			'CFT': {'name': 'Cold Finger T (C)',
					'c': (84, 240, 0),
					'attr': '_currentCFTemp'
					},
			'WT1T': {'name': 'Water Trap 1 T (C)',
					'c': (131, 240, 72),
					'attr': '_currentWT1Temp'
					},
			'WT2T': {'name': 'Water Trap 2 T (C)',
					'c': (88, 0, 112),
					'attr': '_currentWT2Temp'
					},
			'HeFl': {'name': 'He flow rate (ccm)',				#flow rates
					'c': (11, 88, 212),
					'attr': '_currentHeFlow'
					},
			'dtValve': {'name': 'DT trapping trap',				#valve positions
					'c': (0, 0, 0),
					'attr': '_flagDTSwitchingPos'
					},
			'TCD': {'name': 'TCD signal (mV)',					#passive signals
					'c': (227, 40, 11),
					'attr': '_currentTCDSignal'
					},
			'CFV': {'name': 'cold finger vacuum (mbar)',
					'c': (247, 203, 112),
					'attr': '_currentVacGaugeSignal'
					},
		}

		#add empty plots to fill later
		for p in self.plotters:

			#make plot
			self.plotters[p]['instance'] = self.plt.plot(
				name = self.plotters[p]['name'],
				)

			#set color
			# self.plotters[p]['instance'].setPen(
			# 	color = self.plotters[p]['c'],
			# 	width = 5,
			# 	)

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

		#==========#
		# MENU BAR #
		#==========#

		# ACTIONS #
		#---------#

		#file menu:
		#opens
		self.actionOpenDialog.triggered.connect(self.loadDialog)
		self.actionOpenTraces.triggered.connect(self.loadPlot)

		#saves
		self.actionSaveDialog.triggered.connect(self.saveDialog)
		self.actionSaveTraces.triggered.connect(self.savePlot)

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

				#start reading temps and flow rates to print to config panel
				self.configTimer.start()

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

		# SWITCHING VALVES

		# DT switching valves (NOTE: do all through L valve; R is slave)
		self.read_write(
			'valveSwitchingLeft getPos',
			parse = 'updateLabelDTrapping'
			)

		# FLOW RATES

		#He flow
		self.read_write(
			'mfcHeIn getFlow',
			parse = 'updateLabelHeFlow'
			)

		# TEMPERATURES

		#CF temp
		self.read_write(
			'pidColdFinger getTemp',
			parse = 'updateLabelCFTemp'
			)

		#DT_R temp
		self.read_write(
			'pidDT_R getTemp',
			parse = 'updateLabelDTRTemp'
			)

		#DT_L temp
		self.read_write(
			'pidDT_L getTemp',
			parse = 'updateLabelDTLTemp'
			)

		#WT1 temp
		self.read_write(
			'pidWT1 getTemp',
			parse = 'updateLabelWT1Temp'
			)

		#WT2 temp
		self.read_write(
			'pidWT2 getTemp',
			parse = 'updateLabelWT2Temp'
			)

		# PASSIVE SENSORS

		#cold finger vacuum
		self.read_write(
			'vacuumSensor getVacuum',
			parse = 'updateLabelCFVacuum'
			)

		#TCD signal
		self.read_write(
			'tcdGC getSignal',
			parse = 'updateLabelTCDSignal',
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
			if self.HeFlowCheckBox.isChecked() != io:

				#set flag to current state
				self._flagValveHeIn = io
				sleep(0.005) #wait a bit before going into trigger function

				#and change checkbox
				self.HeFlowCheckBox.setChecked(io)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelDTrapping(self, p):
		'''
		Updates the double trap toggle label (L as control; R as slave)
		'''

		try:

			if int(p) == 0: #trapping left
				self.labelDTTrapping.setText('Left')

			else: #trapping right
				self.labelDTTrapping.setText('Right')

			self._flagDTSwitchingPos = int(p)+1 #change of indexing

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

	def updateLabelCFTemp(self, T):
		'''
		Updates the cold finger temp label
		'''

		try:
			self.labelCFTemp.setText('%.1f C' % float(T))
			self._currentCFTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelDTRTemp(self, T):
		'''
		Updates the DT_R temp label
		'''

		try:
			self.labelDTRTemp.setText('%.1f C' % float(T))
			self._currentDTRTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelDTLTemp(self, T):
		'''
		Updates the DT_L temp label
		'''

		try:
			self.labelDTLTemp.setText('%.1f C' % float(T))
			self._currentDTLTemp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelWT1Temp(self, T):
		'''
		Updates the water trap 1 temp label
		'''

		try:
			self.labelWT1Temp.setText('%.1f C' % float(T))
			self._currentWT1Temp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelWT2Temp(self, T):
		'''
		Updates the water trap 2 temp label
		'''

		try:
			self.labelWT2Temp.setText('%.1f C' % float(T))
			self._currentWT2Temp = float(T)

		#catch error if returns string
		except ValueError:
			pass

	def updateLabelCFVacuum(self, P):
		'''
		Updates the current Pirani gauge value
		'''

		try:
			self.labelVacuum.setText('%.1e mbar' % float(P))
			self._currentVacGaugeSignal = float(P)

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

	# SETTING FUNCTIONS #
	#-------------------#

	#function to toggle traps
	def toggleTrap(self):
		'''
		Toggles double-trap interface
		'''

		#if currently trapping T1, open both valves:
		if self._flagDTSwitchingPos == 1:

			self.read_write('valveSwitchingLeft open')
			self.read_write('valveSwitchingRight open')

			#update flag
			# self._flagDTSwitchingPos = 2

		#if currently trapping T2, close both valves:
		elif self._flagDTSwitchingPos == 2:

			self.read_write('valveSwitchingLeft close')
			self.read_write('valveSwitchingRight close')

			#update flag
			# self._flagDTSwitchingPos = 1

	#function to heat DT left
	def heatDTLeft(self):
		'''
		Heats the left double-trap trap
		'''

		#if current and checkbox disagree, then send command to heat/cool
		if self._flagHeatingDTL != self.dtLeftCheckBox.isChecked():

			#send command to heat/cool
			if self.dtLeftCheckBox.isChecked():

				#read value from spin box
				setTemp = self.dtTempSpinBox.value()

				cmd = 'pidDT_L setTemp ' + str(setTemp)
				self.read_write(cmd)

			else:
				self.read_write('pidDT_L setTemp -200') #arbitrarily cold

			# and toggle flagged state
			self._flagHeatingDTL = self.dtLeftCheckBox.isChecked()

	#function to heat DT right
	def heatDTRight(self):
		'''
		Heats the right double-trap trap
		'''

		#if current and checkbox disagree, then send command to heat/cool
		if self._flagHeatingDTR != self.dtRightCheckBox.isChecked():

			#send command to heat/cool
			if self.dtRightCheckBox.isChecked():

				#read value from spin box
				setTemp = self.dtTempSpinBox.value()

				cmd = 'pidDT_R setTemp ' + str(setTemp)
				self.read_write(cmd)

			else:
				self.read_write('pidDT_R setTemp -200') #arbitrarily cold

			# and toggle flagged state
			self._flagHeatingDTR = self.dtRightCheckBox.isChecked()

	#function to heat WT2
	def heatWT2(self):
		'''
		Heats the Water Trap 2
		'''

		#if current and checkbox disagree, then send command to heat/cool
		if self._flagHeatingWT2 != self.wt2HeatCheckBox.isChecked():

			#send command to heat/cool
			if self.wt2HeatCheckBox.isChecked():

				#read value from spin box
				setTemp = self.wt2TempSpinBox.value()

				cmd = 'pidWT2 setTemp ' + str(setTemp)
				self.read_write(cmd)

			else:
				self.read_write('pidWT2 setTemp -200') #arbitrarily cold

			# and toggle flagged state
			self._flagHeatingWT2 = self.wt2HeatCheckBox.isChecked()

	#function to heat WT1
	def heatWT1(self):
		'''
		Heats the Water Trap 1
		'''

		#if current and checkbox disagree, then send command to heat/cool
		if self._flagHeatingWT1 != self.wt1HeatCheckBox.isChecked():

			#send command to heat/cool
			if self.wt1HeatCheckBox.isChecked():

				#read value from spin box
				setTemp = self.wt1TempSpinBox.value()

				cmd = 'pidWT1 setTemp ' + str(setTemp)
				self.read_write(cmd)

			else:
				self.read_write('pidWT1 setTemp -200') #arbitrarily cold

			# and toggle flagged state
			self._flagHeatingWT1 = self.wt1HeatCheckBox.isChecked()

	#function to heat cold finger
	def heatCF(self):
		'''
		Heats the cold finger
		'''

		#if current and checkbox disagree, then send command to heat/cool
		if self._flagHeatingCF != self.cfHeatCheckBox.isChecked():

			#send command to heat/cool
			if self.cfHeatCheckBox.isChecked():

				#read value from spin box
				setTemp = self.cfTempSpinBox.value()

				cmd = 'pidColdFinger setTemp ' + str(setTemp)
				self.read_write(cmd)

			else:
				self.read_write('pidColdFinger setTemp -200') #arbitrarily cold

			# and toggle flagged state
			self._flagHeatingCF = self.cfHeatCheckBox.isChecked()

	#function to open/close He on/off valve
	def heOpenClose(self):
		'''
		Toggles He valve open/closed
		'''
		
		#if current and checkbox disagree, then send command to toggle
		if self._flagValveHeIn != self.HeFlowCheckBox.isChecked():

			#send command to toggle
			if self.HeFlowCheckBox.isChecked():
				self.read_write('valveHeIn open')
			else:
				self.read_write('valveHeIn close')

			# and toggle flagged state
			self._flagValveHeIn = self.HeFlowCheckBox.isChecked()

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

	#==================#
	# HELPER FUNCTIONS #
	#==================#

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

