#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import nbformat
import cairosvg
from io import BytesIO
from PIL import Image
from nbconvert.preprocessors import (TagRemovePreprocessor, Preprocessor)
from traitlets import Set
import glob
import os

# for image embedding
import mistune
from urllib.parse import urlparse
from lxml import etree
import base64
import re

# mathjax support for mistune renderers;
# https://github.com/lepture/mistune-contrib/blob/master/mistune_contrib/math.py
class MathBlockMixin(object):
    """Math mixin for BlockLexer, mix this with BlockLexer::
        class MathBlockLexer(MathBlockMixin, BlockLexer):
            def __init__(self, *args, **kwargs):
                super(MathBlockLexer, self).__init__(*args, **kwargs)
                self.enable_math()
    """
    def enable_math(self):
        self.rules.block_math = re.compile(r'^\$\$([^\$]*?)\$\$', re.DOTALL)
        self.rules.block_latex = re.compile(
            r'^\\begin\{([a-z]*\*?)\}(.*?)\\end\{\1\}', re.DOTALL
        )
        self.default_rules = ['block_math', 'block_latex'] + self.default_rules

    def parse_block_math(self, m):
        """Parse a $$math$$ block"""
        self.tokens.append({
            'type': 'block_math',
            'text': m.group(1)
        })

    def parse_block_latex(self, m):
        self.tokens.append({
            'type': 'block_latex',
            'name': m.group(1),
            'text': m.group(2)
        })

class MathBlockLexer(mistune.BlockLexer, MathBlockMixin):
    def __init__(self, *args, **kwargs):
        super(MathBlockLexer, self).__init__(*args, **kwargs)
        self.enable_math()

class MathInlineMixin(object):
    """Math mixin for InlineLexer, mix this with InlineLexer::
        class MathInlineLexer(InlineLexer, MathInlineMixin):
            def __init__(self, *args, **kwargs):
                super(MathInlineLexer, self).__init__(*args, **kwargs)
                self.enable_math()
    """
    def enable_math(self):
        self.rules.math = re.compile(r'^\$(.+?)\$')
        self.default_rules.insert(0, 'math')
        self.rules.text = re.compile(r'^[\s\S]+?(?=[\\<!\[_*`~\$]|https?://| {2,}\n|$)')

    def output_math(self, m):
        return self.renderer.math(m.group(1))

class MathInlineLexer(MathInlineMixin, mistune.InlineLexer):
    def __init__(self, *args, **kwargs):
        super(MathInlineLexer, self).__init__(*args, **kwargs)
        self.enable_math()

class MathRendererMixin(object):
    def block_math(self, text):
        return '$$%s$$' % text

    def block_latex(self, name, text):
        return r'\begin{%s}%s\end{%s}' % (name, text, name)

    def math(self, text):
        return '$%s$' % text

# auxiliary code for image embedding
class MdRenderer(mistune.Renderer, MathRendererMixin):
    # from https://github.com/lepture/mistune-contrib; under BSD-3

    def get_block(text):
        type = text[0]
        p = text.find(':')
        if p <= 0:
            return ('', '', '')
        l = int(text[1:p])
        t = text[p+1:p+1+l]
        return (text[p+1+l:], type, t)

    def newline(self):
        return '\n'

    def text(self, text):
        return text

    def linebreak(self):
        return '\n'

    def hrule(self):
        return '---\n'

    def header(self, text, level, raw=None):
        return '#'*(level+1) + ' ' + text + '\n\n'

    def paragraph(self, text):
        return text + '\n\n'

    def list(self, text, ordered=True):
        r = ''
        while text:
            text, type, t = MdRenderer.get_block(text)
            if type == 'l':
                r += (ordered and ('# ' + t) or ('* ' + t)) + '\n'
        return r

    def list_item(self, text):
        return 'l' + str(len(text)) + ':' + text

    def block_code(self, code, lang=None):
        return '```\n' + code + '\n```\n'

    def block_quote(self, text):
        r = ''
        for line in text.splitlines():
            r += (line and '> ' or '') + line + '\n'
        return r

    def _emphasis(self, text, pref):
        return pref + text + pref + ' '

    def emphasis(self, text):
        return self._emphasis(text, '*')

    def double_emphasis(self, text):
        return self._emphasis(text, '**')

    def strikethrough(self, text):
        return self._emphasis(text, '~~')

    def codespan(self, text):
        return '`' + text + '`'

    def autolink(self, link, is_email=False):
        return '<' + link + '>'

    def link(self, link, title, text, image=False):
        r = (image and '!' or '') + '[' + text + '](' + link + ')'
        if title:
            r += '"' + title + '"'
        return r

    def image(self, src, title, text):
        self.link(src, title, text, image=True)

    def table(self, header, body):
        hrows = []
        while header:
            header, type1, t = MdRenderer.get_block(header)
            if type1 == 'r':
                flags = {}
                cols = []
                while t:
                    t, type2, t2 = MdRenderer.get_block(t)
                    if type2 == 'f':
                        fl, v = t2.split('=')
                        flags[fl] = v
                    elif type2 == 'c':
                        cols.append(type('',(object,),{'flags':flags,'text':t2})())
                hrows.append(cols)
        brows = []
        while body:
            body, type1, t = MdRenderer.get_block(body)
            if type1 == 'r':
                flags = {}
                cols = []
                while t:
                    t, type2, t2 = MdRenderer.get_block(t)
                    if type2 == 'f':
                        fl, v = t2.split('=')
                        flags[fl] = v
                    elif type2 == 'c':
                        cols.append(type('',(object,),{'flags':flags,'text':t2})())
                brows.append(cols)
        colscount = 0
        colmax = [0] * 100
        align = [''] * 100
        for row in hrows + brows:
            colscount = max(len(row), colscount)
            i = 0
            for col in row:
                colmax[i] = max(len(col.text), colmax[i])
                if 'align' in col.flags:
                    align[i] = col.flags['align'][0]
                i += 1
        r = ''
        for row in hrows:
            i = 0
            for col in row:
                if i > 0:
                    r += ' | '
                r += col.text.ljust(colmax[i])
                i += 1
            r += '\n'
        for i in range(colscount):
            if i > 0:
                r += ' | '
            if align[i] == 'c':
                r += ':' + '-'.ljust(colmax[i]-2, '-') + ':'
            elif align[i] == 'l':
                r += ':' + '-'.ljust(colmax[i]-1, '-')
            elif align[i] == 'r':
                r +=    '-'.ljust(colmax[i]-1, '-') + ':'
            else:
                r += '-'.ljust(colmax[i], '-')
        r += '\n'
        for row in brows:
            i = 0
            for col in row:
                if i > 0:
                    r += ' | '
                r += col.text.ljust(colmax[i])
                i += 1
            r += '\n'
        return r

    def table_row(self, content):
        return 'r' + str(len(content)) + ':' + content

    def table_cell(self, content, **flags):
        content = content.replace('\n', ' ')
        r = ''
        for fl in flags:
            v = flags[fl]
            if type(v) == type(True):
                v = v and 1 or 0
            v = str(v) and str(v) or ''
            r += 'f' + str(len(fl) + 1 + len(v)) + ':' + fl + '=' + v
        return r + 'c' + str(len(content)) + ':' + content

    def footnote_ref(self, key, index):
        return '[^' + str(key) + ']'

    def footnote_item(self, key, text):
        r = '[^' + str(key) + ']:\n'
        for l in text.split('\n'):
            r += '  ' + l.lstrip().rstrip() + '\n'
        return r

    def footnotes(self, text):
        return text

class MarkdownWithMath(mistune.Markdown):
    def __init__(self, renderer, **kwargs):
        if 'inline' not in kwargs:
            kwargs['inline'] = MathInlineLexer
        if 'block' not in kwargs:
            kwargs['block'] = MathBlockLexer
        super(MarkdownWithMath, self).__init__(renderer, **kwargs)

    def output_block_math(self):
        return self.renderer.block_math(self.token['text'])

    def output_block_latex(self):
        return self.renderer.block_latex(self.token['name'], self.token['text'])

class EmbedImagesRenderer(MdRenderer):
    outer_tag = re.compile(r'^<[^>]+>(.*?)</[^>]+>$', re.DOTALL)
    
    _mime_types = {
        'gif': 'image/gif',
        'pbm': 'image/x-portable-bitmap',
        'pgm': 'image/x-portable-graymap',
        'ppm': 'image/x-portable-pixmap',
        'tiff': 'image/tiff',
        'xbm': 'image/x-xbitmap',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'bmp': 'image/x-ms-bmp',
        'png': 'image/png',
        'svg': 'image/svg+xml',
    }
    
    def __init__(self, *args, root_path='.', convert_svgs=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.parser = etree.HTMLParser()
        self.root_path = root_path
        self.convert_svgs = convert_svgs
        
    def _mime_type(self, fname):
        img_ext = os.path.splitext(fname)[-1][1:]
        return self._mime_types.get(img_ext)

    def _html_image(self, src, title, text, width, height):
        s = '<img src="' + mistune.escape_link(src) + '"'
        if text:
            s += ' alt="' + text + '"'

        if not width is None:
            s += ' width="{}"'.format(width)

        if not height is None:
            s += ' height="{}"'.format(height)
        
        if title:
            s += ' title="' + mistune.escape(title) + '"'

        return s + ' />'
    
    def _to_data_src(self, src):
        # do nothing if the URL is not a local path
        scheme = urlparse(src).scheme
        if scheme != '': return None, None, None
        filepath = os.path.join(self.root_path, src)
        
        if not os.path.exists(filepath):
            raise OSError("File '{}' not found.".format(filepath))
        
        mimetype = self._mime_type(src)

        if mimetype is None:
            raise ValueError("Mimetype for '{}' unknown.".format(src))
        elif self.convert_svgs and mimetype == 'image/svg+xml':
            out = BytesIO()
            cairosvg.svg2png(url=filepath, write_to=out, scale=2.5)
            out.seek(0)
            im = Image.open(out)
            width = int(im.width / 2.5)
            height = int(im.height / 2.5)
            out.seek(0)
            content = out.read()
            mimetype = 'image/png'
        else:
            with open(filepath, "rb") as file:
                content = file.read()
            width = None
            height = None
        
        enc = base64.b64encode(content).decode('utf-8')
        data_src = "data:{mimetype};base64,{enc}".format(mimetype=mimetype, enc=enc)
        
        return data_src, width, height

    def _strip_outer_tag(self, html_fragment):
        m = self.outer_tag.search(html_fragment)

        if m is None:
            return html_fragment
        else:
            return m.group(1)
    
    def _proc_html(self, html):
        tree = etree.fromstring(html, parser=self.parser)
        body = tree.find('body')
        
        for img in body.findall('.//img'):
            data_src, width, height = self._to_data_src(img.get('src'))

            if img.get("width") is None and img.get("height") is None:
                if not width is None:
                    img.set("width", str(width))

                if not height is None:
                    img.set("height", str(height))

            if data_src: img.set('src', str(data_src))
            
        return self._strip_outer_tag(
            etree.tostring(body, method='html', pretty_print=True).decode('utf-8')
        )
    
    def image(self, src, title, text):
        data_src, width, height = self._to_data_src(src)
        
        if data_src is None:
            return super().image(src, title, text)
        else:
            return self._html_image(data_src, title, text, width, height)
    
    def inline_html(self, html):
        html = self._proc_html(html)
        return super().inline_html(html)
    
    def block_html(self, html):
        html = self._proc_html(html)
        return super().block_html(html)

class ClearOutputByTagPreprocessor(Preprocessor):
    """
    Removes the output from all code cells in a notebook.
    """

    remove_metadata_fields = Set(
        {'collapsed', 'scrolled'}
    ).tag(config=True)

    def __init__(self, with_tags=None, without_tags=None):
        self.with_tags = set(with_tags) if not with_tags is None else None
        self.without_tags = set(without_tags) if not without_tags is None else None

    def preprocess_cell(self, cell, resources, cell_index):
        """
        Apply a transformation on each cell. See base.py for details.
        """
        if cell.cell_type == 'code':
            tags = set(cell.get('metadata', {}).get('tags', []))
            if (
                ((self.with_tags is None) or
                 len(self.with_tags.intersection(tags)) == len(self.with_tags)) and
                ((self.without_tags is None) or
                 len(self.without_tags.intersection(tags)) == 0)
            ):
                cell.outputs = []
                cell.execution_count = None
                # Remove metadata associated with output
                if 'metadata' in cell:
                    for field in self.remove_metadata_fields:
                        cell.metadata.pop(field, None)
        return cell, resources

#-------------------------------------------------------------------------------
#                               run the conversion
#-------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Export Notebooks')
parser.add_argument('-o',
                    '--outdir',
                    default="DRIVE_MATERIAL",
                    help='The root path where to output the exported files.')

parser.add_argument('-s',
                    '--lab-subdir',
                    metavar='lab_subdir',
                    required=True,
                    help='Path to the directory with the tagged notebooks.' +
                         'E.g. "L1_python_intro".')

parser.add_argument('-d', '--no-image-embed', dest='embed_images', action='store_false')

args = parser.parse_args()
lab_subdir = args.lab_subdir
outdir = args.outdir
embed_images = args.embed_images

# renderer and markdown parser for embedding images
if embed_images:
    renderer = EmbedImagesRenderer(root_path=lab_subdir)
    mistune_parser = MarkdownWithMath(renderer=renderer,
                                      inline=MathInlineLexer,
                                      block=MathBlockLexer)

confs = {
    "STUDENTS_SK": {
        "remove_tags": ["en", "teacher", "drop"],
        "clear_outputs": True
    },

    "STUDENTS_EN": {
        "remove_tags": ["sk", "teacher", "drop"],
        "clear_outputs": True
    },

    "TEACHERS_EN": {
        "remove_tags": ["sk", "student", "drop"],
        "clear_outputs": False
    }
}

for conf_name, conf in confs.items():
    dirpath = os.path.join(outdir, conf_name, lab_subdir)
    os.makedirs(dirpath, exist_ok=True)

    for nb_fname in glob.iglob(os.path.join(lab_subdir, "*.ipynb")):
        nb_fbasename = os.path.basename(nb_fname)
        # skip filenames that start with _
        if(nb_fbasename[0] == '_'): continue

        print("Generating '{}' for notebook '{}'.".format(conf_name, nb_fname))
        resources = {}

        with open(nb_fname, encoding='utf8') as file:
            notebook = nbformat.read(file, nbformat.NO_CONVERT)

        tag_remove = TagRemovePreprocessor(
            remove_cell_tags=conf["remove_tags"])
        tag_remove.preprocess(notebook, resources)

        if conf["clear_outputs"]:
            clear_preproc = ClearOutputByTagPreprocessor(without_tags=['keep'])
            clear_preproc.preprocess(notebook, resources)

        if embed_images:
            for cell in notebook['cells']:
                if cell['cell_type'] == 'markdown':
                    cell['source'] = mistune_parser.render(cell['source'])

        with open(os.path.join(dirpath, nb_fbasename),
          'w', encoding='utf-8') as file:
            nbformat.write(notebook, file)
