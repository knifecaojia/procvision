# 项目长期记忆 (MEMORY.md)

## 环境特征
- 仓库 `05ui-poc` 在 F: 盘 (NTFS)。本机同时运行 CodeBuddy(ZCode)、VS Code、opencode、codex 等多个编辑器/AI 工具，其 Git 文件监视器会抢占 `.git/*.lock` 句柄，导致 git 写索引/更新 HEAD 时稳定报 `Invalid argument` / `File exists`。

## git 远程推送认证
- remote `origin` 默认是 `https://github.com/knifecaojia/procvision.git`，但本环境 credential.helper=helper-selector 在无 TTY 时无法弹凭据，HTTPS push 会失败。
- 本机有 `~/.ssh/id_ed25519` 且已注册 GitHub，`ssh -T git@github.com` 免密可用 → 推送改用 SSH：`git@github.com:knifecaojia/procvision.git`。

## 可复用：git 锁争用绕过法（Windows + 多 IDE 监视器）
当 `git add/commit/reset` 报 `index.lock`/`HEAD.lock` 的 Invalid argument / File exists 时：
1. 先把 `GIT_INDEX_FILE` 指向仓库同盘(F:)、`.git` 之外的临时文件（如 `05ui-poc/.tmp_alt_index`）。
2. `rm -f .git/index.lock .git/HEAD.lock` 清死锁。
3. `git read-tree HEAD` 装入正确树 → `cp .tmp_alt_index .git/index` 同步回真实索引。
4. 绝不用 `/tmp`（C: 盘，临时索引文件会莫名消失）；用临时索引提交前务必先 `git read-tree HEAD`，否则会把 HEAD 文件全判为删除。

## 提交约定
- 提交信息用中文，遵循 `feat(scope): 描述` 风格（见 `1fbae58`）。
- agent 自身的 `.workbuddy/` 目录不纳入提交。
