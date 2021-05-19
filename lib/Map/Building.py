import geopy.distance as distance
from .Coordinate import Coordinate
class Building:
    """
    [Class] Map
    A class to represent the map
    
    Properties:
        - way: List of nodes that defines the shape of the building.
        - coordinate : the coordinate of the building's centroid
    """
    def __init__(self,way):
        self.way = way
        lat,lon = 0,0
        for i in range(0,way.nodes.__len__()-1):
            lat += way.nodes[i].coordinate.lat
            lon += way.nodes[i].coordinate.lon
        lat = lat/(way.nodes.__len__()-1)
        lon = lon/(way.nodes.__len__()-1)
        self.coordinate = Coordinate(lat,lon)
        #self.closestCell = None
        #self.osmId = way.osmId
        self.tags = way.tags
        
    def __str__(self):
        """
        [Method] __str__        
        return a string that summarized the road
        """
        tempstring = f"[Building]\n"
        tempstring = tempstring + f"id: {self.way.osmId}\n"
        tempstring = tempstring + f"number of nodes : {self.way.nodes.__len__()}\n"
        tempstring = tempstring + f"Tags : \n"
        for key in self.tags.keys():
            tempstring = tempstring + f"\t{key} : {self.tags[key]}\n"
        tempstring = tempstring + "\n"
        return tempstring
        return temp
    
    def getPosition(self):
            """
            [Method]getPosition
            get the latitude and longitude of the cell

            Return : (lat,lon)
            """
            return (self.lat,self.lon);