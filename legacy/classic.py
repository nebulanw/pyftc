import json
import websocket
import obsws_python as obs

URI = "ws://localhost/stream/display/command/?code=uswatelt"

match_update_types = ['SHOW_PREVIEW', 'SHOW_MATCH', 'SHOW_RESULTS']
scene_mappings = {
    'SHOW_PREVIEW': "Matches - Score",
    'SHOW_MATCH_F1': "Matches - Left Field",
    'SHOW_MATCH_F2': "Matches - Right Field",
    'SHOW_RESULTS': "Matches - Score"
}
valid_scenes = ["Matches - Score", "Matches - Left Field", "Matches - Right Field"]

def handle_message(message):
    try:
        message = json.loads(message)
    # ignore pong
    except json.JSONDecodeError:
        return

    # ignore initialization messages
    if 'init' in message and message['init'] is True:
        return

    event_type = message['type']

    if not 'type' in message or not event_type in match_update_types:
        return

    if event_type == 'SHOW_MATCH':
        event_type += '_F' + str(message['params']['field'])
    
    new_scene = scene_mappings[event_type]

    current_scene = cl.get_current_program_scene().scene_name
    if current_scene in valid_scenes and current_scene != new_scene:
        print(f"Switching to scene: {new_scene}")
        cl.set_current_program_scene(new_scene)

def on_message(ws, message):
    handle_message(message)

if __name__ == "__main__":
    cl = obs.ReqClient(host='localhost', port=4456, password='placeholder', timeout=3)
    ws = websocket.WebSocketApp(URI, on_message=on_message)
    ws.run_forever()

