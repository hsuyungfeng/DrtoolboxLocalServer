import json
import logging

logger = logging.getLogger(__name__)

class LineBeautifier:
    @staticmethod
    def format_text(text):
        """Adds professional emojis and cleans up markdown for LINE."""
        if not text: return ""
        
        # 1. Clean up excessive thinking tags or weird chars
        text = text.replace("<think>", "").replace("</think>", "").strip()
        
        # 2. Add bullet point emojis if they look like lists
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            trimmed = line.strip()
            if trimmed.startswith('- ') or trimmed.startswith('* '):
                formatted_lines.append("🔹 " + trimmed[2:])
            elif trimmed.startswith('1. ') or trimmed.startswith('2. ') or trimmed.startswith('3. '):
                formatted_lines.append("📍 " + trimmed)
            else:
                formatted_lines.append(line)
        
        return "\n".join(formatted_lines)

    @staticmethod
    def build_flex_bubbles(title, content, footer_text=None):
        """Splits long content into multiple professional Flex Message bubbles."""
        # LINE Flex text limit is around 2000 chars, but for UX we split at 1500
        max_chars = 1500
        chunks = [content[i:i+max_chars] for i in range(0, len(content), max_chars)]
        
        bubbles = []
        for i, chunk in enumerate(chunks):
            current_title = title if i == 0 else f"{title} (續)"
            bubble = {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": current_title,
                            "weight": "bold",
                            "size": "xl",
                            "color": "#1DB446"
                        }
                    ]
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": chunk,
                            "wrap": True,
                            "size": "md",
                            "color": "#333333"
                        }
                    ]
                }
            }
            if i == len(chunks) - 1 and footer_text:
                bubble["footer"] = {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": footer_text,
                            "size": "xs",
                            "color": "#AAAAAA",
                            "wrap": True
                        }
                    ]
                }
            bubbles.append(bubble)
            
        return bubbles

    @staticmethod
    def build_treatment_card(treatment_key):
        """Builds a high-conversion marketing card for specific treatments."""
        treatments = {
            "exosomes": {
                "title": "✨ 外泌體再生療法",
                "desc": "利用高純度外泌體啟動細胞修復，改善膚質、對抗衰老，讓肌膚煥發新生光澤。",
                "url": "https://www.facebook.com/wenxin22636645"
            },
            "pico": {
                "title": "⚡ 皮秒雷射精準除斑",
                "desc": "極速脈衝科技，精準粉碎黑色素，改善暗沉、斑點與毛孔問題，恢復期短效果顯著。",
                "url": "https://www.facebook.com/wenxin22636645"
            },
            "hydrafacial": {
                "title": "💧 水飛梭深度淨化",
                "desc": "非侵入性專利技術，三步驟清潔、吸取、注入營養，讓毛孔深呼吸，打造水嫩透亮肌。",
                "url": "https://www.facebook.com/wenxin22636645"
            }
        }
        
        info = treatments.get(treatment_key.lower())
        if not info: return None

        return {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "精選療程建議", "weight": "bold", "color": "#1DB446", "size": "sm"},
                    {"type": "text", "text": info['title'], "weight": "bold", "size": "xl", "margin": "md"},
                    {"type": "text", "text": info['desc'], "size": "sm", "color": "#666666", "wrap": True, "margin": "md"}
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#1DB446",
                        "action": {
                            "type": "uri",
                            "label": "📅 預約門診",
                            "uri": "https://line.me/ti/p/@181fvgic"
                        }
                    },
                    {
                        "type": "button",
                        "style": "link",
                        "action": {
                            "type": "uri",
                            "label": "🔎 瞭解更多細節",
                            "uri": info['url']
                        }
                    }
                ]
            }
        }

    @staticmethod
    def build_clinic_info_card():
        """Creates a specialized card for clinic address and contact."""
        return {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://lh3.googleusercontent.com/p/AF1QipN_v_X_X_X", 
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {"type": "text", "text": "緻妍外科診所", "weight": "bold", "size": "xl"},
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {"type": "text", "text": "地址", "color": "#aaaaaa", "size": "sm", "flex": 1},
                                    {"type": "text", "text": "台中市太平區新福路 208 號", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "spacing": "sm",
                                "contents": [
                                    {"type": "text", "text": "電話", "color": "#aaaaaa", "size": "sm", "flex": 1},
                                    {"type": "text", "text": "04-2395-0960", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
                                ]
                            }
                        ]
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {
                        "type": "button",
                        "style": "link",
                        "height": "sm",
                        "action": {
                            "type": "uri",
                            "label": "📍 地圖導航",
                            "uri": "https://www.google.com/maps/search/?api=1&query=緻妍外科診所"
                        }
                    },
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": "#1DB446",
                        "action": {
                            "type": "uri",
                            "label": "📞 預約門診",
                            "uri": "tel:0423950960"
                        }
                    }
                ]
            }
        }
