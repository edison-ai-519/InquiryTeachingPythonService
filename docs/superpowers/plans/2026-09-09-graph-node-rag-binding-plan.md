# 图谱节点知识库绑定 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个知识图谱节点增加现有课程知识库 source 绑定，并实现图谱优先、按权限隔离、无绑定回退专家授权库的 RAG 聊天链路。

**Architecture:** 使用 `knowledge_entity_sources` 多对多关联表保存节点与 `curriculum_sources.source` 的关系。图谱导入和管理员接口通过 `KnowledgeGraphService` 统一校验及替换绑定；聊天场景由 `GraphRagService` 解析选中链路涉及的节点、节点 source 与专家授权 source 的交集，图谱上下文优先于节点 RAG 背景片段。无图谱选择时保留现有专家 RAG。

**Tech Stack:** Python 3、FastAPI、SQLAlchemy、SQLite、Pydantic、unittest/现有 `tests/test_day3.py`。

---

### Task 1: 添加节点知识库关联模型与迁移

**Files:**
- Modify: `app/db/models.py`
- Modify: `app/db/migrations.py`
- Modify: `database/schema.sql`
- Test: `tests/test_day3.py`

- [ ] **Step 1: Write the failing test**

在测试文件中增加模型级测试，创建已存在实体和 source，写入两个绑定，断言可按 entity 查询 source、重复绑定受复合主键阻止，并断言迁移后的表存在。

```python
def test_knowledge_entity_rag_sources_are_persisted(self):
    with SessionLocal() as db:
        entity = KnowledgeEntityModel(
            id="entity_rag",
            name="节点",
            entity_type="concept",
            aliases_json="[]",
            description="",
            source="test",
            created_at="now",
            updated_at="now",
        )
        source = CurriculumSourceModel(source="node-rag.txt", updated_at="now")
        db.add_all([entity, source])
        db.flush()
        db.add(KnowledgeEntitySourceModel(entity_id=entity.id, source=source.source, created_at="now"))
        db.commit()
        rows = db.query(KnowledgeEntitySourceModel).filter_by(entity_id=entity.id).all()
        self.assertEqual([row.source for row in rows], ["node-rag.txt"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_day3.InquiryTeachingApiTests.test_knowledge_entity_rag_sources_are_persisted -v`

Expected: FAIL because `KnowledgeEntitySourceModel` and its table do not yet exist.

- [ ] **Step 3: Write minimal implementation**

在 `app/db/models.py` 增加 `KnowledgeEntitySourceModel`，实体和 source 为复合主键并分别外键级联删除；在 `app/db/migrations.py` 增加 `CREATE TABLE IF NOT EXISTS knowledge_entity_sources` 及 source/entity 索引；在 `database/schema.sql` 同步声明表结构。

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_day3.InquiryTeachingApiTests.test_knowledge_entity_rag_sources_are_persisted -v`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add app/db/models.py app/db/migrations.py database/schema.sql tests/test_day3.py
git commit -m "feat: persist graph node rag source bindings"
```

### Task 2: 实现绑定服务、导入校验与管理员接口

**Files:**
- Modify: `app/services/knowledge_graph_service.py`
- Modify: `app/api/knowledge.py`
- Modify: `app/schemas.py`
- Test: `tests/test_day3.py`

- [ ] **Step 1: Write the failing tests**

覆盖导入保存绑定、未知 source 回滚、管理员替换绑定、空列表清除和节点序列化返回 `rag_sources`。

```python
def test_graph_import_rejects_unknown_rag_source(self):
    with SessionLocal() as db:
        service = KnowledgeGraphService(db)
        with self.assertRaises(ValueError):
            service.import_graph_json({"entities": [{"id": "e1", "name": "节点", "entity_type": "concept", "rag_sources": ["missing.txt"]}]})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_day3.InquiryTeachingApiTests.test_graph_import_rejects_unknown_rag_source -v`

Expected: FAIL because import ignores `rag_sources` and no binding API exists.

- [ ] **Step 3: Write minimal implementation**

在图谱服务中增加 `rag_sources_for_entity`、`replace_rag_sources`、`rag_sources_for_entities`；导入时先收集并规范化所有 `rag_sources`，校验 source 全部存在后再写实体及绑定，未知 source 抛出 `ValueError`；实体序列化增加 `rag_sources`。

在 `app/schemas.py` 增加 source 列表请求模型；在 `app/api/knowledge.py` 增加 `PUT /api/knowledge/graph/entities/{entity_id}/rag-sources`，使用 `get_admin_user`，节点不存在返回 404，source 不存在返回 400，返回替换后的 source 列表。

- [ ] **Step 4: Run focused tests**

Run: `python -m unittest tests.test_day3 -v`

Expected: 新增绑定和接口测试 PASS，现有图谱测试保持 PASS。

- [ ] **Step 5: Commit**

```bash
git add app/services/knowledge_graph_service.py app/api/knowledge.py app/schemas.py tests/test_day3.py
git commit -m "feat: configure rag sources per graph node"
```

### Task 3: 实现图谱 source 解析与隔离检索

**Files:**
- Modify: `app/services/graph_rag_service.py`
- Modify: `app/services/knowledge_graph_service.py`
- Test: `tests/test_day3.py`

- [ ] **Step 1: Write failing tests**

增加三种行为测试：节点绑定且有权限时使用交集；节点无绑定时使用专家授权 source 并返回 `expert_fallback`；节点有绑定但无权限时 effective source 为空且返回 `configured_but_not_allowed`。

```python
def test_graph_rag_uses_node_sources_intersected_with_expert_permissions(self):
    result = GraphRagService(db).resolve_sources(
        selected_entity_ids=[entity_id], allowed_sources=["allowed.txt", "other.txt"]
    )
    self.assertEqual(result.effective_sources, ["allowed.txt"])
    self.assertEqual(result.source_resolution, "node_configured")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_day3.InquiryTeachingApiTests.test_graph_rag_uses_node_sources_intersected_with_expert_permissions -v`

Expected: FAIL because GraphRagService currently accepts one global source list and has no resolution result.

- [ ] **Step 3: Write minimal implementation**

在 `GraphRagService` 增加 source 解析结果结构和 `resolve_sources(selected_entity_ids, allowed_sources)`：按选中实体汇总绑定 source，节点绑定时取与授权列表的交集；无绑定时回退授权列表；授权列表为空时返回 `no_expert_permission`；有配置但交集为空时返回 `configured_but_not_allowed`。检索函数使用 `effective_sources`，并把解析字段写入返回 source。

在图谱服务中提供从关系和路径得到实体 ID 的方法，聊天调用时传入选中图谱实际涉及的全部实体。

- [ ] **Step 4: Run focused tests**

Run: `python -m unittest tests.test_day3.InquiryTeachingApiTests.test_graph_rag_uses_node_sources_intersected_with_expert_permissions tests.test_day3.InquiryTeachingApiTests.test_graph_rag_falls_back_to_expert_sources tests.test_day3.InquiryTeachingApiTests.test_graph_rag_does_not_bypass_permissions -v`

Expected: 三个 source 隔离测试 PASS。

- [ ] **Step 5: Commit**

```bash
git add app/services/graph_rag_service.py app/services/knowledge_graph_service.py tests/test_day3.py
git commit -m "feat: isolate graph rag by node and agent permissions"
```

### Task 4: 调整聊天上下文与审计

**Files:**
- Modify: `app/api/chat.py`
- Modify: `app/services/rag_service.py`
- Test: `tests/test_day3.py`

- [ ] **Step 1: Write failing integration tests**

扩展现有图谱聊天测试，断言有效图谱选择时图谱链路在 RAG 上下文之前、不会额外触发普通专家 RAG；无命中或 RAG 异常时仍返回 done；审计包含 `configured_sources`、`effective_sources` 和 `source_resolution`。

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_day3.InquiryTeachingApiTests.test_knowledge_graph_candidates_neighbors_and_graph_rag_chat -v`

Expected: FAIL on the new audit/order assertions because chat currently performs ordinary expert RAG before graph handling and does not record source resolution.

- [ ] **Step 3: Write minimal implementation**

在 `app/api/chat.py` 先校验并构造有效图谱选择；有有效选择时跳过普通 `retrieve_curriculum_context`，调用 GraphRagService 完成 source 解析与检索；无图谱选择时保留现有普通专家 RAG。拼接顺序改为会话资料、图谱链路、图谱 RAG。将 graph source 解析字段写入 `rag_record.source_json`，保持旧字段兼容。

在 `app/services/rag_service.py` 调整上下文提示文字，明确图谱链路是主依据，RAG 片段仅补充背景；source_note 仍只对普通专家 RAG 和已有命中 source 生效。

- [ ] **Step 4: Run focused and regression tests**

Run: `python -m unittest tests.test_day3.InquiryTeachingApiTests.test_knowledge_graph_candidates_neighbors_and_graph_rag_chat tests.test_day3.InquiryTeachingApiTests.test_rag_permissions_isolate_bm25_vector_and_apply_immediately -v`

Expected: PASS。

- [ ] **Step 5: Commit**

```bash
git add app/api/chat.py app/services/rag_service.py tests/test_day3.py
git commit -m "feat: prioritize graph context in rag chat"
```

### Task 5: 全量验证与接口/数据库回归

**Files:**
- Modify: `tests/test_day3.py` only if a missing regression case is found

- [ ] **Step 1: Run formatting and syntax checks**

Run: `python -m compileall app tests`

Expected: exit code 0。

- [ ] **Step 2: Run the complete test suite**

Run: `python -m unittest discover -s tests -v`

Expected: all tests pass with zero failures/errors。

- [ ] **Step 3: Inspect the final diff**

Run: `git diff HEAD~4..HEAD --stat` and `git status --short`。

Expected: only files required by this feature are in the feature commits; pre-existing unrelated working-tree changes remain uncommitted and untouched。

- [ ] **Step 4: Commit any test-only correction**

仅当 Task 5 发现本功能相关的遗漏测试时，执行：

```bash
git add tests/test_day3.py
git commit -m "test: cover graph node rag isolation"
```

### Task 6: 改为手动节点集合选择

**Files:**
- Modify: `frontend/src/components/KnowledgeGraphPanel.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/types.ts` only if selection prop types need renaming
- Modify: `app/services/knowledge_graph_service.py`
- Modify: `app/api/chat.py` if selected entity payload handling needs adjustment
- Test: `tests/test_day3.py`

- [ ] **Step 1: Write the failing backend test**

增加测试：提交两个节点 ID 时只返回两端都属于选中集合的关系；提交单节点时不自动加入相邻节点；只提交 entity IDs 时图谱选择校验通过。

```python
selected = service.selected_graph_payload(
    selected_path_ids=[],
    selected_relation_ids=[],
    selected_entity_ids=["entity_a", "entity_b"],
)
self.assertEqual({row["id"] for row in selected["entities"]}, {"entity_a", "entity_b"})
self.assertEqual([row["id"] for row in selected["relations"]], ["rel_a_b"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_day3.AgentArchitectureApiTests.test_graph_selection_uses_only_manually_selected_nodes -v`

Expected: FAIL because selected_graph_payload currently returns no relation when only entity IDs are supplied, and validation rejects entity-only selection in some cases.

- [ ] **Step 3: Write minimal implementation**

在图谱服务中，当没有显式 relation/path 时，根据 selected entity IDs 查询两端都在集合内的全部关系；返回实体只保留用户选中节点，允许不相邻节点共存。前端将 `selectedGraphEntityIds` 作为唯一选择状态，所有节点均可点击切换；边仅在两端节点都被选中时高亮，回答请求只提交 entity IDs。

- [ ] **Step 4: Run frontend and backend verification**

Run: `npm --prefix frontend run build` and `python -m unittest tests.test_day3.AgentArchitectureApiTests.test_graph_selection_uses_only_manually_selected_nodes -v`。

Expected: frontend build and focused backend test PASS。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/KnowledgeGraphPanel.vue frontend/src/App.vue app/services/knowledge_graph_service.py tests/test_day3.py
git commit -m "feat: select graph replies by nodes"
```
