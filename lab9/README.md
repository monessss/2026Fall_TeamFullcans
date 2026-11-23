# Lab7 / VNAV 2023 Lab 9 — Visual SLAM

| Deliverable | 交付文件 |
| --- | --- |
| D1–D7 报告、图、表 | [report/lab9_report.pdf](report/lab9_report.pdf) |
| D1 信息矩阵与边缘化（个人） | [报告 §1.1](report/lab9_report.pdf) |
| D2 位姿图初始化（个人） | [报告 §1.2](report/lab9_report.pdf) |
| D3 ORB-SLAM（个人） | [报告 §1.3](report/lab9_report.pdf) |
| D4 LSD-SLAM（个人选做） | [报告 §1.4](report/lab9_report.pdf) |
| D5 纯旋转优化（个人选做） | [报告 §1.5](report/lab9_report.pdf) |
| D6 原始轨迹与真值对齐（团队） | [报告 §2.2–2.3](report/lab9_report.pdf) |
| D7 LDSO 与三系统对比（团队选做） | [报告 §2.4](report/lab9_report.pdf) |

本课程 Lab7 对应 MIT VNAV Lab9，因此保留目录名 lab9。
本 fork 的修订基于团队提交 37e5d5fe3c7d5dd31f3e9ae8e6d8af4d24975e46。

## 已提交轨迹的结果

| 比较 | 参考点 / 对齐 | ATE RMSE |
| --- | --- | --- |
| D6 ORB-SLAM3 | body/IMU，SE(3) | 0.038662 m |
| D6 Kimera-VIO | body/IMU，SE(3) | 0.176039 m |
| D7 ORB-SLAM3 | cam0，Sim(3) | 0.020378 m |
| D7 Kimera-VIO | cam0，Sim(3) | 0.170543 m |
| D7 LDSO | cam0，Sim(3) | 0.025309 m |
| D7 LDSO，无回环修正输出 | cam0，Sim(3) | 0.038288 m |

D7 使用 LeftCameraParams.yaml 的 T_BS，先将机体位姿和真值转换到 cam0：
T_WC = T_WB T_BC，再进行时间关联和全局对齐。相机距机体原点约 6.89 cm，
不能用一个全局对齐替代这个随姿态旋转的偏移。LDSO 的原始位姿已经是相机位姿。
D6 保持机体参考点。所有原始轨迹保留；新图表来自重新评估，不代表重新运行了 SLAM。

原始完整运行日志未随团队提交保存。历史笔记中的 16 次回环、具体运行时间、逐帧完成情况
不能由稀疏轨迹独立验证；报告已说明这一限制。新启动脚本会保留日志与运行状态摘要。

## 仅用仓库数据复核结果

评估工具在宿主机运行，需要 Python 3.11+；无需 Docker 或再次下载图像数据。

```bash
cd lab9
python3 -m venv .build/venv
source .build/venv/bin/activate
python -m pip install -r scripts/requirements-evaluation.txt
bash scripts/evaluate.sh --results
bash scripts/evaluate_d7.sh
python scripts/make_figures.py
python scripts/verify_results.py
python -m unittest discover -s scripts/tests -v
bash scripts/build_report.sh
```

构建报告需要 latexmk、XeLaTeX 及报告使用的 LaTeX 宏包。
Debian/Ubuntu 可安装 texlive-xetex、texlive-latex-extra、latexmk。
PDF 编译产物写入 .build/report，只有最终 PDF 复制到 report/。

## 从图像重新运行

需要 Docker Engine、可用的 X11 显示，以及 EuRoC MH_01_easy 解压目录：
~/datasets/vnav/MH_01_easy/mav0。可通过 VNAV_DATASET_ROOT 指定 datasets/vnav 的替代目录。
运行前确认当前用户可以执行 docker。镜像顺序构建，不要并行。

```bash
cd lab9
docker build -t orbslam:latest -f Dockerfile_ORBSLAM3 .
docker build -t kimera:latest -f Dockerfile_KIMERA .
bash scripts/run_slam.sh
bash scripts/evaluate.sh
bash scripts/build_ldso.sh
bash scripts/run_ldso.sh
bash scripts/evaluate_d7.sh
python scripts/make_figures.py
python scripts/verify_results.py
bash scripts/build_report.sh
```

- ORB-SLAM3 新构建固定到 4452a3c4ab75b1cde34e5505a36ec3f9edcdc4c4。
  历史镜像的 ORB 源码版本未记录；这个 pin 只用于后续构建，不反推历史运行版本。
- Kimera-VIO 固定到 980ff72d547417ec0b7c79446ae9c7fab7630adf。
  Kimera-RPGO 固定到 8c5e163ba38345ff583d87403ad53bf966c0221b；其余构建依赖并非全部锁定。
- LDSO 固定到 9b0c48cfd3b3ee95a8dbf1aef2371ed4fca6f81a；Pangolin 使用 v0.6。
- 普通 Docker 主机直接使用本地路径和 host 网络。共享 Docker socket 的嵌套容器需显式设置
  VNAV_HOST_HOME（宿主机上对应容器 $HOME 的路径）；还可分别设置 VNAV_HOST_LAB_DIR、
  VNAV_HOST_DATASETS、LAB9_NET。脚本不再默认使用队友机器路径或专属网络。
- X11 需要允许运行容器的用户访问显示；权限设置由宿主机管理，启动脚本不自动扩大显示访问权限。
- Kimera 的 YAML 兼容处理只替换硬链接副本中的 YAML，不改原始图像、IMU 或真值数据。
- 新运行退出非零或轨迹验证失败时，不覆盖 results/ 中的已归档轨迹。输出目录里的旧文件
  不会被当作本轮成功结果。
- LDSO 评估运行默认 NOGUI=1，自然退出后检查状态；NOGUI=0 时需手动关闭完成后的显示窗口。
  不再依据“文件已出现”强行终止进程。
- 新运行日志和 *_run.json 保存在 results/d6 或 results/d7；它们不是对历史日志的重建。

## 现场演示

在依赖、镜像和数据已准备好的可交互终端执行：

```bash
bash scripts/run_demo.sh
```

演示显示 GUI 和已有轨迹图；中途停止的演示结果不用于评分指标。

## 目录

- report/：最终 PDF、LaTeX、参考文献和引用的图。
- results/d1/：spy 模式与符号消元结果。
- results/d6/：原始 body 轨迹、真值、D6 评估。
- results/d7/：LDSO 原始输出和 D7 评估；cam0 转换轨迹与真值按需生成到 .build/d7_frames/。
- results/validation_summary.json：基于当前归档数据的独立数值复核及文件哈希。
- scripts/：运行、转换、评估、回归检查和报告构建。
- notes/：历史笔记及本次修订的验证范围。
