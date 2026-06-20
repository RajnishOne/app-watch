"""
Discord release notes formatter
"""
import re
import logging

logger = logging.getLogger(__name__)


class DiscordFormatter:
    """Format App Store release notes for Discord"""
    
    # Section headers to recognize
    SECTION_HEADERS = [
        r'^new\s*:?\s*$',
        r'^added\s*:?\s*$',
        r'^improvements?\s*:?\s*$',
        r'^improved\s*:?\s*$',
        r'^fix(es|ed)?\s*:?\s*$',
        r'^bugs?\s*:?\s*$',
        r'^changes?\s*:?\s*$',
    ]
    
    def __init__(self, settings=None):
        # Load formatting settings
        self.settings = settings or {}
        self.version_header_template = self.settings.get('message_format_version_header', '# v{version}')
        self.section_header_template = self.settings.get('message_format_section_header', '## {section}')
        self.bullet = self.settings.get('message_format_bullet', '- ')
        self.empty_line_between_sections = self.settings.get('message_format_empty_line_between_sections', True)
        self.no_release_notes_text = self.settings.get('message_format_no_release_notes', 'No release notes available.')
        self.include_version_header = self.settings.get('message_format_include_version_header', True)
        
        # Compile regex patterns (including custom headers)
        headers = list(self.SECTION_HEADERS)
        custom_headers = self.settings.get('message_format_custom_headers', '')
        if custom_headers:
            for h in custom_headers.split(','):
                h = h.strip()
                if h:
                    headers.append(rf'^{re.escape(h)}\s*:?\s*$')
                    
        self.section_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in headers]
    
    def format_release_notes(self, version, release_notes):
        """
        Format release notes for Discord.
        
        Supports two cases:
        - Case A: Generic release text (fallback)
        - Case B: Structured sections
        """
        if not release_notes:
            version_header = self.version_header_template.format(version=version) if self.include_version_header else ""
            if version_header:
                return f"{version_header}\n\n{self.no_release_notes_text}"
            return self.no_release_notes_text
        
        # Clean up markdown from App Store
        cleaned = self._strip_app_store_markdown(release_notes)
        
        # Try to detect structured sections
        sections = self._parse_sections(cleaned)
        
        if sections:
            # Case B: Structured sections
            return self._format_structured(version, sections)
        else:
            # Case A: Generic release text
            return self._format_generic(version, cleaned)
    
    def _strip_app_store_markdown(self, text):
        """Strip App Store markdown (**, _, *)"""
        # Remove bold markers
        text = re.sub(r'\*\*', '', text)
        # Remove italic markers
        text = re.sub(r'_', '', text)
        text = re.sub(r'\*', '', text)
        return text.strip()
    
    def _parse_sections(self, text):
        """Parse text into structured sections"""
        lines = text.split('\n')
        sections = {}
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line is a section header
            is_header = False
            header_name = None
            
            for pattern in self.section_patterns:
                if pattern.match(line):
                    is_header = True
                    # Normalize header name
                    header_name = self._normalize_header(line)
                    break
            
            if is_header:
                current_section = header_name
                sections[current_section] = []
            elif current_section:
                # Add to current section
                sections[current_section].append(line)
            else:
                # No section header yet, might be generic text
                pass
        
        # Only return sections if we found at least one
        if sections:
            return sections
        return None
    
    def _normalize_header(self, header):
        """Normalize section header names"""
        header_clean = header.strip().rstrip(':').strip()
        header_lower = header_clean.lower()
        
        normalize = self.settings.get('message_format_normalize_headers', True)
        if not normalize:
            return header_clean
            
        # Load standard mapped names from settings
        name_new = self.settings.get('message_format_name_new', 'New')
        name_improvements = self.settings.get('message_format_name_improvements', 'Improvements')
        name_fixed = self.settings.get('message_format_name_fixed', 'Fixed')
        name_changes = self.settings.get('message_format_name_changes', 'Changes')
        
        # Map variations to standard names
        if header_lower in ['new', 'added']:
            return name_new
        elif header_lower in ['improvements', 'improved', 'improvement']:
            return name_improvements
        elif header_lower in ['fixed', 'fixes', 'fix', 'bugs', 'bug']:
            return name_fixed
        elif header_lower in ['changes', 'change']:
            return name_changes
        else:
            return header_clean
    
    def _format_structured(self, version, sections):
        """Format structured sections (Case B)"""
        parts = []
        
        # Add version header if enabled
        if self.include_version_header:
            version_header = self.version_header_template.format(version=version)
            parts.append(version_header)
            parts.append("")
        
        first_section = True
        for section_name, items in sections.items():
            # Add empty line before section (except first)
            if not first_section and self.empty_line_between_sections:
                parts.append("")
            
            # Add section header
            section_header = self.section_header_template.format(section=section_name)
            parts.append(section_header)
            
            # Add items with configured bullet style
            for item in items:
                item_clean = item.strip()
                # Check if item already starts with a bullet-like character
                if not (item_clean.startswith('-') or item_clean.startswith('*') or item_clean.startswith('•')):
                    item_clean = f"{self.bullet}{item_clean}"
                else:
                    # Replace existing bullet with configured one
                    item_clean = self.bullet + item_clean.lstrip('-*•').strip()
                parts.append(item_clean)
            
            if self.empty_line_between_sections:
                parts.append("")  # Empty line after section
            
            first_section = False
        
        return '\n'.join(parts).strip()
    
    def _format_generic(self, version, text):
        """Format generic release text (Case A) - simple bullet list"""
        lines = text.split('\n')
        parts = []
        
        # Add version header if enabled
        if self.include_version_header:
            version_header = self.version_header_template.format(version=version)
            parts.append(version_header)
            parts.append("")
        
        # Convert all non-empty lines to bullets
        for line in lines:
            line = line.strip()
            if line:
                # Check if line already starts with a bullet-like character
                if not (line.startswith('-') or line.startswith('*') or line.startswith('•')):
                    line = f"{self.bullet}{line}"
                else:
                    # Replace existing bullet with configured one
                    line = self.bullet + line.lstrip('-*•').strip()
                parts.append(line)
        
        return '\n'.join(parts).strip()

