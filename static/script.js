document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('login-form');
    const loginContainer = document.getElementById('login-container');
    const navbar = document.getElementById('navbar');
    const createTimetableForm = document.getElementById('createTimetableForm');
    const mainContentArea = document.getElementById('main-content-area');

    // --- API 客户端配置 ---
    const apiClient = axios.create({
        baseURL: 'http://192.168.43.34:5000', // 后端 API 基础 URL
        timeout: 10000,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        },
        withCredentials: false
    });

    // 登录功能
    if (loginForm && loginContainer && navbar) {
        loginForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const loginErrorMsg = document.getElementById('login-error');

            if (loginErrorMsg) loginErrorMsg.textContent = '';

            // 基本校验
            if (!username || !password) {
                if (loginErrorMsg) loginErrorMsg.textContent = '请输入用户名和密码。';
                return;
            }

            // 登录请求
            try {
                const response = await apiClient.post('/login', { username, password });
                const data = response.data;
                if (data.success) {
                    console.log('登录成功:', data.message);
                    loginContainer.style.display = 'none';
                    navbar.style.display = 'block';
                    if (mainContentArea) mainContentArea.style.display = 'block';
                    showContent('create-timetable');
                } else {
                    if (loginErrorMsg) loginErrorMsg.textContent = data.message || '登录失败，请检查用户名或密码。';
                }
            } catch (error) {
                console.error('登录请求错误:', error);
                if (loginErrorMsg) {
                    loginErrorMsg.textContent = error.response?.data?.message || '登录请求失败，请检查网络连接。';
                }
            }
        });
    }

    // 注册功能
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const username = document.querySelector('input[name="username"]').value;
            const password = document.querySelector('input[name="password"]').value;
            const confirmPassword = document.querySelector('input[name="confirm_password"]').value;
            const registerErrorMsg = document.getElementById('register-error');

            if (registerErrorMsg) registerErrorMsg.textContent = '';

            if (!username || !password || !confirmPassword) {
                if (registerErrorMsg) registerErrorMsg.textContent = '请输入用户名和密码。';
                return;
            }

            if (password !== confirmPassword) {
                if (registerErrorMsg) registerErrorMsg.textContent = '两次密码输入不一致！';
                return;
            }

            // 注册请求
            try {
                const response = await apiClient.post('/register', { username, password });
                const data = response.data;
                if (data.success) {
                    alert('注册成功！');
                    window.location.href = "/login";
                } else {
                    if (registerErrorMsg) registerErrorMsg.textContent = data.message || '注册失败，请检查用户名或密码。';
                }
            } catch (error) {
                console.error('注册请求错误:', error);
                if (registerErrorMsg) {
                    registerErrorMsg.textContent = error.response?.data?.message || '注册请求失败，请检查网络连接。';
                }
            }
        });
    } else {
        console.error("未能找到注册表单，请检查 HTML id。");
    }

    // 导航功能
    function showContent(targetId) {
        document.querySelectorAll('.content').forEach(function (element) {
            element.style.display = 'none';
        });
        const targetElement = document.getElementById(targetId);
        if (targetElement) {
            targetElement.style.display = 'block';
        } else {
            console.warn(`无法找到 ID 为 ${targetId} 的内容区域。`);
        }
    }

    // 导航栏点击事件
    if (navbar) {
        navbar.addEventListener('click', function (e) {
            if (e.target.tagName === 'A') {
                const target = e.target.getAttribute('data-target');
                if (target) {
                    showContent(target);
                }
            }
        });
    }

    // 创建课表功能
    if (createTimetableForm) {
        createTimetableForm.addEventListener('submit', async function (e) {
            e.preventDefault();

            const timetableName = document.getElementById('timetable-name').value || "未命名课表";
            const classDaysInput = document.getElementById('上课周期').value;
            const morningPeriods = parseInt(document.getElementById('上午节次').value, 10) || 4;
            const afternoonPeriods = parseInt(document.getElementById('下午节次').value, 10) || 4;

            const weekdaysMap = {
                "5": ["monday", "tuesday", "wednesday", "thursday", "friday"],
                "6": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"],
                "7": ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
            };
            const weekdays = weekdaysMap[classDaysInput] || weekdaysMap["5"];

            const timetableConfig = {
                class_duration: 45,
                break_duration: 10,
                morning_start: "08:00:00",
                afternoon_start: "14:00:00",
                evening_start: null,
                periods_per_morning: morningPeriods,
                periods_per_afternoon: afternoonPeriods,
                periods_per_evening: 0
            };

            const scheduleConfig = {
                name: timetableName,
                weekdays: weekdays,
                timetable: timetableConfig,
                allow_split_class: false,
                allow_mixed_grade: false,
                max_consecutive_same_subject: 2,
                min_subject_interval: 1
            };

            const requestData = {
                schedule_config: scheduleConfig,
                classes: [{ id: "Class001", grade: "1", name: "Class A" }],
                teachers: [{ id: "Teacher001", name: "Mr. Smith" }],
                classrooms: [{ id: "Room001", name: "Room 101" }]
            };

            const submitButton = createTimetableForm.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = '正在生成课表...';
            }

            try {
                const response = await apiClient.post('/create_schedule', requestData);
                if (response.data.success) {
                    alert('课表生成成功！');
                } else {
                    alert('课表生成失败：' + response.data.errors.join("\n"));
                }
            } catch (error) {
                console.error('课表生成请求错误:', error);
                alert('课表生成失败，请稍后重试。');
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = '生成课表';
                }
            }
        });
    } else {
        console.error("无法获取 id 为 createTimetableForm 的元素，请检查 HTML 中的 id 是否正确。");
    }
});
