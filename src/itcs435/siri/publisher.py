import logging
import requests
import time
import typing
import uvicorn

from datetime import datetime
from datetime import timezone
from fastapi import FastAPI
from fastapi import BackgroundTasks
from fastapi import APIRouter
from fastapi import Request
from fastapi import Response
from threading import Thread

from itcs435.siri.datalog import Datalog
from itcs435.siri.participantconfig import ParticipantConfig
from itcs435.siri.subscription import Subscription


class Publisher:
    def __init__(self, participant_ref: str, participant_config_filename: str, local_ip_address: str = '0.0.0.0', datalog_directory: str|None = None):
        self._service_participant_ref = participant_ref
        self._service_local_ip_address = local_ip_address
        self._datalog = datalog_directory

        self._logger = logging.getLogger('uvicorn')

        #self._local_node_database = local_node_database('vdv736.publisher')

        try:
            self._participant_config = ParticipantConfig(participant_config_filename)
        except Exception as ex:
            self._logger.error(ex)

        self._on_subscribe = None
        self._on_unsubscribe = None

    def __enter__(self):
        self.start()

        return self

    def __exit__(self, exception_type, exception_value, exception_traceback) -> None:
        self.stop()

        """if self._local_node_database is not None:
            self._local_node_database.close(True)"""
        
    def start(self) -> None:
        self._endpoint_thread = Thread(target=self._run_endpoint, args=(), name='siri_publisher_endpoint_thread', daemon=True)
        self._endpoint_thread.start()

        time.sleep(0.01) # give the endpoint thread time for startup
        self._logger.info(f"Publisher running at {self._participant_config.participants[self._service_participant_ref]['host']}:{self._participant_config.participants[self._service_participant_ref]['port']}")
        #self._logger.info(f"Local node database at {self._local_node_database._filename}")

        # set internal callbacks
        self._endpoint.set_callbacks(
            on_subscribe_callback=self._on_subscribe_internal,
            on_unsubscribe_callback=self._on_unsubscribe_internal
        )

    def stop(self) -> None:
        if self._endpoint is not None:
            self._endpoint.terminate()
        
        if self._endpoint_thread is not None:
            self._endpoint_thread.join(1)
    
    """def set_callbacks(self, on_status_callback: typing.Callable[[], None]|None = None, on_subscribe_callback: typing.Callable[[Subscription], None]|None = None, on_unsubscribe_callback: typing.Callable[[Subscription], None]|None = None, on_request_callback: typing.Callable[[], None]|None = None) -> None:
        self._on_subscribe = on_subscribe_callback
        self._on_unsubscribe = on_unsubscribe_callback

        self._endpoint.set_callbacks(
            on_status_callback=on_status_callback,
            on_subscribe_callback=self._on_subscribe_internal,
            on_unsubscribe_callback=self._on_unsubscribe_internal, 
            on_request_callback=on_request_callback
        )"""

    """def publish_situation(self, situation: PublicTransportSituation) -> None:
        situation_id = sirixml_get_value(situation, 'SituationNumber')
        self._local_node_database.add_or_update_situation(situation_id, situation)
        
        for _, subscription in self._local_node_database.get_subscriptions().items():
            delivery = SituationExchangeDelivery(self._service_participant_ref, subscription)
            delivery.add_situation(situation)

            response = self._send_request(subscription, delivery)

            if response is not None and sirixml_get_value(response, 'Siri.DataReceivedAcknowledgement.Status', False):
                self._logger.info(f"Sent delivery for subscription {subscription.id} to {subscription.subscriber} successfully")
            else:
                self._logger.error(f"Failed to send delivery for subscription {subscription.id} to {subscription.subscriber}")"""

    def _on_subscribe_internal(self, subscription: Subscription) -> None:
        
        # send initial load here
        """delivery = SituationExchangeDelivery(self._service_participant_ref, subscription)
        for _, situation in self._local_node_database.get_situations().items():
            delivery.add_situation(situation)

        response = self._send_request(subscription, delivery)

        if sirixml_get_value(response, 'Siri.DataReceivedAcknowledgement.Status', False):
            self._logger.info(f"Sent initial load delivery for subscription {subscription.id} to {subscription.subscriber} successfully")
        else:
            self._logger.error(f"Failed to send initial load delivery for subscription {subscription.id} to {subscription.subscriber}")

        # call external callback method
        if self._on_subscribe is not None:
            self._on_subscribe(subscription)"""

    def _on_unsubscribe_internal(self, subscription: Subscription) -> None:

        """# call external callback method
        if self._on_unsubscribe is not None:
            self._on_unsubscribe(subscription)"""
    
    def _run_endpoint(self) -> None:
        self._endpoint = PublisherEndpoint(self._service_participant_ref, self._datalog)

        # disable uvicorn logs
        logging.getLogger('uvicorn.error').handlers = []
        logging.getLogger('uvicorn.error').propagate = False

        logging.getLogger('uvicorn.access').handlers = []
        logging.getLogger('uvicorn.access').propagate = False

        logging.getLogger('uvicorn.asgi').handlers = []
        logging.getLogger('uvicorn.asgi').propagate = False

        # run ASGI server with endpoint
        endpoint_host = self._service_local_ip_address # self._participant_config.participants[self._service_participant_ref]['host']
        endpoint_port = self._participant_config.participants[self._service_participant_ref]['port']

        uvicorn.run(app=self._endpoint.create_endpoint(
            self._service_participant_ref,
            self._participant_config.participants[self._service_participant_ref]['single_endpoint'],
            self._participant_config.participants[self._service_participant_ref]['status_endpoint'],
            self._participant_config.participants[self._service_participant_ref]['subscribe_endpoint'],
            self._participant_config.participants[self._service_participant_ref]['unsubscribe_endpoint'],
            self._participant_config.participants[self._service_participant_ref]['request_endpoint']
        ), host=endpoint_host, port=endpoint_port)

    def _send_request(self, subscription: Subscription, siri_delivery) -> object|None:
        try:
            subscription_host = self._participant_config.participants[subscription.subscriber]['host']
            subscription_port = self._participant_config.participants[subscription.subscriber]['port']
            subscription_protocol = self._participant_config.participants[subscription.subscriber]['protocol']
            
            """if isinstance(siri_delivery, SituationExchangeDelivery):
                delivery_endpoint = self._participant_config.participants[subscription.subscriber]['single_endpoint'] if self._participant_config.participants[subscription.subscriber]['single_endpoint'] is not None else self._participant_config.participants[subscription.subscriber]['delivery_endpoint']
                endpoint = f"{subscription_protocol}://{subscription_host}:{subscription_port}{delivery_endpoint}"""
            
            endpoint = ""

            headers = {
                "Content-Type": "application/xml"
            }

            if self._datalog is not None:
                Datalog.create(self._datalog, siri_delivery.xml(), {
                    'method': 'POST',
                    'endpoint': endpoint,
                    'headers': headers
                }, self._service_participant_ref, 'OUT', type(siri_delivery).__name__, 'Request')
            
            response_xml = requests.post(endpoint, headers=headers, data=siri_delivery.xml())

            if self._datalog is not None:
                Datalog.create(self._datalog, response_xml.content, {
                    'method': 'POST',
                    'endpoint': endpoint,
                    'headers': headers
                }, self._service_participant_ref, 'OUT', type(siri_delivery).__name__, 'Response')

            response = ""#xml2siri_response(response_xml.content)

            return response
        except Exception as ex:
            self._logger.exception(ex)
            return None

class PublisherEndpoint():

    def __init__(self, participant_ref: str, datalog_directory: str|None = None):
        self._service_participant_ref = participant_ref
        self._service_startup_time = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        self._logger = logging.getLogger('uvicorn')
        self._datalog = datalog_directory

        self._router = APIRouter()
        self._endpoint = FastAPI()

        #self._local_node_database = local_node_database('vdv736.publisher')
        
        self._on_status = None
        self._on_subscribe = None
        self._on_unsubscribe = None
        self._on_request = None

    def set_callbacks(self, on_status_callback: typing.Callable[[], None]|None = None, on_subscribe_callback: typing.Callable[[Subscription], None]|None = None, on_unsubscribe_callback: typing.Callable[[Subscription], None]|None = None, on_request_callback: typing.Callable[[], None]|None = None) -> None:
        self._on_status = on_status_callback
        self._on_subscribe = on_subscribe_callback
        self._on_unsubscribe = on_unsubscribe_callback
        self._on_request = on_request_callback

    def create_endpoint(self, participant_ref: str, single_endpoint: str|None = None, status_endpoint: str = '/status', subscribe_endpoint: str = '/subscribe', unsubscribe_endpoint: str = '/unsubscribe', request_endpoint: str = '/request') -> FastAPI:
        self._participant_ref = participant_ref

        if single_endpoint is not None:
            self._router.add_api_route(single_endpoint, self._dispatcher, methods=['POST'])
        else:
            self._router.add_api_route(status_endpoint, self._status, methods=['POST'])
            self._router.add_api_route(subscribe_endpoint, self._subscribe, methods=['POST'])
            self._router.add_api_route(unsubscribe_endpoint, self._unsubscribe, methods=['POST'])
            self._router.add_api_route(request_endpoint, self._request, methods=['POST'])
        
        self._endpoint.include_router(self._router)

        return self._endpoint
    
    def terminate(self):
        #self._local_node_database.close()
        pass
    
    async def _dispatcher(self, req: Request, bgt: BackgroundTasks) -> Response:
        body = str(await req.body())

        if '<CheckStatusRequest' in body:
            return await self._status(req, bgt)
        elif '<SubscriptionRequest' in body:
            return await self._subscribe(req, bgt)
        elif '<TerminateSubscriptionRequest' in body:
            return await self._unsubscribe(req, bgt)
        elif '<SituationExchangeRequest' in body:
            return await self._request(req, bgt)
        else:
            return Response(status_code=400)

    async def _status(self, req: Request, bgt: BackgroundTasks) -> Response:
        xml = await req.body()
            
        """if self._datalog is not None:
            Datalog.create(self._datalog, xml, {
                'method': req.method,
                'endpoint': str(req.url),
                'headers': dict(req.headers)
            }, self._service_participant_ref, 'IN', 'CheckStatusRequest', 'Request')
        
        request = xml2siri_request(xml)"""

        # run callback method for status
        if self._on_status is not None:
            bgt.add_task(self._on_status)

        # simply respond with current status
        """response = CheckStatusResponse(self._service_startup_time)

        if self._datalog is not None:
            Datalog.create(self._datalog, response.xml(), {
                'method': req.method,
                'endpoint': str(req.url),
                'headers': dict(req.headers)
            }, self._service_participant_ref, 'IN', 'CheckStatusRequest', 'Response')"""

        #return Response(content=response.xml(), media_type='application/xml')
        return Response(content=None, media_type='application/xml')

    async def _subscribe(self, req: Request, bgt: BackgroundTasks) -> Response:
        xml = await req.body()
            
        if self._datalog is not None:
            Datalog.create(self._datalog, xml, {
                'method': req.method,
                'endpoint': str(req.url),
                'headers': dict(req.headers)
            }, self._service_participant_ref, 'IN', 'SituationExchangeSubscriptionRequest', 'Request')
        
        """request = xml2siri_request(xml)

        # add subscription parameters to subscription index
        subscription_id = sirixml_get_value(request, 'Siri.SubscriptionRequest.SituationExchangeSubscriptionRequest.SubscriptionIdentifier')
        subscription_termination = sirixml_get_value(request, 'Siri.SubscriptionRequest.SituationExchangeSubscriptionRequest.InitialTerminationTime')

        subscription = Subscription.create(
            subscription_id,
            None,
            None,
            None,
            sirixml_get_value(request, 'Siri.SubscriptionRequest.RequestorRef'),
            subscription_termination
        )"""
            
        try:
            """result = self._local_node_database.add_subscription(subscription_id, subscription)

            # respond with SubscriptionResponse OK
            response = SubscriptionResponse(self._participant_ref, self._service_startup_time)

            if result == True:
                response.ok(subscription_id, subscription_termination)

                # run callback method for subscriptions
                if self._on_subscribe is not None:
                    bgt.add_task(self._on_subscribe, subscription)
            else:
                response.error(subscription_id)"""

            if self._datalog is not None:
                """Datalog.create(self._datalog, response.xml(), {
                    'method': req.method,
                    'endpoint': str(req.url),
                    'headers': dict(req.headers)
                }, self._service_participant_ref, 'IN', 'SituationExchangeSubscriptionRequest', 'Response')"""

            #return Response(content=response.xml(), media_type='application/xml')
            return Response(content=None, media_type='application/xml')
        except Exception as ex:
            # log exception
            self._logger.error(ex)

            # respond with SubscriptionResponse Error
            """response = SubscriptionResponse(self._participant_ref, self._service_startup_time)
            response.error(subscription_id)

            if self._datalog is not None:
                Datalog.create(self._datalog, response.xml(), {
                    'method': req.method,
                    'endpoint': str(req.url),
                    'headers': dict(req.headers)
                }, self._service_participant_ref, 'IN', 'SituationExchangeSubscriptionRequest', 'Response')"""

            #return Response(content=response.xml(), media_type='application/xml')
            return Response(content=None, media_type='application/xml')

    async def _unsubscribe(self, req: Request, bgt: BackgroundTasks) -> Response:
        xml = await req.body()
            
        if self._datalog is not None:
            Datalog.create(self._datalog, xml, {
                'method': req.method,
                'endpoint': str(req.url),
                'headers': dict(req.headers)
            }, self._service_participant_ref, 'IN', 'TerminateSubscriptionRequest', 'Request')
        
        """request = xml2siri_request(xml)

        subscriber_ref = sirixml_get_value(request, 'Siri.TerminateSubscriptionRequest.RequestorRef')

        # check which subscription should be deleted - currently, only all subscriptions by a certain subscriber can be deleted
        subscriptions_to_delete = list()

        for subscription_id, subscription in self._local_node_database.get_subscriptions().items():
            if subscription.subscriber == subscriber_ref:
                subscriptions_to_delete.append(subscription_id)

        response = TerminateSubscriptionResponse(self._participant_ref)
        for subscription_id in subscriptions_to_delete:
            try:
                # delete subscription from subscription stack
                result = self._local_node_database.remove_subscription(subscription_id)

                # respond with SubscriptionResponse OK or ERROR depending on result
                if result == True:
                    response.add_ok(subscriber_ref, subscription_id)

                    # run callback method for subscriptions
                    if self._on_unsubscribe is not None:
                        bgt.add_task(self._on_unsubscribe, subscription)
                else:
                    response.add_error(subscription_id)
                
            except Exception:
                # respond with SubscriptionResponse Error for this subscription
                response.add_error(subscription_id)

        if self._datalog is not None:
            Datalog.create(self._datalog, response.xml(), {
                'method': req.method,
                'endpoint': str(req.url),
                'headers': dict(req.headers)
            }, self._service_participant_ref, 'IN', 'TerminateSubscriptionRequest', 'Response')"""

        #return Response(content=response.xml(), media_type='application/xml')
        return Response(content=None, media_type='application/xml')

    async def _request(self, req: Request, bgt: BackgroundTasks) -> Response:
        xml = await req.body()
            
        if self._datalog is not None:
            Datalog.create(self._datalog, xml, {
                'method': req.method,
                'endpoint': str(req.url),
                'headers': dict(req.headers)
            }, self._service_participant_ref, 'IN', 'SituationExchangeRequest', 'Request')
        
        #request = xml2siri_request(xml)

        # run callback method for requests
        if self._on_request is not None:
            bgt.add_task(self._on_request)

        """delivery = SituationExchangeDelivery(self._service_participant_ref, None)
        for _, situation in self._local_node_database.get_situations().items():
            delivery.add_situation(situation)"""

        """if self._datalog is not None:
            Datalog.create(self._datalog, delivery.xml(), {
                'method': req.method,
                'endpoint': str(req.url),
                'headers': dict(req.headers)
            }, self._service_participant_ref, 'IN', 'SituationExchangeRequest', 'Response')"""

        #return Response(content=delivery.xml(), media_type='application/xml')
        return Response(content=None, media_type='application/xml')