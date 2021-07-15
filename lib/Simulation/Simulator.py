import csv
import random
import multiprocessing
from atpbar import flush
from .JobClass import JobClass
from .Agent import Agent, getAgentKeys
from .Home import Home
from .Infection import Infection
from .StepThread import StepThread
import os
from os.path import join
from lib.Map.MovementSequence import reconstruct
import datetime
import csv
class Simulator:
    def __init__(self,jobCSVPath,osmMap,agentNum = 1000,threadNumber = 4, infectedAgent = 0.02):
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
                    print(row)
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
        self.generateAgents(agentNum, infectedAgent)
        self.splitAgentsForThreading()
        self.infectionHistory = []
        
    def generateAgents(self, count, infectedAgent = 0.02):
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
        for i in range (0, int(len(self.agents)*infectedAgent)):
            self.agents[i].infection = Infection(self.agents[i],self.agents[i],self.stepCount,dormant = 0,recovery = random.randint(72,14*24) *3600,location ="Initial")
            
        
    def splitAgentsForThreading(self):
        chunksize = int(len(self.agents)/ self.threadNumber)
        self.agentChunks = [self.agents[chunksize*i:chunksize*(i+1)] for i in range(int(len(self.agents)/chunksize) + 1)]
        if(len(self.agentChunks[-1]) < chunksize):
            self.agentChunks[0].extend(self.agentChunks[-1])
            self.agentChunks.remove(self.agentChunks[-1])
            
    def generateThread(self):
        self.queues = []
        self.threads = []
        i = 1
        manager = multiprocessing.Manager()
        self.returnDict = []
        self.activitiesDict = []
        for chunkOfAgent in self.agentChunks:
            returnDict = manager.dict()
            activitiesDict = manager.dict()
            self.returnDict.append(returnDict)
            self.activitiesDict.append(activitiesDict)
            thread = StepThread(f"Thread {i}",chunkOfAgent,self.stepCount,returnDict,activitiesDict)
            self.threads.append(thread)
            i += 1  
            

    def step(self,steps = 3600):
        day, hour, minutes = self.currentHour()
        print(f"Current Time = {hour}:{(self.stepCount%3600)/60}")
        if (self.lastHour != hour):
            
            self.generateThread()
            for thread in self.threads:
                thread.setStateToStep(steps)
                thread.start()
            #wait for all thread to finish running
            for thread in self.threads:
                thread.join()
            #reconstruct movement sequence
            for returnDict in self.returnDict:
                for key in returnDict.keys():
                    self.unshuffledAgents[int(key)].activeSequence = reconstruct(self.osmMap.roadNodesDict, returnDict[key][0], returnDict[key][1])
            for activitiesDict in self.activitiesDict:
                for key in activitiesDict.keys():
                    self.unshuffledAgents[int(key)].activities = activitiesDict[key]
            flush()
            self.lastHour = hour
        
        #print("Finished checking activity, proceeding to move agents")
        for x in self.agents:
            x.step(day,hour,steps)
        #print("Finished moving agents, proceeding to check for infection")
        for x in self.agents:
            x.checkInfection(self.stepCount,steps)
        #print("Finished infection checking, proceeding to finalize the infection")
        for x in self.agents:
            x.finalize(self.stepCount,steps)
        print("Finished finalizing the infection")
        self.stepCount += steps
        self.summarize()
        self.printInfectionLocation()
        
    def currentHour(self):
        hour = int(self.stepCount / 3600)% 24
        day = int(hour /24) % 7
        minutes = int(self.stepCount/60)%60
        return day,hour, minutes
    
    def printInfectionLocation(self):
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

            
    def extract(self):
        current_time = datetime.datetime.now()
        path = current_time.strftime("%Y%m%d-%H%M")
        os.mkdir(path)
        

        with open(join(path,'infection_summary.csv'), 'w', newline='') as csvfile:
            fieldnames = ['Day','Hour','Minutes','CurrentStep','Susceptible','Exposed','Infectious','Recovered']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for x in self.infectionHistory:
                writer.writerow(x)
                
        infectionDetails = []        
        for i in self.agents:
            if (i.infection is not None):
                infectionDetails.append(i.infection.summarize())
         
        with open(join(path,'infection_details.csv'), 'w', newline='') as csvfile:
            fieldnames = ['infectedAgentId','infectedAgentProfession','originAgentId','originAgentProfession','location','lat','lon','nodeId'
,"exposedTimeStamp","exposedDay","exposedHour","exposedMinutes","incubationDuration"                   
,"infectiousTimeStamp","infectiousDay","infectiousHour","infectiousMinutes","recoveryDuration"                   
,"recoveredTimeStamp","recoveredDay","recoveredHour","recoveredMinutes"            
,"symptomaticTimeStamp","symptomaticDay","symptomaticHour","symptomaticMinutes"            
,"severeTimeStamp","severeDay","severeHour","severeMinutes"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for x in infectionDetails:
                writer.writerow(x)
         
        with open(join(path,'agents.csv'), 'w', newline='') as csvfile:
            fieldnames = getAgentKeys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for x in self.agents:
                writer.writerow(x.extract())
         
                
       
            