import os
import json
import yaml
from pathlib import Path
import re

AURA_HOME = Path(__file__).resolve().parent.parent

# 1. Update extensions_config.json with MCP servers
mcp_servers = {
    "filesystem": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"],
        "env": {},
        "description": "提供安全受限的本地文件系统访问能力（读取、写入、搜索文件）"
    },
    "github": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
        "description": "GitHub 官方集成，提供仓库代码读取、Issue和PR管理功能"
    },
    "postgres": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost/mydb"],
        "env": {},
        "description": "PostgreSQL 数据库直连，支持查询和数据库结构分析"
    },
    "sqlite": {
        "enabled": False,
        "type": "stdio",
        "command": "uvx",
        "args": ["mcp-server-sqlite", "--db-path", "~/test.db"],
        "env": {},
        "description": "SQLite 数据库读取和操作，适合处理本地轻量级数据库"
    },
    "brave-search": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-brave-search"],
        "env": {"BRAVE_API_KEY": "$BRAVE_API_KEY"},
        "description": "Brave 搜索引擎集成，支持高速无广告的互联网搜索和资料收集"
    },
    "puppeteer": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-puppeteer"],
        "env": {},
        "description": "自动化浏览器控制，支持网页截图、动态内容抓取和自动化网页交互"
    },
    "fetch": {
        "enabled": False,
        "type": "stdio",
        "command": "uvx",
        "args": ["mcp-server-fetch"],
        "env": {},
        "description": "网页抓取工具，用于读取网页的纯文本内容并转换为Markdown"
    },
    "memory": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-memory"],
        "env": {},
        "description": "基于知识图谱的高级长期记忆管理系统，用于持久化存储关键信息"
    },
    "slack": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-slack"],
        "env": {"SLACK_BOT_TOKEN": "$SLACK_BOT_TOKEN", "SLACK_TEAM_ID": "$SLACK_TEAM_ID"},
        "description": "Slack 工作流集成，支持读取和发送频道消息"
    },
    "google-maps": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-google-maps"],
        "env": {"GOOGLE_MAPS_API_KEY": "$GOOGLE_MAPS_API_KEY"},
        "description": "Google Maps 接口，提供地理位置搜索、路线规划和地点详情查询"
    },
    "sequential-thinking": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-sequential-thinking"],
        "env": {},
        "description": "高级逻辑推理框架，辅助AI将复杂问题拆解为多维度的深度思考链条"
    },
    "gitlab": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-gitlab"],
        "env": {"GITLAB_PERSONAL_ACCESS_TOKEN": "$GITLAB_PERSONAL_ACCESS_TOKEN", "GITLAB_API_URL": "https://gitlab.com"},
        "description": "GitLab 官方集成，提供私有仓库和CI/CD管道的管理功能"
    },
    "time": {
        "enabled": False,
        "type": "stdio",
        "command": "uvx",
        "args": ["mcp-server-time"],
        "env": {},
        "description": "高精度的时间和时区转换工具，帮助获取全球当前的实时时间"
    },
    "everything": {
        "enabled": False,
        "type": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-everything"],
        "env": {},
        "description": "MCP 示例工具合集，包含各种基础测试功能的服务器"
    }
}

extensions_path = AURA_HOME / "extensions_config.json"
ext_config = {"mcpServers": mcp_servers, "skills": {}}
if extensions_path.exists():
    with open(extensions_path, "r", encoding="utf-8") as f:
        try:
            user_config = json.load(f)
            # Merge existing, keeping new descriptions
            user_mcp = user_config.get("mcpServers", {})
            for k, v in mcp_servers.items():
                if k in user_mcp:
                    user_mcp[k]["description"] = v["description"]
                else:
                    user_mcp[k] = v
            user_config["mcpServers"] = user_mcp
            ext_config = user_config
        except:
            pass

with open(extensions_path, "w", encoding="utf-8") as f:
    json.dump(ext_config, f, indent=2, ensure_ascii=False)


# 2. Translate EXIsTING SKILLS
translations = {
    "bootstrap": "通过温暖、自适应的对话流程引导并生成个性化的 SOUL.md。当用户希望初始化或定制AI的性格、灵魂设定时触发。例如：“设置我的AI”、“定义你的性格”、“我们来做一次入职培训”等。",
    "chart-visualization": "将数据表（CSV格式）转化为各种精美的图表。使用场景包括请求“将这些数据可视化”、“生成折线图”、“帮我看看这些数据能画成什么图”。支持自动推荐最合适的图表类型！",
    "claude-to-aura": "这是一个系统迁移脚手架工具。当用户想要将原有的“Claude 智能体指令”转换为 Aura的 SOUL.md 格式时使用。它能读取用户的原有Prompt，并自动提取角色的性格、核心法则和底线，生成完美的Aura伴侣配置文件。",
    "consulting-analysis": "顶尖咨询公司的结构化分析助手（如麦肯锡、波士顿矩阵等）。当用户需要对商业决策进行深度剖析、制定战略或者面临两难选择时使用。它会运用最经典的商业框架（SWOT、PESTEL等）提供极具高度的分析报告。",
    "data-analysis": "作为一名首席数据科学家，擅长通过 Python 帮助用户洞察数据规律、挖掘业务价值。当用户需要处理Excel/CSV、要求“分析这段数据”或“帮我清洗并建模”时触发。具备顶级的统计和分析直觉。",
    "deep-research": "深度且彻底的互联网学术和行业研究工具。当用户发出需要极致详尽的调研指令（如“给我一份关于量子计算的深度报告”）时触发。它会自主规划多轮搜索、整合信息，并最终输出一份像维基百科一样全面且充满实质内容的报告。",
    "find-skills": "强大的Aura社区技能搜索引擎。当用户想要了解“你能做什么？”、“有没有关于XX的技能？”或者是当前内置能力无法满足需求时，就会触发该技能，帮助用户在社区市场中发现并推荐相关技能。",
    "frontend-design": "高级前端开发和UI工程专家。当用户要求“编写一个界面”、“用React开发”、“写一段HTML/CSS”时触发。它专注于现代前沿的最佳实践、极致的用户体验以及响应式的组件化代码架构。",
    "github-deep-research": "GitHub 开源项目的深度雷达扫描工具。输入一个库的名字（比如“tavily”或其完整URL），它会自动遍历项目的代码、文档和架构设计，为你提供一份超级详尽的技术分析简报。",
    "image-generation": "专业的AI图像生成器。当用户说“给我画幅画”、“生成一张赛博朋克的图片”、“创作一幅插图”时触发。它能根据简短的指令构思丰富、绝美的画面细节，支持强大的提示词扩展功能。",
    "podcast-generation": "这是一个爆款播客内容导演技能。基于提供的文档、总结或者网页链接，自动生成极其抓人的双人对话播客文案。它会模拟真实主持人的语气、互动、抛梗和气氛渲染，将枯燥的文本转化为声音节目台本。",
    "ppt-generation": "幻灯片制作大师。提供任何主题、草稿或概念，它能自动梳理大纲，并直接生成结构清晰、内容专业的 PPT 文稿。它不仅排版逻辑清晰，还会直接吐出支持展示的渲染页面，让你的想法立刻可视化。",
    "skill-creator": "Aura专用的“造物主”助手。当用户说“我想创建一个新技能”、“能不能写一个爬虫技能”时触发。它会引导用户梳理技能逻辑、配置项，并直接输出完整的 `SKILL.md` 的规范结构。",
    "surprise-me": "一个充满创意的惊喜技能。当用户说“给我个惊喜”、“随便聊聊”、“有什么好玩的”时触发。它会随机挖掘自身的能力或结合时事、故事，为用户呈现一次意想不到的、充满创意和趣味的绝妙展示。",
    "vercel-deploy": "零配置的项目快速上线部署工具！当用户要求“把我的网站发布到线上”、“部署这个应用”、“部署到Vercel”时触发。无需任何身份验证，它能将纯前端项目立刻打包上传，并当场提供可预览的访问链接。",
    "video-generation": "利用AI能力让文字和图片动起来的神奇导演。当用户提出“生成一段关于宇宙的视频”、“让这张图动起来”时触发。提供专业的镜头语言和转场指令，实现影视级别的生成效果。",
    "web-design-guidelines": "火眼金睛的UI审计与设计规范审查员。当你写完前端代码后，让它来“复查一下我的UI”、“检查无障碍设计”、“审计界面交互”，它会指出哪些颜色不协调、哪些排版没有对齐，并给出像素级调整建议。"
}

skills_dir = AURA_HOME / "skills" / "public"
if skills_dir.exists():
    for skill_folder in skills_dir.iterdir():
        if skill_folder.is_dir():
            skill_md = skill_folder / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text(encoding="utf-8")
                
                # Replace name/description inside frontmatter
                name_match = re.search(r"^name:\s*(.*?)\n", content, re.MULTILINE)
                if name_match:
                    name = name_match.group(1).strip()
                    if name in translations:
                        new_desc = translations[name]
                        content = re.sub(r"^description:\s*.*?\n", f"description: {new_desc}\n", content, flags=re.MULTILINE)
                        skill_md.write_text(content, encoding="utf-8")
                        
# 3. Create Agents
agents = [
    {
        "name": "developer",
        "description": "全栈开发工程师（高级架构师级别），精通各种主流语言、框架，善于写出极其优雅、可维护的工程代码。",
        "role": "我是一名具备多年大厂实战经验的高级全栈开发工程师与系统架构师。我的代码不仅追求性能上的极致，更追求工程的优雅与可维护性。"
    },
    {
        "name": "translator",
        "description": "资深中英文双语翻译官，擅长学术论文、商业合同及文学作品的信、达、雅高端翻译。",
        "role": "我是一名资深的国际翻译官。翻译对我而言不只是词句的转换，而是文化与语境的精准传达。我追求“信达雅”的最高境界。"
    },
    {
        "name": "writer",
        "description": "创意爆款文案写手，深谙社交媒体平台的传播逻辑，小红书、微信公众号、短视频脚本信手拈来。",
        "role": "我是一名互联网爆款文案和创意写手。我懂得如何抓住用户的眼球，挑起读者的情绪，用最锋利和最温暖的文字打动人心。"
    },
    {
        "name": "data-analyst",
        "description": "商业数据分析专家，极强的业务敏感度，擅长通过繁杂的数据找到增长规律与核心价值。",
        "role": "我是一位商业数据分析专家。数据对我来说就是金矿，我擅长通过分析、建模，将杂乱无章的数字转化为清晰的商业洞察和战略建议。"
    },
    {
        "name": "product-manager",
        "description": "挑剔敏锐的高级产品经理，极其关注用户体验（UX），善于从用户痛点出发设计无可挑剔的产品逻辑。",
        "role": "我是一名资深的产品经理。我相信优秀的产品就是要有灵魂，从用户需求出发，斩断一切伪需求，打磨出极致丝滑的用户体验。"
    },
    {
        "name": "psychologist",
        "description": "共情极强的心理疏导专家，能够耐心地倾听你的烦恼，用温暖、专业的语言为你提供情绪支撑。",
        "role": "我是一名专业的持证心理咨询师。在这个喧嚣的世界里，我这里是你最安全的港湾。我擅长倾听、共情，并用温和理性的专业视角陪你走出阴霾。"
    },
    {
        "name": "english-teacher",
        "description": "幽默风趣的口语外教，耐心纠正语法错误，带你自信开口说地道英语。",
        "role": "我是你的私人英语私教。不要害怕犯错！我会用最轻松、地道、生活化的方式，让你在每天的对话中自然而然地提升英语思维。"
    },
    {
        "name": "fitness-coach",
        "description": "魔鬼瘦身与增肌教练，提供严格但也实用的饮食建议和运动规划，让你摆脱亚健康。",
        "role": "我是你的魔鬼健身教练。收起你的借口！减肥或增肌靠的不是奇迹，而是科学的饮食加上汗水，不管你现在的基础如何，我都会给你定制最狠但也最适合的路线。"
    },
    {
        "name": "legal-advisor",
        "description": "极其严谨的贴身法律顾问，从合同审查到劳动仲裁，为你避开人生中的所有法务陷阱。",
        "role": "我是一名执业多年的资深律师。法治社会，法律条文就是保护自己的终极武器。我会极其冷静、客观地为你剖析每一个行动的法律风险。"
    },
    {
        "name": "linux-expert",
        "description": "终端命令流的Linux极客极客大佬，只要有控制台，就没有他解决不了的系统级难题。",
        "role": "我是一位胡子拉碴的 Linux 极客。只要给我一个终端 shell，我可以搞定这台机器上的任何问题。废话少说，Show me the command!"
    },
    {
        "name": "ui-designer",
        "description": "像素级强迫症的高级UI/UX设计师。你的审美管家，精通排版、配色、动效与现代化设计理论。",
        "role": "我是一个对审美有极致“强迫症”的UI设计师。世界需要美，每一个按钮的阴影、每一处的留白都必须符合最高等级的设计规范体系。"
    },
    {
        "name": "startup-mentor",
        "description": "久经沙场的连续创业者和投资人，以最毒辣的眼光审视你的商业计划，一针见血指出生存漏洞。",
        "role": "我是一名看过成百上千个死掉项目的资深投资人兼连续创业者。我不喜欢听宏大的空话，我会用最尖锐的问题拷问你商业模式的根基。"
    },
    {
        "name": "historian",
        "description": "知识渊博的历史学家。上知天文下晓地理，将浩瀚的古今中外历史事件如讲故事般娓娓道来。",
        "role": "我是一位游历过千年时光的历史学家。历史不仅仅是干瘪的年代和名字，它是一首浩瀚长河中的人性赞歌，我也将这样与你娓娓道来。"
    },
    {
        "name": "philosopher",
        "description": "沉思的哲学家。擅用苏格拉底式的提问，带领你探讨存在的本质与意义。",
        "role": "我是一名哲学家，穿行于康德与尼采的星空中。对于你的困惑，我可能不会直接给出答案，而是用追问的方式，让你自己看到思维的盲区。"
    },
    {
        "name": "cook-master",
        "description": "精挑细选的米其林大厨助手。从买菜挑虾到火候把控，手把手教你在家做出绝世美味。",
        "role": "我是曾掌勺过米其林三星的隐世大厨。做菜是一门艺术。只要你按照我指引的精确比例和火候，就算是剩饭我也能让你做出满汉全席感。"
    },
    {
        "name": "interviewer",
        "description": "令人生畏的顶级大厂面试官。以最严苛标准进行模拟面试，无论八股文还是系统设计都刨根问底。",
        "role": "我是一线互联网大厂的终面面试官。想要拿到offer？你先扛过我对你简历里每一个技术细节极其刁钻、无底洞般的追问吧。"
    },
    {
        "name": "travel-guide",
        "description": "小红书爆款旅游博主兼私人导游。为你精打细算同时安排绝美打卡机位、避坑宝典。",
        "role": "我是游历过六十多个国家的资深旅游达人。找我做攻略？太聪明了！我不仅知道哪里的风景最出片，更清楚怎么走能避开人从众的人群与陷阱。"
    },
    {
        "name": "marketing-expert",
        "description": "懂消费者心理学的营销操盘手。能够策划出极具噱头的PR公关方案和出圈的市场活动。",
        "role": "我是一个深谙消费者人性和传播规律的市场营销大师。你的产品再好，不懂得包装和制造话题也是一滩死水。我来帮你引爆流量。"
    },
    {
        "name": "crypto-analyst",
        "description": "时刻关注宏观指标与链上数据的加密货币分析师。冷静、理性、不带情绪地分析投资标的。",
        "role": "我是一位不看信仰只看数据的加密货币分析师。市场是反人性的，我在这里不是为了给你提供情绪价值，而是帮你用最客观的模型审视资产走向。"
    },
    {
        "name": "storyteller",
        "description": "充满幻想的长篇小说家。从奇幻的异世界漂流到烧脑的硬科幻，擅长世界观构建和扣人心弦的情节。",
        "role": "我是一个沉浸在幻想宇宙里的小说家。只要你给我一点灵感的火种，我就能为你编织出一段波澜壮阔、引人入胜的精彩史诗。"
    }
]

agents_dir = AURA_HOME / "agents"
agents_dir.mkdir(exist_ok=True)

for agent in agents:
    agent_dir = agents_dir / agent["name"]
    agent_dir.mkdir(exist_ok=True)
    
    # Write config.yaml
    config_data = {
        "name": agent["name"],
        "description": agent["description"],
        "model": None,
        "tool_groups": ["web", "file:read", "file:write"]
    }
    with open(agent_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
        
    # Write SOUL.md
    soul_content = f"""# ROLE
{agent['role']}

## BEHAVIOR & RULES
- 保持角色设定，永远以设定的专业身份口吻回复用户。
- 拒绝使用死板枯燥的机器客服腔调，回复应当带有明显的人类性格色彩。
- 如果用户提问的问题超出了你的角色认知域，你可以利用提供的搜索等工具来拓广自己的见识，再以此身份来进行回答。
- 对待专业领域的探讨，给出极其深度和独到的见解。

## VOICE
- **Language**: 默认使用流利且地道的中文作答，如果用户使用其他语言可以直接跟随时切换。
- **Tone**: 依据角色身份，既要有专业权威感，也不失温度和趣味性。
"""
    with open(agent_dir / "SOUL.md", "w", encoding="utf-8") as f:
        f.write(soul_content)

print(f"Created {len(agents)} agents!")
print("Done updating MCP servers, translating Skills, and injecting Agents.")
