from flask import Flask, request, jsonify, abort
import socket
import json

host = "127.0.0.1"
port = 5050

app = Flask(__name__)

from flask_cors import CORS
CORS(app)

def get_answer_from_engine(bottype, data):
    mySocket = socket.socket()
    mySocket.connect((host, port))

    json_data = {
        'Query': data['query'],
        'BotType': bottype
    }

    if 'selection' in data:
        json_data['Selection'] = data['selection']
    elif 'word' in data:
        json_data['Word'] = data['word']
    elif 'trade' in data:
        json_data['Trade'] = data['trade']
        json_data['Intent'] = data['intent']
    elif 'cancel' in data:
        json_data['Cancel'] = data['cancel']
    elif 'eor' in data:
        json_data['Eor'] = data['eor']

    message = json.dumps(json_data)
    mySocket.send(message.encode())

    data = mySocket.recv(4096).decode()
    ret_data = json.loads(data)

    mySocket.close()
    return ret_data


@app.route('/query/<bot_type>', methods=['POST'])
def query(bot_type):

    data = request.get_json()

    try:        
        if bot_type == 'ruby':
            ret = get_answer_from_engine(bottype='루비', data=data)
            return jsonify(ret)

        elif bot_type == "bbuggu":
            ret = get_answer_from_engine(bottype='뿌꾸', data=data)
            return jsonify(ret)

        else:
            abort(404)

    except Exception as ex:
        abort(500)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.10', port=5000)