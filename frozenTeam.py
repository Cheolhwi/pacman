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
                                        'moves-toward-food': 0,
                                        'chance-return-food': 10,
                                        'eats-food': 30,
                                        'eats-capsule': 20,
                                        'stop': -50,
                                        'reverse': -5,
                                        # new features start from 0 and are learnt by trainning
                                        'carrying': 0,
                                        'ghost-distance': 0,
                                        'dead-end': 0,
                                        'revisit': 0,
                                        # Phase 10.2 structural features for random/narrow maps
                                        'home-path-margin': 0,
                                        'tunnel-depth': 0,
                                        },
            "defensiveWeights": {'numInvaders': -1000, 'onDefense': 100,'teamDistance':2 ,'invaderDistance': -10, 'stop': -100, 'reverse': -2},
            "escapeWeights": {'onDefense': 1000, 'enemyDistance': 30, 'stop': -100, 'distanceToHome': -20, '#-of-ghosts-1-step-away': -100},
            # counts trainning agent-games (2 per game), used to decay the teacher prob
            "trainedEpisodes": 0
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
        # Phase 10.2: static per-map tunnel depth (steps to escape a single-exit
        # corridor system, 0 = on a cycle/junction), feeds the tunnel-depth feature
        self.tunnelDepth = self.computeTunnelDepthMap(gameState.getWalls())
        self.recentPositions = []
        self.stuckRecoverySteps = 0
        MixedAgent.sharedTargets[self.index] = self.startPosition
        MixedAgent.sharedModes[self.index] = "patrol"

        # REMEMBER TRUN TRAINNING TO FALSE when submit to contest server.
        self.trainning = False # trainning mode to true will keep update weights and generate random movements by prob.
        # Low level modes routed to the q learning planner, the rest keep using
        # the heuristic search planner. Empty set means pure heuristic search.
        # The hybrid agent uses {"attack", "go_home"}; defence and patrol always stay
        # on heuristic search because the full q learning agent is much weaker.
        # Set trainning to True together with these modes when trainning the weights.
        self.qlLowLevelModes = set()
        # Phase 10.1: QL-guided A*. When on, the trained offensive Q values act as a
        # bounded extra step cost inside attack-mode A* (path preference), the search
        # framework and targets stay pure heuristic search. Off => boundedAStarToTargets
        # behaves identically to pure HS.
        self.qlGuidedAStar = True  # passed the full Phase 11 acceptance matrix, on by default
        self.qlPathLambda = 0.03  # scale of (maxQ - q) added to the step cost
        self.qlPathCap = 1.0  # max extra cost per step from the QL preference
        # Phase 11.0 diagnostic knob: comma separated offensive feature names whose
        # weights are zeroed inside the search-time Q adapter only (training and the
        # weights file stay untouched). Empty, the default, changes nothing.
        # frozenTeam (Phase 14.0): env-immune copy of the Phase 11 terminal state
        # (commit 09a2652). capture.py runs both teams in one process, so this
        # opponent must ignore every experiment env var to allow asymmetric A/B.
        self.qlPathAblateFeatures = set()
        # Read-only diagnostic counters for the q learning experiments (Phase 9.0).
        # They never change behaviour, final() prints one QL-DIAG line per game.
        self.qlDiagnostics = False
        self.diagPrevCarrying = 0
        self.diagPrevPos = None
        self.diagPrevMode = None
        self.diagMaxCarrying = 0
        self.diagFoodEaten = 0
        self.diagDeaths = 0
        self.diagMaxDepth = 0
        self.diagBoundaryDither = 0
        self.diagModeSwitches = 0
        self.diagDbgSteps = 0
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
                loadedWeights = eval(file.read())
            # the weights file may be trained before new features were added,
            # so merge it into the defaults and keep missing features at their default value
            for modeName, modeWeights in MixedAgent.QLWeights.items():
                if modeName in loadedWeights and isinstance(modeWeights, dict):
                    modeWeights.update(loadedWeights[modeName])
            MixedAgent.QLWeights["trainedEpisodes"] = loadedWeights.get("trainedEpisodes", 0)
            print("Load QLWeights:",MixedAgent.QLWeights )
        # Decay the teacher prob as trainning progresses (DAgger style): early trainning
        # follows the heuristic search teacher to see good trajectories, later trainning
        # acts on its own policy so the weights are learnt on the states the greedy
        # policy actually visits. trainedEpisodes counts agent-games (2 per game).
        # Keep a 0.3 floor: a lower floor lets self-play experience full of boundary
        # standoffs poison the offensive weights (observed at the 0.1 floor).
        self.teacherProb = max(0.3, 0.9 - 0.004 * MixedAgent.QLWeights.get("trainedEpisodes", 0))
        
    
    def final(self, gameState : GameState):
        """
        This function write weights into files after the game is over. 
        You may want to comment (disallow) this function when submit to contest server.
        """
        if self.trainning:
            MixedAgent.QLWeights["trainedEpisodes"] = MixedAgent.QLWeights.get("trainedEpisodes", 0) + 1
            print("Write QLWeights:", MixedAgent.QLWeights)
            file = open(MixedAgent.QLWeightsFile, 'w')
            file.write(str(MixedAgent.QLWeights))
            file.close()
        if self.qlDiagnostics:
            print("QL-DIAG agent", self.index,
                  "maxCarrying", self.diagMaxCarrying,
                  "foodEaten", self.diagFoodEaten,
                  "deaths", self.diagDeaths,
                  "maxDepth", self.diagMaxDepth,
                  "boundaryDither", self.diagBoundaryDither,
                  "modeSwitches", self.diagModeSwitches)
    

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
        # Get the low level plan with heuristic search (default) or Q learning, and return a low level action at last.
        # A low level action is defined in Directions, whihc include {"North", "South", "East", "West", "Stop"}

        desiredLowLevelMode = self.getEffectiveLowLevelMode(gameState, highLevelAction)
        if self.qlDiagnostics:
            self.updateQLDiagnostics(gameState, desiredLowLevelMode)
        if desiredLowLevelMode in self.qlLowLevelModes:
            # Q learning picks one action per step (and updates weights in trainning mode)
            self.lowLevelPlan = self.getLowLevelPlanQL(gameState, highLevelAction)
            self.lowLevelActionIndex = 0
        elif not self.posSatisfyLowLevelPlan(gameState, desiredLowLevelMode, highLevelAction):
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
        if self.shouldReturnHome(gameState):
            return "go_home"
        if mode == "defence" and self.shouldReleaseDefenceForAttack(gameState):
            mode = "attack"
        cooperativeMode = self.getCooperativeModeOverride(gameState, mode)
        if cooperativeMode is not None:
            return cooperativeMode
        if mode == "attack":
            agentState = gameState.getAgentState(self.index)
            if (
                not agentState.isPacman and
                self.getDefenceThreatTargets(gameState) and
                self.shouldHoldAttackDefenceRole(gameState)
            ):
                return "defence"
        if mode == "patrol":
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

    def shouldReleaseDefenceForAttack(self, gameState: GameState) -> bool:
        if not self.getFood(gameState).asList():
            return False
        if self.shouldUseLateLeadDefence(gameState):
            return False
        if gameState.getAgentState(self.index).isPacman:
            return True
        return not self.shouldHoldAttackDefenceRole(gameState)

    def shouldHoldAttackDefenceRole(self, gameState: GameState) -> bool:
        targets = self.getDefenceThreatTargets(gameState)
        if not targets:
            return False
        if self.teammateHasMode(gameState, "defence"):
            return False
        return self.isPrimaryDefenderForTargets(gameState, targets)

    def getDefenceThreatTargets(self, gameState: GameState) -> List[Tuple[int, int]]:
        targets = list(self.getVisibleInvaders(gameState))
        if self.lastEatenFood is not None and self.isLegalPosition(gameState, self.lastEatenFood):
            targets.append(self.lastEatenFood)
        return list(dict.fromkeys(targets))

    def isPrimaryDefenderForTargets(self, gameState: GameState, targets: List[Tuple[int, int]]) -> bool:
        best = None
        for teammate in self.getTeam(gameState):
            teammatePos = gameState.getAgentPosition(teammate)
            if teammatePos is None:
                continue
            teammatePos = nearestPoint(teammatePos)
            distance = self.distanceToClosestTarget(teammatePos, targets)
            candidate = (distance, teammate)
            if best is None or candidate < best:
                best = candidate
        return best is not None and best[1] == self.index

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

    def updateQLDiagnostics(self, gameState: GameState, mode: str):
        # Read-only counters used by the q learning experiments, never changes behaviour.
        agentState = gameState.getAgentState(self.index)
        myPos = agentState.getPosition()
        if myPos is None:
            return
        myPos = nearestPoint(myPos)
        carrying = agentState.numCarrying

        self.diagMaxCarrying = max(self.diagMaxCarrying, carrying)
        if carrying > self.diagPrevCarrying:
            self.diagFoodEaten += carrying - self.diagPrevCarrying
        # teleported back to start from far away means we got eaten
        if self.diagPrevPos is not None and myPos == self.startPosition \
                and util.manhattanDistance(self.diagPrevPos, self.startPosition) > 2:
            self.diagDeaths += 1

        homePoints = self.getHomeBoundaryPoints(gameState)
        if homePoints:
            boundaryDistance = self.distanceToClosestTarget(myPos, homePoints)
            if agentState.isPacman:
                self.diagMaxDepth = max(self.diagMaxDepth, boundaryDistance)
            elif mode == "attack" and boundaryDistance <= 3:
                self.diagBoundaryDither += 1

        if self.diagPrevMode is not None and mode != self.diagPrevMode:
            self.diagModeSwitches += 1
        self.diagPrevMode = mode
        self.diagPrevCarrying = carrying
        self.diagPrevPos = myPos

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

        # Phase 10.1: QL-guided A*, the trained offensive Q values shape the step cost
        # of attack searches as a bounded preference between sibling moves.
        qlContext = None
        if self.qlGuidedAStar and mode == "attack" and self.qlPathLambda > 0:
            qlContext = self.buildQLPathContext(gameState)

        while not frontier.isEmpty() and expansions < self.maxLowLevelExpansions:
            pos, path, costSoFar = frontier.pop()

            if costSoFar > bestCost.get(pos, sys.maxsize):
                continue

            if pos in targetSet:
                return path

            expansions += 1
            legalActions = self.getLegalSearchActions(gameState, pos)
            qlPenalty = {}
            if qlContext is not None and len(legalActions) > 1:
                # Relative normalization per expansion: the locally preferred sibling pays 0,
                # the others pay a capped non-negative surcharge. Never negative, so no
                # "long paths look free" artifact and the heuristic stays an underestimate.
                qValues = {
                    action: self.getQLPathValue(qlContext, nearestPoint(Actions.getSuccessor(pos, action)))
                    for action in legalActions
                }
                maxQ = max(qValues.values())
                qlPenalty = {
                    action: min(self.qlPathCap, self.qlPathLambda * (maxQ - qValue))
                    for action, qValue in qValues.items()
                }
            for action in legalActions:
                nextPos = nearestPoint(Actions.getSuccessor(pos, action))
                newCost = costSoFar + self.getSearchStepCost(gameState, pos, nextPos, targets, mode) + qlPenalty.get(action, 0)
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

    #------------------------------- Phase 10.1: QL-guided A* (QL as path preference) -------------------------------
    def buildQLPathContext(self, gameState: GameState) -> dict:
        """Snapshot everything the search-time Q adapter needs, built once per A* call.
        Ghosts come from getGhostLocs (including scared ghosts) on purpose: the offensive
        weights were trained on features computed from that same set, so filtering it
        differently here would evaluate the linear model off its training distribution.
        Hard scared-aware safety stays the job of getSearchStepCost via
        getVisibleDangerousGhosts, whose penalties dwarf the capped QL term."""
        walls = gameState.getWalls()
        ghosts = self.getGhostLocs(gameState)
        homePoints = self.getHomeBoundaryPoints(gameState)
        # Per-boundary-point closest ghost distance, precomputed once per search
        # for the home-path-margin feature (constant while the search runs).
        ghostBoundaryDist = {}
        if ghosts:
            for b in homePoints:
                ghostBoundaryDist[b] = min(self.getMazeDistance(nearestPoint(g), b) for g in ghosts)
        weights = self.getOffensiveWeights()
        if self.qlPathAblateFeatures:
            # Phase 11.0 ablation: zero the named features in this read-only snapshot.
            weights = {k: (0 if k in self.qlPathAblateFeatures else v) for k, v in weights.items()}
        return {
            "walls": walls,
            "capsules": set(self.getCapsules(gameState)),
            "ghosts": ghosts,
            "homePoints": homePoints,
            "ghostBoundaryDist": ghostBoundaryDist,
            "carrying": gameState.getAgentState(self.index).numCarrying,
            "recentSet": set(self.recentPositions),
            "weights": weights,
            "cache": {},
        }

    def getQLPathValue(self, context: dict, nextPos: Tuple[int, int]) -> float:
        """Q-ish value of stepping onto nextPos, mirroring getOffensiveFeatures semantics
        and normalizations exactly for the subset that is meaningful inside A*.
        Dropped on purpose: stop/reverse (no Stop in search, no dithering in a path),
        closest-food/moves-toward-food (the A* heuristic and progress bonus already drive
        progress toward the HS-chosen target, a nearest-food pull would fight that target),
        bias/carrying (constant across sibling moves, cancel under maxQ - q),
        eats-food (Phase 11.0 ablation pinned it as the cause of the bloxCapture margin
        regression: the en-route food pull buys corridor detours that fight the HS-chosen
        target, same failure family as closest-food; dropping it turned blox from +5.3
        to +8.7 while defaultCapture stayed neutral, n=50 each).
        The kept features only depend on nextPos, so the value is memoized per search."""
        cache = context["cache"]
        if nextPos in cache:
            return cache[nextPos]

        walls = context["walls"]
        ghosts = context["ghosts"]
        w = context["weights"]
        q = 0.0

        if nextPos in context["capsules"]:
            q += w.get("eats-capsule", 0)

        if ghosts:
            q += w.get("#-of-ghosts-1-step-away", 0) * sum(
                nextPos in Actions.getLegalNeighbors(g, walls) for g in ghosts)
            ghostDist = min(self.getMazeDistance(nextPos, nearestPoint(g)) for g in ghosts)
            q += w.get("ghost-distance", 0) * ghostDist / (walls.width + walls.height)

        if len(Actions.getLegalNeighbors(nextPos, walls)) <= 2:
            q += w.get("dead-end", 0)
        if nextPos in context["recentSet"]:
            q += w.get("revisit", 0)

        # Phase 10.2 structural features, mirroring getOffensiveFeatures.
        # home-path-margin: skipped when no ghosts (constant 1.0 across siblings).
        if ghosts:
            bestMargin = max(
                context["ghostBoundaryDist"][b] - self.getMazeDistance(nextPos, b)
                for b in context["homePoints"]
            )
            q += w.get("home-path-margin", 0) * max(-1.0, min(1.0, bestMargin / (walls.width + walls.height)))
        q += w.get("tunnel-depth", 0) * (min(self.tunnelDepth.get(nextPos, 0), 5) / 5.0)

        carrying = context["carrying"]
        if carrying > 0:
            distHome = self.distanceToClosestTarget(nextPos, context["homePoints"]) + 1
            q += w.get("chance-return-food", 0) * carrying * (1 - distHome / (walls.width + walls.height))

        cache[nextPos] = q
        return q

    def computeTunnelDepthMap(self, walls) -> dict:
        """Static map analysis for the tunnel-depth feature (Phase 10.2).
        A cell's depth is how many steps it takes to get back to a cell that is on
        a cycle or junction (the 2-core of the open-cell graph): the tip of a
        length-5 dead-end corridor has depth 5, its mouth 1, open area 0.
        Unlike dead-end (one cell, one exit) this sees whole single-exit corridor
        systems, which is where random/narrow maps get our pacman trapped."""
        openCells = set()
        for x in range(walls.width):
            for y in range(walls.height):
                if not walls[x][y]:
                    openCells.add((x, y))

        def liveNeighbors(cell, alive):
            x, y = cell
            return [n for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)) if n in alive]

        # Iterative degree<=1 pruning leaves the 2-core (cells on cycles).
        core = set(openCells)
        while True:
            leaves = [c for c in core if len(liveNeighbors(c, core)) <= 1]
            if not leaves:
                break
            core -= set(leaves)

        depth = {}
        if not core:
            # Degenerate tree-shaped maze: every cell would be "in a tunnel",
            # the feature carries no signal, keep it inert.
            return {cell: 0 for cell in openCells}

        # Multi-source BFS from the core through the pruned tree cells.
        for cell in core:
            depth[cell] = 0
        frontier = list(core)
        level = 0
        while frontier:
            level += 1
            nextFrontier = []
            for cell in frontier:
                for n in liveNeighbors(cell, openCells):
                    if n not in depth:
                        depth[n] = level
                        nextFrontier.append(n)
            frontier = nextFrontier
        return depth

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
        # Stop is only allowed as a fallback in this project, never as a planned move.
        # Without this the learnt stop weight can let the agent freeze forever in a
        # standoff against a defender sitting right across the boundary.
        movingActions = [a for a in legalActions if a != Directions.STOP]
        if movingActions:
            legalActions = movingActions
        rewardFunction = None
        featureFunction = None
        weights = None
        learningRate = 0

        # Reuse the same mode arbitration as the heuristic search planner (including
        # the forced go_home when carrying enough food), so the q learning planner
        # works on the same task as the teacher and the weights are updated for the right mode.
        mode = self.getEffectiveLowLevelMode(gameState, highLevelAction)
        if mode == "attack":
            rewardFunction = self.getOffensiveReward
            featureFunction = self.getOffensiveFeatures
            weights = self.getOffensiveWeights()
            learningRate = self.alpha
        elif mode == "go_home":
            rewardFunction = self.getEscapeReward
            featureFunction = self.getEscapeFeatures
            weights = self.getEscapeWeights()
            learningRate = self.alpha
        else:
            # defence and patrol both use the defensive q learning model
            rewardFunction = self.getDefensiveReward
            featureFunction = self.getDefensiveFeatures
            weights = self.getDefensiveWeights()
            learningRate = self.alpha

        if len(legalActions) != 0:
            if self.trainning:
                # update weights with every legal action, so each step gives several learning samples
                for action in legalActions:
                    self.updateWeights(gameState, action, rewardFunction, featureFunction, weights,learningRate)

            if self.trainning and util.flipCoin(self.epsilon):
                # exploration: take a random step
                action = random.choice(legalActions)
            else:
                action = None
                if self.trainning and util.flipCoin(self.teacherProb):
                    # follow the heuristic search plan as a teacher;
                    # q-learning is off-policy, so it can learn q values from the teacher's moves,
                    # which reach food and home much more often than a half-trained greedy policy
                    teacherPlan = self.getLowLevelPlanHS(gameState, highLevelAction)
                    if teacherPlan and teacherPlan[0][0] in legalActions:
                        action = teacherPlan[0][0]
                if action is None:
                    # act greedily on current q values
                    for candidate in legalActions:
                        values.append((self.getQValue(featureFunction(gameState, candidate), weights), candidate))
                    action = max(values)[1]
                    if self.qlDiagnostics and self.index == 0 and self.diagDbgSteps < 25:
                        dbgPos = nearestPoint(gameState.getAgentPosition(self.index))
                        dbgHome = self.getHomeBoundaryPoints(gameState)
                        if dbgHome and not gameState.getAgentState(self.index).isPacman \
                                and self.distanceToClosestTarget(dbgPos, dbgHome) <= 2:
                            self.diagDbgSteps += 1
                            print("QL-DBG pos", dbgPos, "pick", action, "ghosts", self.getGhostLocs(gameState))
                            for q, candidate in sorted(values, reverse=True):
                                print("   ", candidate, round(q, 2), dict(featureFunction(gameState, candidate)))
        myPos = gameState.getAgentPosition(self.index)
        nextPos = nearestPoint(Actions.getSuccessor(myPos,action))

        # keep the shared information updated so teammate cooperation still works
        self.currentLowLevelMode = mode
        self.currentHighLevelAction = highLevelAction
        self.currentLowLevelTarget = nextPos
        MixedAgent.sharedModes[self.index] = mode
        MixedAgent.sharedTargets[self.index] = nextPos
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
        # crossing the boundary (return food home, enter enemy land, or get eaten back)
        # ends the current low level episode, so do not bootstrap from the next state value,
        # otherwise the value of the next stage leaks back and the weights blow up
        sideChanged = gameState.getAgentState(self.index).isPacman != nextState.getAgentState(self.index).isPacman
        if sideChanged:
            correction = reward - self.getQValue(features, weights)
        else:
            # compute the correction once with the old weights, then update every feature weight,
            # otherwise the correction keeps changing inside the loop and the weights blow up
            correction = (reward + self.discountRate*self.getValue(nextState, featureFunction, weights)) - self.getQValue(features, weights)
        # clip the correction so a single bad sample cannot blow up the weights
        correction = max(-100, min(100, correction))
        for feature in features:
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
        # Reward for offensive actions, based on what changed after taking the action,
        # so the learning signal is not buried by a big constant term.
        currentAgentState:AgentState = gameState.getAgentState(self.index)
        nextAgentState:AgentState = nextState.getAgentState(self.index)

        ghosts = self.getGhostLocs(gameState)
        ghost_1_step = sum(nextAgentState.getPosition() in Actions.getLegalNeighbors(g,gameState.getWalls()) for g in ghosts)

        reward = -1 # small living cost so the agent keeps making progress

        # reward for eating a food on this step
        foodEaten = nextAgentState.numCarrying - currentAgentState.numCarrying
        if foodEaten > 0:
            reward += foodEaten * 10

        # big reward for bringing food back home
        newFoodReturned = nextAgentState.numReturned - currentAgentState.numReturned
        if newFoodReturned > 0:
            reward += newFoodReturned * 20

        # punish standing next to a ghost
        if ghost_1_step > 0:
            reward -= 5

        # big punishment for getting eaten (sent back to start and lose all carried food)
        nextPos = nextState.getAgentPosition(self.index)
        if nextPos is not None and nearestPoint(nextPos) == self.startPosition and currentAgentState.isPacman:
            reward -= 100

        return reward
    
    def getDefensiveReward(self,gameState, nextState):
        # Reward for defensive actions:
        # we want the agent to chase invaders and protect our food.
        reward = -1 # small living cost so the agent does not wander

        currentInvaders = self.getVisibleInvaders(gameState)
        nextInvaders = self.getVisibleInvaders(nextState)

        # an invader disappeared from our side (eaten or escaped), big reward
        if len(nextInvaders) < len(currentInvaders):
            reward += 50

        # reward for moving closer to the closest visible invader
        myPos = gameState.getAgentPosition(self.index)
        nextPos = nextState.getAgentPosition(self.index)
        if currentInvaders and myPos is not None and nextPos is not None:
            currentDist = self.distanceToClosestTarget(nearestPoint(myPos), currentInvaders)
            nextDist = self.distanceToClosestTarget(nearestPoint(nextPos), currentInvaders)
            reward += (currentDist - nextDist) * 2

        # punish if our defending food got eaten on this step
        currentFoodNum = len(self.getFoodYouAreDefending(gameState).asList())
        nextFoodNum = len(self.getFoodYouAreDefending(nextState).asList())
        if nextFoodNum < currentFoodNum:
            reward -= 10

        # punish if we got eaten as a scared ghost (sent back to start)
        if nextPos is not None and nearestPoint(nextPos) == self.startPosition and myPos is not None and nearestPoint(myPos) != self.startPosition:
            reward -= 50

        return reward
    
    def getEscapeReward(self,gameState, nextState):
        # Reward for escape (go home) actions:
        # we want the agent to bring food back home safely.
        currentAgentState: AgentState = gameState.getAgentState(self.index)
        nextAgentState: AgentState = nextState.getAgentState(self.index)
        reward = -1 # small living cost

        # big reward for actually returning food home
        newFoodReturned = nextAgentState.numReturned - currentAgentState.numReturned
        if newFoodReturned > 0:
            reward += newFoodReturned * 20

        # reward for getting closer to our home boundary
        myPos = gameState.getAgentPosition(self.index)
        nextPos = nextState.getAgentPosition(self.index)
        homeTargets = self.getHomeBoundaryPoints(gameState)
        if homeTargets and myPos is not None and nextPos is not None:
            currentDist = self.distanceToClosestTarget(nearestPoint(myPos), homeTargets)
            nextDist = self.distanceToClosestTarget(nearestPoint(nextPos), homeTargets)
            reward += (currentDist - nextDist) * 2

        # big punishment for getting eaten on the way home (sent back to start)
        if nextPos is not None and nearestPoint(nextPos) == self.startPosition and currentAgentState.isPacman:
            reward -= 100

        return reward



    #------------------------------- Feature Related Action Functions -------------------------------


    
    def getOffensiveFeatures(self, gameState: GameState, action):
        food = self.getFood(gameState) 
        currAgentState = gameState.getAgentState(self.index)

        walls = gameState.getWalls()
        ghosts = self.getGhostLocs(gameState)
        
        # Initialize features
        features = util.Counter()
        nextState = self.getSuccessor(gameState, action)

        # Bias
        features["bias"] = 1.0
        
        # Get the location of pacman after he takes the action
        next_x, next_y = nextState.getAgentPosition(self.index)

        # Number of Ghosts 1-step away
        features["#-of-ghosts-1-step-away"] = sum((next_x, next_y) in Actions.getLegalNeighbors(g, walls) for g in ghosts) 

        # Whether this action eats a food or a capsule
        if food[next_x][next_y]:
            features["eats-food"] = 1.0
        if (next_x, next_y) in self.getCapsules(gameState):
            features["eats-capsule"] = 1.0

        # Discourage stopping and turning back, otherwise the greedy policy keeps dithering
        if action == Directions.STOP:
            features['stop'] = 1
        rev = Directions.REVERSE[gameState.getAgentState(self.index).configuration.direction]
        if action == rev:
            features['reverse'] = 1

        # Use distance to our home boundary instead of the start position,
        # crossing the boundary is enough to return the food
        homePoints = self.getHomeBoundaryPoints(gameState)
        dist_home = self.distanceToClosestTarget((next_x, next_y), homePoints) + 1

        features["chance-return-food"] = (currAgentState.numCarrying)*(1 - dist_home/(walls.width+walls.height)) # The closer to home, the larger food carried, more chance return food
        
        # Closest food
        dist = self.closestFood((next_x, next_y), food, walls)
        if dist is not None:
                # make the distance a number less than one otherwise the update
                # will diverge wildly
                features["closest-food"] = dist/(walls.width+walls.height)
        else:
            features["closest-food"] = 0

        # Binary progress feature: this action gets us strictly closer to the closest food.
        # A progress bonus is more robust than the raw distance, whose learnt sign can be
        # twisted by correlation with the returns, and it can outweigh a fixed ghost
        # penalty wall at the boundary that the raw distance gradient never beats.
        curr_x, curr_y = nearestPoint(gameState.getAgentPosition(self.index))
        currDist = self.closestFood((curr_x, curr_y), food, walls)
        if dist is not None and currDist is not None and dist < currDist:
            features["moves-toward-food"] = 1.0

        # How much food we are carrying, the more we carry the more we should
        # care about ghosts and going home instead of the next food
        features["carrying"] = currAgentState.numCarrying / 10.0

        # Distance to the closest visible dangerous ghost (1 when none visible),
        # so the threat is felt before the ghost is already 1 step away
        if ghosts:
            ghostDist = min(self.getMazeDistance((next_x, next_y), nearestPoint(g)) for g in ghosts)
            features["ghost-distance"] = ghostDist/(walls.width+walls.height)
        else:
            features["ghost-distance"] = 1.0

        # Next position only has one real exit (legal neighbors include standing still),
        # walking into a dead end while carrying food near a ghost is how we get caught
        if len(Actions.getLegalNeighbors((next_x, next_y), walls)) <= 2:
            features["dead-end"] = 1.0

        # Discourage walking back into recently visited cells, otherwise the greedy
        # policy paces in a tiny loop at a guarded boundary instead of trying another entry
        if (next_x, next_y) in self.recentPositions:
            features["revisit"] = 1.0

        # Phase 10.2: can a ghost cut our best home route. For the best boundary
        # point, how much earlier do we arrive than the closest ghost: positive
        # margin = the route home is safe, negative = it can be cut off.
        if ghosts:
            bestMargin = max(
                min(self.getMazeDistance(nearestPoint(g), b) for g in ghosts)
                - self.getMazeDistance((next_x, next_y), b)
                for b in homePoints
            )
            features["home-path-margin"] = max(-1.0, min(1.0, bestMargin / (walls.width + walls.height)))
        else:
            features["home-path-margin"] = 1.0

        # Phase 10.2: how deep the next position sits inside a single-exit corridor
        # system (entry-flexibility direction: larger = fewer ways to retreat).
        features["tunnel-depth"] = min(self.tunnelDepth.get((next_x, next_y), 0), 5) / 5.0

        return features

    def getOffensiveWeights(self):
        return MixedAgent.QLWeights["offensiveWeights"]
    


    def getEscapeFeatures(self, gameState, action):
        features = util.Counter()
        successor = self.getSuccessor(gameState, action)
        walls = gameState.getWalls()

        myState = successor.getAgentState(self.index)
        myPos = myState.getPosition()

        # Computes whether we're on defense (1) or offense (0)
        features['onDefense'] = 1
        if myState.isPacman: features['onDefense'] = 0

        # Computes distance to invaders we can see
        # distances are divided by the map size to keep features small,
        # otherwise the q learning update diverges
        enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
        enemiesAround = [a for a in enemies if not a.isPacman and a.getPosition() != None]
        if len(enemiesAround) > 0:
            dists = [self.getMazeDistance(myPos, a.getPosition()) for a in enemiesAround]
            features['enemyDistance'] = min(dists)/(walls.width+walls.height)

        # number of ghosts right next to us, getting eaten on the way home is the worst case
        ghosts = self.getGhostLocs(gameState)
        features['#-of-ghosts-1-step-away'] = sum(nearestPoint(myPos) in Actions.getLegalNeighbors(g, walls) for g in ghosts)

        if action == Directions.STOP: features['stop'] = 1
        # distance to our home boundary, crossing it is enough to return the food
        homePoints = self.getHomeBoundaryPoints(gameState)
        features["distanceToHome"] = self.distanceToClosestTarget(nearestPoint(myPos), homePoints)/(walls.width+walls.height)

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

        # distances are divided by the map size to keep features small,
        # otherwise the q learning update diverges
        walls = gameState.getWalls()
        team = [successor.getAgentState(i) for i in self.getTeam(successor)]
        team_dist = self.getMazeDistance(team[0].getPosition(), team[1].getPosition())
        features['teamDistance'] = team_dist/(walls.width+walls.height)

        # Computes distance to invaders we can see
        enemies = [successor.getAgentState(i) for i in self.getOpponents(successor)]
        invaders = [a for a in enemies if a.isPacman and a.getPosition() != None]
        features['numInvaders'] = len(invaders)
        if len(invaders) > 0:
            dists = [self.getMazeDistance(myPos, a.getPosition()) for a in invaders]
            features['invaderDistance'] = min(dists)/(walls.width+walls.height)

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
    
