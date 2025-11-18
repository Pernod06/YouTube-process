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
from io import BytesIO
import re
from datetime import datetime


class VideoPDFGenerator:
    """视频数据 PDF 生成器"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
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
            fontName='Helvetica-Bold'
        ))
        
        # 章节标题样式
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c5aa0'),
            spaceAfter=12,
            spaceBefore=20,
            fontName='Helvetica-Bold'
        ))
        
        # 时间戳样式
        self.styles.add(ParagraphStyle(
            name='Timestamp',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            spaceAfter=8,
            fontName='Helvetica-Oblique'
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
            fontName='Helvetica'
        ))
        
        # 描述样式
        self.styles.add(ParagraphStyle(
            name='Description',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#555555'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Oblique'
        ))
    
    def _clean_text(self, text):
        """清理文本中的特殊字符和引用标记"""
        if not text:
            return ""
        # 移除 [cite: xxx] 标记
        text = re.sub(r'\[cite:?\s*\d+(?:,\s*\d+)*\]', '', text)
        # 移除 [cite_start] 标记
        text = re.sub(r'\[cite_start\]', '', text)
        # 清理多余的空格
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def generate_pdf(self, video_data, output_path=None):
        """
        生成 PDF 文档
        
        Args:
            video_data: 视频数据字典
            output_path: 输出文件路径，如果为 None 则返回 BytesIO 对象
            
        Returns:
            如果 output_path 为 None，返回 BytesIO 对象；否则返回文件路径
        """
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
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
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
            
            # 时间戳
            timestamp_start = section.get('timestampStart', '00:00')
            timestamp_end = section.get('timestampEnd', '00:00')
            timestamp_text = f"⏱ {timestamp_start} - {timestamp_end}"
            story.append(Paragraph(timestamp_text, self.styles['Timestamp']))
            
            # 内容
            content = self._clean_text(section.get('content', ''))
            if content:
                story.append(Paragraph(content, self.styles['Content']))
            
            # 章节之间添加间距
            if i < len(sections) - 1:
                story.append(Spacer(1, 0.2*inch))
        
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


def generate_video_pdf(video_data, output_path=None):
    """
    便捷函数：生成视频 PDF
    
    Args:
        video_data: 视频数据字典
        output_path: 输出文件路径，如果为 None 则返回 BytesIO 对象
        
    Returns:
        如果 output_path 为 None，返回 BytesIO 对象；否则返回文件路径
    """
    generator = VideoPDFGenerator()
    return generator.generate_pdf(video_data, output_path)


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

