from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from datetime import time
import random
from models import (
    TimeSlot, Subject, Teacher, Classroom, Class, Schedule,
    ScheduleEntry, ScheduleConfig, WeekDay, DayPart, TimeTable
)
from rules import (Rule, RuleResult, RuleManager)
import logging

logger = logging.getLogger(__name__)

@dataclass
class SchedulingConstraints:
    """排课约束条件"""
    max_daily_hours: Dict[str, int] = field(default_factory=lambda: {"default": 8})
    preferred_time_slots: Dict[str, List[TimeSlot]] = field(default_factory=dict)
    subject_consecutive: Dict[str, bool] = field(default_factory=dict)
    special_room_requirements: Dict[str, Set[str]] = field(default_factory=dict)

class SmartScheduler:
    def __init__(self, config: ScheduleConfig, rule_manager: RuleManager):
        self.config = config
        self.rule_manager = rule_manager
        self.schedule = Schedule(config=config)
        self.constraints = SchedulingConstraints()

    def generate_schedule(self, classes: List[Class], teachers: List[Teacher],
                          classrooms: List[Classroom]) -> Tuple[Schedule, List[str]]:
        """生成完整的课表"""
        errors = []

        # 1. 按优先级对班级的科目进行排序
        for class_ in classes:
            sorted_subjects = sorted(
                class_.subjects,
                key=lambda s: (s.priority, s.weekly_hours),
                reverse=True
            )

            # 2. 为每个科目分配时间段
            for subject in sorted_subjects:
                remaining_hours = subject.weekly_hours
                while remaining_hours > 0:
                    entry = self._try_schedule_subject(
                        class_, subject, teachers, classrooms
                    )
                    if entry:
                        result = self.schedule.add_entry(entry)
                        if not result:
                            errors.append(f"无法为 {class_.name} 安排 {subject.name} 课程：规则冲突")
                            break
                        remaining_hours -= 1
                    else:
                        # 添加更详细的错误信息
                        available_teachers = [t for t in teachers if subject.name in t.subjects]
                        if not available_teachers:
                            errors.append(f"无法为 {class_.name} 安排 {subject.name} 课程：没有合适的教师")
                        else:
                            suitable_classrooms = [c for c in classrooms if c.is_suitable_for(subject)]
                            if not suitable_classrooms:
                                errors.append(f"无法为 {class_.name} 安排 {subject.name} 课程：没有合适的教室")
                            else:
                                errors.append(f"无法为 {class_.name} 安排 {subject.name} 课程：时间段冲突")
                        break

        return self.schedule, errors

    def _try_schedule_subject(self, class_: Class, subject: Subject,
                              teachers: List[Teacher], classrooms: List[Classroom]) -> Optional[ScheduleEntry]:
        """尝试为单个科目安排时间段"""
        # 1. 找到合适的教师
        available_teachers = [
            t for t in teachers
            if subject.name in t.subjects
        ]
        if not available_teachers:
            logger.debug(f"没有找到可教授 {subject.name} 的教师")
            return None

        # 2. 找到合适的教室
        suitable_classrooms = [
            c for c in classrooms
            if (c.is_suitable_for(subject) and c.capacity >= class_.student_count)
        ]
        if not suitable_classrooms:
            logger.debug(f"没有找到适合 {subject.name} 的教室")
            return None

        # 3. 尝试多次安排，增加成功概率
        max_attempts = 3  # 最大尝试次数
        for attempt in range(max_attempts):
            # 随机打乱星期和节次的顺序，以获得更均匀的分配
            weekdays = list(self.config.weekdays)
            random.shuffle(weekdays)
            periods = list(range(1, self._get_daily_periods()))
            random.shuffle(periods)

            for weekday in weekdays:
                for period in periods:
                    time_slot = self._create_time_slot(weekday, period)

                    # 检查科目是否可以在该时间段安排
                    if not subject.can_be_scheduled_at(time_slot):
                        logger.debug(f"{subject.name} 不能在 {weekday.name} 第{period}节安排")
                        continue

                    # 随机打乱教师和教室列表，以获得更均匀的分配
                    random.shuffle(available_teachers)
                    random.shuffle(suitable_classrooms)

                    # 4. 尝试不同的教师和教室组合
                    for teacher in available_teachers:
                        if not teacher.is_available_at(time_slot):
                            logger.debug(f"教师 {teacher.name} 在该时段不可用")
                            continue

                        for classroom in suitable_classrooms:
                            if not classroom.is_available_at(time_slot):
                                logger.debug(f"教室 {classroom.name} 在该时段不可用")
                                continue

                            # 创建课程条目
                            entry = ScheduleEntry(
                                class_info=class_,
                                subject=subject,
                                teacher=teacher,
                                classroom=classroom,
                                time_slot=time_slot
                            )

                            # 检查是否符合所有规则
                            if not self.schedule.has_conflicts(entry):
                                return entry
                            else:
                                logger.debug(f"课程安排与现有课表冲突")

        return None

    def _create_time_slot(self, weekday: WeekDay, period: int) -> TimeSlot:
        """创建时间段"""
        start_time, end_time = self.config.timetable.get_period_time(period)
        day_part = self._get_day_part(period)
        return TimeSlot(
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            period_number=period,
            day_part=day_part
        )

    def _get_day_part(self, period: int) -> DayPart:
        """获取时间段所属的部分（上午/下午/晚上）"""
        if period <= self.config.timetable.periods_per_morning:
            return DayPart.MORNING
        elif period <= (self.config.timetable.periods_per_morning +
                        self.config.timetable.periods_per_afternoon):
            return DayPart.AFTERNOON
        return DayPart.EVENING

    def _get_daily_periods(self) -> int:
        """获取每天的总课时数"""
        return (self.config.timetable.periods_per_morning +
                self.config.timetable.periods_per_afternoon +
                self.config.timetable.periods_per_evening)

class SchedulerService:
    """排课服务类，提供高层接口"""
    def __init__(self, config: ScheduleConfig, rule_manager: RuleManager):
        self.scheduler = SmartScheduler(config, rule_manager)

    def create_schedule(self, classes: List[Class], teachers: List[Teacher],
                        classrooms: List[Classroom]) -> Dict:
        """创建课表"""
        try:
            schedule, errors = self.scheduler.generate_schedule(
                classes, teachers, classrooms
            )

            result = {
                "success": len(errors) == 0,
                "schedule": self._format_schedule(schedule),
                "errors": errors
            }

            if result["success"]:
                logger.info("课表生成成功")
            else:
                logger.warning(f"课表生成存在问题: {errors}")

            return result

        except Exception as e:
            logger.error(f"生成课表时发生错误: {str(e)}")
            return {
                "success": False,
                "schedule": [],
                "errors": [f"系统错误: {str(e)}"]
            }

    def _format_schedule(self, schedule: Schedule) -> List[Dict]:
        """格式化课表输出"""
        # 创建星期几的中文映射
        weekday_map = {
            'monday': '一',
            'tuesday': '二',
            'wednesday': '三',
            'thursday': '四',
            'friday': '五'
        }
        
        formatted = []
        for entry in schedule.entries:
            formatted.append({
                "class": entry.class_info.name,
                "subject": entry.subject.name,
                "teacher": entry.teacher.name,
                "classroom": entry.classroom.name,
                "weekday": weekday_map[entry.time_slot.weekday.value],  # 转换为中文星期
                "period": entry.time_slot.period_number,
                "time": f"{entry.time_slot.start_time}-{entry.time_slot.end_time}"
            })
        return formatted



# 使用示例
if __name__ == "__main__":
    # 创建配置
    config = ScheduleConfig(
        name="示例课表",
        weekdays=[WeekDay.MONDAY, WeekDay.TUESDAY, WeekDay.WEDNESDAY, 
                 WeekDay.THURSDAY, WeekDay.FRIDAY],
        timetable=TimeTable(
            class_duration=45,
            break_duration=10,
            morning_start=time(8, 0),
            afternoon_start=time(14, 0),
            periods_per_morning=4,
            periods_per_afternoon=4  # 总共8节课
        )
    )
    
    # 创建规则管理器
    rule_manager = RuleManager()
    rule_manager.create_default_rules()
    
    # 准备测试数据
    # 1. 创建科目
    subjects = [
        Subject(
            name="数学",
            category="主科",
            weekly_hours=5,
            priority=1,
            requires_consecutive_periods=False,
            max_periods_per_day=2
        ),
        Subject(
            name="语文",
            category="主科",
            weekly_hours=5,
            priority=1,
            requires_consecutive_periods=False,
            max_periods_per_day=2
        ),
        Subject(
            name="英语",
            category="主科",
            weekly_hours=4,
            priority=1,
            requires_consecutive_periods=False,
            max_periods_per_day=2
        ),
        Subject(
            name="物理",
            category="理科",
            weekly_hours=3,
            priority=2,
            requires_consecutive_periods=True,
            max_periods_per_day=2,
            required_room_types={"理科教室"}
        ),
        Subject(
            name="化学",
            category="理科",
            weekly_hours=3,
            priority=2,
            requires_consecutive_periods=True,
            max_periods_per_day=2,
            required_room_types={"理科教室"}
        ),
        Subject(
            name="生物",
            category="理科",
            weekly_hours=3,
            priority=2,
            requires_consecutive_periods=True,
            max_periods_per_day=2,
            required_room_types={"理科教室"}
        ),
        Subject(
            name="历史",
            category="文科",
            weekly_hours=3,
            priority=2,
            requires_consecutive_periods=True,
            max_periods_per_day=2,
            required_room_types={"文科教室"}
        ),
        Subject(
            name="地理",
            category="文科",
            weekly_hours=3,
            priority=2,
            requires_consecutive_periods=True,
            max_periods_per_day=2,
            required_room_types={"文科教室"}
        ),
        Subject(
            name="政治",
            category="文科",
            weekly_hours=3,
            priority=2,
            requires_consecutive_periods=True,
            max_periods_per_day=2,
            required_room_types={"文科教室"}
        )
    ]
    
    # 2. 创建教师
    teachers = [
        Teacher(
            id="T001",
            name="熊敏学",
            subjects=["数学"]
        ),
        Teacher(
            id="T002",
            name="胡阳冰",
            subjects=["语文"]
        ),
        Teacher(
            id="T003",
            name="康子明",
            subjects=["英语"]
        ),
        Teacher(
            id="T004",
            name="王英文",
            subjects=["英语"]
        ),
        Teacher(
            id="T005",
            name="吕绍祺",
            subjects=["化学"]
        ),
        Teacher(
            id="T006",
            name="任雅昶",
            subjects=["生物"]
        ),
        Teacher(
            id="T007",
            name="姜意远",
            subjects=["历史"]
        ),
        Teacher(
            id="T008",
            name="周才英",
            subjects=["地理"]
        ),
        Teacher(
            id="T009",
            name="陈阳飙",
            subjects=["政治"]
        ),
        Teacher(
            id="T010",
            name="李物理",
            subjects=["物理"]
        ),
        Teacher(
            id="T011",
            name="张物理",
            subjects=["物理"]
        ),
        Teacher(
            id="T012",
            name="王语文",
            subjects=["语文"]
        )
    ]
    
    # 3. 创建教室
    classrooms = [
        Classroom(
            id="R101",
            name="A-101",
            floor=1,
            location="教学楼A",
            room_type="普通教室",
            capacity=60,
            is_special=False
        ),
        Classroom(
            id="R102",
            name="A-102",
            floor=1,
            location="教学楼A",
            room_type="普通教室",
            capacity=60,
            is_special=False
        ),
        Classroom(
            id="R103",
            name="A-103",
            floor=1,
            location="教学楼A",
            room_type="普通教室",
            capacity=60,
            is_special=False
        ),
        Classroom(
            id="S201",
            name="B-201",
            floor=2,
            location="教学楼B",
            room_type="理科教室",
            capacity=60,
            is_special=True
        ),
        Classroom(
            id="S202",
            name="B-202",
            floor=2,
            location="教学楼B",
            room_type="理科教室",
            capacity=60,
            is_special=True
        ),
        Classroom(
            id="S203",
            name="B-203",
            floor=2,
            location="教学楼B",
            room_type="理科教室",
            capacity=60,
            is_special=True
        ),
        Classroom(
            id="H301",
            name="C-301",
            floor=3,
            location="教学楼C",
            room_type="文科教室",
            capacity=60,
            is_special=True
        ),
        Classroom(
            id="H302",
            name="C-302",
            floor=3,
            location="教学楼C",
            room_type="文科教室",
            capacity=60,
            is_special=True
        ),
        Classroom(
            id="H303",
            name="C-303",
            floor=3,
            location="教学楼C",
            room_type="文科教室",
            capacity=60,
            is_special=True
        )
    ]
    
    # 4. 创建班级
    classes = [
        Class(
            grade="高一",
            name="高一(1)班",
            student_count=35,
            subjects=subjects  # 所有科目
        ),
        Class(
            grade="高一",
            name="高一(2)班",
            student_count=40,
            subjects=subjects  # 所有科目
        ),
        Class(
            grade="高一",
            name="高一(3)班",
            student_count=50,
            subjects=subjects  # 所有科目
        ),
        Class(
            grade="高一",
            name="高一(4)班",
            student_count=55,
            subjects=subjects  # 所有科目
        )
    ]
    
    # 创建排课服务
    scheduler_service = SchedulerService(config, rule_manager)
    
    # 生成课表
    result = scheduler_service.create_schedule(classes, teachers, classrooms)
    
    # 输出结果
    if result["success"]:
        print("课表生成成功！")
        print("\n=== 课表详情 ===")
        # 按班级分组显示
        schedule_by_class = {}
        for entry in result["schedule"]:
            class_name = entry["class"]
            if class_name not in schedule_by_class:
                schedule_by_class[class_name] = []
            schedule_by_class[class_name].append(entry)
        
        for class_name, entries in schedule_by_class.items():
            print(f"\n{class_name}的课表：")
            # 按星期分组
            for weekday in ['一', '二', '三', '四', '五']:
                print(f"星期{weekday}，", end='')
                # 获取该星期的所有课程并按节次排序
                day_entries = [e for e in entries if e["weekday"] == weekday]
                day_entries.sort(key=lambda x: x["period"])
                
                # 创建一个包含8节课的列表
                day_schedule = ['空课'] * 8
                for entry in day_entries:
                    period_idx = entry["period"] - 1
                    day_schedule[period_idx] = f"{entry['subject']}（{entry['teacher']}）在{entry['classroom']}"
                
                # 输出该天的课程安排
                print("第1节到第8节课分别是：", end='')
                print("、".join(day_schedule))
            print("~~~~")  # 每个班级之后添加分隔符
    else:
        print("课表生成失败：")
        for error in result["errors"]:
            print(f"- {error}")
