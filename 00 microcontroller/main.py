# main.py
# 09. January 2025
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

# main.py to be installed on raspberry pi pico connected to controller board
def main():
    '''
    Defines the main control function. This function reads and writes to/from
    the pi pico from the desktop. It uses json libraries to parse commands and
    available devices.
    '''

    from time import time

    from Library_Communicate import myCom
    from Library_ComSet import deviceList, settings
    from Library_taskManager import myTM
    from Library_parser import parser

    while True:

        if time() >= myCom.getLastExecution() + settings["CommReadOutPeriod"]:
            message_list = myCom.read()
            command_list = parser(messageList=message_list, deviceList=deviceList)
            myTM.addTask(command_list)

        if time() >= myTM.getLastExecution() + settings["TMPeriod"]:

            #add some error handling!
            try:
                myTM.doTasks()

            except:
                pass

if __name__ == "__main__":

    main()
