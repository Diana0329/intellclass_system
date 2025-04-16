from models import (
    TimeSlot, Teacher, Subject, Class, Schedule,
    ScheduleEntry, ScheduleConfig, WeekDay, DayPart, TimeTable, 
    Priority, Grade
)
from rules import RuleManager
from scheduler import SmartScheduler, SchedulerService
from datetime import time
from typing import List, Dict

def create_test_data(grade: str = "小学三年级", 
                    end_day: str = "星期五",
                    morning_periods: int = 4,
                    afternoon_periods: int = 4,
                    evening_periods: int = 0,
                    selected_classes: List[int] = [1, 2, 3, 4, 5, 6, 7, 8]):
    """
    创建测试数据
    :param grade: 年级名称
    :param end_day: 结束日期
    :param morning_periods: 上午课节数
    :param afternoon_periods: 下午课节数
    :param evening_periods: 晚上课节数
    :param selected_classes: 选中的班级序号列表
    """
    def validate_total_hours(subjects_dict: Dict[str, Subject]) -> bool:
        """验证所有科目的总课时是否等于40"""
        total_hours = sum(subject.weekly_hours for subject in subjects_dict.values())
        if total_hours != 40:
            raise ValueError(f"所有科目的周课时之和必须等于40，当前为{total_hours}")
        return True

    # 1. 创建科目
    subjects = {
        # 主要科目
        "语文": Subject(
            name="语文",
            weekly_hours=8,
            priority=Priority.HIGH,
            requires_consecutive_periods=False,
            max_periods_per_day=2
        ),
        "数学": Subject(
            name="数学",
            weekly_hours=8,
            priority=Priority.HIGH,
            requires_consecutive_periods=False,
            max_periods_per_day=2
        ),
        "英语": Subject(
            name="英语",
            weekly_hours=6,
            priority=Priority.HIGH,
            requires_consecutive_periods=False,
            max_periods_per_day=2
        ),
        
        # 次要科目
        "体育": Subject(
            name="体育",
            weekly_hours=4,
            priority=Priority.MEDIUM,
            requires_consecutive_periods=True,
            max_periods_per_day=1
        ),
        "音乐": Subject(
            name="音乐",
            weekly_hours=2,
            priority=Priority.MEDIUM,
            requires_consecutive_periods=False,
            max_periods_per_day=1
        ),
        "美术": Subject(
            name="美术",
            weekly_hours=2,
            priority=Priority.MEDIUM,
            requires_consecutive_periods=True,
            max_periods_per_day=2
        ),
        
        # 其他科目
        "信息": Subject(
            name="信息",
            weekly_hours=2,
            priority=Priority.LOW,
            requires_consecutive_periods=False,
            max_periods_per_day=1
        ),
        "地理": Subject(
            name="地理",
            weekly_hours=2,
            priority=Priority.LOW,
            requires_consecutive_periods=False,
            max_periods_per_day=1
        ),
        "历史": Subject(
            name="历史",
            weekly_hours=2,
            priority=Priority.LOW,
            requires_consecutive_periods=False,
            max_periods_per_day=1
        ),
        "生物": Subject(
            name="生物",
            weekly_hours=2,
            priority=Priority.LOW,
            requires_consecutive_periods=False,
            max_periods_per_day=1
        ),
        "政治": Subject(
            name="政治",
            weekly_hours=1,
            priority=Priority.LOW,
            requires_consecutive_periods=False,
            max_periods_per_day=1
        ),
        "班会": Subject(
            name="班会",
            weekly_hours=1,
            priority=Priority.LOW,
            requires_consecutive_periods=False,
            max_periods_per_day=1
        ),
    }

    # 验证总课时
    validate_total_hours(subjects)

    # 根据课时数自动设置优先级
    sorted_subjects = sorted(subjects.values(), key=lambda x: x.weekly_hours, reverse=True)
    for i, subject in enumerate(sorted_subjects):
        if i < 3:  # 课时最多的3门课
            subject.priority = Priority.HIGH
        elif i < 6:  # 接下来的3门课
            subject.priority = Priority.MEDIUM
        else:  # 其余课程
            subject.priority = Priority.LOW

    # 2. 创建教师
    teachers = [
        # 语文教师（10人）
        Teacher(id="T001", name="陈语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T002", name="李语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T003", name="王语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T004", name="张语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T005", name="刘语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        # 新增语文教师
        Teacher(id="T101", name="赵语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T102", name="钱语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T103", name="孙语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T104", name="周语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T105", name="吴语文", subjects=["语文"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 数学教师（10人）
        Teacher(id="T006", name="陈数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T007", name="李数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T008", name="王数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T009", name="张数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T010", name="刘数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        # 新增数学教师
        Teacher(id="T106", name="赵数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T107", name="钱数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T108", name="孙数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T109", name="周数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T110", name="吴数学", subjects=["数学"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 英语教师（10人）
        Teacher(id="T011", name="陈英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T012", name="李英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T013", name="王英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T014", name="张英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T015", name="刘英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        # 新增英语教师
        Teacher(id="T111", name="赵英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T112", name="钱英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T113", name="孙英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T114", name="周英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T115", name="吴英语", subjects=["英语"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 体育教师
        Teacher(id="T016", name="陈体育", subjects=["体育"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T017", name="李体育", subjects=["体育"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T018", name="王体育", subjects=["体育"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T019", name="张体育", subjects=["体育"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T020", name="刘体育", subjects=["体育"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 音乐教师
        Teacher(id="T021", name="陈音乐", subjects=["音乐"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T022", name="李音乐", subjects=["音乐"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T023", name="王音乐", subjects=["音乐"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T024", name="张音乐", subjects=["音乐"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T025", name="刘音乐", subjects=["音乐"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 美术教师
        Teacher(id="T026", name="陈美术", subjects=["美术"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T027", name="李美术", subjects=["美术"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T028", name="王美术", subjects=["美术"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T029", name="张美术", subjects=["美术"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T030", name="刘美术", subjects=["美术"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 信息教师
        Teacher(id="T031", name="陈信息", subjects=["信息"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T032", name="李信息", subjects=["信息"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T033", name="王信息", subjects=["信息"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T034", name="张信息", subjects=["信息"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T035", name="刘信息", subjects=["信息"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 地理教师
        Teacher(id="T036", name="陈地理", subjects=["地理"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T037", name="李地理", subjects=["地理"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T038", name="王地理", subjects=["地理"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T039", name="张地理", subjects=["地理"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T040", name="刘地理", subjects=["地理"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 历史教师
        Teacher(id="T041", name="陈历史", subjects=["历史"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T042", name="李历史", subjects=["历史"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T043", name="王历史", subjects=["历史"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T044", name="张历史", subjects=["历史"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T045", name="刘历史", subjects=["历史"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 生物教师
        Teacher(id="T046", name="陈生物", subjects=["生物"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T047", name="李生物", subjects=["生物"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T048", name="王生物", subjects=["生物"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T049", name="张生物", subjects=["生物"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T050", name="刘生物", subjects=["生物"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 政治教师
        Teacher(id="T051", name="陈政治", subjects=["政治"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T052", name="李政治", subjects=["政治"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T053", name="王政治", subjects=["政治"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T054", name="张政治", subjects=["政治"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T055", name="刘政治", subjects=["政治"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 地方教师
        Teacher(id="T056", name="陈地方", subjects=["地方"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T057", name="李地方", subjects=["地方"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T058", name="王地方", subjects=["地方"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T059", name="张地方", subjects=["地方"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T060", name="刘地方", subjects=["地方"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 健康教师
        Teacher(id="T061", name="陈健康", subjects=["健康"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T062", name="李健康", subjects=["健康"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T063", name="王健康", subjects=["健康"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T064", name="张健康", subjects=["健康"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T065", name="刘健康", subjects=["健康"], max_hours_per_day=6, max_hours_per_week=25),
        
        # 班会教师（班主任）
        Teacher(id="T066", name="陈班会", subjects=["班会"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T067", name="李班会", subjects=["班会"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T068", name="王班会", subjects=["班会"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T069", name="张班会", subjects=["班会"], max_hours_per_day=6, max_hours_per_week=25),
        Teacher(id="T070", name="刘班会", subjects=["班会"], max_hours_per_day=6, max_hours_per_week=25),
    ]

    # 3. 创建班级
    grade_enum = Grade(grade)
    classes = []
    for class_num in selected_classes:
        class_id = f"{grade_enum.name[2]}{class_num}"  # 如 "3A" 表示三年级一班
        class_name = f"{grade_enum.value}{class_num}班"
        classes.append(
            Class(
                id=class_id,
                name=class_name,
                grade=grade_enum,
                subjects=list(subjects.values())
            )
        )

    # 4. 创建时间表配置（只保留课节数量的配置）
    timetable = TimeTable(
        periods_per_morning=morning_periods,
        periods_per_afternoon=afternoon_periods,
        periods_per_evening=evening_periods
    )

    # 5. 创建排课配置
    schedule_config = ScheduleConfig.create_config(
        name=f"{grade_enum.value}课表",
        grade=grade,
        end_day=end_day,
        morning_periods=morning_periods,
        afternoon_periods=afternoon_periods,
        evening_periods=evening_periods,
        class_count=len(selected_classes)
    )

    return classes, teachers, schedule_config

def test_schedule_generation(
    grade: str = "小学三年级",
    end_day: str = "星期五",
    morning_periods: int = 4,
    afternoon_periods: int = 4,
    evening_periods: int = 0,
    selected_classes: List[int] = [1, 2, 3, 4, 5, 6, 7, 8]
):
    """
    测试排课生成
    :param grade: 年级名称
    :param end_day: 结束日期
    :param morning_periods: 上午课节数
    :param afternoon_periods: 下午课节数
    :param evening_periods: 晚上课节数
    :param selected_classes: 选中的班级序号列表
    """
    print("开始测试排课生成...")
    print(f"\n配置信息:")
    print(f"年级: {grade}")
    print(f"工作日: 星期一 至 {end_day}")
    print(f"上午课节数: {morning_periods}")
    print(f"下午课节数: {afternoon_periods}")
    print(f"晚上课节数: {evening_periods}")
    print(f"选中班级: {selected_classes}")
    
    # 1. 创建测试数据
    classes, teachers, config = create_test_data(
        grade=grade,
        end_day=end_day,
        morning_periods=morning_periods,
        afternoon_periods=afternoon_periods,
        evening_periods=evening_periods,
        selected_classes=selected_classes
    )
    
    # 2. 创建规则管理器
    rule_manager = RuleManager()
    rule_manager.create_default_rules()
    
    # 3. 创建排课服务
    scheduler_service = SchedulerService(config, rule_manager)
    
    # 4. 生成课表
    result = scheduler_service.create_schedule(
        grade_classes=classes,
        teachers=teachers
    )
    
    # 5. 检查结果
    if result["success"]:
        print("\n✅ 课表生成成功！")
        print(f"\n总共生成 {len(result['schedule'])} 节课")
        
        # 按班级分组显示课表
        class_schedules = {}
        for entry in result["schedule"]:
            class_id = entry["class_id"]
            if class_id not in class_schedules:
                class_schedules[class_id] = []
            class_schedules[class_id].append(entry)
        
        # 打印每个班级的课表
        for class_id, schedule in class_schedules.items():
            print(f"\n{'-'*20} {class_id} 课表 {'-'*20}")
            # 按星期和节次排序
            schedule.sort(key=lambda x: (x["weekday"], x["period"]))
            current_weekday = None
            for entry in schedule:
                if current_weekday != entry["weekday"]:
                    current_weekday = entry["weekday"]
                    print(f"\n{current_weekday}:")
                print(f"第{entry['period']}节 ({entry['day_part']}): "
                      f"{entry['subject']} - {entry['teacher_name']}")
        
        # 验证各种约束
        validate_schedule(result["schedule"], classes, teachers)
        
    else:
        print("\n❌ 课表生成失败！")
        print("错误信息:")
        for error in result["errors"]:
            print(f"- {error}")

def validate_schedule(schedule, classes, teachers):
    """验证生成的课表是否满足基本约束"""
    print("\n开始验证课表约束...")
    
    # 1. 检查教师冲突
    teacher_conflicts = check_teacher_conflicts(schedule)
    if teacher_conflicts:
        print("❌ 发现教师时间冲突:")
        for conflict in teacher_conflicts:
            print(f"- {conflict}")
    else:
        print("✅ 教师安排无冲突")
    
    # 2. 检查班级课程数量
    class_subject_count = check_class_subject_count(schedule, classes)
    if class_subject_count:
        print("❌ 课程数量不符合要求:")
        for msg in class_subject_count:
            print(f"- {msg}")
    else:
        print("✅ 课程数量符合要求")
    
    # 3. 检查教师工作量
    teacher_workload = check_teacher_workload(schedule, teachers)
    if teacher_workload:
        print("❌ 教师工作量超出限制:")
        for msg in teacher_workload:
            print(f"- {msg}")
    else:
        print("✅ 教师工作量符合要求")

def check_teacher_conflicts(schedule):
    """检查教师时间冲突"""
    conflicts = []
    teacher_schedule = {}
    
    for entry in schedule:
        key = (entry["weekday"], entry["period"])
        teacher_id = entry["teacher_id"]
        
        if key in teacher_schedule:
            if teacher_id in teacher_schedule[key]:
                conflicts.append(
                    f"教师 {entry['teacher_name']} 在 {entry['weekday']} "
                    f"第 {entry['period']} 节 ({entry['day_part']}) 存在冲突"
                )
        else:
            teacher_schedule[key] = set()
        
        teacher_schedule[key].add(teacher_id)
    
    return conflicts

def check_class_subject_count(schedule, classes):
    """检查班级课程数量"""
    errors = []
    class_subjects = {}
    
    for entry in schedule:
        key = (entry["class_id"], entry["subject"])
        if key not in class_subjects:
            class_subjects[key] = 0
        class_subjects[key] += 1
    
    for class_ in classes:
        for subject in class_.subjects:
            key = (class_.id, subject.name)
            count = class_subjects.get(key, 0)
            if count != subject.weekly_hours:
                errors.append(
                    f"{class_.name} 的 {subject.name} 课程数量为 {count}，"
                    f"应为 {subject.weekly_hours}"
                )
    
    return errors

def check_teacher_workload(schedule, teachers):
    """检查教师工作量"""
    errors = []
    teacher_daily_hours = {}
    teacher_weekly_hours = {}
    
    for entry in schedule:
        teacher_id = entry["teacher_id"]
        key = (teacher_id, entry["weekday"])
        
        # 统计每日课时
        if key not in teacher_daily_hours:
            teacher_daily_hours[key] = 0
        teacher_daily_hours[key] += 1
        
        # 统计每周课时
        if teacher_id not in teacher_weekly_hours:
            teacher_weekly_hours[teacher_id] = 0
        teacher_weekly_hours[teacher_id] += 1
    
    # 检查限制
    for teacher in teachers:
        # 检查每日课时
        for weekday in WeekDay:
            key = (teacher.id, weekday.value)
            daily_hours = teacher_daily_hours.get(key, 0)
            if daily_hours > teacher.max_hours_per_day:
                errors.append(
                    f"教师 {teacher.name} 在 {weekday.value} 的课时数 ({daily_hours}) "
                    f"超过每日限制 ({teacher.max_hours_per_day})"
                )
        
        # 检查每周课时
        weekly_hours = teacher_weekly_hours.get(teacher.id, 0)
        if weekly_hours > teacher.max_hours_per_week:
            errors.append(
                f"教师 {teacher.name} 的周课时数 ({weekly_hours}) "
                f"超过每周限制 ({teacher.max_hours_per_week})"
            )
    
    return errors

if __name__ == "__main__":
    test_schedule_generation(
        grade="小学三年级",
        end_day="星期五",
        morning_periods=4,
        afternoon_periods=4,
        evening_periods=0,
        selected_classes=[1, 2, 3, 4, 5, 6, 7, 8]
    ) 