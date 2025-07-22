from itcs435.nominal.baseadapter import BaseNominalAdapter
from itcs435.nominal.otp.otpclient import OtpClient

class OtpAdapter(BaseNominalAdapter):

    def get_trip_candidates(self, latitude, longitude):
        raise NotImplementedError()