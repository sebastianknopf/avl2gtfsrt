import logging

from avl2gtfsrt.common.env import is_debug
from avl2gtfsrt.nominal.baseadapter import BaseAdapter


class NominalDataClient:

    def __init__(self, adapter_type: str, adapter_config: dict):
        self._adapter_type = adapter_type
        self._adapter_config = adapter_config

    def get_trip_candidates(self, latitude: float, longitude: float) -> list[dict]:
        adapter: BaseAdapter = self._get_configured_adapter()

        try:
            logging.info(f"{self.__class__.__name__}: Loading trip candidates with adapter of type {self._adapter_type} ...")
            result: dict = adapter.get_trip_candidates(latitude, longitude)

            return result
        
        except Exception as ex:
            if is_debug():
                logging.exception(ex)
            else:
                logging.error(str(ex))

    def _get_configured_adapter(self) -> BaseAdapter:
        adapter: BaseAdapter = None
        
        if self._adapter_type == 'otp':
            from avl2gtfsrt.nominal.otp.adapter import OtpAdapter
            adapter = OtpAdapter(self._adapter_config.get('endpoint', None))
        else:
            raise ValueError(f"Unknown nominal adapter type {self._adapter_type}!")
        
        return adapter
        
        
