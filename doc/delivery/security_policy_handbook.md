# 安全策略手册（内外网模式/分级/脱敏/拦截/模型准入）

更新时间：2026-03-14

## 1. 目标
确保数据外发链路可控、可审计、可回溯，满足以下安全能力：
- 内外网模式控制
- 最小化出网
- 敏感分级识别
- 自动脱敏
- 高敏拦截
- 国产模型白名单准入

## 2. 控制入口
- 配置查询：`GET /api/admin/security/egress/config`
- 配置更新：`PUT /api/admin/security/egress/config`
- 审计查询：`GET /api/admin/security/egress/audits`

## 3. 策略字段说明
- `mode`：`intranet` / `extranet`
- `minimal_egress_enabled`：最小化出网（限制目标主机）
- `sensitive_classification_enabled`：敏感分级识别开关
- `auto_desensitize_enabled`：自动脱敏开关
- `high_sensitive_block_enabled`：高敏内容拦截开关
- `domestic_model_whitelist_enabled`：国产模型白名单开关
- `domestic_model_allowlist`：允许模型列表
- `allowed_target_hosts`：允许目标主机列表
- `sensitivity_rules`：分级规则词典（low/medium/high）

## 4. 推荐策略基线
1. `mode=intranet` 作为默认。
2. 在 `extranet` 模式下，默认开启：
  - `minimal_egress_enabled=true`
  - `sensitive_classification_enabled=true`
  - `auto_desensitize_enabled=true`
  - `high_sensitive_block_enabled=true`
  - `domestic_model_whitelist_enabled=true`
3. 仅放行经过审批的目标主机与模型。

## 5. 审计与追踪
审计记录应至少包含：
- 决策结果：allow/block
- 命中策略与阻断原因
- 操作主体（用户/请求路径/操作）
- 目标主机、目标模型
- 时间戳

审计查询建议：
- 每日检查 block/allow 比例
- 每周抽查高敏拦截命中样本
- 发布后重点观察拦截率波动

## 6. 运行建议
- 先在审计模式验证规则，再逐步切换为强拦截。
- 高敏词典和白名单需版本化并留痕。
- 任何策略改动必须关联变更单并补充回滚方案。

