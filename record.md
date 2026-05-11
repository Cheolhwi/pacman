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
