# 上海住房公积金制度深度实证研究（2015—2025）

以2025年为核心，审查上海住房公积金的资金流动、福利分配、住房金融效率与治理机制。研究使用2015—2025年年报、2022—2025年16区完整月度表、财政预算与决算、政策原文及上海统计公报。**这是独立公开资料研究，不是官方审计意见；没有满足因果识别条件的地方不报告政策净效应。**

## 核心结果

| 2025年指标 | 官方年报值 |
|---|---:|
| 缴存额 / 提取额 | 2,663.65 / 1,842.64亿元 |
| 年末缴存余额 / 个贷余额 | 9,466.59 / 6,197.93亿元 |
| 个贷率 | 65.47%（2016年为102.39%） |
| 贷款发放 / 回收 | 869.60 / 863.61亿元，净新增5.99亿元 |
| 年末存款 / 增值收益 | 3,287.72 / 114.94亿元 |

来源：[上海市住房公积金2025年年度报告](https://www.shzfgjj.cn/html/newxxgk/ndbg/228312.html)。年度核心77个数字已在11份官方原始HTML对应标签附近核对，记录见[年度来源审计表](data/processed/annual_source_audit.csv)。

**跨表口径线索。** 四年区月表共768条，2022—2025年区表归集低于年报缴存额分别92.52、105.55、118.33、131.61亿元；差额接近同年缴存人利息支出，但每年仍有约6—7亿元未解释。四年区表提取均与年报在舍入范围内一致。不得将归集差额称为资金缺失；需要官方逐项调节表。

**新增：实际结息口径桥接。** 用上海公积金每年6月30日结息公告而非年度利息费用对照，2022—2025年的区表/年报差额减去同年结息金额后，仅剩1.54、2.55、2.41、2.34亿元待解释。结息账户数与年度实缴人数是不同对象，不能把其差额当作失业或封存人数。详情见[结息桥接研究](reports/interest_settlement_bridge_2022_2025.md)。

**分配与选择。** 2024年高收入者在年度实缴人群占8.12%，在新贷款借款职工占14.43%，后者构成占比为前者1.78倍。缺少购房资格与申请人数，不能将其解读为获贷概率。2025年单位类别和收入组披露变粗，机关、国企、民企的真实单位缴存福利仍不可识别。

**季节性与制度机制（已升级）。** 2022—2025年16区×4年共64个区年，**全部在4月、9月达到提取额最高的两个月**。上海公积金中心2023年实施细则第九条明确规定年冲4月或9月批次；2022年4月官方通知也记载年冲批次。2025年两个月占全年提取27.85%，同期归集占17.00%，剔除黄浦后提取占28.82%。这有力支持年冲安排作为机制解释，但**尚不能据此估计真实年冲业务金额或因果效应**。详见[制度与季节性实证](reports/seasonality_mechanism_2022_2025.md)。

**风险与治理。** 2021—2025年风险准备金计提约为当年公积金业务增值收益的80%。2024及2025年机构决算和2025年预算已归档；两年财政拨款额与年报管理费上缴额在年报舍入范围内接近，符合管理费经财政上缴再拨付的制度路径，但仍需交易台账逐笔核销。2026年修订条例[单独比较](policies/legal_comparison.md)，不追溯用于2025年。

## 最新可验证交付

[GitHub Actions](https://github.com/1998x-stack/shanghai-hpf-research/actions/workflows/ci.yml) 每次构建运行99项年度原始字段、768条区月表、CSV/JSON重建差异和Excel语义测试。**CI下载包** `shanghai-hpf-validated-research` 包含由当前代码即时重建的Excel、数据、计算日志及图表，保留30天；仓库提交的历史Excel是发布快照，不保证包含其后最新计算公式。获取时请以与对应提交SHA匹配的CI产物为准。

## 研究交付

- [完整研究报告](reports/full_research_report.md) · [摘要](reports/executive_summary.md) · [证据等级](reports/findings_and_evidence.md) · [当前局限](reports/limitations.md)
- [四年16区月度面板分析](reports/longitudinal_panel_2022_2025.md) · [2025年逐月复核](reports/monthly_panel_2025.md)
- [Excel工作簿](outputs/shanghai_hpf_research.xlsx)：年度、区月原值、公式计算、财政账、群体构成、敏感性、来源与缺失清单
- [原始来源台账](sources/manifest.csv)：79份原件的机构、网址、发布日期、期间、获取日、版本和SHA-256；原始文件见 [`sources/original/`](sources/original/)；另4份6月结息公告仅有官方URL和已核对数值，尚无原始HTML快照
- [数据缺口登记](data/processed/data_gaps.csv) · [信息公开申请草案](reports/information_requests.md)（未提交）
- [资金比率图](outputs/figures/loan_ratio_2015_2025.png) · [月度提取季节性图](outputs/figures/withdrawal_seasonality_2023_2025.png)

## 复算

```bash
python -m pip install -e '.[dev,analysis]'
python -m hpf_research.audit
python -m hpf_research.source_validation --check all
python -m hpf_research.interest_bridge
python -m hpf_research.seasonality
python analysis/scripts/build_outputs.py
python -m pytest -q
```

重新抓取官方月报：`python -m hpf_research.collect_monthly --year 2024`，可选2022、2023、2024、2025。现有数据和图表可离线复算；重采会读取当前官网版本；若来源变更或产生不同CSV，脚本默认拒绝覆盖旧快照，须先人工保存版本并复核。[方法与口径](docs/METHODOLOGY.md)说明原始值、年度流量、期末存量、年内累计、月度差分与不同人群分母。

## 可复现数据契约

- 年报原件业务章节内提取9项字段×11年=99项，逐字段比对；区月表48份×16区=768行，从归档原HTML独立复解析。
- 来源台账逐行检查12列Schema、SHA-256（仅已归档文件）、URL与状态；故意修改核心数字、单位、区域名和日期的测试应失败。
- 场景假设保存在 [`config/analysis_scenarios.json`](config/analysis_scenarios.json)，历史证券化调整保存在 [`data/raw/loan_adjustments_2015_2025.csv`](data/raw/loan_adjustments_2015_2025.csv)，不得将假设参数称为实际政策效果。
- CI重建派生CSV/JSON并对照Git已提交文件；Excel和图片做语义/结构测试，不以二进制字节相等作为必要条件。

## 研究边界

- 四年区月覆盖率为768/768；区级归属不是居民居住地。
- 2024—2025单位性质分类断点不作臆测映射；群体单位缴存金额、申请审批漏斗、资产期限现金流和机构管理费上缴与财政拨付的交易台账仍是关键缺口。
- 存款余额不等于闲置资金；单位缴存不是财政补贴；贷款利率差情景不是实际财政成本。
- 部分年报细分财务指标仍需逐格复核，最终政策因果结论须等待合格对照或行政汇总数据。

本仓库不隶属上海市公积金管理中心。研究文字与图表按[CC BY 4.0](LICENSE)开放，代码按[MIT](LICENSE-CODE)开放；官方原件仍归原权利主体。欢迎附来源、日期和口径的复核与更正。
