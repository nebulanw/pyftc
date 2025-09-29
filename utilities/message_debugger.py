import websocket
import json

def on_message(ws, message):
    m1 = json.loads(message)
    print(f"mIsInit: {m1['init']:<2} type: {m1['type']:<15} field {m1['params']['field']}")

ws = websocket.WebSocketApp('ws://localhost/stream/display/command/?code=uswaspm1', on_message=on_message)
ws.run_forever()
