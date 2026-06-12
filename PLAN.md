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
