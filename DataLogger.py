import Pyro4
import os

import datetime


class DataLogger:

    data = {}
    def addDatum(self, datum):
        for key in datum.keys():
            if key not in self.data.keys():
                self.data[key] = []
            self.data[key].append(datum[key])

    def getData(self):
        return self.data

    def getFirst(self, label):
        if label in self.data.keys():
            return self.data[label][0]   

    def popFirst(self, label):
        if label in self.data.keys():
            self.data[label].pop(0)

    def clearData(self, label):
        if label in self.data.keys():
            self.data.pop(label)
        

daemon=Pyro4.Daemon()
uri=daemon.register(DataLogger())

ns = Pyro4.locateNS()
ns.register("data.logger", uri)

daemon.requestLoop()
