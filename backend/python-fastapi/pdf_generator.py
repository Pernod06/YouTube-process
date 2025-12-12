"""
PDF 生成器 - 将视频数据转换为 PDF 文档
"""

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from io import BytesIO
import re
import os
from datetime import datetime


def register_chinese_fonts():
    """注册中文字体"""
    # 尝试注册 CID 字体（内置支持）
    try:
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        return 'STSong-Light'
    except:
        pass
    
    # 尝试常见的系统中文字体路径
    font_paths = [
        # Ubuntu 已安装的中文字体
        '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
        '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
        # Linux 其他常见路径
        '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
        '/usr/share/fonts/opentype/noto/NotoSansSC-Regular.otf',
        # 自定义路径
        os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansSC-Regular.otf'),
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                return 'ChineseFont'
            except Exception as e:
                print(f"[WARN] 无法加载字体 {font_path}: {e}")
                continue
    
    # 如果都失败，返回默认字体
    print("[WARN] 未找到中文字体，将使用默认字体（中文可能显示为方块）")
    return 'Helvetica'


# 全局注册字体
CHINESE_FONT = register_chinese_fonts()
CHINESE_FONT_BOLD = CHINESE_FONT  # 大多数中文字体没有粗体版本


class VideoPDFGenerator:
    """视频数据 PDF 生成器"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.chinese_font = CHINESE_FONT
        self._setup_styles()
    
    def _setup_styles(self):
        """设置 PDF 样式"""
        # 标题样式
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=self.chinese_font
        ))
        
        # 章节标题样式
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=12,
            spaceBefore=20,
            fontName=self.chinese_font
        ))
        
        # 时间戳样式
        self.styles.add(ParagraphStyle(
            name='Timestamp',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=8,
            fontName=self.chinese_font
        ))
        
        # 内容样式
        self.styles.add(ParagraphStyle(
            name='Content',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#333333'),
            spaceAfter=15,
            alignment=TA_JUSTIFY,
            fontName=self.chinese_font
        ))
        
        # 描述样式
        self.styles.add(ParagraphStyle(
            name='Description',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#555555'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=self.chinese_font
        ))
        
        # 笔记标题样式
        self.styles.add(ParagraphStyle(
            name='NotesSectionTitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            textColor=colors.HexColor('#b45309'),
            spaceAfter=15,
            spaceBefore=25,
            fontName=self.chinese_font
        ))
        
        # 笔记内容预览样式
        self.styles.add(ParagraphStyle(
            name='NotePreview',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            fontStyle='italic',
            spaceAfter=4,
            fontName=self.chinese_font
        ))
        
        # 笔记正文样式
        self.styles.add(ParagraphStyle(
            name='NoteText',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=15,
            textColor=colors.HexColor('#1f2937'),
            spaceAfter=8,
            fontName=self.chinese_font
        ))
        
        # 笔记时间样式
        self.styles.add(ParagraphStyle(
            name='NoteDate',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#9ca3af'),
            spaceAfter=12,
            fontName=self.chinese_font
        ))
    
    def _clean_text(self, text):
        """清理文本中的特殊字符和引用标记"""
        if not text:
            return ""
        # 确保 text 是字符串类型
        if not isinstance(text, str):
            text = str(text)
        # 移除 [cite: xxx] 标记
        text = re.sub(r'\[cite:?\s*\d+(?:,\s*\d+)*\]', '', text)
        # 移除 [cite_start] 标记
        text = re.sub(r'\[cite_start\]', '', text)
        # 清理多余的空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def generate_pdf(self, video_data, output_path=None, notes=None):
        """
        生成 PDF 文档
        
        Args:
            video_data: 视频数据字典
            output_path: 输出文件路径，如果为 None 则返回 BytesIO 对象
            notes: 用户笔记列表，每个笔记包含 sectionId, sentenceIndex, contentPreview, noteText, createdAt
            
        Returns:
            如果 output_path 为 None，返回 BytesIO 对象；否则返回文件路径
        """
        if notes is None:
            notes = []
        # 创建 PDF 文档
        if output_path:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
        else:
            # 使用 BytesIO 在内存中生成
            buffer = BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=2*cm,
                leftMargin=2*cm,
                topMargin=2*cm,
                bottomMargin=2*cm
            )
        
        # 构建文档内容
        story = []
        
        # 添加标题
        video_info = video_data.get('videoInfo', {})
        title = video_info.get('title', 'Video Document')
        story.append(Paragraph(title, self.styles['CustomTitle']))
        story.append(Spacer(1, 0.3*inch))
        
        # 添加描述
        description = video_info.get('description', '')
        if description:
            story.append(Paragraph(description, self.styles['Description']))
            story.append(Spacer(1, 0.2*inch))
        
        # 添加视频信息表格
        video_id = video_info.get('videoId', 'N/A')
        info_data = [
            ['Video ID:', video_id],
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Total Sections:', str(len(video_data.get('sections', [])))]
        ]
        
        info_table = Table(info_data, colWidths=[3*cm, 10*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4*inch))
        
        # 添加分隔线
        story.append(self._create_line())
        story.append(Spacer(1, 0.2*inch))
        
        # 添加章节内容
        sections = video_data.get('sections', [])
        for i, section in enumerate(sections):
            # 章节标题
            section_title = section.get('title', f'Section {i+1}')
            story.append(Paragraph(f"{i+1}. {section_title}", self.styles['SectionTitle']))
            
            # 获取内容列表
            content_list = section.get('content', [])
            
            # 计算章节时间范围
            if isinstance(content_list, list) and len(content_list) > 0:
                # 新格式：content 是列表
                first_timestamp = content_list[0].get('timestampStart', '00:00:00') if isinstance(content_list[0], dict) else '00:00:00'
                last_timestamp = content_list[-1].get('timestampStart', '00:00:00') if isinstance(content_list[-1], dict) else '00:00:00'
                timestamp_text = f"[{first_timestamp} - {last_timestamp}]"
                story.append(Paragraph(timestamp_text, self.styles['Timestamp']))
                
                # 遍历每个内容项
                for item in content_list:
                    if isinstance(item, dict):
                        item_content = self._clean_text(item.get('content', ''))
                        item_timestamp = item.get('timestampStart', '')
                        if item_content:
                            # 添加带时间戳的内容
                            if item_timestamp:
                                content_with_time = f"<b>[{item_timestamp}]</b> {item_content}"
                            else:
                                content_with_time = item_content
                            story.append(Paragraph(content_with_time, self.styles['Content']))
                    elif isinstance(item, str):
                        # 兼容旧格式：content 项是字符串
                        cleaned = self._clean_text(item)
                        if cleaned:
                            story.append(Paragraph(cleaned, self.styles['Content']))
            elif isinstance(content_list, str):
                # 兼容旧格式：content 是字符串
                timestamp_start = section.get('timestampStart', '00:00')
                timestamp_end = section.get('timestampEnd', '00:00')
                timestamp_text = f"[{timestamp_start} - {timestamp_end}]"
                story.append(Paragraph(timestamp_text, self.styles['Timestamp']))
                
                content = self._clean_text(content_list)
                if content:
                    story.append(Paragraph(content, self.styles['Content']))
            
            # 章节之间添加间距
            if i < len(sections) - 1:
                story.append(Spacer(1, 0.2*inch))
        
        # 添加笔记部分（如果有笔记）
        if notes and len(notes) > 0:
            story.append(Spacer(1, 0.3*inch))
            story.append(self._create_line())
            story.append(Spacer(1, 0.2*inch))
            
            # 笔记标题
            story.append(Paragraph("my notes", self.styles['NotesSectionTitle']))
            story.append(Spacer(1, 0.1*inch))
            
            # 遍历每个笔记
            for note in notes:
                # 笔记内容预览（引用的原文）
                content_preview = note.get('contentPreview', '')
                if content_preview:
                    preview_text = f'"{self._clean_text(content_preview[:100])}..."'
                    story.append(Paragraph(preview_text, self.styles['NotePreview']))
                
                # 笔记正文
                note_text = self._clean_text(note.get('noteText', ''))
                if note_text:
                    story.append(Paragraph(note_text, self.styles['NoteText']))
                
                # 笔记时间
                created_at = note.get('createdAt', '')
                if created_at:
                    try:
                        # 尝试解析 ISO 格式时间
                        from datetime import datetime as dt
                        date_obj = dt.fromisoformat(created_at.replace('Z', '+00:00'))
                        date_str = date_obj.strftime('%Y-%m-%d %H:%M')
                    except:
                        date_str = created_at
                    story.append(Paragraph(date_str, self.styles['NoteDate']))
                
                story.append(Spacer(1, 0.1*inch))
        
        # 添加页脚信息
        story.append(Spacer(1, 0.3*inch))
        story.append(self._create_line())
        story.append(Spacer(1, 0.1*inch))
        footer_text = f"Generated by YouTube Video Processor | {datetime.now().strftime('%Y-%m-%d')}"
        story.append(Paragraph(footer_text, self.styles['Timestamp']))
        
        # 构建 PDF
        doc.build(story)
        
        if output_path:
            return output_path
        else:
            buffer.seek(0)
            return buffer
    
    def _create_line(self):
        """创建分隔线"""
        from reportlab.platypus import HRFlowable
        return HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#cccccc'),
            spaceAfter=0,
            spaceBefore=0
        )


def generate_video_pdf(video_data, output_path=None, notes=None):
    """
    便捷函数：生成视频 PDF
    
    Args:
        video_data: 视频数据字典
        output_path: 输出文件路径，如果为 None 则返回 BytesIO 对象
        notes: 用户笔记列表
        
    Returns:
        如果 output_path 为 None，返回 BytesIO 对象；否则返回文件路径
    """
    generator = VideoPDFGenerator()
    return generator.generate_pdf(video_data, output_path, notes=notes)


# 测试代码
if __name__ == '__main__':
    import json
    from pathlib import Path
    
    # 加载测试数据
    data_path = Path(__file__).parent.parent.parent / 'data' / 'video-data.json'
    with open(data_path, 'r', encoding='utf-8') as f:
        video_data = json.load(f)
    
    # 生成 PDF
    output_path = Path(__file__).parent / 'test_output.pdf'
    generate_video_pdf(video_data, str(output_path))
    print(f"PDF generated: {output_path}")

