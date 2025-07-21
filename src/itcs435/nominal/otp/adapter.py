from itcs435.nominal.baseadapter import BaseNominalAdapter
from itcs435.nominal.otp.otpclient import OtpClient

class OtpAdapter(BaseNominalAdapter):

    def load_nominal_trips_by_position(self, latitude, longitude):
        raise NotImplementedError()