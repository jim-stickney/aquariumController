import netrc
import smtplib
import datetime

class EmailReport:

    def __init__(self, config):

        passwds = netrc.netrc('/root/.netrc')
        host = config.get("email", "server")
        port = config.get("email", "port")
        self.sendTo = config.get("email", "sendaddress")
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
                            self.sendTo,
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


