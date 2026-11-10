# M-Team Keepalive

基于 [fjh1997/mteam-keepalive](https://github.com/fjh1997/mteam-keepalive) 的个人 Fork，上游为 [CangShui/mtlogin-py](https://github.com/CangShui/mtlogin-py)。每 6 小时通过 GitHub Actions 调用 M-Team 的 `updateLastBrowse`。

本 Fork 使用 GitHub 自带的失败邮件通知，不需要飞书配置或 Gmail 发信密码。

## 首次设置

1. 在本仓库 `Settings → Secrets and variables → Actions → New repository secret` 添加以下三个 Secrets，名称必须完全一致：

   | Secret | 内容 |
   | --- | --- |
   | `MT_USERNAME` | M-Team 用户名 |
   | `MT_PASSWORD` | M-Team 密码 |
   | `MT_TOTPSECRET` | 动态验证码的 Base32 长密钥，不是 6 位验证码 |

2. 到仓库 Actions 页面启用工作流。选择 **M-Team keepalive → Run workflow**，手动验证一次。
3. 在 GitHub 账号设置中添加并验证你的 Gmail，将它设为通知邮箱。在 [通知设置](https://github.com/settings/notifications) 的 **System → Actions** 开启 **Email** 和 **Only notify for failed workflows**，保存。确保关注此仓库。
4. 如 Fork 的定时任务处于停用状态，在 Actions 中由你本人重新启用。GitHub 会把定时任务通知发给创建该任务、修改 cron 或重新启用任务的用户；本 Fork 无法替你修改个人通知设置。

详细规则见 [Actions 邮件设置](https://docs.github.com/en/subscriptions-and-notifications/how-tos/managing-github-actions-notifications) 和 [定时工作流通知归属](https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs)。

## 执行与通知

测试失败邮件：到 Actions → M-Team keepalive → Run workflow，勾选
**Test failure email notification (skips real login)** 后运行。该次运行会故意失败，
跳过真实登录，GitHub 按个人设置发送失败提醒。请检查 Gmail 收件箱和垃圾邮件。
测试开关默认为关闭，定时任务正常保活不受影响。此测试验证失败通知链路，
不会制造真实账号登录失败；登录失败的退出码已由回归测试覆盖。

- UTC 0、6、12、18 点运行，也支持手动触发。调度可能延迟。
- 直接运行本仓库源码，无需先构建 Docker 镜像或登录 GHCR。
- 检查失败、登录失败和刷新失败会返回非零退出码，Actions 因此标记为失败，GitHub 再按你的个人通知设置发邮件。
- 不打印 HTTP 请求/响应头和正文，不在日志中输出密码、验证码或登录 Token；异常只输出类型。
- 不再提供飞书通知。
- 每次运行重新登录，临时数据库仅放在 runner 临时目录，结束时删除，不把登录 Token 上传到 cache/artifact。原版的云端 Token 缓存已移除，因此会增加登录频率。
- GitHub Actions 使用固定提交 SHA，三个直接 Python 依赖固定版本；间接依赖仍由 pip 解析。
- 公开仓库的定时任务可能因长期无活动被 GitHub 停用。没有启动的任务不会产生失败邮件，因此邮件不能检测所有漏跑情况。

公开 Fork 的代码可见；凭据必须只放在 Actions Secrets，禁止提交到仓库。公开 Fork 不能直接改成私有仓库。

## 本地测试

建议 Python 3.11 或更新版本：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python local_test.py
```

`local_test.py` 交互读取用户名、密码及 TOTP 密钥；不会保留密码或 TOTP 密钥。本地 Token 保存在 `.local-data/cookie.db`，不要分享或提交此文件。用 `python local_test.py --fresh` 验证重新登录。

真实账号保活仍需自行配置 Secrets 后验证。测试只模拟服务端返回值，不证明当前登录接口或站点风控一定兼容。
