# myTeam.py
# ---------------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
# 
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).


# myTeam.py
# ---------------
# Licensing Information: Please do not distribute or publish solutions to this
# project. You are free to use and extend these projects for educational
# purposes. The Pacman AI projects were developed at UC Berkeley, primarily by
# John DeNero (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# For more info, see http://inst.eecs.berkeley.edu/~cs188/sp09/pacman.html

from typing import List, Tuple

from captureAgents import CaptureAgent
import distanceCalculator
import random, time, util, sys, os
from capture import GameState, noisyDistance
from game import Directions, Actions, AgentState, Agent
from util import nearestPoint
import sys,os

# the folder of current file.
BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

from lib_piglet.utils.pddl_solver import pddl_solver
from lib_piglet.domains.pddl import pddl_state
from lib_piglet.utils.pddl_parser import Action

CLOSE_DISTANCE = 4
MEDIUM_DISTANCE = 15
LONG_DISTANCE = 25


#################
# Team creation #
#################


def createTeam(firstIndex, secondIndex, isRed,
                             first = 'MixedAgent', second = 'MixedAgent'):
    """
    This function should return a list of two agents that will form the
    team, initialized using firstIndex and secondIndex as their agent
    index numbers.  isRed is True if the red team is being created, and
    will be False if the blue team is being created.

    As a potentially helpful development aid, this function can take
    additional string-valued keyword arguments ("first" and "second" are
    such arguments in the case of this function), which will come from
    the --redOpts and --blueOpts command-line arguments to capture.py.
    For the nightly contest, however, your team will be created without
    any extra arguments, so you should make sure that the default
    behavior is what you want for the nightly contest.
    """
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


##########
# Agents #
##########                                       

class MixedAgent(CaptureAgent):
    """
    This is an agent that use pddl to guide the high level actions of Pacman
    """
    # Default weights for q learning, if no QLWeights.txt find, we use the following weights.
    # You should add your weights for new low level planner here as well.
    # weights are defined as class attribute here, so taht agents share same weights.
    QLWeights = {
            "offensiveWeights":{'closest-food': -1, 
                                        'bias': 1, 
                                        '#-of-ghosts-1-step-away': -100, 
                                        'successorScore': 100, 
                                        'chance-return-food': 10,
                                        },
            "defensiveWeights": {'numInvaders': -1000, 'onDefense': 100,'teamDistance':2 ,'invaderDistance': -10, 'stop': -100, 'reverse': -2},
            "escapeWeights": {'onDefense': 1000, 'enemyDistance': 30, 'stop': -100, 'distanceToHome': -20}
        }
    QLWeightsFile = BASE_FOLDER+'/QLWeightsMyTeam.txt'

    # Also can use class variable to exchange information between agents.
    CURRENT_ACTION = {}
    sharedTargets = {}
    sharedModes = {}


    def registerInitialState(self, gameState: GameState):
        self.pddl_solver = pddl_solver(BASE_FOLDER+'/myTeam.pddl')
        self.highLevelPlan: List[Tuple[Action,pddl_state]] = None # Plan is a list Action and pddl_state
        self.currentNegativeGoalStates = []
        self.currentPositiveGoalStates = []
        self.currentActionIndex = 0 # index of action in self.highLevelPlan should be execute next

        self.startPosition = gameState.getAgentPosition(self.index) # the start location of the agent
        CaptureAgent.registerInitialState(self, gameState)

        self.lowLevelPlan: List[Tuple[str,Tuple]] = []
        self.lowLevelActionIndex = 0
        self.previousDefendingFood = self.getFoodYouAreDefending(gameState).asList()
        self.lastEatenFood = None
        self.currentLowLevelTarget = None
        self.currentLowLevelMode = None
        self.currentHighLevelAction = None
        self.lastObservedPosition = self.startPosition
        self.searchBudgetExhausted = False
        self.maxLowLevelExpansions = 600
        self.recentPositions = []
        self.stuckRecoverySteps = 0
        MixedAgent.sharedTargets[self.index] = self.startPosition
        MixedAgent.sharedModes[self.index] = "patrol"

        # REMEMBER TRUN TRAINNING TO FALSE when submit to contest server.
        self.trainning = False # trainning mode to true will keep update weights and generate random movements by prob.
        self.epsilon = 0.1 #default exploration prob, change to take a random step
        self.alpha = 0.02 #default learning rate
        self.discountRate = 0.9 # default discount rate on successor state q value when update
        
        # Use a dictionary to save information about current agent.
        MixedAgent.CURRENT_ACTION[self.index]={}
        """
        Open weights file if it exists, otherwise start with empty weights.
        NEEDS TO BE CHANGED BEFORE SUBMISSION

        """
        if os.path.exists(MixedAgent.QLWeightsFile):
            with open(MixedAgent.QLWeightsFile, "r") as file:
                MixedAgent.QLWeights = eval(file.read())
            print("Load QLWeights:",MixedAgent.QLWeights )
        
    
    def final(self, gameState : GameState):
        """
        This function write weights into files after the game is over. 
        You may want to comment (disallow) this function when submit to contest server.
        """
        if self.trainning:
            print("Write QLWeights:", MixedAgent.QLWeights)
            file = open(MixedAgent.QLWeightsFile, 'w')
            file.write(str(MixedAgent.QLWeights))
            file.close()
    

    def chooseAction(self, gameState: GameState):
        """
        This is the action entry point for the agent.
        In the game, this function is called when its current agent's turn to move.

        We first pick a high-level action.
        Then generate low-level action ("North", "South", "East", "West", "Stop") to achieve the high-level action.
        """

        #-------------High Level Plan Section-------------------
        # Get high level action from a pddl plan.
        self.updateDefenceMemory(gameState)
        self.updateMovementMemory(gameState)

        # Collect objects and init states from gameState
        objects, initState = self.get_pddl_state(gameState)
        positiveGoal, negtiveGoal = self.getGoals(objects,initState)

        # Check if we can stick to current plan 
        if not self.stateSatisfyCurrentPlan(initState, positiveGoal, negtiveGoal):
            # Cannot stick to current plan, prepare goals and replan
            print("Agnet:",self.index,"compute plan:")
            print("\tOBJ:"+str(objects),"\tINIT:"+str(initState), "\tPOSITIVE_GOAL:"+str(positiveGoal), "\tNEGTIVE_GOAL:"+str(negtiveGoal),sep="\n")
            self.highLevelPlan: List[Tuple[Action,pddl_state]] = self.getHighLevelPlan(objects, initState,positiveGoal, negtiveGoal) # Plan is a list Action and pddl_state
            self.currentActionIndex = 0
            self.lowLevelPlan = [] # reset low level plan
            self.currentNegativeGoalStates = negtiveGoal
            self.currentPositiveGoalStates = positiveGoal
            print("\tPLAN:",self.highLevelPlan)
        if self.highLevelPlan is None or len(self.highLevelPlan)==0:
            fallbackPlan = self.getFallbackPlan(gameState)
            return fallbackPlan[0][0]
        
        # Get next action from the plan
        highLevelAction = self.highLevelPlan[self.currentActionIndex][0].name
        MixedAgent.CURRENT_ACTION[self.index] = highLevelAction
        print("Agent:", self.index, highLevelAction)

        #-------------Low Level Plan Section-------------------
        # Get the low level plan using Q learning, and return a low level action at last.
        # A low level action is defined in Directions, whihc include {"North", "South", "East", "West", "Stop"}

        desiredLowLevelMode = self.getEffectiveLowLevelMode(gameState, highLevelAction)
        if not self.posSatisfyLowLevelPlan(gameState, desiredLowLevelMode, highLevelAction):
            self.lowLevelPlan = self.getLowLevelPlanHS(gameState, highLevelAction) #Generate low level plan with heuristic search
            self.lowLevelActionIndex = 0
        lowLevelAction = self.lowLevelPlan[self.lowLevelActionIndex][0]
        self.lowLevelActionIndex+=1
        print("\tAgent:", self.index,lowLevelAction)
        return lowLevelAction

    #------------------------------- PDDL and High-Level Action Functions ------------------------------- 
    
    
    def getHighLevelPlan(self, objects, initState, positiveGoal, negtiveGoal) -> List[Tuple[Action,pddl_state]]:
        """
        This function prepare the pddl problem, solve it and return pddl plan
        """
        # Prepare pddl problem
        self.pddl_solver.parser_.reset_problem()
        self.pddl_solver.parser_.set_objects(objects)
        self.pddl_solver.parser_.set_state(initState)
        self.pddl_solver.parser_.set_negative_goals(negtiveGoal)
        self.pddl_solver.parser_.set_positive_goals(positiveGoal)
        
        # Solve the problem and return the plan
        return self.pddl_solver.solve()

    def get_pddl_state(self,gameState:GameState) -> Tuple[List[Tuple],List[Tuple]]:
        """
        This function collects pddl :objects and :init states from simulator gameState.
        """
        # Collect objects and states from the gameState

        states = []
        objects = []


        # Collect available foods on the map
        foodLeft = self.getFood(gameState).asList()
        if len(foodLeft) > 0:
            states.append(("food_available",))
        myPos = gameState.getAgentPosition(self.index)
        myObj = "a{}".format(self.index)
        cloestFoodDist = self.closestFood(myPos,self.getFood(gameState), gameState.getWalls())
        if cloestFoodDist != None and cloestFoodDist <=CLOSE_DISTANCE:
            states.append(("near_food",myObj))

        # Collect capsule states
        capsules = self.getCapsules(gameState)
        if len(capsules) > 0 :
            states.append(("capsule_available",))
        for cap in capsules:
            if self.getMazeDistance(cap,myPos) <=CLOSE_DISTANCE:
                states.append(("near_capsule",myObj))
                break
        
        # Collect winning states
        currentScore = gameState.data.score
        if gameState.isOnRedTeam(self.index):
            if currentScore > 0:
                states.append(("winning",))
            if currentScore> 3:
                states.append(("winning_gt3",))
            if currentScore> 5:
                states.append(("winning_gt5",))
            if currentScore> 10:
                states.append(("winning_gt10",))
            if currentScore> 20:
                states.append(("winning_gt20",))
        else:
            if currentScore < 0:
                states.append(("winning",))
            if currentScore < -3:
                states.append(("winning_gt3",))
            if currentScore < -5:
                states.append(("winning_gt5",))
            if currentScore < -10:
                states.append(("winning_gt10",))
            if currentScore < -20:
                states.append(("winning_gt20",))

        # Collect team agents states
        agents : List[Tuple[int,AgentState]] = [(i,gameState.getAgentState(i)) for i in self.getTeam(gameState)]
        for agent_index, agent_state in agents :
            agent_object = "a{}".format(agent_index)
            agent_type = "current_agent" if agent_index == self.index else "ally"
            objects += [(agent_object, agent_type)]

            if agent_index != self.index and self.getMazeDistance(gameState.getAgentPosition(self.index), gameState.getAgentPosition(agent_index)) <= CLOSE_DISTANCE:
                states.append(("near_ally",))
            
            if agent_state.scaredTimer>0:
                states.append(("is_scared",agent_object))

            if agent_state.numCarrying>0:
                states.append(("food_in_backpack",agent_object))
                if agent_state.numCarrying >=20 :
                    states.append(("20_food_in_backpack",agent_object))
                if agent_state.numCarrying >=10 :
                    states.append(("10_food_in_backpack",agent_object))
                if agent_state.numCarrying >=5 :
                    states.append(("5_food_in_backpack",agent_object))
                if agent_state.numCarrying >=3 :
                    states.append(("3_food_in_backpack",agent_object))
                
            if agent_state.isPacman:
                states.append(("is_pacman",agent_object))
            
            

        # Collect enemy agents states
        enemies : List[Tuple[int,AgentState]] = [(i,gameState.getAgentState(i)) for i in self.getOpponents(gameState)]
        noisyDistance = gameState.getAgentDistances()
        typeIndex = 1
        for enemy_index, enemy_state in enemies:
            enemy_position = enemy_state.getPosition()
            enemy_object = "e{}".format(enemy_index)
            objects += [(enemy_object, "enemy{}".format(typeIndex))]

            if enemy_state.scaredTimer>0:
                states.append(("is_scared",enemy_object))

            if enemy_position != None:
                for agent_index, agent_state in agents:
                    if self.getMazeDistance(agent_state.getPosition(), enemy_position) <= CLOSE_DISTANCE:
                        states.append(("enemy_around",enemy_object, "a{}".format(agent_index)))
            else:
                if noisyDistance[enemy_index] >=LONG_DISTANCE :
                    states.append(("enemy_long_distance",enemy_object, "a{}".format(self.index)))
                elif noisyDistance[enemy_index] >=MEDIUM_DISTANCE :
                    states.append(("enemy_medium_distance",enemy_object, "a{}".format(self.index)))
                else:
                    states.append(("enemy_short_distance",enemy_object, "a{}".format(self.index)))                                                                                                                                                                                                 


            if enemy_state.isPacman:
                states.append(("is_pacman",enemy_object))
            typeIndex += 1
            
        return objects, states
    
    def stateSatisfyCurrentPlan(self, init_state: List[Tuple],positiveGoal, negtiveGoal):
        if self.highLevelPlan is None or len(self.highLevelPlan) == 0:
            # No plan, need a new plan
            self.currentNegativeGoalStates = negtiveGoal
            self.currentPositiveGoalStates = positiveGoal
            return False
        
        if positiveGoal != self.currentPositiveGoalStates or negtiveGoal != self.currentNegativeGoalStates:
            return False
        
        if self.pddl_solver.matchEffect(init_state, self.highLevelPlan[self.currentActionIndex][0] ):
            # The current state match the effect of current action, current action action done, move to next action
            if self.currentActionIndex < len(self.highLevelPlan) -1 and self.pddl_solver.satisfyPrecondition(init_state, self.highLevelPlan[self.currentActionIndex+1][0]):
                # Current action finished and next action is applicable
                self.currentActionIndex += 1
                self.lowLevelPlan = [] # reset low level plan
                return True
            else:
                # Current action finished, next action is not applicable or finish last action in the plan
                return False

        if self.pddl_solver.satisfyPrecondition(init_state, self.highLevelPlan[self.currentActionIndex][0]):
            # Current action precondition satisfied, continue executing current action of the plan
            return True
        
        # Current action precondition not satisfied anymore, need new plan
        return False
    
    def getGoals(self, objects: List[Tuple], initState: List[Tuple]):
        # Check a list of goal functions from high priority to low priority if the goal is applicable
        # Return the pddl goal states for selected goal function
        if (("winning_gt10",) in initState):
            return self.goalDefWinning(objects, initState)
        else:
            return self.goalScoring(objects, initState)

    def goalScoring(self,objects: List[Tuple], initState: List[Tuple]):
        # If we are not winning more than 5 points,
        # we invate enemy land and eat foods, and bring then back.

        positiveGoal = []
        negtiveGoal = [("food_available",)] # no food avaliable means eat all the food

        for obj in objects:
            agent_obj = obj[0]
            agent_type = obj[1]
            
            if agent_type == "enemy1" or agent_type == "enemy2":
                negtiveGoal += [("is_pacman", agent_obj)] # no enemy should standing on our land.
        
        return positiveGoal, negtiveGoal

    def goalDefWinning(self,objects: List[Tuple], initState: List[Tuple]):
        # If winning greater than 5 points,
        # this example want defend foods only, and let agents patrol on our ground.
        # The "win_the_game" pddl state is only reachable by the "patrol" action in pddl,
        # using it as goal, pddl will generate plan eliminate invading enemy and patrol on our ground.

        positiveGoal = [("defend_foods",)]
        negtiveGoal = []
        
        return positiveGoal, negtiveGoal

    #------------------------------- Heuristic search low level plan Functions -------------------------------
    def getLowLevelPlanHS(self, gameState: GameState, highLevelAction: str) -> List[Tuple[str,Tuple]]:
        mode = self.getEffectiveLowLevelMode(gameState, highLevelAction)
        self.updateDefenceMemory(gameState)

        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return self.getFallbackPlan(gameState, highLevelAction=highLevelAction)

        start = nearestPoint(myPos)
        targets = self.getLowLevelTargets(gameState, mode)
        targets = [target for target in targets if self.isLegalPosition(gameState, target)]

        if not targets:
            return self.getFallbackPlan(gameState, mode, highLevelAction=highLevelAction)

        self.searchBudgetExhausted = False
        plan = self.boundedAStarToTargets(gameState, start, targets, mode)
        if not plan:
            return self.getFallbackPlan(gameState, mode, targets, highLevelAction)

        self.currentLowLevelMode = mode
        self.currentHighLevelAction = highLevelAction
        self.currentLowLevelTarget = plan[-1][1]
        self.lastObservedPosition = start
        MixedAgent.sharedModes[self.index] = mode
        MixedAgent.sharedTargets[self.index] = self.currentLowLevelTarget
        return plan # Return a list of (move action, target location), excluding current location.

    def getLowLevelMode(self, highLevelAction: str) -> str:
        actionName = str(highLevelAction).lower()
        if "attack" in actionName or "food" in actionName or "score" in actionName:
            return "attack"
        if "home" in actionName or "escape" in actionName or "return" in actionName:
            return "go_home"
        if "defend" in actionName or "defence" in actionName:
            return "defence"
        return "patrol"

    def getEffectiveLowLevelMode(self, gameState: GameState, highLevelAction: str) -> str:
        mode = self.getLowLevelMode(highLevelAction)
        if mode == "attack" and self.shouldReturnHome(gameState):
            return "go_home"
        cooperativeMode = self.getCooperativeModeOverride(gameState, mode)
        if cooperativeMode is not None:
            return cooperativeMode
        if mode in ("attack", "patrol"):
            agentState = gameState.getAgentState(self.index)
            if not agentState.isPacman and (self.getVisibleInvaders(gameState) or self.lastEatenFood is not None):
                return "defence"
        return mode

    def getCooperativeModeOverride(self, gameState: GameState, mode: str):
        agentState = gameState.getAgentState(self.index)
        visibleInvaders = self.getVisibleInvaders(gameState)

        if self.shouldUseLateLeadDefence(gameState):
            if agentState.isPacman:
                return "go_home"
            return "defence" if visibleInvaders or self.lastEatenFood is not None else "patrol"

        if mode == "attack" and self.teammateHasMode(gameState, "go_home") and not self.isTeamBehind(gameState):
            if agentState.isPacman:
                return None
            return "defence" if visibleInvaders or self.lastEatenFood is not None else "patrol"

        return None

    def shouldUseLateLeadDefence(self, gameState: GameState) -> bool:
        timeLeft = getattr(gameState.data, "timeleft", 0)
        return self.getScore(gameState) >= 5 and 0 < timeLeft <= 220

    def isTeamBehind(self, gameState: GameState) -> bool:
        return self.getScore(gameState) < 0

    def teammateHasMode(self, gameState: GameState, mode: str) -> bool:
        for teammate in self.getTeam(gameState):
            if teammate != self.index and MixedAgent.sharedModes.get(teammate) == mode:
                return True
        return False

    def shouldReturnHome(self, gameState: GameState) -> bool:
        agentState = gameState.getAgentState(self.index)
        myPos = agentState.getPosition()
        if myPos is None or not agentState.isPacman:
            return False

        myPos = nearestPoint(myPos)
        carrying = agentState.numCarrying
        if carrying >= 3:
            return True

        dangerousGhosts = self.getVisibleDangerousGhosts(gameState)
        ghostDistance = self.distanceToClosestTarget(myPos, dangerousGhosts) if dangerousGhosts else sys.maxsize
        if carrying > 0 and ghostDistance <= CLOSE_DISTANCE + 1:
            return True
        if ghostDistance <= 2:
            return True

        homeTargets = self.getGoHomeTargets(gameState)
        homeDistance = self.distanceToClosestTarget(myPos, homeTargets) if homeTargets else 0
        timeLeft = getattr(gameState.data, "timeleft", 0)
        if carrying > 0 and timeLeft > 0 and timeLeft <= (homeDistance + 5) * 4:
            return True

        if carrying > 0 and self.getScore(gameState) >= 5:
            return True

        return False

    def updateDefenceMemory(self, gameState: GameState):
        currentDefendingFood = self.getFoodYouAreDefending(gameState).asList()
        if getattr(self, "previousDefendingFood", None):
            eatenFood = set(self.previousDefendingFood) - set(currentDefendingFood)
            if eatenFood:
                myPos = gameState.getAgentPosition(self.index)
                if myPos is None:
                    self.lastEatenFood = list(eatenFood)[0]
                    self.previousDefendingFood = currentDefendingFood
                    return
                self.lastEatenFood = min(eatenFood, key=lambda pos: util.manhattanDistance(myPos, pos))
        myPos = gameState.getAgentPosition(self.index)
        if self.lastEatenFood is not None and myPos is not None:
            if util.manhattanDistance(nearestPoint(myPos), self.lastEatenFood) <= 1 and not self.getVisibleInvaders(gameState):
                self.lastEatenFood = None
        self.previousDefendingFood = currentDefendingFood

    def updateMovementMemory(self, gameState: GameState):
        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return

        self.recentPositions.append(nearestPoint(myPos))
        self.recentPositions = self.recentPositions[-6:]
        if self.isDefenceOscillating():
            self.stuckRecoverySteps = 5
        elif self.stuckRecoverySteps > 0:
            self.stuckRecoverySteps -= 1

    def isDefenceOscillating(self) -> bool:
        if len(self.recentPositions) < 5:
            return False

        recent = self.recentPositions[-5:]
        return (
            len(set(recent)) <= 2 or
            (recent[-1] == recent[-3] == recent[-5] and recent[-2] == recent[-4])
        )

    def getLowLevelTargets(self, gameState: GameState, mode: str) -> List[Tuple[int, int]]:
        if mode == "attack":
            return self.getAttackTargets(gameState)

        if mode == "go_home":
            return self.getGoHomeTargets(gameState)

        if mode == "defence":
            return self.getDefenceTargets(gameState)

        return self.getPatrolPoints(gameState)

    def getDefenceTargets(self, gameState: GameState) -> List[Tuple[int, int]]:
        invaders = self.getVisibleInvaders(gameState)
        if self.stuckRecoverySteps > 0:
            recoveryTargets = self.getAntiOscillationTargets(gameState)
            if recoveryTargets:
                closestInvaderDistance = sys.maxsize
                myPos = gameState.getAgentPosition(self.index)
                if myPos is not None and invaders:
                    closestInvaderDistance = self.distanceToClosestTarget(nearestPoint(myPos), invaders)
                if closestInvaderDistance > 2:
                    return recoveryTargets

        if invaders:
            return self.sortTargetsByDistance(gameState, invaders)

        targets = []
        if self.lastEatenFood is not None and self.isLegalPosition(gameState, self.lastEatenFood):
            targets.append(self.lastEatenFood)

        capsules = [cap for cap in self.getCapsulesYouAreDefending(gameState) if self.isLegalPosition(gameState, cap)]
        targets.extend(self.sortTargetsByDistance(gameState, capsules))

        targets.extend(self.getBoundaryChokepoints(gameState))
        targets.extend(self.getPatrolPoints(gameState))
        return list(dict.fromkeys(targets))

    def getAntiOscillationTargets(self, gameState: GameState) -> List[Tuple[int, int]]:
        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return []
        myPos = nearestPoint(myPos)

        candidates = []
        candidates.extend(self.getBoundaryChokepoints(gameState))
        candidates.extend(self.getFoodClusterEntryPoints(gameState))
        candidates.extend([cap for cap in self.getCapsulesYouAreDefending(gameState) if self.isLegalPosition(gameState, cap)])
        candidates.extend(self.getHomeBoundaryPoints(gameState))

        recentSet = set(self.recentPositions[-4:])
        uniqueCandidates = [
            candidate for candidate in dict.fromkeys(candidates)
            if self.isLegalPosition(gameState, candidate) and candidate not in recentSet
        ]
        return sorted(
            uniqueCandidates,
            key=lambda target: (
                -self.distanceToClosestTarget(target, list(recentSet)) if recentSet else 0,
                util.manhattanDistance(myPos, target),
            )
        )[:3]

    def getGoHomeTargets(self, gameState: GameState) -> List[Tuple[int, int]]:
        boundaryPoints = self.getHomeBoundaryPoints(gameState)
        if not boundaryPoints:
            return []

        ranked = sorted(boundaryPoints, key=lambda target: self.getHomeTargetScore(gameState, target))
        safest = [
            target for target in ranked
            if self.getGhostTargetPenalty(gameState, target) < 80
        ]
        return (safest or ranked)[:1]

    def getHomeTargetScore(self, gameState: GameState, target: Tuple[int, int]) -> float:
        myPos = gameState.getAgentPosition(self.index)
        distance = util.manhattanDistance(nearestPoint(myPos), target) if myPos is not None else 0
        score = distance + self.getGhostTargetPenalty(gameState, target)
        if self.isChokepoint(gameState, target):
            score += 2
        return score

    def getAttackTargets(self, gameState: GameState) -> List[Tuple[int, int]]:
        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return []
        myPos = nearestPoint(myPos)

        foods = [food for food in self.getFood(gameState).asList() if self.isLegalPosition(gameState, food)]
        capsules = [cap for cap in self.getCapsules(gameState) if self.isLegalPosition(gameState, cap)]
        dangerousGhosts = self.getVisibleDangerousGhosts(gameState)

        if not foods:
            return self.rankAttackTargets(gameState, capsules)

        safeFoods = [food for food in foods if self.isSafeAttackFood(food, dangerousGhosts)]
        ghostPressure = (
            dangerousGhosts and
            self.distanceToClosestTarget(myPos, dangerousGhosts) <= CLOSE_DISTANCE + 1
        )

        if ghostPressure and capsules:
            capsuleTargets = self.rankAttackTargets(gameState, capsules)
            if not safeFoods:
                return capsuleTargets[:1]
            nearestSafeFood = self.distanceToClosestTarget(myPos, safeFoods)
            nearestCapsule = self.distanceToClosestTarget(myPos, capsuleTargets)
            if nearestCapsule <= nearestSafeFood + 2:
                return capsuleTargets[:1]

        if safeFoods:
            return self.rankAttackTargets(gameState, safeFoods)[:1]

        if capsules:
            return self.rankAttackTargets(gameState, capsules)[:1]

        return self.rankAttackTargets(gameState, foods)[:1]

    def rankAttackTargets(self, gameState: GameState, targets: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        return sorted(targets, key=lambda target: self.getAttackTargetScore(gameState, target))

    def getAttackTargetScore(self, gameState: GameState, target: Tuple[int, int]) -> float:
        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return 0
        myPos = nearestPoint(myPos)
        score = util.manhattanDistance(myPos, target)
        score += self.getGhostTargetPenalty(gameState, target)
        score += self.getTeammateTargetPenalty(gameState, target)
        score += self.getRegionalAttackPenalty(gameState, target)
        return score

    def getRegionalAttackPenalty(self, gameState: GameState, target: Tuple[int, int]) -> float:
        if self.isTeamBehind(gameState):
            return 0

        walls = gameState.getWalls()
        centreY = walls.height // 2
        assignedSide = -1 if self.index == min(self.getTeam(gameState)) else 1
        targetSide = -1 if target[1] < centreY else 1

        penalty = 0
        if targetSide != assignedSide:
            penalty += 6

        for teammate in self.getTeam(gameState):
            if teammate == self.index or MixedAgent.sharedModes.get(teammate) != "attack":
                continue
            teammateTarget = MixedAgent.sharedTargets.get(teammate)
            if teammateTarget is None:
                continue
            teammateTarget = nearestPoint(teammateTarget)
            teammateSide = -1 if teammateTarget[1] < centreY else 1
            if targetSide == teammateSide:
                penalty += 5

        return penalty

    def isSafeAttackFood(self, food: Tuple[int, int], dangerousGhosts: List[Tuple[int, int]]) -> bool:
        if not dangerousGhosts:
            return True
        return self.distanceToClosestTarget(food, dangerousGhosts) > 2

    def getVisibleDangerousGhosts(self, gameState: GameState) -> List[Tuple[int, int]]:
        ghosts = []
        for opponent in self.getOpponents(gameState):
            opponentState = gameState.getAgentState(opponent)
            opponentPos = opponentState.getPosition()
            if opponentPos is None:
                continue
            if not opponentState.isPacman and opponentState.scaredTimer <= 1:
                ghosts.append(nearestPoint(opponentPos))
        return ghosts

    def getGhostTargetPenalty(self, gameState: GameState, target: Tuple[int, int]) -> float:
        dangerousGhosts = self.getVisibleDangerousGhosts(gameState)
        if not dangerousGhosts:
            return 0

        carrying = gameState.getAgentState(self.index).numCarrying
        multiplier = 1 + min(carrying, 6) * 0.35
        ghostDistance = self.distanceToClosestTarget(target, dangerousGhosts)
        if ghostDistance <= 1:
            return 80 * multiplier
        if ghostDistance == 2:
            return 25 * multiplier
        if ghostDistance <= CLOSE_DISTANCE:
            return 6 * multiplier
        return 0

    def getTeammateTargetPenalty(self, gameState: GameState, target: Tuple[int, int]) -> float:
        penalty = 0
        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return penalty
        myPos = nearestPoint(myPos)

        for teammate in self.getTeam(gameState):
            if teammate == self.index:
                continue

            teammateTarget = MixedAgent.sharedTargets.get(teammate)
            if teammateTarget is None:
                continue

            targetDistance = util.manhattanDistance(target, teammateTarget)
            if targetDistance <= 6:
                penalty += 10 + (6 - targetDistance) * 2
                teammatePos = gameState.getAgentPosition(teammate)
                if teammatePos is not None:
                    teammatePos = nearestPoint(teammatePos)
                    if util.manhattanDistance(teammatePos, teammateTarget) <= util.manhattanDistance(myPos, target):
                        penalty += 8

        return penalty

    def sortTargetsByDistance(self, gameState: GameState, targets: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return targets
        return sorted(targets, key=lambda target: util.manhattanDistance(nearestPoint(myPos), target))

    def getVisibleInvaders(self, gameState: GameState) -> List[Tuple[int, int]]:
        invaders = []
        for opponent in self.getOpponents(gameState):
            opponentState = gameState.getAgentState(opponent)
            opponentPos = opponentState.getPosition()
            if opponentState.isPacman and opponentPos is not None:
                invaders.append(nearestPoint(opponentPos))
        return invaders

    def getHomeBoundaryPoints(self, gameState: GameState) -> List[Tuple[int, int]]:
        walls = gameState.getWalls()
        boundaryX = walls.width // 2 - 1 if self.red else walls.width // 2
        return [(boundaryX, y) for y in range(1, walls.height - 1) if not walls[boundaryX][y]]

    def getPatrolPoints(self, gameState: GameState) -> List[Tuple[int, int]]:
        patrolPoints = []
        patrolPoints.extend(self.getBoundaryChokepoints(gameState))
        patrolPoints.extend(self.getFoodClusterEntryPoints(gameState))
        patrolPoints.extend([cap for cap in self.getCapsulesYouAreDefending(gameState) if self.isLegalPosition(gameState, cap)])
        patrolPoints.extend(self.getTeammateUncoveredPatrolPoints(gameState))
        patrolPoints.extend(self.getHomeBoundaryPoints(gameState))

        uniquePoints = [point for point in dict.fromkeys(patrolPoints) if self.isLegalPosition(gameState, point)]
        return sorted(uniquePoints, key=lambda target: self.getPatrolTargetScore(gameState, target))[:8]

    def getBoundaryChokepoints(self, gameState: GameState) -> List[Tuple[int, int]]:
        boundaryPoints = self.getHomeBoundaryPoints(gameState)
        if not boundaryPoints:
            return []

        walls = gameState.getWalls()
        centreY = walls.height // 2
        chokepoints = [point for point in boundaryPoints if self.isChokepoint(gameState, point)]
        candidates = chokepoints or boundaryPoints
        return sorted(candidates, key=lambda pos: (abs(pos[1] - centreY), util.manhattanDistance(pos, self.startPosition)))[:5]

    def getFoodClusterEntryPoints(self, gameState: GameState) -> List[Tuple[int, int]]:
        defendingFood = self.getFoodYouAreDefending(gameState).asList()
        boundaryPoints = self.getHomeBoundaryPoints(gameState)
        if not defendingFood or not boundaryPoints:
            return []

        lowerFoods = [food for food in defendingFood if food[1] < gameState.getWalls().height // 2]
        upperFoods = [food for food in defendingFood if food[1] >= gameState.getWalls().height // 2]
        clusters = [foods for foods in (lowerFoods, upperFoods) if foods]

        entries = []
        for foods in clusters:
            centroidY = sum(food[1] for food in foods) / float(len(foods))
            entries.append(min(boundaryPoints, key=lambda point: abs(point[1] - centroidY)))
        return entries

    def getTeammateUncoveredPatrolPoints(self, gameState: GameState) -> List[Tuple[int, int]]:
        boundaryPoints = self.getHomeBoundaryPoints(gameState)
        if not boundaryPoints:
            return []

        walls = gameState.getWalls()
        centreY = walls.height // 2
        teammateYs = []
        for teammate in self.getTeam(gameState):
            if teammate == self.index:
                continue
            teammateTarget = MixedAgent.sharedTargets.get(teammate)
            teammatePos = gameState.getAgentPosition(teammate)
            reference = teammateTarget if teammateTarget is not None else teammatePos
            if reference is not None:
                teammateYs.append(nearestPoint(reference)[1])

        if not teammateYs:
            preferredSide = -1 if self.index == min(self.getTeam(gameState)) else 1
        else:
            preferredSide = -1 if sum(teammateYs) / float(len(teammateYs)) >= centreY else 1

        sidePoints = [
            point for point in boundaryPoints
            if (point[1] - centreY) * preferredSide >= 0
        ]
        return sorted(sidePoints or boundaryPoints, key=lambda point: abs(point[1] - centreY))[:3]

    def getPatrolTargetScore(self, gameState: GameState, target: Tuple[int, int]) -> float:
        myPos = gameState.getAgentPosition(self.index)
        distance = util.manhattanDistance(nearestPoint(myPos), target) if myPos is not None else 0
        score = distance
        if self.isChokepoint(gameState, target):
            score -= 3
        if target in self.getCapsulesYouAreDefending(gameState):
            score -= 2
        score += self.getTeammateTargetPenalty(gameState, target) * 0.5
        return score

    def isLegalPosition(self, gameState: GameState, pos: Tuple[int, int]) -> bool:
        walls = gameState.getWalls()
        x, y = int(pos[0]), int(pos[1])
        return 0 <= x < walls.width and 0 <= y < walls.height and not walls[x][y]

    def getLegalSearchActions(self, gameState: GameState, pos: Tuple[int, int]) -> List[str]:
        legalActions = []
        for action in [Directions.NORTH, Directions.SOUTH, Directions.EAST, Directions.WEST]:
            nextPos = nearestPoint(Actions.getSuccessor(pos, action))
            if self.isLegalPosition(gameState, nextPos):
                legalActions.append(action)
        return legalActions

    def isChokepoint(self, gameState: GameState, pos: Tuple[int, int]) -> bool:
        legalNeighbors = Actions.getLegalNeighbors(pos, gameState.getWalls())
        if len(legalNeighbors) <= 2:
            return True

        walls = gameState.getWalls()
        nearMiddle = abs(pos[0] - walls.width // 2) <= 2
        return nearMiddle and len(legalNeighbors) <= 3

    def boundedAStarToTargets(self, gameState: GameState, start: Tuple[int, int], targets: List[Tuple[int, int]], mode: str) -> List[Tuple[str, Tuple]]:
        targetSet = set(targets)
        if start in targetSet:
            return []

        frontier = util.PriorityQueue()
        frontier.push((start, [], 0), self.distanceToClosestTarget(start, targets))
        bestCost = {start: 0}
        expansions = 0

        while not frontier.isEmpty() and expansions < self.maxLowLevelExpansions:
            pos, path, costSoFar = frontier.pop()

            if costSoFar > bestCost.get(pos, sys.maxsize):
                continue

            if pos in targetSet:
                return path

            expansions += 1
            for action in self.getLegalSearchActions(gameState, pos):
                nextPos = nearestPoint(Actions.getSuccessor(pos, action))
                newCost = costSoFar + self.getSearchStepCost(gameState, pos, nextPos, targets, mode)
                if newCost >= bestCost.get(nextPos, sys.maxsize):
                    continue
                bestCost[nextPos] = newCost
                priority = newCost + self.distanceToClosestTarget(nextPos, targets)
                frontier.push((nextPos, path + [(action, nextPos)], newCost), priority)

        self.searchBudgetExhausted = expansions >= self.maxLowLevelExpansions
        return []

    def getSearchStepCost(self, gameState: GameState, pos: Tuple[int, int], nextPos: Tuple[int, int], targets: List[Tuple[int, int]], mode: str) -> float:
        stepCost = 1
        carrying = gameState.getAgentState(self.index).numCarrying
        carryingRiskMultiplier = 1 + min(carrying, 6) * 0.45

        dangerousGhosts = self.getVisibleDangerousGhosts(gameState)
        if dangerousGhosts:
            ghostDistance = self.distanceToClosestTarget(nextPos, dangerousGhosts)
            if ghostDistance == 0:
                stepCost += 100 * carryingRiskMultiplier
            elif ghostDistance == 1:
                stepCost += 35 * carryingRiskMultiplier
            elif ghostDistance == 2:
                stepCost += 12 * carryingRiskMultiplier
            elif ghostDistance <= CLOSE_DISTANCE:
                stepCost += 3 * carryingRiskMultiplier

            if carrying > 0 and ghostDistance <= CLOSE_DISTANCE and self.isChokepoint(gameState, nextPos):
                stepCost += 8 + carrying * 2
            elif mode == "go_home" and ghostDistance <= 2 and self.isChokepoint(gameState, nextPos):
                stepCost += 8

        stepCost += self.getTeammateStepConflictPenalty(gameState, nextPos)
        stepCost += self.getRecentPositionPenalty(nextPos, mode)

        currentTargetDistance = self.distanceToClosestTarget(pos, targets)
        nextTargetDistance = self.distanceToClosestTarget(nextPos, targets)
        if nextTargetDistance < currentTargetDistance:
            stepCost -= 0.15
        elif nextTargetDistance > currentTargetDistance:
            stepCost += 0.25

        return max(0.2, stepCost)

    def getRecentPositionPenalty(self, nextPos: Tuple[int, int], mode: str) -> float:
        if mode not in ("defence", "patrol") or not self.recentPositions:
            return 0

        recent = self.recentPositions[-5:]
        if nextPos == recent[-1]:
            return 4
        if nextPos in recent[-3:]:
            return 2.5
        if nextPos in recent:
            return 1
        return 0

    def getTeammateStepConflictPenalty(self, gameState: GameState, nextPos: Tuple[int, int]) -> float:
        penalty = 0
        for teammate in self.getTeam(gameState):
            if teammate == self.index:
                continue
            teammateTarget = MixedAgent.sharedTargets.get(teammate)
            if teammateTarget is None:
                continue

            distance = util.manhattanDistance(nextPos, teammateTarget)
            if distance <= 2:
                penalty += 7
            elif distance <= 4:
                penalty += 2.5
        return penalty

    def distanceToClosestTarget(self, pos: Tuple[int, int], targets: List[Tuple[int, int]]) -> int:
        if not targets:
            return 0
        return min(util.manhattanDistance(pos, target) for target in targets)

    def getFallbackPlan(self, gameState: GameState, mode: str = "patrol", targets: List[Tuple[int, int]] = None, highLevelAction: str = None) -> List[Tuple[str, Tuple]]:
        action = self.getFallbackAction(gameState, targets, mode)
        myPos = gameState.getAgentPosition(self.index)
        nextPos = Actions.getSuccessor(myPos, action) if myPos is not None else myPos
        nextPos = nearestPoint(nextPos) if nextPos is not None else nextPos

        self.currentLowLevelMode = mode
        self.currentHighLevelAction = highLevelAction
        self.currentLowLevelTarget = nextPos
        self.lastObservedPosition = nearestPoint(myPos) if myPos is not None else myPos
        MixedAgent.sharedModes[self.index] = mode
        MixedAgent.sharedTargets[self.index] = nextPos
        return [(action, nextPos)]

    def getFallbackAction(self, gameState: GameState, targets: List[Tuple[int, int]] = None, mode: str = "patrol") -> str:
        legalActions = [action for action in gameState.getLegalActions(self.index) if action != Directions.STOP]
        if not legalActions:
            return Directions.STOP

        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return legalActions[0]

        if targets:
            return min(
                legalActions,
                key=lambda action: self.getFallbackActionScore(gameState, myPos, action, targets, mode)
            )

        reverse = Directions.REVERSE[gameState.getAgentState(self.index).configuration.direction]
        nonReverse = [action for action in legalActions if action != reverse]
        candidates = nonReverse if nonReverse else legalActions
        return min(candidates, key=lambda action: self.getFallbackActionScore(gameState, myPos, action, targets, mode))

    def getFallbackActionScore(self, gameState: GameState, myPos: Tuple[int, int], action: str, targets: List[Tuple[int, int]], mode: str) -> float:
        nextPos = nearestPoint(Actions.getSuccessor(myPos, action))
        score = self.distanceToClosestTarget(nextPos, targets) if targets else 0
        score += self.getSearchStepCost(gameState, nearestPoint(myPos), nextPos, targets or [nextPos], mode)
        return score
    
    def posSatisfyLowLevelPlan(self, gameState: GameState, expectedMode: str = None, expectedHighLevelAction: str = None):
        if self.lowLevelPlan == None or len(self.lowLevelPlan)==0 or self.lowLevelActionIndex >= len(self.lowLevelPlan):
            return False
        if expectedMode is not None and self.currentLowLevelMode != expectedMode:
            return False
        if expectedHighLevelAction is not None and self.currentHighLevelAction != expectedHighLevelAction:
            return False
        if not self.currentLowLevelTargetStillValid(gameState):
            return False
        myPos = gameState.getAgentPosition(self.index)
        if myPos is None:
            return False
        myGridPos = nearestPoint(myPos)
        if self.lastObservedPosition is not None and myGridPos == self.startPosition and self.lastObservedPosition != self.startPosition:
            return False
        nextAction = self.lowLevelPlan[self.lowLevelActionIndex][0]
        if nextAction not in gameState.getLegalActions(self.index):
            return False
        nextPos = Actions.getSuccessor(myPos,nextAction)
        nextPos = nearestPoint(nextPos)
        if nextPos != self.lowLevelPlan[self.lowLevelActionIndex][1]:
            return False
        self.lastObservedPosition = myGridPos
        return True

    def currentLowLevelTargetStillValid(self, gameState: GameState) -> bool:
        if self.currentLowLevelTarget is None:
            return True

        if self.currentLowLevelMode == "attack":
            return self.currentLowLevelTarget in set(self.getAttackTargets(gameState))

        if self.currentLowLevelMode == "go_home":
            return self.currentLowLevelTarget in set(self.getGoHomeTargets(gameState))

        if self.currentLowLevelMode == "defence":
            defenceTargets = self.getDefenceTargets(gameState)
            if self.stuckRecoverySteps > 0 and self.currentLowLevelTarget in set(defenceTargets):
                return True
            if self.getVisibleInvaders(gameState):
                return self.currentLowLevelTarget in set(self.getVisibleInvaders(gameState))
            if self.lastEatenFood is not None:
                return self.currentLowLevelTarget == self.lastEatenFood
            return self.currentLowLevelTarget in set(defenceTargets[:5])

        if self.currentLowLevelMode == "patrol":
            if self.getVisibleInvaders(gameState) or self.lastEatenFood is not None:
                return False
            return self.currentLowLevelTarget in set(self.getPatrolPoints(gameState))

        return self.isLegalPosition(gameState, self.currentLowLevelTarget)

    #------------------------------- Q-learning low level plan Functions -------------------------------

    """
    Iterate through all q-values that we get from all
    possible actions, and return the action associated
    with the highest q-value.
    """
    def getLowLevelPlanQL(self, gameState:GameState, highLevelAction: str) -> List[Tuple[str,Tuple]]:
        values = []
        legalActions = gameState.getLegalActions(self.index)
        rewardFunction = None
        featureFunction = None
        weights = None
        learningRate = 0

        ##########
        # The following classification of high level actions is only a example.
        # You should think and use your own way to design low level planner.
        ##########
        if highLevelAction == "attack":
            # The q learning process for offensive actions are complete, 
            # you can improve getOffensiveFeatures to collect more useful feature to pass more information to Q learning model
            # you can improve the getOffensiveReward function to give reward for new features and improve the trainning process .
            rewardFunction = self.getOffensiveReward
            featureFunction = self.getOffensiveFeatures
            weights = self.getOffensiveWeights()
            learningRate = self.alpha
        elif highLevelAction == "go_home":
            # The q learning process for escape actions are NOT complete,
            # Introduce more features and complete the q learning process
            rewardFunction = self.getEscapeReward
            featureFunction = self.getEscapeFeatures
            weights = self.getEscapeWeights()
            learningRate = 0 # learning rate set to 0 as reward function not implemented for this action, do not do q update, 
        else:
            # The q learning process for defensive actions are NOT complete,
            # Introduce more features and complete the q learning process
            rewardFunction = self.getDefensiveReward
            featureFunction = self.getDefensiveFeatures
            weights = self.getDefensiveWeights()
            learningRate = 0 # learning rate set to 0 as reward function not implemented for this action, do not do q update 

        if len(legalActions) != 0:
            prob = util.flipCoin(self.epsilon) # get change of perform random movement
            if prob and self.trainning:
                action = random.choice(legalActions)
            else:
                for action in legalActions:
                        if self.trainning:
                            self.updateWeights(gameState, action, rewardFunction, featureFunction, weights,learningRate)
                        values.append((self.getQValue(featureFunction(gameState, action), weights), action))
                action = max(values)[1]
        myPos = gameState.getAgentPosition(self.index)
        nextPos = Actions.getSuccessor(myPos,action)
        return [(action, nextPos)]


    """
    Iterate through all features (closest food, bias, ghost dist),
    multiply each of the features' value to the feature's weight,
    and return the sum of all these values to get the q-value.
    """
    def getQValue(self, features, weights):
        return features * weights
    
    """
    Iterate through all features and for each feature, update
    its weight values using the following formula:
    w(i) = w(i) + alpha((reward + discount*value(nextState)) - Q(s,a)) * f(i)(s,a)
    """
    def updateWeights(self, gameState, action, rewardFunction, featureFunction, weights, learningRate):
        features = featureFunction(gameState, action)
        nextState = self.getSuccessor(gameState, action)

        reward = rewardFunction(gameState, nextState)
        for feature in features:
            correction = (reward + self.discountRate*self.getValue(nextState, featureFunction, weights)) - self.getQValue(features, weights)
            weights[feature] =weights[feature] + learningRate*correction * features[feature]
        
    
    """
    Iterate through all q-values that we get from all
    possible actions, and return the highest q-value
    """
    def getValue(self, nextState: GameState, featureFunction, weights):
        qVals = []
        legalActions = nextState.getLegalActions(self.index)

        if len(legalActions) == 0:
            return 0.0
        else:
            for action in legalActions:
                features = featureFunction(nextState, action)
                qVals.append(self.getQValue(features,weights))
            return max(qVals)
    
    def getOffensiveReward(self, gameState: GameState, nextState: GameState):
        # Calculate the reward. 
        currentAgentState:AgentState = gameState.getAgentState(self.index)
        nextAgentState:AgentState = nextState.getAgentState(self.index)

        ghosts = self.getGhostLocs(gameState)
        ghost_1_step = sum(nextAgentState.getPosition() in Actions.getLegalNeighbors(g,gameState.getWalls()) for g in ghosts)

        base_reward =  -50 + nextAgentState.numReturned + nextAgentState.numCarrying
        new_food_returned = nextAgentState.numReturned - currentAgentState.numReturned
        score = self.getScore(nextState)

        if ghost_1_step > 0:
            base_reward -= 5
        if score <0:
            base_reward += score
        if new_food_returned > 0:
            # return home with food get reward score
            base_reward += new_food_returned*10
        
        print("Agent ", self.index," reward ",base_reward)
        return base_reward
    
    def getDefensiveReward(self,gameState, nextState):
        print("Warnning: DefensiveReward not implemented yet, and learnning rate is 0 for defensive ",file=sys.stderr)
        return 0
    
    def getEscapeReward(self,gameState, nextState):
        print("Warnning: EscapeReward not implemented yet, and learnning rate is 0 for escape",file=sys.stderr)
        return 0



    #------------------------------- Feature Related Action Functions -------------------------------


    
    def getOffensiveFeatures(self, gameState: GameState, action):
        food = self.getFood(gameState) 
        currAgentState = gameState.getAgentState(self.index)

        walls = gameState.getWalls()
        ghosts = self.getGhostLocs(gameState)
        
        # Initialize features
        features = util.Counter()
        nextState = self.getSuccessor(gameState, action)

        # Successor Score
        features['successorScore'] = self.getScore(nextState)/(walls.width+walls.height) * 10

        # Bias
        features["bias"] = 1.0
        
        # Get the location of pacman after he takes the action
        next_x, next_y = nextState.getAgentPosition(self.index)

        # Number of Ghosts 1-step away
        features["#-of-ghosts-1-step-away"] = sum((next_x, next_y) in Actions.getLegalNeighbors(g, walls) for g in ghosts) 
        
        
        dist_home =  self.getMazeDistance((next_x, next_y), gameState.getInitialAgentPosition(self.index))+1

        features["chance-return-food"] = (currAgentState.numCarrying)*(1 - dist_home/(walls.width+walls.height)) # The closer to home, the larger food carried, more chance return food
        
        # Closest food
        dist = self.closestFood((next_x, next_y), food, walls)
        if dist is not None:
                # make the distance a number less than one otherwise the update
                # will diverge wildly
                features["closest-food"] = dist/(walls.width+walls.height)
        else:
            features["closest-food"] = 0

        return features

    def getOffensiveWeights(self):
        return MixedAgent.QLWeights["offensiveWeights"]
    


    def getEscapeFeatures(self, gameState, action):
        features = util.Counter()
        successor = self.getSuccessor(gameState, action)

        myState = successor.getAgentState(self.index)
        myPos = myState.getPosition()

        # Computes whether we're on defense (1) or offense (0)
        features['onDefense'] = 1
        if myState.isPacman: features['onDefense'] = 0

        # Computes distance to invaders we can see
        enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
        enemiesAround = [a for a in enemies if not a.isPacman and a.getPosition() != None]
        if len(enemiesAround) > 0:
            dists = [self.getMazeDistance(myPos, a.getPosition()) for a in enemiesAround]
            features['enemyDistance'] = min(dists)

        if action == Directions.STOP: features['stop'] = 1
        features["distanceToHome"] = self.getMazeDistance(myPos,self.startPosition)

        return features

    def getEscapeWeights(self):
        return MixedAgent.QLWeights["escapeWeights"]
    


    def getDefensiveFeatures(self, gameState, action):
        features = util.Counter()
        successor = self.getSuccessor(gameState, action)

        myState = successor.getAgentState(self.index)
        myPos = myState.getPosition()

        # Computes whether we're on defense (1) or offense (0)
        features['onDefense'] = 1
        if myState.isPacman: features['onDefense'] = 0

        team = [successor.getAgentState(i) for i in self.getTeam(successor)]
        team_dist = self.getMazeDistance(team[0].getPosition(), team[1].getPosition())
        features['teamDistance'] = team_dist

        # Computes distance to invaders we can see
        enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
        invaders = [a for a in enemies if a.isPacman and a.getPosition() != None]
        features['numInvaders'] = len(invaders)
        if len(invaders) > 0:
            dists = [self.getMazeDistance(myPos, a.getPosition()) for a in invaders]
            features['invaderDistance'] = min(dists)

        if action == Directions.STOP: features['stop'] = 1
        rev = Directions.REVERSE[gameState.getAgentState(self.index).configuration.direction]
        if action == rev: features['reverse'] = 1

        return features

    def getDefensiveWeights(self):
        return MixedAgent.QLWeights["defensiveWeights"]
    
    def closestFood(self, pos, food, walls):
        fringe = [(pos[0], pos[1], 0)]
        expanded = set()
        while fringe:
            pos_x, pos_y, dist = fringe.pop(0)
            if (pos_x, pos_y) in expanded:
                continue
            expanded.add((pos_x, pos_y))
            # if we find a food at this location then exit
            if food[pos_x][pos_y]:
                return dist
            # otherwise spread out from the location to its neighbours
            nbrs = Actions.getLegalNeighbors((pos_x, pos_y), walls)
            for nbr_x, nbr_y in nbrs:
                fringe.append((nbr_x, nbr_y, dist+1))
        # no food found
        return None
    
    def stateClosestFood(self, gameState:GameState):
        pos = gameState.getAgentPosition(self.index)
        food = self.getFood(gameState)
        walls = gameState.getWalls()
        fringe = [(pos[0], pos[1], 0)]
        expanded = set()
        while fringe:
            pos_x, pos_y, dist = fringe.pop(0)
            if (pos_x, pos_y) in expanded:
                continue
            expanded.add((pos_x, pos_y))
            # if we find a food at this location then exit
            if food[pos_x][pos_y]:
                return dist
            # otherwise spread out from the location to its neighbours
            nbrs = Actions.getLegalNeighbors((pos_x, pos_y), walls)
            for nbr_x, nbr_y in nbrs:
                fringe.append((nbr_x, nbr_y, dist+1))
        # no food found
        return None
    
    def getSuccessor(self, gameState: GameState, action):
        """
        Finds the next successor which is a grid position (location tuple).
        """
        successor = gameState.generateSuccessor(self.index, action)
        pos = successor.getAgentState(self.index).getPosition()
        if pos != nearestPoint(pos):
            # Only half a grid position was covered
            return successor.generateSuccessor(self.index, action)
        else:
            return successor
    
    def getGhostLocs(self, gameState:GameState):
        ghosts = []
        opAgents = CaptureAgent.getOpponents(self, gameState)
        # Get ghost locations and states if observable
        if opAgents:
                for opponent in opAgents:
                        opPos = gameState.getAgentPosition(opponent)
                        opIsPacman = gameState.getAgentState(opponent).isPacman
                        if opPos and not opIsPacman: 
                                ghosts.append(opPos)
        return ghosts
    
