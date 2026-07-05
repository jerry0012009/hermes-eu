---
name: hxcloud-api
description: 华心云 (HXCloud) 统一入口 - 月报确认、咨询记录撰写、访谈记录、排班管理等所有后端API自动化
triggers:
  - 华心云
  - HXCloud
  - 月报
  - 咨询记录
  - 访谈记录
  - 排班
  - 西华大学心理
  - 咨询师确认
---

# 华心云 (HXCloud) 统一入口

## 系统信息
- 前端: http://jerrypsy.top:8105/
- API: `http://jerrypsy.top:8105/admin-api`
- 租户: 西华大学 (ID=163)
- 框架: 芋道 (Yudao/iocoder) ruoyi-vue-pro

## 账号
| 角色 | 用户名 | 密码 | userId | 备注 |
|------|--------|------|--------|------|
| 咨询师 | 0720200029 | Admin.123456 | 155 | 王中瑞，日常操作用这个 |
| 管理员 | admin | Admin.123456 | 140 | 修复/reset时配合使用 |

## Python 工具库
`/root/jerry/HXCloud/hxcloud_api.py`
```python
import sys; sys.path.insert(0, '/root/jerry/HXCloud')
from hxcloud_api import HXCloud
hx = HXCloud()  # 默认用咨询师账号
hx.login()
```

## API 速查

### 通用
```
POST /system/auth/login          # 登录 (Header: tenant-id: 163)
GET  /system/auth/get-permission-info  # 用户权限
GET  /system/tenant/get-id-by-name?name=西华大学  # 租户ID
```

### 月报管理 (psm) ⭐
```
GET  /psm/month-record/page                          # 月报列表
GET  /psm/month-record/get?id=                       # 月报详情
GET  /psm/month-record-detail/page?monthRecordId=&monthRecordDetailStatus=&belongCounselorId=  # 明细列表
GET  /psm/month-record-detail/get?id=                # 单条明细
POST /psm/month-record-detail/updateByCounselor      # 咨询师确认 (body=完整记录)
POST /psm/month-record-detail/updateByInstructor     # 辅导员确认 (body=完整记录)
POST /psm/month-record-detail/reset?id=              # 重置 (退到instructor_collect)
```

### 咨询记录 (psa)
```
GET  /psa/appoint-record/page         # ⭐ 预约记录（查待填写用这个！）
# 待填写: appointRecordStatus == 'yiguo_zixun_shijian'

GET  /psa/consult-record/page         # 咨询记录列表（已填写的）
GET  /psa/consult-record/get?id=      # 单条记录
GET  /psa/consult-record/getConsultRecordByAppointId?appointRecordId=  # 按预约查
POST /psa/consult-record/create       # ⭐ 创建 (POST)
PUT  /psa/consult-record/update       # 更新 (⚠️ 是PUT不是POST！)
GET  /psa/consult-record/delete?id=   # 删除
GET  /psa/consult-view/page           # 联合查询视图 (只读)
GET  /psa/schedule-standard/page      # 排班标准
```

### 访谈记录 (psy)
```
GET  /psy/interview-record/page       # 访谈记录列表
GET  /psy/interview-record/page_my    # 我的访谈记录
POST /psy/interview-record/create     # 创建
POST /psy/interview-record/update     # 更新
GET  /psy/interview-template/page     # 访谈模板列表
```

### 学生 & 测评 (psc / pss)
```
GET  /psc/student/page                # 学生列表
GET  /pss/survey-distributions-admin/page  # 测评计划
```

## 咨询记录创建完整流程 ⭐

```
# 1. 从"我的预约（咨询师）"找待填写
GET  /psa/appoint-record/page
# 筛选: appointRecordStatus == 'yiguo_zixun_shijian'（已过咨询时间）
# ⚠️ 不是 consult-view/page！那是联合查询视图

# 2. 确认该预约没有已有记录
GET  /psa/consult-record/getConsultRecordByAppointId?appointRecordId=xxx
# 返回 data=null 表示没有记录，可以创建

# 3. 查该学生的历史记录（确保连续性+差异性）
GET  /psa/consult-view/page?studentId=xxx

# 4. 创建咨询记录
POST /psa/consult-record/create
Body: {
  "appointId": xxx,
  "consultingQuestionType": "xinli",
  "type": "geti",
  "riskType": "wufengxian",
  "consultRecordStatus": "wancheng",   // ⚠️ 必填！
  "subjectiveRecord": "咨询内容..."
}
# ⚠️ 不要带 filepath 字段！
```

## ⚠️ 踩坑记录（必读）

| 坑 | 现象 | 解决 |
|----|------|------|
| consult-view vs appoint-record | consult-view 是联合查询，待填写的预约在 appoint-record/page 里找 | 用 appoint-record/page + status='yiguo_zixun_shijian' |
| consultRecordStatus 必填 | create 时报"咨询记录状态不能为空" | body 里加 `"consultRecordStatus": "wancheng"` |
| update 用 PUT | POST /consult-record/update 返回 405 | 改用 PUT |
| 移除记录缺字段 | `instructorRemoveStatus=jianyi_yichu` 提交报"系统异常" | body 额外加 `counselorRemoveStatus: "jianyi_yichu"` |
| reset 退两步 | reset 从 done 退到 instructor_collect | 需 admin 调 updateByInstructor 恢复 |
| Token 并发互斥 | 同用户并发登录旧 Token 失效 | 一个脚本只 login 一次 |
| 测试内容残留 | "自动化测试""测试提交"写入正式数据 | ⚠️ 所有提交内容必须是正式专业文本 |
| filepath 污染 | 创建时带了附件字段 | 不要在 create/update body 里带 filepath |

## 咨询记录撰写规范

### 风格要求
- **150-250字**，不长不短
- SOAP框架但用自然语言，不写"主观记录（Subjective）："这种标签
- 包含学生"原话"（引号），增加真实感
- 咨询师输出一句专业知识/技能（如呼吸放松、我信息表达、认知重构等）
- **具体但空泛**：提"期中考试""室友""对象"等场景，但不说哪门课、谁的名字、哪家公司
- ⚠️ 每条记录必须有差异，不同学生、不同次不能复制粘贴
- ⚠️ 同学生跨次要有连续性：参考上次内容，体现变化/进展/新的主题

### 内容模板结构
```
[来访者状态/主诉] + [具体场景（模糊化）] + [学生原话（引号）] + [风险评估] + [咨询师做了什么] + [建议]
```

### 变化要素（每次随机组合）
- **主诉开头**：来访者提到/来访者主动来咨询/来访者近期/来访者表示/交流中来访者提到
- **场景**：学业/恋爱/人际/家庭/职业/适应/情绪/睡眠/备考/小组作业/社团
- **原话风格**："也不是什么大事…""就是觉得…""可能是因为…"
- **咨询师动作**：向来访者介绍了/和来访者讨论了/一起梳理了/引导来访者认识到/帮助来访者理解了
- **专业知识**：深呼吸放松、我信息表达、认知行为ABC、情绪日记、渐进式肌肉放松、正念觉察、时间管理四象限、SMART目标、灾难化思维、完美主义认知

## 月报咨询师确认标准流程

```
1. 登录获取 Token
2. 查询历史已完成记录，建立 studentId → counselorMeasure 映射
3. 查询待确认列表 (status=counselor_collect, belongCounselorId=155)
4. 分三类处理：
   a. 有历史 → 回填上次内容
   b. instructorRemoveStatus=jianyi_yichu → 同意移除（需带 counselorRemoveStatus 字段）
   c. 无历史 → 按模板生成
5. ⚠️ 先用1-2条测试，确认无误后再批量
6. 每条：GET 完整记录 → 修改 counselorMeasure → POST updateByCounselor
```

### 出错修复流程
```
1. Admin 登录 → 调 updateByInstructor（原样提交辅导员数据）→ 状态回到 counselor_collect
2. 咨询师登录 → 调 updateByCounselor（提交正确内容）→ 状态回到 done
```

## 文档与脚本 `/root/jerry/HXCloud/`
| 文件 | 内容 |
|------|------|
| `00_login_and_base.md` | 登录方式、枚举值速查 |
| `01_consult_record.md` | 咨询记录 API 详情 |
| `02_monthly_report.md` | 月报管理 API 详情 |
| `03_interview_record.md` | 访谈记录 API 详情 |
| `04_api_full_map.md` | 全量接口地图 |
| `05_dict_reference.md` | 18个数据字典完整映射 |
| `hxcloud_api.py` | Python 工具库 |
| `auto_confirm.py` | 月报批量确认脚本 |
| `templates_counselor_measures.md` | 咨询师措施模板库 |
| `99_experience_log.md` | 操作经验与踩坑记录 |
