#!/usr/bin/python

from MCP230xx import MCP230XX
import time
import threading
import ConfigParser

from dateutil import parser
import datetime

import os

import sys
import signal


from ReportSystem import EmailReport


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

    def __init__(self, channel):
        self.channel = channel
        self.plugStr = "ACChannel %d" % channel 

    def loadConfig(self):

        self.mode = config.get(self.plugStr, "mode")
        
        if self.mode == "daily timer":
            self.onTime = parser.parse(config.get(self.plugStr, "onTime"))
            self.offTime = parser.parse(config.get(self.plugStr, "offTime"))

    def setState(self, now):

        
        if self.mode == "off":
            state = False
        elif self.mode == "on":
            state = True
        elif self.mode == "daily timer":
            state = self.onTime < now and now < self.offTime

        if state is not self.currentState:
            print "Writting pin: ", self.channel
            acPins.output(self.channel, state) 
            self.currentState = state
            
    

def configLoader():
    mtime = 0

    while True:
        try:
            st_mtime = os.stat("/home/jims/src/controller/config.ini").st_mtime
            if st_mtime != mtime:
                # print "Config File Changed"
                mtime = st_mtime
                config.read("/home/jims/src/controller/config.ini")

                for acChannel in acChannels:
                    acChannel.loadConfig()
        except:
            pass

        time.sleep(0.1)


def timerLoop():
    refreshTime = datetime.timedelta(0, 5, 0)
    while True:
        
        now = datetime.datetime.now()

        print "Setting acChannels: ", now
        for jjj in range(16):
            acChannels[jjj].setState(now)
        print "Done"

        switch = 15 
        for kkk in range(4):
            switch -= gpio.input(kkk) 
        print switch 

        time.sleep(0.1)

# Set up the two MCP23017's
acPins = MCP230XX(busnum = 1, address = 0x20, num_gpios = 16)
# Set all of the pints in the first MCP to output
for iii in range(16):
    acPins.config(iii, 0)

gpio = MCP230XX(busnum = 1, address = 0x21, num_gpios = 16)
# Set the first 4 pins on the second MCP to input
# These are the switches
for iii in range(4):
    gpio.pullup(iii, 1)

config = ConfigParser.ConfigParser()


# Create the ACChannel list
acChannels = [ACChannel(iii) for iii in range(16)]

# Start  the config file thread
configThread = threading.Thread(target=configLoader)
configThread.daemon = True
configThread.start()

#Sleep for a moment so te config can be read for the first time
time.sleep(0.01)

#Connect to the email server
report = EmailReport(config)

# Start the ACChanel controller thread 
timerThread = threading.Thread(target=timerLoop)
timerThread.daemon = True
timerThread.start()

report.start()

def signal_term_handler(signal, frame):
    # report.stop()
    sys.exit(0)
 
signal.signal(signal.SIGINT, signal_term_handler)

signal.pause()
