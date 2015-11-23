#!/usr/bin/python

from MCP230xx import MCP230XX
import time
import threading
import ConfigParser

from dateutil import parser
import datetime

import os
import Pyro4

import sys
import signal

import subprocess

from ReportSystem import EmailReport
from Sensors import getTemps, getSwitchState, getFloatState, readTemps
from Sensors import gpio as Pins2


class ACChannel:
    """
    This class holds the data needed for each AC channel 
    Each channel can have different modes.
    "off" - always off
    "on" - always on
    "daily timer" - the channel is a time that turns on at onTime and off at 
                    offTime every day.
    """
   
    channel = 0
    plugStr = ""
    mode = "off"

    currentState = -1

    onTime = 0
    offTime = 0

    offPin = 8
    onPin = 9
    filling = False

    onTemp = 75
    offTemp = 77
    tempChannel = 0
    isOn = False 

    def __init__(self, channel):
        self.channel = channel
        self.plugStr = "ACChannel %d" % channel 

    def loadConfig(self):

        self.mode = config.get(self.plugStr, "mode")
        
        if self.mode == "daily timer":
            self.onTime = parser.parse(config.get(self.plugStr, "onTime")).time()
            self.offTime = parser.parse(config.get(self.plugStr, "offTime")).time()

        if self.mode == "topoff":
            self._state_changed('filling', False, self.filling)

        if self.mode == "thermostat":
            self.onTemp = float(config.get(self.plugStr, "lowTemp"))
            self.offTemp = float(config.get(self.plugStr, "highTemp"))
            self.tempChannel = int(config.get(self.plugStr, "tempChannel"))
            self._state_changed('thermostat', False, self.isOn)

    def _state_changed(self, label, oldstate, state):
        print label

        data_logger = Pyro4.Proxy("PYRONAME:data.logger")
        datum = {} 
        datum[label+'Time%d' % self.channel] = datetime.datetime.now()
        datum[label+'State%d' % self.channel] = oldstate
        data_logger.addDatum(datum)

        datum[label+'State%d' % self.channel] = state
        data_logger.addDatum(datum)

    def setState(self, now):

        
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
            on = getFloatState(self.onPin)
            off = getFloatState(self.offPin)

            oldFilling = self.filling

            if off == 1 and self.filling is True:
                self.filling = False
            if on == 0 and off == 0:
                self.filling = True

            if oldFilling is not self.filling:
                self._state_changed('filling', oldFilling, self.filling)

            state = self.filling

        elif self.mode == "thermostat":
            oldIsOn = self.isOn 
            temp =  getTemps()[self.tempChannel]
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

            if oldIsOn is not self.isOn:
                self._state_changed('thermostat', oldIsOn, self.isOn)

            state = self.isOn
            

        else:
            state = False

        if state is not self.currentState:
            if self.channel < 16:
	        print "Change on channel ", self.channel
                acPins.output(self.channel, not(state))
            else:
	        print "Change on channel ", self.channel - 6
                Pins2.output(self.channel - 6, state)
	    self.currentState = state



def configLoader():

    sState = -1

    path = "/home/jims/src/controller/config/"

    while True:
        cState = getSwitchState()
        if sState is not cState: 
            filename = 'config%d.ini' % cState 
            sState = cState 
            print "Loading config: " + filename

            config.read(path + "config0.ini")
            config.read(path + filename)

            for acChannel in acChannels:
                acChannel.loadConfig()
            report.loadConfig(config) 
                
        try:
            pass
        except:
            print "Config error"

        time.sleep(0.1)


def timerLoop():
    while True:
        now = datetime.datetime.now()
        for jjj in range(18):
            acChannels[jjj].setState(now)
        time.sleep(0.1)

def reportLoop():
    while True:
        report.addReportData()
        time.sleep(eval(config.get("Report", "delay")))
        
# Start the pyro name server
nsThread = threading.Thread(target=Pyro4.naming.startNSloop)
nsThread.daemon = True
nsThread.start()
Pyro4.locateNS() # Block until nsThread has started up

#Start the configParser
config = ConfigParser.ConfigParser()

# Set up the two MCP23017's
acPins = MCP230XX(busnum = 1, address = 0x20, num_gpios = 16)

# Set all of the pints in the first MCP to output
for iii in range(16):
    acPins.config(iii, 0)


# Create the ACChannel list
acChannels = [ACChannel(iii) for iii in range(18)]

#Connect to the email server
report = EmailReport()

#Start the datalogger
print "Starting the data logger"
data_logger = subprocess.Popen(["/usr/bin/python",
                                "/home/jims/src/controller/DataLogger.py"])

#Start the temperature Reader
tempThread = threading.Thread(target=readTemps)
tempThread.daemon = True
tempThread.start()

time.sleep(4)

# Start  the config file thread
configThread = threading.Thread(target=configLoader)
configThread.daemon = True
configThread.start()


#Sleep for a moment so te config and temps can be read for the first time
time.sleep(1)

#Start the webServer 
#web_server = subprocess.Popen(["/usr/bin/python",
#                               "/home/jims/src/controller/webServer/webServer.py"])

# Start the ACChanel controller thread 
timerThread = threading.Thread(target=timerLoop)
timerThread.daemon = True
timerThread.start()

# Start the ACChanel controller thread 
reportThread = threading.Thread(target=reportLoop)
reportThread.daemon = True
reportThread.start()

report.start()

def signal_term_handler(signal, frame):
    report.stop()
    data_logger.terminate()
    web_server.terminate()
    sys.exit(0)
 
signal.signal(signal.SIGINT, signal_term_handler)

signal.pause()
