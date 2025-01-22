from Library_Drivers_MFC import MFC
from machine import Pin, UART
from time import sleep, ticks_ms, ticks_diff

foo = MFC(name="foo",bus=1,baud=57600,pinRx=9,pinTx=8,maxFlow=200)
%foo = MFC(name="foo",bus=0,baud=57600,pinRx=1,pinTx=0,maxFlow=200)
foo.getSerialNumber()

%get serial number
cmd = [0x61, 0x00]

#calculate checksum by adding up all the values inside the command array
chksum = sum(cmd)

#add checksum to the command array
cmd.extend([chksum % 256])

#now send command to read serial number
foo.myUart.write(bytearray(cmd))

#----------------------------------------------------------------------#
# USE STATIC RESPONSE

#statically wait for response and read
sleep(0.05) #50 milliseconds

i1 = foo.myUart.read()

sleep(0.02) #another 20 milliseconds
#----------------------------------------------------------------------#

#convert output hex to int
k = (i1[1]*256 + i1[2])

#print output to browser window
print(foo.name,'Serial Number:',k)






from machine import Pin, I2C
from time import sleep
from Library_Drivers_VacuumSensor import VacuumSensor, ADS1115, AnalogIn

i2c = I2C(1,sda=Pin(6),scl=Pin(7),freq=100000)
ads = ADS1115(i2c,adr='0x48',gain=1,)
p0 = AnalogIn(ads,0)


v = VacuumSensor(i2c,name='v',adr='0x48',gain=1)
%v.getVacuum()


