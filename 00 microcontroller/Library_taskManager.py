# Library_taskManager.py
# 09. January 2025
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

'''
File to define a bunch of tasks that can be done
'''

from time import time
from Library_ComSet import deviceList

class taskManager:
	'''
	Class to manage tasks
	'''
	def __init__(self, devices):
		'''
		Initialize the class instance

		Attributes
		----------
		__lastExecuted : float
			Time the task manager was last executed

		__taskList : list
			List of tasks to be done

		__devices : list
			List of connected devices

		index : int
			Index of current task(?)

		stateList : dict
			List of current device states
		'''

		#set attributes
		self.__lastExecuted = time()
		self.__devices = devices
		self.__taskList = []

		self.index = 0
		self.stateList = dict(  )  # default fillbusy

	#function to get the task list from the class instance
	def getTaskList(self):
		'''
		Gets task list from taskManager instance
		'''
		try:
			taskList = self.__taskList[0]

		except IndexError:
			taskList = []

		return taskList

	#index setter
	def setIndex(self, index):
		'''
		Sets the index

		Parameters
		----------
		index : int
			The new index
		'''
		self.index = index

	#index getter
	def getIndex(self):
		'''
		Gets the current index
		'''
		return self.index

	#function to add task
	def addTask(self, newTask):
		'''
		Adds a new task to the task list

		Parameters
		----------
		newTask : str(?)
			The new task to perform
		'''
		if len(newTask) > 0:
			self.__taskList.append(newTask[0])

	#function to actually do the tasks
	def doTasks(self):
		'''
		Execute the tasks in the task list
		'''

		#loop through each task and execute
		for task in self.__taskList:
			
			if "kwargs" in task:
				getattr(
					self.__devices[task["Device"]]["Instance"], 
					task["Method"]
					)(task["kwargs"])
			else:
				getattr(
					self.__devices[task["Device"]]["Instance"],
					task["Method"]
					)()
			
			self.__taskList = []


	#function to see when manager was last executed
	def getLastExecution(self):
		'''
		Get last task execution time
		'''
		return self.__lastExecuted


#make an instance of the class
myTM = taskManager(deviceList)