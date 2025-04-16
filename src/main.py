import os
from flask import Flask, jsonify, request, render_template  # 添加 render_template 用于渲染 HTML 页面
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import inspect
from datetime import time, timedelta
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict
import random
from flask_cors import CORS  # Import CORS

# ========= 从你的模块中导入必要的类 =========
from models import (
    TimeSlot as ModelTimeSlot, Teacher as ModelTeacher, Subject as ModelSubject,
    Class as ModelClass, Schedule as ModelSchedule,
    ScheduleEntry as ModelScheduleEntry, ScheduleConfig as ModelScheduleConfig,
    WeekDay as ModelWeekDay, DayPart as ModelDayPart, TimeTable as ModelTimeTable,
    Priority as ModelPriority
)
from rules import RuleManager, Rule, RuleType, RulePriority

# 指向模板文件夹下的 index.html 和 register.html
template_path_index = os.path.join('templates', 'index.html')
template_path_register = os.path.join('templates', 'register.html')
template_path_login = os.path.join('templates', 'login.html')
# 指向静态文件夹下的不同静态文件
static_script_path = os.path.join('static', 'script.js')
static_styles_path = os.path.join('static', 'styles.css')

app = Flask(__name__,
            template_folder='templates',  # 统一指定模板文件夹
            static_folder='static')  # 统一指定静态文件夹

# 配置 CORS
CORS(app,
     resources={r"/*": {"origins": "*"}},
     supports_credentials=True)

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:xld190329.@localhost/intellclass_system'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'your-very-secret-key-here'  # secret_key is still useful for session management if needed later, or JWT secrets

# 初始化数据库
db = SQLAlchemy(app)

# ========= 数据库模型定义 (保持不变) =========
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

# 初始化数据库表
def initialize_database():
    with app.app_context():
        inspector = inspect(db.engine)
        if not inspector.has_table('user'):
            db.create_all()
            print("数据库表创建成功")
        else:
            print("数据库表已存在")
initialize_database()

# ========= SmartScheduler 类定义 (保持不变) =========
class SmartScheduler:
    """
    智能排课调度器类。
    负责根据输入的班级、教师、教室信息和排课规则生成课表。
    """
    def __init__(self, config: ModelScheduleConfig, rule_manager: RuleManager):
        if not isinstance(config, ModelScheduleConfig):
            raise TypeError("config 必须是 ScheduleConfig 类型")
        if not isinstance(rule_manager, RuleManager):
            raise TypeError("rule_manager 必须是 RuleManager 类型")

        self.config = config
        self.rule_manager = rule_manager
        self.schedule = ModelSchedule(config=self.config)
        self.errors = []
        self.available_time_slots = self._generate_available_time_slots()

    def _generate_available_time_slots(self) -> List[ModelTimeSlot]:
        slots = []
        timetable = self.config.timetable
        total_periods = (timetable.periods_per_morning +
                         timetable.periods_per_afternoon +
                         timetable.periods_per_evening)

        for weekday in self.config.weekdays:
            for period in range(1, total_periods + 1):
                try:
                    start_str, end_str = timetable.get_period_time(period)
                    start_time = time.fromisoformat(start_str)
                    end_time = time.fromisoformat(end_str)
                    day_part = timetable.get_day_part(period)
                    slots.append(ModelTimeSlot(
                        weekday=weekday,
                        start_time=start_time,
                        end_time=end_time,
                        period_number=period,
                        day_part=day_part
                    ))
                except ValueError as e:
                    self.errors.append(f"生成时间段错误 (星期 {weekday.value}, 第 {period} 节): {e}")
        return slots

    def generate_schedule(self,
                          grade_classes: List[ModelClass],
                          teachers: List[ModelTeacher]) -> Tuple[Optional[ModelSchedule], List[str]]:
        self.schedule = ModelSchedule(config=self.config)
        self.errors = []

        if not grade_classes: self.errors.append("没有提供班级信息。"); return None, self.errors
        if not teachers: self.errors.append("没有提供教师信息。"); return None, self.errors

        teachers_dict = {t.id: t for t in teachers}

        tasks = []
        for cls in grade_classes:
            if not hasattr(cls, 'subjects') or not cls.subjects:
                self.errors.append(f"班级 '{cls.name}' 没有设置科目，已跳过。")
                continue
            for subject in cls.subjects:
                for _ in range(subject.weekly_hours):
                    tasks.append({'class': cls, 'subject': subject})

        random.shuffle(tasks)
        scheduled_count = 0
        for task in tasks:
            current_class = task['class']
            current_subject = task['subject']
            scheduled_this_task = False

            potential_teachers = [t for t in teachers if current_subject.name in t.subjects]
            if not potential_teachers:
                self.errors.append(f"科目 '{current_subject.name}' (班级: {current_class.name}) 没有找到合适的教师。")
                continue
            random.shuffle(potential_teachers)

            random.shuffle(self.available_time_slots)
            for time_slot in self.available_time_slots:
                if not current_subject.can_be_scheduled_at(time_slot): continue
                for teacher in potential_teachers:
                    if not teacher.is_available_at(time_slot): continue

                    potential_entry = ModelScheduleEntry(
                        class_info=current_class,
                        subject=current_subject,
                        teacher=teacher,
                        time_slot=time_slot
                    )
                    violations = self.rule_manager.check_all_rules(self.schedule, potential_entry)
                    if not violations:
                        if self.schedule.add_entry(potential_entry):
                            scheduled_this_task = True
                            scheduled_count += 1
                            break
                    if scheduled_this_task: break
                if scheduled_this_task: break

            if not scheduled_this_task:
                self.errors.append(f"无法为班级 '{current_class.name}' 的科目 '{current_subject.name}' 找到合适的时间/教师安排。")

        print(f"排课完成。总任务数: {len(tasks)}, 成功安排: {scheduled_count}")
        if scheduled_count < len(tasks):
            self.errors.append(f"警告：有 {len(tasks) - scheduled_count} 节课未能成功安排。")

        return self.schedule, self.errors


# ========= API 路由定义 =========
@app.route('/')
def home():
    return render_template('index.html')

# --- 用户认证 API ---
@app.route('/login', methods=['GET', 'POST', 'OPTIONS'])
def api_login():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "无效的请求数据"}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"success": False, "message": "缺少用户名或密码"}), 400

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            response = jsonify({
                "success": True,
                "message": "登录成功",
                "user": {"id": user.id, "username": user.username}
            })
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response
        else:
            return jsonify({"success": False, "message": "用户名或密码错误"}), 401

    except Exception as e:
        print(f"登录处理错误: {str(e)}")
        return jsonify({"success": False, "message": "服务器处理请求时出错"}), 500

@app.before_request
def log_request_info():
    print('Request Method:', request.method)
    print('Request URL:', request.url)
    print('Request Headers:', dict(request.headers))


# 注册路由
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html')  # 显示注册页面

    # 处理 POST 请求（注册表单提交）
    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return jsonify({"success": False, "message": "用户名或密码不能为空"}), 400

    # 检查用户是否已经存在
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({"success": False, "message": "用户名已存在"}), 409

    # 哈希密码并保存到数据库
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, password=hashed_password)

    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify({"success": True, "message": "注册成功"}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": "注册失败"}), 500

# --- 排课 API ---
@app.route('/create_schedule', methods=['POST'])
def create_schedule():
    data = request.json
    if not data:
        return jsonify({"success": False, "errors": ["无效的请求数据"]}), 400

    try:
        # 1. 解析时间函数保持不变
        def parse_time(time_str):
            if isinstance(time_str, str):
                time_part = time_str.split('T')[-1].split('+')[0].split('Z')[0]
                try: return time.fromisoformat(time_part)
                except ValueError: raise ValueError(f"无法解析的时间格式: '{time_str}' -> '{time_part}'")
            elif isinstance(time_str, time): return time_str
            raise TypeError(f"预期时间为字符串或 time 对象，收到: {type(time_str)}")

        # 2. 解析班级和科目数据
        classes = []
        for c_data in data.get('classes', []):
            subjects_in_class = []
            for s_data in c_data.get('subjects', []):
                allowed_parts = [ModelDayPart(dp) for dp in s_data.get('allowed_day_parts', ['morning', 'afternoon'])]
                s_data['allowed_day_parts'] = allowed_parts
                s_data['priority'] = ModelPriority[s_data.get('priority', 'MEDIUM').upper()]
                subjects_in_class.append(ModelSubject(**s_data))
            c_data['subjects'] = subjects_in_class
            classes.append(ModelClass(**c_data))

        # 3. 解析教师数据
        teachers = []
        for t_data in data.get('teachers', []):
            available_times = []
            for ts in t_data.get('available_times', []):
                try:
                    available_times.append(ModelTimeSlot(
                        weekday=ModelWeekDay(ts['weekday']),
                        start_time=parse_time(ts['start_time']),
                        end_time=parse_time(ts['end_time']),
                        period=ts['period'],
                        day_part=ModelDayPart(ts['day_part'])
                    ))
                except (KeyError, ValueError) as e:
                    raise ValueError(f"解析教师 {t_data.get('name', '未知')} 可用时间错误: {e}")
            t_data['available_times'] = available_times
            teachers.append(ModelTeacher(**t_data))

        # 4. 创建时间表配置
        timetable_data = data.get('timetable', {
            "class_duration": 40,  # 小学一般是40分钟
            "break_duration": 10,
            "morning_start": "08:00:00",
            "afternoon_start": "13:30:00",
            "periods_per_morning": 4,
            "periods_per_afternoon": 4,
            "periods_per_evening": 0
        })
        
        try:
            timetable_data['morning_start'] = parse_time(timetable_data['morning_start'])
            timetable_data['afternoon_start'] = parse_time(timetable_data['afternoon_start'])
            timetable = ModelTimeTable(**timetable_data)
        except (ValueError, TypeError) as e:
            raise ValueError(f"解析时间表配置错误: {e}")

        # 5. 创建排课配置
        schedule_config_data = data.get('schedule_config', {
            "name": "小学课表",
            "weekdays": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "allow_consecutive_same_subject": True,
            "max_consecutive_same_subject": 2,
            "min_subject_interval": 1
        })
        
        try:
            schedule_config_data['weekdays'] = [ModelWeekDay(wd) for wd in schedule_config_data['weekdays']]
            schedule_config_data['timetable'] = timetable
            schedule_config = ModelScheduleConfig(**schedule_config_data)
        except (ValueError, TypeError) as e:
            raise ValueError(f"解析排课配置错误: {e}")

        # 6. 创建规则管理器
        rule_manager = RuleManager()
        rule_manager.create_default_rules()

        # 7. 创建排课器并生成课表
        scheduler = SmartScheduler(config=schedule_config, rule_manager=rule_manager)
        schedule_result, errors = scheduler.generate_schedule(
            grade_classes=classes,
            teachers=teachers
        )

        # 8. 格式化结果
        formatted_schedule = []
        final_errors = list(errors)

        if schedule_result and schedule_result.entries:
            for entry in schedule_result.entries:
                formatted_entry = {
                    "class_id": entry.class_info.id,
                    "class_name": entry.class_info.name,
                    "subject": entry.subject.name,
                    "teacher_id": entry.teacher.id,
                    "teacher_name": entry.teacher.name,
                    "weekday": entry.time_slot.weekday.value,
                    "period": entry.time_slot.period,
                    "time": f"{entry.time_slot.start_time.strftime('%H:%M')}-{entry.time_slot.end_time.strftime('%H:%M')}"
                }
                formatted_schedule.append(formatted_entry)

            # 按班级和时间排序
            formatted_schedule.sort(key=lambda x: (x["class_id"], x["weekday"], x["period"]))

        return jsonify({
            "success": len(final_errors) == 0,
            "schedule": formatted_schedule,
            "errors": final_errors if final_errors else None
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "schedule": [],
            "errors": [f"服务器错误: {str(e)}"]
        }), 500

@app.errorhandler(405)
def method_not_allowed(e):
    return jsonify({
        "success": False,
        "message": "Method Not Allowed",
        "allowed_methods": e.valid_methods
    }), 405

# ========= 应用启动 (移除文件列表打印) =========
if __name__ == '__main__':
    print("=" * 50)
    print("启动 Flask API 服务器...")
    print("=" * 50)
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
    except Exception as e:
        print(f"启动失败: {str(e)}")

