# worker-03 Independence Validation

## 结论

**判定：部分独立。**

通知能力已经形成独立后端模块边界：它有自己的 `NotificationStore`、`NotificationManager`、渠道适配器和专用路由，前后端也已经通过专用 API 访问。
但它还不是完全独立模块，因为审批链路和操作审批链路都直接依赖通知管理器来发消息，前端入口也被主应用和侧边栏直接挂载。

## 依赖图

- `backend/services/notification/` 负责通知领域核心能力：存储、渠道、投递、收件箱。
- `backend/app/dependencies.py` 在应用依赖里直接创建并注入 `notification_manager`，同时把它传给 `approval_workflow_service` 和 `operation_approval_service`。
- `backend/services/approval/service.py` 在审批流里调用通知管理器做待审提醒和结果通知。
- `backend/services/operation_approval/service.py` 在操作审批流里调用通知服务和 inbox 服务。
- `backend/app/modules/admin_notifications/router.py` 暴露管理员通知配置/任务接口。
- `backend/app/modules/me/router.py` 暴露个人消息收件箱接口。
- `fronted/src/features/notification/api.js`、`fronted/src/pages/NotificationSettings.js`、`fronted/src/pages/Messages.js`、`fronted/src/App.js`、`fronted/src/components/Layout.js` 将通知能力接入前端路由与导航。

## 耦合点清单

- 运行时依赖共享模型：`approval_workflow_service` 和 `operation_approval_service` 都持有 `notification_manager` / `notification_service`。
- 跨模块调用存在：审批成功/待审/最终结果都会触发通知发送。
- 收件箱能力共享同一通知存储：`/me/messages` 读取的是 `NotificationStore` 中的 `in_app` job。
- 前端并未独立成单独壳层：`App.js` 直接注册页面，`Layout.js` 直接加导航入口。
- 依赖不存在时会失败快：路由层在 `notification_manager` 为空时直接返回 500，不做兜底。

## 证据

- `backend/services/notification/service.py:24,83,290,389,408,446` 表明通知服务自身封装了渠道、投递、收件箱与重试逻辑。
- `backend/services/notification/store.py:21,29,127,236,461,537,579` 表明通知能力有独立表结构和持久化操作。
- `backend/app/dependencies.py:122-180` 表明应用启动时把通知能力注入到审批和操作审批服务中。
- `backend/services/approval/service.py:27,218,234,283,292,317,377,404,431` 表明审批链路直接调用通知管理器。
- `backend/services/operation_approval/service.py:47,55,753,767,780,800,820,832` 表明操作审批链路也直接调用通知与 inbox。
- `backend/app/modules/admin_notifications/router.py:22-98` 和 `backend/app/modules/me/router.py:20-132` 表明通知路由已独立暴露。
- `fronted/src/features/notification/api.js:3-42`、`fronted/src/App.js:18,20,299,319`、`fronted/src/components/Layout.js:26,27,105,112` 表明前端已把通知能力作为独立功能入口接入。

## 最小解耦建议

1. 保持通知模块为独立领域包，继续只通过 `NotificationManager` 暴露能力，不直接让其他服务访问底层 store。
2. 把审批链路对通知的调用收敛到事件发布接口或专门的通知编排层，减少审批业务对通知实现细节的直接依赖。
3. 前端保持独立页面和 API 封装，但入口注册可以继续挂在主壳层，不必拆出新壳层。

## 备注

- 本次仅做验证与结论输出，没有修改业务代码。
- 未发现阻塞项。
