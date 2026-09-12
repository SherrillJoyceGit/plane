# TC Plane 定制开发文档

本目录记录 TC Plane 相对上游 Plane 的定制功能、发布约定和本机开发信息。通用产品介绍和社区贡献说明仍以仓库根目录的文档为准。

## 导航

- [路线图](roadmap.md)：尚未完成的定制功能。
- [功能归档](features-archive.md)：已经交付的定制功能。
- [版本与分支管理](versioning.md)：版本分支、发布标签和发布流程。
- [本机 Development](local-development.md)：当前 macOS 开发机的运行、重载和排错方式。
- [系统概览](architecture/system-overview.md)：应用、后端、共享包和部署配置的边界。
- [术语约定](glossary.md)：与上游不同或容易混淆的产品术语。
- [前端 Lint](linting.md)：前端工作区的 lint 命令和规则。

## 维护规则

- 代码改变上述稳定事实时，在同一提交中更新对应文档。
- 路线图只记录未完成的功能；完成后保留功能编号并移入功能归档。
- 功能编号从 `F-0001` 起连续分配，已使用的编号不复用。
- 使用相对链接，链接目标移动时在同一变更中修复引用。

日常开发、检查和测试入口参见仓库根目录的 [AGENTS.md](../AGENTS.md)、[README.md](../README.md) 以及各应用的 README 和测试文档。
