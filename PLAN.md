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

本轮 Phase 6 固定实验结果：

- Python 编译检查通过，`capture.py -h` smoke test 通过。
- defaultCapture 正向测试红队 `10/10` 胜，平均分 `+8.8`。
- defaultCapture 红蓝互换后我方作为蓝队 `10/10` 胜；输出按红队视角平均分为 `-5.4`。
- strategicCapture 红队 `10/10` 胜，平均分 `+7.5`。
- bloxCapture 红队仅 `5/10` 胜，平均分 `0.0`，是当前最弱地图。
- RANDOM23 与 RANDOM42 均为红队 `49/49` 胜，平均分分别为 `+10.46938775510204` 和 `+8.346938775510203`。
- `-c` 时间限制测试通过，红队 `10/10` 胜，平均分 `+8.8`。

Phase 6 结论：

- 当前版本已满足提交前稳定性目标，没有崩溃、异常退出或时间限制失败。
- `max_expansions = 600` 暂时保留，不需要为了性能降低；也不建议继续增大，避免引入隐性超时风险。
- contest-like 随机地图结果已经明显超过 `28/49` 参考目标，因此提交版本应优先保护现有 defaultCapture、strategicCapture、RANDOM23/RANDOM42 表现。
- 主要短板集中在 bloxCapture。该地图更容易放大狭窄通道、回家路线被封、defence/patrol 来回振荡、两个 agent 被同一通道牵制等问题。
- 不建议为 bloxCapture 直接大幅调高 ghost risk 或重写主结构，因为这可能破坏随机地图和 defaultCapture 上已经稳定的结果。

后续改进方向限定为“小步 A/B 对比”：

- 保留当前参数作为稳定基线；任何调参必须和本轮 Phase 6 结果对比。
- 优先对比 carrying 回家阈值 `3` 与 `4`。如果 `4` 能提升 bloxCapture，且 defaultCapture 正反两侧仍保持 `10/10`，RANDOM23/RANDOM42 不明显下降，才考虑采用。
- 微调 defence/patrol 的 anti-oscillation：
  - 提高最近位置回访代价；
  - 对 A-B-A-B 短周期移动触发更长 stuck recovery；
  - 对 `lastEatenFood` 加短冷却，避免 agent 被同一失窃点长期拉回。
- 优化狭窄通道下的回家目标选择：
  - carrying > 0 且可见 ghost 靠近 chokepoint 时，不只选最近 home boundary；
  - home boundary 候选点应同时考虑距离、ghost 距离、是否 chokepoint、队友是否占用同一路线；
  - 有 capsule 且 ghost 威胁近时，允许先转 capsule 再回家。
- 加强 bloxCapture 上的协作分工：
  - 一个 agent 携带或回家时，另一个 agent 优先 patrol/defence 或覆盖另一侧通道；
  - 避免两个 agent 同时挤进同一个狭窄入口；
  - 队友 `go_home` 时，留守 agent 可偏向 home boundary 附近接应，而不是继续深入同一路径。

下一轮调参验收矩阵：

- 每个候选改动先跑 bloxCapture 正向 `10` 局，目标从 `5/10` 提升到至少 `7/10` 或平均分明显转正。
- bloxCapture 若改善，再跑 bloxCapture 红蓝互换 `10` 局，确认不是单边地图偏差。
- 回归 defaultCapture 正向与红蓝互换，各 `10` 局必须保持稳定胜率。
- 回归 strategicCapture `10` 局，避免防守/巡逻权重影响开阔地图表现。
- 最后回归 RANDOM23/RANDOM42 各 `49` 局和 `-c` 时间限制测试；随机地图胜率不能因为 blox 专项优化明显下降。

## Phase 7: 补全 Q-learning 低层规划器

目标是在不影响 HS 主路径的前提下,把模板中未完成的 Q-learning 低层规划器补全,使其可训练、可切换。

工作内容:

- 补全 `getDefensiveReward()`:
  - 每步小额生存代价
  - invader 减少给大奖励
  - 靠近最近可见 invader 给小奖励
  - 防守 food 被吃、被吃回出生点给惩罚
- 补全 `getEscapeReward()`:
  - 每步小额生存代价
  - 成功带 food 回家给大奖励
  - 靠近 home boundary 给小奖励
  - 回家路上被吃回出生点给大惩罚
- `getLowLevelPlanQL()` 复用 `getLowLevelMode()` 的 high-level action 到 mode 的映射,三个分支(offensive/escape/defensive)学习率统一启用 `self.alpha`
- QL 规划后同样更新 `sharedModes` / `sharedTargets`,保持队友协作信息一致
- `chooseAction()` 增加 `self.useQLearning` 开关:
  - `False`(默认)走原 HS 低层
  - `True` 走 QL 低层,每步选一个动作
  - 训练权重时把 `trainning` 和 `useQLearning` 同时设为 `True`

完成标准:

- `trainning = False` 时行为与 Phase 6 版本一致,HS 回归测试不退化
- `trainning = True` 时能完整跑完训练局,权重正常更新并写入 `QLWeightsMyTeam.txt`
- 不再出现 "DefensiveReward not implemented" / "EscapeReward not implemented" 警告
- 提交版本保持 `trainning = False`、`useQLearning = False`

本轮 Phase 7 实验结果（详见 record.md 2026-06-12）：

- 三个 mode 的 reward 均已实现并改为 delta 形式：每步 `-1` 生存代价，吃 food / 交 food / 追到 invader 给正奖励，被吃回出生点给大惩罚，不再有 `-50` 每步的大常数项。
- 修复 `updateWeights()`：correction 用旧权重在循环外只计算一次，并裁剪到 `±100`；跨越边界（isPacman 变化）视为 episode 结束，不再 bootstrap 下一状态价值。修复前 defensiveWeights 曾发散到 `1e+49` 量级，修复后训练稳定在百量级。
- 距离类 feature 统一除以 `(walls.width + walls.height)` 归一化；`chance-return-food` 已改用 home boundary 而非出生点。
- 删除旧权重文件后从手写初值重训：红方 50 局 + 蓝方 50 局（RANDOM 地图），训练管线稳定、可跨局续训。
- 训练时加入 teacher-guided 采样：`teacherProb = 0.8` 概率跟随 HS 规划器的动作（off-policy 学习 teacher 轨迹），其余按 epsilon-greedy 探索。
- 纯 QL 全模式评估（`trainning = False`、`useQLearning = True`）在 defaultCapture 10 局全部平局，平均分 `0.0`，远弱于 HS 基线的 `10/10` 胜。
- 结论：训练管线正确但策略强度不足，线性特征 + 单步贪心追不上 A* 规划。提交版本保持 `useQLearning = False`。

## Phase 8: Q-learning 局部增强（hybrid 低层）

背景与定位：

- Phase 6/7 之间的 bloxCapture 收敛实验已把该图修到正反向各 `10/10`（靠 defence 释放协作分工，不是靠 QL），HS 主路径目前没有明显弱图。
- 因此 Phase 8 的目标**不是**用 QL 修某张图，而是回答一个更小的问题：QL 在它最有机会的两个 mode（`attack`、`go_home`）上，能否在不拖累 HS 整体表现的前提下达到可用强度。
- 已验证全模式纯 QL 远弱于 HS，所以本阶段只做局部接入，defence / patrol 一律保持 HS，不再尝试全盘替换。

### Phase 8.1: hybrid 模式路由

- 把单一 `useQLearning` 布尔开关改为按 mode 路由，例如 `self.qlLowLevelModes = {"attack", "go_home"}`：
  - `getEffectiveLowLevelMode()` 结果落在集合内时走 `getLowLevelPlanQL()`；
  - 否则走 `getLowLevelPlanHS()`。
- 集合为空等价于现在的 `useQLearning = False`，保证提交版行为可完全回退。
- 共享状态（`sharedModes` / `sharedTargets`）两条路径都要更新，保持队友协作信息一致（QL 路径已有，确认 hybrid 切换时不遗漏）。

### Phase 8.2: 补 3 个 offensive feature

只加以下 3 个，不再多加（feature 多了调不动）：

- `carrying`：`numCarrying / 10.0`，让 QL 直接知道当前背了多少 food（`chance-return-food` 是乘积项，单独的 carrying 信号更直接）。
- `ghost-distance`：到最近危险 ghost 的归一化距离（无 ghost 时取 1），比只有 `#-of-ghosts-1-step-away` 提前感知威胁；期望权重为正。
- `dead-end`：下一格 legal neighbor 数 `<= 2` 时为 1，让 QL 有机会学到“带 food 且 ghost 近时别钻窄道”。

注意：

- 不需要再加 `distanceToHome`（offensive 的 `chance-return-food` 已用 home boundary；escape 已有独立的 `distanceToHome`）。
- 新 feature 初始权重从 0 开始（`util.Counter` 默认），靠续训学出来，不手写大初值。

### Phase 8.3: 续训

- 在现有 teacher-guided 管线上续训，不删除当前 `QLWeightsMyTeam.txt`（这份权重已经是修复 updateWeights 之后训出来的，起点可靠）。
- 先红方 50 局再蓝方 50 局（RANDOM 地图），训练中确认新 feature 权重方向符合预期（`ghost-distance` 为正、`dead-end` 为负）。
- 训练结束必须把 `trainning = False`；`final()` 写权重和 `score` 文件的副作用按惯例还原。

### Phase 8.4: 评估顺序与验收

评估时固定 `trainning = False`、`qlLowLevelModes = {"attack", "go_home"}`：

1. 接口检查：`python capture.py -r myTeam.py -b staffTeam.py -q -n 1`
2. defaultCapture 正向 10 局
3. bloxCapture 正向 10 局
4. bloxCapture 红蓝互换 10 局
5. 以上不退步才跑 RANDOM23 / RANDOM42 各 49 局和 `-c`

验收标准（以 record.md 中 HS 基线为对照）：

- hybrid 版在 defaultCapture / bloxCapture 正反向不得低于 HS 的 `10/10`；
- RANDOM23 / RANDOM42 胜率不得明显下降；
- 任一条不满足，提交版回退 `qlLowLevelModes = set()`（即纯 HS），QL 仅作为作业报告中的训练实验展示。

明确不做的事（已评估过，避免回头重做）：

- 不把 reward 改回大常数项或重做 reward shaping —— Phase 7 已完成 delta 形式。
- 不改回“只更新选中 action”—— 当前对所有 legal action 更新是刻意设计（每步多个学习样本），配合 correction 裁剪和 episode 边界处理后训练无发散。
- 不重置权重重训 —— 旧坏权重（bias ≈ -479 那份）已在 Phase 7 删除重训过。
- defence / patrol 不接 QL。

本轮 Phase 8 实验结果（详见 record.md 2026-06-13）：

- 8.1 / 8.2 已实现：`qlLowLevelModes` 集合路由 + 3 个新 offensive feature + 旧权重文件 merge 兼容。
- 8.3 续训完成：红蓝各 50 局 RANDOM，训练期各 41/50 胜（hybrid 下 defence/patrol 走 HS，训练局本身稳定），权重无发散；`dead-end ≈ -1.4` 方向正确，`ghost-distance` 收敛到 0。
- 8.4 验收不通过：hybrid（attack+go_home 接 QL）在 defaultCapture `0/10`，10 局全部 `0-0` 平局；隔离实验 attack-only QL 仍 `0/10` 全平，说明瓶颈是单步贪心线性 QL 进攻完不成得分闭环，不是 escape 权重单独的问题。
- 已按验收规则回退提交版 `qlLowLevelModes = set()`：回退后 defaultCapture / bloxCapture 回归均 `10/10`、平均 `+7.0`，与 HS 基线一致。
- 最终结论：QL 保留为代码内可开关的训练实验（报告素材），比赛策略走纯 HS；提交前确认 `trainning = False`、`qlLowLevelModes = set()`。

## Phase 9: Q-learning 确诊与分布修正

背景与动机：

- Phase 8 验收失败的关键证据是 10 局比分全部**精确为 0-0**：`shouldReturnHome()` 的 handoff 已经很激进（`carrying > 0` 且危险 ghost 近距离就交回 HS 回家），但我方 10 局没有送回过任何一颗 food——哪怕送回 1 颗都会是 1-0。
- 主要嫌疑：单步贪心 QL 过不了被防守的边界。ghost 一近就触发 go_home 被 HS 拉回安全区，切回 attack 又凑上去，在边界无限横跳，根本进不了敌方半场；这与"吃 1-2 颗被抓"是不同的病，治法不同。
- 因此本阶段第一步是确诊，不是改算法。

### Phase 9.0: 先确诊，不改算法

- 加只读诊断计数器（`self.qlDiagnostics` 开关，对行为无任何影响），每局 `final()` 打印：
  - `maxCarrying`：本局最大携带数
  - `foodEaten`：累计吃到 food 数
  - `deaths`：死亡（被吃回出生点）次数
  - `maxDepth`：进入敌方半场的最大深度（到 home boundary 的迷宫距离）
  - `boundaryDither`：attack 模式下停留在己方边界 3 格内的步数
  - `modeSwitches`：低层 mode 切换次数
- 跑 attack-only QL（`qlLowLevelModes={"attack"}`）defaultCapture 3 局 + 纯 HS 对照 3 局，对比计数器。
- 判定规则：
  - `boundaryDither` 远高于 HS 且 `maxDepth` 很小 → "进不去"，主修 9.2a；
  - `foodEaten > 0` 但 `deaths` 高、`maxCarrying < 3` → "进去就死"，主修 9.2b；
  - `maxCarrying >= 3` 但仍不得分 → handoff/escape 问题（目前证据不支持，留作分支）。

### Phase 9.1: teacher 衰减（DAgger 思路）

- `teacherProb` 不再固定 `0.8`：从 `0.9` 随训练局数线性衰减到 `0.1`，训练局数 `trainedEpisodes` 持久化在权重文件里。
- 动机：固定 0.8 意味着 QL 学到的 Q 值只在"老师会到达的状态分布"上准确；评估时贪心策略一走偏就进入没训练过的分布。训练后期让 QL 越来越多走自己的策略、经历自己的死亡。

### Phase 9.2: 按确诊结果做 feature 手术（最多 2 个改动）

- 9.2a "进不去"：加二值进度特征 `moves-toward-food`（这步是否缩短到最近 food 的迷宫距离）。二值进度特征对"原始距离特征与回报相关性纠缠导致符号学歪"更鲁棒（escape 的 `distanceToHome` 学成 +595 即此症状）。
- 9.2b "进去就死"：把已收敛为 ≈0 的 `ghost-distance` 换成 `ghost-nearby`（迷宫距离 `<= 3` 的二值）；连续距离太平滑，线性模型学不出"3 格内危险陡增"的非线性。
- 无论哪种：删掉 `successorScore`（学到 -1.5 符号反，纯噪声）。
- 一轮只做一类手术，保证 A/B 可归因。

### Phase 9.3: 带检查点的续训

- 每训练 50 局（红蓝各 25），用 `trainning = False` 的 attack-only 配置跑 defaultCapture 10 局做检查点评估并记录平均分。
- 连续两个检查点没有提升即停（平台期），不盲目加局数。

### Phase 9.4: 分级验收

- L1：attack QL 能稳定得分——defaultCapture 10 局平均分 `> 0`，告别全平局。达到即满足作业报告目标。
- L2：hybrid 在 defaultCapture / bloxCapture 正反向不低于 HS 的 `10/10`——才考虑作为提交配置，且仍需走 Phase 6 验收矩阵。
- L3：不设"超过 HS"为目标（线性单步贪心 vs A* 规划的差距不指望靠调参填平）。
- 无论结果如何，提交版默认保持 `qlLowLevelModes = set()`、`trainning = False`、`qlDiagnostics = False`，除非 L2 全部通过。

明确不做：经验回放、n-step return、神经网络——工程与解释成本超出作业范围，且不解决单步贪心的根本差距。若 9.0 确诊为"进不去"且 9.2a 无效，备选方向是把 Q 值改作 A* 边代价（另立 phase 评估，不在本轮范围）。

本轮 Phase 9 实验结果（详见 record.md 2026-06-13）：

- 9.0 确诊成功：病灶是「进不去」+ Stop 吸收态——守界鬼在过界格制造 -10 惩罚墙，而 `stop` 权重学成正数，使 agent 在边界格整局罚站（Q 值分解实锤）。
- 9.2 实际做了两轮手术：轮次 1 按计划（`moves-toward-food` + 删 `successorScore`）；轮次 2 由检查点 1 的 Q 值证据驱动（QL 排除 Stop + `revisit` 特征）。
- 9.1 的 teacher 衰减地板 0.1 引发自走毒化事故（检查点 3 全输，权重崩坏），提高到 0.3 后修复——衰减下限本身成为关键超参。
- 检查点曲线：0.0 → 2.1 → -8.4(回滚) → 5.0 → 6.3 → **10.0(峰值)** → 3.5 → 8.5，按连续两次无提升停训，采用 ckpt6 权重。
- 验收：L1 大幅超额（attack-only QL 在 default/blox/strategic 全部 10/10 且平均分超 HS）；L2 失败于 RANDOM23（24/49 vs HS 49/49），线性特征对随机地图族泛化差。
- 按预设规则提交配置回退纯 HS（`qlLowLevelModes = set()`），回退后 defaultCapture 回归 10/10、+7.0 与基线一致。ckpt6 权重保留在 `QLWeightsMyTeam.txt` 作为报告素材。

## Phase 10: QL 作为路径偏好（QL-guided A*）

背景与动机：

- Phase 9 的关键证据：attack-only QL 在固定图（default/blox/strategic）全部 10/10 且均分超 HS，但 RANDOM23 仅 24/49（HS 49/49）。QL 不是弱在"不会进攻"，而是弱在单步贪心线性模型对随机地图族泛化差；A* 的泛化能力仍然更强。
- 这正是 Phase 9"明确不做"里预留的备选方向：**把 Q 值改作 A* 边代价**。本阶段反转 QL 与 A* 的角色——不再问"QL 能不能单独决定下一步"，而是问"QL 能不能帮 A* 在多条可行路中选更好的那条"。
- 框架保持纯 HS：目标选择、A* 搜索、模式切换全部不变；ckpt6 训练出的 offensive Q 值只作为 attack 模式 A* 的局部代价修正项（路径偏好）。QL 判断错时 A* 仍然兜底，不会丢掉随机地图的稳定性。

### Phase 10.1: flag 控制的 QL-guided A*（不重训）

- 开关：`self.qlGuidedAStar`（提交默认 `False`，off 时 `boundedAStarToTargets` 与纯 HS 行为完全一致）、`self.qlPathLambda = 0.03`、`self.qlPathCap = 1.0`。
- 注入点在 `boundedAStarToTargets` 而非 `getSearchStepCost`：相对归一化需要整个兄弟动作集合（后者一次只看一条边）；且 `getFallbackActionScore` 也调用 `getSearchStepCost`，改它会污染 fallback 评分。
- 代价形式用**每次扩展的相对归一化**而非裸减法 `cost - λQ`：对被扩展节点的所有合法后继算 q，附加代价 `min(cap, λ·(maxQ - q))`。恒非负 → 无"负代价偏好长路径"伪影，Manhattan 启发式保持低估；局部最优兄弟恰好付 0；单出口走廊零开销。
- 搜索时 Q 适配器 `getQLPathValue`：逐项镜像 `getOffensiveFeatures` 的语义和归一化（权重必须在训练分布上使用），但只保留对 A* 内部有意义的子集：
  - 保留 `eats-food`、`eats-capsule`、`#-of-ghosts-1-step-away`、`ghost-distance`、`dead-end`、`revisit`、`chance-return-food`（仅 carrying>0）。
  - 丢弃 `stop`/`reverse`（A* 内不适用）、`closest-food`/`moves-toward-food`（A* 启发式 + progress bonus 已驱动向 HS 选定目标推进，"最近 food"拉力会与选定目标打架——即"靠近合理目标而非最近 food"的意图，无需重训实现）、`bias`/`carrying`（兄弟间常数，在 maxQ−q 下抵消）。
  - ghost 集合用 `getGhostLocs`（含 scared ghost），与训练一致；scared 安全规避仍由 HS 层 `getVisibleDangerousGhosts` 惩罚负责。
  - 保留特征只依赖 nextPos，按 nextPos 记忆化，每次 A* 调用建一次 context 快照。
- λ 量级：兄弟 q 差主导项是 `eats-food`（≈28.4）→ 0.03×28.4 ≈ 0.85 < 1 步基础代价；QL 只做 tie-breaker，远小于 HS ghost 惩罚（3~100）。

### Phase 10.2: 地图结构特征（条件触发，暂不实现）

仅当 10.1 验收通过或作为报告素材需要时再做：

- `home-path-margin`：回家路是否会被鬼掐断的近似（max over 边界点 b 的 `mazeDist(ghost,b) − mazeDist(pos,b)`，归一化）。
- `entry-flexibility`：是否身处长单出口走廊（`registerInitialState` 时静态预计算 tunnel-depth 图）。
- 两个特征需同时加进 `getOffensiveFeatures`（训练路径）与 `getQLPathValue`（推理路径），并重训（快照权重 → `trainning=True`、`qlLowLevelModes={"attack"}`、Phase 9.3 检查点规则）。

### Phase 10.3: 验收标准

1. flag off 时与纯 HS 行为等价（defaultCapture 回归与基线一致）；
2. flag on 时 RANDOM23 / RANDOM42 不得低于 HS 基线（49/49）——RANDOM23 为约束性验收，首跑；
3. default / blox / strategic 正反向保持 10/10，均分不低于 HS 基线；
4. 任一条不满足：先做 λ∈{0.01, 0.1} 扫描；扫描后随机图仍下降则提交版保持 `qlGuidedAStar = False`，QL-guided A* 仅作为报告实验。

明确不做：

- go_home / defence / patrol 不接 QL 引导（escape 权重病态：`distanceToHome ≈ +352`，不能泄漏进路径代价）。
- 10.1 不重训、不改 reward、不动 `getSearchStepCost` 既有惩罚结构。
- 不上经验回放、n-step return、神经网络（同 Phase 9 结论）。

本轮 Phase 10 实验结果（详见 record.md 2026-06-13）：

- 10.1 已实现并完成完整验收矩阵。核心假设验证成功：**RANDOM23 49/49（+9.47）、RANDOM42 49/49（+9.47）**，随机图泛化完全无损（Phase 9 纯 QL 在 RANDOM23 仅 24/49）——QL 作为有界附加代价时 A* 的全局路径能力完整保留。
- 固定图胜率全部 10/10；defaultCapture 双向均分明显提升（正向 +8.0 vs 同日对照 +6.0，反向我方 +12.0 vs +7.5）；strategicCapture 与同日对照持平；bloxCapture 正向均分稳定下降 ~1.5（+5.5/+5.4 两次复跑 vs 对照 +7.0，窄道图里顺路吃豆偏好引向局部绕行）。
- 验收：标准 1、2 通过；标准 3 胜率全通过但 blox 正向均分低于基线，严格执行 → 不完全达标，**提交默认值保持 `qlGuidedAStar = False`**。QL-guided A* 作为验证过的实验保留，单开关可启用。
- 若做 10.2，窄道图均分回退是首要修复目标。

本轮 Phase 10.2 实验结果（详见 record.md 2026-06-13）：

- 已实现 `home-path-margin` + `tunnel-depth`（训练/推理双路径一致，`computeTunnelDepthMap` 静态预计算 2-core + 多源 BFS），重训 3 轮（每轮红蓝各 25 局 RANDOM，trainedEpisodes 重置 50 起步），按停训规则在 ckpt3 停止。
- 检查点呈跷跷板：blox +7.0/+5.5/+7.0 对 default +4.0/+8.0/+3.0，无检查点同时达标。
- 消融归因（关键结论）：**blox 修复来自重训的基础权重再平衡，与结构特征无关**；两个结构特征学到的都是混淆符号（margin 负、tunnel 正，与 Phase 9 `distanceToHome` 同病）、只有害，`home-path-margin` 是 default 回退的主毒。
- 最优配置（结构特征清零）= 处处中性：blox +7.0、default +6.0 均持平基线——修了 blox 但吐掉 10.1 的 default 收益，净收益为零。
- **提交配置不变（纯 HS，`qlGuidedAStar = False`）**，权重还原 ckpt6。10.2 价值在报告：实证线性 QL 的结构特征被回报相关性毒化，连续两个 phase 的证据共同指向"学习偏好可注入但需非线性表达或更干净的特征设计"。
- 事故与教训：批内 `conda run` 不转发 heredoc stdin 导致一次评估污染（已靠轮间快照完全恢复）；快照纪律再次救场。

## Phase 11: Context-gated QL-guided A*

背景与动机：

- Phase 10.1 已证明：QL 作为有界附加代价注入 attack A* 时，随机图泛化完全无损（RANDOM23/42 49/49），且 defaultCapture 双向均分明显提升（+8.0 / 我方 +12.0）；唯一遗留问题是 bloxCapture 正向均分稳定下降 ~1.5（+5.5/+5.4 vs 基线 +7.0）。
- Phase 10.2 已证明：靠"让 QL 学结构特征 + 重训"修 blox 走不通——结构特征被回报相关性毒化，重训再平衡虽修 blox 但吐掉 default 收益，净收益为零。
- 因此 Phase 11 换路线：**不动权重、不重训、不加 feature**，只在推理侧给 QL 注入加"何时闭嘴"的门控——QL 偏好在开阔、低风险场景保留，在窄道等它已被证明添乱的场景关闭。核心问题：**能否在不丢 default 收益和随机图 49/49 的前提下，把 blox 正向均分恢复到基线 +7.0？**
- 全部改动限定在 `boundedAStarToTargets` / `buildQLPathContext` 的推理路径上，`getSearchStepCost`、训练管线、`QLWeightsMyTeam.txt`（ckpt6）一律不动。flag off 时行为仍与纯 HS 完全等价。

### Phase 11.0: 先确诊 blox 绕行的元凶 feature（不改算法）

沿用 Phase 10.2 的消融方法：在 `buildQLPathContext` 的权重快照里逐个清零候选 feature，跑 bloxCapture 正向 ×10（flag on，ckpt6 权重），对比 +5.5 基准。

候选嫌疑（按先验排序）：

1. `eats-food`（≈ +28.4，顺路吃豆拉力，GPT 讨论的默认嫌疑）；
2. `revisit`（ckpt6 为 -1.69；10.2 重训降到 -0.48 后 blox 自愈，是同等分量的嫌疑）；
3. `dead-end`（≈ -1.4，会让 A* 在窄道入口付附加费）；
4. `chance-return-food`（carrying>0 时的回家拉力，可能与 HS 选定目标打架）。

判定规则：

- 某个 feature 清零后 blox 恢复到 ≈ +7.0 → 它就是主毒，11.1 的门控设计以"在窄道场景屏蔽该信号"为目标；
- 单清都不恢复、组合清零才恢复 → 说明是窄道里整体 q 差被放大，11.1 直接走 tunnel 门（整个扩展关 QL）；
- 全清都不恢复 → 归因不在 QL 项本身，回到 10.1 数据复查（此分支概率低，因为 10.1 消融链已指向 QL 项）。

确诊轮也要顺带跑一次 defaultCapture ×10，确认被清的 feature 是否同时是 default 收益的来源——如果同一个 feature 既是 blox 的毒也是 default 的药，就实锤了"必须按上下文门控、不能全局删"的设计前提。

### Phase 11.1: 二值门控（一次只开一扇门，A/B 可归因）

门控分两个注入粒度，分开实验，不混做：

- **G1 tunnel 门（per-expansion）**：扩展节点 `pos`（或其任一后继）的 `self.tunnelDepth > 0` 时，本次扩展 `qlPenalty = {}`。复用 Phase 10.2 留下的 `computeTunnelDepthMap` 静态预计算，零额外开销。语义：QL 偏好只在开阔区域的兄弟动作间起作用，进入单出口走廊体系后 A* 完全按 HS 代价走。
- **G2 carrying 门（per-search）**：`carrying >= 2` 时本次搜索 λ = 0（在 `buildQLPathContext` 判一次）。语义：没带豆时允许 QL 鼓励顺路吃豆；带豆后目标是安全回家，吃豆偏好不再参与。注意 `carrying >= 3` 本来就触发 go_home（不走 QL 引导），所以 G2 实际只影响 carrying 为 2 的窗口，预期是小修正。

约束：

- 门是二值的（λ = 0.03 或 0），不做多档 λ——多档位引入新调参维度，破坏 A/B 归因。
- 实验顺序：先 G1 单独（首要假设），blox ×10 + default ×10；若 blox 恢复且 default 收益保住，G2 不做；若 blox 只部分恢复，再叠加 G2。
- 每轮改动后先跑 flag-off 回归 ×3 确认等价性没被破坏（门控代码必须包在 `qlGuidedAStar` 分支内）。
- "ghost 压迫 home boundary 时关 QL"（GPT 讨论提过）暂不做：该场景主要影响 go_home，而 go_home 从未接 QL 引导；attack 模式下 ghost 近身时 `getSearchStepCost` 的 3~100 量级惩罚本来就碾压 cap=1.0 的 QL 项。

### Phase 11.2: 验收矩阵（全部以同日 flag-off 对照为准，沿用 10.1 口径）

固定 `trainning=False`、`qlLowLevelModes=set()`、ckpt6 权重，候选配置 = flag on + 胜出的门控组合：

1. flag-off 回归：defaultCapture ×10 与纯 HS 行为等价；
2. bloxCapture 正向 ×10：均分恢复到同日 flag-off 对照水平（≈ +7.0），这是本阶段首要指标，先跑；
3. defaultCapture 正反向 ×10：保住 10.1 的均分收益（明显高于同日 flag-off 对照，量级参考 +2.0 / +4.5）；
4. bloxCapture 反向 ×10、strategicCapture ×10：不低于同日对照；
5. 以上全过才跑 RANDOM23 / RANDOM42 各 ×49：必须 49/49；
6. `-c` 计时 ×10：无超时判负。

决策规则：

- 全部通过 → `qlGuidedAStar = True` 首次具备成为提交默认值的资格（此前 10.1/10.2 均未达标），最终是否启用在提交前确认；
- 标准 2 失败且 11.1 两扇门用尽 → 做一次 λ ∈ {0.01} 的窄道场景外全局缩小扫描（最后一招）；仍失败则提交默认保持 `qlGuidedAStar = False`，Phase 11 作为报告中"门控假设的否定性实验"收尾；
- 标准 3 失败（门控误伤 default 收益）→ 检查门是否开得过宽（如 tunnel 门误盖开阔图的短走廊），收紧后重测一轮，仍失败同上回退。

明确不做：

- 不做"先生成 K 条候选路径再用 QL 排序"的 tie-break 架构重构——现有 per-expansion 相对归一化 + cap 已把 QL 限制在近似 tie-breaker 的量级（λ·maxΔq ≈ 0.85 < 1 步基础代价），若二值门控足以修复 blox，则没有理由支付该工程与验证成本；仅当 11.1 + λ 扫描全部失败且仍想保留 QL 引导时，另立 phase 评估。
- 不重训、不动 ckpt6 权重文件、不加/删训练 feature（10.2 的教训：训练侧动结构特征只会学到混淆符号）。
- 不做多档 λ、不做连续 gating 函数——保持二值门的可归因性。
- go_home / defence / patrol 继续不接任何 QL 信号（escape 权重病态结论不变）。

实验纪律（沿用 9/10 的教训）：

- 本阶段不写权重，但凡跑训练相关命令前仍必须快照 `QLWeightsMyTeam.txt`；
- 批内 flag 翻转用系统 `python3` heredoc 并在评估启动前 `grep` 验证生效（conda run 不转发 heredoc stdin 的事故不能重演）；
- 需要看 agent stdout 的诊断局用 `-q`，批量评估用 `-Q`。

本轮 Phase 11 实验结果（详见 record.md 2026-06-13）：

- 11.0 确诊成功且改写结论：消融矩阵实锤 `eats-food`（+28.4）是 blox 绕行唯一主毒——推理侧清零后 blox 从 +5.3 恢复到 +8.6，且**反超** flag-off 基线 +7.0；`revisit` 是次要毒源（清零 +7.4），`dead-end` / `chance-return-food` 无关。全清零对照精确复现 flag-off 的 +7.0，消融机制自验证通过。
- 重要副产物：**10.1 记录的 default 收益（+8.0/+12.0）被 n=50 大样本证伪为采样噪声**——default 比分呈 1/11 双峰，n=10 均分差 ±2 在噪声内；n=50 下 flag-off/方案 A/方案 B 的高分局率 56%/52%/44% 统计不可区分。
- 11.1 方案判别（n=50 each）：只剔 `eats-food`（blox +8.68 / default 中性）vs 剔 `eats-food`+`revisit`（blox +9.08 / default 偏低）——blox 差异 1 SD 不可区分，default 偏向前者，**采用最小改动方案：从 `getQLPathValue` 永久剔除 `eats-food`**（与 `closest-food` 同属"与 HS 选定目标打架"失败族）。原计划的 tunnel/carrying 门控**不需要了**：剔除后处处不低于基线，无需上下文条件。
- 11.2 验收 8/8 全通过：blox 正向 +9.0（>7.0 基线）、blox 反向我方 +8.2、default 正向 +7.5（n=20）、default 反向我方 +12.0（n=20）、strategic +6.1、**RANDOM23 49/49 +9.47**、RANDOM42 49/49 +9.94、`-c` 10/10 无超时——**`qlGuidedAStar = True` 首次通过全部验收标准，具备提交默认资格**。
- 修正后的最终叙事：QL-guided A* 的真实收益在窄道图（blox +7.0 → +9.0），default/strategic 中性，随机图泛化无损；保留的 QL 信号是 ghost 邻近、dead-end、revisit、带豆回家拉力——一个风险感知 tie-breaker，而非吃豆引导。
- 工具沉淀：`QL_PATH_ABLATE` 环境变量消融开关保留在代码中（默认空集、零行为影响），避免了批间翻转文件 flag 的事故面。
- 提交 flags：`trainning=False`、`qlLowLevelModes=set()`、`qlDiagnostics=False`、`qlGuidedAStar=True`（首次默认启用）；ckpt6 权重未动。

## Phase 12: QL Risk Residual Refinement（风险残差精化）

背景与定位：

- Phase 11 已把 QL 的角色定死：**风险感知 tie-breaker**——A* 负责全局路径，HS/PDDL 负责目标选择，QL 只在兄弟动作间回答"哪条路更危险"，不回答"该不该吃这颗豆"。本阶段不再动这个定位，只回答一个问题：**当前风险信号是"刚刚好"还是"太弱"？能否在不伤随机图 49/49 的前提下，把风险判断质量再提一档？**
- 关键代码事实（设计前提，已核对 ckpt6）：`QLWeightsMyTeam.txt` 里**没有** `home-path-margin` / `tunnel-depth` 的权重条目，`getQLPathValue` 中这两段是恒为 0 的死路径。当前实际生效的信号只有 6 个：`eats-capsule`(+6.06)、`#-of-ghosts-1-step-away`(-4.98)、`ghost-distance`(-0.24, 归一化后量级很小)、`dead-end`(-2.01)、`revisit`(-1.69)、`chance-return-food`(+13.59×carrying×归一化回家进度)。
- 推论：任何新风险特征都**不可能从 ckpt6 白拿权重**。推理侧加入 = 手设权重的 shaped risk prior（不是学到的 Q）；要学权重就必须续训。这个区别在每个子阶段里都要诚实标注，不能混淆叙事。
- 预期管理：Phase 11 配置已具备提交资格，本阶段是提交前 refinement，收益预期为小幅；**Phase 11 状态始终是回退点**，任何一步失败直接回退，不抢救。若 12.1/12.2 全部中性，Phase 12 以"现有风险信号已饱和"的否定性结论收尾——对报告同样有价值。

### Phase 12.0: 基线封存与死代码清理（不跑新实验）

- 把 Phase 11 终态打 git tag（或记录 commit hash）作为本阶段唯一对照基线，封存基线数字：blox 正向 +9.0 / 反向 +8.2、default +7.5 / +12.0（n=20）、strategic +6.1、RANDOM23 49/49 +9.47、RANDOM42 49/49 +9.94。
- 报告叙事统一更名：不再叫 hybrid QL，不再说"QL 替代低层"，统一为 "QL = risk-aware tie-breaker for A*"。
- 可选清理：`getQLPathValue` / `buildQLPathContext` 里 `home-path-margin` 的计算（每个 boundary point 一次 `getMazeDistance`）在 ckpt6 下纯属浪费算力，可加 `weight != 0` 守卫或直接删除；改完跑 flag-on defaultCapture ×3 确认逐位等价（权重为 0，行为不应有任何变化）。此项不强制，但若做 12.3（需要重搜预算）建议先做。

### Phase 12.1: λ 小扫描（最轻，先做）

当前 `qlPathLambda = 0.03`、`qlPathCap = 1.0`。Phase 11 剔除 `eats-food` 后 QL 项的毒性已大幅降低，值得确认 0.03 是不是仍然最优。

- 实现：仿照 `QL_PATH_ABLATE` 加环境变量 `QL_PATH_LAMBDA` 覆盖（默认不设时行为逐位不变），杜绝批间翻文件 flag 的事故面。
- 扫描：λ ∈ {0.01, 0.02, 0.05}，cap 固定 1.0，**不动任何其他参数**。
- 回答三个问题（不是找最高均分）：λ 变小后 blox +9.0 是否保得住（信号是否本来就在起作用）；λ 变大后 RANDOM23 是否仍 49/49（信号还能不能更强）；default 是否仍只是中性波动。
- 流程：每档先 blox 正向 ×10 smoke（只筛明显坏配置，均分差 < 2 不算信号）；幸存档跑 blox n=30~50 + default n≥20；唯一候选档在采纳前必须过 RANDOM23 ×49 = 49/49。
- 决策：0.05 无损随机图且 blox 不低于 +9.0 → 说明 tie-breaker 还有加强空间，采纳 0.05 并为 12.2 留出解释（信号偏弱）；任何档与 0.03 不可区分 → **保持 0.03（无改动默认胜出）**；0.05 伤随机图 → 实锤"当前强度刚刚好"，记录后进入 12.2。

### Phase 12.2: 二值风险事件特征（最多 2 个，推理侧先行，一次只加一个）

Phase 10.2 的教训：连续结构特征（`home-path-margin`、`tunnel-depth`）训练后符号被回报相关性污染——food 常在深处/窄道，线性 QL 把危险结构学成好结构。本阶段改用**二值风险事件**：更粗糙，但符号不易学反（Phase 9 中二值的 `moves-toward-food` 比原始距离特征鲁棒，是同一先验）。

候选（按优先级，第 3 个仅在前两个都失败时考虑）：

1. **`home-cut-risk`**：carrying > 0 且 `max_b (ghostBoundaryDist[b] - myDist(nextPos, b)) <= 1` → 1。语义：所有回家出口的安全余量都被压到 ≤1，即 ghost 能在任何 boundary 截住我。本质是 `home-path-margin` 的二值化，**直接复用 `buildQLPathContext` 现成的 `ghostBoundaryDist` 预计算，零新增基础设施**。
2. **`tunnel-with-ghost-risk`**：`tunnelDepth[nextPos] > 0` 且可见 ghost 距该位置 ≤ CLOSE_DISTANCE → 1。语义：ghost 在附近时进入单出口走廊体系。复用 `computeTunnelDepthMap` 静态预计算。
3. `revisit-under-pressure`（备选）：nextPos ∈ recentSet 且（ghost 可见或 carrying > 0）→ 1。与现有 `revisit` 重叠度高，预期增量最小。

权重来源（诚实分两步，不混叙事）：

- **12.2a 推理侧手设权重**：量级对齐现有风险信号（参考 `dead-end` ≈ -2，初值取 -2，不扫多档），用 `QL_PATH_ABLATE` 同款环境变量开关做 A/B。明确标注：这是 shaped risk prior，不是学到的 Q——报告里如此陈述。
- **12.2b 轻量续训学权重（仅当 12.2a 显著有效才触发）**：把胜出特征加进 `getOffensiveFeatures` 续训，teacher floor 不低于 0.3（Phase 9 教训：floor=0.1 时自走经验被边界僵局污染毒化权重）、训练前快照权重、每轮存 checkpoint、训练分布 = RANDOM 为主 + 固定图少量混入、每轮只看一个主指标。**验收唯一标准：学出的符号必须为负且续训后整个验收矩阵不低于 12.2a 手设版**；学反了就回退手设版，不二次抢救。

前置诊断（先做，避免做冗余功）：

- `getSearchStepCost` 已有 ghost 距离 3~100 量级的 hard penalty + chokepoint 惩罚，碾压 cap=1.0 的 QL 项。新特征必须证明在 **hard penalty 未触发的区间**（ghost 距离 > CLOSE_DISTANCE、或 margin 将塌未塌时）提供增量信息。
- 方法：先加 diagnostic counter（`qlDiagnostics` 通道）统计每个候选特征在 blox / RANDOM23 上的触发率，以及"触发时 hard penalty 是否同时触发"的重叠率。触发率 < 1% 或重叠率 > 90% 的特征直接弃，不进 A/B。

验收（每个特征独立过关）：blox 正向 n=30 不低于 +9.0、default n≥20 中性、RANDOM23 ×49 = 49/49。任何特征伤随机图 → 直接弃，**不调权重抢救**（避免引入新调参维度）。

### Phase 12.3: 路径段风险评估（条件触发，最具研究味，默认不做）

动机：Pacman 的风险常在几步之后才暴露（过界后被两鬼合围、进窄道后无回头路、带豆深入回不来），单步 Q 值看不到。这是"step-level → segment-level risk"的叙事升级。

**触发条件（满足其一才立项，否则跳过）**：12.1 显示 λ 加大有收益但被随机图卡死（信号强度到顶、需要换粒度）；或 12.2 的特征在"延迟暴露型风险"场景（blox 反向、带豆深入局）仍然无效。

机制草图（保持 QL 不改目标的铁律）：

```text
attack A* 返回路径后，对前 K=3~5 步累加 getQLPathValue（已 memoized，近零开销）；
段风险超阈值 → 对该路径首条边加一次性 surcharge，重搜一次（最多 1 次，硬上限）；
重搜结果仍指向同一 HS 目标，只是换入口/换路线。
```

- 约束：重搜增加算力，`-c` 计时 ×10 无超时是硬验收；K 与阈值各只取一个先验值，不做二维扫描；flag off 时逐位等价。
- 验收：同 12.2 矩阵 + `-c` 计时。失败直接回退，不迭代第二版——这是提交前阶段，不是研究阶段。

### Phase 12.4: 统计与验收纪律（全阶段共用，源自 11 的双峰教训）

- **n=10 只当 smoke test**：只用于筛掉明显坏配置；defaultCapture 是 1/11 双峰分布，n=10 均分差 < 2 一律视为噪声，不得写入结论。
- 采纳任何改动前：固定图 n=30~50 复测；**RANDOM23 优先于 RANDOM42**（历史上只有 RANDOM23 暴露过泛化失败），必须 49/49。
- 全部对照使用同日同机基线；每轮只动一个变量；批间配置一律走环境变量，不翻文件 flag。
- 跑任何训练相关命令前快照 `QLWeightsMyTeam.txt`；诊断局 `-q`，批量评估 `-Q`。

### 明确不做（负面清单，比做什么更重要）

- 不再尝试纯 QL 或 attack/go_home hybrid 作为主策略（Phase 7/8/9 已三次证伪，RANDOM23 24/49 是定论）。
- 不把 QL 接到 defence / patrol / go_home（escape 权重病态结论不变：`distanceToHome` +352 / `stop` +7.6）。
- 不把任何"目标拉力"特征放回 path adapter：`eats-food`、`closest-food`、`moves-toward-food` 及一切"更想吃附近豆"的信号属于目标选择层，不属于路径风险层（Phase 11 定论）。
- 不再训练原始连续结构特征（`home-path-margin` / `tunnel-depth` 是 10.2 反例：语义合理但线性 QL 学反符号）。
- 不上 neural network / experience replay / n-step return——收益与解释成本不匹配，违背"不过度工程化"约束。
- 不做盲训（"训 200 局看看"）；若 12.2b 触发续训，teacher floor ≥ 0.3 + checkpoint 纪律是硬约束。

### 执行顺序与终止条件

```text
12.0 封存基线（半小时级）
  → 12.1 λ 扫描（轻，1 个变量）
  → 12.2 二值风险特征（先诊断触发率，再 12.2a 手设，显著有效才 12.2b 续训）
  → 12.3 仅在触发条件满足时立项
任何一步失败 → 回退 Phase 11 配置（它已具备提交资格），该步记为否定性结果。
```

一句话总纲：**接下来的 QL 不追求"更会吃豆"，只追求"更会判断哪条 A* 路线风险小"——把风险信号做得更干净、更稳，且每一步都以 Phase 11 验收矩阵为不可退化底线。**

本轮 Phase 12 实验结果（详见 record.md 2026-06-13 Phase 12）：

- **12.1 λ 扫描：保持 0.03（无改动默认胜出）。** 0.05 与 0.03 在 blox ×30 上均分完全相同（+9.13），default 中性；0.01 与基线不可区分。重要副产物：**λ=0.02 可复现地诱发 blox 0-0 活锁（8/20 局）**——终盘双 agent 困在 attack 模式于己方半场绕环不过界。λ 响应非单调，存在刀锋区，λ 不是可自由微调的旋钮。
- **12.2 前置诊断按规则筛掉 tunnel-with-ghost-risk**（触发率 0.06%~0.22% < 1%）；home-cut-risk 通过（RANDOM 2.7%，hard penalty 重叠仅 9%）进入 12.2a。
- **12.2a home-cut-risk 最终弃**：w=-2 是无效测量（经 λ 折算仅 0.06 步代价，RANDOM23 ×49 逐局比分与 off 完全相同）；唯一一次尺度修正 w=-30（cap 饱和）后 RANDOM23 ×49 **仍然逐局相同**，blox/default 持平——被标记格子从不落在"代价差 < cap 的竞争分支"上。
- **12.3 触发条件不满足，按计划跳过**：问题不是"单步看不到延迟风险"，而是"验收图集上的决策对 QL 项扰动不敏感"，换粒度走同一个 capped 通道无法绕过。
- **总结论（正面叙事）：风险信号栈已饱和。** λ ±60% 无可测影响 + 语义合理/触发合格/重叠仅 9% 的新二值信号打满 cap 仍零决策改变，两条独立证据互证 Phase 11 配置是 cap=1.0 框架内的局部最优。提交配置不变：`qlGuidedAStar=True`、λ=0.03、cap=1.0、ckpt6。
- 工具沉淀：`QL_PATH_LAMBDA`、`QL_PATH_RISK_DIAG`、`QL_PATH_RISK_W` 三个环境变量旋钮保留（默认全部无副作用，flag-off 回归通过）；`score` 已还原，权重文件全程未动。
- **附加（方向 1）对手多样性复测**：QL on/off 对 berkeleyTeam 与 bravo（双攻型）在 blox/RANDOM23 上全部中性（bravo blox n=10 的 -2.8 + 首败被 n=30 证伪为噪声——bravo 带随机 tie-break，单局方差远大于 staffTeam）。饱和结论在可得对手上可迁移；但 repo 内所有对手均被碾压（+9~+12 全胜），"重训对齐特征子集"与"目标层风险 tie-break"在本地没有能检验它们的尺子，留待真实比赛对手。**QL 线在本地评估体系内正式收官。**

## Phase 13: 防守策略与 capsule 时机（HS 层首次系统优化）

背景与定位：

- Phase 4 之后防守/巡逻层只在 bloxCapture 收敛实验中动过协作分工，从未走过 Phase 6 式的 A/B 验收矩阵；capsule 在进攻里只是"ghost 压力下的备选目标"，从未有"时机"概念。QL 线已收官（Phase 12），本阶段回到 HS 规则层，优化这两个未被系统优化过的层。
- 代码现状核对（设计前提）：
  - `getDefenceTargets()` 看到 invader 直接以其当前位置为目标追击；全文件没有任何地方读 `gameState.getAgentState(self.index).scaredTimer`——**我方被 capsule 反制变 scared 后会径直撞上 invader 送死**。
  - defence 同速追击从背后永远追不上（staffTeam 弱进攻掩盖了这点，bravo 双攻能暴露）。
  - 我方 capsule 只是 defence 目标列表里排在 `lastEatenFood` 之后的普通一项，没有"invader 逼近 capsule 时优先卡位"的逻辑。
  - `shouldReturnHome()` 的 `carrying >= 3` 与 `score >= 5 且 carrying > 0` 两个触发完全无视对手 scaredTimer——吃下 capsule 后的收割窗口被白白浪费（`getVisibleDangerousGhosts` 已排除 scared ghost，所以 ghost 触发天然关闭，但上述两个触发照样把 agent 拉回家）。
  - Phase 6 遗留 backlog"有 capsule 且 ghost 威胁近时，允许先转 capsule 再回家"**从未实现**：`shouldReturnHome` 在 `getEffectiveLowLevelMode` 里优先级最高，ghost 近 + 带豆时直接 go_home，哪怕 capsule 就在 1~2 格外。
- 测量尺子问题（继承 Phase 12 结论）：本地对手全被碾压，胜率指标已饱和，改进只能体现在**均分**与**只读防守计数器**上；防守类改动用 bravo（双攻反射式，制造真实双入侵压力）做主要对照对手，capsule 时机类用 staffTeam 标准矩阵。
- 回退点：Phase 11 终态（`qlGuidedAStar=True`、λ=0.03、ckpt6）。任何一步失败直接回退，不抢救。

### Phase 13.0: 防守诊断计数器（只读，先建尺子）

- 仿照 `qlDiagnostics` 加 `defDiagnostics` 只读计数器，`final()` 打印一行（`-q` 可见）：
  - `foodLost`：终局防守 food 数相对开局的减少量；
  - `capsuleLost`：我方 capsule 被吃次数；
  - `invaderSteps`：可见 invader 处于我方半场的累计步数；
  - `scaredChaseSteps`：自身 scaredTimer > 0 且与可见 invader 距离 ≤ 2 的步数（D1 病灶直接测量）；
  - `scaredWindowSteps` / `scaredWindowFood`：对手 scaredTimer > 0 期间的步数与吃豆数（C1 病灶直接测量）。
- 用 bravo + staffTeam 各跑 blox/default ×5（`-q`）拿基线读数，确认各病灶在本地对手上的真实触发频率——**触发率太低的项直接降级不做**（Phase 12.2 的教训：语义合理不等于有决策影响）。

### Phase 13.1: capsule 时机——scared 收割窗口（C1，预期收益最大，先做）

- 改动点：`shouldReturnHome()`。计算 `minScaredTimer = min(对手两个 ghost 的 scaredTimer)`（取 min：以最先醒的为准）。当 `minScaredTimer > 回家距离 + margin`（margin 先验取 8，不扫描）时：
  - `carrying >= 3` 阈值提高到 `carrying >= 8`；
  - 跳过 `score >= 5 且 carrying > 0` 的早退触发；
  - `timeLeft` 触发保留不动（终盘安全网）。
- 开关：环境变量 `HS_SCARED_WINDOW`（默认 off 时行为逐位不变），采纳后才固化为默认。
- 预期效应链：吃 capsule → 不再 3 颗就回家 → 单次过界收割更多 → 均分上升。staffTeam 矩阵可测。

### Phase 13.2: capsule 时机——被追时先转 capsule 再回家（C2，Phase 6 遗留 backlog）

- 改动点：`getEffectiveLowLevelMode` 进入 go_home 前（或 `getGoHomeTargets` 内部），若同时满足：
  - 此次回家由 ghost 压力触发（carrying > 0 且危险 ghost ≤ CLOSE_DISTANCE + 1）；
  - 存在敌方半场 capsule，且 `mazeDist(我, capsule) <= min(mazeDist(我, 最近安全边界点), 先验上限 6)`；
  - capsule 方向不比回家方向更危险（capsule 的 `getGhostTargetPenalty < 80`，复用现成函数）；
  - 则目标改为该 capsule（吃到后 13.1 的窗口逻辑自然接管）。
- 开关：`HS_CAPSULE_DETOUR`。注意与 13.1 叠加评估顺序：先单独 A/B，再合并跑。

### Phase 13.3: 防守——scared 自保（D1）

- 改动点：defence/patrol 路径上检查 `self scaredTimer > 0`：
  - `getDefenceTargets()`：scared 且可见 invader 时，不再以 invader 当前位置为目标，改为"距 invader 2~3 格的 shadowing 点"（invader 合法邻域中离我最近且不与 invader 相邻的格子；候选为空则退到我方 capsule / 失窃 food 簇入口卡位）；
  - `getSearchStepCost()` defence 分支：scared 时对距可见 invader ≤ 1 的格子加大代价（量级对齐现有 ghost 惩罚 35），防止 A* 路径顺路撞上去。
  - scaredTimer 很大（> 20）且无近身 invader 时，维持现有协作释放逻辑转 attack（已有 `shouldReleaseDefenceForAttack` 通道，不新建机制）。
- 开关：`HS_SCARED_DEF`。主要对照对手 bravo（它会吃 capsule 制造该场景）；13.0 的 `scaredChaseSteps` 是直接验收指标（应降到接近 0），均分为间接指标。

### Phase 13.4: 防守——capsule 卡位与拦截（D3 + D2，依 13.0 触发率决定做哪个）

- D3 capsule 卡位：可见 invader 且 `invaderDist(我方 capsule) <= myDist(我方 capsule) + 2` 时，defence 目标改为该 capsule（而不是追在 invader 身后）；invader 吃掉 capsule 的代价是全队防守崩塌，值得最高优先级。
- D2 拦截：invader 可见但追不上（连续 N 步距离不减）时，目标改为"invader 与其回家边界列之间、`myDist(p) <= invaderDist(p)` 的最近卡点"。实现成本高于 D3，仅当 13.0 显示 bravo 局中存在大量"追而不获"步数时才做。
- 开关：`HS_CAPSULE_GUARD` / `HS_INTERCEPT`，一次只开一个。
- 明确不做：noisy distance 推断巡逻（D4）——信息噪声大、收益不可测（本地对手压不出场景），记入负面清单。

### Phase 13.5: 验收矩阵与统计纪律（沿用 11/12 口径）

- 所有 A/B 以**同日 flag-off 对照**为准；n=10 只当 smoke，固定图 n≥30（default 双峰教训）；bravo 对局方差大，一律 n≥30。
- capsule 时机类（13.1/13.2）：staffTeam blox/default 正反向 n=30 + strategic ×10，均分不得低于对照；**RANDOM23 ×49 = 49/49 约束性验收**；`-c` ×10 无超时。
- 防守类（13.3/13.4）：bravo blox ×30 + bravo RANDOM23 ×25 均分与防守计数器对照；staffTeam 全矩阵回归不得退化。
- 任一项伤 RANDOM23 → 该项直接弃，不调参抢救。
- 全部通过的项才把环境变量开关翻成代码默认值；提交前 flags 复核：`trainning=False`、`qlLowLevelModes=set()`、`qlDiagnostics=False`、`defDiagnostics=False`、`qlGuidedAStar=True`。

### 执行顺序

```text
13.0 建尺子（半天级，决定 13.3/13.4 取舍）
  → 13.1 scared 收割窗口（收益最大、改动最小）
  → 13.2 capsule detour（Phase 6 遗留债）
  → 13.3 scared 自保（bravo 可测）
  → 13.4 仅做 13.0 证明触发率合格的那一个
任何一步失败 → 回退 Phase 11 终态，该步记为否定性结果。
```

本轮 Phase 13 实验结果（详见 record.md 2026-06-13 Phase 13）：

- 13.0 尺子先行起效：基线触发率把 D3 直接筛掉（capsuleLost 2/10），D2 升级为首要防守候选（staff blox chaseNoGain 70% + 每局丢 7 颗）。
- **关键机制发现改写了 13.3 的前提**：capture.py 中 scared ghost 被吃后 scaredTimer 立即归零且 KILL_POINTS=0——"自杀式追击"是免费解除 40 步 debuff 的最优解，任何 scared 自保（shadowing）反而把防守冻结整个 scared 期。固定种子 A/B 实锤：flag-off +8，HS_SCARED_DEF 同种子被提前判负；bravo ×5 批量确认（+3.8/+5.2 vs 基线 +12.0/+10.4）。**弃。**
- 13.4 拦截更惨（bravo default ×5 = **-2.2**，胜率 40%）：边界开口多，蹲守单一出口 = 放弃追击压迫，invader 在别处自由吃豆。"追而不获"的持续驱赶本身就是有效防守。**弃。**
- 13.1 scared 收割窗口在 n=30 显著有害（default +4.6 vs +7.67，高分局率 67%→40%）：窗口判定的两难——min(scaredTimer) 因"防守吃 invader 即归零"永不触发，max 规则下已苏醒的 ghost 在收割加深时回防截杀。**弃。**
- 13.2 capsule detour 中性（default +7.0 vs +7.67 噪声内，blox 0 触发），按"无收益不启用"惯例默认 off。
- 验收：flag-off 与 Phase 11 终态 `-f` 固定种子逐位等价（default/blox diff 一致）；`-c` ×5 无超时；同日 flag-off n=30 回归 default 30/30 +7.67、blox 30/30 +9.13。**提交配置不变。**
- 总结论：与 Phase 12 "风险信号饱和"互为印证——HS 防守/capsule 层在本地对手上同样已无廉价收益空间，Phase 4 的简单防守 + 现有 capsule 用法是本地局部最优。四个特性以默认无副作用旋钮形式保留（`HS_SCARED_WINDOW` / `HS_CAPSULE_DETOUR` / `HS_SCARED_DEF` / `HS_INTERCEPT` + `HS_DEF_DIAG` 诊断），供报告与真实对手出现后复验。

## Phase 14: 压迫式防守——从“抓 invader”改为“降低对方有效收益”

背景与定位：

- Phase 13 定论：本地体系内“贴身追击 + 失窃点调查”已是局部最优，四个直觉增强方向全部证伪或中性。但 13.4 的失败机制同时给出正面线索：**压迫本身就是防守**——追而不获的持续驱赶使 invader 无法安心吃豆。本阶段不再增加“去哪里”的规则，而是改两件事：防守的评价方式（不看抓没抓到，看对方少吃、少带、晚回家了多少）和压迫的质量（追击位置软性偏向 invader 的回家方向）。
- 测量尺子升级是本阶段第一公民（继承 12/13 的“本地对手全被碾压、均分饱和”结论）：胜率/均分对防守改动不敏感，主指标改为只读防守计数器（对方有效收益），并引入**镜像对手**（冻结在 Phase 11 终态的 myTeam 自身）作为本地最强攻击压力源——它是仓内唯一会带 3+ 颗豆冲回家、会绕 ghost、会双线进攻的对手，天然制造“对手带 4-6 颗准备回家”“双攻两路拉开”这类 staff/bravo 压不出的场景。
- 回退点：Phase 11 终态（`qlGuidedAStar=True`、λ=0.03、ckpt6）。全部改动 env 门控，默认 off 时行为逐位不变。

### Phase 14.0: 尺子升级——镜像对手 + 有效收益计数器（先建尺子，决定后续取舍）

- 镜像对手：复制 myTeam.py 为 `frozenTeam.py`（Phase 11 终态行为），**把全部 HS_*/QL_* 环境变量读取硬编码为默认值**——capture.py 两队同进程，env flag 会同时作用于双方，冻结副本必须对 env 免疫才能做非对称 A/B。自检：frozenTeam vs frozenTeam 与 myTeam(flag-off) vs frozenTeam 的比分分布应一致。
- 计数器扩展（沿用 `HS_DEF_DIAG` 通道，`final()` 打印）：
  - `invaderFoodReturned`：对方实际送回家的豆数（防守的真实失败量，区别于只是“被吃走”的 foodLost）；
  - `invaderMaxReturn`：单次最大送回量（“一次大额送回”风险的直接测量）；
  - `invaderEscapes` / `invaderKills`：invader 带豆成功过界次数 / 被我方吃掉次数（区分“抓到”与“逼退”两种防守成功）；
  - 已有 foodLost / invaderSteps / chaseNoGain 保留，chaseNoGain 在 14.1 里升级为“压迫未丢失”的守门指标。
- 基线测量：myTeam(flag-off) vs frozenTeam、vs bravo，blox/default 各 ×10（`-q`）。**镜像局方差未知，先标定分布再定后续 n**；各 14.x 候选场景先看触发率，<1% 直接弃（13.0 纪律：语义合理不等于有决策影响）。

### Phase 14.1: 追击中的回家方向压迫（软压迫，第一优先）

- 与 13.4 硬拦截的本质区别：**永不放弃贴身**。目标永远在 invader 本体邻域内，只是当 `mazeDist(我, invader) >= 2` 时，把追击目标从 invader 当前格改为“invader 的合法邻格中更靠近其最近逃生出口一侧的那个”（逃生出口 = 敌方回家边界点中离 invader 最近者）；距离 ≤ 1 时退回原行为直接吃。蹲点 13.4 的病灶是目标硬切到远处出口、压迫归零——这里目标与 invader 始终相邻，只偏一格站位。
- 实现挂点：`getDefenceTargets()` 的 `return self.sortTargetsByDistance(gameState, invaders)` 分支前插入 `getPressureTarget()`；复用 `getHomeBoundaryPoints` / `getMazeDistance`，零新增基础设施。
- 开关 `HS_PRESS_HOME`。流程：先 `-f` 固定种子 smoke（13.3/13.4 都是固定种子先暴露提前判负），再批量 A/B。验收主指标：vs frozenTeam/bravo 的 `invaderFoodReturned`、`invaderEscapes` 下降；守门指标：`chaseNoGain` 不得上升（压迫未丢失的直接证据），staff 矩阵不退化。

### Phase 14.2: 失窃点路径化——从地点到路线证据（第二优先）

- `lastEatenFood` 从单点升级为短历史（deque 保留最近 K=3 个失窃点 + 步号）。当最近 N=40 步内同一区域（失窃点互距 ≤ 5）连续丢 ≥ 2 颗时，无可见 invader 的 defence 目标从“最新失窃格”改为“该区域指向边界的入口 choke”（复用 `getBoundaryChokepoints`，取离失窃质心最近者）——把失窃序列当成对方进入/撤退路线的证据，而不是反复回访最新丢豆格。
- 单点丢失行为不变（防过度反应——“对手专吃边缘低价值豆”场景正是要避免被拉着跑）。明确不用 noisy distance（负面清单不变，这里只用确定发生过的 food loss）。
- 开关 `HS_LOSS_TRAIL`。前置诊断：用 14.0 计数器测“同区域连续丢豆”在镜像/bravo 局的触发率，<1% 弃。

### Phase 14.3: 主防 + 支援位（第三优先）

- 不动“只留一个 primary defender、另一个释放进攻”的协作框架（bloxCapture 收益来源，不可回退）。只改一处：当队友正在追击可见 invader 且我处于 patrol（非 attack）模式时，patrol 点排序偏向 invader 逃生侧的边界 choke / 我方 capsule 侧。支援位**只影响 patrol 目标排序，永不把 attack 模式的 agent 拉回防守**——既不回到双防没进攻的旧坑，也不像 13.4 那样让唯一 defender 放弃追击。
- 开关 `HS_SUPPORT_POS`。前置诊断：“队友追击 + 我在 patrol”同时态的步数占比；预期镜像局显著多于 staff 局，staff 局触发不足就只用镜像局验。

### Phase 14.4: 比分/时间驱动的防守强度三档（条件触发，默认不做）

- 现有 `shouldUseLateLeadDefence` 二值判断 → 三档：大幅领先时优先防“一次大额送回”（`invaderMaxReturn` 是直接尺子）；小领先/持平保持一主防一进攻；落后时只响应高威胁 invader（carrying > 0 或逼近 capsule），不被普通入侵拖节奏。
- **触发条件（满足才立项，否则跳过）**：14.0 基线显示镜像局存在可测频次的“领先后被单次大额送回缩小分差”或“落后时双 agent 被低威胁 invader 牵制”。13.x 教训：先证明病灶存在，再写规则。

### Phase 14.5: 验收矩阵与统计纪律（沿用 11/12/13 口径）

- 防守类主战场：vs frozenTeam + vs bravo，blox/default n≥30（按 14.0 标定的方差调整），主指标 = `invaderFoodReturned` / `foodLost` / `invaderEscapes` 计数器 + 均分。
- 无回归守门：staffTeam 全矩阵（blox/default 正反 n=30 + strategic ×10）均分不低于同日 flag-off；**RANDOM23 ×49 = 49/49 约束性验收**；`-c` ×10 无超时。
- flag-off 逐位等价（`-f` 固定种子 diff 验证）；n=10 只当 smoke；一次只开一个 flag，叠加评估只在单项过关后做；任一项伤 RANDOM23 → 直接弃，不调参抢救。frozenTeam.py 仅作本地评估工具，不进提交。

### 负面清单（Phase 13 定论，不再投入）

- scared 自保 / shadowing（机制级证伪：scared ghost 之死免费且零分代价）；
- 硬拦截 / 蹲出口（13.4：放弃贴身压迫 = 放任对方吃豆）；
- scared 收割窗口（13.1 显著有害）、capsule 时机作为主方向（13.2 中性；除非真实比赛对手明显依赖 capsule 再重开）；
- 纯 QL 防守、noisy distance 推断巡逻（历史定论不变）。

### 执行顺序

```text
14.0 镜像对手 + 有效收益计数器（尺子先行，决定 14.2/14.3/14.4 取舍）
  → 14.1 软压迫（固定种子 smoke → 批量 A/B）
  → 14.2 失窃点路径化（触发率合格才做）
  → 14.3 支援位（触发率合格才做）
  → 14.4 仅在 14.0 暴露对应病灶时立项
任何一步失败 → 回退 Phase 11 终态（提交资格不受影响），该步记为否定性结果。
```

一句话总纲：**防守不再追求“抓到”，只追求“对方带回家的豆变少”——压迫保贴身、站位偏回家侧，尺子从胜率换成对方有效收益，并用冻结的自己当本地最强对手。**

本轮 Phase 14 实验结果（详见 record.md 2026-06-13 Phase 14）：

- **14.0 镜像尺子立功**：frozenTeam（Phase 11 终态 env 免疫副本）逐位自检通过；镜像 blox 暴露 staff/bravo 测不到的病灶——flag-off 防守对自己的攻击 0 击杀、10 颗失窃全部被安全送回，红方 0/10 全败（-3.50，sd 0.53），是本地最锐利的防守仪器。镜像 default 双方互锁全 0-0，只当守门。副产物：bravo flag-off 基线本身有 -25 级爆破局，Phase 12/13 的 bravo 全胜记录含日间运气。
- **14.1 → 14.1b 采纳（默认开启）**：纯软压迫在劣势侧赚（-3.5→-1.5）、优势侧亏（+3.4→+2.5）——压迫的代价是防守者被锁在追击中不再释放进攻；加 score≤0 门控后双向双赢（-1.5 / +3.7），bravo blox ×30 首次 30/30（+11.40，sd 0.72）、default +1.10→+8.03（爆破局 16/60→4/60），staff 全矩阵中性，**RANDOM23 ×49 = 49/49（每局 +11）**，`-c` 无超时。GPT 方案的第一优先（软压迫）与第四优先（比分驱动强度）被数据合并成同一特性。`HS_PRESS_HOME=0` 可关断，关断后与 Phase 11 终态逐位一致。
- **14.2 弃**：触发率合格（130+ 步/局）但镜像 -3.5→-6.0 明确有害——蹲失窃簇的边界 choke 与 13.4 蹲点同族失败；按"任一仪器受伤即弃"纪律处理，旋钮保留默认 off。
- **14.3 降级不做**：supportSteps 触发率在镜像上为 0（压迫开启后"队友防守+我巡逻"局面消失），bravo/staff 仅 ~4%，无判别尺子，记入 backlog。
- 修复 14.0 计数器 bug：chooseAction 的 fallback 提前返回跳过诊断，恰好漏掉爆破局的大额送回事件。
- 提交配置更新：`pressureHomeEnabled=True` 为 Phase 4 协作分工以来防守层首个通过完整验收矩阵的采纳项；其余新旋钮默认 off。
- **附加轮（详见 record.md Phase 14 附加）**：纯 HS 镜像对手（frozenHsTeam）测出两件事——QL 引导价值首次被本地尺子检出（劣势侧 5-8/10 胜局）；14.1b 对"风险中性硬闯型"攻击手失效（-9.6，钉死依赖对手的风险规避）。修复 = **14.1c 保险丝**：压迫期间对手成功送回一次 → 本局退回贴身追杀。全验收矩阵复跑通过（vs HS -9.6→-2.2、vs QL 钉死无损、RANDOM23 49/49）。14.1 最终形态 = 软压迫 + 比分门控 + 失效保险丝，三个组件各对应一类对手测出的失效模式。

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
