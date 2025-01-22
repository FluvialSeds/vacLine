from machine import Pin, I2C
from time import sleep
from Library_Drivers_VacuumSensor import VacuumSensor, ADS1115, AnalogIn


#set up instance
i2c = I2C(1,sda=Pin(6),scl=Pin(7),freq=100000)
#ads = ADS1115(i2c,adr='0x48',gain=1,)
#p0 = AnalogIn(ads,0)
v = VacuumSensor(i2c,name='v',adr='0x48',gain=1)

#make plot
while True:
    v.getVacuum()
    sleep(0.2)
    