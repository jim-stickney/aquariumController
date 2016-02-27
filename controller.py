#!/usr/bin/python

import time
import ConfigParser

from dateutil import parser
import datetime

import os

import sys
import signal

import smbus


class ACChannel:
    """
    This class holds the data needed for each AC channel 
    Each channel can have different modes.
    "off" - always off
    "on" - always on
    "daily timer" - the channel is a time that turns on at onTime and off at 
                    offTime every day.
    """
   
    def __init__(self, channel, io):
        
        self.io = io

        self.channel = channel
        self.plugStr = "ACChannel %d" % channel 

        self.mode = "off"

        self.currentState = -1

        self.onTime = 0
        self.offTime = 0

        self.offPin = 8
        self.onPin = 9
        self.filling = False

        self.onTemp = 75
        self.offTemp = 77
        self.tempChannel = 0
        self.isOn = False 


    def loadConfig(self, config):

        self.mode = config.get(self.plugStr, "mode")
        
        if self.mode == "daily timer":
            self.onTime = parser.parse(config.get(self.plugStr, "onTime")).time()
            self.offTime = parser.parse(config.get(self.plugStr, "offTime")).time()

        if self.mode == "thermostat":
            self.onTemp = float(config.get(self.plugStr, "lowTemp"))
            self.offTemp = float(config.get(self.plugStr, "highTemp"))
            self.tempChannel = int(config.get(self.plugStr, "tempChannel"))

    def getState(self, now):

        if self.mode == "off":
            state = False
        elif self.mode == "on":
            state = True
        elif self.mode == "daily timer":
            now = now.time()
            if self.onTime < self.offTime:
                state = self.onTime < now and now < self.offTime
            else:
                state = not( self.offTime < now < self.onTime ) 

        elif self.mode == "topoff":

            off, on = self.io.getFloat()

            oldFilling = self.filling

            if off == 1 and self.filling is True:
                self.filling = False
            if on == 0 and off == 0:
                self.filling = True

            state = self.filling

        elif self.mode == "thermostat":
            oldIsOn = self.isOn 
            temp =  io.getTemps()[self.tempChannel]
            if self.onTemp < self.offTemp:
                if temp < self.onTemp:
                    self.isOn = True
                if temp > self.offTemp and self.isOn == True:
                    self.isOn = False
            else:
                if temp > self.onTemp:
                    self.isOn = True
                if temp < self.offTemp and self.isOn == True:
                    self.isOn = False

            state = self.isOn
            

        else:
            state = False

        if state:
            return 1<<self.channel 
        else:
            return 0


# The device addresses
DEVICE0 = 0x20
DEVICE1 = 0x21

# Pin direction registers
IODIRA = 0x00
IODIRB = 0x01

# Intput registers
GPIOA = 0x12
GPIOB = 0x13

# Output registers
OLATA = 0x14
OLATB = 0x15

# The pull up registers
GPPUA = 0x0C
GPPUB = 0x0D


class ioPins: 

    def __init__(self):
        self.lastTempUpdate = datetime.datetime.now()
        self.lastTemps = []

    def setupPins(self):

        # Device0 A all pins should be output
        if bus.read_byte_data(DEVICE0, IODIRA) is not 0x00:
            bus.write_byte_data(DEVICE0, IODIRA, 0x00)

        # Device0 B all pins should be output
        if bus.read_byte_data(DEVICE0, IODIRB) is not 0x00:
            bus.write_byte_data(DEVICE0, IODIRB, 0x00)

        # Device1 A first 4 pins should be input 
        if bus.read_byte_data(DEVICE1, IODIRA) is not 0x0F:
            bus.write_byte_data(DEVICE1, IODIRA, 0x0F)

        # Device1 A first 4 pins should be pulled up 
        if bus.read_byte_data(DEVICE1, IODIRA) is not 0x0F:
            bus.write_byte_data(DEVICE1, GPPUA, 0x0F)


        # Device1 B frist 2 pins should be pulled up 
        if bus.read_byte_data(DEVICE1, IODIRB) is not 0x03:
            bus.write_byte_data(DEVICE1, IODIRB, 0x03)

        # Device1 B first 2 pins should be pulled up 
        if bus.read_byte_data(DEVICE1, IODIRB) is not 0x03:
            bus.write_byte_data(DEVICE1, GPPUB, 0x03)

    def getSwitch(self):
        S = bus.read_byte_data(DEVICE1, GPIOA)
        S &= 15

        return 15 - S

    def getFloat(self):
        F = bus.read_byte_data(DEVICE1, GPIOB)
        F &= 3

        off = (F & 1)
        on = (F & 2) - 1

        return off, on

    def getTemps(self):

        bus = '/sys/bus/w1/devices/'
        devices = os.listdir(bus)

        now = datetime.datetime.now()
        dT = datetime.timedelta(seconds=60) 
        if (now - self.lastTempUpdate) > dT or len(self.lastTemps) == 0:

            temps = []
            for d in devices:
                if d[:2] == '28':

                    f = open(bus + d + '/w1_slave')
                    data = f.readlines()
                    f.close()

                    data = data[1].split()[-1][2:]
                    data = eval(data)/1000.0
                    
                    temps.append(data*1.8 + 32.0)
            self.lastTemps = temps 
            self.lastTempUpdate = now
                
        return self.lastTemps 

    def setPins(self, state):

        stateA = sState & 255
        stateB = (sState >> 8) & 255
        stateC = ((sState >> 16) & 3) << 2

        stateA = 255 - stateA
        stateB = 255 - stateB
        # stateC = 255 - stateC

        # print bin(stateA)
        # print bin(stateB)
        # print bin(stateC)
        bus.write_byte_data(DEVICE0, OLATA, stateA)
        bus.write_byte_data(DEVICE0, OLATB, stateB)
        bus.write_byte_data(DEVICE1, OLATB, stateC)


class configLoader():

    def __init__(self, io, channels):
        self.sState = -1
        self.io = io
        self.channels = channels

        self.path = "/home/jims/src/controller2/config/"
       

    def checkConfig(self): 
        cState = self.io.getSwitch() 

        if self.sState is not cState: 
            
            config = ConfigParser.ConfigParser()
            
            filename = 'config%d.ini' % cState 
            self.sState = cState 

            config.read(self.path + "config0.ini")
            config.read(self.path + filename)

            for acChannel in self.channels:
                acChannel.loadConfig(config)


class LogData:

    def __init__(self, io):
        dT = datetime.timedelta(minutes = 20)
        self.lastUpdate = datetime.datetime.now() - dT
        self.io = io

        self.sState = -1
        self.Switch = -1
        self.Float = -1

    def update(self, sState):

        off, on = io.getFloat()
        Float = off + 2*on

        Switch = io.getSwitch()

        now = datetime.datetime.now()
        dT = datetime.timedelta(minutes=10)

        A = now - self.lastUpdate > dT
        B = sState != self.sState
        C = Float != self.Float
        D = Switch != self.Switch

        if A or B or C or D:

            self.sState = sState
            self.Float = Float
            self.Switch = Switch

            self.lastUpdate = now
            #Wirte to file
            data = "%s\t" % now
            temps = self.io.getTemps()
            for temp in temps:
                data += "%f\t" % temp

            data += "%s," % format(sState >>  16, '02b')
            data += "%s," % format((sState >> 8) & 255, '08b')
            data += "%s\t" % format(sState & 255, '08b')


            data += "%s\t" % format(Switch, '04b')
            data += "%s" % format(Float, '02b')

            print data

            data += "\n"

            with open('/home/jims/data.log', 'a') as F:
                F.write(data)


bus = smbus.SMBus(1)
io = ioPins()

channels = []
for iii in range(18):
    channels.append(ACChannel(iii, io))

cLoad = configLoader(io, channels)

logData = LogData(io)

#Main Loop
while True:
    io.setupPins()

    cLoad.checkConfig()

    now = datetime.datetime.now()
    sState = 0
    for channel in channels:
        sState += channel.getState(now)
    io.setPins(sState)

    logData.update(sState)

    time.sleep(0.1)
