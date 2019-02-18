# VR-Input-Controller
Controller for multiple input modalities for VR and AR Devices

# This controller is configured following the [MVC](https://en.wikipedia.org/wiki/Model%E2%80%93view%E2%80%93controller) 
principle to work with the following projects:

The [RiQue](https://github.com/Pseipel/RiQue) component is used as a service for natural language processing. 
It is based on the Rasa Chatbot API. In the RiQue project you can also find a descruption for setting up 
a neo4j graph database. This database is used as the repository for the used architecture implemented here.

In general the view can be any device that is capable of sending http requests. 
In our case the view is implemented of the Microsoft HoloLens in [this project](https://github.com/DLR-SC/holo-island-viz).

# Usage

## Install and start server

1. `pip install Flask` 
2. `pip install requests`
3. `FLASK_APP=main.py flask run` 
4. See if the application is running by going to [https://localhost:5005/](https://localhost:5005/)

## defined interfaces

The `controller` expects the following format of input:

```
{
  recipient_id: 'default',
  application_state: 
    {
      focused_object: 'rce vampzero compeonent',
      focused_object_type: 'package',
      selected_object: 'rce core component',
      selected_object_type: 'bundle',
      gesture_type: 'double tap'
    },
  user_utterance: 'show information for this bundle'
}
```

The `recipient_id` will be used to have multiple conversations at the same time.
The `application_state` is representing the context the user is in. The `focused object` is prioritized. 
If this is empty, the `selected object` will be used instead. At the moment, the `gesture_type` is not used. 
`user_utterance` is a string representation of the utterance made by the user.

The response to this input has the format:
```
{
  'recipient_id': 'default',
  'natural_language_response': 'This is what I found for your question',
  'data': 
    [
      {name: '', path: '', value: '42', ...}
    ],
  'intent_name': 'showAllNodes',
  'error': ''
}
```

The `controller` queries a database and returns the retrieved data to the `view` in field `data`. 
`natural_language_string` can be used as a response for the user. 
`intent_name` is an additional field the view can use to inform the user, what the RiQue extracted out of his utterance.
In case of failure the `error` field is filled.

## Address for requests

Depending on the machine you are using, the controller is running on the default port `5000` and the address `http://localhost:5000/api`.

An example for testing with curl looks like this:

`curl -XPOST http://localhost:5000/api 
-H "Content-type: application/json;charset=utf-8" 
-H "Accept: application/json; charset=UTF-8"
-d {
  recipient_id: 'default',
  application_state: 
    {
      focused_object: '',
      focused_object_type: '',
      selected_object: 'rce core component',
      selected_object_type: 'bundle',
      gesture_type: ''
    },
  user_utterance: 'show information fir this bundle'
} | python -m json.tool`

The last part ` | python -m json.tool` is optional and just for beautifying the controllers response.
