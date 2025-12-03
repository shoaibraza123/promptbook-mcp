#!/usr/bin/env python3
"""
Copilot Session Organizer - Automatiza el almacenamiento y organización de prompts
Extrae metadata, categoriza y genera índice searchable de sesiones exportadas
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from config import CONFIG, Config

SessionMetadata = Dict[str, Any]
ParsedSession = Dict[str, Any]
Conversation = Dict[str, Any]
IndexData = Dict[str, Any]


class CopilotSessionParser:
    def __init__(self, session_file: Path):
        self.file_path = session_file
        self.content = session_file.read_text(encoding='utf-8')
        self.metadata: SessionMetadata = {}
        self.conversations: List[Conversation] = []

    def parse(self) -> ParsedSession:
        """Parse a Copilot session file and extract structured data.

        Returns:
            ParsedSession: Metadata, categorized conversations, and summary text.
        """
        self._extract_metadata()
        self._extract_conversations()
        self._categorize()
        return {
            'metadata': self.metadata,
            'conversations': self.conversations,
            'categories': self.metadata.get('categories', []),
            'summary': self._generate_summary()
        }

    def _extract_metadata(self) -> None:
        """Extract session metadata from header"""
        # Session ID
        if match := re.search(r'Session ID:.*?`([^`]+)`', self.content):
            self.metadata['session_id'] = match.group(1)

        # Dates
        if match := re.search(r'Started:.*?(\d{1,2}/\d{1,2}/\d{4}, \d{1,2}:\d{2}:\d{2})', self.content):
            self.metadata['started'] = match.group(1)

        if match := re.search(r'Duration:.*?(\d+m \d+s)', self.content):
            self.metadata['duration'] = match.group(1)

        if match := re.search(r'Exported:.*?(\d{1,2}/\d{1,2}/\d{4}, \d{1,2}:\d{2}:\d{2})', self.content):
            self.metadata['exported'] = match.group(1)

        # File size
        self.metadata['file_size'] = self.file_path.stat().st_size
        self.metadata['file_name'] = self.file_path.name

    def _extract_conversations(self) -> None:
        """Extract user prompts and context"""
        # Find all user messages
        user_pattern = r'### 👤 User\s*\n\n(.*?)(?=\n---|\n### |$)'
        matches = re.finditer(user_pattern, self.content, re.DOTALL)

        for i, match in enumerate(matches, 1):
            prompt_text = match.group(1).strip()

            conversation: Conversation = {
                'index': i,
                'prompt': prompt_text,
                'type': self._classify_prompt(prompt_text),
                'has_structure': self._has_structured_format(prompt_text),
                'length': len(prompt_text),
                'keywords': self._extract_keywords(prompt_text)
            }

            # Extract structured sections if present
            if conversation['has_structure']:
                conversation['structure'] = self._extract_structure(prompt_text)

            self.conversations.append(conversation)

    def _classify_prompt(self, text: str) -> str:
        """Classify prompt type based on content"""
        text_lower = text.lower()

        if any(word in text_lower for word in ['refactor', 'clean code', 'optimize']):
            return 'refactoring'
        elif any(word in text_lower for word in ['test', 'testing', 'spec']):
            return 'testing'
        elif any(word in text_lower for word in ['bug', 'fix', 'error', 'issue']):
            return 'debugging'
        elif any(word in text_lower for word in ['implement', 'create', 'develop', 'feature']):
            return 'implementation'
        elif any(word in text_lower for word in ['review', 'analyze', 'check']):
            return 'code-review'
        elif any(word in text_lower for word in ['documentation', 'document', 'readme']):
            return 'documentation'
        else:
            return 'general'

    def _has_structured_format(self, text: str) -> bool:
        """Check if prompt follows a structured format"""
        structure_markers = ['## ROL', '## CONTEXTO', '## OBJETIVO', '## 📋', '## 🎯']
        return any(marker in text for marker in structure_markers)

    def _extract_structure(self, text: str) -> Dict[str, str]:
        """Extract structured sections from prompt"""
        structure: Dict[str, str] = {}
        sections = ['ROL', 'CONTEXTO', 'OBJETIVO', 'Output', 'Notas']

        for section in sections:
            # Try with emoji and without
            patterns = [
                f'## 📋 {section}(.*?)(?=##|$)',
                f'## 🎯 {section}(.*?)(?=##|$)',
                f'## {section}(.*?)(?=##|$)'
            ]

            for pattern in patterns:
                if match := re.search(pattern, text, re.DOTALL | re.IGNORECASE):
                    structure[section.lower()] = match.group(1).strip()
                    break

        return structure

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from prompt"""
        # Common technical keywords
        tech_keywords: set[str] = set()

        # Programming languages
        languages = ['python', 'javascript', 'typescript', 'java', 'go', 'rust', 'cap', 'cds']
        # Frameworks
        frameworks = ['react', 'vue', 'angular', 'express', 'sap', 'bruno', 'jest']
        # Actions
        actions = ['refactor', 'test', 'debug', 'implement', 'optimize', 'fix']

        text_lower = text.lower()
        all_keywords = languages + frameworks + actions

        for keyword in all_keywords:
            if keyword in text_lower:
                tech_keywords.add(keyword)

        return list(tech_keywords)

    def _categorize(self) -> None:
        """Categorize session based on all conversations"""
        categories: set[str] = set()
        for conv in self.conversations:
            categories.add(conv['type'])

        self.metadata['categories'] = list(categories)

        # Main category (most common)
        if self.conversations:
            type_counts: defaultdict[str, int] = defaultdict(int)
            for conv in self.conversations:
                type_counts[conv['type']] += 1
            top_category = max(type_counts.items(), key=lambda item: item[1])[0]
            self.metadata['main_category'] = top_category

    def _generate_summary(self) -> str:
        """Generate a brief summary of the session"""
        num_convs = len(self.conversations)
        main_cat = self.metadata.get('main_category', 'general')

        return f"{num_convs} conversations - Focus: {main_cat}"


class PromptOrganizer:
    """Utility responsible for persisting prompts and updating the index."""

    def __init__(self, base_dir: Optional[Path] = None, *, config: Config | None = None):
        """Initialize the organizer with configurable base directories.

        Args:
            base_dir: Overrides the default prompts base directory.
            config: Shared configuration instance (defaults to ``CONFIG``).
        """
        self.config = config or CONFIG
        resolved_base = (base_dir or self.config.base_dir).resolve()
        self.base_dir = resolved_base
        self.prompts_dir = resolved_base / 'prompts'
        self.index_file = self.prompts_dir / 'index.json'

    def organize(self, session_files: List[Path], auto_categorize: bool = True) -> None:
        """Process Copilot session exports and update the prompt library.

        Args:
            session_files: Exported session markdown files.
            auto_categorize: Whether to categorize each prompt independently.
        """
        self.prompts_dir.mkdir(exist_ok=True)
        categories = [
            'refactoring',
            'testing',
            'debugging',
            'implementation',
            'code-review',
            'documentation',
            'general',
        ]
        for category in categories:
            (self.prompts_dir / category).mkdir(exist_ok=True)
        index = self._load_index()
        for session_file in session_files:
            print(f"📄 Processing: {session_file.name}")
            parser = CopilotSessionParser(session_file)
            data: ParsedSession = parser.parse()
            self._save_prompts(data, auto_categorize)
            self._update_index(index, data)
            print(f"  ✓ {data['summary']}")
        self._save_index(index)
        print(f"\n✅ Index saved: {self.index_file}")

    def _save_prompts(self, data: ParsedSession, auto_categorize: bool) -> None:
        """Save extracted prompts to organized files"""
        session_id = data['metadata'].get('session_id', 'unknown')
        main_category = data['metadata'].get('main_category', 'general')

        for conv in data['conversations']:
            category = conv['type'] if auto_categorize else main_category
            category_dir = self.prompts_dir / category

            # Create filename
            timestamp = data['metadata'].get('started', '').replace('/', '-').replace(':', '-').replace(', ', '_')
            filename = f"{timestamp}_{session_id[:8]}_prompt{conv['index']}.md"
            filepath = category_dir / filename

            # Generate markdown content
            content = self._format_prompt_markdown(conv, data['metadata'])
            filepath.write_text(content, encoding='utf-8')

    def _format_prompt_markdown(self, conversation: Conversation, metadata: SessionMetadata) -> str:
        """Format prompt as reusable markdown template"""
        lines: List[str] = []

        # Header
        lines.append(f"# Prompt: {conversation['type'].title()}\n")

        # Metadata
        lines.append("## Metadata")
        lines.append(f"- **Type**: {conversation['type']}")
        lines.append(f"- **Session**: {metadata.get('session_id', 'N/A')}")
        lines.append(f"- **Date**: {metadata.get('started', 'N/A')}")
        lines.append(f"- **Keywords**: {', '.join(conversation.get('keywords', []))}")
        lines.append("")

        # Structured sections if available
        if conversation.get('has_structure') and 'structure' in conversation:
            structure = cast(Dict[str, str], conversation['structure'])
            for section, content in structure.items():
                lines.append(f"## {section.upper()}")
                lines.append(content)
                lines.append("")

        # Full prompt
        lines.append("## Original Prompt")
        lines.append("```")
        lines.append(conversation['prompt'])
        lines.append("```")
        lines.append("")

        # Template variables section
        lines.append("## Template Variables")
        lines.append("<!-- Define variables for reuse -->")
        lines.append("- `{{PROJECT_NAME}}`: ")
        lines.append("- `{{CONTEXT}}`: ")
        lines.append("- `{{SPECIFIC_TASK}}`: ")
        lines.append("")

        return '\n'.join(lines)

    def _load_index(self) -> IndexData:
        """Load existing index or create new one"""
        if self.index_file.exists():
            existing: IndexData = json.loads(self.index_file.read_text()) or {}
            return existing
        return {'sessions': [], 'categories': {}, 'tags': {}}

    def _update_index(self, index: IndexData, data: ParsedSession) -> None:
        """Update index with new session data"""
        session_entry = {
            'session_id': data['metadata'].get('session_id'),
            'started': data['metadata'].get('started'),
            'duration': data['metadata'].get('duration'),
            'main_category': data['metadata'].get('main_category'),
            'categories': data['metadata'].get('categories', []),
            'num_prompts': len(data['conversations']),
            'summary': data['summary']
        }

        # Add to sessions
        index['sessions'].append(session_entry)

        # Update category index
        for category in data['metadata'].get('categories', []):
            if category not in index['categories']:
                index['categories'][category] = []
            index['categories'][category].append(data['metadata'].get('session_id'))

        # Update tags
        for conv in data['conversations']:
            for keyword in conv.get('keywords', []):
                if keyword not in index['tags']:
                    index['tags'][keyword] = []
                index['tags'][keyword].append(data['metadata'].get('session_id'))

    def _save_index(self, index: IndexData) -> None:
        """Save index to JSON file"""
        self.index_file.write_text(json.dumps(index, indent=2, ensure_ascii=False))

    def generate_readme(self) -> None:
        """Generate or refresh the prompt library README."""
        readme_path = self.prompts_dir / 'README.md'

        content = """# Prompt Library

Biblioteca organizada de prompts reutilizables extraídos de sesiones de Copilot CLI.

## Estructura

```
prompts/
├── refactoring/     # Prompts para refactorización de código
├── testing/         # Prompts para testing y QA
├── debugging/       # Prompts para debugging y fixes
├── implementation/  # Prompts para nuevas features
├── code-review/     # Prompts para revisión de código
├── documentation/   # Prompts para documentación
├── general/         # Otros prompts
├── index.json      # Índice searchable
└── README.md       # Este archivo
```

## Uso Rápido

1. **Buscar por categoría**: Navega a la carpeta correspondiente
2. **Buscar por keyword**: Consulta `index.json` sección `tags`
3. **Ver todas las sesiones**: Revisa `index.json` sección `sessions`

## Cómo Usar un Template

Cada prompt incluye:
- Metadata (tipo, fecha, keywords)
- Secciones estructuradas (si están disponibles)
- Prompt original
- Variables de template para personalizar

Ejemplo:
```markdown
{{PROJECT_NAME}} = "MiProyecto"
{{CONTEXT}} = "Backend en Node.js con Express"
{{SPECIFIC_TASK}} = "Optimizar queries de base de datos"
```

## Añadir Nuevas Sesiones

```bash
python prompt_organizer.py --organize *.md
```

## Comandos Útiles

```bash
# Organizar todas las sesiones
python prompt_organizer.py --organize copilot-session-*.md

# Buscar por keyword
grep -r "refactor" prompts/

# Ver índice
cat prompts/index.json | jq .
```
"""
        readme_path.write_text(content)
        print(f"📖 README generated: {readme_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Organiza y almacena prompts de Copilot CLI')
    parser.add_argument('--organize', nargs='+', help='Archivos de sesión a organizar')
    parser.add_argument('--dir', default='.', help='Directorio base (default: actual)')
    parser.add_argument(
        '--no-auto-categorize',
        action='store_true',
        help='No categorizar prompts individualmente',
    )

    args = parser.parse_args()

    base_dir = Path(args.dir)
    organizer = PromptOrganizer(base_dir)

    if args.organize:
        session_files = [Path(f) for f in args.organize]
        organizer.organize(session_files, auto_categorize=not args.no_auto_categorize)
        organizer.generate_readme()
    else:
        print("Uso: prompt_organizer.py --organize copilot-session-*.md")
        print("\nEjemplos:")
        print("  python prompt_organizer.py --organize *.md")
        print("  python prompt_organizer.py --organize copilot-session-*.md --dir ~/prompts")


if __name__ == '__main__':
    main()
