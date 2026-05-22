# G1 23DOF 实机启动与手柄操作说明

本文档用于指导第一次接触 G1 23DOF 实机控制的操作者完成以下事情：

1. 在电脑终端启动实机控制程序。
2. 处理已知的 DDS 动态库版本冲突问题。
3. 使用手柄让机器人站立、进入速度控制、触发动作和安全退出。

## 1. 操作前检查

启动控制程序前，请先确认：

- 机器人已上电，急停状态正常。
- 机器人周围留有足够空间，尤其是踢腿和冲拳动作方向。
- 操作者可以随时接触急停或停止控制。
- 手柄已连接并能正常使用。
- 实机上的动作配置文件已经更新到需要使用的版本。
- 第一次测试时，建议安排一名观察人员在机器人侧面协助看护。

## 2. 手柄按键名称

本文档统一使用下面的按键名称：

| 文档名称 | 配置文件中的名称 | 说明 |
| --- | --- | --- |
| `L1` | `LB` | 左上肩键 |
| `L2` | `LT` | 左扳机键 |
| `R1` | `RB` | 右上肩键 |
| `R2` | `RT` | 右扳机键 |
| `start` | `start` | 开始键 |
| `select` | `select` | 选择键 |
| `F1` | `F1` | 手柄 F1 键 |
| `A` | `A` | 右侧 A 键 |
| `B` | `B` | 右侧 B 键 |
| `X` | `X` | 右侧 X 键 |
| `Y` | `Y` | 右侧 Y 键 |
| `↑` | `up` | 十字键上 |
| `↓` | `down` | 十字键下 |
| `←` | `left` | 十字键左 |
| `→` | `right` | 十字键右 |

## 3. 实机控制程序启动

在电脑上打开终端，并进入实机控制程序目录：

```bash
cd /home/unitree/KKlyh/unitree_rl_mjlab/deploy/robots/g1_23dof/build
```

启动控制程序：

```bash
./g1_ctrl --network=eth0
```

其中：

- `g1_ctrl` 是实机控制程序。
- `--network=eth0` 表示使用 `eth0` 网卡与机器人通信。

程序正常启动后，再进行手柄操作。

## 4. 已知动态库冲突问题

### 4.1 典型报错

如果启动时出现类似下面的报错：

```text
undefined symbol: ddsi_sertype_v0
```

这通常不是动作配置文件问题，而是 DDS 动态库版本冲突。

常见原因是：

- 编译 `g1_ctrl` 时使用了一套 CycloneDDS 动态库。
- 运行 `g1_ctrl` 时又从其他路径加载了另一套 `libddsc.so` 或 `libddscxx.so`。

### 4.2 先检查当前加载的库

进入控制程序目录：

```bash
cd /home/unitree/KKlyh/unitree_rl_mjlab/deploy/robots/g1_23dof/build
```

执行以下检查命令：

```bash
ldd ./g1_ctrl | grep -E "dds|ddsc|unitree|iceoryx"
echo $LD_LIBRARY_PATH
sudo ldconfig -p | grep -E "ddsc|ddscxx|unitree"
```

重点看：

- `libddsc.so` 实际加载到了哪个目录。
- `libddscxx.so` 实际加载到了哪个目录。
- `LD_LIBRARY_PATH` 中 DDS 相关路径是否正确。

### 4.3 临时修复方式

在当前终端执行：

```bash
cd /home/unitree/KKlyh/unitree_rl_mjlab/deploy/robots/g1_23dof/build

export LD_LIBRARY_PATH=/usr/local/lib:/home/unitree/cyclonedds_ws/install/lib:/usr/local/cuda-11.4/lib64:$LD_LIBRARY_PATH
```

然后再次检查动态库加载路径：

```bash
ldd ./g1_ctrl | grep -E "dds|ddsc|unitree|iceoryx"
```

确认加载路径正确后，再启动控制程序：

```bash
./g1_ctrl --network=eth0
```

注意：

- `export LD_LIBRARY_PATH=...` 只对当前终端会话生效。
- 如果新开一个终端后又出现相同报错，需要在新终端重新执行这条 `export` 命令。

## 5. 机器人状态切换

控制程序启动后，机器人操作按下面顺序进行。

| 当前状态 | 手柄操作 | 目标状态 | 用途 |
| --- | --- | --- | --- |
| `Passive` | `start` | `FixStand` | 从被动状态进入固定站立 |
| `FixStand` | `F1` | `Velocity` | 进入速度控制 |
| `FixStand` | `select` | `Passive` | 退出站立，回到被动状态 |
| `Velocity` | `select` | `Passive` | 停止当前控制，回到被动状态 |

### 推荐启动顺序

1. 启动 `g1_ctrl`。
2. 确认机器人周围安全。
3. 按 `start`，让机器人从 `Passive` 进入 `FixStand`。
4. 等待机器人站稳。
5. 按 `F1`，进入 `Velocity`。
6. 在 `Velocity` 状态下触发动作。

## 6. 动作触发按键

只有在 `Velocity` 状态下，下面的动作触发按键才生效。

| 手柄操作 | 动作 |
| --- | --- |
| `R1 + A` | `merged_motion__01_dance1_subject2_150_700_cont_mask_inter0` |
| `R1 + B` | 护花使者 `huhuashizhe_23dof_omni` |
| `R1 + X` | 大花轿 `dahuajiao_even_23dof_modified` |
| `R1 + Y` | Bruce Lee 动作 `bruce_lee_pose` |
| `R1 + ↓` | 倒马动作 `daoma_23dof_gmr` |
| `R1 + ←` | Charleston 舞蹈 `Charleston_dance` |
| `R2 + A` | 勾拳 `Hooks_punch` |
| `R2 + B` | 侧踢 `Side_kick` |
| `R2 + X` | 马步冲拳 `Horse-stance_punch` |
| `R2 + Y` | 回旋踢 `Roundhouse_kick` |

## 7. 动作执行中如何退出

机器人执行 Mimic 动作时：

| 手柄操作 | 功能 |
| --- | --- |
| `F1` | 退出当前动作，返回 `Velocity` |
| `select` | 退出当前动作，返回 `Passive` |

动作播放完成后，配置会自动返回 `Velocity`。

## 8. 新手最常用操作流程

### 8.1 启动并执行一个动作

1. 打开终端。
2. 执行：

   ```bash
   cd /home/unitree/KKlyh/unitree_rl_mjlab/deploy/robots/g1_23dof/build
   ./g1_ctrl --network=eth0
   ```

3. 如果出现 `ddsi_sertype_v0` 报错，按本文档第 4 节修复动态库路径后重新启动。
4. 控制程序正常运行后，按 `start`。
5. 等机器人固定站稳后，按 `F1`。
6. 选择一个动作，例如：
   - `R2 + X`：马步冲拳。
   - `R2 + Y`：回旋踢。
   - `R1 + X`：大花轿。
7. 动作结束后，机器人自动回到 `Velocity`。

### 8.2 立即停止当前控制

按：

```text
select
```

机器人会返回 `Passive`。

如果机器人姿态异常、周围有人靠近或动作风险变高，应优先停止控制。

## 9. 安全注意事项

- 不要在机器人还没站稳时连续触发动作。
- 踢腿、侧踢、回旋踢等动作前方和侧方必须留出安全距离。
- 不熟悉动作幅度时，先用低风险动作验证控制链路。
- 现场有人靠近机器人动作范围时，不要触发动作。
- 机器人状态异常时，先按 `select` 回到 `Passive`，必要时使用急停。

## 10. 快速备忘

| 目标 | 操作 |
| --- | --- |
| 启动控制程序 | `./g1_ctrl --network=eth0` |
| 被动到站立 | `start` |
| 站立到速度控制 | `F1` |
| 返回被动状态 | `select` |
| 动作中返回速度控制 | `F1` |
| 动作中返回被动状态 | `select` |

