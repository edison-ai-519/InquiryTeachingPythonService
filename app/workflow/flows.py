from copy import deepcopy
from typing import Any


STAGE_DIRECTIONS: dict[str, str] = {
    "observation_start": (
        "你要帮助教师完成情境创设与观察起步。\n"
        "1. 围绕学生可接触的真实现象或可模拟情境，先设计一个能激起好奇心的“认知诱饵”，让问题先被看见。\n"
        "2. 可以优先考虑失衡装置、异常对比、结果反常、明显缺口等素材，让学生意识到“这里有不对劲的地方”。\n"
        "3. 观察引导要植入“摹略思维”，即把观察变成有结构的记录，而不是随意浏览。\n"
        "4. 可配套观察任务单，明确学生要看什么、记什么、比什么，重点关注边界在哪里、什么在变化、什么保持不变。"
    ),
    "question_refine": (
        "你要帮助教师把零散发问提炼为有价值的核心问题，并先画清系统边界。\n"
        "1. 先梳理系统要素关系图，明确哪些是系统内变量、哪些是外部干扰、哪些是待验证对象。\n"
        "2. 用“小故 / 大故”来推进问题提炼：先找“缺少哪个条件就必然失败”的必要条件，再找“哪些条件同时具备就更可能成功”的充分条件。\n"
        "3. 引导学生把模糊提问改写成可探究、可验证、可操作的主问题，而不是停留在经验判断。\n"
        "4. 在表达上保持聚焦，帮助学生从“想到什么问什么”走向“围绕系统边界问为什么”。"
    ),
    "hypothesis": (
        "你要帮助教师把学生的猜想整理成多个可比较、可证伪的假设，并保留探索张力。\n"
        "1. 鼓励学生先发散，尽量提出不同解释路径，不急于过早收敛到唯一答案。\n"
        "2. 结合系统探索学习法，从系统、变量、关系、证据四个角度看待猜想，避免只凭直觉下结论。\n"
        "3. 借用墨家思维中的“察类明故”，引导学生区分现象判断、原因判断和机制判断，让猜想更接近可检验的命题。\n"
        "4. 可顺带比较哪些假设更容易被观察和测试，哪些假设虽然合理但暂时证据不足，以便后续进入实验设计。"
    ),
    "experiment_design": (
        "你要帮助教师把猜想落成低成本、可操作、可复现的测试方案。\n"
        "1. 优先明确测试目标、变量设置、对照条件、记录方式和安全边界，让学生知道“改什么、看什么、记什么”。\n"
        "2. 可以引导学生制作简单原型或小规模验证装置，用最小成本把关键变量显性化。\n"
        "3. 融入“研取思维”，强调真正的知识来自真实情境中的取舍与判断：证据支持哪个方案，为什么排除其他方案。\n"
        "4. 提前布防“试错”和“遇疑”，提醒学生把意外结果当作有价值的线索，并继续追问它为什么会发生。"
    ),
    "new_questions": (
        "你要帮助教师把测试中的异常结果、偏差和意外发现转化为新的探究机会。\n"
        "1. 重点不是立刻修正结果，而是先记录异常、对照现象、追踪原因，弄清它为什么和预期不同。\n"
        "2. 鼓励学生从“逢疑、循疑、遇疑、过疑”四个角度审视测试过程：哪里被表象带偏，哪里依赖了经验，哪里出现了意外，哪里推理跳步了。\n"
        "3. 用系统探索学习法把偏差重新放回系统中看，判断是变量设置问题、操作问题、测量问题还是原理问题。\n"
        "4. 把异常提炼成新的问题，帮助教师把一次测试延伸成下一轮探究的入口。"
    ),
    "conclusion": (
        "你要帮助教师把测试得到的证据整理成阶段性结论，并避免结论跳跃。\n"
        "1. 先把观察事实、实验数据、推理过程、阶段结论分开表达，确保学生知道自己是凭什么得出判断的。\n"
        "2. 用“小故 / 大故”回看证据链：哪些条件是结论成立的必要条件，哪些条件组合起来更接近充分条件。\n"
        "3. 借鉴墨家“以验定说”的态度，鼓励学生用证据说话，而不是用声音大小或经验权威定输赢。\n"
        "4. 结论要保留边界和条件，明确“在什么情况下成立、还缺什么证据、哪些地方仍然待验证”。"
    ),
    "extension": (
        "你要帮助教师完成总结、迁移与下一轮探究起点的设计。\n"
        "1. 先回看本轮形成的问题、证据、结论和遗留疑问，梳理出一条清晰的探究闭环。\n"
        "2. 把未解现象或可迁移情境转化为新的认知诱饵，让学生看到知识可以继续生长。\n"
        "3. 引导学生思考：同一原理还能在哪里用，条件改变后结论是否变化，哪些判断需要重新测试。\n"
        "4. 让教师把本轮经验沉淀成可复用的方法，而不是只停留在单次课堂结果。"
    ),
    "insect_material_collection": (
        "你要帮助教师把昆虫旅馆项目的起点落到真实环境中的自然取材。\n"
        "1. 引导学生从校园、社区或自然环境中寻找适合搭建昆虫旅馆的天然材料，如枯枝、竹节、松果、落叶、树皮等。\n"
        "2. 强调先判断材料是否安全、是否适合昆虫栖息，再决定是否收集，避免随意采摘、过度采集或破坏原有微环境。\n"
        "3. 鼓励学生把取材过程做成有结构的观察记录：材料来源、外形特征、可能用途、是否需要晾晒清理。\n"
        "4. 帮助教师把“找材料”设计成一次生态友好、证据导向的观察任务，而不是简单收集。 "
    ),
    "insect_habitat_needs": (
        "你要帮助教师判断本地昆虫可能需要怎样的栖息条件，并把观察边界说清楚。\n"
        "1. 本阶段面向本地昆虫开放观察，不预设单一目标物种，而是根据周边环境判断哪些昆虫更可能被吸引。\n"
        "2. 引导学生围绕干燥/潮湿、避光/向光、通风、遮挡、高低位置、邻近植物等条件分析栖息需求。\n"
        "3. 帮助教师明确观察边界：只做非侵扰式观察，不捕捉、不惊扰、不伤害昆虫，也不人为强行引入个体。\n"
        "4. 让学生把“可能会来哪些昆虫、为什么会来、需要什么环境”整理成可后续验证的判断。 "
    ),
    "insect_structure_design": (
        "你要帮助教师把昆虫旅馆的设计想法整理成可比较、可改进的结构方案。\n"
        "1. 围绕材料组合、孔洞大小、分层布局、遮雨结构、通风方式、固定方法等提出多个设计选项。\n"
        "2. 鼓励学生比较不同结构分别更可能吸引哪些本地昆虫，并说明判断依据，而不是只选一个直觉上好看的方案。\n"
        "3. 帮助教师把设计表达成可验证的猜想，例如不同孔径、不同摆放高度、不同遮挡程度可能带来什么差异。\n"
        "4. 保持设计低成本、可搭建、可后续优化，为后面的实际搭建和观察留下空间。 "
    ),
    "insect_build_and_sensing": (
        "你要帮助教师把昆虫旅馆的设计落成真实作品，并完成传感强化部署。\n"
        "1. 引导学生完成结构搭建，明确材料处理、固定方式、摆放位置与安全边界，确保旅馆稳定、适合长期放置。\n"
        "2. 默认纳入传感强化方案：至少配置温湿度传感器，并可根据条件扩展光照等观测项。\n"
        "3. 帮助教师说明传感器安装位置、记录频率、供电与防水防晒等实际问题，让数据采集具备可持续性。\n"
        "4. 强调传感器的作用是辅助理解环境变化与昆虫活动关系，而不是替代现场观察。 "
    ),
    "insect_settlement_observation": (
        "你要帮助教师把昆虫旅馆后的持续观察组织成非侵扰式、证据清楚的记录活动。\n"
        "1. 重点观察是否有昆虫自然入住、何时活动、活动痕迹如何变化，并与温湿度等环境数据建立对应关系。\n"
        "2. 强调不打扰、不伤害昆虫，不频繁搬动旅馆，不为了得到结果而人为干预昆虫行为。\n"
        "3. 引导学生把现场观察、图像记录、传感数据、阶段判断区分开表达，避免把猜测直接当成结论。\n"
        "4. 帮助教师梳理“看到了什么、记录到了什么、据此能先得出什么阶段性认识”。 "
    ),
    "insect_iteration_sharing": (
        "你要帮助教师把昆虫旅馆项目的观察结果转化为优化改造、展示分享和下一轮问题。\n"
        "1. 基于入住情况、活动痕迹和传感数据，判断哪些结构、材料或摆放条件值得保留，哪些需要调整。\n"
        "2. 鼓励学生提出有依据的优化方案，如调整孔径、改变朝向、增加遮挡、替换材料或改进记录方式。\n"
        "3. 帮助教师把成果表达成可展示、可分享的项目总结，包括设计思路、观察证据、改进判断和生态反思。\n"
        "4. 保留下一轮继续追问的问题，让项目形成'搭建—观测—优化'的持续迭代闭环。"
    ),
    "study_plan_design": (
        "你要帮助教师围绕研学目标与基地资源，设计完整的研学方案框架。\n"
        "1. 明确研学主题、学习目标、适用年级与课时安排，确保方案与课程标准对接。\n"
        "2. 结合基地特色资源（如自然生态、农业科技、历史文化等），设计核心探究任务与学习活动。\n"
        "3. 规划方案的整体结构：前期准备、实地活动、成果展示等各阶段的时间与内容安排。\n"
        "4. 预设学习产出形式（如研究报告、实践作品、汇报展示等），为后续阶段提供明确目标。"
    ),
    "study_docking_process": (
        "你要帮助教师完成研学方案与基地课程、学校教学需求的对接。\n"
        "1. 梳理基地现有课程资源与学校教学计划的匹配点，明确哪些内容可以整合、哪些需要调整。\n"
        "2. 设计详细的行程安排：交通方式、时间节点、分组方式、用餐与休息安排等。\n"
        "3. 制定安全预案：明确安全责任分工、应急处理流程、特殊学生关注事项等。\n"
        "4. 建立协作机制：学校教师、基地导师、学生小组之间的沟通方式与协作分工。"
    ),
    "study_project_implementation": (
        "你要帮助教师组织学生参与研学活动，并记录过程性证据。\n"
        "1. 引导学生按照方案开展实地活动，观察、记录、体验、探究，积累第一手学习证据。\n"
        "2. 关注学生的参与度、合作情况、问题解决表现，及时给予指导与反馈。\n"
        "3. 记录过程中的突发情况、学生反应、环境变化等，为后续总结提供真实素材。\n"
        "4. 收集学生的学习产出：观察记录、实验数据、访谈资料、照片视频等。"
    ),
    "study_result_summary": (
        "你要帮助教师整理研学成果与过程证据，形成总结报告与改进建议。\n"
        "1. 汇总学生在各阶段的学习产出，按照研学目标进行整理、分类与提炼。\n"
        "2. 组织学生进行成果展示与汇报，鼓励多样化的表达形式（如报告、作品、演讲等）。\n"
        "3. 引导学生进行反思：学到了什么、遇到了什么问题、如何解决的、还有哪些改进空间。\n"
        "4. 帮助教师形成研学总结报告，包括活动成效、经验提炼、改进建议，为后续研学提供参考。"
    ),
    "ancient_road_theme_goals": (
        "你要帮助教师把石佛岭古道跨学科素材转化为适合本班学情的课程主题与目标。\n"
        "1. 可从石灰岩与岩缝、岩缝植物、种子传播、古道排水与蹄窝、古道保护中组合主题，明确学段、课时、已有知识和课程产出。\n"
        "2. 根据场地与课时区分古道现场观察、校园观察和室内模型实验；没有现场条件时，不把实地访问设为课程前提。\n"
        "3. 小学阶段侧重观察、比较、记录和表达；中学阶段增加变量控制、数据图表、机制解释和证据评价。\n"
        "4. 将保护古道和尊重生境写入学习目标，确保课程问题可探究、活动可实施、成果可评价。"
    ),
    "ancient_road_field_observation": (
        "你要帮助教师把古道主题设计成有边界、可记录的现场观察任务。\n"
        "1. 按主题列出学生观察什么、测量什么、拍摄什么，以及观察点位、分组方式、时间和记录字段。\n"
        "2. 可观察岩石纹理与裂隙、植物所在微环境、种子形态、路面凹坑形态或排水痕迹；把观察事实与原因猜想分开。\n"
        "3. 明确保护要求：只观察、测量和拍照，不敲击、刻画、滴酸、掘根或带走石材、植物和种子；采样或设备使用须先取得许可。\n"
        "4. 为无法到场的班级提供照片、地图或安全替代材料，避免将现场进入设为唯一学习路径。"
    ),
    "ancient_road_model_experiment": (
        "你要帮助教师把古道现场问题转化为校园或室内可重复的模型实验。\n"
        "1. 根据主题设计低风险替代模型，例如用托盘和不同坡度比较排水，用替代材料研究凹坑形态，或用纸片模型比较种子下落。\n"
        "2. 明确研究问题、假设、自变量、因变量、控制变量、对照条件、材料、步骤和记录单位；定量实验至少重复三次。\n"
        "3. 为每个模型写清它模拟了什么、没有模拟什么，不能把模型结果直接当作古道历史事实的证明。\n"
        "4. 避免不必要的危险操作；涉及弱酸、刀具、加热或专业设备时，明确由教师控制并按要求配备防护。"
    ),
    "ancient_road_course_evidence": (
        "你要帮助教师组织古道跨学科课程实施，并保障过程证据完整。\n"
        "1. 生成课前准备、课堂/现场时间安排、学生小组角色、教师提示点和各阶段学习产出。\n"
        "2. 为学生提供统一记录表，记录日期、地点、天气、材料来源、仪器、单位、原始数据和异常情况。\n"
        "3. 将现场观察、室内模型、资料查阅和学生解释分别标记，避免不同来源的证据混为一谈。\n"
        "4. 对现场活动、样品采集、特殊器材和实验风险列出许可、成人监督与应急准备要求。"
    ),
    "ancient_road_evidence_analysis": (
        "你要帮助教师带领学生用证据检验古道主题中的解释，而不是把猜想当成结论。\n"
        "1. 整理原始数据并建议合适的表格、图表和比较方法，指出数据波动、测量误差和样本限制。\n"
        "2. 对蹄窝成因等历史解释，比较不同假设及其可观察证据，结论使用“支持、部分支持、不支持或证据不足”等审慎表述。\n"
        "3. 明确区分直接观察、实验结果、资料记载和推理；模型实验只能支持模型条件下的判断。\n"
        "4. 引导学生说明结论成立的条件、尚缺证据和下一步如何改进验证。"
    ),
    "ancient_road_outcomes_conservation": (
        "你要帮助教师把探究过程整理成跨学科成果，并落实古道保护意识。\n"
        "1. 根据课程目标生成研究报告、科学展板、工程模型或口头展示的结构和评价要点。\n"
        "2. 成果须呈现问题与假设、方法与变量、原始数据、图表、证据结论、局限和改进建议。\n"
        "3. 引导学生提出不损害古道与生境的保护建议，避免把采集、刻画或干预生物作为成果活动。\n"
        "4. 结合学段、课时和学生表现设计反思与后续问题，形成可复用的课程资料。"
    ),
    "ancient_road_home_question": (
        "你要帮助家长从石佛岭古道主题中找到孩子能在家庭场景探究的问题。\n"
        "1. 可围绕石灰岩纹理、岩缝植物、种子传播或古道排水等主题，转化为孩子能观察或比较的家庭问题。\n"
        "2. 结合孩子年龄、兴趣、可用时长、家庭空间、现有材料和成人陪伴；情况未填写时先采用普通家庭易获取的材料，不假定具体条件。\n"
        "3. 家庭活动不要求选择基地资料或前往古道；可自动参考相关基地知识并在回答中标明出处。\n"
        "4. 用开放问题支持孩子提出自己的猜想，不替孩子提前给出实验结论。"
    ),
    "ancient_road_home_model": (
        "你要帮助家长把古道现象转化为桌面或居家可完成的安全小模型。\n"
        "1. 优先使用纸张、托盘、少量清水、常见石材图片或正规购买的种子等易获取材料。\n"
        "2. 可设计纸片种子下落比较、托盘不同坡度排水观察、石材图片纹理比较或室内种子发芽观察。\n"
        "3. 步骤控制简单，适配家庭空间与活动时长；说明模型代表什么及其与真实古道环境的差异。\n"
        "4. 不要求攀爬、野外采样或使用危险设备，模型结果不能作为古道历史成因的直接证明。"
    ),
    "ancient_road_home_safety": (
        "你要帮助家长准备居家探究材料，并把成人责任和安全边界说清楚。\n"
        "1. 列出必需材料、可替代材料、准备步骤和活动结束后的整理方式，优先使用家中已有的低风险物品。\n"
        "2. 不安排采集古道石材、植物或野生种子，不使用酸液、刀具、加热、专业传感器或高处/临水环境。\n"
        "3. 明确哪些步骤须由成人操作或陪同，清水实验要控制水量并及时擦干，种子活动只在室内容器中进行。\n"
        "4. 安全说明应具体到本次活动，不用笼统的“注意安全”替代操作边界。"
    ),
    "ancient_road_parent_child_observation": (
        "你要帮助亲子共同完成观察和记录，让孩子承担主要的发现与表达。\n"
        "1. 把步骤拆成孩子可执行的小任务，例如观察、计数、计时、画图、比较或口述发现。\n"
        "2. 提供简短记录表或绘图提示，记录实验条件、每次结果和孩子注意到的差异；条件允许时可重复几次。\n"
        "3. 给家长提供不直接告知答案的引导问题，如“你发现哪里不同”“怎样比较才公平”“要不要再试一次”。\n"
        "4. 成人负责安全、材料准备和必要协助，不替孩子完成观察、记录或结论。"
    ),
    "ancient_road_home_reflection": (
        "你要帮助家长和孩子回顾家庭探究发现，并区分证据、猜想和模型局限。\n"
        "1. 用孩子能理解的语言整理观察记录，指出哪些结果重复出现、哪些结果不同以及可能原因。\n"
        "2. 鼓励孩子用自己的话或图画说明发现，并保留“不确定”“还想再试”的空间。\n"
        "3. 明确家庭模型只能说明本次材料和条件下的现象，不能据此断定真实古道的历史成因或生态机制。\n"
        "4. 生成简洁的家庭活动记录、亲子讨论问题和后续观察建议，并标注所引用基地资料出处。"
    ),
}


STAGE_DISPLAY_DIRECTIONS: dict[str, str] = {
    "observation_start": "从真实现象或模拟情境切入，设计能激发好奇的观察起点。",
    "question_refine": "围绕系统边界和小故/大故，把零散发问提炼成可探究的核心问题。",
    "hypothesis": "鼓励多路径猜想，整理成可比较、可证伪的假设。",
    "experiment_design": "把猜想落成低成本测试方案，明确变量、对照、记录与安全边界。",
    "new_questions": "把异常结果和偏差转化为新的探究机会，继续追问。",
    "conclusion": "基于证据整理阶段性结论，强调条件、边界与可验证性。",
    "extension": "总结探究闭环，迁移到新情境并生成下一轮问题。",
    "insect_material_collection": "从校园或自然环境寻找合适材料，强调生态友好、适度收集和用途判断。",
    "insect_habitat_needs": "面向本地昆虫开放观察，分析可能的栖息需求、摆放位置与观察边界。",
    "insect_structure_design": "比较旅馆结构方案，围绕材料、孔径、分层、遮挡与通风形成可验证设计。",
    "insect_build_and_sensing": "完成搭建并部署温湿度等传感器，组织可持续的环境数据采集。",
    "insect_settlement_observation": "在不干扰昆虫的前提下，结合现场观察和传感数据记录自然入住情况。",
    "insect_iteration_sharing": "根据观察与数据优化旅馆设计，并形成展示分享与下一轮改进问题。",
    "study_plan_design": "围绕研学目标与基地资源，设计完整的研学方案框架与学习任务。",
    "study_docking_process": "对接基地课程与学校教学需求，明确行程安排、安全预案与协作分工。",
    "study_project_implementation": "组织学生参与研学活动，记录过程表现、突发情况与学习证据。",
    "study_result_summary": "整理研学成果与过程证据，形成总结报告与改进建议。",
    "ancient_road_theme_goals": "选择石佛岭古道主题，结合学段、课时与场地形成课程目标。",
    "ancient_road_field_observation": "设计古道现场观察任务、记录字段与文物及生境保护边界。",
    "ancient_road_model_experiment": "把古道问题转成可重复的校园模型实验，明确变量、对照和安全要求。",
    "ancient_road_course_evidence": "组织课程实施并记录现场、实验和资料证据。",
    "ancient_road_evidence_analysis": "比较古道主题假设与证据，讨论误差、局限和结论边界。",
    "ancient_road_outcomes_conservation": "形成跨学科成果、改进建议与古道保护倡议。",
    "ancient_road_home_question": "从古道主题提出适合孩子和家庭条件的探究问题。",
    "ancient_road_home_model": "用家庭常见材料搭建安全模型，观察古道相关现象。",
    "ancient_road_home_safety": "准备低风险材料，明确成人陪伴和家庭活动安全边界。",
    "ancient_road_parent_child_observation": "支持孩子主导观察、记录、比较和表达。",
    "ancient_road_home_reflection": "回顾家庭探究证据，解释模型局限并提出后续问题。",
}


def stage_item(
    *,
    id: str,
    name: str,
    direction_key: str,
) -> dict[str, Any]:
    return {
        "id": id,
        "name": name,
        "direction": STAGE_DIRECTIONS[direction_key],
        "display_direction": STAGE_DISPLAY_DIRECTIONS[direction_key],
    }


FLOW_TEMPLATES: dict[str, dict[str, Any]] = {
    "inquiry_7_stage": {
        "name": "inquiry_7_stage",
        "display_name": "七阶段科学探究流",
        "description": "从观察起点到延伸新问题，完整支撑探究式科学课设计。",
        "role_category": "teacher",
        "stages": [
            stage_item(
                id="observation_start",
                name="观察起点",
                direction_key="observation_start",
            ),
            stage_item(
                id="question_refine",
                name="循疑问题",
                direction_key="question_refine",
            ),
            stage_item(
                id="hypothesis",
                name="可能的猜想",
                direction_key="hypothesis",
            ),
            stage_item(
                id="experiment_design",
                name="实验设计",
                direction_key="experiment_design",
            ),
            stage_item(
                id="new_questions",
                name="实验中的新问题",
                direction_key="new_questions",
            ),
            stage_item(
                id="conclusion",
                name="可能的结论",
                direction_key="conclusion",
            ),
            stage_item(
                id="extension",
                name="延伸与新问题",
                direction_key="extension",
            ),
        ],
    },
    "three_step_inquiry": {
        "name": "three_step_inquiry",
        "display_name": "三步快速探究流",
        "description": "适合短课时或快速备课：观察起点、问题提出、科学探究。",
        "role_category": "teacher",
        "stages": [
            stage_item(
                id="observe",
                name="观察起点",
                direction_key="observation_start",
            ),
            stage_item(
                id="ask",
                name="问题提出",
                direction_key="question_refine",
            ),
            stage_item(
                id="investigate",
                name="科学探究",
                direction_key="experiment_design",
            ),
        ],
    },
    "steam_project": {
        "name": "steam_project",
        "display_name": "STEAM 项目化探究流",
        "description": "面向跨学科项目制课堂，强调原型制作、证据迭代和成果展示。",
        "role_category": "teacher",
        "stages": [
            stage_item(
                id="scenario",
                name="真实情境",
                direction_key="observation_start",
            ),
            stage_item(
                id="challenge",
                name="工程挑战",
                direction_key="question_refine",
            ),
            stage_item(
                id="prototype",
                name="原型制作",
                direction_key="experiment_design",
            ),
            stage_item(
                id="showcase",
                name="展示评价",
                direction_key="extension",
            ),
        ],
    },
    "insect_hotel_project": {
        "name": "insect_hotel_project",
        "display_name": "昆虫旅馆项目探究流",
        "description": "面向本地昆虫开放观察，结合自然取材、旅馆搭建、传感监测与持续优化。",
        "role_category": "teacher",
        "stages": [
            stage_item(
                id="natural_materials",
                name="自然取材",
                direction_key="insect_material_collection",
            ),
            stage_item(
                id="habitat_needs",
                name="栖息需求判断",
                direction_key="insect_habitat_needs",
            ),
            stage_item(
                id="structure_design",
                name="旅馆结构设计",
                direction_key="insect_structure_design",
            ),
            stage_item(
                id="build_and_sensing",
                name="搭建与传感部署",
                direction_key="insect_build_and_sensing",
            ),
            stage_item(
                id="settlement_observation",
                name="自然入住观测",
                direction_key="insect_settlement_observation",
            ),
            stage_item(
                id="iteration_sharing",
                name="优化改造与分享",
                direction_key="insect_iteration_sharing",
            ),
        ],
    },
    "study_travel_project": {
        "name": "study_travel_project",
        "display_name": "研学方案设计流",
        "description": "面向研学基地工作台，从方案设计到结果总结的完整研学项目管理流程。",
        "role_category": "study_travel",
        "stages": [
            stage_item(
                id="plan_design",
                name="方案设计",
                direction_key="study_plan_design",
            ),
            stage_item(
                id="docking_process",
                name="对接流程",
                direction_key="study_docking_process",
            ),
            stage_item(
                id="project_implementation",
                name="项目实施",
                direction_key="study_project_implementation",
            ),
            stage_item(
                id="result_summary",
                name="结果总结",
                direction_key="study_result_summary",
            ),
        ],
    },
    "stone_buddha_ancient_road_course": {
        "name": "stone_buddha_ancient_road_course",
        "display_name": "石佛岭古道跨学科课程实施",
        "description": "围绕古道地质、生境、种子与工程主题，完成课程目标、现场观察、模型实验、证据分析和成果保护设计。",
        "role_category": "teacher",
        "stages": [
            stage_item(id="theme_and_course_goals", name="主题与课程目标", direction_key="ancient_road_theme_goals"),
            stage_item(id="field_observation_tasks", name="古道现场观察任务", direction_key="ancient_road_field_observation"),
            stage_item(id="classroom_model_experiment", name="校园模型实验设计", direction_key="ancient_road_model_experiment"),
            stage_item(id="course_implementation_evidence", name="课程实施与证据记录", direction_key="ancient_road_course_evidence"),
            stage_item(id="evidence_analysis", name="证据分析与解释", direction_key="ancient_road_evidence_analysis"),
            stage_item(id="learning_outcomes_and_conservation", name="成果展示与古道保护", direction_key="ancient_road_outcomes_conservation"),
        ],
    },
    "stone_buddha_ancient_road_home_inquiry": {
        "name": "stone_buddha_ancient_road_home_inquiry",
        "display_name": "石佛岭古道主题家庭探究",
        "description": "把古道地质、生境、种子与排水主题转化为家庭安全模型和亲子观察活动。",
        "role_category": "parent",
        "stages": [
            stage_item(id="home_inquiry_question", name="家庭探究问题", direction_key="ancient_road_home_question"),
            stage_item(id="home_model_activity", name="家庭模型活动", direction_key="ancient_road_home_model"),
            stage_item(id="home_materials_and_safety", name="材料准备与安全", direction_key="ancient_road_home_safety"),
            stage_item(id="parent_child_observation", name="亲子观察与记录", direction_key="ancient_road_parent_child_observation"),
            stage_item(id="home_findings_and_reflection", name="发现讨论与反思", direction_key="ancient_road_home_reflection"),
        ],
    },
}


# The Parent workbench follows the exact same stage sequence and goals as
# Teacher; only its independent role category changes prompt selection.
for _teacher_flow_name, _teacher_flow in list(FLOW_TEMPLATES.items()):
    if _teacher_flow.get("role_category") != "teacher":
        continue
    if _teacher_flow_name == "stone_buddha_ancient_road_course":
        continue
    _parent_flow = deepcopy(_teacher_flow)
    _parent_flow["name"] = f"parent_{_teacher_flow_name}"
    _parent_flow["display_name"] = f"家庭{_teacher_flow['display_name']}"
    _parent_flow["description"] = f"{_teacher_flow['description']}（家庭场景）"
    _parent_flow["role_category"] = "parent"
    FLOW_TEMPLATES[_parent_flow["name"]] = _parent_flow


def list_flows(role_category: str = "teacher") -> list[dict[str, Any]]:
    # 根据角色分类过滤流程
    # 教师工作台：inquiry_7_stage, three_step_inquiry, steam_project, insect_hotel_project
    # 研学基地工作台：study_travel_project
    result = []
    for flow in FLOW_TEMPLATES.values():
        flow_role = flow.get("role_category", "teacher")
        if flow_role == role_category:
            result.append({
                "name": flow["name"],
                "display_name": flow["display_name"],
                "description": flow["description"],
                "stage_count": len(flow["stages"]),
                "stages": deepcopy(flow["stages"]),
            })
    return result


def get_flow(flow_name: str) -> dict[str, Any]:
    if flow_name not in FLOW_TEMPLATES:
        raise KeyError(f"Unknown flow: {flow_name}")
    return deepcopy(FLOW_TEMPLATES[flow_name])


def get_stage(flow_name: str, index: int) -> dict[str, Any]:
    flow = get_flow(flow_name)
    stages = flow["stages"]
    if index < 0 or index >= len(stages):
        raise IndexError(f"Stage index out of range: {index}")
    return deepcopy(stages[index])
