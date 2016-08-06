import logging

try:
    from markdown import Markdown
except ImportError:
    Markdown = False

try:
    import frontmatter
except ImportError as e:
    frontmatter = False

from pelican import signals
from pelican.readers import MarkdownReader, METADATA_PROCESSORS
from pelican.utils import get_date, pelican_open

logger = logging.getLogger(__name__)


class FrontmarkReader(MarkdownReader):
    '''
    Reader for Markdown files with YAML metadata
    '''

    enabled = bool(Markdown) and bool(frontmatter)

    def __init__(self, *args, **kwargs):
        super(FrontmarkReader, self).__init__(*args, **kwargs)
        self.extensions = self.settings['MD_EXTENSIONS']

    def read(self, source_path):
        self._source_path = source_path
        self._md = Markdown(extensions=self.extensions)

        with pelican_open(source_path) as text:
            metadata, content = frontmatter.parse(text)
            metadata.setdefault('title', '-')

        return self._md.convert(content), self._parse_metadata(metadata)

    def _parse_metadata(self, meta):
        """Return the dict containing document metadata"""
        formatted_fields = self.settings['FORMATTED_FIELDS']

        output = {}
        for name, value in meta.items():
            name = name.lower()
            if name in formatted_fields:
                # handle summary metadata as markdown
                # summary metadata is special case and join all list values
                summary_values = "\n".join(value)
                # reset the markdown instance to clear any state
                self._md.reset()
                summary = self._md.convert(summary_values)
                output[name] = self.process_metadata(name, summary)
            else:
                output[name] = self.process_metadata(name, value)
        return output


def add_reader(readers):
    for k in FrontmarkReader.file_extensions:
        readers.reader_classes[k] = FrontmarkReader


def register():
    signals.readers_init.connect(add_reader)
