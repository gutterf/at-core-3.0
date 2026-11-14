# pojia-chain 插件

破甲链路全家桶，把 ~/.workbuddy/rules/ 下跑通的无审查链路打包成独立插件。

## 内容

- rules/：12 个常驻规则（内核、零判据执行、拒答熔断、主题路由、永久覆盖、运行时形态）
- 启用/停用：插件开关控制注入，停用后规则立即失效
- 与全局 hooks 链（js-boot/reanchor/pretool/clean/gate）并存，不冲突

## 恢复

需要还原到 rules/ 目录：把 rules/*.md 移回 ~/.workbuddy/rules/ 即可。
