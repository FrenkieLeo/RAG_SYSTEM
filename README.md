# PDF 批量加密工具

这是一个面向 Windows 用户的桌面小工具，用于批量给某个文件夹里的 PDF 加密，并限制常见权限：

- 禁止打印
- 禁止复制/提取内容
- 禁止修改文档内容
- 禁止注释
- 禁止填写表单和签名
- 禁止插入、删除、旋转页面

最终产物可以打包成一个 `PdfBatchLocker.exe`，拷贝给其他 Windows 用户后可直接双击运行，不需要对方安装 Python 或其他环境。

## 使用方式

1. 双击打开 `PdfBatchLocker.exe`。
2. 选择包含 PDF 的输入文件夹。
3. 选择输出文件夹。默认建议输出到新的文件夹，避免覆盖原文件。
4. 如源 PDF 已经有打开密码，填写“源 PDF 密码”。
5. 如需要打开 PDF 时输入密码，勾选“设置打开密码”并填写两次。
6. 填写“权限密码”。权限密码用于日后解除打印、复制、注释、插入/删除页面等限制，请妥善保存。
7. 勾选需要禁止的操作，点击“开始加密”。

> 注意：PDF 权限限制依赖 PDF 阅读器执行。Adobe Acrobat、Edge 等主流阅读器通常会遵守这些限制，但不能阻止恶意工具或不遵守规范的软件绕过权限。

## 给别人直接使用

把构建后的单文件复制给对方即可：

```text
dist\PdfBatchLocker.exe
```

对方不需要安装 Python、pypdf 或任何依赖。

## 在 Windows 本地构建 exe

构建者电脑需要安装 Python 3.12 或更新版本。终端进入本项目目录后运行：

```bat
build_windows.bat
```

构建完成后，exe 位于：

```text
dist\PdfBatchLocker.exe
```

## 通过 GitHub Actions 构建

仓库包含 `.github/workflows/build-windows.yml`。推送分支后，或手动运行 `Build Windows executable` 工作流，会在 Windows 环境中：

1. 安装依赖
2. 运行测试
3. 使用 PyInstaller 打包
4. 上传 `PdfBatchLocker.exe` 构建产物

## 开发和测试

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements-dev.txt
python -m pytest
python -m pdf_batch_locker
```

Linux/macOS 下运行开发界面时，请使用对应平台的虚拟环境激活命令。
