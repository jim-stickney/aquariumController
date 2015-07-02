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

import Pyro4

data_logger = Pyro4.Proxy("PYRONAME:data.logger")

class EmailReport:

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

        self.lastAverage = self.lastReport = datetime.datetime.now()
        avgPeriod = eval(self.config.get("Report", "avgPeriod"))
        self.avgPeriod = datetime.timedelta(minutes = avgPeriod)

        delay = eval(self.config.get("Report", "reportPeriod"))
        # self.delay = datetime.timedelta(hours = delay)
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

        datum = {}
        datum['time'] = datetime.datetime.now()
        datum['temps'] = getTemps()

        data_logger.addDatum(datum)

        now = datetime.datetime.now()

        now = datetime.datetime.now()

        while parser.parse(data_logger.getFirst('time')) < now - self.avgPeriod: 
            data_logger.popFirst('time')
            data_logger.popFirst('temps')

        if now > self.lastAverage+self.avgPeriod:
            print "Doing average"
            data = data_logger.getData()

            temps = numpy.array(data['temps'])
            avgTemp = list(temps.sum(0)/temps.shape[0])
            print "N = ", temps.shape[0]

            datum = {'avgTimes':self.lastAverage, 'avgTemps':avgTemp}
            data_logger.addDatum(datum)
            
            while self.lastAverage+self.avgPeriod < now:
                self.lastAverage += self.avgPeriod

        if now > self.lastReport+self.delay:
            print "emailing report"
            self.sendReport()


    def sendReport(self):

        now = datetime.datetime.now()
        while self.lastReport+self.delay < now:
            self.lastReport += self.delay

        subject = "Status report: " + str(now) 
       
        temps = getTemps()
        msg = ""
        msg += "The current time is " + str(now) + "\n"
        msg += "The next report is scheduled for "  
        msg += str(self.lastReport + self.delay) + "\n"
        for iii in range(len(temps)):
            msg += "The current temperature at sensor %d is: %f \n" % (iii, 
                                                                       temps[iii] 
                                                                       )
        ss = getSwitchState()
        msg += "The current switch state is: " 
        msg += str(ss) + "\n"


        times = []
        temps = []

        data = data_logger.getData()

        if 'avgTemps' in data.keys():
            temps += data['avgTemps']
            for t in data['avgTimes']:
                times.append(parser.parse(t))

        if 'temps' in data.keys():
            temps += data['temps']
            for t in data['time']:
                times.append(parser.parse(t))


        temps = numpy.array(temps)
    

        pylab.clf()
        pylab.plot_date(times, temps, '-')
        pylab.xlabel('date')
        pylab.ylabel('Temperature (deg F)')
        pylab.savefig('/tmp/tempPlot.png')
        
        self.send(subject, msg, ['/tmp/tempPlot.png', ])

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


