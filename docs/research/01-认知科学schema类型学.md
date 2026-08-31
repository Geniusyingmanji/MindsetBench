# 数学模型之外的可跨域迁移图式：认知科学文献调研报告

调研目的：为跨学科 mindset 迁移 benchmark 寻找"数学模型类图式"（守恒量、混合分布、信噪比等）之外的、有文献依据的可迁移认知图式类型。以下六节每节按（a）分类内容、（b）超出数学模型的部分、（c）机器可判题目设想、（d）出处组织。

## 一、Gentner：结构映射理论与关系范畴（relational categories）

（a）Gentner (1983) 的结构映射理论（SMT）把知识表征拆为三层：对象属性、一阶关系、高阶关系（关系之间的关系，典型是 CAUSE、IMPLIES）。可迁移的是关系结构而非对象特征，且受"系统性原则"约束。后续的"关系范畴"研究（Gentner & Kurtz 2005; Goldwater & Schalk 2016）把由共同关系结构定义的范畴系统化，例如"桥""屏障""催化剂""瓶颈"。Rottman, Gentner & Goldwater (2012) 给出因果系统范畴——共因、共果、因果链、正反馈、负反馈——实验显示专家按因果结构而非学科域给现象分类（如把生物学和经济学的正反馈现象归为一类），新手按学科域分类。

（b）SMT 是"图式载体"的元理论：任何高阶关系系统都可迁移，不限于数量关系。因果系统范畴虽可形式化为图，但认知内容是定性因果拓扑；"催化剂""瓶颈"这类关系范畴是纯定性的角色结构。

（c）题目设想：给 5 段跨域现象描述（体温调节、央行加息抑通胀、麦克风啸叫、谣言扩散、捕食者-猎物循环），要求选出与目标现象共享因果结构的那一个（负反馈 vs 正反馈 vs 因果链，答案唯一），干扰项与目标同学科但异结构——复刻 Rottman et al. 的专家-新手分离信号。

（d）出处：Gentner 1983, Cognitive Science 7:155-170；Gentner & Markman 1997；Rottman, Gentner & Goldwater 2012, Cognitive Science 36:919-932；Goldwater & Schalk 2016, Psychological Bulletin 142:729-757。

## 二、Cheng & Holyoak：语用推理图式（pragmatic reasoning schemas）

（a）Cheng & Holyoak (1985)：人在现实情境中用"由目标类别定义的一般化规则集"推理。核心为许可图式（要做行动 A 必须先满足前提 P，含四条产生式规则）和义务图式（若情境 C 成立则必须做 A）。解释了 Wason 选择任务的内容效应。近亲：Cosmides (1989) 的社会契约/查骗者图式。

（b）完全超出：道义（deontic）规则推理——违规检测、许可/义务/禁止的角色结构——不含数量、概率或方程，且与形式逻辑（实质条件句）系统性偏离。

（c）题目设想：跨域违规检测题——给一条许可规则（"进入 BSL-2 区必须完成生物安全培训"），列 4 个待核查对象（对应 P、非P、A、非A），问最少必须核查哪两个（答案唯一：做了 A 者、未满足 P 者）。同一图式可换皮到签证、处方、代码合并权限。

（d）出处：Cheng & Holyoak 1985, Cognitive Psychology 17(4):391-416；Holyoak & Cheng 1995, Thinking & Reasoning 1(4)；Cosmides 1989, Cognition 31:187-276。

## 三、Lakoff & Johnson：意象图式；Talmy：力动态

（a）Johnson (1987)、Lakoff (1987)：意象图式是知觉-运动经验中反复出现的动态模式，二十余种：CONTAINER、SOURCE-PATH-GOAL、FORCE、BALANCE、LINK、CENTER-PERIPHERY、VERTICALITY、CYCLE 等。Talmy (1988) 力动态：主动体（Agonist）与拮抗体（Antagonist）各有趋动/趋静倾向与相对强弱，组合生成 causing/letting/hindering/helping/preventing/overcoming 等语义原语，并统一解释情态动词语义。

（b）完全超出：具身-拓扑图式，只有定性结构（内外、沿路径、力的对抗方向与强弱序）。容器图式支持拓扑传递性推理；力动态支持定性因果归类（"防洪堤阻挡趋动河水"与"审查制度阻挡言论"同构）。

（c）题目设想：力动态归类题——给源域描述（"堤坝挡住了本要泛滥的河水"），从 4 个跨域候选中选出力动态结构相同者（正确项："专利壁垒挡住了本要进入市场的竞争者"；干扰项分别是 letting、helping、overcoming 结构）。

（d）出处：Johnson 1987, The Body in the Mind；Lakoff 1987, Women, Fire, and Dangerous Things；Talmy 1988, Force dynamics in language and cognition, Cognitive Science 12(1):49-100。

## 四、Johnson-Laird：心理模型；Polya：启发式

（a）Johnson-Laird (1983)：演绎推理靠构建情境的心理模型（可能性集合），应用于三段论、空间关系、时间推理与多模型反例搜索；难度由需维护的模型数预测。Polya (1945)《怎样解题》：四阶段框架 + 67 条启发式词典（倒推、辅助问题、特殊化/一般化、分解重组、对称性、类比等）。

（b）心理模型是可能性枚举/反例搜索图式，适用于任何定性描述，无需数学。Polya 启发式是域中立的搜索策略图式，但注意：它是策略（procedure）而非情境结构，与"图式=情境的数学模型"不同层，应作为独立维度（strategy transfer）而非 schema transfer。

（c）题目设想：多模型定性推理题——给 5 条约束（"A 在 B 之后到场""C 与 D 不同时在场"…），问"E 是否必然在 F 之前"，三值答案（必然/必然否/不确定）唯一；换皮为供应链到货、地质层序即成跨域题。

（d）出处：Johnson-Laird 1983, Mental Models, Harvard UP；Polya 1945, How to Solve It, Princeton UP。

## 五、教育心理学：问题图式分类

（a）Riley, Greeno & Heller (1983)：加减法应用题分 Change/Combine/Compare/Equalize 四图式，按未知量位置细分难度。Marshall (1995) 扩为五种语义情境（Change/Group/Compare/Restate/Vary），提出图式的四种知识成分（识别、精化、规划、执行），是 schema-based instruction 研究线的基础。

（b）这一支基本仍在数学模型范畴内。价值在方法论：(i) "图式识别"与"图式执行"是可分离测量的能力，前者才是迁移瓶颈；(ii) 成熟的干扰项设计传统——同表面故事、异图式的配对题。

（c）题目设想：图式识别题（不要求解题）——4 道表面情境相同但深层图式不同的题 + 1 道表面不同但图式与题 2 相同的题，指出"哪两道解法结构相同"。

（d）出处：Riley, Greeno & Heller 1983, in The Development of Mathematical Thinking, Academic Press；Marshall 1995, Schemas in Problem Solving, Cambridge UP。

## 六、非数学类比的实证研究：历史、道德、法律

（a）四条证据线：
1. 收敛图式——Gick & Holyoak (1983)：从"分兵合围要塞"与放射治疗故事归纳"多个弱力从不同方向同时汇聚于同一目标"图式；单源迁移率约 30%（基线 10%），双源比较后显著提升。
2. 历史类比——Khong (1992) Analogies at War：越战决策中 Korea/Munich/Dien Bien Phu 类比执行六项诊断功能；Spellman & Holyoak (1992) 海湾战争实验证明普通人做历史类比遵守映射一致性约束（一对一、关系一致），映射有可预测的多解分布。
3. 道德类比——Campbell & Kumar (2012) 道德一致性推理（天桥 vs 扳道）；Holyoak & Powell (2016) deontological coherence 约束满足模型。
4. 法律类比——Holyoak & Simon (1999) 融贯性推移；Spellman & Schauer：判例检索由表面相似驱动、辩护需关系层证成，"区分先例"即指出破坏映射的结构差异。

（b）全部超出：共同内核是角色关系系统的映射与一致性约束，不含数值。

（c）题目设想：角色映射题——给源案（慕尼黑：希特勒-张伯伦-捷克-英法）与目标案实体列表，锚定 X→希特勒，问"保持关系一致时 Y 必须映射到谁"（约束下唯一）；或法律"区分"题——从 4 个事实差异中选出唯一破坏先例核心关系结构的差异。

（d）出处：Gick & Holyoak 1983, Cognitive Psychology 15:1-38；Khong 1992, Analogies at War, Princeton UP；Spellman & Holyoak 1992, JPSP 62:913-933；Campbell & Kumar 2012, Ethics 122(2):273-312；Holyoak & Powell 2016, Psychological Bulletin 142(11)；Holyoak & Simon 1999, JEP: General 128:3-31。

## 汇总表

| 图式家族 | 代表结构 | 超出数学模型 | 机器可判性 | 关键出处 |
|---|---|---|---|---|
| 因果系统范畴 | 正/负反馈、共因、共果、因果链 | 是（定性因果拓扑） | 高：结构归类 | Rottman et al. 2012 |
| 语用推理图式 | 许可、义务、查骗者 | 是（道义规则） | 高：违规检测 | Cheng & Holyoak 1985 |
| 意象图式/力动态 | 容器、源-路径-目标；阻挡/放行/助推/压服 | 是（定性力代数） | 中高：构型归类 | Johnson 1987; Talmy 1988 |
| 心理模型 | 可能性枚举、反例搜索 | 是 | 高：三值判定 | Johnson-Laird 1983 |
| 算术问题图式 | Change/Combine/Compare | 基本否（方法论价值） | 高：识别配对 | Riley et al. 1983; Marshall 1995 |
| 收敛策略图式 | 多弱力汇聚 | 是 | 中 | Gick & Holyoak 1983 |
| 角色系统映射 | 历史/政治类比的角色对应 | 是 | 高：强制对应 | Spellman & Holyoak 1992 |
| 一致性/先例图式 | 同案同判、区分先例 | 是 | 中高 | Holyoak & Simon 1999 |

三点提炼：(1) 最即插即用的非数学图式家族：因果系统范畴、许可/义务图式、角色系统映射；(2) 力动态与意象图式提供封闭的定性结构标签集；(3) Polya 启发式与问题图式属不同层（策略 vs 情境结构），应作独立维度。
