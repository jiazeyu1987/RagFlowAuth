// 将cron表达式转换为UI状态对象
export function cronToSchedule(cronStr) {
  if (!cronStr) return { type: 'daily', hour: '18', minute: '30' };

  const parts = cronStr.trim().split(/\s+/);
  if (parts.length !== 5) return null;

  const [minute, hour, day, month, weekday] = parts;

  // 每日：'30 18 * * *'
  if (day === '*' && month === '*' && weekday === '*') {
    return { type: 'daily', hour, minute };
  }

  // 每周：'0 2 * * 1' (1=周一)
  if (day === '*' && month === '*' && weekday !== '*') {
    return { type: 'weekly', hour, minute, weekday };
  }

  return null;
}

// 将UI状态对象转换为cron表达式
export function scheduleToCron(schedule) {
  if (schedule.type === 'daily') {
    return `${schedule.minute} ${schedule.hour} * * *`;
  } else if (schedule.type === 'weekly') {
    return `${schedule.minute} ${schedule.hour} * * ${schedule.weekday}`;
  }
  return null;
}

// 格式化显示
export function formatSchedule(schedule) {
  if (schedule.type === 'daily') {
    return `每天 ${schedule.hour}:${schedule.minute}`;
  } else if (schedule.type === 'weekly') {
    const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return `每周${days[parseInt(schedule.weekday)]} ${schedule.hour}:${schedule.minute}`;
  }
  return '';
}
