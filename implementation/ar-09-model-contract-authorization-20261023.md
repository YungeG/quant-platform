# AR-09追加范围与分支发布授权

用户在上一轮两项明确询问后回复“允许”。据此，本轮获得：

1. 追加新版模型实验合同并实施训练/评估解耦；保留两类样本的事前预约、Backtest模型实际可用时点校验、完整任务闭包和旧合同/凭证字节。
2. 推送Backtest、Research、Validation、Promotion整改分支及Platform集成分支。**不授权改动子仓库远端main**，没有force push/删除分支/真实市场或AR10授权。

这是对范围和执行的授权，不虚构用户签署了尚未生成的fixture hash。主控负责提出确切新接口、独立复核、形成READY符号包、实施和实际验收；不能让writer自行选择架构，也不能因为获得范围授权就宣布验收通过。

## 本轮执行路径

- 在既有ExperimentSpec@1（普通/模型）及@2（target）之外增加显式新版本；旧schema与canonical payload/ref保持不变，不删除旧membership约束。
- 新版把声明样本全集与生成Trial的评估子集分开；FeatureBuild/ModelTraining继续按ModelBuildPlan预约训练slice，Trial只按新评估集合展开。所有Source/OOS声明与实际reader/ref/时钟一致，不能倒填模型available_at或在旧slice标签下运行后续数据。
- 不新增金融公式、重复simulator、实际训练/行情任务或模型准备失败假ref。采用既有执行与只读provenance verifier。
- 独立审查新合同后冻结精确symbols/write sets，再启动实施；先小型合成闭环，再受影响leaf/default root全套。旧15项失败日志及NOT_READY材料保留。
- 最终leaf commit经测试/复核后推整改分支并核实确切SHA可达；随后完成干净组合验证与Platform集成分支发布。

## 已发生的独立发布

Backtest `ea957d59527e93765681d85c7a2f3fd83e6356a0`已通过3299项完整测试（2项原有skip）及独立复核。授权后先执行同目标dry-run，再推送并通过ls-remote验证：

`origin/impl/ar-backtest-release-20261022` → `ea957d59527e93765681d85c7a2f3fd83e6356a0`

没有修改远端main。证据在执行目录的`backtest-publish-dry-run.log`、`backtest-publish.log`和`backtest-published-ref.txt`。其他leaf与root尚不在此记录中声称已发布。
