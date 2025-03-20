import random
import math

# 课程与其对应的权重
courses = {
    "语文": 4,
    "数学": 4,
    "英语": 3,
    "体育": 2,
    "美术": 1,
    "音乐": 1,
    "科学": 1,
    "道德与法治": 1,
    "信息技术": 1
}

# 计算每种课程每周的课时数
total_weight = sum(courses.values())
total_classes_per_week = 40

# 每节课对应的课时数
course_hours_per_week = {
    course: math.ceil((weight / total_weight) * total_classes_per_week)
    for course, weight in courses.items()
}

# 生成课表
days_of_week = ['周一', '周二', '周三', '周四', '周五']
classes_per_day = 8
weeks = 20

# 存储所有周的课表
schedule = []

# 为每周安排课程
for week in range(1, weeks + 1):
    week_schedule = []

    if week <= 18:
        # 前18周课程相同，按照比例安排课时
        available_courses = list(courses.keys())

        for day in range(5):  # 每周5天
            day_schedule = []

            # 根据权重将课程安排到每天
            for course, hours in course_hours_per_week.items():
                day_schedule.extend([course] * hours)

            # 打乱顺序并截取8节课
            random.shuffle(day_schedule)
            week_schedule.append(day_schedule[:classes_per_day])

    elif week == 19:
        # 第19周，移除所有权重为1的课程
        available_courses = [course for course in courses if courses[course] != 1]

        for day in range(5):  # 每周5天
            day_schedule = []

            # 安排剩余课程
            for course, hours in course_hours_per_week.items():
                if course in available_courses:
                    day_schedule.extend([course] * hours)

            # 打乱顺序并截取8节课
            random.shuffle(day_schedule)
            week_schedule.append(day_schedule[:classes_per_day])

    elif week == 20:
        # 第20周，移除权重为1的课程和体育课
        available_courses = [course for course in courses if courses[course] != 1 and course != "体育"]

        for day in range(5):  # 每周5天
            day_schedule = []

            # 安排剩余课程
            for course, hours in course_hours_per_week.items():
                if course in available_courses:
                    day_schedule.extend([course] * hours)

            # 用自习课代替空余课时
            while len(day_schedule) < classes_per_day:
                day_schedule.append("自习课")

            # 打乱顺序并截取8节课
            random.shuffle(day_schedule)
            week_schedule.append(day_schedule[:classes_per_day])

    schedule.append(week_schedule)

# 打印课表
for week in range(weeks):
    print(f"----- 第{week + 1}周 -----")
    for day in range(5):
        print(f"{days_of_week[day]}: {', '.join(schedule[week][day])}")
    print("\n")
