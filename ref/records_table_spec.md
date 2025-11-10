# 工作记录页面 - 表格设计规范

## 概述

工作记录页面采用表格式布局展示装配工艺执行记录，记录装配过程中的OK、NG和条件通过三种状态。设计遵循工业软件深色主题，使用橙色作为主要强调色，红色标识NG状态，绿色标识OK状态，黄色标识条件通过状态。

## 页面整体布局

### 页面结构层次

```
┌─────────────────────────────────────────────────────────────────┐
│ 标题栏 (Title Bar)                                               │
│ - 页面标题 + 记录统计                                            │
│ - 操作按钮组 (选择日期 / 导出报表)                               │
├─────────────────────────────────────────────────────────────────┤
│ 搜索和筛选栏 (Search & Filter Bar)                               │
│ - 搜索输入框 (记录编号/产品SN/工艺名称)                          │
│ - 状态筛选下拉框 (所有状态/OK/NG/条件通过)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│                    数据表格区域                                   │
│                   (Table Container)                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Table Header                                              │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Row 1                                                     │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Row 2                                                     │  │
│  ├──────────────────────────────────────────────────────────┤  │
│  │ Row 3                                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Flex容器层级

```tsx
<div className="flex-1 flex flex-col overflow-hidden">
  {/* 标题栏 - flex-shrink-0 */}
  {/* 搜索栏 - flex-shrink-0 */}
  {/* 表格区 - flex-1 overflow-y-auto */}
</div>
```

## 标题栏设计规范 (Title Bar)

### 容器样式

```tsx
<div className="bg-[#252525] border-b border-[#3a3a3a] px-6 py-4 flex-shrink-0">
```

#### 样式属性详解

| 属性                 | 值         | 说明            |
| -------------------- | ---------- | --------------- |
| `bg-[#252525]`     | 深灰色背景 | RGB(37, 37, 37) |
| `border-b`         | 底部边框   | 1px solid       |
| `border-[#3a3a3a]` | 边框颜色   | RGB(58, 58, 58) |
| `px-6`             | 水平内边距 | 24px            |
| `py-4`             | 垂直内边距 | 16px            |
| `flex-shrink-0`    | 不收缩     | 固定高度        |

### 左侧标题区域

#### 主标题

```tsx
<h2 className="text-white flex items-center gap-2">
  <ClipboardList className="w-5 h-5 text-orange-500" />
  工作记录
</h2>
```

**样式规范**

- 文字颜色: `text-white` - 纯白色
- 图标尺寸: `w-5 h-5` - 20×20px
- 图标颜色: `text-orange-500` - 橙色强调
- 元素间距: `gap-2` - 8px

#### 副标题

```tsx
<p className="text-gray-400 text-sm mt-1">
  Work Records - {filteredRecords.length} 条记录
</p>
```

**样式规范**

- 文字颜色: `text-gray-400` - 中灰色
- 字号: `text-sm` - 14px
- 顶部间距: `mt-1` - 4px
- 内容: 英文标题 + 动态记录数量

### 右侧操作按钮组

#### 次要按钮 - 选择日期

```tsx
<Button className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white">
  <Calendar className="w-4 h-4 mr-2" />
  选择日期
</Button>
```

**样式规范**

| 状态 | 属性   | 值                    |
| ---- | ------ | --------------------- |
| 默认 | 背景   | 透明                  |
| 默认 | 边框   | `#3a3a3a` 1px solid |
| 默认 | 文字   | `text-gray-400`     |
| 悬停 | 背景   | `#2a2a2a`           |
| 悬停 | 文字   | `text-white`        |
| 图标 | 尺寸   | 16×16px              |
| 图标 | 右边距 | 8px                   |

#### 主要按钮 - 导出报表

```tsx
<Button className="bg-orange-500 hover:bg-orange-600 text-white">
  <Download className="w-4 h-4 mr-2" />
  导出报表
</Button>
```

**样式规范**

| 状态 | 属性 | 值                     |
| ---- | ---- | ---------------------- |
| 默认 | 背景 | `orange-500` #f97316 |
| 悬停 | 背景 | `orange-600` #ea580c |
| 文字 | 颜色 | `text-white`         |
| 图标 | 尺寸 | 16×16px               |

## 搜索和筛选栏设计规范 (Search & Filter Bar)

### 容器样式

```tsx
<div className="bg-[#1f1f1f] border-b border-[#3a3a3a] px-6 py-3 flex-shrink-0">
```

#### 样式属性详解

| 属性             | 值         | 说明                           |
| ---------------- | ---------- | ------------------------------ |
| `bg-[#1f1f1f]` | 深灰色背景 | RGB(31, 31, 31) - 比标题栏更深 |
| `px-6`         | 水平内边距 | 24px                           |
| `py-3`         | 垂直内边距 | 12px - 比标题栏稍矮            |

### 搜索输入框

#### 容器结构

```tsx
<div className="flex-1 relative">
  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
  <Input
    value={searchTerm}
    onChange={(e) => setSearchTerm(e.target.value)}
    placeholder="搜索记录编号、产品SN或工艺名称..."
    className="pl-10 bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
  />
</div>
```

#### 图标定位

| 属性                 | 值       | 说明        |
| -------------------- | -------- | ----------- |
| `absolute`         | 绝对定位 | 相对于容器  |
| `left-3`           | 左边距   | 12px        |
| `top-1/2`          | 垂直位置 | 50%         |
| `-translate-y-1/2` | 垂直居中 | 向上平移50% |
| `w-4 h-4`          | 图标尺寸 | 16×16px    |
| `text-gray-500`    | 图标颜色 | 中等灰色    |

#### 输入框样式

| 属性                          | 值         | 说明                       |
| ----------------------------- | ---------- | -------------------------- |
| `pl-10`                     | 左内边距   | 40px - 为图标留空间        |
| `bg-[#1a1a1a]`              | 背景色     | RGB(26, 26, 26) - 最深背景 |
| `border-[#3a3a3a]`          | 边框色     | RGB(58, 58, 58)            |
| `text-white`                | 文字颜色   | 纯白色                     |
| `placeholder:text-gray-600` | 占位符颜色 | 深灰色                     |

### 状态筛选下拉框

#### 容器样式

```tsx
<Select value={filterStatus} onValueChange={setFilterStatus}>
  <SelectTrigger className="w-48 bg-[#1a1a1a] border-[#3a3a3a] text-white">
    <Filter className="w-4 h-4 mr-2" />
    <SelectValue />
  </SelectTrigger>
  <SelectContent className="bg-[#252525] border-[#3a3a3a]">
    <SelectItem value="all" className="text-white">所有状态</SelectItem>
    <SelectItem value="ok" className="text-white">OK</SelectItem>
    <SelectItem value="ng" className="text-white">NG</SelectItem>
    <SelectItem value="conditional" className="text-white">条件通过</SelectItem>
  </SelectContent>
</Select>
```

#### 样式规范

| 元素    | 属性 | 值               |
| ------- | ---- | ---------------- |
| Trigger | 宽度 | `w-48` - 192px |
| Trigger | 背景 | `#1a1a1a`      |
| Trigger | 边框 | `#3a3a3a`      |
| Trigger | 文字 | `text-white`   |
| Content | 背景 | `#252525`      |
| Content | 边框 | `#3a3a3a`      |
| Item    | 文字 | `text-white`   |

## 表格容器设计规范

### 外层容器

```tsx
<div className="flex-1 overflow-y-auto p-6">
  <div className="bg-[#252525] border border-[#3a3a3a] rounded-lg overflow-hidden">
    <Table>
      {/* 表格内容 */}
    </Table>
  </div>
</div>
```

#### 容器层级说明

1. **滚动容器**: `flex-1 overflow-y-auto p-6`

   - `flex-1`: 占据剩余空间
   - `overflow-y-auto`: 垂直滚动
   - `p-6`: 内边距 24px
2. **表格包装器**: `bg-[#252525] border border-[#3a3a3a] rounded-lg overflow-hidden`

   - `bg-[#252525]`: 深灰色背景
   - `border`: 1px 边框
   - `border-[#3a3a3a]`: 边框颜色
   - `rounded-lg`: 圆角 8px
   - `overflow-hidden`: 隐藏溢出（保持圆角）

## 表格头部设计规范 (Table Header)

### 完整结构

```tsx
<TableHeader>
  <TableRow className="border-[#3a3a3a] hover:bg-[#2a2a2a]">
    <TableHead className="text-gray-400">记录编号</TableHead>
    <TableHead className="text-gray-400">产品SN</TableHead>
    <TableHead className="text-gray-400">工艺名称</TableHead>
    <TableHead className="text-gray-400">操作员</TableHead>
    <TableHead className="text-gray-400">工位</TableHead>
    <TableHead className="text-gray-400">耗时</TableHead>
    <TableHead className="text-gray-400">状态</TableHead>
    <TableHead className="text-gray-400">操作</TableHead>
  </TableRow>
</TableHeader>
```

### TableRow 样式规范

| 属性                   | 值       | 说明            |
| ---------------------- | -------- | --------------- |
| `border-[#3a3a3a]`   | 边框颜色 | RGB(58, 58, 58) |
| `hover:bg-[#2a2a2a]` | 悬停背景 | RGB(42, 42, 42) |

### TableHead 样式规范

```tsx
<TableHead className="text-gray-400">
```

#### 标准样式

- **文字颜色**: `text-gray-400` - RGB(156, 163, 175)
- **字体**: 继承默认字体
- **对齐方式**: 左对齐（默认）
- **内边距**: 由 ShadCN Table 组件提供的默认内边距

### 表头列说明

| 列名     | 宽度策略 | 内容说明               |
| -------- | -------- | ---------------------- |
| 记录编号 | 自动     | REC-2024110701234 格式 |
| 产品SN   | 自动     | SN20241107001 格式     |
| 工艺名称 | 较宽     | 包含双行（标题+编号）  |
| 操作员   | 较窄     | 姓名                   |
| 工位     | 较窄     | 带Badge的工位号        |
| 耗时     | 自动     | XXmin XXs 格式         |
| 状态     | 较宽     | Badge + 可能的缺陷信息 |
| 操作     | 固定     | 操作按钮               |

## 表格主体设计规范 (Table Body)

### 完整行结构

```tsx
<TableBody>
  {filteredRecords.map(record => {
    const StatusIcon = statusLabels[record.status].icon;
    return (
      <TableRow key={record.id} className="border-[#3a3a3a] hover:bg-[#2a2a2a]">
        {/* 各列单元格 */}
      </TableRow>
    );
  })}
</TableBody>
```

### TableRow 交互样式

| 状态 | 样式类                 | 效果           |
| ---- | ---------------------- | -------------- |
| 默认 | `border-[#3a3a3a]`   | 灰色边框       |
| 悬停 | `hover:bg-[#2a2a2a]` | 深灰色背景高亮 |

### 单元格类型和样式

#### 1. 记录编号列

```tsx
<TableCell className="text-white">{record.recordId}</TableCell>
```

**样式规范**

- 文字颜色: `text-white` - 纯白色
- 内容格式: `REC-YYYYMMDDXXXXX`
- 字体: 等宽字体（适合ID显示）

#### 2. 产品SN列

```tsx
<TableCell className="text-white">{record.productSN}</TableCell>
```

**样式规范**

- 文字颜色: `text-white` - 纯白色
- 内容格式: `SNYYYYMMDDXXX`

#### 3. 工艺名称列（双行显示）

```tsx
<TableCell>
  <div className="text-white">{record.processTitle}</div>
  <div className="text-gray-500 text-xs">{record.processName}</div>
</TableCell>
```

**样式规范详解**

| 元素           | 类名              | 说明              |
| -------------- | ----------------- | ----------------- |
| 第一行（标题） | `text-white`    | 白色，正常字号    |
| 第二行（编号） | `text-gray-500` | 灰色              |
| 第二行（编号） | `text-xs`       | 12px - 超小号字体 |

**视觉层次**

```
主控板PCB装配工艺        ← 白色，醒目
PCB-ASM-2024-015        ← 灰色小字，辅助信息
```

#### 4. 操作员列

```tsx
<TableCell className="text-white">{record.operator}</TableCell>
```

**样式规范**

- 文字颜色: `text-white`
- 内容: 操作员姓名

#### 5. 工位列（带Badge）

```tsx
<TableCell>
  <Badge className="bg-orange-500/10 text-orange-400 border-orange-500/30">
    {record.workstation}
  </Badge>
</TableCell>
```

**Badge样式详解**

| 属性                     | 值   | 说明               |
| ------------------------ | ---- | ------------------ |
| `bg-orange-500/10`     | 背景 | 橙色，10%透明度    |
| `text-orange-400`      | 文字 | 橙色400            |
| `border-orange-500/30` | 边框 | 橙色500，30%透明度 |

**颜色计算**

- 背景: `rgba(249, 115, 22, 0.1)`
- 文字: `#fb923c`
- 边框: `rgba(249, 115, 22, 0.3)`

#### 6. 耗时列

```tsx
<TableCell className="text-white">{record.duration}</TableCell>
```

**样式规范**

- 文字颜色: `text-white`
- 内容格式: `XXmin XXs`

#### 7. 状态列（复杂列 - 重点设计）

##### 状态标签配置

```tsx
const statusLabels: Record<string, { label: string; icon: any; className: string }> = {
  ok: { 
    label: 'OK', 
    icon: CheckCircle,
    className: 'bg-green-500/10 text-green-400 border-green-500/30' 
  },
  ng: { 
    label: 'NG', 
    icon: XCircle,
    className: 'bg-red-500/10 text-red-400 border-red-500/30' 
  },
  conditional: { 
    label: '条件通过', 
    icon: AlertCircle,
    className: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30' 
  }
};
```

##### 渲染结构

```tsx
<TableCell>
  <Badge className={`flex items-center gap-1 w-fit ${statusLabels[record.status].className}`}>
    <StatusIcon className="w-3 h-3" />
    {statusLabels[record.status].label}
  </Badge>
  {record.defects.length > 0 && (
    <div className="text-xs text-red-400 mt-1">
      {record.defects.join(', ')}
    </div>
  )}
</TableCell>
```

##### OK状态 Badge详细样式

| 属性     | 类名                    | 实际值                 |
| -------- | ----------------------- | ---------------------- |
| Flex布局 | `flex items-center`   | 水平排列，垂直居中     |
| 图标间距 | `gap-1`               | 4px                    |
| 宽度     | `w-fit`               | 适应内容               |
| 背景色   | `bg-green-500/10`     | rgba(34, 197, 94, 0.1) |
| 文字颜色 | `text-green-400`      | #4ade80                |
| 边框     | `border-green-500/30` | rgba(34, 197, 94, 0.3) |
| 图标尺寸 | `w-3 h-3`             | 12×12px               |

##### NG状态 Badge详细样式

| 属性     | 类名                  | 实际值                 |
| -------- | --------------------- | ---------------------- |
| 背景色   | `bg-red-500/10`     | rgba(239, 68, 68, 0.1) |
| 文字颜色 | `text-red-400`      | #f87171                |
| 边框     | `border-red-500/30` | rgba(239, 68, 68, 0.3) |
| 图标     | `<XCircle />`       | X形圆圈图标            |

##### 条件通过状态 Badge详细样式

| 属性     | 类名                     | 实际值                 |
| -------- | ------------------------ | ---------------------- |
| 背景色   | `bg-yellow-500/10`     | rgba(234, 179, 8, 0.1) |
| 文字颜色 | `text-yellow-400`      | #facc15                |
| 边框     | `border-yellow-500/30` | rgba(234, 179, 8, 0.3) |
| 图标     | `<AlertCircle />`      | 感叹号圆圈图标         |

##### 缺陷信息显示

```tsx
{record.defects.length > 0 && (
  <div className="text-xs text-red-400 mt-1">
    {record.defects.join(', ')}
  </div>
)}
```

**样式规范**

| 属性     | 类名             | 说明                    |
| -------- | ---------------- | ----------------------- |
| 字号     | `text-xs`      | 12px                    |
| 颜色     | `text-red-400` | 红色，表示错误          |
| 上边距   | `mt-1`         | 4px，与Badge分隔        |
| 内容格式 | 逗号分隔         | "焊点缺失, PCB位置偏移" |

**视觉示例**

```
┌────────────────────────┐
│ [×] NG                 │  ← Badge（红色）
│ 焊点缺失, PCB位置偏移    │  ← 缺陷信息（红色小字）
└────────────────────────┘
```

#### 8. 操作列（操作按钮）

```tsx
<TableCell>
  <Button className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white h-8">
    <Eye className="w-3 h-3 mr-1" />
    详情
  </Button>
</TableCell>
```

**按钮样式详解**

| 状态      | 属性                        | 值           |
| --------- | --------------------------- | ------------ |
| 默认-背景 | `bg-transparent`          | 透明         |
| 默认-边框 | `border border-[#3a3a3a]` | 1px 灰色边框 |
| 默认-文字 | `text-gray-400`           | 中灰色       |
| 悬停-背景 | `hover:bg-[#2a2a2a]`      | 深灰色       |
| 悬停-文字 | `hover:text-white`        | 纯白色       |
| 高度      | `h-8`                     | 32px         |
| 图标尺寸  | `w-3 h-3`                 | 12×12px     |
| 图标间距  | `mr-1`                    | 4px          |

## 颜色系统完整规范

### 背景色色板

| 用途     | 颜色值      | Tailwind类       | RGB值           | 使用场景           |
| -------- | ----------- | ---------------- | --------------- | ------------------ |
| 最深背景 | `#1a1a1a` | `bg-[#1a1a1a]` | RGB(26, 26, 26) | 输入框、深层容器   |
| 深背景   | `#1f1f1f` | `bg-[#1f1f1f]` | RGB(31, 31, 31) | 搜索栏背景         |
| 标准背景 | `#252525` | `bg-[#252525]` | RGB(37, 37, 37) | 表格、卡片、标题栏 |
| 悬停背景 | `#2a2a2a` | `bg-[#2a2a2a]` | RGB(42, 42, 42) | 行悬停、按钮悬停   |

### 边框色色板

| 用途     | 颜色值      | Tailwind类           | RGB值           |
| -------- | ----------- | -------------------- | --------------- |
| 标准边框 | `#3a3a3a` | `border-[#3a3a3a]` | RGB(58, 58, 58) |

### 文字色色板

| 用途     | Tailwind类        | 颜色值  | 使用场景       |
| -------- | ----------------- | ------- | -------------- |
| 主要文字 | `text-white`    | #ffffff | 数据内容、标题 |
| 次要文字 | `text-gray-400` | #9ca3af | 表头、辅助信息 |
| 三级文字 | `text-gray-500` | #6b7280 | 子标题、次要ID |
| 占位文字 | `text-gray-600` | #4b5563 | 输入框占位符   |

### 状态色色板（重点）

#### OK状态（绿色系）

| 用途 | 类名                    | 颜色值  | 透明度 |
| ---- | ----------------------- | ------- | ------ |
| 背景 | `bg-green-500/10`     | #22c55e | 10%    |
| 文字 | `text-green-400`      | #4ade80 | 100%   |
| 边框 | `border-green-500/30` | #22c55e | 30%    |

#### NG状态（红色系）

| 用途     | 类名                  | 颜色值  | 透明度 |
| -------- | --------------------- | ------- | ------ |
| 背景     | `bg-red-500/10`     | #ef4444 | 10%    |
| 文字     | `text-red-400`      | #f87171 | 100%   |
| 边框     | `border-red-500/30` | #ef4444 | 30%    |
| 缺陷信息 | `text-red-400`      | #f87171 | 100%   |

#### 条件通过状态（黄色系）

| 用途 | 类名                     | 颜色值  | 透明度 |
| ---- | ------------------------ | ------- | ------ |
| 背景 | `bg-yellow-500/10`     | #eab308 | 10%    |
| 文字 | `text-yellow-400`      | #facc15 | 100%   |
| 边框 | `border-yellow-500/30` | #eab308 | 30%    |

#### 橙色主题（工位标识）

| 用途     | 类名                     | 颜色值  | 透明度 |
| -------- | ------------------------ | ------- | ------ |
| 背景     | `bg-orange-500/10`     | #f97316 | 10%    |
| 文字     | `text-orange-400`      | #fb923c | 100%   |
| 边框     | `border-orange-500/30` | #f97316 | 30%    |
| 按钮主色 | `bg-orange-500`        | #f97316 | 100%   |
| 按钮悬停 | `hover:bg-orange-600`  | #ea580c | 100%   |

## 图标使用规范

### 图标库

使用 `lucide-react` 图标库

### 页面级图标

| 图标     | 组件                  | 尺寸               | 颜色                | 用途         |
| -------- | --------------------- | ------------------ | ------------------- | ------------ |
| 列表图标 | `<ClipboardList />` | `w-5 h-5` (20px) | `text-orange-500` | 页面标题     |
| 日历图标 | `<Calendar />`      | `w-4 h-4` (16px) | 继承按钮颜色        | 选择日期按钮 |
| 下载图标 | `<Download />`      | `w-4 h-4` (16px) | 继承按钮颜色        | 导出报表按钮 |
| 搜索图标 | `<Search />`        | `w-4 h-4` (16px) | `text-gray-500`   | 搜索输入框   |
| 筛选图标 | `<Filter />`        | `w-4 h-4` (16px) | 继承选择器颜色      | 状态筛选     |

### 状态图标

| 图标     | 组件                | 尺寸               | 颜色                | 状态     |
| -------- | ------------------- | ------------------ | ------------------- | -------- |
| 成功图标 | `<CheckCircle />` | `w-3 h-3` (12px) | `text-green-400`  | OK状态   |
| 失败图标 | `<XCircle />`     | `w-3 h-3` (12px) | `text-red-400`    | NG状态   |
| 警告图标 | `<AlertCircle />` | `w-3 h-3` (12px) | `text-yellow-400` | 条件通过 |

### 操作图标

| 图标     | 组件        | 尺寸               | 用途     |
| -------- | ----------- | ------------------ | -------- |
| 查看图标 | `<Eye />` | `w-3 h-3` (12px) | 详情按钮 |

## 交互设计规范

### 悬停效果 (Hover States)

#### 表格行悬停

```tsx
className="border-[#3a3a3a] hover:bg-[#2a2a2a]"
```

- **默认**: 透明背景，灰色边框
- **悬停**: 深灰色背景 `#2a2a2a`
- **过渡**: 平滑过渡（继承自组件）

#### 按钮悬停

**次要按钮**

```tsx
className="bg-transparent ... hover:bg-[#2a2a2a] hover:text-white"
```

- 默认: 透明背景，灰色文字
- 悬停: 深灰背景，白色文字

**主要按钮**

```tsx
className="bg-orange-500 hover:bg-orange-600"
```

- 默认: 橙色500
- 悬停: 橙色600（加深）

### 视觉反馈规范

#### 状态指示

1. **颜色编码**: 绿色=好，红色=坏，黄色=警告
2. **图标辅助**: 每种状态配有独特图标
3. **文字说明**: 状态名称清晰可读

#### 层次结构

1. **主要信息**: 白色文字（记录编号、产品SN）
2. **次要信息**: 灰色文字（工艺编号）
3. **辅助信息**: 小号灰色文字（缺陷详情）

## 数据过滤和搜索

### 过滤逻辑

```tsx
const filteredRecords = records.filter(record => {
  const matchesSearch = record.recordId.toLowerCase().includes(searchTerm.toLowerCase()) ||
                       record.productSN.toLowerCase().includes(searchTerm.toLowerCase()) ||
                       record.processTitle.toLowerCase().includes(searchTerm.toLowerCase());
  const matchesStatus = filterStatus === 'all' || record.status === filterStatus;
  return matchesSearch && matchesStatus;
});
```

### 搜索字段

- 记录编号 (recordId)
- 产品SN (productSN)
- 工艺名称 (processTitle)

### 筛选选项

- 所有状态 (all)
- OK (ok)
- NG (ng)
- 条件通过 (conditional)

## 数据结构规范

### 记录数据模型

```typescript
interface WorkRecord {
  id: number;                    // 唯一ID
  recordId: string;              // 记录编号 REC-YYYYMMDDXXXXX
  processName: string;           // 工艺编号 XXX-XXX-YYYY-XXX
  processTitle: string;          // 工艺名称
  productSN: string;             // 产品SN号
  orderNo: string;               // 订单号
  operator: string;              // 操作员姓名
  workstation: string;           // 工位号 A01, B02等
  status: 'ok' | 'ng' | 'conditional';  // 状态
  startTime: string;             // 开始时间 YYYY-MM-DD HH:mm:ss
  endTime: string;               // 结束时间
  duration: string;              // 耗时 XXmin XXs
  defects: string[];             // 缺陷列表（仅NG和条件通过）
}
```

### 状态标签配置模型

```typescript
interface StatusLabel {
  label: string;                 // 显示文本
  icon: React.ComponentType;     // 图标组件
  className: string;             // CSS类名
}

const statusLabels: Record<string, StatusLabel> = {
  ok: { ... },
  ng: { ... },
  conditional: { ... }
};
```

## 表格列配置

### 列宽策略

| 列名     | 策略 | 预估宽度 | 说明               |
| -------- | ---- | -------- | ------------------ |
| 记录编号 | 自动 | ~150px   | 固定格式ID         |
| 产品SN   | 自动 | ~130px   | 固定格式SN         |
| 工艺名称 | 弹性 | ~200px   | 双行显示，较宽     |
| 操作员   | 固定 | ~80px    | 姓名简短           |
| 工位     | 固定 | ~80px    | Badge固定尺寸      |
| 耗时     | 固定 | ~100px   | 时间格式固定       |
| 状态     | 弹性 | ~150px   | Badge + 可能的缺陷 |
| 操作     | 固定 | ~100px   | 单个按钮           |

### 内容对齐

- **默认**: 左对齐
- **数值**: 可考虑右对齐（如耗时）
- **操作**: 左对齐

## 响应式设计

### 滚动策略

```tsx
<div className="flex-1 overflow-y-auto p-6">
```

- 垂直滚动: 表格内容区域独立滚动
- 表头固定: 由ShadCN Table组件实现
- 水平滚动: 表格宽度不足时自动出现

### 最小宽度建议

- **容器最小宽度**: 1200px（建议）
- **表格自然宽度**: 根据内容自适应
- **移动端**: 考虑横向滚动或响应式重构

## 可访问性规范

### 语义化HTML

- 使用 `<Table>`, `<TableHead>`, `<TableBody>`, `<TableRow>`, `<TableCell>` 组件
- 保持正确的DOM层级结构

### 键盘导航

- 按钮可通过Tab键聚焦
- Enter键触发按钮操作
- 输入框和选择器支持标准键盘操作

### 颜色对比度

- 主要文字（白色）与背景对比度 > 7:1
- 次要文字（灰色400）与背景对比度 > 4.5:1
- 状态颜色与背景保持足够对比

### 状态指示

- 不仅依赖颜色，同时使用图标
- 缺陷信息提供文字说明

## 性能优化

### 渲染优化

```tsx
{filteredRecords.map(record => {
  const StatusIcon = statusLabels[record.status].icon;
  return (
    <TableRow key={record.id} className="...">
      {/* 单元格内容 */}
    </TableRow>
  );
})}
```

- 使用唯一 `key` 值优化列表渲染
- 状态图标组件预先提取避免重复查找

### 数据加载

- 考虑分页加载大量数据
- 实现虚拟滚动处理超长列表
- 搜索和筛选在前端实时处理

## 扩展功能建议

### 未来增强

1. **列排序**: 点击表头按各列排序
2. **列筛选**: 每列独立筛选条件
3. **批量操作**: 多选记录批量导出
4. **详情抽屉**: 点击详情按钮打开侧边详情面板
5. **日期范围**: 精确的日期范围选择器
6. **分页**: 大数据量时的分页控制
7. **列可见性**: 用户自定义显示的列
8. **导出格式**: 支持Excel、CSV、PDF多种格式

### 表格增强组件

```tsx
// 未来可能的扩展
<TableActions>
  <BulkSelect />
  <ColumnVisibility />
  <ExportOptions />
</TableActions>
```

## ShadCN Table组件特性

### 默认样式

ShadCN的Table组件已内置以下样式：

- 单元格内边距
- 边框样式
- 响应式行为
- 文字对齐

### 覆写策略

```tsx
// 需要覆写时明确指定
<TableCell className="text-white">  // 覆写默认文字颜色
<TableRow className="hover:bg-[#2a2a2a]">  // 覆写默认悬停
```

## 设计原则总结

1. **清晰的视觉层次**: 通过颜色、字号、粗细区分信息优先级
2. **状态一目了然**: 颜色+图标双重编码，快速识别记录状态
3. **高效的数据浏览**: 紧凑布局，合理间距，便于快速扫描
4. **直观的交互反馈**: 悬停高亮，操作按钮明确
5. **深色工业风格**: 低对比度背景减少视觉疲劳
6. **橙色品牌强调**: 主要操作和工位标识使用橙色
7. **错误醒目标识**: NG状态和缺陷信息用红色突出
8. **信息密度平衡**: 双行显示提供更多信息而不显拥挤
9. **一致的间距系统**: 使用4px基准的间距体系
10. **渐进式细节披露**: 缺陷信息仅在需要时显示

## 完整样式速查表

### 快速复制样式

**容器**

```tsx
外层: "flex-1 flex flex-col overflow-hidden"
标题栏: "bg-[#252525] border-b border-[#3a3a3a] px-6 py-4 flex-shrink-0"
搜索栏: "bg-[#1f1f1f] border-b border-[#3a3a3a] px-6 py-3 flex-shrink-0"
表格区: "flex-1 overflow-y-auto p-6"
表格包装: "bg-[#252525] border border-[#3a3a3a] rounded-lg overflow-hidden"
```

**表格元素**

```tsx
TableRow: "border-[#3a3a3a] hover:bg-[#2a2a2a]"
TableHead: "text-gray-400"
TableCell(主): "text-white"
TableCell(辅): "text-gray-500 text-xs"
```

**Badge状态**

```tsx
OK: "bg-green-500/10 text-green-400 border-green-500/30"
NG: "bg-red-500/10 text-red-400 border-red-500/30"
条件通过: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30"
工位: "bg-orange-500/10 text-orange-400 border-orange-500/30"
```

**按钮**

```tsx
主要: "bg-orange-500 hover:bg-orange-600 text-white"
次要: "bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white"
详情: "bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white h-8"
```

**输入框**

```tsx
Search: "pl-10 bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
Select Trigger: "w-48 bg-[#1a1a1a] border-[#3a3a3a] text-white"
Select Content: "bg-[#252525] border-[#3a3a3a]"
```

---

**文档版本**: v1.0
**最后更新**: 2024-11-08
**适用组件**: WorkRecordsPanel
**设计系统**: ProcVision Industrial Design System
