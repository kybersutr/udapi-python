"""Root class represents the technical root node in each tree."""
import logging

from udapi.core.node import Node, ListOfNodes
from udapi.core.mwt import MWT

# 7 instance attributes is too low (CoNLL-U has 10 columns)
# The set of public attributes/properties and methods of Root was well-thought.
# pylint: disable=too-many-instance-attributes

class Root(Node):
    """Class for representing root nodes (technical roots) in UD trees."""
    __slots__ = ['_sent_id', '_zone', '_bundle', '_descendants', '_mwts', 'text', 'comment']

    def __init__(self, sent_id=None, zone=None, comment=None, text=None):
        """Create new root node."""
        # Call constructor of the parent object.
        super().__init__()

        self.ord = 0
        self.form = '<ROOT>'
        self.lemma = '<ROOT>'
        self.upos = '<ROOT>'
        self.xpos = '<ROOT>'
        self.deprel = '<ROOT>'
        self.comment = comment
        self.text = text

        self._sent_id = sent_id
        self._zone = zone
        self._bundle = None
        self._descendants = []
        self._mwts = []

    @property
    def sent_id(self):
        """ID of this tree, stored in the sent_id comment in CoNLL-U."""
        return self._sent_id

    @sent_id.setter
    def sent_id(self, sent_id):
        self._sent_id = sent_id

    @property
    def bundle(self):
        """Return the bundle which this tree belongs to."""
        return self._bundle

    @bundle.setter
    def bundle(self, bundle):
        self._bundle = bundle

    @property
    def zone(self):
        """Return zone (string label) of this tree."""
        return self._zone

    @zone.setter
    def zone(self, zone):
        """Specify which zone the root belongs to."""
        if self._bundle:
            self._bundle.check_zone(zone)
        self._zone = zone

    @property
    def parent(self):
        """Return dependency parent (head) node.

        This root-specific implementation returns always None.
        """
        return None

    @parent.setter
    def parent(self, _):
        """Attempts at setting parent of root result in AttributeError exception."""
        raise AttributeError('The technical root cannot have a parent.')

    @property
    def descendants(self):
        """Return a list of all descendants of the current node.

        The nodes are sorted by their ord.
        This root-specific implementation returns all the nodes in the tree except the root itself.
        """
        return ListOfNodes(self._descendants, origin=self)

    def is_descendant_of(self, node):
        """Is the current node a descendant of the node given as argument?

        This root-specific implementation returns always False.
        """
        return False

    def is_root(self):
        """Return True for all Root instances."""
        return True

    def remove(self):
        """Remove the whole tree from its bundle."""
        self.bundle.trees = [root for root in self.bundle.trees if root != self]

    def shift(self, reference_node, after=0, move_subtree=0, reference_subtree=0):
        """Attempts at changing the word order of root result in Exception."""
        raise Exception('Technical root cannot be shifted as it is always the first node')

    def address(self):
        """Full (document-wide) id of the root.

        The general format of root nodes is:
        root.bundle.bundle_id + '/' + root.zone, e.g. s123/en_udpipe.
        If zone is empty, the slash is excluded as well, e.g. s123.
        Root's address is stored in CoNLL-U files as sent_id (in a special comment).
        TODO: Make sure root.sent_id returns always the same string as root.address.
        """
        return self._bundle.bundle_id + ('/' + self.zone if self.zone else '')

    # TODO document whether misc is a string or dict or it can be both
    def create_multiword_token(self, words=None, form=None, misc=None):
        """Create and return a new multi-word token (MWT) in this tree.

        The new MWT can be optionally initialized using the following args.
        Args:
        words: a list of nodes which are part of the new MWT
        form: string representing the surface form of the new MWT
        misc: misc attribute of the new MWT
        """
        mwt = MWT(words, form, misc, root=self)
        self._mwts.append(mwt)
        return mwt

    @property
    def multiword_tokens(self):
        """Return a list of all multi-word tokens in this tree."""
        return self._mwts

    # TODO should this setter be part of the public API?
    @multiword_tokens.setter
    def multiword_tokens(self, mwts):
        """Set the list of all multi-word tokens in this tree."""
        self._mwts = mwts

    def _update_ordering(self):
        """Update the ord attribute of all nodes.

        Update also the list of all tree nodes stored in root._descendants.
        This method is automatically called after node removal or reordering.
        """
        self._descendants = sorted(self.unordered_descendants(), key=lambda node: node.ord)
        for (new_ord, node) in enumerate(self._descendants, 1):
            node.ord = new_ord

    def get_sentence(self, if_missing='detokenize'):
        """Return either the stored `root.text` or (if None) `root.compute_text()`.

        Args:
        if_missing: What to do if `root.text` is `None`? (default=detokenize)
         * `detokenize`: use `root.compute_text()` to compute the sentence.
         * `empty`: return an empty string
         * `warn_detokenize`, `warn_empty`: in addition emit a warning via `logging.warning()`
         * `fatal`: raise an exception
        """
        sentence = self.text
        if sentence is not None:
            return sentence
        if if_missing == 'fatal':
            raise RuntimeError('Tree %s has empty root.text.' % self.address())
        if if_missing.startswith('warn'):
            logging.warning('Tree %s has empty root.text.', self.address())
        if if_missing.endswith('detokenize'):
            return self.compute_text()
        return ''

    def add_comment(self, string):
        """Add a given `string` to `root.comment` separated by a newline and space."""
        if self.comment is None:
            self.comment = string
        else:
            self.comment += "\n " + string
