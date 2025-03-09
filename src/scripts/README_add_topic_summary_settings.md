# 话题总结设置脚本使用说明

`add_topic_summary_settings.py` 是一个用于在数据库的settings表中添加或更新topic_summary设置的脚本。这个设置包含了话题总结功能所需的配置信息，如时间间隔、分组和需要识别的话题列表。

## 功能介绍

1. 检查数据库中是否已存在topic_summary设置
2. 如果存在，则更新设置值
3. 如果不存在，则创建新的设置
4. 支持通过命令行参数自定义设置内容

## 设置内容

topic_summary设置包含以下字段：

- `interval`: 时间间隔，格式为"{value} {unit}"，例如"30 minutes"，支持的单位有: seconds, minutes, hours
- `group`: 对应的微博账号分组名称
- `topics`: 需要识别的话题列表

这些字段会被序列化为JSON格式存储在settings表的value字段中。

## 使用方法

### 基本用法

```bash
python add_topic_summary_settings.py
```

这将使用默认值创建或更新topic_summary设置：
- 时间间隔：24 hours（24小时）
- 分组：default
- 话题：["日本新番制作发表", "日本歌手中国演唱会消息"]

### 自定义设置

```bash
python add_topic_summary_settings.py --interval "30 minutes" --group 娱乐 --topics "新电影上映,明星活动" --description "娱乐分组的话题总结设置"
```

参数说明：
- `--interval`: 时间间隔，格式为"{value} {unit}"，例如"30 minutes"，支持的单位有: seconds, minutes, hours
- `--group`: 对应的分组名称
- `--topics`: 需要识别的话题，可以是JSON格式的数组或逗号分隔的字符串
- `--description`: 设置描述（可选）

### 时间间隔格式

时间间隔支持三种时间单位：

1. 秒（seconds）：
```bash
python add_topic_summary_settings.py --interval "3600 seconds"
```

2. 分钟（minutes）：
```bash
python add_topic_summary_settings.py --interval "30 minutes"
```

3. 小时（hours）：
```bash
python add_topic_summary_settings.py --interval "24 hours"
```

### 话题格式

话题可以通过两种方式提供：

1. JSON数组格式：
```bash
python add_topic_summary_settings.py --topics '["话题1", "话题2", "话题3"]'
```

2. 逗号分隔的字符串：
```bash
python add_topic_summary_settings.py --topics "话题1,话题2,话题3"
```

## 注意事项

1. 脚本需要在项目根目录下运行，或者确保Python路径正确设置
2. 如果topic_summary设置已存在，脚本会更新现有设置而不是创建新设置
3. 设置成功添加或更新后，会在控制台显示设置内容
4. 如果设置失败，请查看日志文件了解详细错误信息
5. 时间间隔必须是有效的格式，值必须是正整数，单位必须是seconds、minutes或hours之一

## 与话题总结脚本配合使用

这个设置脚本与话题总结脚本（topic_summary.py）配合使用：

1. 首先使用本脚本设置话题总结的配置：
```bash
python add_topic_summary_settings.py --interval "12 hours" --group 娱乐 --topics "新电影上映,明星活动"
```

2. 然后可以在定时任务中使用这些设置执行话题总结：
```bash
python topic_summary.py --use-settings
```

这样，话题总结脚本就会从数据库中读取设置，并按照设置的内容执行话题总结。 