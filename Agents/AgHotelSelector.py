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

__author__ = 'ericpereziban'

# Configuration stuff
hostname = socket.gethostname()
port = 9014

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgentHotelSelector = Agent('AgentHotelSelector',
                       agn.AgentHotelSelector,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)

AgentConsultor = Agent('AgentConsultor',
                       agn.AgentConsultor,
                       'http://%s:9010/comm' % (hostname),
                       'http://%s:9010/Stop' % (hostname))

AgentHotelFinder = Agent('AgentHotelFinder',
                       agn.AgentHotelFinder,
                       'http://%s:9016/comm' % (hostname),
                       'http://%s:9016/Stop' % (hostname))

# Global triplestore graph
dsgraph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)

def get_msg_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt


@app.route("/comm")
def comunicacion():
    """
    Entrypoint de comunicacion
    """

    global dsgraph
    global mss_cnt
    message = request.args['content']

    g = Graph()
    g.parse(data=message, format='xml')
    msdict = get_message_properties(g)

    ghotels = None

    if msdict is None:
        ghotels = build_message(Graph(),ACL['not-understood'],sender=AgentHotelSelector.uri,msgcnt=get_msg_count())
    else:
        if msdict['performative'] != ACL.request:
            ghotels = build_message(Graph(),ACL['not-understood'],sender=AgentHotelSelector.uri,msgcnt=get_msg_count())

        else:
            content = msdict['content']
            action = g.value(subject=content,predicate=RDF.type)
            print(action)
            if action == ONTO.SearchHotel:
                restrictions = g.objects(content,ONTO.RestrictedBy)
                restrictionsDict = {}

                for restriction in restrictions:
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.CityRestriction:
                        city = g.value(subject=restriction,predicate=ONTO.City)
                        restrictionsDict['city'] = city
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.PriceRestriction:
                        price = g.value(subject=restriction,predicate=ONTO.Price)
                        restrictionsDict['price'] = price
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.CheckInDateRestriction:
                        checkindate = g.value(subject=restriction,predicate=ONTO.CheckInDate)
                        restrictionsDict['checkindate'] = checkindate
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.CheckOutDateRestriction:
                        checkoutdate = g.value(subject=restriction,predicate=ONTO.CheckOutDate)
                        restrictionsDict['checkoutdate'] = checkoutdate
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.CentralRestriction:
                        central = g.value(subject=restriction,predicate=ONTO.Central)
                        restrictionsDict['central'] = central
                print(restrictionsDict)
                searchHotelsAct = ONTO['SearchHotel_' + str(mss_cnt)]
                g.add((searchHotelsAct, RDF.type, ONTO.SearchHotel))
                mss_cnt += 1
                msg = build_message(g, ACL.request, AgentHotelSelector.uri, AgentHotelFinder.uri, searchHotelsAct, mss_cnt)

                print(msg)
                print(AgentHotelFinder.address)
                ghotels = send_message(msg, AgentHotelFinder.address)
                return ghotels.serialize(format='xml'),200
@app.route("/Stop")
def stop():
    """
    Entrypoint que para el agente

    :return:
    """
    tidyup()
    shutdown_server()
    return "Parando Servidor"


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
