from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum
from typing import Tuple
from datetime import time

# 星期枚举
class WeekDay(Enum):
    MONDAY = "星期一"
    TUESDAY = "星期二"
    WEDNESDAY = "星期三"
    THURSDAY = "星期四"
    FRIDAY = "星期五"
    SATURDAY = "星期六"
    SUNDAY = "星期日"

    @classmethod
    def get_weekdays(cls, end_day: str) -> List['WeekDay']:
        """根据结束日期获取工作日列表"""
        weekday_map = {
            "星期五": 5,
            "星期六": 6,
            "星期日": 7
        }
        end_index = weekday_map.get(end_day, 5)
        return list(WeekDay)[:end_index]

# 时间段枚举
class DayPart(Enum):
    MORNING = "上午"
    AFTERNOON = "下午"
    EVENING = "晚上"

# 年级枚举
class Grade(Enum):
    GRADE_1 = "小学一年级"
    GRADE_2 = "小学二年级"
    GRADE_3 = "小学三年级"
    GRADE_4 = "小学四年级"
    GRADE_5 = "小学五年级"
    GRADE_6 = "小学六年级"

# 优先级枚举
class Priority(Enum):
    HIGH = 3
    MEDIUM = 2
    LOW = 1

# 时间槽
@dataclass
class TimeSlot:
    weekday: WeekDay
    period: int  # 第几节课（1开始）
    day_part: DayPart

# 科目信息
@dataclass
class Subject:
    name: str
    weekly_hours: int  # 每周需要上几节
    priority: Priority = Priority.MEDIUM
    requires_consecutive_periods: bool = False  # 是否需要连堂
    max_periods_per_day: int = 2  # 每天最多几节

# 班级信息
@dataclass
class Class:
    id: str  # 唯一标识符，如 "1A" 表示一年级A班
    name: str  # 显示名称，如 "一年级一班"
    grade: Grade  # 年级
    subjects: List[Subject] = field(default_factory=list)

    @classmethod
    def create_grade_classes(cls, grade: Grade, class_count: int) -> List['Class']:
        """创建指定年级的班级列表"""
        classes = []
        for i in range(1, class_count + 1):
            class_id = f"{grade.name[2]}{i}"  # 如 "1A" 表示一年级一班
            class_name = f"{grade.value}{i}班"
            classes.append(cls(
                id=class_id,
                name=class_name,
                grade=grade
            ))
        return classes

# 教师信息
@dataclass
class Teacher:
    id: str  # 工号
    name: str
    subjects: List[str]  # 可教授的科目名称
    max_hours_per_day: int = 6  # 每天最多上课时数
    max_hours_per_week: int = 25  # 每周最多上课时数
    available_times: List[TimeSlot] = field(default_factory=list)

    def can_teach(self, subject: str) -> bool:
        return subject in self.subjects

    def is_available_at(self, time_slot: TimeSlot) -> bool:
        if not self.available_times:  # 如果没有指定可用时间，则默认都可用
            return True
        return any(
            at.weekday == time_slot.weekday and 
            at.period == time_slot.period 
            for at in self.available_times
        )

# 排课条目
@dataclass
class ScheduleEntry:
    class_info: Class
    subject: Subject
    teacher: Teacher
    time_slot: TimeSlot

# 课表集合
@dataclass
class Schedule:
    entries: List[ScheduleEntry] = field(default_factory=list)

    def add_entry(self, entry: ScheduleEntry) -> bool:
        if self.has_conflicts(entry):
            return False
        self.entries.append(entry)
        return True

    def has_conflicts(self, new_entry: ScheduleEntry) -> bool:
        for entry in self.entries:
            if entry.time_slot.weekday == new_entry.time_slot.weekday and \
               entry.time_slot.period == new_entry.time_slot.period:
                # 检查教师冲突
                if entry.teacher.id == new_entry.teacher.id:
                    return True
                # 检查班级冲突
                if entry.class_info.id == new_entry.class_info.id:
                    return True
        return False

    def get_class_schedule(self, class_id: str) -> List[ScheduleEntry]:
        return [e for e in self.entries if e.class_info.id == class_id]

    def get_teacher_schedule(self, teacher_id: str) -> List[ScheduleEntry]:
        return [e for e in self.entries if e.teacher.id == teacher_id]

# 时间表配置
@dataclass
class TimeTable:
    periods_per_morning: int = 4  # 上午课节数
    periods_per_afternoon: int = 4  # 下午课节数
    periods_per_evening: int = 0  # 晚上课节数

    def __post_init__(self):
        """初始化后的验证"""
        total_periods = self.periods_per_morning + self.periods_per_afternoon + self.periods_per_evening
        if total_periods != 8:
            raise ValueError(f"每天的总课程数必须为8节，当前为{total_periods}节")

    def get_day_part(self, period: int) -> DayPart:
        """获取指定节次属于哪个时间段"""
        if period <= self.periods_per_morning:
            return DayPart.MORNING
        elif period <= self.periods_per_morning + self.periods_per_afternoon:
            return DayPart.AFTERNOON
        else:
            return DayPart.EVENING

    def get_total_periods(self) -> int:
        """获取每天的总课节数"""
        return self.periods_per_morning + self.periods_per_afternoon + self.periods_per_evening

    def is_valid_period(self, period: int) -> bool:
        """检查课节数是否有效"""
        return 1 <= period <= self.get_total_periods()

    def get_period_range(self, day_part: DayPart) -> Tuple[int, int]:
        """获取指定时间段的课节范围"""
        if day_part == DayPart.MORNING:
            return (1, self.periods_per_morning)
        elif day_part == DayPart.AFTERNOON:
            start = self.periods_per_morning + 1
            end = start + self.periods_per_afternoon - 1
            return (start, end)
        else:
            start = self.periods_per_morning + self.periods_per_afternoon + 1
            end = start + self.periods_per_evening - 1
            return (start, end)

# 排课配置
@dataclass
class ScheduleConfig:
    name: str
    grade: Grade  # 年级
    weekdays: List[WeekDay]  # 工作日
    class_ids: List[str]  # 班级列表
    timetable: TimeTable
    allow_consecutive_same_subject: bool = True
    max_consecutive_same_subject: int = 2
    min_subject_interval: int = 1

    @classmethod
    def create_config(cls, 
                     name: str,
                     grade: str,
                     end_day: str,
                     morning_periods: int,
                     afternoon_periods: int,
                     evening_periods: int,
                     class_count: int) -> 'ScheduleConfig':
        """
        创建排课配置
        :param name: 配置名称
        :param grade: 年级名称（如 "小学一年级"）
        :param end_day: 结束日期（如 "星期五"）
        :param morning_periods: 上午课节数
        :param afternoon_periods: 下午课节数
        :param evening_periods: 晚上课节数
        :param class_count: 班级数量
        """
        grade_enum = Grade(grade)
        weekdays = WeekDay.get_weekdays(end_day)
        
        # 创建时间表配置，确保每天的课程数量正确
        total_periods = morning_periods + afternoon_periods + evening_periods
        if total_periods != 8:  # 确保每天总课程数为8节
            raise ValueError(f"每天的总课程数必须为8节，当前为{total_periods}节")
            
        timetable = TimeTable(
            periods_per_morning=morning_periods,
            periods_per_afternoon=afternoon_periods,
            periods_per_evening=evening_periods
        )
        
        # 生成班级ID列表
        class_ids = [f"{grade_enum.name[2]}{i}" for i in range(1, class_count + 1)]
        
        return cls(
            name=name,
            grade=grade_enum,
            weekdays=weekdays,
            class_ids=class_ids,
            timetable=timetable
        )

    def validate(self) -> List[str]:
        """验证配置是否有效"""
        errors = []
        
        # 检查课节数配置
        total_periods = (self.timetable.periods_per_morning + 
                        self.timetable.periods_per_afternoon + 
                        self.timetable.periods_per_evening)
        
        if total_periods != 8:  # 确保每天总课程数为8节
            errors.append(f"每天的总课程数必须为8节，当前为{total_periods}节")
        
        if self.timetable.periods_per_morning <= 0:
            errors.append("上午课节数必须大于0")
            
        if self.timetable.periods_per_afternoon <= 0:
            errors.append("下午课节数必须大于0")
        
        # 检查班级配置
        if not self.class_ids:
            errors.append("至少需要一个班级")
        
        # 检查工作日配置
        if not self.weekdays:
            errors.append("至少需要一个工作日")
        
        return errors
