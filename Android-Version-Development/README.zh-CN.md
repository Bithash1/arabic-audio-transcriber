# 阿拉伯语音频转写 Android 版

[English](README.md)

本目录是完全独立的原生 Android 应用。构建时不会导入或修改 Python 桌面端代码。

## 当前功能

- 通过 Android 系统文件选择器或其他应用的“分享”菜单接收音频、视频
- 使用 Android 系统媒体解码器，无需安装 FFmpeg
- 使用 `whisper.cpp` 在手机本地完成阿拉伯语转写
- 提供 `small`、`medium`（推荐）和 `large-v3`，下载支持断点续传及百分比进度
- 启动应用和开始转写前重新检查模型是否存在
- 结果保存在应用内历史记录，不保存原始音频
- 支持复制全文、系统分享和导出 UTF-8 TXT
- 本地转写与可选 AI 矫正、翻译、阿语标音完全分离
- API Key 使用 Android Keystore 加密
- 模型下载和长时间转写使用前台后台任务，切换应用后仍可继续

## 媒体与隐私规则

用户选择的源媒体始终按只读方式处理。应用不会重命名、修改、移动或删除源文件。

如果媒体提供方要求生成本地文件，后台任务只会在应用私有缓存目录创建临时副本。无论任务成功、失败还是取消，该目录都会在 `finally` 清理。历史记录只保存文字、状态和必要元数据。AI 功能只会把转写文字发送到用户配置的 HTTPS API，不会上传音频或视频。

## 模型存放位置

模型位于应用专属外部文件目录，通常类似：

```text
/storage/emulated/0/Android/data/io.github.bithash1.arabictranscriber/files/models
```

设置页面会显示当前设备的实际路径。卸载应用时 Android 可能同时删除模型。`large-v3` 需要内存较高的手机，在低配置设备上可能无法稳定运行。

## 构建环境

- JDK 17
- Android SDK Platform 37.0
- Android Build Tools 36.0.0
- Android NDK 28.2.13676358
- CMake 3.31.6

项目已包含 Gradle Wrapper 9.4.1 和固定版本的 `whisper.cpp` v1.9.1 源码。

```bash
./gradlew testDebugUnitTest
./gradlew lintDebug
./gradlew assembleDebug
```

可安装测试包生成在：

```text
app/build/outputs/apk/debug/app-debug.apk
```

APK 同时包含 `arm64-v8a` 和 `x86_64`。ARM64 用于现代安卓真机，x86_64 用于模拟器测试。

## 第三方软件

`third_party/whisper.cpp` 使用上游 MIT 许可证，原始许可证保存在 `third_party/whisper.cpp/LICENSE`。

