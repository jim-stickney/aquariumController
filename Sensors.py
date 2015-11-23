import os

from MCP230xx import MCP230XX

import threading
import time

gpio = MCP230XX(busnum = 1, address = 0x21, num_gpios = 16)
# Set the first 4 pins on the second MCP to input These are the switches
for iii in range(4):
    gpio.pullup(iii, 1)

for iii in [8,9]:
    gpio.pullup(iii, 1)

gpio.config(10, 0)
gpio.config(11, 0)


def getFloatState(pin):
    
    return gpio.input(pin)>>pin

def getSwitchState():
    
    switch = 15
    for kkk in range(4):
        switch -= gpio.input(kkk)
    return switch


sensorIDs = {}
sensorIDs['28-000006878783'] = 'A'
sensorIDs['28-00000687bab0'] = 'B'

delay = 10 
tempData = [[0,0]]
def readTemps():
    while True:
        bus = '/sys/bus/w1/devices/'
        devices = os.listdir(bus)

        Temps = {}
        temps = []

        for d in devices:
            if d[:2] == '28':

                f = open(bus + d + '/w1_slave')
                data = f.readlines()
                f.close()

                data = data[1].split()[-1][2:]
                data = eval(data)/1000.0
                
                Temps[sensorIDs[d]] = data*1.8 + 32.0

        temps = [Temps['A'], Temps['B']]
        tempData[0] = temps
        time.sleep(delay)


def getTemps():
    return tempData[0] 

