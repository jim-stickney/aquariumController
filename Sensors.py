import os

from MCP230xx import MCP230XX


gpio = MCP230XX(busnum = 1, address = 0x21, num_gpios = 16)
# Set the first 4 pins on the second MCP to input These are the switches
for iii in range(4):
    gpio.pullup(iii, 1)



def getSwitchState():
    
    switch = 15
    for kkk in range(4):
        switch -= gpio.input(kkk)
    return switch


sensorIDs = {}
sensorIDs['28-000006b13699'] = 'A'
sensorIDs['28-000006882529'] = 'B'

def getTemps():
    
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
    return temps

