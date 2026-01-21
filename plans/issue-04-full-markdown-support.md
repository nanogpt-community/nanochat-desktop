# Issue #4: Full Markdown library support

**Issue URL**: https://github.com/nanogpt-community/nanochat-desktop/issues/4
**Status**: OPEN
**Priority**: MEDIUM

## Description
Markdown still isn't working correctly. Bold and italics work, but section headers (with ## for example) don't work.

## Objective
Implement full Markdown rendering support in message display:
- Headers (H1-H6) with proper sizing and formatting
- Lists (ordered and unordered)
- Code blocks (inline and multiline) with syntax highlighting
- Blockquotes
- Tables
- Links (clickable)
- Images (if supported)
- Horizontal rules
- All standard Markdown syntax

## Technical Context
- **File Location**: `src/ui/message_view.py`, markdown rendering logic
- **Current Issue**: Limited markdown support - only bold/italic working
- **Tech Stack**: GTK4, potentially need a markdown rendering library
- **Possible Solutions**:
  - Use GtkTextView with Pango markup
  - Integrate markdown-to-Pango converter
  - Use WebKit2GTK for full markdown rendering
  - Use python-markdown with custom GTK renderer

## Investigation

Current implementation likely uses basic Pango markup which doesn't support full Markdown. We need to:
1. Find current markdown rendering code
2. Evaluate rendering options
3. Implement full Markdown parser/renderer

## Implementation Plan

### Step 1: Audit Current Markdown Implementation
**Files to analyze**: `src/ui/message_view.py`, `src/utils/markdown.py`

Find and document current markdown rendering:
```python
# Current implementation (example)
def render_markdown(text: str) -> str:
    # Basic replacements
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)  # Bold
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)      # Italic
    return text
```

### Step 2: Choose Markdown Rendering Approach

**Option A: Pango Markup (Lightweight)**
- Pros: No dependencies, fast, native GTK
- Cons: Limited features, need to write custom parser

**Option B: python-markdown + Custom Renderer (Recommended)**
- Pros: Full markdown support, extensible
- Cons: Need custom GTK/Pango renderer

**Option C: WebKit2GTK (Full-featured)**
- Pros: Perfect rendering, supports everything
- Cons: Heavy dependency, overkill for text

**Recommendation**: Option B (python-markdown + custom renderer)

### Step 3: Install Dependencies
**Files to modify**: `setup.py`, `flatpak/com.nanogpt.NanoChat.yml`

Add markdown library:
```python
# setup.py
install_requires=[
    # ... existing deps ...
    'markdown>=3.5',
    'pygments>=2.17',  # For syntax highlighting
]
```

**Flatpak manifest**:
```yaml
# flatpak/com.nanogpt.NanoChat.yml
modules:
  - name: python-markdown
    buildsystem: simple
    build-commands:
      - pip3 install --prefix=/app markdown pygments
```

### Step 4: Create Markdown Renderer
**Files to create**: `src/ui/markdown_renderer.py`

Implement full markdown to Pango markup converter:
```python
import re
import markdown
from markdown.extensions import fenced_code, tables, nl2br
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.formatters import PangoMarkupFormatter
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Pango

class MarkdownRenderer:
    """Convert Markdown to GTK/Pango markup"""
    
    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                'fenced_code',
                'tables',
                'nl2br',
                'codehilite',
            ]
        )
    
    def render_to_pango(self, markdown_text: str) -> str:
        """Convert markdown to Pango markup"""
        # Convert markdown to HTML first
        html = self.md.convert(markdown_text)
        
        # Convert HTML to Pango markup
        pango_markup = self._html_to_pango(html)
        
        return pango_markup
    
    def _html_to_pango(self, html: str) -> str:
        """Convert HTML to Pango markup"""
        # Headers
        html = re.sub(r'<h1>(.*?)</h1>', r'<span size="xx-large" weight="bold">\1</span>\n', html)
        html = re.sub(r'<h2>(.*?)</h2>', r'<span size="x-large" weight="bold">\1</span>\n', html)
        html = re.sub(r'<h3>(.*?)</h3>', r'<span size="large" weight="bold">\1</span>\n', html)
        html = re.sub(r'<h4>(.*?)</h4>', r'<span weight="bold">\1</span>\n', html)
        html = re.sub(r'<h5>(.*?)</h5>', r'<span size="small" weight="bold">\1</span>\n', html)
        html = re.sub(r'<h6>(.*?)</h6>', r'<span size="x-small" weight="bold">\1</span>\n', html)
        
        # Text formatting
        html = re.sub(r'<strong>(.*?)</strong>', r'<b>\1</b>', html)
        html = re.sub(r'<em>(.*?)</em>', r'<i>\1</i>', html)
        html = re.sub(r'<code>(.*?)</code>', r'<tt>\1</tt>', html)
        
        # Lists
        html = re.sub(r'<ul>', '', html)
        html = re.sub(r'</ul>', '\n', html)
        html = re.sub(r'<ol>', '', html)
        html = re.sub(r'</ol>', '\n', html)
        html = re.sub(r'<li>(.*?)</li>', r'  • \1\n', html)
        
        # Blockquotes
        html = re.sub(r'<blockquote>(.*?)</blockquote>', r'<i>\1</i>', html, flags=re.DOTALL)
        
        # Paragraphs
        html = re.sub(r'<p>(.*?)</p>', r'\1\n', html)
        
        # Links (convert to blue underlined text)
        html = re.sub(r'<a href="(.*?)">(.*?)</a>', r'<span foreground="blue" underline="single">\2</span>', html)
        
        # Remove remaining HTML tags
        html = re.sub(r'<[^>]+>', '', html)
        
        return html


class MarkdownTextView(Gtk.TextView):
    """TextView that renders markdown"""
    
    def __init__(self):
        super().__init__(
            editable=False,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            margin_top=8,
            margin_bottom=8,
            margin_start=8,
            margin_end=8
        )
        
        self.renderer = MarkdownRenderer()
        
        # Create tags for code blocks
        buffer = self.get_buffer()
        self.code_tag = buffer.create_tag(
            "code",
            family="monospace",
            background="#f5f5f5"
        )
    
    def set_markdown(self, markdown_text: str):
        """Set content from markdown"""
        buffer = self.get_buffer()
        
        # Split into regular text and code blocks
        parts = self._split_code_blocks(markdown_text)
        
        buffer.set_text("")
        end_iter = buffer.get_end_iter()
        
        for part_type, content in parts:
            if part_type == "code":
                # Insert code block with formatting
                buffer.insert_with_tags(
                    end_iter,
                    content,
                    self.code_tag
                )
            else:
                # Insert regular markdown as Pango markup
                pango_markup = self.renderer.render_to_pango(content)
                buffer.insert_markup(end_iter, pango_markup, -1)
    
    def _split_code_blocks(self, text: str):
        """Split text into code and non-code parts"""
        parts = []
        code_pattern = r'```(.*?)\n(.*?)```'
        
        last_end = 0
        for match in re.finditer(code_pattern, text, re.DOTALL):
            # Add text before code block
            if match.start() > last_end:
                parts.append(("text", text[last_end:match.start()]))
            
            # Add code block
            lang = match.group(1).strip()
            code = match.group(2)
            parts.append(("code", code))
            
            last_end = match.end()
        
        # Add remaining text
        if last_end < len(text):
            parts.append(("text", text[last_end:]))
        
        return parts
```

### Step 5: Alternative - Use Multiple Widgets
**Files to create**: `src/ui/markdown_view.py`

For better rendering, use different widgets for different elements:
```python
class MarkdownView(Gtk.Box):
    """Composite widget that renders markdown using multiple GTK widgets"""
    
    def __init__(self, markdown_text: str):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8
        )
        
        self._render_markdown(markdown_text)
    
    def _render_markdown(self, text: str):
        """Parse and render markdown"""
        lines = text.split('\n')
        
        current_block = []
        block_type = 'paragraph'
        
        for line in lines:
            # Headers
            if line.startswith('# '):
                self._flush_block(current_block, block_type)
                self._add_header(line[2:], 1)
                current_block = []
            elif line.startswith('## '):
                self._flush_block(current_block, block_type)
                self._add_header(line[3:], 2)
                current_block = []
            elif line.startswith('### '):
                self._flush_block(current_block, block_type)
                self._add_header(line[4:], 3)
                current_block = []
            # Code blocks
            elif line.startswith('```'):
                if block_type == 'code':
                    self._add_code_block('\\n'.join(current_block))
                    current_block = []
                    block_type = 'paragraph'
                else:
                    self._flush_block(current_block, block_type)
                    block_type = 'code'
                    current_block = []
            # Lists
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                if block_type != 'list':
                    self._flush_block(current_block, block_type)
                    block_type = 'list'
                current_block.append(line)
            else:
                current_block.append(line)
        
        self._flush_block(current_block, block_type)
    
    def _add_header(self, text: str, level: int):
        """Add a header"""
        label = Gtk.Label(
            label=text,
            xalign=0,
            wrap=True
        )
        
        size_classes = {
            1: "title-1",
            2: "title-2",
            3: "title-3",
            4: "title-4",
        }
        
        if level in size_classes:
            label.add_css_class(size_classes[level])
        
        self.append(label)
    
    def _add_code_block(self, code: str):
        """Add a code block"""
        text_view = Gtk.TextView(
            editable=False,
            monospace=True,
        )
        text_view.get_buffer().set_text(code)
        text_view.add_css_class("code-block")
        
        self.append(text_view)
    
    def _flush_block(self, lines: list, block_type: str):
        """Flush accumulated lines as a block"""
        if not lines:
            return
        
        text = '\\n'.join(lines)
        
        if block_type == 'paragraph':
            self._add_paragraph(text)
        elif block_type == 'list':
            self._add_list(lines)
    
    def _add_paragraph(self, text: str):
        """Add a paragraph"""
        label = Gtk.Label(
            label=self._render_inline(text),
            xalign=0,
            wrap=True,
            use_markup=True
        )
        self.append(label)
    
    def _render_inline(self, text: str) -> str:
        """Render inline markdown (bold, italic, code)"""
        # Bold
        text = re.sub(r'\\*\\*(.+?)\\*\\*', r'<b>\\1</b>', text)
        # Italic
        text = re.sub(r'\\*(.+?)\\*', r'<i>\\1</i>', text)
        # Inline code
        text = re.sub(r'`(.+?)`', r'<tt>\\1</tt>', text)
        return text
    
    def _add_list(self, items: list):
        """Add a list"""
        for item in items:
            text = item.strip().lstrip('- ').lstrip('* ')
            label = Gtk.Label(
                label=f"  • {self._render_inline(text)}",
                xalign=0,
                wrap=True,
                use_markup=True
            )
            self.append(label)
```

### Step 6: Update Message View
**Files to modify**: `src/ui/message_view.py`

Use the new markdown renderer:
```python
from nanochat.ui.markdown_view import MarkdownView

class MessageView(Gtk.Box):
    def _create_content_view(self, content: str):
        """Create markdown-rendered content view"""
        markdown_view = MarkdownView(content)
        markdown_view.add_css_class("message-content")
        return markdown_view
```

### Step 7: Add CSS Styling
**Files to modify**: `src/ui/style.css`

Style markdown elements:
```css
.code-block {
    background: alpha(@window_bg_color, 0.5);
    border: 1px solid alpha(@borders, 0.3);
    border-radius: 6px;
    padding: 12px;
    font-family: monospace;
}

.message-content {
    padding: 8px;
}
```

### Step 8: Test Implementation

**Manual Testing Checklist**:
- [ ] Headers (H1-H6) render with correct sizes
- [ ] Bold text renders correctly
- [ ] Italic text renders correctly
- [ ] Inline code renders in monospace
- [ ] Code blocks render with background
- [ ] Unordered lists render with bullets
- [ ] Ordered lists render with numbers
- [ ] Blockquotes render distinctly
- [ ] Links are visible (and clickable if implemented)
- [ ] Tables render properly
- [ ] Mixed markdown elements work together
- [ ] Long text wraps correctly
- [ ] Performance is acceptable with large markdown

**Test Cases**:
```markdown
# Header 1
## Header 2
### Header 3

**Bold text** and *italic text* and `inline code`.

- List item 1
- List item 2
  - Nested item

1. Ordered item 1
2. Ordered item 2

```python
def example():
    print("Code block")
```

> This is a blockquote

[Link text](https://example.com)
```

## Files to Create/Modify

### New Files
- `src/ui/markdown_renderer.py` - Markdown to Pango converter (Option 1)
- `src/ui/markdown_view.py` - Composite markdown widget (Option 2)

### Modified Files
- `src/ui/message_view.py` - Use new markdown renderer
- `setup.py` - Add markdown dependencies
- `flatpak/com.nanogpt.NanoChat.yml` - Add markdown to build
- `src/ui/style.css` - Style markdown elements

## Dependencies
- `markdown` (Python library) - For parsing markdown
- `pygments` (optional) - For syntax highlighting in code blocks

## Acceptance Criteria
- [ ] All standard Markdown syntax renders correctly
- [ ] Headers (H1-H6) display with proper sizing
- [ ] Lists (ordered and unordered) render properly
- [ ] Code blocks render in monospace with background
- [ ] Inline code renders correctly
- [ ] Bold and italic text work (regression test)
- [ ] No performance issues with large markdown documents
- [ ] Text wraps appropriately
- [ ] Styling is consistent with app theme

## Potential Issues & Solutions

**Issue**: Pango markup doesn't support all HTML/Markdown features
**Solution**: Use composite widget approach with different GTK widgets for different elements

**Issue**: Code blocks with syntax highlighting are complex
**Solution**: Start with simple monospace rendering, add highlighting later

**Issue**: Tables are difficult to render in GTK
**Solution**: Use simple formatting or skip table support for v1

**Issue**: Performance issues with complex markdown
**Solution**: Cache rendered markup, lazy render off-screen content

## Related Issues
- Issue #5 - Thinking block view (thinking content may contain markdown)

## Estimated Effort
**Time**: 4-6 hours
**Complexity**: Medium-High
**Risk**: Medium

## Additional Notes
- This is a critical UX issue - proper markdown is expected
- Consider syntax highlighting as a follow-up enhancement
- May want to add markdown preview in input area (future)
- Consider supporting extensions like math formulas (future)
- Test with actual AI-generated content which often uses complex markdown
