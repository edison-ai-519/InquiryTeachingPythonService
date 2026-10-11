# Knowledge Graph Optimization TODO

## 1. 当前架构

### 组件与入口

- 用户端由 `frontend/src/App.vue` 的 `showGraphInRightPanel` 控制右侧“图谱 / 编辑器”切换；`KnowledgeGraphPanel.vue` 承担完整模式图谱、节点选择、按选中节点回答和全屏入口。
- 管理端由 `KnowledgeConfigCenterModal.vue` 的“图谱配置”页使用同一个 `FocusKnowledgeGraphCanvas.vue`，以 `variant="map"` 隐藏目录和详情；其全屏预览通过 `Teleport` 和 `graphExpanded` 实现。
- 用户端全屏同样由 `KnowledgeGraphPanel.vue` 的 `expanded` 状态及 `Teleport` 实现。两种全屏幕布各自创建一个新的画布实例，当前不会共享平移、缩放状态。
- `KnowledgeGraphAdminModal.vue` 是另一套固定椭圆 SVG 实现；当前未发现它被 `frontend/src` 的其他文件引用，应在后续确认无动态注册后删除或统一到主画布，避免两套图谱逻辑继续分叉。

### 数据、请求与扩展

- `KnowledgeGraphPayload` 的真实结构为 `entities`、`relations`、`paths`、`recommended_path_ids`；节点使用 `id/name/entity_type/aliases/description/source/rag_sources`，关系使用主语、谓词、宾语、置信度和证据字段。
- 首次用户图谱请求是 `POST /api/knowledge/graph/candidates`。后端以消息、会话主题和当前阶段匹配锚点，收集锚点的一跳和二跳关系，再返回节点、关系与推荐路径。
- 双击节点请求 `GET /api/knowledge/graph/entities/{id}/neighbors?hops=1`。接口将 hop 限制为 `1..2`，服务层默认上限为 20 节点、40 关系。
- `App.vue` 已使用 `Map` 按实体、关系、路径 ID 合并扩展结果，并以 `entityId:hops` 作为已完成请求缓存键；它没有候选图谱请求缓存、请求代次保护或取消机制。

### 渲染、布局与交互

- 主画布是原生 SVG，不使用 D3、Cytoscape 或 ECharts。`<g>` 使用响应式 `translate(x y) scale(scale)` 实现平移与缩放。
- 当前逻辑视图固定为 `viewBox="0 0 620 380"`，节点按 `name + id` 稳定排序，均匀放在中心 `(310, 190)`、半径 `(248, 142)` 的单一椭圆环上；所有节点半径固定为 22。
- 每条可见关系生成一个 SVG `<line>`；高亮边额外生成 `<text>` 标签。每个节点生成 `<g> + <circle> + <text>`。普通边没有方向箭头。
- 单击仅更新父级 `selectedGraphEntityIds`；关联边通过主题色、加粗和 SVG `drop-shadow` 高亮。双击继续触发邻域扩展。拖拽、滚轮缩放和工具栏缩放都在 `FocusKnowledgeGraphCanvas.vue` 内部处理。
- 未实现图谱容器的 `ResizeObserver`、窗口尺寸监听、`requestAnimationFrame` 节流、指针捕获或拖拽阈值。

### 当前验证基线

- 已运行 `python -m unittest tests.test_day3.AgentArchitectureApiTests.test_knowledge_graph_candidates_neighbors_and_graph_rag_chat -v`，通过。该用例验证候选请求、邻域返回上限和图谱选择聊天链路；它不覆盖浏览器布局、响应式尺寸或交互性能。

---

## 2. 当前发现的问题

### P0 Bug

当前没有发现会使已有图谱基础链路立即不可用的 P0 崩溃。以下 P1 问题在节点或关系规模增长后会成为实际可用性和性能瓶颈，应优先处理。

### P1 用户体验问题

1. **固定单环在中等规模后失效**
   - 现象：节点、文字和关系线迅速聚集，关系交叉形成“毛线球”。
   - 根因：所有节点始终位于同一椭圆，关系不参与布局，也没有碰撞、分层或多环规则。
   - 位置：`FocusKnowledgeGraphCanvas.vue` 的 `visibleLayoutEntities`、`visibleNodes` 和 `visibleEdges`。
   - 影响：5--10 节点且关系稀疏时尚可阅读；约 12--20 节点时交叉关系已明显；约 25--30 节点时椭圆相邻间距接近 44px 节点直径；50 节点后节点与线条严重拥挤；100 节点不具备可读性。实际失效阈值会随关系密度提前。
   - 方案：第一阶段改为稳定多环布局并限制默认展示密度；只有图谱数据明确提供根节点时才启用“中心节点 + 邻居环”。

2. **画布不随真实容器尺寸布局**
   - 现象：右侧窄面板、配置预览和全屏幕布共用 `620 x 380` 逻辑尺寸；CSS 只做视觉缩放，容易产生留白、贴边或窄屏拥挤。
   - 根因：节点坐标、`viewBox`、半径均为固定常量，图谱组件没有观察容器尺寸。
   - 位置：`FocusKnowledgeGraphCanvas.vue`；`style.css` 中 `.knowledge-graph-svg`、`.focus-graph-shell.map-only` 的固定最小高度。
   - 方案：使用 `ResizeObserver` 驱动动态逻辑 viewport 和 variant layout profile，尺寸为 0 时延后首帧布局。

3. **普通用户端关闭按钮与产品定位冲突**
   - 现象：右侧图谱顶部“关闭”按钮会切回编辑器，容易被理解成关闭或丢弃图谱。
   - 根因：`KnowledgeGraphPanel.vue` 仍发出 `close`，`App.vue` 仍将其绑定为 `showGraphInRightPanel = false`；但右侧已有“图谱 / 编辑器”切换控件。
   - 影响：重复入口和不必要的 UI 状态切换。
   - 方案：删除普通面板关闭按钮、`close` emit 及 `App.vue` 的 `@close` 绑定；保留右侧切换控件。

4. **配置预览的放大按钮视觉权重过高**
   - 现象：文字加图标的 30px 高按钮抢占预览标题栏，窄窗口下更明显。
   - 根因：`.graph-preview-pane-head button` 使用通用文本按钮尺寸，未按辅助工具定位设计。
   - 方案：改为仅 `Maximize2` 图标的方形工具按钮，桌面 `28 x 28px`，移动端 `32 x 32px`；添加 `title="放大图谱"`、`aria-label`、`focus-visible`、disabled 和触摸状态。全屏幕布中的“关闭”按钮必须保留，因为它只关闭幕布并返回工作区。

5. **拖拽、点击和缩放缺少手势边界**
   - 现象：节点 `click.stop` 未阻止先发生的 `pointerdown`；拖拽后仍可能触发节点点击。滚轮缩放固定围绕 SVG 原点，放大时指针所在位置不会保持稳定。
   - 根因：无 drag threshold、无 `setPointerCapture`、无按指针坐标换算的缩放锚点。
   - 位置：`FocusKnowledgeGraphCanvas.vue` 的 `startPan/movePan/endPan/onWheel`。
   - 方案：记录移动距离，超过 4px 才标记拖拽；使用 pointer capture；拖拽结束后抑制一次 click；按鼠标位置计算 zoom anchor，并限制平移范围。

6. **全屏幕布缺少对话框行为**
   - 现象：全屏通过 `role="dialog"` 和 `aria-modal` 标注，但没有 Escape 关闭、焦点管理、焦点返回和 body scroll lock。
   - 影响：键盘用户与移动端体验不完整，背景页面可能继续滚动。
   - 方案：复用一个受控 stage helper，打开时保存触发元素、锁定 body、聚焦关闭按钮；支持 Escape 和关闭后焦点返回。

### P1 性能问题

1. **候选图谱服务没有节点和关系上限**
   - 现象：`find_candidate_graph` 会收集所有命中锚点的一跳、二跳关系；消息命中较多实体时，返回体和 SVG 都可能快速变大。
   - 根因：候选服务没有 `node_limit`、`relation_limit` 或锚点数限制；扩展接口有 20/40 限制，但候选接口没有。
   - 方案：为候选接口增加服务端默认上限，例如 24 节点、48 关系和最多 3 个锚点；响应中返回 `truncated`、`total_candidate_count`，前端明确提示“已展示重点子图”。具体阈值须以真实数据压测后确定。

2. **候选查询与序列化存在可确认的重复工作**
   - 现象：锚点及其邻居通过 `_relations_for_entity` 逐个查询；每个实体序列化又调用一次 `rag_sources_for_entity`；路径构建对关系进行双层遍历。
   - 根因：关系查询是按实体发起，`serialize_entity` 没有使用已有的批量 `rag_sources_for_entities`，`_build_paths` 在关系数为 R 时有 O(R²) 比较。
   - 位置：`app/services/knowledge_graph_service.py` 的 `find_candidate_graph`、`serialize_entity`、`_build_paths`。
   - 方案：批量读取所有实体的 RAG source；一次查询候选实体关联关系并在内存构建 adjacency map；路径生成只遍历锚点相邻关系。保留排序和置信度语义。

3. **前端高频事件直接驱动响应式重渲染**
   - 现象：每次 `pointermove` 更新响应式 `viewport`，每次 wheel 都更新 scale；无 rAF 合帧或节流。
   - 根因：SVG `<g>` transform 虽然轻量，但高频事件仍会触发 Vue 更新和 VDOM 比对；高亮会在多条关系上启用 `drop-shadow`。
   - 方案：将 pending transform 放在普通对象中，每帧仅提交一次响应式值；wheel 合并到一帧；当高亮边数超过阈值时去掉 filter，只保留颜色和线宽。

4. **扩展请求存在陈旧结果合并风险**
   - 现象：全局 `isExpandingGraphNode` 阻止并发扩展，但请求没有 AbortController、会话/图谱代次或组件生命周期校验。切换会话、重置图谱或快速切换专家后，旧请求仍可能回写当前 `knowledgeGraph`。
   - 方案：每次候选加载、扩展和重置都增加 `graphRequestGeneration`；请求完成时仅在 generation 与当前一致时写入。组件卸载或会话切换时 abort 未完成请求。缓存仍以实体、hop 和图谱版本区分。

### P2 代码结构与数据质量问题

1. `showKnowledgeGraphPanel` 在 `App.vue` 中仅被重置或置为 false，没有控制当前模板；应在删除普通关闭流程时确认后清理。
2. `KnowledgeGraphAdminModal.vue` 未被引用且复制了一套固定椭圆渲染逻辑；保留会造成样式和行为分叉。
3. 前端对找不到端点的关系直接不绘制，后端关系创建会校验端点，但导入或历史脏数据仍应在 API 层统计并返回 `invalid_relation_count`。自环关系当前没有禁止或专门渲染策略。
4. `match_entities` 通过遍历所有实体并做子串匹配；在大词库下应增加别名规范化、倒排索引或数据库预筛选，但先用基准数据确认瓶颈。
5. 当前没有浏览器端图谱测试脚本；后续应把布局、去重、坐标稳定和交互边界抽成可测的纯函数。

---

## 3. UI 调整

### 删除

- `frontend/src/components/KnowledgeGraphPanel.vue`：删除普通面板头部的 `<button @click="$emit('close')">`，同时移除 `X` 的该处使用和 `close` emit。
- `frontend/src/App.vue`：删除 `KnowledgeGraphPanel` 上的 `@close="showGraphInRightPanel = false"`。
- 确认后删除无用途的 `showKnowledgeGraphPanel` 状态和仅为它服务的赋值；不得删除 `showGraphInRightPanel`，它仍服务于“图谱 / 编辑器”显式切换。

### 保留

- 用户端和配置端 `graph-stage-overlay` 内的关闭按钮及 `expanded/graphExpanded = false` 逻辑必须保留。
- 右侧“图谱 / 编辑器”切换控件保留，它是用户切换工作内容的明确导航，不是关闭图谱。

### 修改

- `KnowledgeConfigCenterModal.vue`：放大触发按钮改为仅含 `Maximize2`，提供 `title` 和 `aria-label="放大图谱"`；键盘 Enter/Space 继续由原生 button 支持。
- `style.css`：为 `.graph-preview-pane-head .graph-icon-button` 定义桌面 `inline-size/block-size: 28px`、`padding: 0`；`max-width: 680px` 下改为 32px。hover、active、focus-visible、disabled 分别使用边框/背景/outline/opacity，不将文本按钮样式复用到此控件。
- 全屏关闭按钮继续保留“关闭”文字，避免纯图标在幕布场景下语义不清。

---

## 4. 响应式尺寸方案

1. 在 `FocusKnowledgeGraphCanvas.vue` 给真实画布容器添加 `ref`，在 `onMounted` 建立 `ResizeObserver`，在 `onBeforeUnmount` disconnect；只在宽高均大于 0 时提交尺寸。
2. 将 SVG 改为动态 `viewBox="0 0 ${viewportWidth} ${viewportHeight}"`，不再写死 `620 x 380`。SVG 逻辑尺寸直接来自观测容器，避免 CSS 拉伸与坐标体系脱节。
3. 计算 profile：`compact` 为右侧窄面板，`normal` 为配置预览和普通桌面，`fullscreen` 为幕布。profile 由 `variant`、容器宽高和 overlay 上下文决定，而不是仅由窗口宽度决定。
4. 每个 profile 计算 `centerX/Y`、边距、节点半径、最小环距、标签长度：compact 使用较小节点和更短标签；normal 保持当前信息密度；fullscreen 增加边距、节点半径和可见标签长度。
5. 位置缓存存储归一化坐标 `{ xRatio, yRatio }`，渲染时映射为实际 viewport。Resize 时图谱按比例缩放，节点相对空间关系保持稳定；不得在 resize 时重新排序或随机布局。
6. map 预览应设置“预览可见节点预算”，全屏和用户端可用更高预算；超出预算显示聚合提示或通过目录、搜索和扩展进入局部图谱，不在小画布硬塞全部节点。

---

## 5. 图谱布局优化

| 方案 | 适用性 | 优点 | 风险与结论 |
| --- | --- | --- | --- |
| 当前单环椭圆 | 5--10 节点、低关系密度 | 实现简单、排序稳定 | 20 节点左右已产生大量交叉，不再作为默认大图方案。 |
| 稳定多环布局 | 当前阶段推荐 | 无新依赖；可按容量分环；可和位置缓存、增量扩展兼容 | 需实现碰撞与分环策略。建议每环按实际周长和节点直径计算容量，而不是写死节点数。 |
| 中心节点 + 邻居环 | 有明确锚点时推荐 | 最符合“围绕某一概念展开”的教学语义 | 当前 payload 没有 `anchor_entity_ids/layout_root_id`；需先由候选和邻居 API 明确返回展开根。 |
| 分层布局 | 课程概念存在稳定有向层级时可选 | 可读性强，方向明确 | 当前谓词包含一般关联和可能的环，不能对所有图谱强制使用。先为特定 `entity_type/predicate` 子图试点。 |
| D3-force | 暂不推荐立即引入 | 自动减少重叠，适合探索型复杂关系 | 位置会运动，双击扩展需 reheating/freeze，破坏空间记忆。 |
| Cytoscape/ECharts/ELK | 50--100+ 节点且需求持续增加时再评估 | 成熟布局、选择、缩放和性能能力 | 引入成本、包体和交互迁移较高；当前先完成 SVG 渐进优化与基准压测。 |

推荐路线：保留 SVG，先实现响应式稳定多环布局；候选 API 提供锚点后，为局部图谱启用锚点中心布局；只有压测表明 50--100+ 节点场景仍无法达到可读性与帧率目标时，再评估 Cytoscape 或 ELK，不建议此时直接引入 D3-force。

---

## 6. 双击扩展优化

### 现状

扩展结果合并后，`visibleLayoutEntities` 对所有节点重新按名称和 ID 排序，再从零计算单环坐标。因此即使旧节点没有变化，也会整体移动，破坏空间记忆。

### 目标设计：incremental layout

- 新增 `GraphLayoutState`：`positions: Map<nodeId, NormalizedPosition>`、`expandedBy: Map<nodeId, Set<nodeId>>`、`layoutRevision`。
- 初次候选图谱仅为未定位节点生成稳定多环位置；后续选择、高亮、缩放和平移绝不修改 positions。
- `App.vue` 的合并函数返回 `{ graph, addedEntityIds, addedRelationIds }`，扩展完成时保存 `lastExpansion = { sourceId, addedEntityIds, revision }` 并传给画布。
- 画布收到扩展上下文后，只为 `addedEntityIds` 分配位置：优先在 source 节点朝向空白区域的小扇形中分布；空间不足时放入下一个外环。已有节点坐标不变。
- 用固定角度种子（source ID hash）决定扇形起点，保证同一扩展结果可复现；用最小距离检查避免与已有节点重叠。没有 source、数据导入或图谱整体替换时，才允许全量初始化。
- 扩展过程中只在 source 节点附近显示 loading ring；不得让整个图谱替换成 loading 画面。

---

## 7. 性能分析

### 已确认的问题

- **API/查询**：候选接口无节点/关系限制；候选关系按实体重复查询；实体序列化存在每实体一次 RAG source 查询；路径生成含 O(R²) 关系比较。
- **布局**：扩展后所有节点重新排序和计算坐标；固定单环使更多节点必须同时渲染。
- **Vue 与事件**：pointermove/wheel 直接更新响应式状态，无 rAF 合帧。
- **SVG DOM**：N 节点至少约 `3N` 个节点相关 SVG 元素，M 关系至少 `M` 条 `<line>`；高亮关系额外有 `<text>`。满量管理端和全屏会将所有实体传入 `maxNodes`。
- **绘制**：选中节点和关联边使用 `drop-shadow`，高 degree 节点会让较多 SVG filter 同时参与绘制。

### 需要压测确认的风险

- `match_entities` 的全表子串扫描在真实实体规模下的耗时。
- candidate 返回量、浏览器 SVG 数量、缩放/拖拽 FPS 与高亮 filter 对 50+ 节点的影响。
- 图谱数据较大时配置中心 `graph.entities.find/filter` 在列表、表单和画布间的重复查找成本。
- 快速切换会话、专家、幕布及连续双击时是否出现陈旧响应覆盖或重复扩展。

### 建议采集指标

- 记录候选和邻居接口的实体数、关系数、数据库查询数、服务耗时与响应字节数。
- 前端以 Performance API 记录 request、merge、layout、首次 SVG 渲染、一次 wheel/pan 帧耗时。
- 开发环境用 Vue Devtools/浏览器 Performance 采样 10、30、50、100 节点场景，分别统计节点数、关系数、长任务与帧率。

---

## 8. 性能优化计划

### P0 / 首先实施

1. 为候选 API 加默认节点、关系和锚点上限，返回截断元数据；为用户端和管理端定义不同可见预算。
2. 将 `serialize_entity` 的逐实体 source 查询改为批量 `rag_sources_for_entities`，并将候选关系查询改为批量查询加 adjacency map。
3. 将 `_build_paths` 改为邻接表遍历，保持最多 10 条路径和现有置信度排序语义。
4. 为候选与扩展请求增加 generation 和 abort，防止旧响应写入新图谱。

### P1 / 随布局一起实施

1. 抽出纯函数 `buildInitialLayout`、`placeExpansionNodes`、`clampViewport`，以 `Map` 缓存节点位置。
2. 在 SVG 容器上加入 ResizeObserver 和 rAF 合帧的 pan/zoom 更新；wheel 以指针为锚点，平移有边界。
3. 对图谱渲染设置 profile 预算；只对选中节点和有限关联边启用 filter，高密度时降级为无 filter 的描边高亮。
4. 请求缓存改为“完成缓存 + in-flight promise 去重”；缓存键包含实体、hop、图谱数据版本，切换会话或图谱版本时失效。

### P2 / 压测后实施

1. 为实体匹配引入预构建别名索引或数据库预筛选。
2. 为超大图引入分组、聚合节点或局部探索模式；只有 SVG 优化达到边界后再选型第三方图谱引擎。
3. 清理未引用的 `KnowledgeGraphAdminModal.vue` 和无效的 `showKnowledgeGraphPanel` 状态。

---

## 9. 视觉优化

- **节点**：保持按实体类型区分描边；compact/normal/fullscreen 分别使用不同半径。选中节点最明显，hover 次之，邻居以细描边或低饱和底色提示，避免为所有相关元素添加发光。
- **标签**：保留 SVG `<title>` 完整名称；根据 profile 用固定字符预算截断；不要让长文本改变节点几何尺寸。全屏可提高预算，右侧紧凑模式降低预算。
- **边**：普通边使用低对比度细线；选中或 hover 关系加粗高亮；使用单一定义的 `marker-end` 表示方向；仅选中边显示谓词标签，标签应避开节点并在密集时隐藏低优先级标签。
- **背景与工具栏**：保持低对比网格或纯色背景，缩放、重置和全屏都采用一致的图标工具按钮与 tooltip；普通工具不使用主操作按钮视觉。
- **加载与空态**：首次加载显示 skeleton canvas；扩展时在源节点显示局部 loading ring；空态明确说明“无可展示关系”，并保留返回编辑器的显式切换入口。

---

## 10. 文件级修改计划

### `frontend/src/components/FocusKnowledgeGraphCanvas.vue`

- 新增 ResizeObserver、layout profile、动态 viewBox、位置缓存、稳定多环和增量布局。
- 抽出可测试的布局、缩放锚点和平移边界纯函数。
- 增加 pointer capture、拖拽阈值、click 抑制、rAF wheel/pan 合帧和局部扩展 loading。
- 保持单击选择、目录、详情、关系高亮、zoom、reset、drag、wheel、双击扩展和 `map/full` variant。

### `frontend/src/components/KnowledgeGraphPanel.vue`

- 删除普通关闭按钮、`close` emit 与不再使用的图标导入。
- 保留全屏入口及全屏关闭按钮；将布局更新上下文传给画布；统一全屏的焦点、Escape 与焦点返回。

### `frontend/src/components/KnowledgeConfigCenterModal.vue`

- 将预览放大按钮改为纯图标工具按钮和无障碍标签。
- 将配置预览的 profile、节点预算和 stage 行为接入共享画布；保留配置编辑、关系选择和全屏关闭。

### `frontend/src/App.vue`

- 删除普通面板 `@close` 绑定和确认后的死状态。
- 让 `mergeKnowledgeGraph` 返回新增 ID；维护 graph generation、AbortController、in-flight 缓存和最后一次扩展上下文。
- 保持选中节点回答、会话切换和专家切换语义。

### `frontend/src/style.css`

- 加入 profile 驱动的容器高度、工具图标按钮、全屏可访问状态、稀疏边和高密度降级样式。
- 移除与普通关闭按钮相关的无用布局；避免 map 预览使用固定过大的最小高度。

### `frontend/src/types.ts` 与 `frontend/src/api.ts`

- 为候选响应增加可选的 `anchor_entity_ids`、`truncated`、总量元数据；为扩展结果或本地状态传递 source 与新增节点信息。
- 更新 API 参数与类型，确保前端不会猜测根节点或截断情况。

### `app/services/knowledge_graph_service.py` 与 `app/api/knowledge.py`

- 为候选查询施加上限、批量关系/source 查询、邻接表路径生成和可观测指标。
- 返回锚点和截断元数据，保持用户权限、现有路径评分、邻居接口上限和聊天图谱选择不变。

### `tests/test_day3.py` 与新增前端测试

- 增加候选上限、批量序列化、路径生成、重复扩展、陈旧请求和自环/缺失端点的后端测试。
- 引入轻量前端单测工具后，覆盖稳定多环、尺寸映射、增量位置、拖拽阈值和缩放锚点；补充 Playwright 视口回归截图。

---

## 11. 实施顺序

1. **Phase 1：UI 清理与无障碍**
   - 修改普通关闭按钮、放大图标按钮、全屏 focus/scroll/Escape。
   - 风险：误删图谱/编辑器切换状态。
   - 验证：用户端无普通关闭按钮；图谱/编辑器切换仍可用；全屏关闭、Escape 和焦点返回正常。

2. **Phase 2：响应式尺寸与输入手势**
   - 加 ResizeObserver、动态 viewBox、profile、drag threshold、pointer capture、rAF pan/zoom。
   - 风险：dialog 初始 0 尺寸、触摸设备和缩放边界。
   - 验证：右侧、配置预览、全屏、390px 宽屏和窗口 resize 下无裁切、无跳变。

3. **Phase 3：稳定多环与增量布局**
   - 引入位置缓存、初始多环、锚点布局接口、扩展扇形放置。
   - 风险：新增节点碰撞、缓存失效和导入全量替换。
   - 验证：双击连续扩展时旧节点坐标不变，新节点靠近展开源且不重复。

4. **Phase 4：服务端查询与请求控制**
   - 候选上限、批量 source/关系、邻接路径、generation、abort 与 in-flight 去重。
   - 风险：截断后遗漏关键关系、缓存跨会话污染。
   - 验证：接口测试、查询计数、快速切换会话/专家/节点不会出现旧结果覆盖。

5. **Phase 5：性能与视觉压测**
   - 运行 10、30、50、100 节点基准；按数据调整预算、filter 降级和聚合阈值。
   - 风险：为追求性能牺牲教学可读性。
   - 验证：浏览器 Performance 无持续长任务，选中、拖拽和缩放保持可用。

6. **Phase 6：回归测试与清理**
   - 补齐单元、接口和 Playwright 视口测试；删除未引用旧组件和死状态。
   - 风险：删除遗留代码影响隐藏入口。
   - 验证：全量后端测试、前端构建、桌面/移动截图和手工交互清单全部通过。

---

## 12. 验收标准

- **小图谱（5--10 节点）**：单环或多环清晰，标签无明显碰撞，边方向与高亮可辨。
- **中图谱（20--30 节点）**：节点不重叠，普通关系明显弱于选中关系，关键路径可读，不出现全部节点挤在中心的效果。
- **较大图谱（50+ 节点）**：按预算、分环或聚合展示；交互不明显卡顿；不会把全部关系无差别铺到紧凑预览中。
- **用户端右侧窗口**：普通关闭按钮不存在；图谱/编辑器切换仍可用；拖拽、缩放、重置、选择和按节点回答正常。
- **配置中心预览**：放大入口是带 tooltip 的轻量图标按钮；列表、编辑表单和预览不互相挤压。
- **全屏幕布**：放大后动态适配真实尺寸；关闭按钮、Escape、焦点返回和背景滚动锁定正常。
- **窄屏与移动端**：390px 宽下无横向溢出；工具按钮达到 32px 点击面积；触摸拖拽与滚轮替代交互可用。
- **连续双击扩展**：已有节点尽量不移动；新节点围绕展开节点出现；无重复节点、关系或旧请求覆盖；局部 loading 可见。
- **回归**：管理端 map variant、用户端 full variant、节点目录、详情、相邻关系高亮、zoom in/out、reset、drag/pan、wheel zoom、双击扩展和聊天选择全部继续工作。
