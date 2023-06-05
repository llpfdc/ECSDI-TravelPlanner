import json
from datetime import datetime
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

__author__ = 'sergioguri00'

# Configuration stuff
hostname = socket.gethostname()
port = 9032

agn = Namespace("http://www.agentes.org#")

# Contador de mensajes
mss_cnt = 0

# Datos del Agente

AgentActivitiesFinder = Agent('AgentActivitiesFinder',
                       agn.AgentActivitiesFinder,
                       'http://%s:%d/comm' % (hostname, port),
                       'http://%s:%d/Stop' % (hostname, port))


AgentConsultor = Agent('AgentConsultor',
                       agn.AgentConsultor,
                       'http://%s:9010/comm' % (hostname),
                       'http://%s:9010/Stop' % (hostname))

AgentActivitiesSelector = Agent('AgentActivitiesSelector',
                       agn.AgentActivitiesSelector,
                       'http://%s:9031/comm' % (hostname),
                       'http://%s:9031/Stop' % (hostname))
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
def find_activities(city, outbound, returnDate, rangePlayful, rangeFestive, rangeCultural):
  suma = int(rangePlayful) + int(rangeCultural)
  outbound_date = datetime.strptime(outbound, "%Y-%m-%d").date()
  return_date = datetime.strptime(returnDate, "%Y-%m-%d").date()
  days = (return_date - outbound_date).days
  res_playful = round(days * 2 * (int(rangePlayful) / suma))
  res_culture = round(days * 2 * (int(rangeCultural) / suma))
  res_festive = round((int(rangeFestive) / 3) * days)
  rest = days + (days - int(rangeFestive))
  city = str(city)
  if city=="BCN": city = "Barcelona"
  if city=="BER": city = "Berlin"
  if city=="DFW": city = "Dallas"
  if city=="LON": city = "London"
  if city=="NYC": city = "New York"
  if city=="PAR": city = "Paris"
  if city=="SFO": city = "San Fra"

  url = "https://test.api.amadeus.com/v1/reference-data/locations/cities"
  headers = {
      "Authorization": "Bearer " + get_acces_token_flight()
  }
  params = {
      "keyword": city,
      "max": 1
  }
  response = requests.get(url, headers=headers, params=params)
  response_data = json.loads(response.text)
  latitude = response_data['data'][0]['geoCode']['latitude']
  longitude = response_data['data'][0]['geoCode']['longitude']

  url = "https://test.api.amadeus.com/v1/reference-data/locations/pois"
  paramsCultural = {
      "latitude": latitude,
      "longitude": longitude,
      "radius": 5,
      "categories": 'SIGHTS'
  }
  paramsPlayful = {
      "latitude": latitude,
      "longitude": longitude,
      "radius": 5,
      "categories": 'SHOPPING'
  }
  paramsFestival = {
      "latitude": latitude,
      "longitude": longitude,
      "radius": 5,
      "categories": 'NIGHTLIFE'
  }
  paramsRestaurant = {
      "latitude": latitude,
      "longitude": longitude,
      "radius": 5,
      "categories": 'RESTAURANT'
  }
  response = requests.get(url, headers=headers, params=paramsCultural)
  cultural = []
  response_data = json.loads(response.text)
  print(response.json)
  poi_data = response_data["data"][:res_culture]
  for poi in poi_data:
      name = poi["name"]
      latitude = poi["geoCode"]["latitude"]
      longitude = poi["geoCode"]["longitude"]
      cultural.append(
          {'name': name, 'latitude': latitude, 'longitude': longitude})

  time.sleep(2)

  response = requests.get(url, headers=headers, params=paramsPlayful)
  playful = []
  response_data = json.loads(response.text)
  print(response.json)
  poi_data = response_data["data"][:res_playful]
  for poi in poi_data:
      name = poi["name"]
      latitude = poi["geoCode"]["latitude"]
      longitude = poi["geoCode"]["longitude"]
      playful.append(
          {'name': name, 'latitude': latitude, 'longitude': longitude})

  time.sleep(2)

  response = requests.get(url, headers=headers, params=paramsFestival)
  festival = []
  response_data = json.loads(response.text)
  print(response.json)
  poi_data = response_data["data"][:res_festive]
  for poi in poi_data:
      name = poi["name"]
      latitude = poi["geoCode"]["latitude"]
      longitude = poi["geoCode"]["longitude"]
      festival.append(
          {'name': name, 'latitude': latitude, 'longitude': longitude})

  time.sleep(2)

  response = requests.get(url, headers=headers, params=paramsRestaurant)
  restaurants = []
  response_data = json.loads(response.text)
  print(response.json)
  poi_data = response_data["data"][:rest]
  for poi in poi_data:
      name = poi["name"]
      latitude = poi["geoCode"]["latitude"]
      longitude = poi["geoCode"]["longitude"]
      restaurants.append(
          {'name': name, 'latitude': latitude, 'longitude': longitude})

  result = []
  for i in range(days):
      day = []
      if (len(cultural) - 1 >= i):
          day.append(cultural[i])
      else:
          day.append(playful[days - 1 + (i - len(cultural) + 1)])
      day.append(restaurants[i])
      if (len(playful) - 1 >= i):
          day.append(playful[i])
      else:
          day.append(cultural[days - 1 + (i - len(playful) + 1)])
      if (len(festival) - 1 >= i):
          day.append(festival[i])
      else:
          day.append(restaurants[days - 1 + (i - len(festival) + 1)])
      result.append(day)

  json_result = json.dumps(result)

  return json_result

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

    if msdict is None:  # Si el mensaje no tiene contenido
        gactivities = build_message(Graph(), ACL['not-understood'], sender=AgentActivitiesFinder.uri, msgcnt=get_msg_count())
        return gactivities
    else:
        if msdict['performative'] != ACL.request:
            gactivities = build_message(Graph(), ACL['not-understood'], sender=AgentActivitiesFinder.uri, msgcnt=get_msg_count())
            return gactivities
        else:
            content = msdict['content']
            action = g.value(subject=content, predicate=RDF.type)
            if action == ONTO.SearchActivities:
                restrictions = g.objects(content,ONTO.RestrictedBy)
                print(restrictions)
                restrictionsDict = {}
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
                results = find_activities(restrictionsDict['city'], restrictionsDict['outbound'], restrictionsDict['return'], restrictionsDict['rangePlayful'], restrictionsDict['rangeFestive'], restrictionsDict['rangeCultural'])
                result_graph = Graph()
                activities_subj = ONTO['Activities']
                result_graph.add((activities_subj, RDF.type, ONTO.Activities))
                result_graph.add((activities_subj, ONTO.Activities, Literal(results)))

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

