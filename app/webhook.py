# heavily borrowing from: https://github.com/hiroakis/tornado-websocket-example

from tornado import websocket, web, ioloop
from tornado.ioloop import PeriodicCallback
import json
import os
import opentracing
from ddtrace.opentracer import Tracer, set_global_tracer

# here we keep the currently connected clients
clients = {}

# Here we can keep things to store and forward if a cient reconnects
store = {}


def init_tracer(service_name):
    config = {
      'agent_hostname': os.environ['DATADOG_AGENT_APM_HOST'],
      'agent_port': os.environ['DATADOG_AGENT_APM_PORT'],
    }
    tracer = Tracer(service_name, config=config)
    set_global_tracer(tracer)
    return tracer


class IndexHandler(web.RequestHandler):
    def get(self):
        self.render("index.html")

class SocketHandler(websocket.WebSocketHandler):
    
    def check_origin(self, origin):
        return True

    def open(self):
        with opentracing.tracer.start_span('subscribe') as span:
            self.timeout = None
            self.callback = PeriodicCallback(self.send_hello, 20000)
            self.callback.start()
            tenant = self.request.uri.split('/subscribe/')[1]
            span.set_tag("tenant", tenant)
            clients[tenant] = self
            self.flush_messages(tenant)
            span.finish()

    # keep the connection alive through proxies as much as possible
    def send_hello(self):
        self.ping('ping')
        
    # see if there are any messages to forward on          
    def flush_messages(self, tenant):
        with opentracing.tracer.start_span('flush_messages') as span:
            if tenant in store:
                messages = store[tenant]
                span.set_tag("tenant", tenant)
                span.set_tag("number_of_messages", len(messages))
                for payload in messages:
                    self.write_message(json.dumps(payload, ensure_ascii=False))
            store[tenant] = []
            span.finish()

    def on_close(self):
        with opentracing.tracer.start_span('unsubscribe') as span:
            self.callback.stop()
            tenant = self.request.uri.split('/subscribe/')[1]
            span.set_tag("tenant", tenant)
            if tenant in clients:
                span.set_tag("is_tenant_client", "yes")
                del clients[tenant]
            span.finish()


class ApiHandler(web.RequestHandler):

    @web.asynchronous
    def get(self, *args):
        self.finish()

    @web.asynchronous
    def post(self, *args):
        with opentracing.tracer.start_span('publish') as span:
            publishedUri = self.request.uri.split('/publish/')[1]
            span.set_tag("publishedUri", publishedUri)
            tenant = publishedUri.split('/')[0]
            span.set_tag("tenant", tenant)
            endpoint = "/" + "/".join(publishedUri.split('/')[1:])
            span.set_tag("endpoint", endpoint)
            headers = {}
            for header in self.request.headers:
                headers[header] = self.request.headers[header]
            payload = {'headers': headers, 'requestPath': endpoint, 'body': self.request.body}

            if tenant in clients:
                span.set_tag("is_tenant_client", "yes")
                clients[tenant].write_message(json.dumps(payload, ensure_ascii=False))
            else:
                self.store_message(tenant, payload)
            span.finish()
            self.finish()

    def store_message(self, tenant, payload):
        if tenant in store:
            store[tenant].append(payload)

app = web.Application([
    (r'/', IndexHandler),
    (r'/subscribe/.*', SocketHandler),
    (r'/publish/.*', ApiHandler),
    (r'/(favicon.ico)', web.StaticFileHandler, {'path': '../'}),
    (r'/(rest_api_example.png)', web.StaticFileHandler, {'path': './'}),
])

if __name__ == '__main__':
    init_tracer("webhook-relay")
    app.listen(8080)
    ioloop.IOLoop.instance().start()
