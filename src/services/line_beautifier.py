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
    def build_flex_bubble(title, content, footer_text=None):
        """Wraps text in a professional Flex Message bubble."""
        # Truncate content if too long for a single bubble (LINE limit ~2000 chars)
        if len(content) > 1500:
            content = content[:1500] + "...\n(內容較長，請點擊下方詳情)"

        bubble = {
            "type": "bubble",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
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
                        "text": content,
                        "wrap": True,
                        "size": "md",
                        "color": "#333333"
                    }
                ]
            }
        }
        
        if footer_text:
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
            
        return bubble

    @staticmethod
    def build_clinic_info_card():
        """Creates a specialized card for clinic address and contact."""
        return {
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://lh3.googleusercontent.com/p/AF1QipN_v_X_X_X", # Placeholder or clinic logo
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
                            "label": "📞 撥打電話",
                            "uri": "tel:0423950960"
                        }
                    }
                ]
            }
        }
