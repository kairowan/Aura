---
name: drawio-diagrams
description: 生成和修改 draw.io 图表文件。用户提到流程图、架构图、时序图、泳道图、组织结构图、ER 图、系统拓扑图、业务流程图时都应该使用这个技能；它会把结果直接产出为 Aura 可预览的 `.drawio` artifact。
---

# Draw.io Diagrams Skill

这个技能用于在 Aura 中生成和迭代 draw.io 图表。目标不是输出 Mermaid 或伪 XML，而是生成可以直接被 Aura artifact 面板预览和下载的 `.drawio` 文件。

## 适用场景

- 流程图、泳道图、时序图、架构图、拓扑图、组织架构图
- 用户要求“画一个系统图”“给我一个 draw.io 文件”“把这个架构图改一下”
- 已经存在 `.drawio` 文件，需要继续增删节点、修改连接关系或调整文案

## 工作原则

1. 最终交付物必须写入 `/mnt/user-data/outputs/<name>.drawio`
2. 完成后必须调用 `present_files` 把该文件展示给用户
3. 如果用户要修改现有图，先读取当前 `.drawio` 文件内容，再修改；不要凭记忆重建
4. 修改时优先保持已有 `mxCell id` 稳定，只新增必要节点，避免整图重写

## Draw.io XML 结构

合法的 draw.io 文件至少应包含这层结构：

```xml
<mxfile>
  <diagram name="Page-1">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <!-- 你的 mxCell 节点 -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### 硬性规则

- `id="0"` 和 `id="1"` 是保留根节点，不能删除
- 所有业务节点都从 `id="2"` 开始，或使用唯一的语义化 id
- 所有 `mxCell` 都必须是 `<root>` 下的同级元素，不要把 `mxCell` 嵌套进另一个 `mxCell`
- 图形节点要有 `vertex="1"`，连线节点要有 `edge="1"`
- 所有图形都需要 `mxGeometry`
- 连线需要正确设置 `source` 和 `target`

## 推荐工作流

### 新建图

1. 先明确图类型和页面结构
2. 生成完整的 `.drawio` XML
3. 写入 `/mnt/user-data/outputs/<descriptive-name>.drawio`
4. 调用 `present_files`

### 修改图

1. 读取现有 `.drawio` 文件
2. 基于已有 `mxCell id` 做局部编辑
3. 若新增节点，给出新的唯一 id
4. 保留未修改部分，避免无关 diff
5. 覆盖原文件或生成一个新的 `-v2.drawio`
6. 调用 `present_files`

## 常用样式片段

### 普通矩形

```xml
<mxCell id="api" value="API Gateway" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#dae8fc;strokeColor=#6c8ebf;" vertex="1" parent="1">
  <mxGeometry x="280" y="120" width="160" height="64" as="geometry"/>
</mxCell>
```

### 箭头连线

```xml
<mxCell id="edge-api-auth" style="edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=classic;strokeColor=#4b5563;" edge="1" parent="1" source="api" target="auth">
  <mxGeometry relative="1" as="geometry"/>
</mxCell>
```

### 泳道

```xml
<mxCell id="frontend-lane" value="Frontend" style="swimlane;startSize=30;horizontal=0;" vertex="1" parent="1">
  <mxGeometry x="40" y="40" width="220" height="420" as="geometry"/>
</mxCell>
```

## 质量要求

- 默认给出中文标签，除非用户明确要求英文
- 优先保证布局清晰，再追求装饰性
- 节点间距要均匀，避免重叠
- 如果图很复杂，拆成多个页面或多个区域，不要把所有元素挤在一起
- 如果用户要求“继续修改”，要先解释你改了哪些节点和连线，再交付更新后的文件
