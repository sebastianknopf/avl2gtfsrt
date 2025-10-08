from avl2gtfsrt.vdv.vdv435 import *

gnss_physical_position_data_structure = GnssPhysicalPositionDataStructure(
    PublisherId='XMLGEN',
    GnssPhysicalPosition=GnssPhysicalPosition(
        WGS84PhysicalPosition=WGS84PhysicalPosition(
            Latitude=48.0080445,
            Longitude=09.334598,
        )    
    )
)

print(gnss_physical_position_data_structure.xml())