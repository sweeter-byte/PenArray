"""
Text Processing Utilities for BiZhen Multi-Agent System.

Provides accurate character counting for Chinese essays following
Gaokao essay counting standards. This is CRITICAL for word count
enforcement in the revision system.

Standard Chinese Essay Counting Rules:
- Each Chinese character counts as 1 unit
- Each English word counts as 1 unit (not per-character)
- Punctuation marks count as 1 unit each
- Numbers: consecutive digits count as 1 unit
- Whitespace (spaces, newlines, tabs) are NOT counted
"""

import re
from typing import Tuple


def count_chinese_chars(text: str) -> int:
    """
    Count characters in Chinese essay following Gaokao standards.

    This function provides ACCURATE character counting that should NOT
    be delegated to LLMs due to their inconsistent counting abilities.

    Counting Rules:
    - Chinese characters (汉字): 1 each
    - Chinese punctuation: 1 each
    - English words (consecutive letters): 1 per word
    - Numbers (consecutive digits): 1 per number group
    - Other punctuation: 1 each
    - Whitespace: NOT counted

    Args:
        text: Essay text to count

    Returns:
        Total character count

    Example:
        >>> count_chinese_chars("人生如梦，岁月如歌。")
        10  # 8 Chinese chars + 2 punctuation marks

        >>> count_chinese_chars("Hello世界！")
        3   # 1 English word + 2 Chinese chars + 1 punctuation
    """
    if not text:
        return 0

    # Remove all whitespace (spaces, newlines, tabs)
    text = re.sub(r'\s+', '', text)

    count = 0
    i = 0

    while i < len(text):
        char = text[i]

        # Chinese character (CJK Unified Ideographs range)
        if '\u4e00' <= char <= '\u9fff':
            count += 1
            i += 1
        # Chinese punctuation
        elif char in '，。！？；：""''【】（）《》、…—～·':
            count += 1
            i += 1
        # ASCII letters - count consecutive as one word
        elif char.isalpha():
            # Find the end of the word
            j = i
            while j < len(text) and text[j].isalpha():
                j += 1
            count += 1  # One word = one unit
            i = j
        # Digits - count consecutive as one number
        elif char.isdigit():
            # Find the end of the number
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            count += 1  # One number = one unit
            i = j
        # Other punctuation (ASCII punctuation, etc.)
        elif char in '.,!?;:\'"()[]{}/-_@#$%^&*+=<>|\\`~':
            count += 1
            i += 1
        else:
            # Any other character (rare cases)
            count += 1
            i += 1

    return count


def analyze_essay_length(text: str, target_min: int = 850, target_max: int = 1050) -> Tuple[int, str, str]:
    """
    Analyze essay length and provide feedback for revision.

    Args:
        text: Essay text
        target_min: Minimum acceptable character count (default 850)
        target_max: Maximum acceptable character count (default 1050)

    Returns:
        Tuple of (count, status, suggestion)
        - count: Actual character count
        - status: "pass", "tolerate", or "fail"
        - suggestion: Revision guidance if needed

    Example:
        >>> analyze_essay_length("..." * 300)  # 900 chars
        (900, "pass", "")

        >>> analyze_essay_length("..." * 400)  # 1200 chars
        (1200, "fail", "当前字数1200字，需要删减至850-1050字范围内。建议删减约150-350字。")
    """
    count = count_chinese_chars(text)

    # Pass: within target range
    if target_min <= count <= target_max:
        return count, "pass", ""

    # Tolerate: slightly over (up to 1100)
    if target_max < count <= 1100:
        return count, "tolerate", ""

    # Fail: too long
    if count > 1100:
        excess = count - target_max
        suggestion = f"当前字数{count}字，需要删减至{target_min}-{target_max}字范围内。建议删减约{excess - 50}-{excess}字。"
        return count, "fail", suggestion

    # Fail: too short
    if count < target_min:
        deficit = target_min - count
        suggestion = f"当前字数{count}字，需要扩展至{target_min}-{target_max}字范围内。建议增加约{deficit}-{deficit + 100}字。"
        return count, "fail", suggestion

    return count, "pass", ""


def check_essay_structure(text: str) -> dict:
    """
    Check if essay has proper structure (introduction, body, conclusion).

    Args:
        text: Essay text

    Returns:
        Dictionary with structure analysis:
        - has_introduction: bool
        - has_body: bool
        - has_conclusion: bool
        - is_complete: bool (all three present)
        - feedback: str (if incomplete)
    """
    # Split into paragraphs
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

    result = {
        "has_introduction": False,
        "has_body": False,
        "has_conclusion": False,
        "is_complete": False,
        "feedback": ""
    }

    # Need at least 3 paragraphs for proper structure
    if len(paragraphs) < 3:
        result["feedback"] = "文章段落不足，缺少完整的开头、主体、结尾结构。"
        return result

    # Check for introduction markers
    intro_markers = ["引言", "开篇", "首先", "众所周知", "当今", "随着", "在这个"]
    first_para = paragraphs[0]
    result["has_introduction"] = any(m in first_para for m in intro_markers) or len(first_para) >= 50

    # Check for body (multiple middle paragraphs with arguments)
    body_markers = ["首先", "其次", "再次", "此外", "另外", "同时", "一方面", "另一方面", "不仅", "而且"]
    body_text = "\n".join(paragraphs[1:-1])
    result["has_body"] = len(paragraphs) >= 3 and (
        any(m in body_text for m in body_markers) or len(body_text) >= 300
    )

    # Check for conclusion markers
    conclusion_markers = ["综上所述", "总之", "因此", "由此可见", "总而言之", "归根结底", "最后"]
    last_para = paragraphs[-1]
    result["has_conclusion"] = any(m in last_para for m in conclusion_markers) or (
        len(last_para) >= 50 and len(paragraphs) >= 3
    )

    # Overall assessment
    result["is_complete"] = all([
        result["has_introduction"],
        result["has_body"],
        result["has_conclusion"]
    ])

    if not result["is_complete"]:
        missing = []
        if not result["has_introduction"]:
            missing.append("开头")
        if not result["has_body"]:
            missing.append("主体")
        if not result["has_conclusion"]:
            missing.append("结尾")
        result["feedback"] = f"文章结构不完整，缺少：{', '.join(missing)}。"

    return result
