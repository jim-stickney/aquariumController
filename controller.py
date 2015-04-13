import RPi.GPIO as GPIO ## Import GPIO library
import time
import threading
import ConfigParser

from dateutil import parser
import datetime

import os


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

    onTime = 0
    offTime = 0

    def __init__(self, channel):
        self.channel = channel
        self.plugStr = "plug %d" % channel 

    def loadConfig(self):
        print self.plugStr

        self.mode = config.get(self.plugStr, "mode")

        print self.mode
        
        if self.mode == "daily timer":
            self.onTime = parser.parse(config.get(self.plugStr, "onTime"))
            self.offTime = parser.parse(config.get(self.plugStr, "offTime"))

    def getState(self, now):

        if self.mode == "off":
            return False
        elif self.mode == "on":
            return True
        elif self.mode == "daily timer":
            return self.onTime < now and now < self.offTime
    

def configLoader():
    mtime = 0

    while True:
        try:
            st_mtime = os.stat("/home/jims/src/controller/config.ini").st_mtime
            if st_mtime != mtime:
                print "Config File Changed"
                mtime = st_mtime
                config.read("/home/jims/src/controller/config.ini")

                for acChannel in acChannels:
                    acChannel.loadConfig()
        except:
            pass

        time.sleep(0.1)


def timerLoop():
    ACState = -1 
    refreshTime = datetime.timedelta(0, 5*60, 0)
    while True:
        
        data = 0 
        now = datetime.datetime.now()

        for jjj in range(8):
            if acChannels[jjj].getState(now):
                data += 2**jjj

        if data != ACState:
            ACState = data
            ACSetTime = now
            for iii in range(8):

                if data>>(7-iii) & 1:
                    state = False
                else:
                    state = True
                GPIO.output(DSA, state) 

                GPIO.output(CLK, True) 
                GPIO.output(CLK, False) 

        if now - ACSetTime > refreshTime:
            ACState = -1

        

        time.sleep(0.1)



#Set up the GPIO for the controller
DSA = 17
CLK = 27

GPIO.setmode(GPIO.BCM) ## Use board pin numbering
GPIO.setup(DSA, GPIO.OUT) ## Setup GPIO Pin 17 to OUT
GPIO.setup(CLK, GPIO.OUT) ## Setup GPIO Pin 27 to OUT

config = ConfigParser.ConfigParser()

# Create the ACChannel list
acChannels = [ACChannel(iii) for iii in range(8)]

# Start  the config file thread
configThread = threading.Thread(target=configLoader)
configThread.daemon = True
configThread.start()

# Start the ACChanel controller thread 
timerThread = threading.Thread(target=timerLoop)
timerThread.daemon = True
timerThread.start()

try:
    while True:
        time.sleep(10)

        
except:
    print "exiting!"
    GPIO.cleanup()
