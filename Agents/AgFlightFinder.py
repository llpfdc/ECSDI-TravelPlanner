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
from Util.APIKeys import get_acces_token_flight
import time

# Configuration stuff
hostname = socket.gethostname()
port = 9012

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgentFlightFinder = Agent('AgentFlightFinder',
                       agn.AgentFlightFinder,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))


AgentConsultor = Agent('AgentConsultor',
                       agn.AgentConsultor,
                       'http://%s:9010/comm' % (hostname),
                       'http://%s:9010/Stop' % (hostname))

AgentFlightSelector = Agent('AgentFlightSelector',
                       agn.AgentFlightSelector,
                       'http://%s:9011/comm' % (hostname),
                       'http://%s:9011/Stop' % (hostname))
# Directory agent address
DirectoryAgent = Agent('DirectoryAgent',
                       agn.Directory,
                       'http://%s:9000/Register' % hostname,
                       'http://%s:9000/Stop' % hostname)

# Global triplestore graph
dsgraph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)
def get_msg_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt
def find_flight(origin,dest,departureDate ,returnDate,maxPrice):
  url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
  headers = {
      "Authorization": "Bearer " + get_acces_token_flight()
  }
  params = {
      "originLocationCode": origin,
      "destinationLocationCode": dest,
      "departureDate" : departureDate,
      "adults": 1,
      "maxPrice": maxPrice,
      "currencyCode": "EUR",
      "max": 1
  }
  response = requests.get(url, headers=headers, params=params)
  return response.json()


def get_departure(data):
    return data["data"][0]["itineraries"][0]["segments"][0]["departure"]


def get_arrival(data):
    return data["data"][0]["itineraries"][0]["segments"][0]["arrival"]


def get_price(data):
    return data["data"][0]["price"]

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

    gflights = None

    if msdict is None:  # Si el mensaje no tiene contenido
        gflights = build_message(Graph(), ACL['not-understood'], sender=AgentFlightFinder.uri, msgcnt=get_msg_count())
        return gflights
    else:
        if msdict['performative'] != ACL.request:
            gflights = build_message(Graph(), ACL['not-understood'], sender=AgentFlightFinder.uri, msgcnt=get_msg_count())
            return gflights
        else:
            content = msdict['content']
            action = g.value(subject=content, predicate=RDF.type)
            if action == ONTO.SearchPlan:
                restrictions = g.objects(content,ONTO.RestrictedBy)
                restrictionsDict = {}
                for restriction in restrictions:
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.OriginRestriction:
                        origin = str(g.value(subject=restriction,predicate=ONTO.Origin))
                        restrictionsDict['origin'] = origin
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.DestinationRestriction:
                        destination = str(g.value(subject=restriction,predicate=ONTO.Destination))
                        restrictionsDict['destination'] = destination
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.PriceRestriction:
                        price = int(g.value(subject=restriction,predicate=ONTO.Price))
                        restrictionsDict['price'] = price
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.OutboundRestriction:
                        outbound = str(g.value(subject=restriction,predicate=ONTO.Outbound))
                        restrictionsDict['outbound'] = outbound
                    if g.value(subject=restriction,predicate=RDF.type) == ONTO.ReturnRestriction:
                        returnDate = str(g.value(subject=restriction,predicate=ONTO.Return))
                        restrictionsDict['return'] = returnDate
                print(restrictionsDict)

                results1 = find_flight(restrictionsDict['origin'],restrictionsDict['destination'],restrictionsDict['outbound'],restrictionsDict['return'],restrictionsDict['price'])
                result_graph = Graph()
                flight_subj = ONTO['Flight1']
                result_graph.add((flight_subj, RDF.type, ONTO.Flight1))
                result_graph.add((flight_subj, ONTO.DepartureTime, Literal(get_departure(results1)['at'])))
                result_graph.add((flight_subj, ONTO.ArrivalTime, Literal(get_arrival(results1)['at'])))
                result_graph.add((flight_subj, ONTO.Price, Literal(get_price(results1)['total'])))
                time.sleep(2)
                results2 = find_flight(restrictionsDict['destination'],restrictionsDict['origin'], restrictionsDict['return'],restrictionsDict['outbound'],restrictionsDict['price'])
                flight_subj = ONTO['Flight2']
                result_graph.add((flight_subj, RDF.type, ONTO.Flight2))
                result_graph.add((flight_subj, ONTO.DepartureTime, Literal(get_departure(results2)['at'])))
                result_graph.add((flight_subj, ONTO.ArrivalTime, Literal(get_arrival(results2)['at'])))
                result_graph.add((flight_subj, ONTO.Price, Literal(get_price(results2)['total'])))


                return result_graph.serialize(format='xml'), 200

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
