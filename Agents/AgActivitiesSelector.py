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

__author__ = 'sergioguri00'

# Configuration stuff
hostname = socket.gethostname()
port = 9031

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgentActivitiesSelector = Agent('AgentActivitiesSelector',
                       agn.AgentActivitiesSelector,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))

# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)

#AgentConsultor = Agent('AgentConsultor',
#                       agn.AgentConsultor,
#                       'http://%s:9010/comm' % (hostname),
#                       'http://%s:9010/Stop' % (hostname))

AgentActivitiesFinder = Agent('AgentActivitiesFinder',
                       agn.AgentActivitiestFinder,
                       'http://%s:9032/comm' % (hostname),
                       'http://%s:9032/Stop' % (hostname))

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

    gactivities = None

    if msdict is None: #Si el mensaje no tiene contenido
        gactivities = build_message(Graph(),ACL['not-understood'],sender=AgentActivitiesSelector.uri,msgcnt=get_msg_count())
    else:
        if msdict['performative'] != ACL.request: #Si no es una performativa de request(en este caso solo acepta request)
            gactivities = build_message(Graph(),ACL['not-understood'],sender=AgentActivitiesSelector.uri,msgcnt=get_msg_count())

        else:
            content = msdict['content']
            action = g.value(subject=content,predicate=RDF.type)

            if action == ONTO.SearchActivities:
                restrictions = g.objects(content,ONTO.RestrictedBy)
                restrictionsDict = {}
                print(restrictions)
                for restriction in restrictions:
                    if g.value(subject=restriction, predicate=RDF.type) == ONTO.CityRestriction:
                        city = g.value(subject=restriction, predicate=ONTO.City)
                        restrictionsDict['city'] = city
                    if g.value(subject=restriction, predicate=RDF.type) == ONTO.PlayfulRestriction:
                        rangePlayful = g.value(subject=restriction, predicate=ONTO.Playful)
                        restrictionsDict['rangePlayful'] = rangePlayful
                    if g.value(subject=restriction, predicate=RDF.type) == ONTO.FestiveRestriction:
                        rangeFestive = g.value(subject=restriction, predicate=ONTO.Festive)
                        restrictionsDict['rangeFestive'] = rangeFestive
                    if g.value(subject=restriction, predicate=RDF.type) == ONTO.CulturalRestriction:
                        rangeCultural = g.value(subject=restriction, predicate=ONTO.Cultural)
                        restrictionsDict['rangeCultural'] = rangeCultural
                    if g.value(subject=restriction, predicate=RDF.type) == ONTO.OutboundRestriction:
                        outbound = g.value(subject=restriction, predicate=ONTO.Outbound)
                        restrictionsDict['outbound'] = outbound
                    if g.value(subject=restriction, predicate=RDF.type) == ONTO.ReturnRestriction:
                        returnDate = g.value(subject=restriction, predicate=ONTO.Return)
                        restrictionsDict['return'] = returnDate
                print(restrictionsDict)
                searchActivitiesAct = ONTO['SearchActivities_' + str(mss_cnt)]
                g.add((searchActivitiesAct, RDF.type, ONTO.SearchActivities))
                mss_cnt += 1
                msg = build_message(g, ACL.request, AgentActivitiesSelector.uri, AgentActivitiesFinder.uri, searchActivitiesAct, mss_cnt)

                gactivities = send_message(msg, AgentActivitiesFinder.address)

                return gactivities.serialize(format='xml'),200
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

