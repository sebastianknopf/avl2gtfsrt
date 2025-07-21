from itcs435.nominal.baseadapter import BaseNominalAdapter
from itcs435.nominal.otp.otpclient import OtpClient

class OtpAdapter(BaseNominalAdapter):

    def cache_trip_candidates_by_position(self, latitude, longitude):
        raise NotImplementedError()