# FIT5222 Assignment 2 需求文档

## 1. 项目背景

本项目对应课程作业 **FIT5222 Assignment 2: Pacman Capture the Flag**。目标是在现有 `pacman` 仓库中完成一个可运行的双智能体对抗控制器，并以 `myTeam.py` 作为主要提交与实现入口。

该任务不是单纯的最短路问题，而是一个同时具备以下特点的规划问题：

- 多智能体对抗：我方与敌方各有两名 agent，需要同时考虑协作与博弈。
- 动态环境：food、capsule、敌方位置与我方风险会不断变化。
- 部分可观测：敌人并非始终可见，只能在有限条件下观察到真实位置。
- 时间受限：每一步动作决策必须在严格的时间限制内完成。

在游戏中，agent 需要跨越中线进入敌方半场，吃掉敌方 food，并安全返回己方半场完成 deposit 得分。同时，agent 还需要在必要时切换到防守模式，拦截入侵者并保护己方 food 与 capsule。

本需求文档的目标不是简单复述题目说明，而是为后续实现 `getLowLevelPlanHS()`、补充高层规则映射、加入重规划机制与双 agent 协作逻辑提供直接实现依据。

本文档默认只讨论以下唯一实现方向：

- 保留现有高层 PDDL 框架。
- 将低层动作规划从 Q-learning 替换为 Heuristic Search。

不讨论以下范围：

- 继续扩展纯 Q-learning 方案。
- 整体放弃 PDDL 并重写完整控制架构。
- 引入运行时 LLM、外部 API 或大型学习框架。

## 2. 运行环境与启动流程

### 2.1 本地默认运行环境

本地开发、调试与测试默认使用如下环境：

```bash
conda activate flatland-rl
```

进入项目后的推荐工作流如下：

```bash
conda activate flatland-rl
cd /path/to/pacman
python capture.py -h
```

其中：

- `capture.py` 是 Pacman simulator 的命令行入口。
- `-r` 用于指定 red team。
- `-b` 用于指定 blue team。
- `-l` 用于指定 layout。
- `-q` 与 `-Q` 用于静默运行。
- `-n` 用于指定对局次数。

### 2.2 环境检查命令

每次开始开发前，建议先执行以下检查命令：

```bash
which python
python --version
python capture.py -h
```

这些检查的目的包括：

- 确认当前解释器确实来自 `flatland-rl` 环境。
- 确认 Python 版本与作业环境一致。
- 确认 simulator 可以成功启动。
- 避免出现环境错位问题，例如：

```bash
zsh: bad CPU type in executable: python
```

### 2.3 环境边界

`conda activate flatland-rl` 是 shell 层面的环境命令，不能写进 `myTeam.py`。

正确的使用位置包括：

- README 或需求文档。
- 本地测试脚本说明。
- 开发流程文档。

错误的使用位置包括：

- `myTeam.py`
- `myTeam.pddl`
- agent 运行时逻辑

## 3. 代码边界与当前架构

### 3.1 主要代码入口

本次实现的核心文件如下：

- `myTeam.py`：主智能体实现入口。
- `myTeam.pddl`：高层 PDDL 规则定义文件。
- `capture.py`：本地 simulator 与比赛规则入口。

本次需求范围中，`myTeam.py` 是最主要的修改位置，`myTeam.pddl` 只允许做最小必要修补。

### 3.2 当前控制流程

当前模板控制流程固定理解为：

```text
GameState
-> get_pddl_state()
-> getGoals()
-> getHighLevelPlan()
-> getLowLevelPlanQL() / getLowLevelPlanHS()
-> concrete action
```

其含义如下：

- `get_pddl_state()`：从当前 `GameState` 提取高层规划所需对象与状态。
- `getGoals()`：根据当前局势选择高层目标。
- `getHighLevelPlan()`：调用 PDDL solver 生成高层动作序列。
- `getLowLevelPlanQL()`：当前默认低层 planner。
- `getLowLevelPlanHS()`：预留的 Heuristic Search 低层 planner。

### 3.3 本次实现边界

本次实现只替换 low-level planner，不整体推翻高层 PDDL 框架，也不重写 `chooseAction()` 的整体结构。

允许的范围：

- 将 `getLowLevelPlanQL()` 的调用替换为 `getLowLevelPlanHS()`。
- 为 low-level HS 增加目标选择、风险评估、fallback 与重规划逻辑。
- 为高层 action name 增加兼容映射层。
- 为双 agent 增加最小协作共享信息结构。

不允许的范围：

- 重构整个 `myTeam.py` 的高层逻辑。
- 完全推翻 `myTeam.pddl`。
- 引入在线学习、深度学习或额外外部服务。

## 4. 接口约束

### 4.1 `chooseAction()` 修改要求

当前低层调用逻辑为：

```python
self.lowLevelPlan = self.getLowLevelPlanQL(gameState, highLevelAction)
```

目标修改为：

```python
self.lowLevelPlan = self.getLowLevelPlanHS(gameState, highLevelAction)
```

除 low-level planner 切换外，`chooseAction()` 的对外行为与调用方式不应改变。

### 4.2 `getLowLevelPlanHS()` 接口约束

目标函数接口保持如下形式：

```python
def getLowLevelPlanHS(self, gameState, highLevelAction):
    ...
    return [(action, location), ...]
```

返回结果格式固定为：

```python
[
    ("North", (x1, y1)),
    ("East", (x2, y2)),
    ...
]
```

要求如下：

- 不修改外部调用方式。
- 每个元素必须包含动作与预期到达位置。
- 动作只能从 `North`、`South`、`East`、`West` 中选择。
- `Stop` 不作为 A* 主动搜索动作，只允许在 fallback 中使用。

## 5. Low-level Heuristic Search 设计要求

### 5.1 搜索状态

初版低层搜索状态定义为 agent 当前坐标：

```text
S = (x, y)
```

初版不将以下因素直接并入搜索状态：

- `carrying food`
- `enemy belief`
- `scared timer`
- `returned food`
- teammate mode

原因是这些因素会显著扩大搜索空间，影响单步规划性能。初版应优先保证可运行性与响应速度，再通过 cost function 与目标选择补充局势信息。

### 5.2 合法动作

低层搜索中的合法动作通过以下方式获得：

- 优先使用 `gameState.getLegalActions(self.index)`。
- 或结合墙体判断，过滤掉会撞墙的动作。

默认动作集合为：

```text
{North, South, East, West}
```

约束如下：

- `Stop` 不参与主搜索。
- 如果下一格是 wall，则该动作不能加入搜索扩展。
- 如果搜索失败或当前局面异常，可退回 `Stop` 或其他合法 fallback 动作。

### 5.3 目标判定

low-level goal test 需要先将 high-level action 映射为 mode，再根据 mode 选择目标集合：

- `attack`：到达安全 food 或合适的 capsule。
- `go_home`：到达己方边界的安全点。
- `defence`：到达可见 invader、最近丢失 food 点，或关键防守点。
- `patrol`：到达中线 chokepoint 或预设巡逻点。

可以抽象为：

```text
Goal(s) =
attack  -> s in FoodTargets or CapsuleTargets
go_home -> s in HomeBoundary
defence -> s in DefensiveTargets
patrol  -> s in PatrolPoints
```

### 5.4 搜索算法

初版默认使用：

```text
bounded A*
```

实现要求：

- 使用启发式优先展开节点。
- 限制最大展开节点数，避免超时。
- 目标不是理论最优，而是稳定地产生合理动作。

默认参数要求：

```python
max_expansions = 600
```

如果性能不足，可降为：

```python
max_expansions = 300
```

### 5.5 启发函数

初版启发函数默认采用 Manhattan distance：

```text
h(s) = ManhattanDistance(s, target)
```

仅当性能验证稳定时，才允许考虑切换为更昂贵的：

```text
h(s) = MazeDistance(s, target)
```

使用原则：

- 初版优先稳健和速度。
- 不应在还未稳定通过时间测试前默认启用 `MazeDistance` 作为搜索主 heuristic。

## 6. High-level 到 Low-level 的规则映射

### 6.1 action name 兼容映射层

由于高层 PDDL action name 与需求文档中的 mode 名称可能不完全一致，必须增加兼容映射层。

推荐逻辑如下：

```python
name = highLevelAction.name.lower()

if "attack" in name or "food" in name or "score" in name:
    mode = "attack"
elif "home" in name or "escape" in name or "return" in name:
    mode = "go_home"
elif "defend" in name or "defence" in name:
    mode = "defence"
else:
    mode = "patrol"
```

这层兼容逻辑必须作为 low-level planner 的入口之一，而不是散落在多个局部判断中。

### 6.2 `attack` 规则

`attack` 模式下，目标优先级如下：

1. 最近的安全 food。
2. 当 ghost 阻塞路径时，优先 capsule。
3. 当 `carrying` 达到阈值后，应触发回家逻辑。
4. 当队友已锁定同一 food cluster 时，应切换到另一簇 food。

`attack` 模式中的目标选择应综合以下因素：

- 我方到 food 的距离。
- food 到 home boundary 的距离。
- food 附近 ghost 风险。
- teammate 是否正在争夺相同区域。

### 6.3 `go_home` 规则

`go_home` 模式的触发条件至少包括以下情况：

1. `carrying` 达到阈值，例如 `3` 或 `4`。
2. 可见危险 ghost 距离过近。
3. 剩余时间较少，且当前已携带 food。
4. 当前比分领先，没有必要继续冒险。

`go_home` 的目标必须固定为：

```text
nearest safe home boundary point
```

该模式的核心是：

- 优先找最短回家路径。
- 强烈惩罚接近危险 ghost。
- 避免穿过敌方 ghost 附近的 chokepoint。

### 6.4 `defence` 规则

`defence` 模式下，目标优先级如下：

1. 可见 invader。
2. 最近一次被偷的 food 位置。
3. 我方 capsule 附近。
4. 中线或 home boundary chokepoint。
5. 默认巡逻点。

为支持 food disappeared inference，文档要求维护：

```python
self.previousDefendingFood
self.lastEatenFood
```

用途如下：

- 比较前后两次 defending food 列表。
- 若发现某个 food 消失，则记录其位置到 `lastEatenFood`。
- 在看不到 invader 时，优先前往该区域调查。

### 6.5 `patrol` 规则

当没有可见 invader 时，agent 默认进入 `patrol` 模式。

巡逻点优先级如下：

1. 中线 chokepoints。
2. 靠近我方 food cluster 的入口。
3. 我方 capsule 附近。
4. 队友未覆盖的一侧边界。

`patrol` 不是纯随机移动，而是带目标的弱防守模式。

## 7. Cost Function 要素

低层搜索中的路径代价以每步基础成本为核心，并叠加风险与协作惩罚。

基础 cost 设为：

```text
base cost = 1
```

其上至少需要加入以下要素：

- `danger`：越接近可见危险 ghost，惩罚越高。
- `carryingRisk`：携带 food 越多，越应保守。
- `teammateConflict`：与队友争抢同一目标或区域时增加惩罚。
- `reward`：接近优质目标时可以有轻微抵扣。

直观解释如下：

- 普通走一步，代价为 `1`。
- 若下一步更靠近危险 ghost，则显著加罚。
- 若当前已携带较多 food，则鼓励更安全的路径。
- 若队友已锁定相邻目标，则降低重复争抢。
- 若某一步明显更接近高价值安全 food 或 capsule，可给予小幅奖励抵扣。

## 8. 重规划触发条件

当满足以下任一条件时，当前 `lowLevelPlan` 必须被废弃并重新搜索：

1. `lowLevelPlan` 为空。
2. 当前 agent 位置与 plan 预期不一致。
3. high-level action 已改变。
4. 目标 food 或 capsule 已不存在。
5. 可见危险 ghost 进入阈值范围。
6. `carrying` 已达到回家阈值。
7. agent 被吃掉并回到起点。
8. 队友与当前 agent 的目标发生冲突。
9. 搜索超过 `max_expansions`。
10. 当前路径的下一步动作已不合法。

该机制的目标是避免 agent 盲目坚持旧路线，特别是在下列场景中：

- 前往 food 的过程中突然看到 ghost。
- food 被队友或敌人改变局面后失效。
- defensive target 已移动或消失。

## 9. Teammate Cooperation 最小要求

为提升对局表现，系统需要实现最小程度的双 agent 协作。

建议共享结构如下：

```python
MixedAgent.sharedTargets = {}
MixedAgent.sharedModes = {}
```

每次完成 low-level 规划后更新：

```python
MixedAgent.sharedTargets[self.index] = target
MixedAgent.sharedModes[self.index] = mode
```

### 9.1 协作要求

- food 目标选择必须加入 teammate conflict 惩罚。
- 两个 agent 不应长期锁定同一 food cluster。
- 当队友正在回家时，另一名 agent 更倾向于承担 patrol 或 defence。
- 当比分领先且剩余时间较少时，允许两名 agent 偏向防守。
- 当比分落后时，允许两名 agent 同时进入进攻态。

### 9.2 默认协作策略

默认策略写死为以下原则：

- 分区域进攻。
- 必要时一攻一守。
- 领先少时双防守。
- 落后时可双进攻。

## 10. 约束与性能目标

### 10.1 本地 simulator 约束

当前本地 `capture.py` 与 Berkeley 风格规则中可以直接确认以下限制：

- 对局总动作数默认 `1200` moves。
- `registerInitialState` 启动预算为 `15` 秒。
- 每步 `1` 秒会触发 warning。
- 单步超过 `3` 秒会 instant forfeit。

### 10.2 更新版 submission instruction 差异

计划文档中还引用了更新版 submission instruction 的 `5` 秒 timestep 说法。由于本地代码约束更严格，本需求文档要求实现时按更严格版本设计。

### 10.3 工程性能目标

为了同时兼容本地更严格限制与更新版说明，单步规划的工程目标控制为：

```text
0.1 ~ 0.5 秒
```

设计原则如下：

- 以本地 simulator 限制为主。
- 低层搜索优先保证稳定与及时返回。
- 即使对局规模增大，也应尽量避免频繁超时。

## 11. 功能验收标准

需求实现后，至少应满足以下功能表现：

1. `attack` 时能稳定朝 food 推进，而不是随机游走。
2. `attack` 不会明显冲向危险 ghost。
3. `go_home` 时在携带 food 后能稳定回到边界。
4. `defence` 时看到 invader 会主动追击。
5. 看不到 invader 时会巡逻 chokepoint 或调查失窃点。
6. food 被偷后，能够前往 `lastEatenFood` 附近调查。
7. 搜索失败不会抛异常。
8. fallback 始终返回合法动作。
9. 红蓝两侧都能正确识别 home boundary。
10. 两个 agent 不会长期争抢同一目标。
11. 批量对局中不应频繁 `Stop`。
12. 批量对局中不应频繁超时。

## 12. 测试计划

### 12.1 测试前置

所有测试命令默认前置：

```bash
conda activate flatland-rl
cd /path/to/pacman
```

### 12.2 环境 smoke test

```bash
python capture.py -h
```

目标：

- 验证当前 Python 环境能正常运行 simulator。

### 12.3 单局可视或静默测试

```bash
python capture.py -r myTeam.py -b staffTeam.py -q -n 1
```

目标：

- 确认不存在 import error。
- 确认 `chooseAction()` 能返回合法动作。
- 确认 `getLowLevelPlanHS()` 不抛异常。

### 12.4 批量静默测试

```bash
python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/defaultCapture
```

目标：

- 检查整体是否稳定运行。
- 检查是否存在超时。
- 检查是否经常 `Stop`。

### 12.5 红蓝互换测试

```bash
python capture.py -r staffTeam.py -b myTeam.py -Q -n 10 -l ./layouts/defaultCapture
```

目标：

- 检查 red/blue 的 boundary 判断是否写反。
- 检查 home boundary 判断是否具备对称性。

### 12.6 多地图测试

```bash
python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/strategicCapture
python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/bloxCapture
```

目标：

- 检查在不同布局下是否仍能正常规划。
- 检查是否对单一地图过拟合。

### 12.7 接近 contest 的 49 局测试

```bash
python capture.py -r myTeam.py -b staffTeam.py -Q -n 49 -l RANDOM23
python capture.py -r myTeam.py -b staffTeam.py -Q -n 49 -l RANDOM42
```

目标：

- 统计 `win / loss / tie`。
- 将 `28/49` 作为“接近或超过 baseline”的参考指标。

注意：`28/49` 是目标指标，但不是当前需求文档阶段唯一成败标准。

### 12.8 时间限制测试

```bash
python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -c
```

目标：

- 检查是否违反动作时间限制。
- 验证 low-level HS 在批量运行中是否稳定。

### 12.9 测试顺序要求

测试说明必须明确以下顺序：

1. 先验证 import 与接口正确性。
2. 再验证 agent 行为是否符合预期。
3. 最后再看胜率与时间表现。

## 13. 实现假设

本需求文档采用以下固定假设：

- 文档语言固定为中文。
- 默认保存文件名固定为 `assignment2_requirements.md`。
- 当前实现只允许使用标准 Python 与仓库现有依赖。
- 不新增新的第三方 Python package。
- 不在运行时调用 LLM 或外部 API。
- `myTeam.pddl` 只做最小必要修补。
- 主体工作集中在 `myTeam.py`。

后续代码实现的重点位置包括：

- `getLowLevelPlanHS()`
- target selection
- risk-aware cost function
- fallback action
- replanning trigger
- teammate target sharing

此外，后续真正编码时，正文应直接以本需求文档为实现依据，不再新增额外的方案比选章节，以避免偏离当前唯一实现路线。
