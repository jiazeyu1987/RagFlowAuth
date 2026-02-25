# 一键前后端测试

## 命令
- PowerShell：`.\scripts\run_fullstack_tests.ps1`
- 批处理（双击可用）：`.\scripts\run_fullstack_tests.bat`

## 默认执行内容
- 后端：`python -m unittest discover -s backend/tests -p "test_*.py"`
- 前端：`cd fronted && npm run e2e:all`

## 报告输出
- 时间戳报告：`doc/test/reports/fullstack_test_report_YYYYMMDD_HHMMSS.md`
- 最新报告（覆盖）：`doc/test/reports/fullstack_test_report_latest.md`

## 可选参数
- 自定义后端命令：  
  `.\scripts\run_fullstack_tests.ps1 -BackendCommand "python -m unittest discover -s backend/tests -p \"test_*.py\""`
- 自定义前端命令：  
  `.\scripts\run_fullstack_tests.ps1 -FrontendCommand "npm run e2e"`
- 自定义报告文件：  
  `.\scripts\run_fullstack_tests.ps1 -OutputFile "doc/test/reports/my_report.md"`

