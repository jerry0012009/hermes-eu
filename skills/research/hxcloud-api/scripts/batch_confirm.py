#!/usr/bin/env python3
"""
月报咨询师批量确认脚本
用法: python3 /root/.hermes/skills/research/hxcloud-api/scripts/batch_confirm.py [--dry-run]

策略:
  1. 有历史 counselorMeasure → 回填上次内容
  2. 辅导员建议移除 (jianyi_yichu) → 同意移除 (需带 counselorRemoveStatus)
  3. 无历史 → 按规则生成 (见 templates_counselor_measures.md)
"""
import json, sys, requests

BASE = "http://jerrypsy.top:8105/admin-api"
TID = 163
COUNSELOR_ID = 155  # 王中瑞
MONTH_ID = 73       # 当前月报ID，需按需修改
DRY_RUN = "--dry-run" in sys.argv

DIAG_LABELS = {'dep': '抑郁', 'anx': '焦虑', 'sleep': '睡眠障碍', 'ocd': '强迫',
               'ptsd': 'PTSD', 'bipolar': '双相情感障碍', 'psy': '精神分裂症',
               'person': '人格障碍', 'others': '心理健康'}

def gen(rec):
    crisis = rec.get('crisisPlanLevel', '')
    risk = rec.get('suicideInjuryRiskType', '')
    diag = rec.get('psychiatricDiagnosis', '')
    med = rec.get('medicationStatus', '')
    desc = rec.get('studentDesc', '') or ''
    parts = []
    if crisis == 'one':
        if risk in ('changshi', 'harm', 'harmaction', 'recentplan'):
            parts.append("注意评估是否有伤害自己和他人风险（如有明确的计划与尝试，需要突破保密移交监护权，由家长看护），及时调整危机风险等级，或通知家长与学校相关人员。建议该同学心理咨询。")
        else:
            parts.append("密切关注，遵医嘱治疗，建议在规律服药基础上，寻求校内外心理咨询配合。")
    elif crisis == 'two':
        if risk in ('recentidea', 'recentthought', 'recentplan'):
            parts.append("确认该同学目前情绪状态，是否自伤或伤人想法，如有相关风险需要通知并向家长建议继续遵医嘱治疗，或考虑移交家长监护，如无异常情况请继续保持关注。")
        else:
            parts.append("同意通知家长和学校相关人员，委托同学关注动态，鼓励来中心咨询。")
        if diag not in ('none', 'todo', None) and med == 'under':
            parts.append("建议遵医嘱治疗。")
    else:
        if diag not in ('none', 'todo', None):
            if med == 'tingyao':
                parts.append("保持关注，注意评估是否有伤害自己和他人风险，建议该同学遵医嘱服药，鼓励预约心理咨询中心咨询。")
            elif med == 'under':
                parts.append("保持关注，建议规律去精神科复诊，建议寻求心理咨询。")
            elif med == 'yizhu':
                parts.append(f"保持关注，提供关于{DIAG_LABELS.get(diag,'心理健康')}的心理知识，鼓励预约心理咨询中心咨询。")
            else:
                parts.append(f"保持关注，提供关于{DIAG_LABELS.get(diag,'心理健康')}的心理知识，鼓励精神科就诊，鼓励预约心理咨询中心咨询。")
        elif risk in ('recentidea', 'recentthought'):
            parts.append("保持关注生活中可能的突发事件，及时提供必要的支持，定期评估是否存在自伤风险，鼓励来心理中心咨询。")
        elif '挂科' in desc or '学业' in desc:
            parts.append("保持关注，跟进学业成绩，有挂科情况约谈交流，鼓励来心理中心咨询。")
        elif '宿舍' in desc or '舍友' in desc or '寝室' in desc:
            parts.append("保持关注与舍友关系，与生活中可能的突发事件，及时提供必要的支持，鼓励来心理中心咨询。")
        else:
            parts.append("保持关注，提供必要的支持，鼓励来心理中心咨询。")
    if diag == 'todo' or med == 'todo':
        parts.append("请补充该同学精神科诊断后的信息，目前是否正常上学，是否存在自杀或伤害他人的想法或计划。")
    return " ".join(parts)

def main():
    s = requests.Session()
    s.headers.update({"tenant-id": str(TID)})
    r = s.post(f"{BASE}/system/auth/login", json={"username":"0720200029","password":"Admin.123456"})
    s.headers.update({"Authorization": f"Bearer {r.json()['data']['accessToken']}", "Content-Type": "application/json"})
    print(f"登录成功 {'[DRY-RUN]' if DRY_RUN else '[LIVE]'}")

    # Build history
    student_last = {}
    for mid in [69, 70, 71, 73]:
        for page in range(1, 10):
            r = s.get(f"{BASE}/psm/month-record-detail/page", params={
                "monthRecordId": mid, "belongCounselorId": COUNSELOR_ID,
                "monthRecordDetailStatus": "done", "pageNo": page, "pageSize": 50})
            data = r.json()["data"]
            for rec in data["list"]:
                sid = rec["studentId"]
                if rec.get("counselorMeasure"):
                    if sid not in student_last or rec["monthRecordId"] > student_last[sid]["monthRecordId"]:
                        student_last[sid] = rec
            if len(data["list"]) < 50: break
    print(f"历史库: {len(student_last)} 学生")

    # Get pending
    pending = []
    for page in range(1, 10):
        r = s.get(f"{BASE}/psm/month-record-detail/page", params={
            "monthRecordId": MONTH_ID, "monthRecordDetailStatus": "counselor_collect",
            "belongCounselorId": COUNSELOR_ID, "pageNo": page, "pageSize": 50})
        data = r.json()["data"]
        pending.extend(data["list"])
        if len(data["list"]) < 50: break
    print(f"待确认: {len(pending)} 条")

    stats = {"回填": 0, "移除": 0, "生成": 0, "ok": 0, "fail": 0}
    for i, rec in enumerate(pending):
        rid, sid, sname = rec["id"], rec["studentId"], rec["studentName"]
        remove = rec.get("instructorRemoveStatus", "")
        is_removal = remove == "jianyi_yichu"

        if is_removal:
            measure = "同意移除重点关注名单，保持对该同学的正常关注，鼓励自我成长，鼓励预约心理咨询。"
            tag = "移除"; stats["移除"] += 1
        elif sid in student_last:
            measure = student_last[sid].get("counselorMeasure", "")
            tag = "回填"; stats["回填"] += 1
        else:
            measure = gen(rec)
            tag = "生成"; stats["生成"] += 1

        if DRY_RUN:
            print(f"  [{i+1:3d}] {tag} {sname} => {measure[:60]}...")
            stats["ok"] += 1
        else:
            full = s.get(f"{BASE}/psm/month-record-detail/get", params={"id": rid}).json()["data"]
            full["counselorMeasure"] = measure
            if is_removal:
                full["counselorRemoveStatus"] = "jianyi_yichu"  # P1: 移除必须带此字段
            r = s.post(f"{BASE}/psm/month-record-detail/updateByCounselor", json=full)
            if r.json().get("code") == 0:
                stats["ok"] += 1
                print(f"  [{i+1:3d}] ✅ [{tag}] {sname}")
            else:
                stats["fail"] += 1
                print(f"  [{i+1:3d}] ❌ [{tag}] {sname}: {r.json().get('msg','')}")

    print(f"\n{'='*50}\n结果: 回填={stats['回填']} 移除={stats['移除']} 生成={stats['生成']} 成功={stats['ok']} 失败={stats['fail']}")

if __name__ == "__main__":
    main()
