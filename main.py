from flask import Flask
from flask import request
from flask import jsonify
import requests
import json

app = Flask(__name__)
test = {}
sender_id = 'default'
remote_repository_uri = "bolt://localhost:7687"
help_text = "This is a sample controller for a system consisting of " \
            "1. a view, 2. a database and 3. a speech processing component. " \
            "It is running on this machine and can be accessed via the port 5005."


@app.route("/help/", strict_slashes=False)
@app.route("/info/", strict_slashes=False)
def info():
    return help_text


@app.route("/api", methods=['POST', 'PUT'])
def process_speech_input():
    application_state = request.json['application_state']
    user_utterance = request.json['user_utterance']

    # Gesture type is ignored at the moment but could be used in former development
    gesture_type = request.json['gesture_type']
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


def set_speech_component_context(state):
    request_array = []
    for state_attribute in state:
        for key, value in state_attribute.iterItems():
            request_data = {
                'event': 'slot',
                'name': key,
                'value': value
            }
            request_array.append(request_data)

    return requests.put('localhost:5005/conversations/' + sender_id + '/tracker/events', request_array)


def request_speech_component_core(utterance):
    payload = '{"sender": "' + sender_id + '", "message": "' + utterance + '"}'
    headers = {'Content-type': 'application/json'}
    response = requests.post('http://localhost:5005/webhooks/rest/webhook',
                             data=payload,
                             headers=headers).text
    return json.loads(response)


def build_response(speech_component_response):
    recipient_id = speech_component_response[0]['recipient_id']
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
    intent_name = speech_component_response_json['intent']['name']
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
    if db_response:
        db_response = json.loads(db_response)
        if len(db_response['data']) == 0:
            return ''
        return db_response['data'][0]
    return ""


def query_graph_db(graph_query):
    graph_query = graph_query.replace('"', '\\"')

    payload = '{"query": "' + graph_query + '"}'
    headers = {'Content-type': 'application/json;charset=utf-8', 'Accept': 'application/json;charset=utf-8'}
    response = requests.post('http://localhost:7474/db/data/cypher',
                             data=payload,
                             headers=headers).text
    return response


def initial_data():
    return "allTheDataNeededForVisualisation"
