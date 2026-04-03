# Fullstack 报告目录说明

更新时间: 2026-04-02

## 当前合规验收证据

- `fullstack_test_report_latest.md`
  - 当前最新的覆盖报告。
- `fullstack_test_report_20260402_183937.md`
  - 由 `scripts/run_fullstack_tests.ps1` 修复后实际执行生成的真实 PASS 报告。

## 已归档但已被新报告覆盖

- `fullstack_test_report_20260402_171121.md`
  - 基于当时已实际通过的命令结果汇总，结论有效。
  - 后续已被 `20260402_183937` 的一键执行 PASS 报告覆盖，验收优先引用最新报告。

## 历史或示例文件

- `fullstack_test_report_20260225_105559.md`
- `fullstack_test_report_20260225_125604.md`
- `fullstack_test_report_demo.md`

上述文件仅作为历史调试或示例输出保留，不作为本轮 `P5-1` 合规验收证据。

## 使用规则

1. 需要当前验收结论时，优先查看 `fullstack_test_report_latest.md`。
2. 需要固定时间点的归档证据时，引用最近一次真实 PASS 的时间戳报告。
3. 历史报告只能作为排障或过程痕迹，不得替代当前验收基线。
