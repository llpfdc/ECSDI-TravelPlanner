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
from Util.APIKeys import get_acces_token_hotel


# Configuration stuff
hostname = socket.gethostname()
port = 9016

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgentHotelFinder = Agent('AgentHotelFinder',
                       agn.AgentHotelFinder,
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

AgentHotelSelector = Agent('AgentHotelSelector',
                       agn.AgentHotelSelector,
                       'http://%s:9014/comm' % (hostname),
                       'http://%s:9014/Stop' % (hostname))

# Global triplestore graph
dsgraph = Graph()

cola1 = Queue()

# Flask stuff
app = Flask(__name__)
def get_msg_count():
    global mss_cnt
    mss_cnt += 1
    return mss_cnt
def find_hotels(cityCode, radius):
  url = "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-city"
  headers = {
      "Authorization": "Bearer " + get_acces_token_hotel()
  }
  params = {
      "cityCode": cityCode,
      "radius": radius,
      "radiusUnit": "KM",
      "hotelSource":  "ALL"
  }
  response = requests.get(url, headers=headers, params=params)
  return response.json()

def find_best_hotels(hotelIds, checkInDate, checkOutDate, priceRange):
  url = "https://test.api.amadeus.com/v3/shopping/hotel-offers"
  headers = {
      "Authorization": "Bearer " + get_acces_token_hotel()
  }
  params = {
      "hotelIds": hotelIds,
      "adults": 1,
      "checkInDate": checkInDate,
      "checkOutDate": checkOutDate,
      "roomQuantity": 1,
      "priceRange": priceRange,
      "currency": "EUR",
      "paymentPolicity": "NONE",
      "includeClosed": False,
      "bestRateOnly": True
  }
  response = requests.get(url, headers=headers, params=params)
  return response.json()


def get_hotelId(data):
    max = len(data["data"])
    hotels = [0 for i in range (max)]
    i = 0
    while i < max:
        hotels[i] = data["data"][i]["hotelId"]
        i = i + 1
    return hotels

def find_best_hotel(hotels):
  max = len(hotels["data"])
  i = 0
  best_hotel = None
  best_offer = None
  hotel = [0 for i in range (2)]
  while i < max:
      max_offers = len(hotels["data"][i]["offers"])
      j = 0
      while j < max:
        if best_hotel is None:
          best_hotel = i
          best_offer = j
        else:
          if hotels["data"][best_hotel]["offers"][best_offer]["price"]["total"] > hotels["data"][i]["offers"][j]["price"]["total"]:
            best_hotel = i
            best_offer = j
        j += 1
      i += 1
  hotel[0] = best_hotel
  hotel[1] = best_offer
  return hotel

def get_hotel_name (data, hotel):
  return data["data"][hotel[0]]["hotel"]["name"]

def get_checkInDate(data, hotel):
  return data["data"][hotel[0]]["offers"][hotel[1]]["checkInDate"]

def get_checkOutDate(data, hotel):
  return data["data"][hotel[0]]["offers"][hotel[1]]["checkOutDate"]

def get_hotel_latitude(data, hotel):
  return data["data"][hotel[0]]["hotel"]["latitude"]

def get_hotel_longitude(data, hotel):
  return data["data"][hotel[0]]["hotel"]["longitude"]

def get_price(data, hotel):
  return data["data"][hotel[0]]["offers"][hotel[1]]["price"]["total"]

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

    if msdict is None:  # Si el mensaje no tiene contenido
        ghotels = build_message(Graph(), ACL['not-understood'], sender=AgentHotelFinder.uri, msgcnt=get_msg_count())
        return ghotels
    else:
        if msdict['performative'] != ACL.request:
            ghotels = build_message(Graph(), ACL['not-understood'], sender=AgentHotelFinder.uri, msgcnt=get_msg_count())
            return ghotels
        else:
            content = msdict['content']
            action = g.value(subject=content, predicate=RDF.type)
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
                        if central:
                            restrictionsDict['central'] = 5
                        else:
                            restrictionsDict['central'] = 10
                print(restrictionsDict)
                results = find_hotels(restrictionsDict['city'],restrictionsDict['central'])
                hotelsId = get_hotelId(results)
                hotels = find_best_hotels(','.join(hotelsId), restrictionsDict['checkindate'], restrictionsDict['checkoutdate'], restrictionsDict['price'])
                print("Hotels: ", hotels)
                hotel = find_best_hotel(hotels)
                print("Best hotel: ", hotels["data"][hotel[0]])
                print("Best hotel offer: ", hotels["data"][hotel[0]]["offers"][hotel[1]])

                result_graph = Graph()
                hotel_subj = ONTO['Hotel']
                result_graph.add((hotel_subj, RDF.type, ONTO.Hotel))
                result_graph.add((hotel_subj, ONTO.HotelName, Literal(get_hotel_name(hotels, hotel))))
                result_graph.add((hotel_subj, ONTO.CheckInDate, Literal(get_checkInDate(hotels, hotel))))
                result_graph.add((hotel_subj, ONTO.CheckOutDate, Literal(get_checkOutDate(hotels, hotel))))
                result_graph.add((hotel_subj, ONTO.HotelPrice, Literal(get_price(hotels, hotel))))
                result_graph.add((hotel_subj, ONTO.HotelLatitude, Literal(get_hotel_latitude(hotels, hotel))))
                result_graph.add((hotel_subj, ONTO.HotelLongitude, Literal(get_hotel_longitude(hotels, hotel))))
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
