"""CorefHtml class is a writer for HTML+JavaScript visualization of coreference."""
from udapi.core.basewriter import BaseWriter
from udapi.core.coref import span_to_nodes, CorefEntity, CorefMention

ETYPES = 'person place organization animal plant object substance time number abstract event'.split()

class CorefHtml(BaseWriter):

    def __init__(self, path_to_js='web', **kwargs):
        super().__init__(**kwargs)
        self.path_to_js = path_to_js

    def process_document(self, doc):
        print('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">')
        print('<title>Udapi CorefUD viewer</title>')
        print('<script src="https://code.jquery.com/jquery-3.6.3.min.js"></script>')
        #print('<script src="coref.js"></script>') #$(window).on("load", function() {...}
        #print('<link rel="stylesheet" href="coref.css">')
        print('<style>\n'
              'span {border: 1px solid black; border-radius: 5px; padding: 2px; display:inline-block;}\n'
              '.empty {color: gray;}\n.singleton {border-style: dotted;}\n'
              '.crossing:before {content: "!"; display: block; background: #ffd500;}\n'
              '.active {border: 1px solid red;}\n.selected {background: red !important;}\n'
              '.other {background: hsl(0, 0%, 85%);}')
        for i, etype in enumerate(ETYPES):
            print(f'.{etype} {{background: hsl({int(i * 360/len(ETYPES))}, 80%, 85%);}}')
        print('</style>')
        print('</head>\n<body>')

        mention_ids = {}
        for entity in doc.coref_entities:
            for idx, mention in enumerate(entity.mentions, 1):
                mention_ids[mention] = f'{entity.eid}e{idx}'

        for tree in doc.trees:
            self.process_tree(tree, mention_ids)

        print('<script>\n$("span").click(function(e) {\n'
              ' let was_selected = $(this).hasClass("selected");\n'
              ' $("span").removeClass("selected");\n'
              ' if (!was_selected){$("."+$(this).attr("class").split(" ")[0]).addClass("selected");}\n'
              ' e.stopPropagation();\n});\n'
              '$("span").hover(\n'
              ' function(e) {$("span").removeClass("active"); $("."+$(this).attr("class").split(" ")[1]).addClass("active");},\n'
              ' function(e) {$("span").removeClass("active");}\n'
              ');\n</script>')
        print('</body></html>')

    def _start_subspan(self, subspan, mention_ids, crossing=False):
        m = subspan.mention
        e = m.entity
        classes = f'{e.eid} {mention_ids[m]} {e.etype or "other"}'
        title = f'eid={subspan.subspan_eid}\ntype={e.etype}\nhead={m.head.form}'
        if all(w.is_empty() for w in subspan.words):
            classes += ' empty'
        if len(e.mentions) == 1:
            classes += ' singleton'
        if crossing:
            classes += ' crossing'
            title += '\ncrossing'
        if m.other:
            title += f'\n{m.other}'
        print(f'<span class="{classes}" title="{title}">', end='') #data-eid="{e.eid}"

    def process_tree(self, tree, mention_ids):
        mentions = set()
        nodes_and_empty = tree.descendants_and_empty
        for node in nodes_and_empty:
            for m in node.coref_mentions:
                mentions.add(m)

        subspans = []
        for mention in mentions:
            subspans.extend(mention._subspans())
        subspans.sort(reverse=True)

        opened = []
        print('<p>')
        for node in nodes_and_empty:
            while subspans and subspans[-1].words[0] == node:
                subspan = subspans.pop()
                self._start_subspan(subspan, mention_ids)
                opened.append(subspan)
            
            is_head = self._is_head(node)
            if is_head:
                print('<b>', end='')
            if node.is_empty():
                print('<i>', end='')
            print(node.form, end='')
            if node.is_empty():
                print('</i>', end='')
            if is_head:
                print('</b>', end='')
            
            while opened and opened[-1].words[-1] == node:
                print('</span>', end='')
                opened.pop()

            # Two mentions are crossing iff their spans have non-zero intersection,
            # but neither is a subset of the other, e.g. (e1 ... (e2 ... e1) ... e2).
            # Let's visualize this (simplified) as
            # <span class=e1>...<span class=e2>...</span></span><span class="e2 crossing">...</span>
            # i.e. let's split mention e2 into two subspans which are next to each other.
            # Unfortunatelly, we cannot mark now both crossing mentions using html class "crossing"
            # (opening tags are already printed), so we'll mark only the second part of the second mention.
            endings = [x for x in opened if x.words[-1] == node]
            if endings:
                new_opened, brokens, found_crossing = [], [], False
                for subspan in opened:
                    if subspan.words[-1] == node:
                        found_crossing = True
                    elif found_crossing:
                        brokens.append(subspan)
                    else:
                        new_opened.append(subspan)
                opened = new_opened
                print('</span>' * (len(endings) + len(brokens)), end='')
                for broken in brokens:
                    self._start_subspan(broken, mention_ids, True)
                    opened.append(subspan)

            if not node.no_space_after:
                print(' ', end='')
                
        print('</p>')

    def _is_head(self, node):
        for mention in node.coref_mentions:
            if mention.head == node:
                return mention
        return None

# id needs to be a valid DOM querySelector
# so it cannot contain # nor / and it cannot start with a digit
def _id(node):
    if node is None:
        return 'null'
    return '"n%s"' % node.address().replace('#', '-').replace('/', '-')


def _esc(string):
    if string is None:
        string = ''
    return string.replace('\\', '\\\\').replace('"', r'\"')
