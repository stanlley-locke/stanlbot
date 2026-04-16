from html import escape

def safe_html(text: str) -> str:
    text = escape(text, quote=False)
    text = text.replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    text = text.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")
    text = text.replace("&lt;code&gt;", "<code>").replace("&lt;/code&gt;", "</code>")
    text = text.replace("&lt;pre&gt;", "<pre>").replace("&lt;/pre&gt;", "</pre>")
    return text

def truncate_message(text: str, max_len: int = 4000) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 40] + "\n\n[Message truncated due to length limits]"