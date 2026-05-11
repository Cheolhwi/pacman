# FIT5222 Assignment 2 分阶段实验计划

## Summary

目标是基于现有 `myTeam.py` 与 `myTeam.pddl`，保留高层 PDDL 框架，只把低层从 `getLowLevelPlanQL()` 切换到 `getLowLevelPlanHS()`，并分阶段完成：基础可运行、进攻回家稳定、防守巡逻完善、协作与重规划补齐、最后做批量测试与调参。

默认实现决策固定为：

- 低层搜索使用 `bounded A*`
- 启发函数先用 `Manhattan distance`
- `max_expansions = 600`，若超时再降到 `300`
- 主体改动集中在 `myTeam.py`
- `myTeam.pddl` 只做最小必要修补
- 先保证稳定合法返回动作，再追求胜率

## 接口与实现约束

必须保持以下接口和行为不变：

- `chooseAction()` 的对外调用方式不变，只把低层调用替换为 `self.getLowLevelPlanHS(gameState, highLevelAction)`
- `getLowLevelPlanHS(self, gameState, highLevelAction)` 返回 `[(action, location), ...]`
- 主搜索动作仅使用 `North/South/East/West`
- `Stop` 只允许作为 fallback
- 新增的类内共享状态统一放在 `MixedAgent` 类变量或实例缓存中

建议在实现开始前就确定会新增的最小内部状态：

- `MixedAgent.sharedTargets = {}`
- `MixedAgent.sharedModes = {}`
- `self.previousDefendingFood`
- `self.lastEatenFood`
- 当前 low-level target 缓存，例如 `self.currentLowLevelTarget`

## Phase 1: 基线搭建与接口打通

目标是先把“能跑”这件事做稳，不追求强度。

工作内容：

- 读通 `chooseAction()`、`stateSatisfyCurrentPlan()`、`posSatisfyLowLevelPlan()`、`getGoals()` 的现有流程
- 在 `getLowLevelPlanHS()` 中先实现最小可运行版本
- 增加 high-level action 到 low-level mode 的统一映射层
- 实现基础工具函数：
  - home boundary 计算
  - patrol points 计算
  - legal neighbor / legal action 过滤
  - fallback action 选择
- 把 low-level 调用从 QL 切到 HS
- 保证任何异常场景都能返回合法动作

本阶段 mode 映射固定为：

- 包含 `attack/food/score` -> `attack`
- 包含 `home/escape/return` -> `go_home`
- 包含 `defend/defence` -> `defence`
- 其他全部 -> `patrol`

完成标准：

- `python capture.py -r myTeam.py -b staffTeam.py -q -n 1` 不报错
- `getLowLevelPlanHS()` 不再 `NotImplemented`
- agent 始终返回合法动作
- fallback 可覆盖空 plan、非法下一步、搜索失败三类情况

## Phase 2: 核心 HS 搜索与进攻模式

目标是先把 `attack` 做成稳定可解释的主路径。

工作内容：

- 用 `(x, y)` 作为搜索状态
- 用 bounded A* 生成从当前位置到目标点的动作序列
- 实现 attack 目标选择：
  - 默认优先最近的安全 food
  - ghost 阻塞时允许转 capsule
  - 队友锁定同簇 food 时切换目标
- 初版 cost function 只保留必要项：
  - `base cost = 1`
  - 可见 ghost 距离惩罚
  - 队友目标冲突惩罚
  - 轻微目标接近奖励
- 先不把复杂 belief state 放进搜索状态，只体现在选点和 cost 上

本阶段 attack 的默认规则固定为：

- 优先安全 food，再考虑 capsule
- 若携带未达阈值，不主动回家
- 若目标失效则立刻重规划
- 队友目标与自己曼哈顿距离过近时加冲突惩罚

完成标准：

- `attack` 不再随机游走
- 明显会朝 food 推进
- 不会主动贴近可见危险 ghost
- `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/defaultCapture` 可稳定跑完

## Phase 3: 回家逻辑与风险驱动重规划

目标是让 agent 在“该撤的时候能撤得回来”。

工作内容：

- 实现 `go_home` 目标固定为最近安全 home boundary point
- 实现回家触发条件：
  - `carrying >= 3` 先作为默认阈值
  - 危险 ghost 进入阈值范围
  - 剩余时间少且已携带 food
  - 大比分领先时降低进攻冒险
- 强化 risk-aware cost：
  - carrying 越多，ghost 邻近惩罚越高
  - chokepoint 且靠近 ghost 时追加惩罚
- 补齐 low-level replan trigger：
  - plan 为空
  - 当前位置与 plan 不一致
  - high-level action 改变
  - 目标 food/capsule 消失
  - 下一步动作不合法
  - 被吃回出生点
  - 搜索超预算

完成标准：

- `go_home` 时能稳定往边界走
- 携带 food 后不容易继续无意义深入敌区
- 批量运行中 `Stop` 次数明显受控
- 红蓝两侧都能正确识别 home boundary

## Phase 4: 防守、巡逻与失窃点调查

目标是补齐非进攻局面的行为闭环。

工作内容：

- 实现 defence 目标优先级：
  - 可见 invader
  - `lastEatenFood`
  - 我方 capsule 附近
  - 关键边界 chokepoint
- 维护 `previousDefendingFood` 和 `lastEatenFood`
- 实现 patrol 目标优先级：
  - 中线 chokepoint
  - 我方 food cluster 入口
  - capsule 附近
  - 队友未覆盖的一侧
- patrol 保持“有目标的弱防守”，不能退化成随机走

完成标准：

- 看到 invader 时会主动追击
- 看不到 invader 时会巡逻或去失窃点调查
- food 消失后能去对应区域检查
- `python capture.py -r staffTeam.py -b myTeam.py -Q -n 10 -l ./layouts/defaultCapture` 通过红蓝互换验证

本轮 Phase 4 观察到的问题：

- 防守目标过于固定时，agent 可能在狭窄通道或边界附近出现 A-B-A-B 式来回移动，表现为一直防守同一局部区域但无法有效推进。
- 需要加入 defence/patrol 的防振荡机制：记录最近位置，对最近走过的位置加代价；检测到短周期来回后，临时切换到离振荡点更远的防守/巡逻脱困目标。
- 只有在 invader 已经非常近时才继续强追，否则优先脱离卡点，避免长期被 `lastEatenFood` 或移动中的 invader 反复拉回同一个位置。

## Phase 5: 双 Agent 协作与策略分工

目标是减少两个 agent 互相打架。

工作内容：

- 每次 low-level 规划完成后更新：
  - `MixedAgent.sharedTargets[self.index]`
  - `MixedAgent.sharedModes[self.index]`
- 在 target selection 中加入 teammate conflict 惩罚
- 固定默认协作策略：
  - 常态下分区域进攻
  - 队友回家时，自己更偏 patrol/defence
  - 领先且时间少时偏双防守
  - 落后时允许双进攻
- 不做复杂通信，只做最小共享和目标避让

完成标准：

- 两个 agent 不会长期锁定同一 food cluster
- 队友已回家时，另一名 agent 能承担更稳的场上角色
- 批量对局中重复抢同一目标的情况明显减少

本轮 Phase 5 实验结果：

- 已补充共享目标/模式初始化，避免开局或跨局 stale target 影响目标评分。
- 已加入协作模式覆盖：
  - 领先且剩余时间较少时，Pacman 优先回家，非 Pacman 偏 patrol/defence。
  - 队友处于 `go_home` 且当前未落后时，留在本方的 agent 偏 patrol/defence。
  - 落后时不限制双进攻，允许两个 agent 同时抢分。
- 已加入进攻上下半区软分工和同目标簇惩罚，减少长期锁定同一 food cluster。
- `conda run -n flatland-rl python -m py_compile myTeam.py` 通过。
- `conda run -n flatland-rl python capture.py -h` 通过。
- `conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -q -n 1` 通过，红队胜 10 分。
- `conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/defaultCapture` 通过，红队 10/10 胜，平均分 `+8.2`。
- `conda run -n flatland-rl python capture.py -r staffTeam.py -b myTeam.py -Q -n 10 -l ./layouts/defaultCapture` 通过，蓝队 10/10 胜；输出以红队视角计分，平均分 `-7.0`。

## Phase 6: 批量实验、调参与提交前收敛

目标是把功能正确性转成可交付结果。

实验顺序固定为：

1. smoke test  
   `python capture.py -h`
2. 单局接口测试  
   `python capture.py -r myTeam.py -b staffTeam.py -q -n 1`
3. 批量静默测试  
   `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/defaultCapture`
4. 红蓝互换测试  
   `python capture.py -r staffTeam.py -b myTeam.py -Q -n 10 -l ./layouts/defaultCapture`
5. 多地图测试  
   `./layouts/strategicCapture`、`./layouts/bloxCapture`
6. 接近 contest 的 49 局测试  
   `-l RANDOM23`、`-l RANDOM42`
7. 时间限制测试  
   `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -c`

本阶段只允许调以下参数，不改主结构：

- `max_expansions`
- carrying 回家阈值 `3/4`
- ghost danger penalty
- teammate conflict penalty
- patrol / defence 目标优先级权重

验收重点：

- 不频繁超时
- 不频繁 `Stop`
- 红蓝两边行为对称
- 49 局结果尽量接近或超过文档参考的 `28/49`
- 即使未到目标胜率，也必须先满足稳定性与功能标准

## Test Cases

需要重点观察的行为场景：

- `attack` 时能否稳定接近 food
- ghost 出现后是否会放弃旧路线并重规划
- `carrying >= 3` 后是否能进入 `go_home`
- 被吃回起点后是否能丢弃旧 plan
- 看见 invader 时 defence 是否优先追击
- 看不见 invader 时是否会去 `lastEatenFood`
- 双 agent 是否长期争抢同一路径或同一 food cluster
- 多地图下是否仍能正确找 boundary 与 chokepoint

## Assumptions

默认假设如下：

- 本轮实现不继续使用 Q-learning 作为主低层策略
- 低层只做单 agent 路径搜索，局势复杂度通过目标选择与代价函数补足
- 初版 heuristic 固定用 Manhattan，不默认切 MazeDistance
- `myTeam.pddl` 不做结构性重写
- 先做“稳定合理”，再做“高胜率”
