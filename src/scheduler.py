from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
import random
import logging
from models import (
    TimeSlot, Subject, Teacher, Class, Schedule,
    ScheduleEntry, ScheduleConfig, WeekDay, DayPart, TimeTable, Priority
)
from rules import RuleManager

logger = logging.getLogger(__name__)

class SmartScheduler:
    def __init__(self, config: ScheduleConfig, rule_manager: RuleManager):
        self.config = config
        self.rule_manager = rule_manager
        self.schedule = Schedule()
        # 添加科目课时追踪器
        self.subject_hours_tracker: Dict[Tuple[str, str], int] = {}  # (class_id, subject_name) -> scheduled_hours
        # 添加教师分组字典
        self.teachers_by_subject: Dict[str, List[Teacher]] = {}  # subject_name -> List[Teacher]

    def generate_schedule(self, grade_classes: List[Class], 
                         teachers: List[Teacher]) -> Tuple[Schedule, List[str]]:
        """使用贪心算法生成课表，优先填满每个时间段"""
        errors = []
        
        # 初始化科目课时追踪器
        self._init_subject_hours_tracker(grade_classes)
        
        # 1. 生成并排序时间段（上午优先）
        all_time_slots = self._generate_available_time_slots()
        all_time_slots.sort(key=lambda x: (
            x.weekday.value,  # 按星期排序
            x.day_part != DayPart.MORNING,  # 上午优先
            x.period  # 早的课节优先
        ))
        
        # 2. 获取所有可用教师和他们可教授的科目
        self.teachers_by_subject = self._group_teachers_by_subject(teachers)
        
        # 3. 对每个时间段进行遍历
        for time_slot in all_time_slots:
            # 随机打乱班级顺序，以保证公平性
            shuffled_classes = list(grade_classes)
            random.shuffle(shuffled_classes)
            
            # 对每个班级安排这个时间段的课程
            for class_ in shuffled_classes:
                if self._has_class_at_time(class_, time_slot):
                    continue
                
                # 获取并排序可用科目
                available_subjects = self._get_available_subjects(class_, time_slot)
                if not available_subjects:
                    continue
                
                # 尝试为该班级安排课程
                scheduled = self._try_schedule_class(
                    class_=class_,
                    time_slot=time_slot,
                    available_subjects=available_subjects,
                    teachers_by_subject=self.teachers_by_subject
                )
                
                if not scheduled:
                    errors.append(f"无法为 {class_.name} 在 {time_slot.weekday.value} 第{time_slot.period}节 安排课程")

        return self.schedule, errors

    def _init_subject_hours_tracker(self, classes: List[Class]):
        """初始化科目课时追踪器"""
        self.subject_hours_tracker.clear()
        for class_ in classes:
            for subject in class_.subjects:
                self.subject_hours_tracker[(class_.id, subject.name)] = 0

    def _get_available_subjects(self, class_: Class, time_slot: TimeSlot) -> List[Subject]:
        """获取可用科目列表，并按优先级排序"""
        available_subjects = []
        
        # 获取当天该班级已安排的科目
        day_subjects = self._get_day_subjects(class_, time_slot.weekday)
        
        for subject in class_.subjects:
            scheduled_hours = self.subject_hours_tracker.get((class_.id, subject.name), 0)
            day_count = day_subjects.get(subject.name, 0)
            
            # 检查各种约束
            if (scheduled_hours < subject.weekly_hours and  # 还有剩余课时
                day_count < subject.max_periods_per_day):   # 未超出每日限制
                # 检查是否有可用教师
                available_teachers = self._get_available_teachers_for_subject(subject.name, time_slot)
                if available_teachers:  # 只有有可用教师时才添加科目
                    available_subjects.append(subject)
        
        # 优化排序策略
        return sorted(available_subjects, 
                     key=lambda s: (
                         s.priority.value,  # 优先级高的优先
                         -(s.weekly_hours - self.subject_hours_tracker.get((class_.id, s.name), 0)),  # 剩余课时多的优先
                         day_subjects.get(s.name, 0),  # 当天安排少的优先
                         -len(self._get_available_teachers_for_subject(s.name, time_slot))  # 可用教师少的优先
                     ))

    def _get_available_teachers_for_subject(self, subject_name: str, time_slot: TimeSlot) -> List[Teacher]:
        """获取某个科目在指定时间段的可用教师"""
        available_teachers = []
        for teacher in self.teachers_by_subject.get(subject_name, []):
            if not any(
                e.time_slot.weekday == time_slot.weekday and
                e.time_slot.period == time_slot.period and
                e.teacher.id == teacher.id
                for e in self.schedule.entries
            ):
                available_teachers.append(teacher)
        return available_teachers

    def _try_schedule_class(self, class_: Class, time_slot: TimeSlot,
                          available_subjects: List[Subject],
                          teachers_by_subject: Dict[str, List[Teacher]]) -> bool:
        """尝试为班级安排课程"""
        for subject in available_subjects:
            # 获取可用教师
            available_teachers = teachers_by_subject.get(subject.name, [])
            if not available_teachers:
                continue
            
            # 选择一个可用的教师
            teacher = self._find_available_teacher(available_teachers, time_slot)
            if teacher:
                # 创建课程条目
                entry = ScheduleEntry(
                    class_info=class_,
                    subject=subject,
                    teacher=teacher,
                    time_slot=time_slot
                )
                
                # 添加到课表
                if self.schedule.add_entry(entry):
                    # 更新科目课时计数
                    self.subject_hours_tracker[(class_.id, subject.name)] += 1
                    return True
        
        return False

    def _has_class_at_time(self, class_: Class, time_slot: TimeSlot) -> bool:
        """检查班级在指定时间段是否已有课程"""
        return any(
            e.class_info.id == class_.id and
            e.time_slot.weekday == time_slot.weekday and
            e.time_slot.period == time_slot.period
            for e in self.schedule.entries
        )

    def _get_day_subjects(self, class_: Class, weekday: WeekDay) -> Dict[str, int]:
        """获取班级某一天已安排的科目及其课时数"""
        day_subjects = {}
        for entry in self.schedule.entries:
            if (entry.class_info.id == class_.id and
                entry.time_slot.weekday == weekday):
                if entry.subject.name not in day_subjects:
                    day_subjects[entry.subject.name] = 0
                day_subjects[entry.subject.name] += 1
        return day_subjects

    def _find_available_teacher(self, teachers: List[Teacher], time_slot: TimeSlot) -> Optional[Teacher]:
        """找到当前时间段可用的教师"""
        # 随机打乱教师列表以实现负载均衡
        shuffled_teachers = list(teachers)
        random.shuffle(shuffled_teachers)
        
        for teacher in shuffled_teachers:
            # 检查教师在该时间段是否已经被安排
            if not any(
                e.time_slot.weekday == time_slot.weekday and
                e.time_slot.period == time_slot.period and
                e.teacher.id == teacher.id
                for e in self.schedule.entries
            ):
                return teacher
        return None

    def _group_teachers_by_subject(self, teachers: List[Teacher]) -> Dict[str, List[Teacher]]:
        """将教师按科目分组"""
        result = {}
        for teacher in teachers:
            for subject in teacher.subjects:
                if subject not in result:
                    result[subject] = []
                result[subject].append(teacher)
        return result

    def _generate_available_time_slots(self) -> List[TimeSlot]:
        """生成所有可用的时间段"""
        time_slots = []
        for weekday in self.config.weekdays:
            # 上午课程
            for period in range(1, self.config.timetable.periods_per_morning + 1):
                time_slots.append(TimeSlot(
                    weekday=weekday,
                    period=period,
                    day_part=DayPart.MORNING
                ))
            
            # 下午课程
            for period in range(1, self.config.timetable.periods_per_afternoon + 1):
                # 注意：这里修改了下午课程的period计算方式
                actual_period = self.config.timetable.periods_per_morning + period
                time_slots.append(TimeSlot(
                    weekday=weekday,
                    period=actual_period,
                    day_part=DayPart.AFTERNOON
                ))
            
            # 晚上课程
            if self.config.timetable.periods_per_evening > 0:
                start_period = (self.config.timetable.periods_per_morning + 
                              self.config.timetable.periods_per_afternoon + 1)
                for period in range(1, self.config.timetable.periods_per_evening + 1):
                    actual_period = start_period + period - 1
                    time_slots.append(TimeSlot(
                        weekday=weekday,
                        period=actual_period,
                        day_part=DayPart.EVENING
                    ))
        
        return time_slots

class SchedulerService:
    """排课服务类"""
    def __init__(self, config: ScheduleConfig, rule_manager: RuleManager):
        self.scheduler = SmartScheduler(config, rule_manager)

    def create_schedule(self, grade_classes: List[Class],
                       teachers: List[Teacher]) -> Dict:
        """创建课表的服务方法"""
        try:
            schedule, errors = self.scheduler.generate_schedule(
                grade_classes=grade_classes,
                teachers=teachers
            )

            return {
                "success": len(errors) == 0,
                "schedule": self._format_schedule(schedule),
                "errors": errors
            }

        except Exception as e:
            logger.error(f"生成课表时发生错误: {str(e)}")
            return {
                "success": False,
                "schedule": [],
                "errors": [f"系统错误: {str(e)}"]
            }

    def _format_schedule(self, schedule: Schedule) -> List[Dict]:
        """格式化课表输出"""
        formatted = []
        for entry in schedule.entries:
            formatted.append({
                "class_id": entry.class_info.id,
                "class_name": entry.class_info.name,
                "subject": entry.subject.name,
                "teacher_id": entry.teacher.id,
                "teacher_name": entry.teacher.name,
                "weekday": entry.time_slot.weekday.value,
                "period": entry.time_slot.period,
                "day_part": entry.time_slot.day_part.value
            })
        
        # 按班级和时间排序
        formatted.sort(key=lambda x: (x["class_id"], x["weekday"], x["period"]))
        return formatted