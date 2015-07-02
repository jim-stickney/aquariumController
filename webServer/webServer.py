from flask import Flask, render_template, Markup

import datetime


import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy
plt.ioff()

from dateutil import parser

import mpld3

import Pyro4

app = Flask(__name__)

data_logger = Pyro4.Proxy('PYRONAME:data.logger')

@app.route("/")
def hello():


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
    
    fig, ax = plt.subplots()
    ax.cla()
    ax.plot_date(times, temps, '-')
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature (in deg F)")

    nT = len(data['thermostatTime1'])
    thermostatTimes = [0]*(nT+1)
    thermostatState = numpy.zeros(nT+1)
    for iii in range(nT):
        thermostatState[iii] = int(data['thermostatState1'][iii] )
        thermostatTimes[iii] = parser.parse(data['thermostatTime1'][iii])

    thermostatTimes[-1] = datetime.datetime.now() 
    thermostatState[-1] = thermostatState[-2]

    fig1, ax1 = plt.subplots()
    ax1.cla()
    ax1.plot_date(thermostatTimes, thermostatState, '-')
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Thermostat State")

    nT = len(data['fillingTime0'])
    fillingTimes = [0]*(nT+1)
    fillingState = numpy.zeros(nT+1)
    for iii in range(nT):
        fillingState[iii] = int(data['fillingState0'][iii] )
        fillingTimes[iii] = parser.parse(data['fillingTime0'][iii])

    fillingTimes[-1] = datetime.datetime.now() 
    fillingState[-1] = fillingState[-2]
        
    fig2, ax2 = plt.subplots()
    ax2.cla()
    ax2.plot_date(fillingTimes, fillingState, '-')
    ax2.set_xlabel("Time")
    ax2.set_ylabel("Filling State")
    
    now = datetime.datetime.now()
    timeString = now.strftime("%Y-%m-%d %H:%M")
    templateData = {'title': "My aquarium status",
                    'time': timeString,
                    'tempFigure' : Markup(mpld3.fig_to_html(fig)),
                    'thermostatFigure' : Markup(mpld3.fig_to_html(fig1)),
                    'fillingFigure' : Markup(mpld3.fig_to_html(fig2)),
                    }

    return render_template('main.html', **templateData)


app.run(host='0.0.0.0', port=80, debug=True)
