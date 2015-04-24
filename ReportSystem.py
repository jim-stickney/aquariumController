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

    loadingConfig = False

    def loadConfig(self, config):
    
        self.loadingConfig = True
    
        if self.email is not None:
            self.email.quit()

        print "Getting passwords"
        passwds = netrc.netrc('/root/.netrc')
        host = config.get("email", "server")
        port = config.get("email", "port")
        self.sendTo = config.get("email", "sendaddress")
        username, acnt, password = passwds.authenticators(host)
        print "Done!"

        
        print "logig on to email"
        email = smtplib.SMTP(host,
                             port
                             )
        email.starttls()


        email.login(username,
                    password
                    )
        print "Done!"

        self.config = config
        self.email = email
        self.username = username

        reportTime = config.get("Report", "reportTime")
        if reportTime == "now":
            self.nextReport = datetime.datetime.now()
        else:
            self.nextReport = parser.parse(reportTime)

        self.loadingConfig = False

    def send(self,
             subject, 
             text, 
             files=[]):

        while self.loadingConfig:
            time.sleep(0.1)

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

        self.email.sendmail(send_from, send_to, msg.as_string())

    def addReportData(self):

        self.temps.append(getTemps())
        self.switchStates.append(getSwitchState())
        self.times.append(datetime.datetime.now())

        now = datetime.datetime.now()

        if datetime.datetime.now() > self.nextReport:
            self.sendReport()


    def sendReport(self):

        delay = eval(self.config.get("Report", "reportPeriod"))
        self.nextReport += datetime.timedelta(hours=delay)
        now = datetime.datetime.now()

        subject = "Status report: " + str(now) 
       
        temps = numpy.array(self.temps)
        avgTemps = temps.sum(0)/temps.shape[0]

        # print avgTemps

        self.avgTimes.append(now)
        self.avgTemps.append(avgTemps)

        msg = ""
        msg += "The current time is " + str(now) + "\n"
        msg += "The next report is scheduled for " + str(self.nextReport) + "\n"
        for iii in range(len(avgTemps)):
            msg += "The average temperature at sensor %d is: %f \n" % (iii, 
                                                                       avgTemps[iii]
                                                                       )

        msg += "The current switch state is: " + str(self.switchStates[-1]) + "\n"

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


