class Subscription:

    @classmethod
    def create(cls, id: str, host: str, port: int, protocol: str, subscriber: str, termination: str):

        obj = cls()
        obj.id = id
        obj.host = host
        obj.port = port
        obj.protocol = protocol
        obj.subscriber = subscriber
        obj.termination = termination

        return obj
    
    def __init__(self):
        self.id = None
        self.host = None
        self.port = None
        self.protocol = None
        self.subscriber = None
        self.termination = None

        self.remote_service_participant_ref = None
        self.remote_service_startup_time = None

        self.single_endpoint = None
        self.status_endpoint = '/status'
        self.subscribe_endpoint = '/subscribe'
        self.unsubscribe_endpoint = '/unsubscribe'