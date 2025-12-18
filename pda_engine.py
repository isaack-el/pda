class PDA:
    """Pushdown Automata Engine for Document Validation"""
    
    def __init__(self):
        self.stack = ['Z0']
        self.current_state = 'q0'
        self.history = []
        
    def reset(self):
        self.stack = ['Z0']
        self.current_state = 'q0'
        self.history = []
        
    def _add_history(self, char, action):
        self.history.append({
            'char': char,
            'state': self.current_state,
            'stack': self.stack.copy(),
            'action': action
        })
    
    def process_filename(self, filename):
        self.reset()
        self._add_history('ε', 'START - Validasi nama file')
        
        dot_found = False
        
        for char in filename:
            if self.current_state == 'q0':
                if char.isalnum() or char == '_':
                    self._add_history(char, 'READ - Karakter valid')
                elif char == '.':
                    if dot_found:
                        self._add_history(char, 'REJECT - Lebih dari satu titik')
                        self.current_state = 'q_reject'
                        return False, self.history
                    dot_found = True
                    self.stack.append('.')
                    self._add_history(char, 'PUSH . - Titik ditemukan')
                    self.current_state = 'q_dot'
                elif char in '@?#!%&*':
                    self._add_history(char, 'REJECT - Karakter tidak valid')
                    self.current_state = 'q_reject'
                    return False, self.history
                else:
                    self._add_history(char, 'REJECT - Karakter tidak diizinkan')
                    self.current_state = 'q_reject'
                    return False, self.history
            elif self.current_state == 'q_dot':
                if char.isalnum():
                    self._add_history(char, 'READ - Bagian ekstensi')
                else:
                    self._add_history(char, 'REJECT - Ekstensi tidak valid')
                    self.current_state = 'q_reject'
                    return False, self.history
        
        if not dot_found:
            self._add_history('ε', 'REJECT - Tidak ada titik')
            self.current_state = 'q_reject'
            return False, self.history
        
        parts = filename.split('.')
        if len(parts) != 2:
            self._add_history('ε', 'REJECT - Format tidak valid')
            self.current_state = 'q_reject'
            return False, self.history
        
        extension = parts[1].lower()
        valid_extensions = ['pdf', 'docx', 'xlsx', 'txt', 'jpg', 'png', 'xml', 'html']
        
        if extension not in valid_extensions:
            self._add_history('ε', f'REJECT - Ekstensi {extension} tidak valid')
            self.current_state = 'q_reject'
            return False, self.history
        
        if self.stack[-1] == '.':
            self.stack.pop()
            self._add_history('ε', 'POP . - Ekstensi valid')
        
        if len(self.stack) == 1 and self.stack[0] == 'Z0':
            self.current_state = 'q_accept'
            self._add_history('ε', 'ACCEPT - Nama file valid')
            return True, self.history
        
        self.current_state = 'q_reject'
        self._add_history('ε', 'REJECT - Stack tidak kosong')
        return False, self.history
    
    def process_content(self, content):
        self.reset()
        self._add_history('ε', 'START - Validasi isi file')
        
        if content.startswith('%PDF'):
            for i in range(min(4, len(content))):
                self._add_history(content[i], 'READ - Header PDF')
            self.current_state = 'q_accept'
            self._add_history('ε', 'ACCEPT - File PDF valid')
            return True, self.history
        
        if content.startswith('PK'):
            self._add_history('P', 'READ - Karakter pertama DOCX')
            self._add_history('K', 'READ - Karakter kedua DOCX')
            self.current_state = 'q_accept'
            self._add_history('ε', 'ACCEPT - File DOCX valid')
            return True, self.history
        
        if content.isalnum():
            for char in content[:10]:
                self._add_history(char, 'READ - Karakter TXT valid')
            self.current_state = 'q_accept'
            self._add_history('ε', 'ACCEPT - File TXT valid')
            return True, self.history
        
        self.current_state = 'q_reject'
        self._add_history('ε', 'REJECT - Format tidak dikenali')
        return False, self.history
    
    def process_filetype(self, extension):
        self.reset()
        self._add_history('ε', 'START - Validasi tipe file')
        
        extension = extension.lower()
        
        categories = {
            'pdf': ['pdf'],
            'doc': ['doc', 'docx'],
            'gambar': ['jpg', 'jpeg', 'png', 'gif', 'bmp'],
            'spreadsheet': ['xls', 'xlsx', 'csv'],
            'teks': ['txt', 'text'],
            'xml': ['xml', 'html', 'htm'],
            'data': ['json', 'csv']
        }
        
        found_category = None
        for category, exts in categories.items():
            if extension in exts:
                found_category = category
                break
        
        if found_category:
            self._add_history(extension, f'READ - File {found_category}')
            self.current_state = 'q_accept'
            self._add_history('ε', f'ACCEPT - Tipe file valid ({found_category})')
            return True, self.history
        else:
            self._add_history(extension, 'READ - Ekstensi file')
            self.current_state = 'q_reject'
            self._add_history('ε', 'REJECT - Tipe file tidak valid')
            return False, self.history
    
    def process_xml(self, xml_content):
        self.reset()
        self._add_history('ε', 'START - Validasi XML')
        
        tag_name = ''
        in_tag = False
        in_closing_tag = False
        
        i = 0
        while i < len(xml_content):
            char = xml_content[i]
            
            if char == '<':
                if i + 1 < len(xml_content) and xml_content[i + 1] == '/':
                    in_closing_tag = True
                    self._add_history('</', 'READ - Tag penutup')
                    i += 2
                    continue
                else:
                    in_tag = True
                    tag_name = ''
                    self._add_history('<', 'READ - Tag pembuka')
                    i += 1
                    continue
            elif char == '>':
                if in_tag:
                    self.stack.append(tag_name)
                    self._add_history('>', f'PUSH {tag_name} - Tag pembuka')
                    in_tag = False
                    self.current_state = 'q_content'
                elif in_closing_tag:
                    if self.stack and self.stack[-1] == tag_name:
                        self.stack.pop()
                        self._add_history('>', f'POP {tag_name} - Tag penutup cocok')
                    else:
                        expected = self.stack[-1] if self.stack else 'nothing'
                        self._add_history('>', f'REJECT - Tag tidak cocok (dibuka: {expected}, ditutup: {tag_name})')
                        self.current_state = 'q_reject'
                        return False, self.history
                    in_closing_tag = False
                i += 1
                continue
            elif in_tag or in_closing_tag:
                tag_name += char
            else:
                if self.current_state == 'q_content':
                    self._add_history(char, 'READ - Konten')
            i += 1
        
        if len(self.stack) == 1 and self.stack[0] == 'Z0':
            self.current_state = 'q_accept'
            self._add_history('ε', 'ACCEPT - XML valid')
            return True, self.history
        else:
            remaining_tags = self.stack[1:]
            self.current_state = 'q_reject'
            self._add_history('ε', f'REJECT - Tag belum ditutup: {", ".join(remaining_tags)}')
            return False, self.history
    
    def process_multilevel(self, content):
        self.reset()
        self._add_history('ε', 'START - Validasi multi-level')
        
        if '<' in content and '>' in content:
            xml_valid, xml_history = self.process_xml(content)
            if not xml_valid:
                return False, self.history
            
            import re
            content_match = re.search(r'>(.*?)<', content)
            if content_match and content_match.group(1):
                inner_content = content_match.group(1)
                
                self._add_history('ε', 'CHECK - Validasi konten sebagai nama file')
                filename_valid, filename_history = self.process_filename(inner_content)
                
                if filename_valid:
                    for step in filename_history:
                        if step not in self.history:
                            self.history.append(step)
                    self._add_history('ε', 'ACCEPT - Validasi multi-level berhasil')
                    return True, self.history
                else:
                    self._add_history('ε', 'REJECT - Konten tidak valid sebagai nama file')
                    return False, self.history
        
        return self.process_content(content)
    
    def get_transition_table(self, validator_type):
        tables = {
            'filename': [
                {'state': 'q0', 'input': 'a-z/A-Z/0-9/_', 'stack_top': 'Z0', 'new_state': 'q0', 'action': 'READ'},
                {'state': 'q0', 'input': '.', 'stack_top': 'Z0', 'new_state': 'q_dot', 'action': 'PUSH .'},
                {'state': 'q_dot', 'input': 'a-z/0-9', 'stack_top': '.', 'new_state': 'q_dot', 'action': 'READ'},
            ],
            'content': [
                {'state': 'q0', 'input': '%', 'stack_top': 'Z0', 'new_state': 'q_pdf_check', 'action': 'CHECK PDF'},
                {'state': 'q0', 'input': 'P', 'stack_top': 'Z0', 'new_state': 'q_docx_check', 'action': 'CHECK DOCX'},
            ],
            'filetype': [
                {'state': 'q0', 'input': 'pdf', 'stack_top': 'Z0', 'new_state': 'q_accept', 'action': 'ACCEPT (PDF)'},
                {'state': 'q0', 'input': 'doc/docx', 'stack_top': 'Z0', 'new_state': 'q_accept', 'action': 'ACCEPT (DOC)'},
            ],
            'xml': [
                {'state': 'q0', 'input': '<', 'stack_top': 'Z0', 'new_state': 'q_tag_open', 'action': 'READ TAG'},
                {'state': 'q_tag_open', 'input': 'tag_name', 'stack_top': 'Z0', 'new_state': 'q_tag_push', 'action': 'PUSH tag'},
            ],
            'multilevel': [
                {'state': 'q0', 'input': '<', 'stack_top': 'Z0', 'new_state': 'q_xml_parse', 'action': 'PARSE XML'},
                {'state': 'q_xml_parse', 'input': 'content', 'stack_top': '*', 'new_state': 'q_filename_check', 'action': 'CHECK FILENAME'},
            ]
        }
        
        return tables.get(validator_type, [])