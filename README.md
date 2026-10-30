# 小车调试助手

这是一个在电脑浏览器里使用的小车排查工具，面向机器人课程和教学实验。小车沿地面黑线行驶时，底部传感器会不断读取路面；即使电脑仍能连接小车，这组读数也可能已经停止更新。软件把这两件事分别检查，并给出后续检查步骤。

## 第一次查看

先看[作品介绍](docs/project-introduction.pdf)，再看[44秒功能演示](https://p3523190446-create.github.io/car-debug-assistant/)。想亲自试用时，按下方运行步骤启动软件；默认演示模式无需连接实物小车。

演示重点：电脑与小车的连接仍正常，但巡线读数已4.6秒未更新。软件指出停更、给出检查步骤，并在后续读数更新时记录恢复。

三个术语：主控是小车上负责收发状态的控制板；巡线传感器是读取路面、辅助识别黑线的模块；快照是某一时刻保存的一份状态记录。

## 运行

需要 Python 3.10 或更新版本，无第三方运行依赖。

Windows 可双击“启动助手.cmd”。也可在源码目录运行：

```shell
python app.py --open
```

浏览器地址：http://127.0.0.1:8788/ 。关闭服务窗口即可停止。

## 体验功能

1. 默认进入示例模式，选择“巡线数据过期”，点击“巡线怎么了？”查看字段与检查步骤。
2. 点击“数据恢复”，查看检查结果与恢复记录。
3. 点击“载入示例过程”，用上一帧、下一帧查看六帧状态变化。
4. 在“快照回放”导入 `examples/simulated-sequence.json`，查看120帧连续模拟过程。生成方式见 `examples/模拟数据说明.md`。
5. 点击“导出诊断报告”保存 Markdown 报告，或点击“导出本机记录”保存 JSON。

视频及示例使用程序生成的数据，实车诊断效果仍待验证。示例输入由软件实际计算，不作为实车测量结果。

## 连接已有控制台

将 `runtime.example.json` 复制为 `runtime.json`，填写设备状态服务的地址。这里的“控制台”指已有的小车调试程序，它负责和硬件通信；本工具从中读取状态。服务需提供 `GET /api/status`（只读状态接口）。也可指定配置文件：

```shell
python app.py --runtime runtime.json
```

只支持本机 HTTP 接口。工具只读取状态，不占用串口、不发送车辆控制命令。没有状态服务时可以使用示例模式或导入快照。

下列名称是供接入开发者使用的字段，不影响示例体验。状态字段为 `connected`、`link_age_ms`、`age_ms`、`line.valid`、`line.age_ms`、八项整数的 `line.raw`、`line.digital_mask`、`capabilities.drive_control`。完整样例见 `examples/demo-sequence.json`。

## 检查规则

- 主控通信年龄小于3000毫秒，巡线组数据年龄小于1500毫秒；两类数据分别检查。
- 缺失或格式不正确的字段显示“未确认”。未知帧不会关闭此前的问题。
- `drive_control` 表示接口能力，不能据此判断车辆的运动许可。
- 读数有效只表示字段和数据年龄通过检查，不代表车辆已经完成行驶验证。

## 测试

在源码目录运行：

```shell
python -m unittest -v test_diagnostics.py test_sessions.py
python examples/generate_simulation.py
```

第一条运行26项测试，第二条重新生成120帧模拟输入并核对2次异常与2次对应恢复。

## 文件与许可

`app.py` 提供本机服务；`diagnostics.py` 实现状态规则和问答；`sessions.py` 分析快照序列；HTML、CSS、JS提供浏览器界面。`/walkthrough` 是软件演示视图。

项目采用 MIT 许可，见 `LICENSE`。贡献说明见 `CONTRIBUTING.md`。
