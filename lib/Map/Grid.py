import geopy.distance as distance
from .Coordinate import Coordinate

class Grid():  
    """
    [Class] Grid
    A class to represent the Grid
    
    Properties:
        - origin : The origin coordinate of this grid.
        - end : The end coordinate of this grid.
        - lonDistance : x distance (in longitude)
        - latDistance : y distance (in latitude)
        - nodes : list of nodes inside this grids
        - buildings : list of buildings inside this grids
        - roads : list of roads inside this grids
    """
    
    def __init__(self,origin,latDistance,lonDistance):
        """
        [Constructor]
        Initialize an new grid.
        
        Parameter:
            - origin : [Coordinate] origin coordinate
            - latDistance : [Double] distance in latitude
            - lonDistance : [Double] distance in longitude
        """
        self.origin = origin.newCoordinateWithTranslation(0, 0)
        self.end = origin.newCoordinateWithTranslation(latDistance, lonDistance)
        self.latDistance = latDistance
        self.lonDistance = lonDistance
        self.nodes = []
        self.buildings = []
        self.roads = []
        self.buildingSettings = []
        self.defaultBuildings = None
    
    def addBuilding(self,building):
        """
        [Method] addBuilding
        Add a building to the building list
        
        Parameter:
            - building = [Building] a building inside this grid
        """
        self.buildings.append(building)
    
    def addNode(self, node):
        """
        [Method] addNodes
        Add a node to the nodes list
        
        Parameter:
            - node = [Node] a node inside this grid
        """
        self.nodes.append(node)
    
    def addRoad(self, road):
        """
        [Method] addRoads
        Add a road to the roads list
        
        Parameter:
            - road = [Road] a node inside this grid
        """
        self.roads.append(road)
    
    def remapBuilding(self):
        """
        [Method] remapBuilding
        find closest nodes inside this grid 
       
        to do : maybe even create a new nodes
        """
        for building in self.buildings:
            closest = None
            closestDistance = 1000000000000000
            for road in self.roads:
                temp = road.distanceToCoordinate(building.coordinate)
                if closestDistance > temp :
                    closestDistance = temp
                    closest = road
            building.closestRoad = closest
            closest.addBuilding(building)
            building.entryPoint = closest.getClosestCoordinate(building.coordinate)

    def addBuildingSettings(self,setting):
        if (setting["number"] == "All"):
            self.defaultBuildings = setting
        else:
            setting["number"] = int(setting["number"])
            self.buildingSettings.append(setting)
        
    def retagBuildings(self):
        #collect all buildings that have the type "yes" and "+"
        nonTaggedBuildings = []        
        for building in self.buildings:
            if building.type == "yes" or building.type == "+":
                nonTaggedBuildings.append(building)
                
        #mark the building according to the csv (the one that we have the numbers)
        for setting in self.buildingSettings:
            for i in range(0,setting["number"]):
                if (len(nonTaggedBuildings) <= 0):
                    break #break if the config have more buildings than the actual buildings count
                building = nonTaggedBuildings.pop(0) #maybe randomize later?
                building.setType(setting["type"])
            if (len(nonTaggedBuildings) <= 0):
                break #break if the config have more buildings than the actual buildings count
                
        #mark the rest of the buildings as the default buildings (the one that marked as "All" in the CSV)
        if self.defaultBuildings is not None:
            for building in nonTaggedBuildings:
                building.setType(self.defaultBuildings["type"])
        
    def __str__(self):
        """
        [Method] __str__        
        return a string that summarized the grid
        """
        temp = f"Grid\n"
        temp = temp + f"\tstarting = (lat = {self.origin.lat}, lon = {self.origin.lon})\n"
        temp = temp + f"\tend = (lat = {self.end.lat}, lon = {self.end.lon})\n"
        temp = temp + f"\tnodes = {self.nodes.__len__()}\n"
        temp = temp + f"\tbuildings = {self.buildings.__len__()}\n"
        temp = temp + f"\troads = {self.roads.__len__()}\n"
        return temp