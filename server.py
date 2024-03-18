from openai import OpenAI

from dotenv import load_dotenv
load_dotenv()

import json
import tornado.ioloop
import tornado.web
import tornado.websocket
import os
import signal

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.getenv("OPENAI_API_KEY"),
)


def exit_function(signum,frame):
    exit(0)

signal.signal(signal.SIGTERM,exit_function)
signal.signal(signal.SIGINT,exit_function)

path = os.path.join(os.path.dirname(__file__))

websockets = {}

agentBehavior = '''
Tu nombre es Brenda Aiquipa, destacada en medicina general. Te encuentras en una consulta virtual para evaluar el estado de salud
de un paciente. Iniciarás con una cordial presentación y procederás a interrogar mediante preguntas concisas, uno por uno, de tipo 
afirmativo o negativo, para determinar la posible afección. Una vez identificado el diagnóstico preliminar, brindarás recomendaciones.
Si fuese necesario un análisis más detallado o con pruebas físicas, instruirás al paciente a activar el "modo hospital" para 
los exámenes correspondientes.
El paciente activará el modo hospital al decir "modo hospital". En este modo, simularás que el paciente ya se encuentra en un hospital
real y le sugerirás realizar pruebas físicas, una por una, como por ejemplo:
- Ve a enfermería para que te realicen una prueba de sangre y calculen tu índice de masa corporal.
- Ve a nefología para que realicen una prueba de rayos X a tus riñones.
El paciente afirmará cada una de las recomendaciones al decir "Listo" o cualquier otra respuesta afirmativa. Al final, le darás su
diagnóstico y una receta médica, ya sean pastillas, reposo, etc. Y responderás a las consultas adicionales del paciente.
Este ejercicio se desarrolla en el marco de una simulación, por lo que la precisión clínica de las respuestas puede variar. 
Tus intervenciones serán breves, claras y al punto, sin exceder las tres frases y manteniendo la economía de palabras.
'''

def get_gpt_answer(messages):
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",  
        messages = messages
    )
    return completion.choices[0].message.content
def process_message(data,websocket):
    print(data)
    if data["action"] == "registerID":
        websockets[data["id"]] = {"ws" : websocket, "chat_history":[{"role": "system", "content": agentBehavior}]}
    elif data["action"] == "answerChat":
        websockets[data["id"]]["chat_history"].append({"role":"user","content":data["message"]})
        response = get_gpt_answer(websockets[data["id"]]["chat_history"])
        websockets[data["id"]]["chat_history"].append({"role":"assistant","content":response})
        websocket.send_data({"action":"gpt_answer","message":response})
    else:
        print("no action")
class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print("Websocket abierto")
    
    def on_close(self):
        print("Websocket cerrado")

    def send_data(self,data):
        self.write_message(json.dumps(data))

    def on_message(self,message):
        try:
            data = json.loads(message)
            process_message(data,self)
        except TypeError:
            print("error al processar mensaje")

class StaticHandler(tornado.web.StaticFileHandler):
    def get_content_type(self):
        _, extension = tornado.web.os.path.splitext(self.absolute_path)
        
        mime_types = {
            ".js": "application/javascript",
            ".css": "text/css",
            ".html": "text/html",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".svg": "image/svg+xml"
        }
        
        return mime_types.get(extension, "text/plain")

TornadoSettings = static_handler_args={'debug':False}
application = tornado.web.Application([
    (r'/command', WebSocketHandler),
    (r'/(.*)',StaticHandler,{"path":os.path.join(path,"public\\"),"default_filename":"index.html"})
],**TornadoSettings)


if __name__ == '__main__':
    application.listen(80)
    tornado.ioloop.IOLoop.instance().start()
