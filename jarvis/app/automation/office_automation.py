"""
Office Automation Controller for NIVA.
Creates and modifies professional Microsoft Excel (.xlsx), Word (.docx), and PowerPoint (.pptx) documents.
"""

import logging
import os
from typing import Any, Dict, List, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import docx
from docx.shared import Inches, Pt, RGBColor
import pptx
from pptx.util import Inches as PptxInches, Pt as PptxPt

from app.automation.file_manager import FileManager
from app.safety.validation import PathValidator

logger = logging.getLogger("NIVA.Office")


class OfficeAutomation:
    """Creates formatted spreadsheets, documents, and presentations."""

    @classmethod
    def create_excel_sheet(
        cls,
        path: str,
        sheet_title: str,
        headers: List[str],
        rows: List[List[Any]],
        include_summary_row: bool = False
    ) -> Dict[str, Any]:
        """
        Creates an Excel workbook with styled headers, zebra rows, borders, and auto-formulas.
        """
        target_path = FileManager.resolve_path(path)
        is_safe, reason = PathValidator.is_safe_path(target_path, for_writing=True)
        if not is_safe:
            return {"success": False, "error": reason}

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = sheet_title or "Sheet1"

            # Header style
            header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            border_thin = Border(
                left=Side(style='thin', color='D9D9D9'),
                right=Side(style='thin', color='D9D9D9'),
                top=Side(style='thin', color='D9D9D9'),
                bottom=Side(style='thin', color='D9D9D9')
            )

            # Write headers
            ws.append(headers)
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = Alignment(horizontal="center", vertical="center")

            # Write rows
            for row_data in rows:
                ws.append(row_data)

            # Apply cell formatting & zebra striping
            row_count = len(rows) + 1
            for r in range(2, row_count + 1):
                row_fill = PatternFill(start_color="F2F5F9" if r % 2 == 0 else "FFFFFF", fill_type="solid")
                for c in range(1, len(headers) + 1):
                    cell = ws.cell(row=r, column=c)
                    cell.fill = row_fill
                    cell.border = border_thin
                    cell.font = Font(name="Calibri", size=10)

            # Add Total/Summary row if requested
            if include_summary_row and len(rows) > 0:
                summary_row = ["Total"] + [None] * (len(headers) - 1)
                ws.append(summary_row)
                sum_row_idx = row_count + 1

                for col_idx in range(2, len(headers) + 1):
                    col_letter = get_column_letter(col_idx)
                    # Check if first data cell in column is numeric
                    val = rows[0][col_idx - 1] if col_idx - 1 < len(rows[0]) else None
                    if isinstance(val, (int, float)):
                        ws.cell(row=sum_row_idx, column=col_idx).value = f"=SUM({col_letter}2:{col_letter}{row_count})"

                # Style summary row
                sum_font = Font(name="Calibri", size=11, bold=True)
                for col_idx in range(1, len(headers) + 1):
                    cell = ws.cell(row=sum_row_idx, column=col_idx)
                    cell.font = sum_font
                    cell.border = Border(top=Side(style='thin'), bottom=Side(style='double'))

            # Auto-fit column widths
            for col in ws.columns:
                max_len = max(len(str(cell.value or '')) for cell in col)
                col_letter = get_column_letter(col[0].column)
                ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

            wb.save(target_path)
            wb.close()

            if os.path.exists(target_path):
                return {
                    "success": True,
                    "message": f"Successfully created Excel workbook: {target_path} ({len(rows)} rows)",
                    "path": target_path
                }
            return {"success": False, "error": f"Failed to verify Excel file creation at {target_path}"}

        except Exception as e:
            return {"success": False, "error": f"Error generating Excel workbook: {str(e)}"}

    @classmethod
    def create_word_document(
        cls,
        path: str,
        title: str,
        paragraphs: List[str],
        table_data: Optional[List[List[str]]] = None
    ) -> Dict[str, Any]:
        """
        Creates a Word (.docx) document with headers, formatted paragraphs, and tables.
        """
        target_path = FileManager.resolve_path(path)
        is_safe, reason = PathValidator.is_safe_path(target_path, for_writing=True)
        if not is_safe:
            return {"success": False, "error": reason}

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        try:
            doc = docx.Document()

            # Add Title
            title_p = doc.add_heading(title, level=0)
            title_p.alignment = docx.enum.text.WD_ALIGN_PARAGRAPH.CENTER

            # Add paragraphs
            for p_text in paragraphs:
                p = doc.add_paragraph(p_text)
                p.paragraph_format.line_spacing = 1.15
                p.paragraph_format.space_after = Pt(8)

            # Add table if provided
            if table_data and len(table_data) > 0:
                rows_cnt = len(table_data)
                cols_cnt = len(table_data[0])
                table = doc.add_table(rows=rows_cnt, cols=cols_cnt)
                table.style = 'Light Shading Accent 1'

                for r_idx, row in enumerate(table_data):
                    for c_idx, val in enumerate(row):
                        cell = table.cell(r_idx, c_idx)
                        cell.text = str(val)

            doc.save(target_path)

            if os.path.exists(target_path):
                return {
                    "success": True,
                    "message": f"Successfully created Word document: {target_path}",
                    "path": target_path
                }
            return {"success": False, "error": f"Failed to verify Word document at {target_path}"}

        except Exception as e:
            return {"success": False, "error": f"Error generating Word document: {str(e)}"}

    @classmethod
    def create_presentation(
        cls,
        path: str,
        presentation_title: str,
        slides: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Creates a PowerPoint (.pptx) deck with title slide and bulleted content slides.
        """
        target_path = FileManager.resolve_path(path)
        is_safe, reason = PathValidator.is_safe_path(target_path, for_writing=True)
        if not is_safe:
            return {"success": False, "error": reason}

        os.makedirs(os.path.dirname(target_path), exist_ok=True)

        try:
            prs = pptx.Presentation()

            # Slide 1: Title slide layout (0)
            title_slide_layout = prs.slide_layouts[0]
            slide = prs.slides.add_slide(title_slide_layout)
            slide.shapes.title.text = presentation_title
            if len(slide.placeholders) > 1:
                slide.placeholders[1].text = "Generated by NIVA Autonomous AI Assistant"

            # Content slides layout (1: title and content)
            bullet_slide_layout = prs.slide_layouts[1]
            for s_info in slides:
                s_title = s_info.get("title", "Slide")
                bullets = s_info.get("bullets", [])

                slide = prs.slides.add_slide(bullet_slide_layout)
                slide.shapes.title.text = s_title

                body_shape = slide.shapes.placeholders[1]
                tf = body_shape.text_frame

                for idx, bullet in enumerate(bullets):
                    p = tf.add_paragraph() if idx > 0 else tf.paragraphs[0]
                    p.text = bullet
                    p.level = 0

            prs.save(target_path)

            if os.path.exists(target_path):
                return {
                    "success": True,
                    "message": f"Successfully created PowerPoint presentation: {target_path} ({len(slides)+1} slides)",
                    "path": target_path
                }
            return {"success": False, "error": f"Failed to verify presentation at {target_path}"}

        except Exception as e:
            return {"success": False, "error": f"Error generating presentation: {str(e)}"}
