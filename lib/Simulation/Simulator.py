import csv
import random
import multiprocessing
#from atpbar import flush
from .JobClass import JobClass
from .Agent import Agent, getAgentKeys
from .Home import Home
from .Infection import Infection
from .BasicInfectionModel import BasicInfectionModel
from .StepThread import StepThread
import os
from os.path import join
from lib.Map.MovementSequence import reconstruct
import datetime
import csv
from pathlib import Path
import time

summaryFieldnames = [
    'Day',
    'Hour',
    'Minutes',
    'CurrentStep',
    'Susceptible',
    'Exposed',
    'Infectious',
    'Recovered'
]

detailsFieldnames = [
    'infectedAgentId',
    'infectedAgentProfession',
    'originAgentId',
    'originAgentProfession',
    'location',
    'lat',
    'lon',
    'nodeId',
    'exposedTimeStamp',
    'exposedDay',
    'exposedHour',
    'exposedMinutes',
    'incubationDuration',
    'infectiousTimeStamp',
    'infectiousDay',
    'infectiousHour',
    'infectiousMinutes',
    'recoveryDuration',
    'recoveredTimeStamp',
    'recoveredDay',
    'recoveredHour',
    'recoveredMinutes',
    'symptomaticTimeStamp',
    'symptomaticDay',
    'symptomaticHour',
    'symptomaticMinutes',
    'severeTimeStamp',
    'severeDay',
    'severeHour',
    'severeMinutes',
]

class Simulator:
    """
    [Class] Simulator
    The main simulator class
    
    Properties:
        - osmMap = [Map] the map used to simulate it
        - jobClasses = [array] array of jobClasses
        - agents = [array] array of agents
        - unshuffledAgents = [array] array of agents the agent is sorted based on their id 
        - stepCount = [int] current step count which represent how many simulated seconds from the beggining of the simulation
        - history = [Dictionary] of SEIR status that was staged after each step was finished
        - timeStamp = [array]  the timestamp of the history proporties
        - threadNumber = [int] how many thread this simulator allowed to create when doing pathfinding
        - lastHour = [int] last calculated hour, used to trigger pathfinding.
        - vaccinationPercentage = [float] percentage of people that got the vaccine in the simulation.
        - infectionHistory = [array] array of infection that happened in our simulation
        - reportPath = [string] path for the records
        - reportInterval = [int] how many step do we want to wait before we extract the data
        - reportCooldown = [int] the current value of report interval
        - infectionModel = [InfectionModel] the infection model
        
    Don't Access Properties:
        - returnDict = [array] (DO NOT USE) array of dictionary that was returned by the thread 
        - activitiesDict = [array] (DO NOT USE) array of dictionary that was returned by the thread 
        - queue = [array] (DO NOT USE) array of queues that was returned by the thread 
        - threads = [array] (DO NOT USE) array of StepThreads that was returned by the thread 
        
    """
    def __init__(self, osmMap, jobCSVPath, agentNum = 1000, threadNumber = 4, infectedAgent = 5, vaccinationPercentage = 0.0, reportPath="report", reportInterval=10, infectionModel = None):
        """
        [Constructor]
        The constructor for Simulator class

        Properties:
            - osmMap = [Map] the map used to simulate it
            - jobCSVPath = [string] path to the job.csv
            - agentNum = [int] number of agent that will be generated
            - threadNumber = [int] how many thread this simulator allowed to create when doing pathfinding
            - infectedAgent = [int] how many agents are infected at the beginning of our simulation
            - vaccinationPercentage = [float] percentage of people that got the vaccine in the simulation.
            - reportPath = [string] path for the records
            - reportInterval = [int] how many step do we want to wait before we extract the data
            - infectionModel = [InfectionModel] the infection model
        """
        self.jobClasses = []
        self.osmMap = osmMap
        with open(jobCSVPath) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            keys = []
            for row in csv_reader:
                data = {}
                if len(keys) == 0:
                    keys = row
                elif len(row) != 0:         
                    #print(row)
                    for i in range(0,len(keys)):
                        data[keys[i]]=row[i]
                    temp =JobClass(data)
                    temp.buildings = osmMap.buildingsDict.get(temp.place)
                    self.jobClasses.append(temp)
            print(f'Processed {line_count} lines.')
        self.agents = []
        self.unshuffledAgents = []
        #self.stepCount = 3600*8
        self.stepCount = 0
        self.history = {}
        self.history ["Susceptible"] = []
        self.history ["Exposed"] = []
        self.history ["Infectious"] = []
        self.history ["Recovered"] = []
        self.timeStamp = []
        self.threadNumber = threadNumber
        self.returnDict = None
        self.activitiesDict = None
        self.lastHour = -1
        self.vaccinationPercentage = vaccinationPercentage
        self.generateAgents(agentNum, infectedAgent)
        self.splitAgentsForThreading()
        self.infectionHistory = []
        self.queue = []
        self.threads = []
        self.reportPath = self.createReportDir(reportPath)
        self.reportInterval = reportInterval
        self.reportCooldown = reportInterval
        if infectionModel is None:
            self.infectionModel = BasicInfectionModel(self,self.osmMap)
        else:
            self.infectionModel = infectionModel
           
    def createReportDir(self, reportPath):
        """
        [Method] createReportdir
        Method to create the report directory

        Properties:
            - reportPath = [string] path for the records
        """
        current_time = datetime.datetime.now()
        new_dir = current_time.strftime("%Y%m%d-%H%M")
        path = os.path.join(reportPath, new_dir)
        Path(path).mkdir(parents=True, exist_ok=True)

        return path

    def generateAgents(self, count, infectedAgent = 5):
        """
        [Method] generateAgents
        Method to create the report directory

        Properties:
            - count = [int] number of agent that will be generated
            - infectedAgent = [int] how many agents are infected at the beginning of our simulation
        """
        total = 0
        self.osmMap
        houses = []
        houses.extend(self.osmMap.buildingsDict['residential'])
        houses.extend(self.osmMap.buildingsDict['house'])
        houses.extend(self.osmMap.buildingsDict['apartments'])
        #last line of defense, if somehow the building doesn't have node, remove it
        agentId = 0
        for x in houses:
            if x.node is None:
                houses.remove(x)
                
        for x in self.jobClasses:
            total += x.populationProportion
        for x in self.jobClasses:
            temp = int(x.populationProportion*count/float(total))
            ageRange = x.maxAge - x.minAge
            for i in range(0,temp):             
                agent = Agent(agentId, self.osmMap,x.minAge+random.randint(0,ageRange),x)
                agentId +=1         
                self.agents.append(agent)
                self.unshuffledAgents.append(agent)
        for x in range(0,count- len(self.agents)):
            x = self.jobClasses[0]
            temp = int(x.populationProportion*count/float(total))
            ageRange = x.maxAge - x.minAge
            agent = Agent(agentId, self.osmMap,x.minAge+random.randint(0,ageRange),x)
            agentId +=1         
            self.agents.append(agent)
            self.unshuffledAgents.append(agent)
            
        random.shuffle(self.agents) #shuffle so that we can randomly assign vaccine 
        
        
        for i in range(0,int(self.vaccinationPercentage*len(self.agents))):
            self.agents[i].setVaccinated()

        random.shuffle(self.agents) #shuffle so that we can randomly assign a household 
        
        housePop = 0
        building = None
        home = None
        houseId = 0
        for agent in self.agents:
            #generate Home
            if housePop ==0:
                housePop = random.randint(1,3)
                building = random.choice(houses)
                if (building.type == "house"):
                    houses.remove(building)
                home = Home(building,houseId)
                houseId += 1
                if "home" not in building.content.keys():                 
                    building.content["home"] = []   
                building.content["home"].append(home)
            if "agent" not in building.content.keys():                    
                building.content["agent"] = []   
            building.content["agent"].append(agent)      
            agent.setHome(home)
            home.addOccupant(agent)
            housePop -= 1
            building.node.addAgent(agent)
            
            
        random.shuffle(self.agents) #shuffle so that we can randomly assign people who got initial infection 
        for i in range (0, infectedAgent):
            self.agents[i].infection = Infection(self.agents[i],self.agents[i],self.stepCount,dormant = 0,recovery = random.randint(72,14*24) *3600,location ="Initial")
            
        
    def splitAgentsForThreading(self):
        """
        [Method] splitAgentsForThreading
        Method to split agents into several array for threading purposes
        
        TODO = change name to mark it as private
        """
        chunksize = int(len(self.agents)/ self.threadNumber)
        self.agentChunks = [self.agents[chunksize*i:chunksize*(i+1)] for i in range(int(len(self.agents)/chunksize) + 1)]
        if(len(self.agentChunks[-1]) < chunksize):
            self.agentChunks[0].extend(self.agentChunks[-1])
            self.agentChunks.remove(self.agentChunks[-1])
            
            

    def step(self,stepSize = 3600):
        """
        [Method] step
        The step function. there are 5 main step:
            - pathfinding (triggered when the hour changes)
            - move the agents
            - check infection of the agents
            - finalize the infection 
            - summarize
        
        Parameter: 
            - stepSize = how long we wanted to step forward in seconds (60 means 60 seconds)
        """
        day, hour, minutes = self.currentHour()
        week = int(self.stepCount/ (7*24*3600))
        print("Week = {} Day = {} Current Time = {:02d}:{:02d}".format(week,day,hour,minutes))
        if (self.lastHour != hour):
            self.lastHour = hour
            ###############################################################################################
            # Generate Threads
            # Do not refactor into other function
            # ref : https://stackoverflow.com/questions/49391569/python3-process-object-never-joins
            ###############################################################################################
            threads = []
            i = 1
            manager = multiprocessing.Manager()
            returnDicts = [] #if not working, probably this must be allocated locally
            activitiesDicts = [] #if not working, probably this must be allocated locally
            for chunkOfAgent in self.agentChunks:
                returnDict = manager.dict()
                activitiesDict = manager.dict()
                returnDicts.append(returnDict)
                activitiesDicts.append(activitiesDict)
                thread = StepThread(f"Thread {i}",chunkOfAgent,self.stepCount,returnDict,activitiesDict)
                threads.append(thread)
                i += 1  
            ###############################################################################################
            # Generate Threads end
            ###############################################################################################

            
            for thread in threads:
                thread.daemon = True
                thread.setStateToStep(stepSize)
                thread.start()
            time.sleep(30) # sleep for 20 second to help the threads starts their work
            # wait for all thread to finish running
            for i in range(0,len(threads)):
                threads[i].join()
                    
            for returnDict in returnDicts:
                for key in returnDict.keys():
                    self.unshuffledAgents[int(key)].activeSequence = reconstruct(self.osmMap.roadNodesDict, returnDict[key][0], returnDict[key][1])
            for activitiesDict in activitiesDicts:
                for key in activitiesDict.keys():
                    self.unshuffledAgents[int(key)].activities = activitiesDict[key]
            #flush()
            self.lastHour = hour
            
            self.threads = []
                
        #print("Finished checking activity, proceeding to move agents")
        for x in self.agents:
            x.step(day,hour,stepSize)
        #print("Finished moving agents, proceeding to check for infection")
        for agent in self.agents:
            self.infectionModel.infect(agent,stepSize,self.stepCount)
            #x.checkInfection(self.stepCount,stepSize)
        #print("Finished infection checking, proceeding to finalize the infection")
        for x in self.agents:
            x.finalize(self.stepCount,stepSize)
        print("Finished finalizing the infection")
        self.stepCount += stepSize
        self.summarize()
        self.printInfectionLocation()

        if self.reportCooldown < 1:
            print("Extracting data")
            self.extract()
            self.reportCooldown = self.reportInterval
        self.reportCooldown -= 1
        
    def currentHour(self):
        """
        [Method] currentHour
        method to return the current tiem
        
        return: 
            - day = [int] current simulated day (0-6) 0 = Monday, 6 = Sunday
            - hour = [int] current simulated hour
            - minutes = [int] current simulated minutes
        """
        hour = int(self.stepCount / 3600)% 24
        day = int(self.stepCount /(24*3600)) % 7
        minutes = int(self.stepCount/60)%60
        return day,hour, minutes
    
    def printInfectionLocation(self):
        """
        [Method] printInfectionLocation
        method to print where the infection happened to command line 
        """
        summary = {}
        for agent in self.agents:
            if agent.infection is not None:
                if agent.infection.location not in summary: 
                    summary[agent.infection.location]=0
                summary[agent.infection.location] += 1

        print("\nknown infection location")
        for key in summary.keys():
            print(f"{key} = {summary[key]}")
        print("\n")
    
    
    
    def summarize(self):
        """
        [Method] summarize
        method to do staged data collection for current simulated time
        """
        result = {}
        day, hour,minutes = self.currentHour()
        result["CurrentStep"] = self.stepCount
        result["Day"] = day
        result["Hour"] = hour
        result["Minutes"] = minutes
        result["Susceptible"] = 0
        result["Infectious"] = 0
        result["Exposed"] = 0
        result["Recovered"] = 0
        for x in self.agents:
            result[x.infectionStatus] += 1
        for x in result.keys():
            if x in self.history.keys():
                self.history[x].append(result[x])
        self.timeStamp.append(self.stepCount/3600)
        self.infectionHistory.append(result)
        
        return result
    
    def killStepThreads(self):
        """
        [Method] killStepThreads
        method to force terminate the StepThreads
        """
        for thread in self.threads:
            thread.terminate()
            
    def extract(self):
        """
        [Method] extract
        method to write the simulation result to files
        """
        # This function always open and close the files 
        # to guarantee that they are being rewriten from scratch

        # TODO: Remember where in the "infection history" we stopped saving the log, and continue later.
        summaryFilePath = join(self.reportPath,'infection_summary.csv')
        with open(summaryFilePath, 'w', newline='') as summaryFile:
            writer = csv.DictWriter(summaryFile, fieldnames=summaryFieldnames)
            writer.writeheader()
            for x in self.infectionHistory:
                writer.writerow(x)
            summaryFile.close()
        
        detailsFilePath = join(self.reportPath,'infection_details.csv')
        with open(detailsFilePath, 'w', newline='') as detailsFile:
            writer = csv.DictWriter(detailsFile, fieldnames=detailsFieldnames)
            writer.writeheader()
            for i in self.agents:
                if (i.infection is not None):
                    summary = i.infection.summarize()
                    writer.writerow(summary)
            detailsFile.close()
         
        # TODO Issue: Consider if we want to keep the history of the agents in the future (maybe this is too much data)
 
        agentsFilePath = join(self.reportPath,'agents.csv')
        with open(agentsFilePath, 'w', newline='') as agentsFile:
            agentFieldnames = getAgentKeys()
            writer = csv.DictWriter(agentsFile, fieldnames=agentFieldnames)
            writer.writeheader()
            for x in self.agents:
                writer.writerow(x.extract())
            agentsFile.close()
         
                
       
            
