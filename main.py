from flask import Flask, abort
from flask import request
from flask import jsonify
import requests
import json

app = Flask(__name__)
test = {}
sender_id = 'default'
help_text = "This is a sample controller for a system consisting of " \
            "1. a view, 2. a database and 3. a speech processing component. " \
            "It is running on this machine and can be accessed via the port 5005." \
            "If you receive a 404, please check if your natural language processing component and your database " \
            "is up and running. You can test this controller without setting any other services if you use the "


@app.route("/", strict_slashes=False)
@app.route("/help/", strict_slashes=False)
@app.route("/info/", strict_slashes=False)
def info():
    """
    :return: a help text and indicates that the application is running.
    """
    return help_text


@app.route('/<path:path>')
def catch_all(path):
    """
    response for unknown paths.
    :param path: any path that is not declared in other functions.
    :return: an error message.
    """
    return 'You entered this path: %s. It might be, that either this path does not exist ' \
           'or you are using the GET method instead of POST or PUT' % path


@app.route("/api", methods=['POST', 'PUT'])
def process_speech_input():
    """
    processes the given data and returns a JSON containing the requested data.
    :return: a JSON containing the requested data from the database.
    """
    application_state = request.json.get('application_state', None)
    user_utterance = request.json.get('user_utterance', None)

    # Gesture type is ignored at the moment but could be used in former development
    gesture_type = request.json.get('gesture_type', None)
    state = {}
    if application_state:
        if application_state['focused_object']:
            state = {application_state['focused_object_type']: application_state['focused_object']}
        else:
            if application_state['selected_object']:
                state = {application_state['selected_object_type']: application_state['selected_object']}
    if state:
        set_speech_component_context(state)
    speech_component_response = request_speech_component_core(user_utterance)
    return build_response(speech_component_response)


@app.route("/api/intents", methods=['GET'])
def get_all_intents():
    """
    This function returns all intents used by the speech processing service.
    This information might be useful for developing a frontend.
    :return: All intents used by the speech processing service.
    """
    headers = {'Accept': 'application/json'}
    try:
        response = requests.get('http://localhost:5005/domain', headers=headers)
        intents = []
        for item in json.loads(response.text)['intents']:
            for key in dict(item):
                intents.append(key)
        return str(intents)
    except requests.exceptions.RequestException as e:
        print(e)
        abort(404)


def set_speech_component_context(state):
    """
    If given, the context as state will be passed to the natural language component before the utterance is processed.
    :param state: Application context.
    """
    request_array = []
    for state_attribute in state:
        for key, value in state_attribute.iterItems():
            request_data = {
                'event': 'slot',
                'name': key,
                'value': value
            }
            request_array.append(request_data)

    response_slot_setting = requests.put('localhost:5005/conversations/' + sender_id + '/tracker/events', request_array)

    if response_slot_setting:
        print('successfully updated slots')
    else:
        abort(404)


def request_speech_component_core(utterance):
    """
    Passes the users utterance to the speech component.
    :param utterance: The users natural language utterance.
    :return: The response from the nlp service.
    """
    payload = '{"sender": "' + sender_id + '", "message": "' + utterance + '"}'
    headers = {'Content-type': 'application/json'}
    try:
        response = requests.post('http://localhost:5005/webhooks/rest/webhook',
                                 data=payload,
                                 headers=headers)
        return json.loads(response.text)
    except requests.exceptions.RequestException as e:
        print(e)
        abort(404)


def build_response(speech_component_response):
    """
    Builds response out of the retrieved data.
    :param speech_component_response: The response made by the speech_component.
    :return: A JSON with recipient_id, intent_name, natural_language_response, data and error.
    """
    recipient_id = speech_component_response[0].get('recipient_id', None)
    if recipient_id is None:
        recipient_id = sender_id

    if not speech_component_response[0]['text'][0] == "{":
        natural_language_response = speech_component_response[0]['text']
        return jsonify({
            "recipient_id": recipient_id,
            "intent_name": "",
            "natural_language_response": natural_language_response,
            "error": "",
            "data": ""
        })

    speech_component_response_json = json.loads(speech_component_response[0]['text'])
    natural_language_response = 'here is what i found'
    print(speech_component_response_json)
    intent_name = speech_component_response_json['intent']['name']
    confidence = speech_component_response_json['intent']['confidence']
    if confidence < 0.5:
        natural_language_response = 'I am not sure if I got you right. ' + natural_language_response
    error = speech_component_response_json.get('error', '')

    if error:
        return jsonify({
            "recipient_id": recipient_id,
            "intent_name": intent_name,
            "natural_language_response": natural_language_response,
            "error": error,
            "data": ""
        })

    database_query = speech_component_response_json["query"]
    database_response = query_graph_db(database_query)

    return jsonify({
        "recipient_id": recipient_id,
        "intent_name": intent_name,
        "natural_language_response": natural_language_response,
        "error": error,
        "data": convert_db_response(database_response)
    })


def convert_db_response(db_response):
    """
    A simple parser, to extract the the needed information from the database response.
    :param db_response: The database response.
    :return: The data field from the database response if not empty.
    """
    if db_response:
        db_response = json.loads(db_response)
        if len(db_response['data']) == 0:
            return ''
        return db_response['data'][0]
    return ""


def query_graph_db(graph_query):
    """
    Queries the neo4j Database and returns as text.
    :param graph_query: The cypher query for the database.
    :return: The database response.
    """
    graph_query = graph_query.replace('"', '\\"')

    payload = '{"query": "' + graph_query + '"}'
    headers = {'Content-type': 'application/json;charset=utf-8', 'Accept': 'application/json;charset=utf-8'}
    try:
        response = requests.post('http://localhost:7474/db/data/cypher',
                                 data=payload,
                                 headers=headers)
        return response.text
    except requests.exceptions.RequestException as e:
        print(e)
        abort(404)


@app.route("/test", methods=['POST', 'PUT'])
def test_api():
    """
    This is implemented for testing reasons.
    :return: Some test data for testing without the need to have a database or a nlp service.
    """
    return jsonify({
        "recipient_id": 'default',
        "intent_name": 'showAllNodes',
        "natural_language_response": 'this is what I found for your request',
        "error": '',
        "data": ["rce toolkit - common modules", {
            "metadata": {
                "id": 7373,
                "labels": ["compilationUnit"]
            },
            "data": {
                "Loc": 620,
                "name": "asynctaskserviceimpl.java",
                "className": "http://www.example.org/osgiapplicationmodel#//compilationunit"
            },
            "paged_traverse": "http://localhost:7474/db/data/node/7373/"
                              "paged/traverse/{returnType}{?pageSize,leaseTime}",
            "outgoing_relationships": "http://localhost:7474/db/data/node/7373/relationships/out",
            "outgoing_typed_relationships": "http://localhost:7474/db/data/node/7373/"
                                            "relationships/out/{-list|&|types}",
            "create_relationship": "http://localhost:7474/db/data/node/7373/relationships",
            "labels": "http://localhost:7474/db/data/node/7373/labels",
            "traverse": "http://localhost:7474/db/data/node/7373/traverse/{returnType}",
            "extensions": {},
            "all_relationships": "http://localhost:7474/db/data/node/7373/relationships/all",
            "all_typed_relationships": "http://localhost:7474/db/data/node/7373/relationships/all/{-list|&|types}",
            "property": "http://localhost:7474/db/data/node/7373/properties/{key}",
            "self": "http://localhost:7474/db/data/node/7373",
            "incoming_relationships": "http://localhost:7474/db/data/node/7373/relationships/in",
            "properties": "http://localhost:7474/db/data/node/7373/properties",
            "incoming_typed_relationships": "http://localhost:7474/db/data/node/7373/"
                                            "relationships/in/{-list|&|types}"
        }]
    })


def initial_data():
    """
    In future, this method should return the data, for initial visualization if needed.
    :return: an empty string
    """
    return ""
