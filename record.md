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

## Phase 11: Context-gated QL-guided A*（实际收敛为 eats-food 剔除）

日期：2026-06-13

目标：按 PLAN.md Phase 11，先确诊 10.1 遗留的 bloxCapture 正向均分回退（+5.5 vs flag-off +7.0）的元凶 feature，再决定门控设计；不重训、不动 ckpt6 权重，全部改动限定在推理侧。

### 实现：消融开关（取代批间文件 flag 翻转）

- 新增环境变量 `QL_PATH_ABLATE`（逗号分隔 feature 名），在 `registerInitialState` 读入 `self.qlPathAblateFeatures`，仅在 `buildQLPathContext` 的只读权重快照里把命名特征清零——训练路径与权重文件完全不受影响，默认空集时行为与改动前逐位一致。
- 动机：10.2 的 conda heredoc stdin 事故说明批间翻转文件 flag 是事故面；环境变量随命令显式传入，已验证 `conda run` 正确转发。

### 11.0 消融矩阵（flag-on，ckpt6 权重，bloxCapture 正向 ×10）

| 配置 | blox 均分 | 判定 |
| --- | --- | --- |
| A0 基准（全特征） | +5.3 | 复现 10.1 回退（+5.5/+5.4）✓ |
| A1 清零 `eats-food` | **+8.6** | **元凶，且剔除后反超 flag-off 基线** |
| A2 清零 `revisit` | +7.4 | 次要毒源 |
| A3 清零 `dead-end` | +5.7 | 无关 |
| A4 清零 `chance-return-food` | +5.6 | 无关 |
| A5 全清零（flag-off 等价） | +7.0（10 局全 7） | 精确复现 flag-off，机制自验证 ✓ |

### 重要副产物：10.1 的 default 收益被证伪为采样噪声

defaultCapture 比分呈 1/11 双峰（差 1 局均分变 0.5），n=10 的 ±2 均分差在噪声内。大样本复测：

| default 配置 | n=50 高分局率 | 均分 |
| --- | --- | --- |
| flag-off（全清零） | 56% | +6.6 |
| 只剔 `eats-food` | 52% | +6.2 |
| 剔 `eats-food`+`revisit` | 44% | +5.4 |
| 全特征 flag-on（n=20） | 55% | +6.5 |

两两差异均在 1.3 SD 内——**QL 引导在 default 上对所有配置都是中性**，10.1 记录的 +8.0/+12.0 收益是 n=10 的运气。同理 11.0 期间一次 D6 的 +4.0 低分也被 n=30 复跑（+6.3）证伪。教训：双峰分布的图，n=10 均分差 < 2 不能当信号。

### 11.1 方案判别与采用

- 方案 A（只剔 `eats-food`）：blox n=50 = **+8.68**，default 中性；
- 方案 B（剔 `eats-food`+`revisit`）：blox n=50 = +9.08，default 偏低 ~1.2；
- blox 上 A/B 差 1 SD 不可区分，default 偏向 A → **采用方案 A**：从 `getQLPathValue` 永久删除 `eats-food` 项（docstring 记录依据：顺路吃豆拉力与 HS 选定目标打架，与设计期丢弃的 `closest-food` 同失败族），`buildQLPathContext` 同步移除 food 快照。
- **原计划的 tunnel/carrying 门控全部不需要**：元凶剔除后处处不低于基线，无需上下文条件——比门控更简单、零运行时开销、无新超参。

### 11.2 验收矩阵（代码固化后，无环境变量，`qlGuidedAStar=True`，ckpt6）

| 测试 | 结果 | 对照 | 判定 |
| --- | --- | --- | --- |
| bloxCapture 正向 ×10 | 10/10，**+9.0** | flag-off +7.0 | ✓ 10.1 回退翻转为净增益 |
| bloxCapture 反向 ×10 | 10/10，我方 +8.2 | 基线 +7.5 | ✓ |
| defaultCapture 正向 ×20 | 20/20，+7.5 | 同日 flag-off +6.6 | ✓ 中性 |
| defaultCapture 反向 ×20 | 20/20，我方 +12.0 | 基线 +4.8~+7.5 | ✓ |
| strategicCapture ×10 | 10/10，+6.1 | 同日量级 +6.7 | ✓ 日间方差内 |
| **RANDOM23 ×49** | **49/49，+9.47** | 49/49，+9.5 | **✓ 约束性验收通过** |
| RANDOM42 ×49 | 49/49，+9.94 | 49/49 | ✓ |
| `-c` 计时 ×10 | 10/10，+4.0 | — | ✓ 无超时 |

### 结论

- **8/8 全通过，`qlGuidedAStar = True` 首次通过完整验收矩阵，具备提交默认资格**（10.1/10.2 均未达到）。提交 flags：`trainning=False`、`qlLowLevelModes=set()`、`qlDiagnostics=False`、`qlGuidedAStar=True`。
- 修正后的最终叙事：QL-guided A* 的真实收益在窄道图（blox +7.0 → +9.0），default/strategic 中性，随机图泛化无损。保留的 QL 信号（ghost 邻近、dead-end、revisit、带豆回家拉力）构成一个**风险感知 tie-breaker**；被剔除的 `eats-food` 证明"学到的最大权重 ≠ 对路径规划最有用的信号"。
- 对报告的价值：Phase 9（确诊方法）→ 10.1（角色反转）→ 10.2（结构特征毒化）→ 11（消融定位单一元凶 + 大样本证伪噪声收益）构成完整闭环；11 的消融矩阵 + n=50 复测是其中统计上最干净的一环。
- 副作用已还原：`score` 已 checkout，权重文件与 ckpt6 逐位一致（diff 验证），仓内备份已移出。快照与全部运行日志在 /tmp/qlweights_phase11_ckpt6_snapshot.txt、/tmp/p11_*.log（重启后丢失）。

---

日期：2026-06-13（Phase 12）

目标：按 PLAN.md Phase 12，在 QL = risk-aware tie-breaker 定位不变的前提下，回答"当前风险信号是刚刚好还是太弱"。基线 = Phase 11 终态（commit 09a2652），全程不训练、不动 ckpt6 权重。

### 12.1 λ 小扫描

实现：新增 `QL_PATH_LAMBDA` 环境变量覆盖 `qlPathLambda`（默认不设时行为逐位不变），沿用 `QL_PATH_ABLATE` 的事故面控制思路；已验证透过 `conda run` 生效、不设时无副作用。

smoke（bloxCapture 正向 ×10）与复测：

| λ | blox ×10 | blox ×30 | 判定 |
| --- | --- | --- | --- |
| 0.03 基线 | +8.6 | **+9.13**（30/30） | 同日对照 |
| 0.01 | +8.2 | — | 与基线不可区分 |
| 0.02 | **+4.9（3 平局）** | 复跑 ×10：**+3.5（5 平局）** | **可复现病态** |
| 0.05 | +9.8 | **+9.13**（30/30，与基线同均分） | 不可区分 |

- default ×20 @ λ=0.05：+7.5（与 Phase 11 持平，中性）。
- **结论：保持 λ=0.03（无改动默认胜出），未跑 RANDOM23（无采纳候选）。**
- 重要副产物：**λ=0.02 在 blox 上可复现地诱发 0-0 平局（两轮合计 8/20 局）**。机制（-q 诊断局）：终盘双 agent 长期处于 attack 模式（178 回合）但在己方半场绕环不过界——tie-break 强度在特定值附近会把兄弟动作排序扭成活锁环路。λ 响应**非单调**（0.01 好、0.02 坏、0.03/0.05 好），实锤 λ 不是可自由微调的旋钮，0.03 是已验证的安全点。

### 12.2 二值风险特征：前置诊断

实现：`QL_PATH_RISK_DIAG=1` 只读计数器（`getQLPathValue` 内统计、`final()` 打印 QL-RISK-DIAG 行），统计候选事件触发率与"hard penalty（`getSearchStepCost` 的 3~100 量级 ghost 惩罚）同格触发"重叠率。

| 候选 | blox 触发率 | RANDOM 触发率 | RANDOM hard 重叠 | 判定（规则：<1% 或重叠>90% 弃） |
| --- | --- | --- | --- | --- |
| tunnel-with-ghost-risk（tunnelDepth>0 且 ghostDist≤2·depth+2） | 0.06% | 0.22% | 56% | **触发率不足，弃** |
| home-cut-risk（carrying>0 且所有 boundary 安全余量 ≤1） | 0.12% | **2.7%** | **仅 9%** | 通过，进 12.2a |

home-cut-risk 触发集中在带豆深入局（单局最高 205 次），且 91% 触发在 hard penalty 半径外——形式上正是想要的增量信息。

### 12.2a home-cut-risk 手设权重 A/B（最终弃）

实现：`QL_PATH_RISK_W` 环境变量（默认 0 = 行为逐位不变），事件触发时给 q 加该权重。

- **第一轮 w=-2（对齐 dead-end 量级）：无效测量。** RANDOM23 ×49 on/off **逐局比分完全相同**（diff 验证）。原因是尺度错配：-2 经 λ=0.03 折算仅 +0.06 步代价，且 RANDOM23 系列图上每局完全确定（同图重跑计数逐位一致），微扰不足以翻转任何排序。
- **第二轮 w=-30（0.03×30=0.9，cap 饱和，唯一一次尺度修正，不扫档）：仍然零效应。** RANDOM23 ×49 逐局比分仍与 off 完全相同；blox ×30 = +9.0（vs 基线 +9.13，持平）；default ×20 = +6.0（vs +7.5，双峰噪声内偏负）。
- **判定：弃。** 即使把单个二值事件打到 cap 上限，验收图集上 A* 的决策没有一次被改变——被标记格子从不出现在"代价差 < cap 的竞争分支"上。

### Phase 12 总结论

- **保持 Phase 11 配置不变提交**：`qlGuidedAStar=True`、λ=0.03、cap=1.0、ckpt6 权重；12.1/12.2 的全部改动只留下三个默认无副作用的实验旋钮（`QL_PATH_LAMBDA` / `QL_PATH_RISK_DIAG` / `QL_PATH_RISK_W`）。
- 最终 flag-off 回归：blox ×10 = +8.2（10/10）、default ×10 = +5.0（10/10，双峰 n=10 噪声内），行为无恙。
- **正面叙事：风险信号栈已饱和。** 两条独立证据互证——(1) λ 在 ±60% 范围内（0.01~0.05）对 blox/default 无可测影响；(2) 一个语义合理、触发率合格、与 hard penalty 重叠仅 9% 的新二值风险信号，即使权重打满 cap 也无法改变验收图集上的任何决策。Phase 11 配置是 cap=1.0 框架内的局部最优，廉价增改没有收益空间。
- **负面警示：λ=0.02 活锁。** tie-break 信号不是单调旋钮，存在能诱发 0-0 活锁的刀锋区；这反过来支持"不再加强 QL 信号"的收尾决策。
- 12.3（路径段风险）触发条件不满足（λ 加大无收益、新特征无效应不是"延迟暴露"问题而是"决策不敏感"问题），按计划跳过。
- 副作用：`score` 已 checkout 还原；`QLWeightsMyTeam.txt` 全程未动（git status 验证）；运行日志在 /tmp/p12_*.log（重启后丢失）。

### Phase 12 附加：方向 1 对手多样性复测（零代码改动）

动机：Phase 12 的"风险信号饱和"结论全部条件于 staffTeam；用仓库现成的其他对手检验其可迁移性。flag-off 用 `QL_PATH_LAMBDA=0` 实现（短路 `qlPathLambda > 0` 守卫，与纯 HS 等价）。

对手盘点：`wise.py` 与 `berkeleyTeam.py` 逐位相同（弃用）；有效对手为 berkeleyTeam（1 攻 1 守反射式）与 bravo（双攻反射式，制造 staffTeam 评估未覆盖的双入侵局面）。

| 对手 | 图 | QL off | QL on | 判定 |
| --- | --- | --- | --- | --- |
| berkeley | blox ×10 | +11.9（10/10） | +12.5（10/10） | 噪声内中性 |
| berkeley | RANDOM23 ×25 | +11.44（25/25） | +11.08（25/25） | 噪声内中性 |
| bravo | blox ×10 | +10.2（10/10） | +7.4（9/10，一败） | 疑似信号 → 复测 |
| bravo | blox ×30 复测 | **+11.50（30/30）** | **+11.53（30/30）** | **n=10 信号被证伪，完全中性** |
| bravo | RANDOM23 ×25 | +11.56（25/25） | +11.56（25/25） | 逐局不同、均值巧合相同，中性 |

结论：

- **QL on/off 对 berkeley/bravo 全部中性，饱和结论在可得对手上可迁移**；n=10 出现的 -2.8 + 首败再次验证了小样本纪律（bravo 带随机 tie-break，单局分差 1~17，方差远大于 staffTeam，n=10 不可用）。
- 方法论限制（诚实记录）：repo 内全部对手（staff/berkeley/bravo）都被轻松碾压（除一局噪声败局外全胜，均分 +9~+12），没有任何对手能把比分压进"QL 项可能起作用的竞争区间"。**"重训对齐特征子集"与"目标层风险 tie-break"两个候选方向在本地缺乏能检验它们的尺子，留待真实比赛对手出现后再立项。**
- QL 线在本地评估体系内正式收官：Phase 7-9（QL 作为策略失败）→ 10-11（QL 作为风险 tie-breaker 成功）→ 12（通道饱和证明 + 对手迁移性验证）。
- 副作用：本轮零代码改动；`score` 已还原。日志在 /tmp/p12_d1_*.log、/tmp/p12_bravo30_*.log。

## Phase 13: 防守策略与 capsule 时机（HS 层首次系统优化）

日期：2026-06-13

目标：按 PLAN.md Phase 13，对从未走过验收矩阵的两层——防守策略与 capsule 时机——做先测量、后改动的系统实验。全部改动 env 门控（默认 off 行为逐位不变），以 Phase 11 终态（commit 09a2652）为回退点。

### 13.0 防守诊断计数器与基线触发率

实现：`HS_DEF_DIAG=1` 只读计数器（`updateDefenceDiagnostics`，`final()` 打印 DEF-DIAG 行），统计 foodLost / capsuleLost / invaderSteps / scaredChaseSteps / chaseSteps / chaseNoGain / scaredWindowSteps / scaredWindowFood / safeWindowSteps / capsuleDetours。

基线测量（bravo + staffTeam × blox/default，各 ×5，`-q`）：

| 病灶 | 证据 | 判定 |
| --- | --- | --- |
| C1 scared 窗口浪费 | staff default 高分局：窗口 39 步只吃 4-6 颗（3 颗即回家） | 触发合格，进 13.1 |
| C2 capsule detour | 计数器测不到，按 Phase 6 遗留 backlog 直接做 | 进 13.2 |
| D1 scared 追击 | 25 局仅 1 局 5 步（capsuleLost 仅 2/10 bravo 局） | 触发率低，降级实现 |
| D2 追而不获 | staff blox：chaseNoGain 13/18（70%）且每局丢 7 颗；bravo blox ~50% | 证据最强，进 13.4 |
| D3 capsule 卡位 | capsuleLost 2/10 | 触发率低，弃 |

### 实现（全部保留在代码中，默认 off）

- `HS_SCARED_WINDOW`（13.1）：对手 scared 期间 `shouldReturnHome` 的 carrying 阈值 3→8、跳过领先早退。窗口判定第一版用 min(scaredTimer) 几乎不触发（safeWindowSteps 3/39，防守吃掉 invader 即归零），改为 max(scaredTimer) > 回家距离+8 且附近无清醒危险 ghost。
- `HS_CAPSULE_DETOUR`（13.2）：ghost 压力触发回家时，若敌方半场 capsule 距离 ≤ min(回家距离, 6) 且未被把守，go_home 目标改为 capsule。
- `HS_SCARED_DEF`（13.3）：自身 scared 时防守目标改为距 invader 2-3 格的 shadowing 环（BFS），A* 对 invader 相邻格 +35 代价。
- `HS_INTERCEPT`（13.4）：追击连续 3 步无进展时，目标改为「我能不晚于 invader 到达的出口/capsule 中离它最近者」。

### 关键机制发现：scared ghost 之死是免费的

capture.py 核对（`checkDeath`，line ~682-725）：scared ghost 被 Pacman 碰撞后回出生点且 **scaredTimer 立即归零**，`KILL_POINTS = 0` 无分数代价。因此基线"自杀式追击"实为最优——以一次重生路程的代价解除 40 步 debuff；任何"scared 自保"都让防守端白白瘫痪 40 步。13.3 的设计前提被游戏规则直接证伪。

### 固定种子 A/B（`-f`，defaultCapture vs bravo，同一种子）

| 配置 | 结果 |
| --- | --- |
| flag-off | 红队 +8 |
| HS_CAPSULE_DETOUR | 红队 +8（未触发，逐位同 flag-off） |
| HS_SCARED_DEF | **被提前判负（对方回满 18 颗）** |
| HS_INTERCEPT | **被提前判负** |

### 批量 A/B（同日对照，n 见表）

| 测试 | flag-on | 同日 flag-off | 判定 |
| --- | --- | --- | --- |
| 13.3 bravo default ×5 | +5.2（4/5，有 -10） | +10.4 | **弃** |
| 13.3 bravo blox ×5 | +3.8（4/5，有 -24） | +12.0 | **弃** |
| 13.4 bravo default ×5 | **-2.2（2/5 胜）** | +10.4 | **弃** |
| 13.4 bravo blox ×5 | **-3.8（3/5 胜）** | +12.0 | **弃** |
| 13.1 staff default ×30 | **+4.6**（高分局 12/30，且全为 10 分） | **+7.67**（高分局 20/30，全为 11 分） | **弃**（~2.9σ） |
| 13.2 staff default ×30 | +7.0（18/60 agent-局触发） | +7.67 | 中性，不启用 |
| 13.2 staff blox ×30 | +8.2（**0/60 触发**，等价又一份 flag-off 样本） | +9.13 | 标定双峰噪声幅度（n=30 同配置 ±0.9） |

13.1 失败机制：窗口用 max(scaredTimer) 判定，但杀手是已苏醒重生的那只 ghost——收割越深，它越有时间回防在边界截杀，把 11 分局打成 1 分局（高分局率 67%→40%）；幸存的高分局也因晚回家少交 1 颗（11→10）。而 min 规则因"防守吃 invader 即归零"永不触发——该特性在两种判定下分别为有害/无效，无中间档。

13.4 失败机制：边界开口多，蹲守"离 invader 最近的出口"时它在别处自由吃豆；贴身追击虽然追不上，但持续驱赶使其无法安心吃豆——压迫本身就是防守。蹲点/追击在距离缩短时还会互相翻转，最坏两头空。

### 验收与收尾

- flag-off 逐位等价：`-f` 固定种子 default/blox 各 1 局，与 git stash 还原的 HEAD（Phase 11 终态）输出 **diff 完全一致**。
- `-c` 计时 ×5：5/5 胜，+7.0，无超时（新增 per-step 计算不影响时限）。
- 同日 flag-off n=30 对照本身即本轮回归：default 30/30 胜 +7.67、blox 30/30 胜 +9.13。
- **提交配置不变**：`qlGuidedAStar=True`、λ=0.03、ckpt6；新增 5 个默认无副作用旋钮（`HS_DEF_DIAG` / `HS_SCARED_WINDOW` / `HS_CAPSULE_DETOUR` / `HS_SCARED_DEF` / `HS_INTERCEPT`）。
- `score` 已还原；日志在 /tmp/p13_*.log（重启后丢失）。

### 结论

- **四个候选全部不采纳**：两个防守特性被机制级证伪（scared 之死免费 + 压迫即防守），scared 窗口在双峰图上显著有害，capsule detour 中性。本地评估体系内，Phase 4 的简单防守（贴身追击 + 失窃点调查）+ 现有 capsule 用法已是局部最优。
- 与 Phase 12 的"风险信号饱和"互为印证：HS 规则层和 QL 引导层在本地对手上都已无廉价收益空间；真正的改进空间只能由更强的真实比赛对手暴露。
- 对报告的价值：13.0 的测量先行方法 + 13.3 的"游戏机制证伪设计直觉"（scared 自保反而有害）+ 13.4 的"追而不获仍优于蹲点"是三个干净的否定性实验；本轮零回归风险（逐位等价验证）。

---

日期：2026-06-13（Phase 14）

目标：按 PLAN.md Phase 14，把防守评价从"抓到 invader"换成"降低对方有效收益"，并解决 12/13 暴露的尺子饱和问题。基线 = Phase 13 终态（HEAD ed0c415，flag-off 与 Phase 11 终态逐位等价）。

### 14.0 尺子升级：镜像对手 + 有效收益计数器

- **frozenTeam.py**：Phase 11 终态（commit 09a2652）myTeam 的 env 免疫副本（唯一 env 读取 `QL_PATH_ABLATE` 硬编码为空）。自检：`-f` 固定种子下 frozen-vs-frozen 与 myTeam(flag-off)-vs-frozen 对局逐位一致（仅队名头两行不同）。仅作本地评估工具，不进提交。
- 计数器（`HS_DEF_DIAG` 通道新增）：`invaderFoodReturned` / `invaderMaxReturn` / `invaderEscapes` / `invaderKills` / `invaderFoodDropped` / `pressureSteps` / `lossTrailSteps` / `supportSteps`。
- **计数器 bug 修复**：`chooseAction` 在 PDDL 计划为空时提前 return fallback，跳过诊断更新——爆破局大量走该路径，导致"被送回 35 颗"的局 `invaderFoodReturned` 计为 0。诊断调用补到 fallback 分支（mode="fallback"），行为零影响。
- 基线（n=10，`-q`）：
  - **镜像 blox = 本地最锐利防守仪器**：flag-off 红方 0/10 全败（-3.50，sd 0.53），foodLost 10.0 **全部**被安全送回（kills=0，escapes 6.5）——对自己的攻击，原防守整场零击杀、零拦截。蓝方固有优势 ~+3.4（反向基线 10/10）。
  - 镜像 default：10/10 全 0-0 平局（双方互锁），只能当回归守门。
  - bravo blox：防守已完美（returned 0 / kills 15），无改进空间；bravo default：returned 2.4/局。
  - **重要副产物：bravo flag-off 基线本身有爆破局**（blox 1-3/30、default 4-13/30 区间，单局 -25），Phase 12 的 30/30 +11.5 有日间运气成分；bravo 一切判断必须同日对照 + n≥30。

### 14.1 软压迫 → 14.1b 比分门控（最终采纳，默认开启）

实现：`getPressureTargets()`——追击距离 ≥2 时，目标从 invader 当前格改为"其合法邻格中最靠近其逃生出口（我方边界点中离它最近者）的那个"（限我方半场；并列取离我近者）；距离 ≤1 退回原行为直接吃。挂在 `getDefenceTargets` 追击分支，开关 `HS_PRESS_HOME`。

- **v1（无门控）**：镜像正向 -3.50→-1.50（5 平局，送回 10.0→4.0，chaseNoGain 7.0→3.5，固定种子 smoke 从 -4 变平局且送回归零）；但镜像反向 +3.4→+2.5——**压迫的代价是防守者整场被锁在追击中、不再释放进攻**，劣势侧净赚、优势侧净亏。bravo 中性（早期误判"回归"实为基线爆破局被漏解析）。
- 中间一版 carrying≥3 门控（误诊断驱动）：frozen 攒满 3 颗立即冲刺导致压迫窗口为 0（pressureSteps=0），镜像收益全失，**撤销**。
- **14.1b（score≤0 门控）**：仅在持平或落后时压迫，领先时退回原版贴身追杀。这正是 PLAN 14.4"比分驱动防守强度"预设的现象，被 14.1 的双向测量直接证实后合并实现。

14.1b 验收矩阵（全部同日对照）：

| 测试 | flag-off | 14.1b on | 判定 |
| --- | --- | --- | --- |
| 镜像 blox 正向 ×10 | -3.50（0/10，sd 0.53） | **-1.50（5 平局）** | ✓ 防守收益保留 |
| 镜像 blox 反向 ×10 | 我方 +3.40 | **+3.70** | ✓ 进攻代价消除 |
| 镜像 default ×10 | 10/10 平 | 10/10 平 | ✓ 守门 |
| bravo blox ×30 | +8.40（27/30，sd 10.23） | **+11.40（30/30，sd 0.72）** | ✓ 爆破局消失 |
| bravo default ×30 | +1.10（17/30） | **+8.03（26/30）** | ✓（合计爆破局 16/60→4/60） |
| staff blox ×30 | +9.40（30/30） | +9.80（30/30） | ✓ 中性 |
| staff default ×30 | +6.67（30/30） | +5.33（30/30） | ✓ 1/11 双峰 17vs13 高分局，~1.5σ 噪声 |
| staff strategic ×10 | +6.90 | +6.50 | ✓ 中性 |
| **RANDOM23 ×49** | 历史 49/49 +9.47 | **49/49，每局 +11.00** | **✓ 约束性验收** |
| `-c` 计时 ×10 | — | 10/10，无超时 | ✓ |

机制叙事：压迫式站位掐断的是"落后局的滚雪球"——爆破局里对手带豆滚大额送回，落后触发压迫后 invader 被钉在我方半场（固定种子局 281 步无法回家）；领先时门控自动让位给进攻释放，staff/优势侧零损耗。

**采纳**：`pressureHomeEnabled` 默认 on（`HS_PRESS_HOME=0` 可关断做 A/B）。最终验证：无 env 固定种子复现压迫局；`HS_PRESS_HOME=0` 与 Phase 11 终态逐位一致。

### 14.2 失窃点路径化（弃）

实现：`recentFoodLosses`（40 步窗口）+ `getLossTrailTarget()`——无可见 invader 且 ≥2 失窃点互距 ≤5 时，防守目标改为离失窃簇最近的边界 choke。触发率前置诊断大幅合格（flag-off bravo 局 130-160 步/局）。

- **镜像正向 ×10：-3.50→-6.00（5 局 -8），明确有害**；bravo default ×30 +6.77（vs +1.10）正向但按"任一仪器受伤即弃、不抢救"纪律**弃**。
- 失败机制与 13.4 同族：蹲簇入口 choke = 放弃对最新失窃点的即时调查，镜像攻击换个口子进就绕过了站位。旋钮 `HS_LOSS_TRAIL` 保留默认 off。

### 14.3 支援位（触发率不足，降级不做）

`supportSteps` 计数器（patrol 中且队友在 defence）：镜像 0 步/局（压迫开启后该局面不存在）、bravo ~12 步/agent 局（~4%）、staff ~7 步。决定性仪器上触发为零 + 无判别尺子 → 按 12.2/13.0 纪律记入 backlog，待真实对手。

### 结论

- **Phase 14 打破了 Phase 13"本地局部最优"的结论，但靠的不是新规则而是新尺子**：镜像对手暴露了"防守对自己的攻击零击杀零拦截"这一 staff/bravo 测不到的病灶；有效收益计数器把"压迫 vs 蹲点 vs 追杀"的取舍变成可测量。
- 14.1b 是 bloxCapture 协作分工（Phase 4）之后防守层第一个通过完整验收矩阵的采纳项，且其最终形态（比分门控）来自实验中测到的"压迫的进攻机会成本"——GPT 方案里的第一优先（软压迫）与第四优先（比分驱动强度）在数据驱动下合并成了一个特性。
- 提交配置：`qlGuidedAStar=True`、λ=0.03、ckpt6、**`pressureHomeEnabled=True`（新）**；其余旋钮默认 off（`HS_LOSS_TRAIL` / `HS_SCARED_WINDOW` / `HS_CAPSULE_DETOUR` / `HS_SCARED_DEF` / `HS_INTERCEPT` / `HS_DEF_DIAG`）。
- 副作用：`score` 已 checkout 还原；权重文件未动；frozenTeam.py 为新增本地评估工具（未提交）；运行日志在 /tmp/p14_*.log（重启后丢失）。

### Phase 14 附加：QL vs 纯 HS 镜像（用户提问触发）+ 14.1c 压迫保险丝

动机：frozenTeam 自带 `qlGuidedAStar=True`；做一个纯 HS 冻结副本（frozenHsTeam.py，仅 `qlGuidedAStar=False`），回答"QL 引导对强对手有没有价值"并检验 14.1b 的对手敏感性。

**发现 1：QL 价值首次被本地尺子测出。** 镜像 blox 交叉对局（同代理基线：红 -3.5 / 纯 HS 同代理 -2.8）：frozenQL 红方对 frozenHS = -1.0 ~ +0.8（两进程，含从劣势侧赢 5-8/10——同代理镜像从未出现过红方胜局）；反向 frozenHS 红方对 frozenQL = -2.5。Phase 12 在 staff/berkeley/bravo 上测不出的 QL 贡献，镜像尺子一次测出。

**发现 2：14.1b 对"风险中性硬闯型"攻击手存在失效模式。** myTeam(14.1b) 红方对 frozenHS = **-9.6（8 局 -12）**：主防（agent 2）压了 65 步但 HS invader 不吃软压迫——两趟硬闯各带 9 颗安全送回（esc 2 / ret 18），同时比分门控让防守者整场锁死（score 恒 ≤0），进攻只剩单人（仅 6 颗）。机制：**钉死效果依赖对手路径的风险规避**——QL 引导的 invader 不肯穿过危险格才被钉 281 步；纯 HS 的直接从侧格穿过。真实比赛中"简单坚决的 A*"恰是最常见对手类型，此弱点必须修。

**附带方法论发现：不加 `-f` 时 RNG 完全未播种**（capture.py 只在 `-f` 时 seed；myTeam 有 random.choice 兜底），固定图镜像局坍缩到少数吸引子（如 {-4,+2}），同配置两进程 ×10 均分可漂 1.8 分——固定图小样本结论必须意识到吸引子采样效应。

**14.1c 保险丝（采纳）**：压迫期间（pressureSteps>0 后）对手任一次成功送回（score 下降）→ 本局永久退回贴身追杀。机制驱动、零参数、单向触发；对 QL 型对手（esc=0）永不触发，钉死收益无损。

| 测试 | 14.1b | 14.1c | off | 判定 |
| --- | --- | --- | --- | --- |
| vs frozenHS 红方 | **-9.60** | **-2.20（n=20，9 平局）** | -1.0~+0.8 | ✓ 灾难清零，残差 ~1-3 为保险成本 |
| vs frozenHS 蓝方 | +2.0 | +2.0 | — | ✓ |
| vs frozenQL 红方 ×10 | -1.50（5 平） | **-1.50（5 平）** | -3.50 | ✓ 逐分一致 |
| bravo default ×30 | +8.03（26/30） | +6.67（24/30） | +1.10（17/30） | ✓ 噪声内 |
| bravo blox ×30 | +11.40（30/30） | +10.10（28/30，败局浅至 -10/-4） | +8.40（27/30，-25 级） | ✓ |
| staff default/blox ×30 | +5.33 / +9.80 | +5.33 / +9.40 | +6.67 / +9.40 | ✓ 双峰噪声内 |
| RANDOM23 ×49 | 49/49 | **49/49（+8.96）** | 49/49 | ✓ 约束验收 |

固定种子验证：QL 镜像 `-f` 仍平局（保险丝不触发，行为不变）；`HS_PRESS_HOME=0` 仍与 Phase 11 终态逐位一致。

结论：14.1 线最终形态 = **软压迫 + 比分门控 + 失效保险丝**。三个组件各对应一类对手暴露的失效模式（随机游走悬停→压迫保贴身；优势侧进攻锁死→比分门控；硬闯型压不住→保险丝），全部由仪器测出而非先验设计。frozenHsTeam.py 与 frozenTeam.py 同为本地评估工具。bravo 合计败局：off 16/60 → 14.1b 4/60 → 14.1c 8/60（保险代价），爆破深度 -25 → -10。

---

日期：2026-06-13（Phase 15.0：角色诊断尺子，先建尺子）

目标：按 PLAN.md Phase 15，为"对手行为驱动的自适应防守强度控制器"建在线信号 + effective-mode 角色诊断，并验证核心假说"信号能否分离对手类型"。零行为改动（`HS_DEF_DIAG` 通道只读计数器），回退点 = 14.1c 终态。

### 实现

- 新增 class 级 `diagEffMode = {index: (effectiveMode, carryingFlag)}`，让诊断能看到队友本步 effective mode（非 PDDL 高层动作——上一轮口头诊断抓错了层，这里修正）。
- `HS_DEF_DIAG` 新计数器：`oneInvaderSteps`/`twoInvaderSteps`（用 isPacman，无 5 格门控，每步精确）、`noAttackerSteps`（两 agent 均不产出进攻）、`bothDefendSteps`、`roleFlips`（本 agent attack↔defence 翻转）。
- flag-off 对 HEAD（14.1c）`-f` 固定种子逐位等价（诊断零行为影响，权威对照通过；早期对 /tmp 旧基线的 diff 是文件生成条件不同的假阳性）。

### 基线信号（×10，blox 主仪器；agent 0 计数）

| 对手 | 均分 | 1-inv步 | 2-inv步 | banking(ret) | roleFlips | noAttacker |
| --- | --- | --- | --- | --- | --- | --- |
| bravo | +7.9 | 107 | **76.7** | 0 | 99 | 139 |
| staff | +9.0 | 19 | 6 | 5.5 | **15** | 100 |
| 镜像 QL | **-1.8** | 226 | 5.4 | 4.8 | **241** | 64 |
| frozenHS | -1.6 | 228 | 10.8 | 9.6 | **176** | 121 |

（default 图：bravo 2-inv 78 / roleFlips 67；staff 2-inv 1.5 / roleFlips 11——同序。）

### 两个结论：一个证实、一个推翻

- **✅ 信号能分离对手类型（控制器有可用输入）**：`twoInvaderSteps` 干净拎出 bravo 双攻（76-78 vs 其余全 <11）；`roleFlips` 干净拎出镜像病态（241/176 vs staff 15）。控制器方向在本地立得住。
- **❌ 推翻了 plan 写入的 bug 假设**：原断言"双防塌缩 = 无人进攻（noAttackerSteps 高）且只在镜像高"。数据完全相反——`noAttackerSteps` 普遍高，且**输球的镜像最低（64）**、赢球的 staff 是 100，与胜负不相关。"没人进攻"不是病灶。
- **真病灶 = roleFlips（角色抖动）**：镜像 agent 0 单独在 ~300 步翻 241 次攻防角色（~80% 步）。机制精确化：PDDL 派 defend → `getEffectiveLowLevelMode` 每步用瞬时距离经 `shouldReleaseDefenceForAttack` 重算翻成 attack → 下步又翻回，**无滞回导致 241 次抖 + 每次翻转重置 lowLevelPlan**，攻防两头都做不好。人工观战看到的"两个都在防守"是这种高频抖动的视觉表现，不是静态双防。

### 对 15.1 的修正

- **修复重心从"强放一个进攻手"改成"角色滞回/承诺，掐掉抖动"**；防守人数自适应（bravo→2 防）降为次要。
- bravo 的 roleFlips（99）虽高但 2-inv 也高（77）——churn 由真实双威胁正当化，不该被滞回压掉；判别式应是 `roleFlips 高 AND twoInvaderSteps 低` = 病态抖动（镜像），而非单看 roleFlips。
- 15.0 是"先建尺子"方法论的又一次兑现：诊断在写任何修复代码前就推翻了一个看似合理的病因假设（与 13.3 scared 自保、14.0 误判 bravo 回归同族）。
- 副作用：`score` 已还原；诊断计数器以默认 off 旋钮保留；日志在 /tmp/p15_*.log。

### Phase 15.1: 角色滞回（四变体全判弃，保留 15.0 诊断）

目标：按 15.0 修正后的重心，给攻防角色加滞回掐掉 roleFlips=241 抖动。挂点 `getEffectiveLowLevelMode` 的攻防出口，开关 `HS_ROLE_CTRL`（默认 off 逐位等价）。主尺子镜像落后场景，守门 bravo/staff 全图 + RANDOM23。

四个变体，每个都通过逐位等价，但批量 A/B 各自只是把回归挪个位置：

| 测试（×10/×30） | off | 15.1a lock | 15.1b debounce | 15.1c score门控 | 15.1d score+invader |
| --- | --- | --- | --- | --- | --- |
| 镜像正向（落后） | -0.90 | +1.80 | 0.00 | **+2.50** | +1.80 |
| 镜像反向（我蓝） | +3.40 | +0.20✗ | -0.10✗ | +2.80 | — |
| vs frozenHS（落后） | -1.60 | +2.0 | **-5.80**✗ | -0.80 | **-4.80**✗ |
| bravo blox | +10.10 | +10.33 | — | **+4.33**✗ | +11.83 |
| bravo default | +6.67 | +0.47✗ | +2.70 | +7.17 | +9.33 |
| staff blox | +9.00 | +3.30✗ | +10.00 | **+14.00** | +9.13 |
| staff default | +5.33 | — | — | +6.00 | — |

- **15.1a commitment-lock（commit K=10 步）**：落后局赚（镜像/frozenHS +3.6），但 K 步失聪让领先局崩——staff blox +9.4→+3.3、bravo default +6.67→+0.47。机制：staff 仅 15 次切换但每次锁 10 步=半场不响应。
- **15.1b debounce（连续 D=3 步才切换、不锁）**：治好 staff blox（+10.0），但太松——追着 frozenHS 硬闯抖动，frozenHS +2.0→**-5.80**（比基线还差）。
- **15.1c score 门控（仅 score≤0 时承诺）**：三版首个全面不亏的，落后承诺/领先全速响应，staff blox 打出 +14（开局承诺进攻早建大优势，同日 off 复核 +9.0 确认 delta 真实）；RANDOM23 49/49、计时 0 超时。**但 bravo blox 单独塌（+10.10→+4.33）**——落后时承诺进攻正好放任 bravo 双攻偷豆。
- **15.1d（score≤0 且 liveInvaders≤1 才承诺）**：修好 bravo blox（+11.83），但 frozenHS 又塌到 **-4.80**——frozenHS 在 1/2 入侵间摆动，门控让承诺反复开关，比不开更糟。

### 结论：判弃 Phase 15.1，保留 14.1c

- **四变体四种回归 profile，回归像打地鼠换位置消不掉**。根因：**角色抖动对某些对手是 bug（自镜像僵局），对另一些是 feature（真实攻击手快速攻防切换）**，而区分条件（score、入侵数）与对手类型纠缠太深，几个门控分不开——再加门控就是在 3-4 个本地对手上过拟合（负面清单明令禁止）。
- 与 14.1 的对照很说明问题：14.1 的三次迭代每次**严格变好**直到全清（v1→carrying→score），值得继续；15.1 的四次迭代只是**平移回归**，是该停的信号。
- **重要再认识**：人工观战看到的"双防守"是自镜像特有的退化现象，不是普适 bug；"修复"它反而伤真实对手。镜像在这里是一把**过敏的尺子**——它报的警只对它自己成立。这反过来支持 14.1c 的"压迫"设计（落后才压、领先释放）已是本地局部最优。
- **保留**：15.0 只读诊断（`diagEffMode` + roleFlips/liveInvaders/noAttacker 等计数器）——它既正确诊断了抖动、又正确证明了每个修复失败，是有价值的仪器，默认 off 零影响。**回退**：15.1 全部行为代码（`applyRoleHysteresis` 删除，`getEffectiveLowLevelMode` 还原），逐位等价 HEAD 验证通过。
- 提交配置不变：14.1c 终态（`pressureHomeEnabled=True` + 保险丝）。`score` 已还原；frozenHsTeam.py 保留为本地评估工具；日志 /tmp/p15*.log。
