# -*- coding: utf-8 -*-
"""
Created on Fri Dec 27 15:58:13 2013

Esqueleto de agente usando los servicios web de Flask

/comm es la entrada para la recepcion de mensajes del agente
/Stop es la entrada que para el agente

Tiene una funcion AgentBehavior1 que se lanza como un thread concurrente

Asume que el agente de registro esta en el puerto 9000

@author: javier
"""
import json
from multiprocessing import Process, Queue
import socket

from rdflib import Namespace, Graph, RDF, Literal, URIRef
from flask import Flask, request,render_template

from Util.FlaskServer import shutdown_server
from Util.Agent import Agent
from Util.ACLMessages import get_message_properties, build_message
from Util.ACLMessages import *
from Util.FlaskServer import shutdown_server
from Util.Agent import Agent
from Util.OntoNamespaces import ACL,ONTO

from Util.Logging import config_logger
__author__ = 'javier'

# Configuration stuff
hostname = socket.gethostname()
port = 9010

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgentConsultor = Agent('AgentConsultor',
                       agn.AgentConsultor,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

AgentFlightSelector = Agent('AgentFlightSelector',
                       agn.AgentFlightSelector,
                            'http://%s:9011/comm' % hostname,
                            'http://%s:9011/Stop' % hostname)

AgentHotelSelector = Agent('AgentHotelSelector',
                       agn.AgentHotelSelector,
                            'http://%s:9014/comm' % hostname,
                            'http://%s:9014/Stop' % hostname)

AgentActivitiesSelector = Agent('AgentActivitiesSelector',
                       agn.AgentActivitiesSelector,
                            'http://%s:9031/comm' % hostname,
                            'http://%s:9031/Stop' % hostname)

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)

# Global triplestore graph
dsgraph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__,template_folder='../templates')


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """
    global dsgraph
    global mss_cnt


    message = request.args['content']

    gm = Graph()
    gm.parse(data=message,format='xml')

    msdic = get_message_properties(gm)

    gr = None
    if msdic is None:
        mss_cnt += 1
        gr = build_message(Graph(), ACL['not-understood'], sender=AgentConsultor.uri, msgcnt=str(mss_cnt))
    else:

        if msdic['performative'] != ACL.request:
            mss_cnt += 1
            gr = build_message(Graph(), ACL['not-understood'], sender=AgentConsultor.uri, msgcnt=str(mss_cnt))

        else:
            content = msdic['content']
            action = gm.value(subject=content, predicate=RDF.type)

            #aqui le llegaran todas las acciones que pueda hacer que le lleguen de otros agentes(ej: cuando todos hayan terminado de realizar las busquedas)
            if action == ONTO.FlightFound:
                flight_departure = gm.objects(content,ONTO.DepartureTime)
                flight_arrival = gm.objects(content,ONTO.ArrivalTime)
                flight_price = gm.objects(content,ONTO.Price)
                print(flight_arrival)
@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    tidyup()
    shutdown_server()
    return "Parando Servidor"

@app.route("/SearchPlan",methods=['GET','POST'])
def SearchPlan():

    if request.method == 'GET':
        return render_template('travel_planner.html')
    else:
        origin = request.form['origin']
        destination = request.form['destination']
        price = request.form['price']
        outboundDate = request.form['outboundDate']
        returnDate = request.form['returnDate']
        central = request.form['rangeCentral']
        rangePlayful = request.form['rangePlayful']
        rangeFestive = request.form['rangeFestive']
        rangeCultural = request.form['rangeCultural']


        #plan = search_plan(origin,destination,price,outboundDate,returnDate,rangePlayful,rangeFestive,rangeCultural)
        hotel = search_hotel(destination, price, outboundDate, returnDate, central)
        activities_searched = search_activities(outboundDate, returnDate, rangePlayful, rangeFestive, rangeCultural)
        res_activities = str(activities_searched.value(subject=ONTO['Activities'], predicate=ONTO.Activities))
        html_activities = json.loads(res_activities)
        return render_template('plan.html',
                               #flight_price_departure=str(plan.value(subject=ONTO['Flight1'], predicate=ONTO.Price)),
                               #flight_arrival_departure=str(plan.value(subject=ONTO['Flight1'], predicate=ONTO.ArrivalTime)),
                               #flight_departure_departure=str(plan.value(subject=ONTO['Flight1'], predicate=ONTO.DepartureTime)),

                               #flight_price_return=str(plan.value(subject=ONTO['Flight2'], predicate=ONTO.Price)),
                               #flight_arrival_return=str(plan.value(subject=ONTO['Flight2'], predicate=ONTO.ArrivalTime)),
                               #flight_departure_return=str(plan.value(subject=ONTO['Flight2'], predicate=ONTO.DepartureTime)),

                               hotel_name=str(hotel.value(subject=ONTO['Hotel'],predicate=ONTO.HotelName)),
                               hotel_checkin=str(hotel.value(subject=ONTO['Hotel'],predicate = ONTO.CheckInDate)),
                               hotel_checkout=str(hotel.value(subject=ONTO['Hotel'], predicate=ONTO.CheckOutDate)),
                               hotel_price=str(hotel.value(subject=ONTO['Hotel'], predicate=ONTO.HotelPrice)),
                               activities = html_activities
                               )

def search_plan(origin,destination,price,outboundDate,returnDate,rangePlayful,rangeFestive,rangeCultural) :
    global mss_cnt

    g = Graph()

    action = ONTO['SearchPlan_' + str(mss_cnt)]
    g.add((action,RDF.type,ONTO.SearchPlan))

    if origin:
        originRestriction = ONTO['OriginRestriction_' + str(mss_cnt)]
        g.add((originRestriction,RDF.type,ONTO.OriginRestriction))
        g.add((originRestriction, ONTO.Origin, Literal(origin)))
        g.add((action,ONTO.RestrictedBy,URIRef(originRestriction)))
    if destination:
        destinationRestriction = ONTO['DestinationRestriction_' + str(mss_cnt)]
        g.add((destinationRestriction,RDF.type,ONTO.DestinationRestriction))
        g.add((destinationRestriction, ONTO.Destination, Literal(destination)))
        g.add((action,ONTO.RestrictedBy,URIRef(destinationRestriction)))
    if price:
        priceRestriction = ONTO['PriceRestriction_' + str(mss_cnt)]
        g.add((priceRestriction,RDF.type,ONTO.PriceRestriction))
        g.add((priceRestriction, ONTO.Price, Literal(price)))
        g.add((action,ONTO.RestrictedBy,URIRef(priceRestriction)))
    if outboundDate:
        outboundRestriction = ONTO['OutboundRestriction_' + str(mss_cnt)]
        g.add((outboundRestriction,RDF.type,ONTO.OutboundRestriction))
        g.add((outboundRestriction, ONTO.Outbound, Literal(outboundDate)))
        g.add((action,ONTO.RestrictedBy,URIRef(outboundRestriction)))
    if returnDate:
        returnRestriction = ONTO['ReturnRestriction_' + str(mss_cnt)]
        g.add((returnRestriction,RDF.type,ONTO.ReturnRestriction))
        g.add((returnRestriction, ONTO.Return, Literal(returnDate)))
        g.add((action,ONTO.RestrictedBy,URIRef(returnRestriction)))
    if rangePlayful:
        playfulRestriction = ONTO['PlayfulRestriction_' + str(mss_cnt)]
        g.add((playfulRestriction,RDF.type,ONTO.PlayfulRestriction))
        g.add((playfulRestriction, ONTO.Playful, Literal(rangePlayful)))
        g.add((action,ONTO.RestrictedBy,URIRef(playfulRestriction)))
    if rangeFestive:
        festiveRestriction = ONTO['FestiveRestriction_' + str(mss_cnt)]
        g.add((festiveRestriction,RDF.type,ONTO.FestiveRestriction))
        g.add((festiveRestriction, ONTO.Festive, Literal(rangeFestive)))
        g.add((action,ONTO.RestrictedBy,URIRef(festiveRestriction)))
    if rangeCultural:
        culturalRestriction = ONTO['CulturalRestriction_' + str(mss_cnt)]
        g.add((culturalRestriction,RDF.type,ONTO.CulturalRestriction))
        g.add((culturalRestriction, ONTO.Festive, Literal(rangeCultural)))
        g.add((action,ONTO.RestrictedBy,URIRef(culturalRestriction)))


    msg = build_message(g,ACL.request, AgentConsultor.uri, AgentFlightSelector.uri, action, mss_cnt)
    mss_cnt +=1
    print(msg)
    resp = send_message(msg, AgentFlightSelector.address)
    return resp

def search_hotel(city, price, checkInDate, checkOutDate, central):
    global mss_cnt

    g = Graph()

    action = ONTO['SearchHotel_' + str(mss_cnt)]
    g.add((action, RDF.type, ONTO.SearchHotel))

    if city:
        cityRestriction = ONTO['CityRestriction_' + str(mss_cnt)]
        g.add((cityRestriction, RDF.type, ONTO.CityRestriction))
        g.add((cityRestriction, ONTO.City, Literal(city)))
        g.add((action, ONTO.RestrictedBy, URIRef(cityRestriction)))
    if price:
        priceRestriction = ONTO['PriceRestriction_' + str(mss_cnt)]
        g.add((priceRestriction, RDF.type, ONTO.PriceRestriction))
        g.add((priceRestriction, ONTO.Price, Literal(price)))
        g.add((action, ONTO.RestrictedBy, URIRef(priceRestriction)))
    if checkInDate:
        checkInDateRestriction = ONTO['CheckInDateRestriction_' + str(mss_cnt)]
        g.add((checkInDateRestriction, RDF.type, ONTO.CheckInDateRestriction))
        g.add((checkInDateRestriction, ONTO.CheckInDate, Literal(checkInDate)))
        g.add((action, ONTO.RestrictedBy, URIRef(checkInDateRestriction)))
    if checkOutDate:
        checkOutDateRestriction = ONTO['CheckOutDateRestriction_' + str(mss_cnt)]
        g.add((checkOutDateRestriction, RDF.type, ONTO.CheckOutDateRestriction))
        g.add((checkOutDateRestriction, ONTO.CheckOutDate, Literal(checkOutDate)))
        g.add((action, ONTO.RestrictedBy, URIRef(checkOutDateRestriction)))
    if central:
        centralRestriction = ONTO['CentralRestriction_' + str(mss_cnt)]
        g.add((centralRestriction, RDF.type, ONTO.CentralRestriction))
        g.add((centralRestriction, ONTO.Central, Literal(central)))
        g.add((action, ONTO.RestrictedBy, URIRef(centralRestriction)))

    msg = build_message(g, ACL.request, AgentConsultor.uri, AgentHotelSelector.uri, action, mss_cnt)
    mss_cnt += 1
    print(msg)
    resp = send_message(msg, AgentHotelSelector.address)
    return resp

def search_activities(outboundDate, returnDate, rangePlayful, rangeFestive, rangeCultural):
    global mss_cnt

    g = Graph()

    action = ONTO['SearchActivities_' + str(mss_cnt)]
    g.add((action, RDF.type, ONTO.SearchActivities))

    if outboundDate:
        outboundRestriction = ONTO['OutboundRestriction_' + str(mss_cnt)]
        g.add((outboundRestriction, RDF.type, ONTO.OutboundRestriction))
        g.add((outboundRestriction, ONTO.Outbound, Literal(outboundDate)))
        g.add((action, ONTO.RestrictedBy, URIRef(outboundRestriction)))
    if returnDate:
        returnRestriction = ONTO['ReturnRestriction_' + str(mss_cnt)]
        g.add((returnRestriction, RDF.type, ONTO.ReturnRestriction))
        g.add((returnRestriction, ONTO.Return, Literal(returnDate)))
        g.add((action, ONTO.RestrictedBy, URIRef(returnRestriction)))
    if rangePlayful:
        playfulRestriction = ONTO['PlayfulRestriction_' + str(mss_cnt)]
        g.add((playfulRestriction, RDF.type, ONTO.PlayfulRestriction))
        g.add((playfulRestriction, ONTO.Playful, Literal(rangePlayful)))
        g.add((action, ONTO.RestrictedBy, URIRef(playfulRestriction)))
    if rangeFestive:
        festiveRestriction = ONTO['FestiveRestriction_' + str(mss_cnt)]
        g.add((festiveRestriction, RDF.type, ONTO.FestiveRestriction))
        g.add((festiveRestriction, ONTO.Festive, Literal(rangeFestive)))
        g.add((action, ONTO.RestrictedBy, URIRef(festiveRestriction)))
    if rangeCultural:
        culturalRestriction = ONTO['CulturalRestriction_' + str(mss_cnt)]
        g.add((culturalRestriction, RDF.type, ONTO.CulturalRestriction))
        g.add((culturalRestriction, ONTO.Cultural, Literal(rangeCultural)))
        g.add((action, ONTO.RestrictedBy, URIRef(culturalRestriction)))

    msg = build_message(g, ACL.request, AgentConsultor.uri, AgentActivitiesSelector.uri, action, mss_cnt)
    mss_cnt += 1
    print(msg)
    resp = send_message(msg, AgentActivitiesSelector.address)
    return resp

def tidyup():
    """
    Acciones previas a parar el agente

    """
    pass


def agentbehavior1(cola):
    """
    Un comportamiento del agente

    :return:
    """
    pass


if __name__ == '__main__':
    # Ponemos en marcha los behaviors
    ab1 = Process(target=agentbehavior1, args=(cola1,))
    ab1.start()

    # Ponemos en marcha el servidor
    app.run(host=hostname, port=port)

    # Esperamos a que acaben los behaviors
    ab1.join()
    print('The End')