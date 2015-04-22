#!/usr/bin/python

from MCP230xx import MCP230XX
import time
import threading
import ConfigParser

from dateutil import parser
import datetime

import os
import smtplib

import sys
import signal

import netrc


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
        self.plugStr = "ACChannel %d" % channel 

    def loadConfig(self):

        self.mode = config.get(self.plugStr, "mode")
        
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
                # print "Config File Changed"
                mtime = st_mtime
                config.read("/home/jims/src/controller/config.ini")

                for acChannel in acChannels:
                    acChannel.loadConfig()
        except:
            pass

        time.sleep(0.1)


def timerLoop():
    ACState = -1 
    refreshTime = datetime.timedelta(0, 5, 0)
    while True:
        
        data = 0 
        now = datetime.datetime.now()

        for jjj in range(16):
            if acChannels[jjj].getState(now):
                data += 2**jjj

        if data != ACState:
            ACState = data
            ACSetTime = now
            for iii in range(15):

                if data>>iii & 1:
                    state1 = False
                else:
                    state1 = True
                acPins.output(iii, state1) 

        if now - ACSetTime > refreshTime:
            ACState = -1

        switch = 15 
        for kkk in range(4):
            switch -= gpio.input(kkk) 
        print switch 

        time.sleep(0.1)

class Email:

    def __init__(self):

        passwds = netrc.netrc('/root/.netrc')
        host = config.get("email", "server")
        port = config.get("email", "port")
        username, acnt, password = passwds.authenticators(host)

        
        email = smtplib.SMTP(host,
                             port
                             )
        email.starttls()

        email.login(username,
                    password
                    )

        self.username = username
        self.email = email

    def send(self, subject, message):
        subject = "Subject: " + subject
        self.email.sendmail(self.username,
                            config.get("email", "sendaddress"),
                            "\r\n".join([subject, "", message])
                            )

    def start(self):
        subject = "Starting aquarimum controller"
        msg = "The controller is starting at: %s" %  \
              str(datetime.datetime.now())

        self.send(subject, msg)

    def stop(self):
        subject = "Stopping aquarimum controller"
        msg = "The controller is stopping at: %s" %  \
              str(datetime.datetime.now())

        self.send(subject, msg)



#Set up the two MCP23017's
acPins = MCP230XX(busnum = 1, address = 0x20, num_gpios = 16)
for iii in range(16):
    acPins.config(iii, 0)

gpio = MCP230XX(busnum = 1, address = 0x21, num_gpios = 16)
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
email = Email()
# Start the ACChanel controller thread 
timerThread = threading.Thread(target=timerLoop)
timerThread.daemon = True
timerThread.start()

email.start()

def signal_term_handler(signal, frame):
    email.stop()
    sys.exit(0)
 
signal.signal(signal.SIGINT, signal_term_handler)

signal.pause()
