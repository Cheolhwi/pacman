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
