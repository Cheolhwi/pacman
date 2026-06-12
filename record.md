# Phase 6 实验记录

日期：2026-05-11

运行环境：

- 项目目录：`/Users/cheolhwi/Documents/fit5222/pacman`
- 指定环境：`flatland-rl`
- 实际命令前缀：`/opt/anaconda3/bin/conda run -n flatland-rl`
- 说明：当前 shell 中 `conda` 未进入 `PATH`，直接执行 `conda` 会报 `command not found`，因此本轮使用 conda 的绝对路径运行。

## 代码检查

| 项目 | 命令 | 结果 |
| --- | --- | --- |
| Python 编译检查 | `/opt/anaconda3/bin/conda run -n flatland-rl python -m py_compile myTeam.py` | 通过 |
| smoke test | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -h` | 通过，help 正常输出 |

## Phase 6 固定实验

| 序号 | 实验 | 命令 | 结果 |
| --- | --- | --- | --- |
| 1 | smoke test | `python capture.py -h` | 通过 |
| 2 | 单局接口测试 | `python capture.py -r myTeam.py -b staffTeam.py -q -n 1` | 通过，红队胜 10 分 |
| 3 | 批量静默测试 defaultCapture | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/defaultCapture` | 红队 10/10 胜，平均分 `+8.8`，比分 `7, 10, 10, 7, 10, 7, 10, 10, 10, 7` |
| 4 | 红蓝互换 defaultCapture | `python capture.py -r staffTeam.py -b myTeam.py -Q -n 10 -l ./layouts/defaultCapture` | 蓝队 10/10 胜；按红队视角平均分 `-5.4`，比分 `-11, -11, -3, -3, -3, -11, -3, -3, -3, -3` |
| 5a | 多地图 strategicCapture | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/strategicCapture` | 红队 10/10 胜，平均分 `+7.5`，比分 `7, 7, 8, 8, 7, 8, 7, 7, 8, 8` |
| 5b | 多地图 bloxCapture | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/bloxCapture` | 红队 5/10 胜，平均分 `0.0`，比分 `3, -3, 3, 3, -3, 3, 3, -3, -3, -3` |
| 6a | 49 局 RANDOM23 | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 49 -l RANDOM23` | 红队 49/49 胜，平均分 `+10.46938775510204` |
| 6b | 49 局 RANDOM42 | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 49 -l RANDOM42` | 红队 49/49 胜，平均分 `+8.346938775510203` |
| 7 | 时间限制测试 | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -c` | 红队 10/10 胜，平均分 `+8.8`，比分 `7, 10, 7, 10, 10, 7, 10, 10, 10, 7` |

## 观察

- 所有 Phase 6 命令均正常退出，未观察到崩溃、异常退出或 `-c` 下的超时失败。
- defaultCapture 红蓝互换均稳定，说明红蓝边界识别和基本行为对称性通过。
- contest-like 的 `RANDOM23` 与 `RANDOM42` 均达到 `49/49`，明显高于计划中参考目标 `28/49`。
- `bloxCapture` 表现最弱，仅 `5/10`，平均分为 `0.0`。该地图可能更容易暴露狭窄通道、回家路径和防守牵制问题，但本轮没有稳定性失败。

## 调参结论

本轮未修改 `myTeam.py` 参数。

原因：

- `maxLowLevelExpansions = 600` 在所有测试中未表现出超时问题。
- `-c` 时间限制测试通过。
- RANDOM23/RANDOM42 的 49 局结果已经超过 Phase 6 验收参考。
- 虽然 bloxCapture 只有 5/10，但贸然调高风险惩罚或改变 carrying 阈值可能影响 defaultCapture 和随机地图上已经稳定的结果。

## 当前建议

- 提交前可保留当前参数作为稳定版本。
- 若后续专门优化 bloxCapture，优先只在允许范围内尝试：
  - 将 carrying 回家阈值从 `3` 对比测试为 `4`；
  - 微调 defence/patrol 的 anti-oscillation 权重；
  - 在 bloxCapture 上单独复测红蓝互换，确认是否是地图结构导致的对称低胜率。
  
  

## bloxCapture 收敛实验

日期：2026-05-12

目标：

- 阅读 `PLAN.md` Phase 6 后，针对当前最弱地图 `bloxCapture` 做小步改动。
- 验收目标为 `bloxCapture` 正向达到 `10/10`，并完成红蓝互换、默认图、多地图、随机图和时间限制回归。

### 基线复现与问题定位

| 项目 | 命令/方法 | 结果 |
| --- | --- | --- |
| bloxCapture 正向基线 | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/bloxCapture` | 红队 `6/10` 胜，平均分 `+0.6`，比分 `-3, -3, 3, 3, -3, 3, 3, 3, 3, -3` |
| 强制 Red starts | 通过脚本固定 `CaptureRules.newGame()` 的 starter 为 red | 修改前比分 `-3`，我方 returned 为 `0`，说明红队先手局容易被 defence 长期牵制 |
| 强制 Blue starts | 同上，starter 固定为 blue | 修改前比分 `+3`，我方能 returned `22`，说明寻路和进攻本身可行 |

观察：

- `bloxCapture` 的失败主要不是 A* 搜索不可达，而是 PDDL 看到敌方 Pacman 后，两个 agent 容易同时进入 `defence`。
- 在狭窄通道地图中，两个 agent 被同一防守威胁牵住后，我方进攻压力不足，最终常以 `-3` 输掉。
- 因此本轮没有调整 `maxLowLevelExpansions`、carrying 阈值或 ghost risk，而是只改高低层衔接中的协作分工。

### 代码改动

文件：`myTeam.py`

改动点：

- 在 `getEffectiveLowLevelMode()` 中允许 PDDL 产生的 `defence` 被低层协作逻辑转换为 `attack`。
- 新增 `shouldReleaseDefenceForAttack()`、`shouldHoldAttackDefenceRole()`、`getDefenceThreatTargets()`、`isPrimaryDefenderForTargets()`。
- 当存在防守威胁时，只让距离 threat 最近的一名 teammate 保持防守；另一名 teammate 释放为进攻。
- `shouldReturnHome()` 优先级提升到所有模式之上，确保带豆或危险时仍能回家。
- 保留 late lead defence：后期领先时不释放防守，避免破坏收官稳定性。

### 修改后验证

| 序号 | 实验 | 命令/方法 | 结果 |
| --- | --- | --- | --- |
| 1 | Python 编译检查 | `/opt/anaconda3/bin/conda run -n flatland-rl python -m py_compile myTeam.py` | 通过 |
| 2 | 强制 Red starts | 固定 starter 为 red，`bloxCapture` 单局 | 修改后比分 `+7`，我方 returned `15`，对方 returned `8` |
| 3 | 强制 Blue starts | 固定 starter 为 blue，`bloxCapture` 单局 | 修改后比分 `+7`，我方 returned `14`，对方 returned `7` |
| 4 | bloxCapture 正向 | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/bloxCapture` | 红队 `10/10` 胜，平均分 `+7.0`，比分全为 `7` |
| 5 | bloxCapture 红蓝互换 | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r staffTeam.py -b myTeam.py -Q -n 10 -l ./layouts/bloxCapture` | 我方蓝队 `10/10` 胜；按红队视角平均分 `-7.5`，比分 `-6, -11, -6, -11, -6, -11, -6, -6, -6, -6` |
| 6 | defaultCapture 正向 | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/defaultCapture` | 红队 `10/10` 胜，平均分 `+7.0` |
| 7 | defaultCapture 红蓝互换 | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r staffTeam.py -b myTeam.py -Q -n 10 -l ./layouts/defaultCapture` | 我方蓝队 `10/10` 胜；按红队视角平均分 `-4.8` |
| 8 | strategicCapture | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/strategicCapture` | 红队 `10/10` 胜，平均分 `+6.8` |
| 9 | RANDOM23 | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -Q -n 49 -l RANDOM23` | 红队 `49/49` 胜，平均分 `+9.46938775510204` |
| 10 | RANDOM42 | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -Q -n 49 -l RANDOM42` | 红队 `49/49` 胜，平均分 `+11.408163265306122` |
| 11 | 时间限制测试 | `/opt/anaconda3/bin/conda run -n flatland-rl python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -c` | 红队 `10/10` 胜，平均分 `+5.0` |
| 12 | diff 空白检查 | `git diff --check -- myTeam.py` | 通过 |

### 结论

- `bloxCapture` 已从 Phase 6 记录中的 `5/10`，以及本轮复现的 `6/10`，提升到正向 `10/10`。
- 红蓝互换后我方作为蓝队也达到 `10/10`，说明改动不是单边地图偏差。
- defaultCapture、strategicCapture、RANDOM23、RANDOM42 和 `-c` 均通过回归，没有观察到崩溃、异常退出或时间限制失败。
- RANDOM23 平均分从旧记录 `+10.46938775510204` 降至 `+9.46938775510204`，但胜率仍为 `49/49`；RANDOM42 平均分提升至 `+11.408163265306122`。
- 测试期间 `capture.py` 会覆盖 `score` 文件，本轮已将该副作用还原，只保留 `myTeam.py` 的策略改动。

## Phase 7: 补全 Q-learning 低层规划器

日期：2026-06-12

目标：

- 按 PLAN.md Phase 7，把模板中未完成的 Q-learning 低层规划器补全，使其可训练、可切换，同时不影响 HS 主路径的已有表现。

### 代码改动

文件：`myTeam.py`

改动点：

- 补全 `getDefensiveReward()`：每步 `-1` 生存代价；invader 数量减少 `+50`；靠近最近可见 invader 每格 `+2`；防守 food 被吃 `-10`；被吃回出生点 `-50`。
- 补全 `getEscapeReward()`：每步 `-1` 生存代价；成功带 food 回家每颗 `+20`；靠近 home boundary 每格 `+2`；回家路上被吃回出生点 `-100`。
- `getLowLevelPlanQL()` 复用 `getLowLevelMode()` 做 high-level action 到 mode 的映射，offensive/escape/defensive 三个分支学习率统一启用 `self.alpha`；规划后同步更新 `sharedModes` / `sharedTargets`。
- `chooseAction()` 增加 `self.useQLearning` 开关：默认 `False` 走 HS 低层；`True` 时每步由 QL 选一个动作。
- 修复 `updateWeights()`：correction 在循环外用旧权重只计算一次，避免循环内重复用已更新权重导致发散。
- `getEscapeFeatures()` / `getDefensiveFeatures()` 的距离特征除以 `(walls.width + walls.height)` 归一化，与 offensive 特征一致。

### 实验记录

| 序号 | 实验 | 命令/方法 | 结果 |
| --- | --- | --- | --- |
| 1 | Python 编译检查 | `/opt/anaconda3/bin/conda run -n flatland-rl python -m py_compile myTeam.py` | 通过 |
| 2 | HS 默认路径单局 | `python capture.py -r myTeam.py -b staffTeam.py -q -n 1` | 通过，红队胜 11 分 |
| 3 | 训练冒烟（修复前） | 临时 `trainning = True`，1 局 | 能跑完并写出权重，但 defensiveWeights 发散到 `1e+49` 量级，定位为 correction 在循环内重算 + 距离特征未归一化 |
| 4 | 训练冒烟（修复后） | 删除旧权重文件，`trainning = True`，3 局 | 通过，三组权重均更新且保持在百量级，escapeWeights 也开始更新，无发散 |
| 5 | defaultCapture 回归 | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/defaultCapture` | 红队 `10/10` 胜 |
| 6 | bloxCapture 回归 | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 10 -l ./layouts/bloxCapture` | 红队 `10/10` 胜，平均分 `+7.0`，比分全为 `7` |

### 结论

- Q-learning 低层规划器已补全：三个 mode 的 reward 都已实现，不再打印 "not implemented" 警告，训练时权重可以稳定更新并写入 `QLWeightsMyTeam.txt`。
- 默认配置保持 `trainning = False`、`useQLearning = False`，低层仍走 HS，defaultCapture 与 bloxCapture 回归均保持 `10/10`，对提交版本无影响。
- 训练实验产生的权重文件与 `score` 副作用已经还原，仓库中只保留 `myTeam.py`、`PLAN.md`、`record.md` 的改动。
- 后续若要实际用 QL 低层比赛，需要先用更多训练局学习权重，再把 `useQLearning` 设为 `True` 并按 Phase 6 的验收矩阵做回归。

### Q-learning 本地训练实验

日期：2026-06-12

方法：

- 删除旧 `QLWeightsMyTeam.txt`，从代码内手写默认权重开始训练（旧文件中 offensive 权重是修复 `updateWeights` 之前训练出来的，起点不可靠）。
- `trainning = True` 时每步更新权重并以 `epsilon = 0.1` 随机探索，每局结束 `final()` 把权重写入文件，下一局自动加载续训。

| 序号 | 实验 | 命令 | 结果 |
| --- | --- | --- | --- |
| 1 | 红方训练 50 局 | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 50 -l RANDOM` | 跑完无发散，我方 5/50 胜（训练期带随机探索，胜率低是预期） |
| 2 | 蓝方训练 50 局 | `python capture.py -r staffTeam.py -b myTeam.py -Q -n 50 -l RANDOM` | 跑完无发散，我方 8/50 胜 |
| 3 | 纯 QL 策略评估 | `trainning = False`、`useQLearning = True`，defaultCapture 10 局 | 全部平局，平均分 `0.0`，远低于 HS 基线的 `10/10` |

结论：

- 训练管线工作正常：权重持续更新、量级稳定（百量级内）、可跨局续训。
- 100 局训练后的纯 QL 策略仍明显弱于 HS（10 平 vs 10 胜），线性特征 + 单步贪心很难追上 A* 规划，提交版本继续保持 `useQLearning = False` 走 HS。
- 训练后的权重保留在 `QLWeightsMyTeam.txt`，后续可在此基础上继续训练；提交前确认 `trainning = False`。

## Phase 8: Q-learning 局部增强（hybrid 低层）

日期：2026-06-13

目标：

- 按 PLAN.md Phase 8，验证 QL 在 `attack` / `go_home` 两个 mode 上局部接入（defence / patrol 保持 HS）能否达到可用强度，且不拖累 HS 基线。

### 代码改动

文件：`myTeam.py`

改动点：

- Phase 8.1：删除单一 `useQLearning` 布尔开关，改为按 mode 路由的 `self.qlLowLevelModes` 集合。`chooseAction()` 先算 `getEffectiveLowLevelMode()`，结果在集合内走 `getLowLevelPlanQL()`，否则走原 HS 路径；空集等价于纯 HS，可完全回退。
- Phase 8.2：`getOffensiveFeatures()` 新增 3 个 feature：
  - `carrying`：`numCarrying / 10.0`；
  - `ghost-distance`：到最近可见危险 ghost 的归一化迷宫距离（无 ghost 时取 1）；
  - `dead-end`：下一格 legal neighbors（含原地）`<= 2` 时为 1。
- 默认权重表为新 feature 加 0 初值；加载旧权重文件时改为 merge 进默认表，旧文件缺少的新 key 保持默认值，避免 `updateWeights()` KeyError。

### 实验记录

| 序号 | 实验 | 命令/配置 | 结果 |
| --- | --- | --- | --- |
| 1 | 编译检查 | `python -m py_compile myTeam.py` | 通过 |
| 2 | 训练冒烟 | `trainning=True`、`qlLowLevelModes={"attack","go_home"}`，`-q -n 1` | 通过，红队胜 10 分，新 feature 权重开始更新 |
| 3 | 红方续训 50 局 | `python capture.py -r myTeam.py -b staffTeam.py -Q -n 50 -l RANDOM` | 训练期 41/50 胜（Phase 7 全模式训练时仅 5/50），无发散 |
| 4 | 蓝方续训 50 局 | `python capture.py -r staffTeam.py -b myTeam.py -Q -n 50 -l RANDOM` | 训练期 41/50 胜，无发散 |
| 5 | hybrid 评估单局 | `trainning=False`、`qlLowLevelModes={"attack","go_home"}`，`-q -n 1` | 平局 |
| 6 | hybrid 评估 defaultCapture | 同上，`-Q -n 10 -l ./layouts/defaultCapture` | `0/10` 胜，10 局全部 `0-0` 平局，不达验收标准 |
| 7 | 隔离实验 attack-only | `qlLowLevelModes={"attack"}`（go_home 退回 HS），defaultCapture 10 局 | 仍 `0/10` 胜，10 局全部 `0-0` 平局 |
| 8 | 回退后 HS 回归 defaultCapture | `qlLowLevelModes=set()`，`-Q -n 10 -l ./layouts/defaultCapture` | 红队 `10/10` 胜，平均分 `+7.0` |
| 9 | 回退后 HS 回归 bloxCapture | `qlLowLevelModes=set()`，`-Q -n 10 -l ./layouts/bloxCapture` | 红队 `10/10` 胜，平均分 `+7.0`，比分全为 `7` |

### 观察与归因

- 续训后权重量级稳定：`dead-end` 学到约 `-1.4`（方向正确），`carrying` 约 `-0.4`，`ghost-distance` 收敛到约 `0`（其信息已被 `#-of-ghosts-1-step-away` 和 reward 覆盖，边际价值不大）。
- hybrid 评估 10 局全 `0-0`：我方 HS defence 守住了对面，但 QL 进攻端从未完成"吃够 food 并送回家"的得分闭环。
- 隔离实验排除了 escape 权重单独背锅的假设（`escapeWeights` 里 `distanceToHome` 为大正值确实可疑）：即使 `go_home` 退回 HS，attack-only QL 仍然 10 局全平。说明单步贪心的线性 QL 进攻通常吃 1-2 颗就被抓，到不了 `carrying >= 3` 的回家阈值，瓶颈在 QL 策略本身的强度，与 Phase 7 全模式评估结论一致。

### 结论

- Phase 8.4 验收不通过：hybrid 在 defaultCapture 为 `0/10`，远低于 HS 基线 `10/10`，按计划提交版回退 `qlLowLevelModes = set()`（纯 HS）。
- 回退后 defaultCapture / bloxCapture 回归均为 `10/10`、平均 `+7.0`，与既有基线一致，本轮路由重构对 HS 主路径无副作用。
- QL 部分（训练管线 + hybrid 路由 + 新 feature）保留在代码中作为作业报告的训练实验展示；续训后的权重保留在 `QLWeightsMyTeam.txt`。
- 提交配置已确认：`trainning = False`、`qlLowLevelModes = set()`；`score` 文件副作用已还原。

## Phase 9: Q-learning 确诊与分布修正

日期：2026-06-13

目标：按 PLAN.md Phase 9，先确诊 Phase 8 失败的真实病灶，再做对症修正，按分级验收（L1 得分 / L2 不低于 HS）决定提交配置。

### 9.0 确诊

诊断手段：只读计数器（`qlDiagnostics`），每局打印 maxCarrying / foodEaten / deaths / maxDepth / boundaryDither / modeSwitches。

| 配置 | maxDepth | foodEaten | boundaryDither |
| --- | --- | --- | --- |
| attack-only QL（3 局） | 0 | 0 | ~266 |
| 纯 HS 对照（3 局） | 11-14 | 4-6 | 9-31 |

进一步用 Q 值分解定位到死锁现场：agent 停在边界格 (15,7)，两只 staff 防守鬼坐在 (16,8)；过界动作 Q = -0.98（`#-of-ghosts-1-step-away` ×2 = -10.1 惩罚墙），而 `stop` 权重被学成正数（+1.16）使 Stop 的 Q = +4.76 全场最高，agent **整局罚站**。确诊为「进不去」：单步贪心被守界鬼的惩罚墙挡死，且 Stop 成为吸收态。

### 9.1 / 9.2 修正

- teacher 衰减（DAgger 思路）：`teacherProb` 从 0.9 随 `trainedEpisodes`（持久化在权重文件，agent-局计数）线性衰减；后因毒化事故把地板从 0.1 提高到 0.3。
- feature 手术轮次 1：加 `moves-toward-food` 二值进度特征；删 `successorScore`（学到 -1.5 符号反，纯噪声）。
- feature 手术轮次 2（针对死锁）：QL 候选动作排除 Stop（与项目"Stop 只作 fallback"约定一致）；加 `revisit` 特征（下一格在 `recentPositions` 最近 6 格内则为 1），让罚站/兜圈在 Q 值上变贵。

### 9.3 带检查点的续训（每轮红蓝各 25 局 RANDOM，attack-only 评估 defaultCapture 10 局）

| 检查点 | 平均分 | 胜/平/负 | 备注 |
| --- | --- | --- | --- |
| 1 | 0.0 | 0/10/0 | 仍全平：stop 死锁尚未修复（修复在其后实施） |
| 2 | 2.1 | 3/7/0 | L1 首次达成；赢局双 agent 过界（depth 8-12）吃 3-4 颗 |
| 3 | -8.4 | 0/0/10 | **自走毒化**：teacher 到地板 0.1 后，自走经验充满边界僵局负奖励，`revisit` 翻正、`moves-toward-food` 崩塌；回滚 |
| 4 | 5.0 | 10/10/0 | 恢复 ckpt2 权重 + teacher 地板 0.3 后续训：对症起效 |
| 5 | 6.3 | 7/3/0 | 赢局都是 9 分 |
| 6 | **10.0** | **10/0/0** | **峰值**：每局 10-0，超过 HS 基线的 +7.0 |
| 7 | 3.5 | 5/5/0 | 第一次无提升 |
| 8 | 8.5 | 10/0/0 | 第二次无提升 → 按规则停训，回滚 ckpt6 权重 |

经验教训：训练轮之间必须快照权重文件（检查点 3 毒化后靠评估日志里的 `Load QLWeights` 行才抢救回 ckpt2）；`-Q` 会吞掉 agent 的 stdout，诊断/权重打印要用 `-q`。

### 9.4 分级验收（attack-only QL，ckpt6 权重，trainning=False）

| 测试 | attack-only QL | HS 基线 | 判定 |
| --- | --- | --- | --- |
| defaultCapture 正向 | 10/10，+10.0 | 10/10，+7.0 | ✓ 超 HS |
| defaultCapture 反向 | 10/10，我方 +7.0 | 10/10，+4.8 | ✓ 超 HS |
| bloxCapture 正向 | 10/10，+12.4 | 10/10，+7.0 | ✓ 超 HS |
| bloxCapture 反向 | 10/10，我方 +7.8 | 10/10，+7.5 | ✓ |
| strategicCapture | 10/10，+11.9 | 10/10，+7.5 | ✓ 超 HS |
| **RANDOM23 ×49** | **24/49 (49%)，+5.9** | **49/49，+9.5** | **✗ 严重退步** |
| RANDOM42 ×49 | 49/49，+8.7 | 49/49，+11.4 | ✓ 胜率持平 |
| `-c` 计时 ×10 | 10/10，+10.0 | 10/10，+5.0 | ✓ |

### 结论

- L1 达成且大幅超额：attack-only QL 在全部固定图（default/blox/strategic 正反向）10/10 全胜，平均分全面超过 HS 基线。
- L2 未通过：RANDOM23 仅 24/49，远低于 HS 的 49/49。线性特征 + 单步贪心在固定图上学到了有效的过界-吃豆模式，但对随机地图族泛化差（约一半地图失败），A* 的泛化能力无法靠这套特征逼近。
- 按 9.4 预设规则，提交配置回退纯 HS：`trainning = False`、`qlLowLevelModes = set()`、`qlDiagnostics = False`。
- ckpt6 最佳权重保留在 `QLWeightsMyTeam.txt`（快照另存 `/tmp/qlweights_ckpt6_best.txt`），QL 全链路（确诊 → 修正 → 检查点训练 → 验收）作为报告素材。

## Phase 10: QL 作为路径偏好（QL-guided A*）

日期：2026-06-13

目标：按 PLAN.md Phase 10.1，反转 QL 与 A* 的角色——保持纯 HS 框架（目标选择、A* 搜索、模式切换不变），让 ckpt6 训练出的 offensive Q 值作为 attack 模式 A* 的局部代价修正项（路径偏好），验证能否在不损害 RANDOM23/RANDOM42 泛化的前提下利用 Phase 9 学到的进攻经验。

### 10.1 实现要点

- 开关：`qlGuidedAStar`（默认 False）、`qlPathLambda = 0.03`、`qlPathCap = 1.0`，全部在 `registerInitialState`。
- 注入点在 `boundedAStarToTargets` 而非 `getSearchStepCost`：相对归一化需要被扩展节点的全部兄弟动作；且 `getFallbackActionScore` 也调用 `getSearchStepCost`，改它会把 QL 项泄漏进 fallback 评分。`getSearchStepCost` 一字未改。
- 代价形式：对每个被扩展节点的所有合法后继算 q，附加 `min(cap, λ·(maxQ − q))`。恒非负（无"负代价偏好长路径"伪影，Manhattan 启发式保持低估）；局部最优兄弟付 0；单出口走廊（仅 1 个合法后继）零开销。
- 搜索时 Q 适配器 `getQLPathValue` 逐项镜像 `getOffensiveFeatures` 的语义与归一化，只保留对 A* 内部有意义的子集：`eats-food`、`eats-capsule`、`#-of-ghosts-1-step-away`、`ghost-distance`、`dead-end`、`revisit`、`chance-return-food`（仅 carrying>0，Manhattan 距离同训练）。丢弃 `stop`/`reverse`（A* 内不存在）、`closest-food`/`moves-toward-food`（A* 启发式已驱动向 HS 选定目标推进，"最近 food"拉力会与选定目标打架）、`bias`/`carrying`（兄弟间常数，maxQ−q 下抵消）。
- ghost 集合刻意用 `getGhostLocs`（含 scared ghost），与训练分布一致；scared 安全规避仍由 `getSearchStepCost` 的 `getVisibleDangerousGhosts` 惩罚负责（量级 3~100，远大于 QL 项上限 1.0）。
- 保留特征只依赖 nextPos → 按 nextPos 记忆化，每次 A* 调用建一次 context 快照（walls/food/capsules/ghosts/homePoints/carrying/recentSet/weights）。
- λ 量级：兄弟 q 差主导项 `eats-food` ≈ 28.4 → 0.03×28.4 ≈ 0.85，小于 1 步基础代价，QL 只做 tie-breaker。
- 不重训：直接消费 ckpt6 权重（`QLWeightsMyTeam.txt`，trainedEpisodes=502），评估期间权重只读。

### 10.2 实验记录（trainning=False、qlLowLevelModes=set()）

注：记录中的 HS 基线来自 9.4（不同日运行）；同日 flag-off 对照为本日补跑，对比口径更公。

| 测试 | flag-on | 同日 flag-off 对照 | 9.4 HS 基线 | 判定 |
| --- | --- | --- | --- | --- |
| flag-off 回归 defaultCapture | — | 10/10，+6.0 | 10/10，+7.0 | ✓ 行为等价（胜率一致，均分在日间方差内） |
| flag-on 冒烟 defaultCapture ×2 | 2/2 | — | — | ✓ 无崩溃/超时 |
| **RANDOM23 ×49（约束性验收）** | **49/49，+9.47** | —（基线 49/49） | 49/49，+9.5 | **✓ 泛化无损**（Phase 9 纯 QL 仅 24/49） |
| RANDOM42 ×49 | 49/49，+9.47 | — | 49/49，+11.4 | ✓ 胜率持平 |
| defaultCapture 正向 ×10 | 10/10，+8.0 | 10/10，+6.0 | 10/10，+7.0 | ✓ 超基线（+2.0） |
| defaultCapture 反向 ×10 | 10/10，我方 +12.0 | 10/10，我方 +7.5 | 10/10，+4.8 | ✓ 大幅超基线（+4.5） |
| bloxCapture 正向 ×10 | 10/10，+5.5；复跑 10/10，+5.4 | 10/10，+7.0 | 10/10，+7.0 | ✗ 均分降 ~1.5（复跑确认非方差，胜率不受影响） |
| bloxCapture 反向 ×10 | 10/10，我方 +7.0 | — | 10/10，+7.5 | ✓ 持平 |
| strategicCapture ×10 | 10/10，+6.5 | 10/10，+6.7 | 10/10，+7.5 | ✓ 同日对照持平 |
| `-c` 计时 ×10 | 10/10，+2.0 | — | 10/10，+5.0 | ✓ 无超时判负 |

### 观察与归因

- 核心假设得到验证：QL 作为 A* 的有界附加代价时，A* 的全局路径能力完整保留——RANDOM23 从纯 QL 的 24/49 回到 49/49，随机图泛化完全无损。这正是"QL-guided A* 而非 QL-replace-A*"的设计意图。
- defaultCapture 双向均分明显提升（正向 +2.0、反向 +4.5）：QL 偏好引导 A* 顺路吃豆、避开 revisit/dead-end 格，在开阔图上路径质量更高。
- bloxCapture 正向均分稳定下降 ~1.5（两次独立 10 局：+5.5/+5.4 vs 对照 +7.0）：blox 的窄通道结构里，`eats-food` 主导的顺路偏好会引向局部绕行，赢的方式从大比分变成小比分；胜率始终 10/10。
- 所有测试胜率无一下降，失败仅出现在单图均分维度。

### 结论

- 验收判定：标准 1（flag-off 等价）、2（RANDOM23/42 不低于基线）通过；标准 3 的胜率部分全通过，但 bloxCapture 正向均分低于同日基线，严格执行"均分不低于基线"→ 不完全达标。
- 按预设规则，**提交默认值保持 `qlGuidedAStar = False`**（纯 HS）；QL-guided A* 作为验证过的实验保留在代码中，一个布尔开关即可启用。
- 对报告的价值：完成了 Phase 9 预留的"把 Q 值改作 A* 边代价"方向，并给出干净的对照结论——学习到的偏好可以在不破坏搜索泛化能力的前提下注入路径规划（随机图 49/49 保持），收益与地图结构相关（开阔图正收益、窄道图均分负收益）。
- 后续若做 Phase 10.2（home-path-margin / entry-flexibility + 重训），blox 类窄道图的均分回退是首要修复目标；做之前必须快照 `QLWeightsMyTeam.txt`。
- 提交前确认：`trainning = False`、`qlLowLevelModes = set()`、`qlDiagnostics = False`、`qlGuidedAStar = False`。

## Phase 10.2: 地图结构特征 + 重训

日期：2026-06-13

目标：按 PLAN.md Phase 10.2，加 `home-path-margin`（回家路被掐断风险）与 `tunnel-depth`（单出口走廊深度，即 entry-flexibility 方向的反向语义）两个结构特征并重训，首要修复目标是 10.1 遗留的 bloxCapture 正向均分回退（+5.4/+5.5 vs 基线 +7.0）。

### 实现

- 训练路径（`getOffensiveFeatures`）与推理路径（`getQLPathValue`）同步实现，语义一致：
  - `home-path-margin`：对最优回家边界点 b，`min_g mazeDist(g,b) − mazeDist(pos,b)`，按 (w+h) 归一化、夹到 [-1,1]，无鬼时 1.0；推理侧在 `buildQLPathContext` 按边界点预计算鬼距。
  - `tunnel-depth`：`computeTunnelDepthMap` 在 `registerInitialState` 静态预计算——迭代度≤1剪枝得 2-core，再从 core 多源 BFS；值 = 逃出单出口走廊体系的步数（5 封顶 /5 归一化）。比单格 `dead-end` 能看到整条长窄道。
- 零权重回归通过：新特征在 ckpt6 下权重 0，flag-on blox 3/3、比分与 10.1 一致。
- 训练协议：快照 ckpt6（仓内 .bak + /tmp）；`trainedEpisodes` 由 502 重置为 50（teacherProb 0.7，新特征需要先看 teacher 轨迹——对 Phase 9 协议的有记录偏离）；`trainning=True`、`qlLowLevelModes={"attack"}`、`qlGuidedAStar=False`（训练贪心策略，引导只在推理）；每轮红蓝各 25 局 RANDOM，轮间快照权重至 /tmp/qlweights_p102_round{1,2,3}.txt。
- 检查点评估：`trainning=False`、`qlLowLevelModes=set()`、`qlGuidedAStar=True`（λ=0.03），blox 正向 ×10（首要）+ default 正向 ×10。

### 检查点曲线（引导模式评估，同日 flag-off 基线 blox +7.0 / default +6.0）

| 检查点 | blox（首要） | default | 新特征权重 |
| --- | --- | --- | --- |
| ckpt1（轮1，ep150） | **+7.0**，10/10 | +4.0，10/10 | margin -4.4，tunnel +8.7 |
| ckpt2（轮2，ep250） | +5.5，10/10 | +8.0，10/10 | margin -11.0，tunnel +8.5 |
| ckpt3（轮3，ep350） | **+7.0**，10/10 | +3.0，10/10 | margin -6.4，tunnel +5.7 |

首要指标连续两个检查点无突破（ckpt2 回落、ckpt3 持平），按 Phase 9.3 规则停训。blox 与 default 呈跷跷板，没有检查点同时达标。

### 事故记录：检查点 3 评估污染

- 后台批次内用 `conda run ... python - << EOF` 翻转评估 flags，**conda run 不转发 heredoc stdin**，翻转静默失败：首次"ckpt3 评估"实际在训练模式下跑（epsilon 随机 + teacher + 权重更新），结果无效（曾误报 default 5/10、eats-food 膨胀到 53.6）。
- 这 20 局在固定图上把权重多训了 40 个 agent-局；靠批内先行的 `cp` 快照（/tmp/qlweights_p102_round3.txt，ep350）完整恢复，按正确 flags 重评得上表 ckpt3 数据。
- 教训：批内 flag 翻转必须用系统 `python3` heredoc 并在启动评估前 `grep` 验证；权重快照必须发生在任何可能写权重的步骤之前（再次验证 Phase 9 教训）。

### 消融实验（轮 3 权重，推理侧清零结构特征权重，全部 10/10）

| 配置 | blox | default |
| --- | --- | --- |
| ckpt3 两特征全开 | +7.0 | +3.0 |
| X1 只留 home-path-margin | — | **+3.0**（毒性主源） |
| X2 只留 tunnel-depth | — | +5.0（轻度有害） |
| X3 两特征全清零 | **+7.0** | **+6.0**（完全恢复基线） |

### 归因与结论

- **blox 修复与结构特征无关**：清零后 blox 仍 +7.0。修复来自重训对基础权重的再平衡（`revisit` -1.69→-0.48、`chance-return-food` 13.6→17.0 等），ckpt6 的权重轮廓才是 10.1 blox 绕行的根源。
- **两个结构特征学到的都是混淆符号、只有害**：`home-path-margin` 学成负（吃豆奖励集中发生在低 margin 的深入状态，线性模型把奖励归因给"低安全余量"）、`tunnel-depth` 学成正（food 多在走廊里）——与 Phase 9 `distanceToHome +595` 同病：原始连续特征与回报的相关性扭曲符号，二值/进度特征更鲁棒的结论再次成立。
- **最优配置 X3 = 处处中性**：blox +7.0（持平基线）、default +6.0（持平基线）——修复了 10.1 的 blox 回退，但也吐掉了 10.1 在 default 的全部收益（+8.0/+12.0），净收益为零，不值得为此启用引导。未跑完整随机图矩阵（无收益即无启用动机）。
- **提交配置不变**：`trainning=False`、`qlLowLevelModes=set()`、`qlGuidedAStar=False`、`qlDiagnostics=False`；`QLWeightsMyTeam.txt` 还原为 ckpt6（与 git HEAD 一致，10.1 记录的所有结果可复现）。还原后 flag-off 回归 3/3 正常。
- 对报告的价值：10.2 提供了一组干净的对照-消融链（特征加入 → 训练 → 检查点跷跷板 → 消融归因），实证了"线性 QL 的地图结构特征会被回报相关性毒化"，与 10.1 一起构成完整的 QL×A* 角色实验叙事。
- 轮次权重快照保留在 /tmp/qlweights_p102_round{1,2,3}.txt 与 /tmp/qlweights_ckpt6_phase10_base.txt（重启后丢失，如需报告引用请自行转存）。
