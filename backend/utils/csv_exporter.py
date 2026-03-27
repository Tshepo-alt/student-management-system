# backend/utils/csv_exporter.py
"""
CSV Exporter Utility
Provides a unified interface for generating CSV exports from database models.
Supports multiple formats, streaming, and various export options.
"""

import csv
import io
import json
from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum


class ExportFormat(Enum):
    """Supported export formats"""
    CSV = "csv"
    JSON = "json"
    EXCEL = "excel"  # Placeholder for future Excel support


class DateFormat(Enum):
    """Date formatting options"""
    ISO = "iso"  # YYYY-MM-DD
    DMY = "dmy"  # DD/MM/YYYY
    MDY = "mdy"  # MM/DD/YYYY
    FULL = "full"  # Month DD, YYYY
    DATETIME = "datetime"  # YYYY-MM-DD HH:MM:SS


@dataclass
class ColumnDefinition:
    """Definition for a CSV column"""
    name: str  # Column header name
    field: Optional[str] = None  # Model field name or path (e.g., 'student.first_name')
    formatter: Optional[Callable] = None  # Custom formatter function
    width: Optional[int] = None  # Suggested column width for display
    required: bool = True  # Whether column is required


class CSVExporter:
    """
    CSV Exporter Utility Class
    
    Usage:
        exporter = CSVExporter()
        
        # Simple export
        csv_data = exporter.export(
            data=students,
            columns=[
                ColumnDefinition(name="Student Number", field="student_number"),
                ColumnDefinition(name="Name", field="full_name", formatter=lambda x: f"{x.first_name} {x.last_name}"),
                ColumnDefinition(name="Email", field="email")
            ]
        )
        
        # Or use response helper
        return exporter.download_response(
            data=students,
            columns=columns,
            filename="students_export"
        )
    """
    
    def __init__(self, delimiter: str = ',', quotechar: str = '"', 
                 quoting: int = csv.QUOTE_MINIMAL, encoding: str = 'utf-8'):
        """
        Initialize CSV exporter with configuration
        
        Args:
            delimiter: CSV delimiter character (default: ',')
            quotechar: Quote character for fields (default: '"')
            quoting: CSV quoting style (default: csv.QUOTE_MINIMAL)
            encoding: Output encoding (default: 'utf-8')
        """
        self.delimiter = delimiter
        self.quotechar = quotechar
        self.quoting = quoting
        self.encoding = encoding
    
    def _get_nested_value(self, obj: Any, field_path: str) -> Any:
        """
        Get nested attribute value from object using dot notation
        
        Args:
            obj: The object to extract value from
            field_path: Dot-separated path (e.g., 'student.program.name')
        
        Returns:
            The value at the path or None if not found
        """
        if not field_path:
            return None
        
        parts = field_path.split('.')
        current = obj
        
        try:
            for part in parts:
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current
        except (AttributeError, KeyError, TypeError):
            return None
    
    def _format_value(self, value: Any, formatter: Optional[Callable] = None,
                      date_format: DateFormat = DateFormat.ISO) -> str:
        """
        Format a value for CSV output
        
        Args:
            value: The value to format
            formatter: Custom formatter function
            date_format: Date format to use
        
        Returns:
            Formatted string value
        """
        if formatter and callable(formatter):
            try:
                return str(formatter(value))
            except Exception:
                return str(value) if value is not None else ''
        
        if value is None:
            return ''
        
        # Handle datetime objects
        if isinstance(value, datetime):
            if date_format == DateFormat.ISO:
                return value.strftime('%Y-%m-%d %H:%M:%S')
            elif date_format == DateFormat.DMY:
                return value.strftime('%d/%m/%Y')
            elif date_format == DateFormat.MDY:
                return value.strftime('%m/%d/%Y')
            elif date_format == DateFormat.FULL:
                return value.strftime('%B %d, %Y')
            else:
                return value.strftime('%Y-%m-%d')
        
        # Handle date objects
        if isinstance(value, date):
            if date_format == DateFormat.ISO:
                return value.strftime('%Y-%m-%d')
            elif date_format == DateFormat.DMY:
                return value.strftime('%d/%m/%Y')
            elif date_format == DateFormat.MDY:
                return value.strftime('%m/%d/%Y')
            elif date_format == DateFormat.FULL:
                return value.strftime('%B %d, %Y')
            else:
                return value.strftime('%Y-%m-%d')
        
        # Handle Decimal objects
        if isinstance(value, Decimal):
            return f'{value:.2f}'
        
        # Handle boolean
        if isinstance(value, bool):
            return 'Yes' if value else 'No'
        
        # Handle lists and dicts (convert to JSON)
        if isinstance(value, (list, dict)):
            return json.dumps(value, default=str)
        
        # Handle strings with special characters
        if isinstance(value, str):
            # Escape quotes and handle newlines
            value = value.replace('\n', ' ').replace('\r', ' ')
            value = value.replace('"', '""')
            return value
        
        return str(value)
    
    def export_to_string(self, data: List[Any], columns: List[ColumnDefinition],
                         date_format: DateFormat = DateFormat.ISO) -> str:
        """
        Export data to CSV string
        
        Args:
            data: List of objects to export
            columns: List of column definitions
            date_format: Date format to use
        
        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter, 
                           quotechar=self.quotechar, quoting=self.quoting)
        
        # Write headers
        headers = [col.name for col in columns]
        writer.writerow(headers)
        
        # Write data rows
        for record in data:
            row = []
            for col in columns:
                value = None
                
                if col.field:
                    value = self._get_nested_value(record, col.field)
                elif col.formatter:
                    value = col.formatter(record)
                else:
                    # Use the record itself
                    value = record
                
                formatted = self._format_value(value, col.formatter, date_format)
                row.append(formatted)
            
            writer.writerow(row)
        
        output.seek(0)
        return output.getvalue()
    
    def export_to_bytes(self, data: List[Any], columns: List[ColumnDefinition],
                        date_format: DateFormat = DateFormat.ISO) -> bytes:
        """
        Export data to CSV bytes
        
        Args:
            data: List of objects to export
            columns: List of column definitions
            date_format: Date format to use
        
        Returns:
            CSV bytes
        """
        csv_string = self.export_to_string(data, columns, date_format)
        return csv_string.encode(self.encoding)
    
    def export_to_file(self, filepath: str, data: List[Any], 
                       columns: List[ColumnDefinition],
                       date_format: DateFormat = DateFormat.ISO) -> None:
        """
        Export data to CSV file
        
        Args:
            filepath: Path to output file
            data: List of objects to export
            columns: List of column definitions
            date_format: Date format to use
        """
        csv_string = self.export_to_string(data, columns, date_format)
        with open(filepath, 'w', encoding=self.encoding) as f:
            f.write(csv_string)
    
    def export_stream(self, data: List[Any], columns: List[ColumnDefinition],
                      date_format: DateFormat = DateFormat.ISO) -> io.StringIO:
        """
        Export data to stream object
        
        Args:
            data: List of objects to export
            columns: List of column definitions
            date_format: Date format to use
        
        Returns:
            StringIO stream object
        """
        csv_string = self.export_to_string(data, columns, date_format)
        stream = io.StringIO(csv_string)
        stream.seek(0)
        return stream
    
    def download_response(self, data: List[Any], columns: List[ColumnDefinition],
                          filename: str, date_format: DateFormat = DateFormat.ISO,
                          include_timestamp: bool = True) -> tuple:
        """
        Create Flask response for CSV download
        
        Args:
            data: List of objects to export
            columns: List of column definitions
            filename: Base filename (without extension)
            date_format: Date format to use
            include_timestamp: Whether to include timestamp in filename
        
        Returns:
            Flask Response object
        """
        from flask import Response
        
        csv_string = self.export_to_string(data, columns, date_format)
        
        # Build filename with timestamp
        if include_timestamp:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            full_filename = f"{filename}_{timestamp}.csv"
        else:
            full_filename = f"{filename}.csv"
        
        return Response(
            csv_string,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={full_filename}',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )
    
    def export_dict(self, data: List[Dict[str, Any]], 
                    columns: List[ColumnDefinition],
                    date_format: DateFormat = DateFormat.ISO) -> str:
        """
        Export dictionary data to CSV
        
        Args:
            data: List of dictionaries
            columns: List of column definitions
            date_format: Date format to use
        
        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter,
                           quotechar=self.quotechar, quoting=self.quoting)
        
        # Write headers
        headers = [col.name for col in columns]
        writer.writerow(headers)
        
        # Write data rows
        for record in data:
            row = []
            for col in columns:
                value = record.get(col.field, '') if col.field else record
                formatted = self._format_value(value, col.formatter, date_format)
                row.append(formatted)
            writer.writerow(row)
        
        output.seek(0)
        return output.getvalue()


# ============================================
# PREDEFINED EXPORTERS FOR COMMON DATA TYPES
# ============================================

class StudentExporter:
    """Predefined exporter for student data"""
    
    @staticmethod
    def get_columns() -> List[ColumnDefinition]:
        """Get standard student export columns"""
        return [
            ColumnDefinition(name="Student Number", field="student_number"),
            ColumnDefinition(name="First Name", field="first_name"),
            ColumnDefinition(name="Last Name", field="last_name"),
            ColumnDefinition(name="Email", field="email"),
            ColumnDefinition(name="Phone", field="phone"),
            ColumnDefinition(name="Program", field="program.program_name"),
            ColumnDefinition(name="Campus", field="campus.campus_name"),
            ColumnDefinition(name="Year of Study", field="current_year"),
            ColumnDefinition(name="Current GPA", field="current_gpa"),
            ColumnDefinition(name="Academic Status", field="academic_status"),
            ColumnDefinition(name="Sponsorship", field="is_government_sponsored",
                           formatter=lambda x: "Government" if x else "Private"),
            ColumnDefinition(name="OVC Status", field="is_ovc",
                           formatter=lambda x: "Yes" if x else "No"),
            ColumnDefinition(name="Wants Accommodation", field="wants_accommodation",
                           formatter=lambda x: "Yes" if x else "No"),
            ColumnDefinition(name="BGCSE Points", field="bgcse_points"),
            ColumnDefinition(name="Enrollment Date", field="enrollment_date")
        ]
    
    @staticmethod
    def get_details_columns() -> List[ColumnDefinition]:
        """Get detailed student export columns"""
        return [
            ColumnDefinition(name="Student Number", field="student_number"),
            ColumnDefinition(name="Full Name", formatter=lambda x: f"{x.first_name} {x.last_name}"),
            ColumnDefinition(name="Email", field="email"),
            ColumnDefinition(name="Phone", field="phone"),
            ColumnDefinition(name="Alternative Phone", field="alternative_phone"),
            ColumnDefinition(name="Physical Address", field="physical_address"),
            ColumnDefinition(name="Program", field="program.program_name"),
            ColumnDefinition(name="Campus", field="campus.campus_name"),
            ColumnDefinition(name="Year of Study", field="current_year"),
            ColumnDefinition(name="Current GPA", field="current_gpa"),
            ColumnDefinition(name="Academic Status", field="academic_status"),
            ColumnDefinition(name="Sponsorship", field="is_government_sponsored",
                           formatter=lambda x: "Government" if x else "Private"),
            ColumnDefinition(name="OVC Status", field="is_ovc", formatter=lambda x: "Yes" if x else "No"),
            ColumnDefinition(name="Social Worker Name", field="social_worker_name"),
            ColumnDefinition(name="Emergency Contact", field="emergency_contact_name"),
            ColumnDefinition(name="Emergency Phone", field="emergency_contact_phone"),
            ColumnDefinition(name="BGCSE Points", field="bgcse_points"),
            ColumnDefinition(name="BGCSE Year", field="bgcse_year"),
            ColumnDefinition(name="BGCSE School", field="bgcse_school"),
            ColumnDefinition(name="Wants Accommodation", field="wants_accommodation",
                           formatter=lambda x: "Yes" if x else "No"),
            ColumnDefinition(name="Enrollment Date", field="enrollment_date"),
            ColumnDefinition(name="Expected Graduation", field="expected_graduation")
        ]


class PaymentExporter:
    """Predefined exporter for payment data"""
    
    @staticmethod
    def get_columns() -> List[ColumnDefinition]:
        """Get standard payment export columns"""
        return [
            ColumnDefinition(name="Receipt Number", field="receipt_number"),
            ColumnDefinition(name="Student Number", field="student.student_number"),
            ColumnDefinition(name="Student Name", 
                           formatter=lambda x: f"{x.student.first_name} {x.student.last_name}" if x.student else ""),
            ColumnDefinition(name="Amount", field="amount"),
            ColumnDefinition(name="Payment Date", field="payment_date"),
            ColumnDefinition(name="Payment Method", field="payment_method"),
            ColumnDefinition(name="Payment Type", field="payment_type"),
            ColumnDefinition(name="Status", field="status"),
            ColumnDefinition(name="Transaction ID", field="transaction_id"),
            ColumnDefinition(name="Is Government Payment", field="is_government_payment",
                           formatter=lambda x: "Yes" if x else "No")
        ]


class AccommodationExporter:
    """Predefined exporter for accommodation data"""
    
    @staticmethod
    def get_columns() -> List[ColumnDefinition]:
        """Get standard accommodation application export columns"""
        return [
            ColumnDefinition(name="Application ID", field="id"),
            ColumnDefinition(name="Student Number", field="student.student_number"),
            ColumnDefinition(name="Student Name", 
                           formatter=lambda x: f"{x.student.first_name} {x.student.last_name}" if x.student else ""),
            ColumnDefinition(name="Email", field="student.email"),
            ColumnDefinition(name="Room Type", field="room_type",
                           formatter=lambda x: "Bachelor Pad" if x == "bachelor_pad" else "Three-Bed Room"),
            ColumnDefinition(name="Block Preference", field="block_preference"),
            ColumnDefinition(name="Allocated Block", field="allocated_block"),
            ColumnDefinition(name="Allocated Room", field="allocated_room_number"),
            ColumnDefinition(name="Status", field="status"),
            ColumnDefinition(name="Emergency Contact", field="emergency_contact_name"),
            ColumnDefinition(name="Emergency Phone", field="emergency_contact_phone"),
            ColumnDefinition(name="Medical Conditions", field="medical_conditions"),
            ColumnDefinition(name="Applied Date", field="created_at")
        ]


class ProgramExporter:
    """Predefined exporter for program data"""
    
    @staticmethod
    def get_columns() -> List[ColumnDefinition]:
        """Get standard program export columns"""
        return [
            ColumnDefinition(name="Program Code", field="program_code"),
            ColumnDefinition(name="Program Name", field="program_name"),
            ColumnDefinition(name="Program Type", field="program_type.type_name"),
            ColumnDefinition(name="Duration (Years)", field="duration_years"),
            ColumnDefinition(name="Total Credits", field="total_credits"),
            ColumnDefinition(name="Min BGCSE Points", field="min_bgcse_points"),
            ColumnDefinition(name="Faculty", field="faculty.faculty_name"),
            ColumnDefinition(name="Department", field="department.department_name"),
            ColumnDefinition(name="Campus", field="campus.campus_name"),
            ColumnDefinition(name="Description", field="description"),
            ColumnDefinition(name="Career Opportunities", field="career_opportunities")
        ]


# ============================================
# UTILITY FUNCTIONS
# ============================================

def create_csv_response(data: List[Any], columns: List[ColumnDefinition],
                        filename: str, **kwargs) -> tuple:
    """
    Quick helper to create CSV download response
    
    Args:
        data: List of objects to export
        columns: List of column definitions
        filename: Base filename (without extension)
        **kwargs: Additional arguments for CSVExporter
    
    Returns:
        Flask Response object
    """
    exporter = CSVExporter(**kwargs)
    return exporter.download_response(data, columns, filename)


def export_models_to_csv(models: List[Any], fields: List[str], 
                         headers: List[str], filename: str) -> tuple:
    """
    Quick helper to export model list to CSV with simple field mapping
    
    Args:
        models: List of model instances
        fields: List of model field names to export
        headers: List of column headers (must match fields length)
        filename: Base filename (without extension)
    
    Returns:
        Flask Response object
    """
    if len(fields) != len(headers):
        raise ValueError("Fields and headers must have the same length")
    
    columns = [
        ColumnDefinition(name=headers[i], field=fields[i])
        for i in range(len(fields))
    ]
    
    exporter = CSVExporter()
    return exporter.download_response(models, columns, filename)


def dict_list_to_csv(data: List[Dict[str, Any]], headers: List[str],
                     field_mapping: Dict[str, str], filename: str) -> tuple:
    """
    Quick helper to export list of dictionaries to CSV
    
    Args:
        data: List of dictionaries
        headers: List of column headers
        field_mapping: Mapping from header to dict key
        filename: Base filename (without extension)
    
    Returns:
        Flask Response object
    """
    columns = [
        ColumnDefinition(name=header, field=field_mapping.get(header, header))
        for header in headers
    ]
    
    exporter = CSVExporter()
    return exporter.download_response(data, columns, filename)


def generate_statistics_csv(stats_data: Dict[str, Any], filename: str) -> tuple:
    """
    Generate CSV from statistics dictionary
    
    Args:
        stats_data: Dictionary of statistics
        filename: Base filename (without extension)
    
    Returns:
        Flask Response object
    """
    from flask import Response
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['GIPS COLLEGE - STATISTICS REPORT'])
    writer.writerow([f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
    writer.writerow([])
    
    for key, value in stats_data.items():
        if isinstance(value, dict):
            writer.writerow([key.upper()])
            for sub_key, sub_value in value.items():
                writer.writerow([f'  {sub_key}', sub_value])
            writer.writerow([])
        else:
            writer.writerow([key.replace('_', ' ').title(), value])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename={filename}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            'Content-Type': 'text/csv'
        }
    )


# ============================================
# BATCH EXPORTER
# ============================================

class BatchCSVExporter:
    """
    Batch CSV exporter for handling large datasets with pagination
    """
    
    def __init__(self, batch_size: int = 1000, **kwargs):
        """
        Initialize batch exporter
        
        Args:
            batch_size: Number of records per batch
            **kwargs: Arguments for CSVExporter
        """
        self.batch_size = batch_size
        self.exporter = CSVExporter(**kwargs)
    
    def export_in_batches(self, query, columns: List[ColumnDefinition],
                          filename: str) -> tuple:
        """
        Export large dataset in batches
        
        Args:
            query: SQLAlchemy query object
            columns: List of column definitions
            filename: Base filename (without extension)
        
        Returns:
            Flask Response object
        """
        from flask import Response
        
        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.exporter.delimiter,
                           quotechar=self.exporter.quotechar, 
                           quoting=self.exporter.quoting)
        
        # Write headers
        headers = [col.name for col in columns]
        writer.writerow(headers)
        
        # Process in batches
        offset = 0
        while True:
            batch = query.offset(offset).limit(self.batch_size).all()
            if not batch:
                break
            
            for record in batch:
                row = []
                for col in columns:
                    value = None
                    if col.field:
                        value = self.exporter._get_nested_value(record, col.field)
                    formatted = self.exporter._format_value(value, col.formatter)
                    row.append(formatted)
                writer.writerow(row)
            
            offset += self.batch_size
        
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename={filename}_{timestamp}.csv',
                'Content-Type': 'text/csv; charset=utf-8'
            }
        )