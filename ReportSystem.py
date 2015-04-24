import netrc
import smtplib, os

import matplotlib
matplotlib.use('Agg')
import pylab
import numpy

from dateutil import parser
import time
import datetime

from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from email import encoders

from Sensors import getTemps, getSwitchState

class EmailReport:

    temps = []
    switchStates = []
    times = []
    avgTemps = []
    avgTimes = []

    email = None

    loadingConfig = True 

    def loadConfig(self, config):
    
        self.loadingConfig = True
    
        passwds = netrc.netrc('/root/.netrc')
        self.host = config.get("email", "server")
        self.port = config.get("email", "port")
        self.sendTo = config.get("email", "sendaddress")
        self.username, acnt, self.password = passwds.authenticators(self.host)

        self.config = config

        reportTime = config.get("Report", "reportTime")
        if reportTime == "now":
            self.lastReport = datetime.datetime.now()
        else:
            self.lastReport = parser.parse(reportTime)

        delay = eval(self.config.get("Report", "reportPeriod"))
        # self.delay = datetime.timedelta(hours=delay)
        self.delay = datetime.timedelta(minutes = delay)

        self.loadingConfig = False

    def send(self,
             subject, 
             text, 
             files=[]):

        while self.loadingConfig:
            time.sleep(0.01)

        send_from = self.username
        send_to = self.sendTo

        msg = MIMEMultipart()
        msg['From'] = send_from
        msg['To'] = send_to
        msg['Date'] = formatdate(localtime = True)
        msg['Subject'] = subject

        msg.attach( MIMEText(text) )

        for f in files:
            part = MIMEBase('application', "octet-stream")
            part.set_payload( open(f,"rb").read() )
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', 
                            'attachment; filename="{0}"'.format(os.path.basename(f)))
            msg.attach(part)

        email = smtplib.SMTP(self.host,
                             self.port
                             )
        email.starttls()
        email.login(self.username,
                    self.password
                    )

        email.sendmail(send_from, send_to, msg.as_string())

        email.quit()

    def addReportData(self):

        while self.loadingConfig:
            time.sleep(0.01)

        self.temps.append(getTemps())
        self.switchStates.append(getSwitchState())
        self.times.append(datetime.datetime.now())

        now = datetime.datetime.now()

        if datetime.datetime.now() > self.lastReport+self.delay:
            self.sendReport()


    def sendReport(self):

        now = datetime.datetime.now()
        while self.lastReport < now:
            self.lastReport += self.delay

        subject = "Status report: " + str(now) 
       
        temps = numpy.array(self.temps)
        avgTemps = temps.sum(0)/temps.shape[0]


        self.avgTimes.append(now)
        self.avgTemps.append(avgTemps)

        msg = ""
        msg += "The current time is " + str(now) + "\n"
        msg += "The next report is scheduled for "  
        msg += str(self.lastReport + self.delay) + "\n"
        for iii in range(len(avgTemps)):
            msg += "The average temperature at sensor %d is: %f \n" % (iii, 
                                                                       avgTemps[iii]
                                                                       )

        msg += "The current switch state is: " + str(self.switchStates[-1]) + "\n"

        pylab.clf()
        pylab.plot_date(self.times, self.temps, '-')
        pylab.xlabel('date')
        pylab.ylabel('Temperature (deg F)')
        pylab.savefig('/tmp/tempPlot.png')
        
        pylab.clf()
        pylab.plot_date(self.avgTimes, self.avgTemps, '-')
        pylab.xlabel('date')
        pylab.ylabel('Dailey Average Temperature (deg F)')
        pylab.savefig('/tmp/avgTempPlot.png')

        self.send(subject, msg, ['/tmp/tempPlot.png', 
                                 '/tmp/avgTempPlot.png'])

        self.temps = []
        self.times = []
        self.swtichStates = []

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


