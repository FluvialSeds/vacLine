# Library_Communicate.py
# 09. January 2025
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

'''
File to make a communication class, which is how we will read and write messages
to the pi pico controller
'''

from sys import stdin
from select import select
from time import time

#define communcation class
class Communicate:
    '''
    Class to communicate between pi pico and desktop
    '''
    def __init__(self):
        '''
        Initialize the class instance

        Attributes
        ----------
        __lastExectued : float
            time when last executed

        __message : string
            communication message
        '''
        self.__lastExecuted = time()
        self.__message = ""


    def read(self):
        '''
        Function to read a message

        Returns
        -------
        msg : float
            The message to read
        '''

        #make empty list
        msg = []
        
        #get messages from read list
        while stdin in select([stdin], [], [], 0)[0]:
            char = stdin.read(1)
            
            #if new line, pull attribute to msg and reset attribute
            if char == "\n":
                if len(self.__message) > 0:
                    msg.append(self.__message)
                    self.__message = ""
            
            #or else store in attribute
            else:
                self.__message += char
        
        #store execution time
        self.__lastExecuted = time()
        
        return msg


    def getLastExecution(self):
        '''
        Just return the time of last execution
        '''
        return self.__lastExecuted

#make an instance of the class (to be imported in main.py)
myCom = Communicate()
