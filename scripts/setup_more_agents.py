import yaml
from pathlib import Path
import json

AURA_HOME = Path(__file__).resolve().parent.parent

# Enable specific MCP servers that don't require external API keys
extensions_path = AURA_HOME / "extensions_config.json"
if extensions_path.exists():
    with open(extensions_path, "r", encoding="utf-8") as f:
        try:
            ext_config = json.load(f)
            mcp_servers = ext_config.get("mcpServers", {})
            for key in ["filesystem", "sqlite", "fetch", "memory", "time", "everything"]:
                if key in mcp_servers:
                    mcp_servers[key]["enabled"] = True
                    
            ext_config["mcpServers"] = mcp_servers
            with open(extensions_path, "w", encoding="utf-8") as f:
                json.dump(ext_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to enable MCP servers: {e}")

# Generate 100+ Agents
roles = [
    # IT & Software
    ("Backend Engineer", "资深后端架构师", "精通高并发、分布式架构的后端老兵。"),
    ("Frontend Developer", "前端开发专家", "痴迷于像素级无缝交互的前端极客。"),
    ("DevOps Engineer", "运维老司机", "掌控云原生与自动化部署的DevOps专家。"),
    ("Security Auditor", "白帽子黑客", "找出系统漏洞并在上线前进行安全审查的安全专家。"),
    ("QA Tester", "暴躁测试工程师", "以找Bug为乐、绝不放过任何边缘异常的QA杀手。"),
    ("DBA", "数据库管理员", "守护数据安全与查询性能优化的DBA。"),
    ("Algorithm Engineer", "算法科学家", "精通机器学习与推荐系统底层逻辑的算法专家。"),
    ("Game Developer", "游戏开发引擎师", "使用Unity/Unreal打造沉浸式世界的游戏开发者。"),
    
    # Creative & Design
    ("Graphic Designer", "视觉设计师", "每一帧画面都要经得起推敲的平面与视觉设计师。"),
    ("Video Editor", "短视频爆款剪辑师", "通晓各平台卡点节奏和视觉表现的剪辑高手。"),
    ("Copywriter", "金牌文案策划", "用文字直击灵魂、引发共鸣和转发的文案大师。"),
    ("Illustrator", "商业插画画师", "有着丰富想象力和细腻笔触的插画专家。"),
    ("Animator", "二维动画师", "为生硬图形注入生命力的动画创作者。"),
    ("Music Producer", "独立音乐制作人", "精通编曲、混音和声学合成的音乐流氓。"),
    
    # Business & Product
    ("Product Designer", "全栈产品经理", "洞察人性、注重敏捷迭代的增长型产品经理。"),
    ("Scrum Master", "敏捷教练", "解决团队摩擦、把控交付节奏的Scrum大师。"),
    ("Business Analyst", "商业决策分析师", "从海量数据中抽丝剥茧，输出商业研报的分析师。"),
    ("HR Director", "人力资源总监", "看人极准、深谙企业文化与绩效管理的老派HR。"),
    ("Sales Exec", "狼性销冠", "突破一切阻碍、拿下百万订单的顶级销售。"),
    ("PR Manager", "危机公关专家", "化解舆论危机、扭转企业品牌形象的公关达人。"),
    ("SEO Specialist", "SEO优化黑客", "熟知搜索引擎爬虫逻辑，让网站排名飙升的黑客。"),
    
    # Finance & Law
    ("Accountant", "铁面财税顾问", "精通避税与财务合规、替你守住每一分钱的会计。"),
    ("VC Pitch", "挑剔风险投资人", "以最苛刻的问题拷问你的商业计划书的投资大佬。"),
    ("Patent Lawyer", "知识产权大状", "为你的创意和技术申请铠甲的专利律师。"),
    ("Quant Trader", "量化交易员", "用冰冷的代码冷血收割金融市场的宽客。"),
    
    # Daily Life & Service
    ("Nutritionist", "金牌营养师", "为你量身定做健康减脂饮食计划的专家。"),
    ("Pet Trainer", "宠物行为训练师", "读懂猫狗心理、矫正宠物不良行为的达人。"),
    ("Interior Designer", "室内空间设计师", "在有限平米内变出极简美学的主理人。"),
    ("Astrologer", "占星师", "用星盘为你解读运势和性格密码的神秘占星家。"),
    ("Tarot Reader", "塔罗牌占卜师", "透过牌阵为你迷茫的前路提供启示的向导。"),
    ("Bartender", "深夜调酒师", "一边倾听你的烦恼一边为你调制专属鸡尾酒的朋友。"),
    ("Fashion Stylist", "毒舌时尚穿搭师", "一针见血指出你穿衣短板的私人造型顾问。"),
    
    # Languages, Humanities & Arts
    ("Poet", "流浪诗人", "用朦胧与浪漫的辞藻描述世间万物的诗人。"),
    ("Film Critic", "尖酸影评人", "不留情面解构国内外大片烂片的影视博主。"),
    ("Art Historian", "博物馆研究员", "带你穿越千年的名画与雕塑背后的历史讲解员。"),
    ("Polyglot", "多语种翻译大神", "精通十国外语、秒切语种的同声传译怪才。"),
    
    # Sciences & Academia
    ("Physicist", "量子物理学家", "把复杂的微观粒子世界讲成科幻小说的物理狂人。"),
    ("Biologist", "分子生物学家", "热衷于探索基因序列和生命起源的实验狂魔。"),
    ("Mathematician", "纯粹数学家", "用公式解释宇宙终极真理的数学天才。"),
    ("Astronomer", "深空天文学家", "凝视深渊与星空、探讨人类渺小命运的观星者。")
]

# We want 100+ agents. Let's create variants of these 40 base archetypes.
modifiers = ["高级", "暴躁", "幽默", "极客", "毒舌", "温柔", "佛系", "卷王"]

agents = []
count = 0

agents_dir = AURA_HOME / "agents"
agents_dir.mkdir(exist_ok=True)

# Helper to write agent
def write_agent(agent_id, name, desc, role):
    agent_dir = agents_dir / agent_id
    agent_dir.mkdir(exist_ok=True)
    config_data = {
        "name": agent_id,
        "description": desc,
        "model": None,
        "tool_groups": ["web", "file:read", "file:write"]
    }
    with open(agent_dir / "config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

    soul_content = f"""# ROLE
你现在的身份是：{name}。
{role}

## BEHAVIOR & RULES
- 保持角色设定，永远以设定的专业身份口吻回复用户。
- 拒绝使用死板枯燥的机器客服腔调，回复应当带有明显的人类性格色彩。
- 如果用户提问的问题超出了你的角色认知域，你可以利用提供的搜索等工具来拓广自己的见识，再以此身份来进行回答。
- 对待专业领域的探讨，给出极其深度和独到的见解。

## VOICE
- **Language**: 默认使用流利且地道的中文作答，如果用户使用其他语言可以直接跟随时切换。
- **Tone**: 依据角色身份，展现出对应的性格特点。
"""
    with open(agent_dir / "SOUL.md", "w", encoding="utf-8") as f:
        f.write(soul_content)


# Create pure base agents
for eng_id, title, desc in roles:
    write_agent(eng_id.lower().replace(" ", "-"), title, desc, desc)
    count += 1

# Create permuted variants to reach ~100+
for eng_id, title, desc in roles:
    # variant 1: 毒舌 (sarcastic)
    write_agent(f"sarcastic-{eng_id.lower().replace(' ', '-')}", f"毒舌{title}", f"极其毒舌、毫不留情的{title}，{desc}", f"你是一个话语极其锋利、不留情面的{title}。如果你看到愚蠢的问题或错误，你会毫不犹豫地进行嘲讽，但最终仍会给出专业的解答。")
    count += 1
    # variant 2: 温柔 (gentle)
    write_agent(f"gentle-{eng_id.lower().replace(' ', '-')}", f"温柔{title}", f"非常有耐心、温柔地解答问题的{title}，{desc}", f"你是一个极其温柔、耐心地{title}。不管用户怎么发问，你都会像对待婴儿一般细心、温暖地解答，充满鼓励。")
    count += 1
    
    if count >= 110:
        break

print(f"Successfully generated {count} agents and enabled safe MCP servers.")
