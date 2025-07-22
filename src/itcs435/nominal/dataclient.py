import logging

from itcs435.common.env import is_set
from itcs435.nominal.baseadapter import BaseNominalAdapter


class NominalDataClient:

    def __init__(self, adapter_type: str):
        self._adapter_type = adapter_type

    def get_trip_candidates(self, latitude: float, longitude: float) -> list[dict]:
        adapter: BaseNominalAdapter = self._get_configured_adapter()

        try:
            logging.info(f"Running nominal adapter {self._adapter_type} ...")
            adapter.get_trip_candidates(latitude, longitude)
        except Exception as ex:
            if is_set('ITCS435_DEBUG'):
                logging.exception(ex)
            else:
                logging.error(str(ex))

    def _get_configured_adapter(self) -> BaseNominalAdapter:
        adapter: BaseNominalAdapter = None
        
        if self._adapter_type == 'otp':
            from itcs435.nominal.otp.adapter import OtpAdapter
            adapter = OtpAdapter()
        else:
            raise ValueError(f"Unknown nominal adapter type {self._adapter_type}!")
        
        return adapter
        
        
